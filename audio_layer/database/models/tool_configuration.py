"""
ToolConfiguration モデル

憲法III: テストファーストに従い、contract テストを先に実装済み
data-model.md 仕様に基づく利用可能ツール設定管理
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass


@dataclass
class ToolConfiguration:
    """
    ツール設定データクラス
    
    data-model.md 契約:
    - デフォルトツール: calculator, timer, weather, datetime
    - 使用統計追跡: last_used_at, usage_count
    """
    tool_name: str
    is_enabled: bool = True
    priority_order: int = 0
    config_json: Optional[str] = None
    description: Optional[str] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """バリデーション実行"""
        if self.updated_at is None:
            self.updated_at = datetime.now()
        
        self._validate_tool_name()
        self._validate_config_json()
    
    def _validate_tool_name(self):
        """tool_name バリデーション"""
        if not self.tool_name:
            raise ValueError("tool_name is required")
        if not isinstance(self.tool_name, str):
            raise ValueError("tool_name must be string")
    
    def _validate_config_json(self):
        """config_json JSON形式バリデーション"""
        if self.config_json:
            try:
                json.loads(self.config_json)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in config_json: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """設定JSON取得（パース済み）"""
        if self.config_json:
            try:
                return json.loads(self.config_json)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """設定JSON設定"""
        self.config_json = json.dumps(config, ensure_ascii=False) if config else None
        self.updated_at = datetime.now()
    
    def record_usage(self) -> None:
        """使用記録更新"""
        self.last_used_at = datetime.now()
        self.usage_count += 1
        self.updated_at = datetime.now()
    
    def is_available(self) -> bool:
        """ツール利用可能性判定"""
        return self.is_enabled
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """使用統計取得"""
        return {
            "tool_name": self.tool_name,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "days_since_last_use": (datetime.now() - self.last_used_at).days if self.last_used_at else None,
            "is_enabled": self.is_enabled
        }


class ToolConfigurationRepository:
    """
    ToolConfiguration データアクセス層
    
    憲法II: 直接DB操作（Repository/UoWパターン回避）
    Yes-Man専用ツールの管理とデフォルト設定提供
    """
    
    # data-model.md デフォルトツール設定
    DEFAULT_TOOLS = {
        "calculator": {
            "is_enabled": True,
            "priority_order": 1,
            "config_json": json.dumps({
                "precision": 4,
                "max_expression_length": 100,
                "allowed_operations": ["+", "-", "*", "/"],
                "output_format": "number"
            }, ensure_ascii=False),
            "description": "基本計算機能（四則演算）"
        },
        "timer": {
            "is_enabled": True,
            "priority_order": 2,
            "config_json": json.dumps({
                "max_duration_seconds": 86400,  # 24時間
                "max_concurrent_timers": 10,
                "notification_sound": True,
                "custom_messages": True
            }, ensure_ascii=False),
            "description": "タイマー機能（複数並行実行対応）"
        },
        "datetime": {
            "is_enabled": True,
            "priority_order": 3,
            "config_json": json.dumps({
                "default_timezone": "Asia/Tokyo",
                "default_format": "%Y年%m月%d日 %H時%M分",
                "include_weekday": True
            }, ensure_ascii=False),
            "description": "日時情報取得機能"
        },
        "weather": {
            "is_enabled": False,  # 将来拡張
            "priority_order": 4,
            "config_json": json.dumps({
                "api_provider": "openweathermap",
                "default_location": "Tokyo",
                "units": "metric",
                "forecast_days": 3
            }, ensure_ascii=False),
            "description": "天気情報取得機能（将来拡張予定）"
        }
    }
    
    def __init__(self, db_path: str = "yes_man.db"):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """データベース接続取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_tool(self, tool_name: str) -> Optional[ToolConfiguration]:
        """ツール設定取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tool_configurations WHERE tool_name = ?
            """, (tool_name,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_tool(row)
            return None
    
    def get_enabled_tools(self, order_by_priority: bool = True) -> List[ToolConfiguration]:
        """有効ツール一覧取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            order_clause = "ORDER BY priority_order ASC, tool_name ASC" if order_by_priority else "ORDER BY tool_name ASC"
            
            cursor.execute(f"""
                SELECT * FROM tool_configurations 
                WHERE is_enabled = 1 
                {order_clause}
            """)
            
            return [self._row_to_tool(row) for row in cursor.fetchall()]
    
    def get_all_tools(self) -> List[ToolConfiguration]:
        """全ツール取得（無効含む）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tool_configurations 
                ORDER BY priority_order ASC, tool_name ASC
            """)
            
            return [self._row_to_tool(row) for row in cursor.fetchall()]
    
    def save_tool(self, tool: ToolConfiguration) -> bool:
        """ツール設定保存（UPSERT）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tool_configurations 
                (tool_name, is_enabled, priority_order, config_json, description, 
                 last_used_at, usage_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tool.tool_name,
                tool.is_enabled,
                tool.priority_order,
                tool.config_json,
                tool.description,
                tool.last_used_at.isoformat() if tool.last_used_at else None,
                tool.usage_count,
                tool.updated_at.isoformat() if tool.updated_at else None
            ))
            
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows > 0
    
    def enable_tool(self, tool_name: str) -> bool:
        """ツール有効化"""
        return self._update_tool_enabled_status(tool_name, True)
    
    def disable_tool(self, tool_name: str) -> bool:
        """ツール無効化"""
        return self._update_tool_enabled_status(tool_name, False)
    
    def _update_tool_enabled_status(self, tool_name: str, is_enabled: bool) -> bool:
        """ツール有効/無効状態更新"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_configurations 
                SET is_enabled = ?, updated_at = ?
                WHERE tool_name = ?
            """, (is_enabled, datetime.now().isoformat(), tool_name))
            
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows > 0
    
    def record_tool_usage(self, tool_name: str) -> bool:
        """ツール使用記録"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE tool_configurations 
                SET usage_count = usage_count + 1, 
                    last_used_at = ?, 
                    updated_at = ?
                WHERE tool_name = ?
            """, (now, now, tool_name))
            
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows > 0
    
    def get_tool_usage_statistics(self) -> List[Dict[str, Any]]:
        """全ツール使用統計取得"""
        tools = self.get_all_tools()
        return [tool.get_usage_statistics() for tool in tools]
    
    def get_most_used_tools(self, limit: int = 5) -> List[ToolConfiguration]:
        """使用頻度上位ツール取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tool_configurations 
                WHERE usage_count > 0
                ORDER BY usage_count DESC, last_used_at DESC
                LIMIT ?
            """, (limit,))
            
            return [self._row_to_tool(row) for row in cursor.fetchall()]
    
    def initialize_default_tools(self) -> int:
        """デフォルトツール初期化"""
        count = 0
        for tool_name, config in self.DEFAULT_TOOLS.items():
            tool = ToolConfiguration(
                tool_name=tool_name,
                is_enabled=config["is_enabled"],
                priority_order=config["priority_order"],
                config_json=config["config_json"],
                description=config["description"]
            )
            if self.save_tool(tool):
                count += 1
        return count
    
    def update_tool_priority(self, tool_name: str, new_priority: int) -> bool:
        """ツール優先度更新"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_configurations 
                SET priority_order = ?, updated_at = ?
                WHERE tool_name = ?
            """, (new_priority, datetime.now().isoformat(), tool_name))
            
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows > 0
    
    def cleanup_unused_tools(self, days_threshold: int = 90) -> int:
        """長期間未使用ツールのクリーンアップ"""
        cutoff_date = datetime.now() - datetime.timedelta(days=days_threshold)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_configurations 
                SET is_enabled = 0, updated_at = ?
                WHERE last_used_at < ? OR last_used_at IS NULL
                AND tool_name NOT IN ('calculator', 'timer', 'datetime')  -- コアツールは除外
            """, (datetime.now().isoformat(), cutoff_date.isoformat()))
            
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows
    
    def _row_to_tool(self, row: sqlite3.Row) -> ToolConfiguration:
        """SQLite Row → ToolConfiguration 変換"""
        return ToolConfiguration(
            tool_name=row["tool_name"],
            is_enabled=bool(row["is_enabled"]),
            priority_order=row["priority_order"],
            config_json=row["config_json"],
            description=row["description"],
            last_used_at=datetime.fromisoformat(row["last_used_at"]) if row["last_used_at"] else None,
            usage_count=row["usage_count"],
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
        )