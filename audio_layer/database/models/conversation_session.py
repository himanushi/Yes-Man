"""
ConversationSession モデル

憲法III: テストファーストに従い、contract テストを先に実装済み
data-model.md 仕様に基づくユーザー対話セッション管理
"""

import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class SessionStatus(Enum):
    """セッション状態列挙型"""
    ACTIVE = "active"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"


@dataclass
class ConversationSession:
    """
    対話セッションデータクラス
    
    data-model.md 契約:
    - session_id: UUID v4形式
    - session_status: enum('active', 'completed', 'interrupted')
    - started_at ≤ ended_at
    """
    id: Optional[int] = None
    session_id: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    user_name: Optional[str] = None
    total_exchanges: int = 0
    session_status: str = SessionStatus.ACTIVE.value
    
    def __post_init__(self):
        """バリデーション実行"""
        if self.session_id is None:
            self.session_id = str(uuid.uuid4())
        if self.started_at is None:
            self.started_at = datetime.now()
        
        # data-model.md バリデーション契約
        self._validate_session_id()
        self._validate_session_status()
        self._validate_timestamps()
    
    def _validate_session_id(self):
        """session_id UUID v4形式バリデーション"""
        if self.session_id:
            try:
                uuid_obj = uuid.UUID(self.session_id, version=4)
                if str(uuid_obj) != self.session_id:
                    raise ValueError(f"Invalid UUID v4 format: {self.session_id}")
            except ValueError as e:
                raise ValueError(f"session_id must be UUID v4 format: {e}")
    
    def _validate_session_status(self):
        """session_status 列挙型バリデーション"""
        valid_statuses = [status.value for status in SessionStatus]
        if self.session_status not in valid_statuses:
            raise ValueError(f"session_status must be one of {valid_statuses}, got: {self.session_status}")
    
    def _validate_timestamps(self):
        """started_at ≤ ended_at バリデーション"""
        if self.started_at and self.ended_at:
            if self.started_at > self.ended_at:
                raise ValueError(f"started_at ({self.started_at}) must be <= ended_at ({self.ended_at})")
    
    def complete_session(self) -> None:
        """セッション完了処理"""
        self.ended_at = datetime.now()
        self.session_status = SessionStatus.COMPLETED.value
        self._validate_timestamps()
    
    def interrupt_session(self) -> None:
        """セッション中断処理"""
        self.ended_at = datetime.now()
        self.session_status = SessionStatus.INTERRUPTED.value
        self._validate_timestamps()


class ConversationSessionRepository:
    """
    ConversationSession データアクセス層
    
    憲法II: 直接DB操作（Repository/UoWパターン回避）
    """
    
    def __init__(self, db_path: str = "yes_man.db"):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """データベース接続取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_session(self, session: ConversationSession) -> int:
        """
        新規セッション作成
        
        Returns:
            int: 作成されたセッションのid
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversation_sessions 
                (session_id, started_at, ended_at, user_name, total_exchanges, session_status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.started_at.isoformat() if session.started_at else None,
                session.ended_at.isoformat() if session.ended_at else None,
                session.user_name,
                session.total_exchanges,
                session.session_status
            ))
            session_id = cursor.lastrowid
            conn.commit()
            return session_id
    
    def get_session_by_session_id(self, session_id: str) -> Optional[ConversationSession]:
        """session_id によるセッション取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversation_sessions WHERE session_id = ?
            """, (session_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_session(row)
            return None
    
    def get_active_sessions(self) -> List[ConversationSession]:
        """アクティブセッション一覧取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversation_sessions 
                WHERE session_status = ? 
                ORDER BY started_at DESC
            """, (SessionStatus.ACTIVE.value,))
            
            return [self._row_to_session(row) for row in cursor.fetchall()]
    
    def update_session(self, session: ConversationSession) -> bool:
        """セッション更新"""
        if not session.id:
            raise ValueError("Cannot update session without id")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE conversation_sessions 
                SET session_id = ?, started_at = ?, ended_at = ?, 
                    user_name = ?, total_exchanges = ?, session_status = ?
                WHERE id = ?
            """, (
                session.session_id,
                session.started_at.isoformat() if session.started_at else None,
                session.ended_at.isoformat() if session.ended_at else None,
                session.user_name,
                session.total_exchanges,
                session.session_status,
                session.id
            ))
            
            updated_rows = cursor.rowcount
            conn.commit()
            return updated_rows > 0
    
    def increment_exchange_count(self, session_id: str) -> bool:
        """会話回数インクリメント"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE conversation_sessions 
                SET total_exchanges = total_exchanges + 1 
                WHERE session_id = ?
            """, (session_id,))
            
            updated_rows = cursor.rowcount
            conn.commit()
            return updated_rows > 0
    
    def get_sessions_by_date_range(self, start_date: datetime, end_date: datetime) -> List[ConversationSession]:
        """日時範囲でのセッション検索"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversation_sessions 
                WHERE started_at >= ? AND started_at <= ?
                ORDER BY started_at DESC
            """, (start_date.isoformat(), end_date.isoformat()))
            
            return [self._row_to_session(row) for row in cursor.fetchall()]
    
    def _row_to_session(self, row: sqlite3.Row) -> ConversationSession:
        """SQLite Row → ConversationSession 変換"""
        return ConversationSession(
            id=row["id"],
            session_id=row["session_id"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            user_name=row["user_name"],
            total_exchanges=row["total_exchanges"],
            session_status=row["session_status"]
        )