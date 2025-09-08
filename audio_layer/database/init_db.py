"""
データベース初期化とマイグレーション

憲法III: テストファーストに従い、contract テストを先に実装済み
data-model.md 仕様に基づくSQLiteデータベース初期セットアップ
"""

import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

from .models.conversation_session import ConversationSessionRepository
from .models.conversation_exchange import ConversationExchangeRepository  
from .models.agent_settings import AgentSettingsRepository
from .models.tool_configuration import ToolConfigurationRepository
from .models.audio_settings import AudioSettingsRepository


class DatabaseInitializer:
    """
    Yes-Manデータベース初期化管理
    
    憲法II: 直接DB操作で単純化
    data-model.md完全準拠のスキーマ作成
    """
    
    def __init__(self, db_path: str = "yes_man.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def initialize_database(self, force_recreate: bool = False) -> bool:
        """
        データベース完全初期化
        
        Args:
            force_recreate: 既存DB削除して再作成
            
        Returns:
            bool: 初期化成功
        """
        try:
            if force_recreate and os.path.exists(self.db_path):
                os.remove(self.db_path)
                self.logger.info(f"Existing database {self.db_path} removed")
            
            # 1. テーブル作成
            self._create_tables()
            self.logger.info("Database tables created successfully")
            
            # 2. インデックス作成
            self._create_indexes()
            self.logger.info("Database indexes created successfully")
            
            # 3. デフォルトデータ投入
            self._insert_default_data()
            self.logger.info("Default data inserted successfully")
            
            # 4. 初期化検証
            if self._verify_initialization():
                self.logger.info(f"Database initialization completed: {self.db_path}")
                return True
            else:
                self.logger.error("Database initialization verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            return False
    
    def _create_tables(self) -> None:
        """data-model.mdスキーマに基づくテーブル作成"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # ConversationSession テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ended_at DATETIME NULL,
                    user_name TEXT NULL,
                    total_exchanges INTEGER DEFAULT 0,
                    session_status TEXT DEFAULT 'active'
                )
            """)
            
            # ConversationExchange テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_exchanges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    exchange_order INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    wake_word_confidence REAL,
                    user_input TEXT NOT NULL,
                    agent_response TEXT NOT NULL,
                    response_time_ms INTEGER,
                    voicevox_speaker_id INTEGER DEFAULT 1,
                    langflow_flow_id TEXT,
                    FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id)
                )
            """)
            
            # AgentSettings テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    data_type TEXT DEFAULT 'string',
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT DEFAULT 'system'
                )
            """)
            
            # ToolConfiguration テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_configurations (
                    tool_name TEXT PRIMARY KEY,
                    is_enabled BOOLEAN DEFAULT TRUE,
                    priority_order INTEGER DEFAULT 0,
                    config_json TEXT,
                    description TEXT,
                    last_used_at DATETIME NULL,
                    usage_count INTEGER DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # AudioSettings テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audio_settings (
                    setting_name TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL,
                    setting_type TEXT DEFAULT 'string',
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def _create_indexes(self) -> None:
        """data-model.mdパフォーマンス最適化インデックス作成"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # ConversationExchange パフォーマンス最適化インデックス
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_exchanges_session_timestamp 
                ON conversation_exchanges(session_id, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_exchanges_timestamp 
                ON conversation_exchanges(timestamp)
            """)
            
            # AgentSettings 更新日時インデックス
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_settings_updated_at 
                ON agent_settings(updated_at)
            """)
            
            # ToolConfiguration 有効性・優先度インデックス
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tool_configurations_enabled_priority 
                ON tool_configurations(is_enabled, priority_order)
            """)
            
            # AudioSettings 設定名検索インデックス
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audio_settings_name_type
                ON audio_settings(setting_name, setting_type)
            """)
            
            conn.commit()
    
    def _insert_default_data(self) -> None:
        """デフォルトデータ投入"""
        # AgentSettings デフォルト値
        agent_repo = AgentSettingsRepository(self.db_path)
        agent_repo.reset_to_defaults()
        
        # ToolConfiguration デフォルトツール
        tool_repo = ToolConfigurationRepository(self.db_path)
        tool_repo.initialize_default_tools()
        
        # AudioSettings デフォルト設定
        audio_repo = AudioSettingsRepository(self.db_path)
        audio_repo.reset_to_defaults()
        
        # システム初期化記録
        self._record_initialization()
    
    def _record_initialization(self) -> None:
        """システム初期化記録"""
        agent_repo = AgentSettingsRepository(self.db_path)
        agent_repo.set_setting(
            "system_initialized_at",
            datetime.now().isoformat(),
            "string",
            "Yes-Manシステム初期化日時",
            "system"
        )
        agent_repo.set_setting(
            "database_version",
            "1.0.0",
            "string", 
            "データベーススキーマバージョン",
            "system"
        )
    
    def _verify_initialization(self) -> bool:
        """初期化検証"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 必要テーブルの存在確認
                required_tables = [
                    "conversation_sessions",
                    "conversation_exchanges", 
                    "agent_settings",
                    "tool_configurations",
                    "audio_settings"
                ]
                
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                for table in required_tables:
                    if table not in existing_tables:
                        self.logger.error(f"Required table {table} not found")
                        return False
                
                # デフォルトデータの存在確認
                cursor.execute("SELECT COUNT(*) FROM agent_settings")
                agent_settings_count = cursor.fetchone()[0]
                if agent_settings_count == 0:
                    self.logger.error("No default agent settings found")
                    return False
                
                cursor.execute("SELECT COUNT(*) FROM tool_configurations")
                tools_count = cursor.fetchone()[0]
                if tools_count == 0:
                    self.logger.error("No default tools found")
                    return False
                
                cursor.execute("SELECT COUNT(*) FROM audio_settings")
                audio_settings_count = cursor.fetchone()[0]
                if audio_settings_count == 0:
                    self.logger.error("No default audio settings found")
                    return False
                
                return True
                
        except Exception as e:
            self.logger.error(f"Database verification failed: {e}")
            return False
    
    def get_database_info(self) -> Dict[str, any]:
        """データベース情報取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # テーブル情報
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                # データ件数
                data_counts = {}
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    data_counts[table] = cursor.fetchone()[0]
                
                # データベースサイズ
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                # システム情報
                agent_repo = AgentSettingsRepository(self.db_path)
                init_time = agent_repo.get_setting("system_initialized_at")
                db_version = agent_repo.get_setting("database_version")
                
                return {
                    "database_path": self.db_path,
                    "database_size_bytes": db_size,
                    "tables": tables,
                    "data_counts": data_counts,
                    "initialized_at": init_time.get_typed_value() if init_time else None,
                    "schema_version": db_version.get_typed_value() if db_version else None,
                    "total_conversations": data_counts.get("conversation_sessions", 0),
                    "total_exchanges": data_counts.get("conversation_exchanges", 0)
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}
    
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """データベースバックアップ"""
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"yes_man_backup_{timestamp}.db"
            
            if not os.path.exists(self.db_path):
                self.logger.error(f"Source database {self.db_path} not found")
                return False
            
            # SQLiteファイルコピー
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            self.logger.info(f"Database backed up to {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            return False
    
    def cleanup_old_data(self, retention_days: int = 90) -> Dict[str, int]:
        """古いデータのクリーンアップ"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            cleanup_counts = {}
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 古いセッション削除
                cursor.execute("""
                    DELETE FROM conversation_exchanges 
                    WHERE session_id IN (
                        SELECT session_id FROM conversation_sessions 
                        WHERE started_at < ?
                    )
                """, (cutoff_date.isoformat(),))
                exchanges_deleted = cursor.rowcount
                
                cursor.execute("""
                    DELETE FROM conversation_sessions 
                    WHERE started_at < ?
                """, (cutoff_date.isoformat(),))
                sessions_deleted = cursor.rowcount
                
                conn.commit()
                
                cleanup_counts = {
                    "sessions_deleted": sessions_deleted,
                    "exchanges_deleted": exchanges_deleted,
                    "retention_days": retention_days
                }
                
                self.logger.info(f"Cleanup completed: {cleanup_counts}")
                return cleanup_counts
                
        except Exception as e:
            self.logger.error(f"Database cleanup failed: {e}")
            return {"error": str(e)}


