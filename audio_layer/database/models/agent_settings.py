"""
AgentSettings モデル

憲法III: テストファーストに従い、contract テストを先に実装済み
data-model.md 仕様に基づくYes-Manエージェント設定管理
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum


class DataType(Enum):
    """設定データ型列挙型"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"


@dataclass
class AgentSetting:
    """
    エージェント設定データクラス
    
    data-model.md 契約:
    - data_type: string, integer, float, boolean, json
    - 主要設定項目の適切な型変換
    """
    key: str
    value: str
    data_type: str = DataType.STRING.value
    description: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: str = "system"
    
    def __post_init__(self):
        """バリデーション実行"""
        if self.updated_at is None:
            self.updated_at = datetime.now()
        
        self._validate_data_type()
        self._validate_key()
    
    def _validate_data_type(self):
        """data_type 列挙型バリデーション"""
        valid_types = [dtype.value for dtype in DataType]
        if self.data_type not in valid_types:
            raise ValueError(f"data_type must be one of {valid_types}, got: {self.data_type}")
    
    def _validate_key(self):
        """key フィールドバリデーション"""
        if not self.key:
            raise ValueError("key is required")
        if not isinstance(self.key, str):
            raise ValueError("key must be string")
    
    def get_typed_value(self) -> Union[str, int, float, bool, Dict, List]:
        """data_type に基づく型変換値取得"""
        if self.data_type == DataType.STRING.value:
            return self.value
        elif self.data_type == DataType.INTEGER.value:
            try:
                return int(self.value)
            except ValueError:
                raise ValueError(f"Cannot convert '{self.value}' to integer")
        elif self.data_type == DataType.FLOAT.value:
            try:
                return float(self.value)
            except ValueError:
                raise ValueError(f"Cannot convert '{self.value}' to float")
        elif self.data_type == DataType.BOOLEAN.value:
            if self.value.lower() in ("true", "1", "yes", "on"):
                return True
            elif self.value.lower() in ("false", "0", "no", "off"):
                return False
            else:
                raise ValueError(f"Cannot convert '{self.value}' to boolean")
        elif self.data_type == DataType.JSON.value:
            try:
                return json.loads(self.value)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON value '{self.value}': {e}")
        else:
            return self.value
    
    def set_typed_value(self, value: Union[str, int, float, bool, Dict, List]) -> None:
        """型付き値から文字列値設定"""
        if self.data_type == DataType.JSON.value and not isinstance(value, str):
            self.value = json.dumps(value, ensure_ascii=False)
        elif self.data_type == DataType.BOOLEAN.value:
            self.value = "true" if value else "false"
        else:
            self.value = str(value)
        
        self.updated_at = datetime.now()


