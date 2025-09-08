"""
AudioSettings モデル

憲法III: テストファーストに従い、contract テストを先に実装済み
data-model.md 仕様に基づく音声処理関連設定管理
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum


class AudioSettingType(Enum):
    """音声設定データ型列挙型"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"


@dataclass
class AudioSetting:
    """
    音声設定データクラス
    
    data-model.md 契約:
    - 主要設定: microphone_device_id, whisper_model_size, audio_buffer_seconds, etc.
    - 憲法IV: プライバシーファースト対応設定
    """
    setting_name: str
    setting_value: str
    setting_type: str = AudioSettingType.STRING.value
    description: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """バリデーション実行"""
        if self.updated_at is None:
            self.updated_at = datetime.now()
        
        self._validate_setting_name()
        self._validate_setting_type()
    
    def _validate_setting_name(self):
        """setting_name バリデーション"""
        if not self.setting_name:
            raise ValueError("setting_name is required")
        if not isinstance(self.setting_name, str):
            raise ValueError("setting_name must be string")
    
    def _validate_setting_type(self):
        """setting_type 列挙型バリデーション"""
        valid_types = [stype.value for stype in AudioSettingType]
        if self.setting_type not in valid_types:
            raise ValueError(f"setting_type must be one of {valid_types}, got: {self.setting_type}")
    
    def get_typed_value(self) -> Union[str, int, float, bool]:
        """setting_type に基づく型変換値取得"""
        if self.setting_type == AudioSettingType.STRING.value:
            return self.setting_value
        elif self.setting_type == AudioSettingType.INTEGER.value:
            try:
                return int(self.setting_value)
            except ValueError:
                raise ValueError(f"Cannot convert '{self.setting_value}' to integer")
        elif self.setting_type == AudioSettingType.FLOAT.value:
            try:
                return float(self.setting_value)
            except ValueError:
                raise ValueError(f"Cannot convert '{self.setting_value}' to float")
        elif self.setting_type == AudioSettingType.BOOLEAN.value:
            if self.setting_value.lower() in ("true", "1", "yes", "on"):
                return True
            elif self.setting_value.lower() in ("false", "0", "no", "off"):
                return False
            else:
                raise ValueError(f"Cannot convert '{self.setting_value}' to boolean")
        else:
            return self.setting_value
    
    def set_typed_value(self, value: Union[str, int, float, bool]) -> None:
        """型付き値から文字列値設定"""
        if self.setting_type == AudioSettingType.BOOLEAN.value:
            self.setting_value = "true" if value else "false"
        else:
            self.setting_value = str(value)
        
        self.updated_at = datetime.now()


