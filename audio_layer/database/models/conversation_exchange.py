"""
ConversationExchange モデル

憲法III: テストファーストに従い、contract テストを先に実装済み
data-model.md 仕様に基づく個別発話・応答ペア管理
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class ConversationExchange:
    """
    会話交換データクラス
    
    data-model.md 契約:
    - wake_word_confidence: 0.0-1.0
    - response_time_ms: > 0
    - voicevox_speaker_id: VoiceVoxの有効なスピーカーID
    """
    id: Optional[int] = None
    session_id: str = None
    exchange_order: int = None
    timestamp: Optional[datetime] = None
    wake_word_confidence: Optional[float] = None
    user_input: str = None
    agent_response: str = None
    response_time_ms: Optional[int] = None
    voicevox_speaker_id: int = 1
    langflow_flow_id: Optional[str] = None
    
    def __post_init__(self):
        """バリデーション実行"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # data-model.md バリデーション契約
        self._validate_wake_word_confidence()
        self._validate_response_time()
        self._validate_voicevox_speaker_id()
        self._validate_required_fields()
    
    def _validate_wake_word_confidence(self):
        """wake_word_confidence 0.0-1.0 バリデーション"""
        if self.wake_word_confidence is not None:
            if not (0.0 <= self.wake_word_confidence <= 1.0):
                raise ValueError(f"wake_word_confidence must be between 0.0-1.0, got: {self.wake_word_confidence}")
    
    def _validate_response_time(self):
        """response_time_ms > 0 バリデーション"""
        if self.response_time_ms is not None:
            if self.response_time_ms <= 0:
                raise ValueError(f"response_time_ms must be > 0, got: {self.response_time_ms}")
            
            # 憲法V: パフォーマンス制約 - 音声応答<3秒
            if self.response_time_ms > 3000:
                # 警告ログ（実装時にloggingで出力）
                pass  # TODO: logging.warning(f"Response time {self.response_time_ms}ms exceeds 3s constraint")
    
    def _validate_voicevox_speaker_id(self):
        """voicevox_speaker_id 有効範囲バリデーション"""
        # VoiceVox有効スピーカーID範囲（一般的に0-50程度）
        if not (0 <= self.voicevox_speaker_id <= 50):
            raise ValueError(f"voicevox_speaker_id must be valid VoiceVox speaker (0-50), got: {self.voicevox_speaker_id}")
    
    def _validate_required_fields(self):
        """必須フィールドバリデーション"""
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.user_input:
            raise ValueError("user_input is required")
        if not self.agent_response:
            raise ValueError("agent_response is required")
        if self.exchange_order is None:
            raise ValueError("exchange_order is required")
    
    def is_yes_man_response(self) -> bool:
        """Yes-Man性格特性応答判定"""
        if not self.agent_response:
            return False
            
        # Yes-Man特性キーワード
        yes_man_indicators = [
            "はい！", "もちろん", "喜んで", "お任せ", "得意", 
            "！", "ですよ", "しますね", "できます"
        ]
        
        return any(indicator in self.agent_response for indicator in yes_man_indicators)
    
    def meets_performance_constraints(self) -> bool:
        """パフォーマンス制約遵守判定"""
        if self.response_time_ms is None:
            return False
        
        # 憲法V: 音声応答<3秒制約
        return self.response_time_ms < 3000