class AgentSettingsRepository:
    """
    AgentSettings データアクセス層
    
    憲法II: 直接DB操作（Repository/UoWパターン回避）
    Yes-Man専用設定の管理とデフォルト値提供
    """
    
    # data-model.md 主要設定項目
    DEFAULT_SETTINGS = {
        "yes_man_personality_prompt": {
            "value": "あなたは陽気で協力的なYes-Manです。「はい！」「もちろんです！」「喜んで！」などの肯定的な表現を使い、失敗やエラーも前向きに表現してください。",
            "data_type": DataType.STRING.value,
            "description": "Yes-Manのメインキャラクタープロンプト"
        },
        "wake_word_confidence_threshold": {
            "value": "0.8",
            "data_type": DataType.FLOAT.value,
            "description": "ウェイクワード検出信頼度閾値"
        },
        "response_timeout_seconds": {
            "value": "30",
            "data_type": DataType.INTEGER.value,
            "description": "エージェント応答タイムアウト秒数"
        },
        "silence_detection_seconds": {
            "value": "5",
            "data_type": DataType.INTEGER.value,
            "description": "会話終了判定の無音秒数"
        },
        "voicevox_default_speaker": {
            "value": "1",
            "data_type": DataType.INTEGER.value,
            "description": "VoiceVoxデフォルトスピーカーID"
        }
    }
    
    def __init__(self, db_path: str = "yes_man.db"):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """データベース接続取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_setting(self, key: str) -> Optional[AgentSetting]:
        """設定取得（デフォルト値フォールバック付き）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_settings WHERE key = ?
            """, (key,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_setting(row)
            
            # デフォルト値フォールバック
            if key in self.DEFAULT_SETTINGS:
                default = self.DEFAULT_SETTINGS[key]
                return AgentSetting(
                    key=key,
                    value=default["value"],
                    data_type=default["data_type"],
                    description=default["description"],
                    updated_by="default"
                )
            
            return None
    
    def set_setting(self, key: str, value: Union[str, int, float, bool, Dict, List], 
                   data_type: Optional[str] = None, description: Optional[str] = None,
                   updated_by: str = "user") -> bool:
        """設定値設定（型自動判定付き）"""
        if data_type is None:
            data_type = self._infer_data_type(value)
        
        setting = AgentSetting(
            key=key,
            value="",  # set_typed_value で設定
            data_type=data_type,
            description=description,
            updated_by=updated_by
        )
        setting.set_typed_value(value)
        
        return self.save_setting(setting)
    
    def save_setting(self, setting: AgentSetting) -> bool:
        """設定保存（UPSERT）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO agent_settings 
                (key, value, data_type, description, updated_at, updated_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                setting.key,
                setting.value,
                setting.data_type,
                setting.description,
                setting.updated_at.isoformat() if setting.updated_at else None,
                setting.updated_by
            ))
            
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows > 0
    
    def get_all_settings(self) -> Dict[str, AgentSetting]:
        """全設定取得（デフォルト値含む）"""
        settings = {}
        
        # デフォルト設定を先に追加
        for key, default_config in self.DEFAULT_SETTINGS.items():
            settings[key] = AgentSetting(
                key=key,
                value=default_config["value"],
                data_type=default_config["data_type"],
                description=default_config["description"],
                updated_by="default"
            )
        
        # データベース設定で上書き
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_settings ORDER BY key")
            
            for row in cursor.fetchall():
                setting = self._row_to_setting(row)
                settings[setting.key] = setting
        
        return settings
    
    def get_yes_man_config(self) -> Dict[str, Any]:
        """Yes-Man固有設定の型付き辞書取得"""
        settings = self.get_all_settings()
        config = {}
        
        for key, setting in settings.items():
            try:
                config[key] = setting.get_typed_value()
            except ValueError:
                # 型変換エラー時はデフォルト値使用
                if key in self.DEFAULT_SETTINGS:
                    default_setting = AgentSetting(
                        key=key,
                        value=self.DEFAULT_SETTINGS[key]["value"],
                        data_type=self.DEFAULT_SETTINGS[key]["data_type"]
                    )
                    config[key] = default_setting.get_typed_value()
        
        return config
    
    def reset_to_defaults(self) -> int:
        """デフォルト設定にリセット"""
        count = 0
        for key, default_config in self.DEFAULT_SETTINGS.items():
            setting = AgentSetting(
                key=key,
                value=default_config["value"],
                data_type=default_config["data_type"],
                description=default_config["description"],
                updated_by="system_reset"
            )
            if self.save_setting(setting):
                count += 1
        return count
    
    def validate_yes_man_settings(self) -> Dict[str, List[str]]:
        """Yes-Man設定の整合性検証"""
        errors = {}
        config = self.get_yes_man_config()
        
        # wake_word_confidence_threshold 検証
        threshold = config.get("wake_word_confidence_threshold", 0.8)
        if not (0.0 <= threshold <= 1.0):
            errors["wake_word_confidence_threshold"] = ["Must be between 0.0-1.0"]
        
        # response_timeout_seconds 検証
        timeout = config.get("response_timeout_seconds", 30)
        if timeout <= 0 or timeout > 300:  # 最大5分
            errors["response_timeout_seconds"] = ["Must be between 1-300 seconds"]
        
        # voicevox_default_speaker 検証
        speaker_id = config.get("voicevox_default_speaker", 1)
        if not (0 <= speaker_id <= 50):  # VoiceVox有効範囲
            errors["voicevox_default_speaker"] = ["Must be valid VoiceVox speaker ID (0-50)"]
        
        return errors
    
    def _infer_data_type(self, value: Any) -> str:
        """値から data_type を推論"""
        if isinstance(value, bool):
            return DataType.BOOLEAN.value
        elif isinstance(value, int):
            return DataType.INTEGER.value
        elif isinstance(value, float):
            return DataType.FLOAT.value
        elif isinstance(value, (dict, list)):
            return DataType.JSON.value
        else:
            return DataType.STRING.value
    
    def _row_to_setting(self, row: sqlite3.Row) -> AgentSetting:
        """SQLite Row → AgentSetting 変換"""
        return AgentSetting(
            key=row["key"],
            value=row["value"],
            data_type=row["data_type"],
            description=row["description"],
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
            updated_by=row["updated_by"]
        )