class AudioSettingsRepository:
    """
    AudioSettings データアクセス層
    
    憲法II: 直接DB操作（Repository/UoWパターン回避）
    憲法IV: プライバシーファースト対応音声設定管理
    """
    
    # data-model.md 主要音声設定 + 憲法制約対応
    DEFAULT_SETTINGS = {
        "microphone_device_id": {
            "value": "default",
            "type": AudioSettingType.STRING.value,
            "description": "マイクデバイス識別子（デフォルト自動選択）"
        },
        "whisper_model_size": {
            "value": "medium",
            "type": AudioSettingType.STRING.value,
            "description": "Whisperモデルサイズ（small/medium/large）"
        },
        "audio_buffer_seconds": {
            "value": "3",
            "type": AudioSettingType.INTEGER.value,
            "description": "音声バッファサイズ秒数（憲法IV: プライバシー保護）"
        },
        "noise_reduction_enabled": {
            "value": "true",
            "type": AudioSettingType.BOOLEAN.value,
            "description": "ノイズリダクション有効化"
        },
        "vad_sensitivity": {
            "value": "0.5",
            "type": AudioSettingType.FLOAT.value,
            "description": "Voice Activity Detection感度（0.0-1.0）"
        },
        "sample_rate": {
            "value": "16000",
            "type": AudioSettingType.INTEGER.value,
            "description": "音声サンプルレート（Hz）"
        },
        "channels": {
            "value": "1",
            "type": AudioSettingType.INTEGER.value,
            "description": "音声チャンネル数（モノラル）"
        },
        "chunk_size": {
            "value": "1024",
            "type": AudioSettingType.INTEGER.value,
            "description": "音声処理チャンクサイズ"
        },
        "wake_word_model_path": {
            "value": "",
            "type": AudioSettingType.STRING.value,
            "description": "ウェイクワード検出モデルパス"
        },
        "audio_processing_threads": {
            "value": "2",
            "type": AudioSettingType.INTEGER.value,
            "description": "音声処理スレッド数"
        }
    }
    
    def __init__(self, db_path: str = "yes_man.db"):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """データベース接続取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_setting(self, setting_name: str) -> Optional[AudioSetting]:
        """音声設定取得（デフォルト値フォールバック付き）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM audio_settings WHERE setting_name = ?
            """, (setting_name,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_setting(row)
            
            # デフォルト値フォールバック
            if setting_name in self.DEFAULT_SETTINGS:
                default = self.DEFAULT_SETTINGS[setting_name]
                return AudioSetting(
                    setting_name=setting_name,
                    setting_value=default["value"],
                    setting_type=default["type"],
                    description=default["description"]
                )
            
            return None
    
    def set_setting(self, setting_name: str, value: Union[str, int, float, bool], 
                   setting_type: Optional[str] = None, description: Optional[str] = None) -> bool:
        """音声設定値設定"""
        if setting_type is None:
            setting_type = self._infer_setting_type(value)
        
        setting = AudioSetting(
            setting_name=setting_name,
            setting_value="",  # set_typed_value で設定
            setting_type=setting_type,
            description=description
        )
        setting.set_typed_value(value)
        
        return self.save_setting(setting)
    
    def save_setting(self, setting: AudioSetting) -> bool:
        """音声設定保存（UPSERT）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO audio_settings 
                (setting_name, setting_value, setting_type, description, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                setting.setting_name,
                setting.setting_value,
                setting.setting_type,
                setting.description,
                setting.updated_at.isoformat() if setting.updated_at else None
            ))
            
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows > 0
    
    def get_all_settings(self) -> Dict[str, AudioSetting]:
        """全音声設定取得（デフォルト値含む）"""
        settings = {}
        
        # デフォルト設定を先に追加
        for name, default_config in self.DEFAULT_SETTINGS.items():
            settings[name] = AudioSetting(
                setting_name=name,
                setting_value=default_config["value"],
                setting_type=default_config["type"],
                description=default_config["description"]
            )
        
        # データベース設定で上書き
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audio_settings ORDER BY setting_name")
            
            for row in cursor.fetchall():
                setting = self._row_to_setting(row)
                settings[setting.setting_name] = setting
        
        return settings
    
    def get_audio_config(self) -> Dict[str, Any]:
        """音声処理用の型付き設定辞書取得"""
        settings = self.get_all_settings()
        config = {}
        
        for name, setting in settings.items():
            try:
                config[name] = setting.get_typed_value()
            except ValueError:
                # 型変換エラー時はデフォルト値使用
                if name in self.DEFAULT_SETTINGS:
                    default_setting = AudioSetting(
                        setting_name=name,
                        setting_value=self.DEFAULT_SETTINGS[name]["value"],
                        setting_type=self.DEFAULT_SETTINGS[name]["type"]
                    )
                    config[name] = default_setting.get_typed_value()
        
        return config
    
    def get_whisper_config(self) -> Dict[str, Any]:
        """Whisper.cpp用設定取得"""
        config = self.get_audio_config()
        return {
            "model_size": config.get("whisper_model_size", "medium"),
            "sample_rate": config.get("sample_rate", 16000),
            "channels": config.get("channels", 1),
            "chunk_size": config.get("chunk_size", 1024),
            "vad_sensitivity": config.get("vad_sensitivity", 0.5),
            "processing_threads": config.get("audio_processing_threads", 2)
        }
    
    def get_privacy_config(self) -> Dict[str, Any]:
        """プライバシー保護用設定取得（憲法IV対応）"""
        config = self.get_audio_config()
        return {
            "audio_buffer_seconds": config.get("audio_buffer_seconds", 3),
            "memory_only_processing": True,  # 憲法IV: ディスク書き込み禁止
            "auto_cleanup_enabled": True,
            "max_session_duration_minutes": 60  # 長時間セッション制限
        }
    
    def validate_audio_settings(self) -> Dict[str, List[str]]:
        """音声設定の整合性検証"""
        errors = {}
        config = self.get_audio_config()
        
        # audio_buffer_seconds 検証（憲法IV: 3秒制約）
        buffer_seconds = config.get("audio_buffer_seconds", 3)
        if buffer_seconds != 3:
            errors["audio_buffer_seconds"] = ["Must be 3 seconds for privacy protection (Constitution IV)"]
        
        # whisper_model_size 検証
        model_size = config.get("whisper_model_size", "medium")
        if model_size not in ["tiny", "small", "medium", "large", "large-v2"]:
            errors["whisper_model_size"] = ["Must be valid Whisper model size"]
        
        # vad_sensitivity 検証
        vad_sensitivity = config.get("vad_sensitivity", 0.5)
        if not (0.0 <= vad_sensitivity <= 1.0):
            errors["vad_sensitivity"] = ["Must be between 0.0-1.0"]
        
        # sample_rate 検証
        sample_rate = config.get("sample_rate", 16000)
        valid_rates = [8000, 16000, 22050, 44100, 48000]
        if sample_rate not in valid_rates:
            errors["sample_rate"] = [f"Must be one of {valid_rates}"]
        
        return errors
    
    def reset_to_defaults(self) -> int:
        """デフォルト音声設定にリセット"""
        count = 0
        for name, default_config in self.DEFAULT_SETTINGS.items():
            setting = AudioSetting(
                setting_name=name,
                setting_value=default_config["value"],
                setting_type=default_config["type"],
                description=default_config["description"]
            )
            if self.save_setting(setting):
                count += 1
        return count
    
    def optimize_for_performance(self) -> Dict[str, str]:
        """パフォーマンス最適化設定適用（憲法V対応）"""
        optimizations = {}
        
        # CPU使用率30%以下の制約対応
        if self.set_setting("whisper_model_size", "small"):  # mediumより軽量
            optimizations["whisper_model_size"] = "small (CPU optimization)"
        
        if self.set_setting("audio_processing_threads", 2):  # CPU負荷分散
            optimizations["audio_processing_threads"] = "2 (balanced processing)"
        
        if self.set_setting("chunk_size", 512):  # 小さなチャンクでレスポンス向上
            optimizations["chunk_size"] = "512 (low latency)"
        
        if self.set_setting("vad_sensitivity", 0.7):  # 高感度で早期検出
            optimizations["vad_sensitivity"] = "0.7 (quick detection)"
        
        return optimizations
    
    def _infer_setting_type(self, value: Any) -> str:
        """値から setting_type を推論"""
        if isinstance(value, bool):
            return AudioSettingType.BOOLEAN.value
        elif isinstance(value, int):
            return AudioSettingType.INTEGER.value
        elif isinstance(value, float):
            return AudioSettingType.FLOAT.value
        else:
            return AudioSettingType.STRING.value
    
    def _row_to_setting(self, row: sqlite3.Row) -> AudioSetting:
        """SQLite Row → AudioSetting 変換"""
        return AudioSetting(
            setting_name=row["setting_name"],
            setting_value=row["setting_value"],
            setting_type=row["setting_type"],
            description=row["description"],
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
        )