def main():
    """
    データベース初期化メインエントリーポイント
    
    Usage:
        python -m audio_layer.database.init_db
    """
    import argparse
    import sys
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="Yes-Man Database Initializer")
    parser.add_argument("--db-path", default="yes_man.db", 
                       help="Database file path (default: yes_man.db)")
    parser.add_argument("--force", action="store_true",
                       help="Force recreate existing database")
    parser.add_argument("--info", action="store_true",
                       help="Show database information")
    parser.add_argument("--backup", type=str, nargs='?', const="auto",
                       help="Create database backup")
    parser.add_argument("--cleanup", type=int, nargs='?', const=90,
                       help="Cleanup old data (retention days, default: 90)")
    
    args = parser.parse_args()
    
    initializer = DatabaseInitializer(args.db_path)
    
    try:
        if args.info:
            info = initializer.get_database_info()
            print("=== Yes-Man Database Information ===")
            for key, value in info.items():
                print(f"{key}: {value}")
            return
        
        if args.backup:
            backup_path = None if args.backup == "auto" else args.backup
            if initializer.backup_database(backup_path):
                print(f"Database backup completed")
            else:
                print("Database backup failed")
                sys.exit(1)
            return
        
        if args.cleanup is not None:
            results = initializer.cleanup_old_data(args.cleanup)
            print(f"Cleanup completed: {results}")
            return
        
        # デフォルト: データベース初期化
        if initializer.initialize_database(args.force):
            print(f"✅ Yes-Man database initialized successfully: {args.db_path}")
            
            # 初期化情報表示
            info = initializer.get_database_info()
            print(f"📊 Tables: {len(info['tables'])}, Total size: {info['database_size_bytes']} bytes")
        else:
            print("❌ Database initialization failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()