class ConversationExchangeRepository:
    """
    ConversationExchange データアクセス層
    
    憲法II: 直接DB操作（Repository/UoWパターン回避）
    """
    
    def __init__(self, db_path: str = "yes_man.db"):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """データベース接続取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_exchange(self, exchange: ConversationExchange) -> int:
        """
        新規会話交換作成
        
        Returns:
            int: 作成された交換のid
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversation_exchanges 
                (session_id, exchange_order, timestamp, wake_word_confidence, 
                 user_input, agent_response, response_time_ms, voicevox_speaker_id, langflow_flow_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exchange.session_id,
                exchange.exchange_order,
                exchange.timestamp.isoformat() if exchange.timestamp else None,
                exchange.wake_word_confidence,
                exchange.user_input,
                exchange.agent_response,
                exchange.response_time_ms,
                exchange.voicevox_speaker_id,
                exchange.langflow_flow_id
            ))
            exchange_id = cursor.lastrowid
            conn.commit()
            return exchange_id
    
    def get_exchanges_by_session_id(self, session_id: str) -> List[ConversationExchange]:
        """session_id による会話交換一覧取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversation_exchanges 
                WHERE session_id = ? 
                ORDER BY exchange_order ASC
            """, (session_id,))
            
            return [self._row_to_exchange(row) for row in cursor.fetchall()]
    
    def get_next_exchange_order(self, session_id: str) -> int:
        """session_id の次の exchange_order 取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(MAX(exchange_order), 0) + 1 as next_order
                FROM conversation_exchanges 
                WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            return row["next_order"]
    
    def get_recent_exchanges(self, limit: int = 50) -> List[ConversationExchange]:
        """最近の会話交換取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversation_exchanges 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            return [self._row_to_exchange(row) for row in cursor.fetchall()]
    
    def get_performance_metrics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """パフォーマンス指標取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            where_clause = "WHERE session_id = ?" if session_id else ""
            params = (session_id,) if session_id else ()
            
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_exchanges,
                    AVG(response_time_ms) as avg_response_time,
                    MIN(response_time_ms) as min_response_time,
                    MAX(response_time_ms) as max_response_time,
                    AVG(wake_word_confidence) as avg_confidence,
                    COUNT(CASE WHEN response_time_ms < 3000 THEN 1 END) as under_3s_count
                FROM conversation_exchanges 
                {where_clause}
            """, params)
            
            row = cursor.fetchone()
            
            metrics = {
                "total_exchanges": row["total_exchanges"],
                "avg_response_time_ms": row["avg_response_time"],
                "min_response_time_ms": row["min_response_time"],
                "max_response_time_ms": row["max_response_time"],
                "avg_wake_word_confidence": row["avg_confidence"],
                "performance_compliance_rate": 0.0
            }
            
            # 憲法V: パフォーマンス制約遵守率計算
            if metrics["total_exchanges"] > 0:
                metrics["performance_compliance_rate"] = row["under_3s_count"] / metrics["total_exchanges"]
            
            return metrics
    
    def search_exchanges_by_content(self, search_term: str, limit: int = 100) -> List[ConversationExchange]:
        """会話内容による検索"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversation_exchanges 
                WHERE user_input LIKE ? OR agent_response LIKE ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (f"%{search_term}%", f"%{search_term}%", limit))
            
            return [self._row_to_exchange(row) for row in cursor.fetchall()]
    
    def get_yes_man_response_rate(self, session_id: Optional[str] = None) -> float:
        """Yes-Man性格応答率取得"""
        exchanges = (self.get_exchanges_by_session_id(session_id) 
                    if session_id else self.get_recent_exchanges(1000))
        
        if not exchanges:
            return 0.0
        
        yes_man_count = sum(1 for exchange in exchanges if exchange.is_yes_man_response())
        return yes_man_count / len(exchanges)
    
    def _row_to_exchange(self, row: sqlite3.Row) -> ConversationExchange:
        """SQLite Row → ConversationExchange 変換"""
        return ConversationExchange(
            id=row["id"],
            session_id=row["session_id"],
            exchange_order=row["exchange_order"],
            timestamp=datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else None,
            wake_word_confidence=row["wake_word_confidence"],
            user_input=row["user_input"],
            agent_response=row["agent_response"],
            response_time_ms=row["response_time_ms"],
            voicevox_speaker_id=row["voicevox_speaker_id"],
            langflow_flow_id=row["langflow_flow_id"]
        )