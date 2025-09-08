"""
会話履歴管理

憲法III: テストファーストに従い、contract テストを先に実装済み
会話履歴の保存・取得・分析機能
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .database.models.conversation_session import ConversationSession, ConversationSessionRepository
from .database.models.conversation_exchange import ConversationExchange, ConversationExchangeRepository
from .database.models.agent_settings import AgentSettingsRepository


class ConversationStatus(Enum):
    """会話状態"""
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    ARCHIVED = "archived"


@dataclass
class ConversationSummary:
    """会話サマリー"""
    session_id: str
    user_name: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    total_exchanges: int
    duration_minutes: Optional[int]
    topics: List[str] = field(default_factory=list)
    sentiment: str = "neutral"
    status: ConversationStatus = ConversationStatus.ACTIVE


@dataclass
class ConversationAnalytics:
    """会話分析結果"""
    total_sessions: int
    active_sessions: int
    total_exchanges: int
    average_session_duration: float
    top_topics: List[Tuple[str, int]]
    daily_activity: Dict[str, int]
    user_engagement: Dict[str, float]


class ConversationManager:
    """
    会話履歴管理クラス
    
    憲法IV: プライバシーファースト - データは適切に管理・暗号化
    憲法V: パフォーマンス制約 - 効率的な履歴検索
    """
    
    def __init__(self, db_path: str = "yes_man.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # データベースリポジトリ
        self.session_repo = ConversationSessionRepository(db_path)
        self.exchange_repo = ConversationExchangeRepository(db_path)
        self.settings_repo = AgentSettingsRepository(db_path)
        
        # キャッシュ
        self._recent_sessions_cache: Dict[str, ConversationSummary] = {}
        self._cache_expiry = timedelta(minutes=15)
        self._last_cache_update = datetime.now() - self._cache_expiry
    
    async def get_conversation_history(self, 
                                     session_id: str,
                                     limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        指定セッションの会話履歴取得
        
        Args:
            session_id: セッションID
            limit: 取得件数制限
            
        Returns:
            List[Dict]: 会話履歴
        """
        try:
            exchanges = await asyncio.to_thread(
                self.exchange_repo.get_session_exchanges,
                session_id,
                limit
            )
            
            history = []
            for exchange in exchanges:
                history.extend([
                    {
                        "role": "user",
                        "content": exchange.user_input,
                        "timestamp": exchange.timestamp.isoformat(),
                        "exchange_id": exchange.id,
                        "wake_word_confidence": exchange.wake_word_confidence
                    },
                    {
                        "role": "assistant", 
                        "content": exchange.agent_response,
                        "timestamp": exchange.timestamp.isoformat(),
                        "exchange_id": exchange.id,
                        "response_time_ms": exchange.response_time_ms,
                        "flow_id": exchange.langflow_flow_id
                    }
                ])
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation history for {session_id}: {e}")
            return []
    
    async def get_recent_sessions(self, 
                                days: int = 7,
                                include_ended: bool = True) -> List[ConversationSummary]:
        """
        最近の会話セッション取得
        
        Args:
            days: 取得期間（日数）
            include_ended: 終了セッションも含める
            
        Returns:
            List[ConversationSummary]: セッションサマリーリスト
        """
        try:
            # キャッシュ確認
            if self._should_update_cache():
                await self._update_sessions_cache()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_sessions = []
            
            for summary in self._recent_sessions_cache.values():
                if summary.started_at >= cutoff_date:
                    if include_ended or summary.status == ConversationStatus.ACTIVE:
                        recent_sessions.append(summary)
            
            # 開始日時でソート（新しい順）
            recent_sessions.sort(key=lambda x: x.started_at, reverse=True)
            return recent_sessions
            
        except Exception as e:
            self.logger.error(f"Failed to get recent sessions: {e}")
            return []
    
    async def _should_update_cache(self) -> bool:
        """キャッシュ更新が必要かチェック"""
        return datetime.now() - self._last_cache_update > self._cache_expiry
    
    async def _update_sessions_cache(self) -> None:
        """セッションキャッシュ更新"""
        try:
            sessions = await asyncio.to_thread(self.session_repo.get_recent_sessions, days=30)
            
            self._recent_sessions_cache.clear()
            
            for session in sessions:
                # 会話時間計算
                duration_minutes = None
                if session.ended_at:
                    duration = session.ended_at - session.started_at
                    duration_minutes = int(duration.total_seconds() / 60)
                
                # ステータス決定
                status = ConversationStatus.ENDED if session.ended_at else ConversationStatus.ACTIVE
                if session.session_status == "archived":
                    status = ConversationStatus.ARCHIVED
                
                summary = ConversationSummary(
                    session_id=session.session_id,
                    user_name=session.user_name,
                    started_at=session.started_at,
                    ended_at=session.ended_at,
                    total_exchanges=session.total_exchanges,
                    duration_minutes=duration_minutes,
                    status=status
                )
                
                self._recent_sessions_cache[session.session_id] = summary
            
            self._last_cache_update = datetime.now()
            self.logger.debug(f"Updated sessions cache with {len(sessions)} sessions")
            
        except Exception as e:
            self.logger.error(f"Failed to update sessions cache: {e}")
    
    async def search_conversations(self, 
                                 query: str,
                                 session_id: Optional[str] = None,
                                 days: Optional[int] = None,
                                 limit: int = 50) -> List[Dict[str, Any]]:
        """
        会話内容検索
        
        Args:
            query: 検索クエリ
            session_id: 特定セッションに限定（オプション）
            days: 検索期間（日数、オプション）
            limit: 検索結果制限
            
        Returns:
            List[Dict]: 検索結果
        """
        try:
            cutoff_date = None
            if days:
                cutoff_date = datetime.now() - timedelta(days=days)
            
            # データベース検索
            exchanges = await asyncio.to_thread(
                self.exchange_repo.search_exchanges,
                query,
                session_id,
                cutoff_date,
                limit
            )
            
            results = []
            for exchange in exchanges:
                # 該当箇所のハイライト
                user_input = exchange.user_input
                agent_response = exchange.agent_response
                
                if query.lower() in user_input.lower():
                    highlighted_text = user_input
                    match_in = "user_input"
                else:
                    highlighted_text = agent_response
                    match_in = "agent_response"
                
                results.append({
                    "session_id": exchange.session_id,
                    "exchange_order": exchange.exchange_order,
                    "timestamp": exchange.timestamp.isoformat(),
                    "user_input": user_input,
                    "agent_response": agent_response,
                    "match_in": match_in,
                    "highlighted_text": highlighted_text,
                    "response_time_ms": exchange.response_time_ms
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Conversation search failed: {e}")
            return []
    
    async def get_conversation_analytics(self, days: int = 30) -> ConversationAnalytics:
        """
        会話分析データ取得
        
        Args:
            days: 分析期間（日数）
            
        Returns:
            ConversationAnalytics: 分析結果
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # セッション統計
            sessions = await asyncio.to_thread(
                self.session_repo.get_sessions_since, cutoff_date
            )
            
            total_sessions = len(sessions)
            active_sessions = sum(1 for s in sessions if s.ended_at is None)
            
            # 平均セッション時間計算
            completed_sessions = [s for s in sessions if s.ended_at]
            avg_duration = 0.0
            if completed_sessions:
                total_minutes = sum(
                    (s.ended_at - s.started_at).total_seconds() / 60
                    for s in completed_sessions
                )
                avg_duration = total_minutes / len(completed_sessions)
            
            # 交換統計
            total_exchanges = await asyncio.to_thread(
                self.exchange_repo.count_exchanges_since, cutoff_date
            )
            
            # 日別活動統計
            daily_activity = await self._calculate_daily_activity(cutoff_date)
            
            # トピック抽出（簡単な実装）
            top_topics = await self._extract_topics(cutoff_date)
            
            # ユーザー関与度（簡単な実装）
            user_engagement = await self._calculate_user_engagement(sessions)
            
            return ConversationAnalytics(
                total_sessions=total_sessions,
                active_sessions=active_sessions,
                total_exchanges=total_exchanges,
                average_session_duration=avg_duration,
                top_topics=top_topics,
                daily_activity=daily_activity,
                user_engagement=user_engagement
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation analytics: {e}")
            return ConversationAnalytics(
                total_sessions=0,
                active_sessions=0,
                total_exchanges=0,
                average_session_duration=0.0,
                top_topics=[],
                daily_activity={},
                user_engagement={}
            )
    
    async def _calculate_daily_activity(self, cutoff_date: datetime) -> Dict[str, int]:
        """日別活動統計計算"""
        try:
            exchanges = await asyncio.to_thread(
                self.exchange_repo.get_exchanges_since, cutoff_date
            )
            
            daily_counts = {}
            for exchange in exchanges:
                date_key = exchange.timestamp.strftime('%Y-%m-%d')
                daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
            
            return daily_counts
            
        except Exception as e:
            self.logger.error(f"Daily activity calculation failed: {e}")
            return {}
    
    async def _extract_topics(self, cutoff_date: datetime, limit: int = 10) -> List[Tuple[str, int]]:
        """トピック抽出（簡単なキーワード集計）"""
        try:
            exchanges = await asyncio.to_thread(
                self.exchange_repo.get_exchanges_since, cutoff_date
            )
            
            # 簡単なキーワード抽出
            word_counts = {}
            common_words = {"の", "は", "を", "に", "が", "で", "と", "て", "だ", "です", "ます"}
            
            for exchange in exchanges:
                # ユーザー入力からキーワード抽出
                words = exchange.user_input.split()
                for word in words:
                    word = word.strip('。、！？')
                    if len(word) > 1 and word not in common_words:
                        word_counts[word] = word_counts.get(word, 0) + 1
            
            # 頻度順にソート
            sorted_topics = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_topics[:limit]
            
        except Exception as e:
            self.logger.error(f"Topic extraction failed: {e}")
            return []
    
    async def _calculate_user_engagement(self, sessions: List[ConversationSession]) -> Dict[str, float]:
        """ユーザー関与度計算"""
        try:
            user_stats = {}
            
            for session in sessions:
                user = session.user_name or "匿名ユーザー"
                if user not in user_stats:
                    user_stats[user] = {
                        "sessions": 0,
                        "total_exchanges": 0,
                        "total_duration": 0.0
                    }
                
                user_stats[user]["sessions"] += 1
                user_stats[user]["total_exchanges"] += session.total_exchanges
                
                if session.ended_at:
                    duration = (session.ended_at - session.started_at).total_seconds() / 60
                    user_stats[user]["total_duration"] += duration
            
            # 関与度スコア計算（セッション数 × 平均交換数）
            engagement_scores = {}
            for user, stats in user_stats.items():
                avg_exchanges = stats["total_exchanges"] / stats["sessions"] if stats["sessions"] > 0 else 0
                engagement_scores[user] = stats["sessions"] * avg_exchanges
            
            return engagement_scores
            
        except Exception as e:
            self.logger.error(f"User engagement calculation failed: {e}")
            return {}
    
    async def export_conversations(self, 
                                 session_ids: List[str], 
                                 format: str = "json") -> Optional[str]:
        """
        会話履歴エクスポート
        
        Args:
            session_ids: エクスポート対象セッションIDリスト
            format: エクスポート形式（json/csv/txt）
            
        Returns:
            Optional[str]: エクスポートデータ（文字列形式）
        """
        try:
            export_data = {}
            
            for session_id in session_ids:
                # セッション情報取得
                session = await asyncio.to_thread(
                    self.session_repo.get_session, session_id
                )
                
                if not session:
                    continue
                
                # 交換履歴取得
                exchanges = await asyncio.to_thread(
                    self.exchange_repo.get_session_exchanges, session_id
                )
                
                export_data[session_id] = {
                    "session_info": {
                        "session_id": session.session_id,
                        "user_name": session.user_name,
                        "started_at": session.started_at.isoformat(),
                        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                        "total_exchanges": session.total_exchanges
                    },
                    "exchanges": [
                        {
                            "order": ex.exchange_order,
                            "timestamp": ex.timestamp.isoformat(),
                            "user_input": ex.user_input,
                            "agent_response": ex.agent_response,
                            "response_time_ms": ex.response_time_ms,
                            "wake_word_confidence": ex.wake_word_confidence
                        }
                        for ex in exchanges
                    ]
                }
            
            # フォーマット変換
            if format.lower() == "json":
                import json
                return json.dumps(export_data, ensure_ascii=False, indent=2)
            elif format.lower() == "csv":
                return self._convert_to_csv(export_data)
            elif format.lower() == "txt":
                return self._convert_to_txt(export_data)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
        except Exception as e:
            self.logger.error(f"Conversation export failed: {e}")
            return None
    
    def _convert_to_csv(self, data: Dict) -> str:
        """CSV形式に変換"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー
        writer.writerow([
            "session_id", "user_name", "exchange_order", "timestamp",
            "user_input", "agent_response", "response_time_ms"
        ])
        
        # データ
        for session_id, session_data in data.items():
            session_info = session_data["session_info"]
            for exchange in session_data["exchanges"]:
                writer.writerow([
                    session_id,
                    session_info["user_name"],
                    exchange["order"],
                    exchange["timestamp"],
                    exchange["user_input"],
                    exchange["agent_response"],
                    exchange["response_time_ms"]
                ])
        
        return output.getvalue()
    
    def _convert_to_txt(self, data: Dict) -> str:
        """テキスト形式に変換"""
        output = []
        
        for session_id, session_data in data.items():
            session_info = session_data["session_info"]
            
            output.append(f"=== セッション: {session_id} ===")
            output.append(f"ユーザー: {session_info['user_name']}")
            output.append(f"開始時刻: {session_info['started_at']}")
            output.append(f"総交換数: {session_info['total_exchanges']}")
            output.append("")
            
            for exchange in session_data["exchanges"]:
                output.append(f"[{exchange['timestamp']}]")
                output.append(f"ユーザー: {exchange['user_input']}")
                output.append(f"Yes-Man: {exchange['agent_response']}")
                output.append(f"応答時間: {exchange['response_time_ms']}ms")
                output.append("")
            
            output.append("-" * 50)
        
        return "\n".join(output)
    
    async def cleanup_old_conversations(self, retention_days: int = 90) -> Dict[str, int]:
        """
        古い会話履歴のクリーンアップ
        
        Args:
            retention_days: 保持期間（日数）
            
        Returns:
            Dict[str, int]: クリーンアップ統計
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # 古いセッションを取得
            old_sessions = await asyncio.to_thread(
                self.session_repo.get_sessions_before, cutoff_date
            )
            
            deleted_sessions = 0
            deleted_exchanges = 0
            
            for session in old_sessions:
                # 交換履歴削除
                exchanges = await asyncio.to_thread(
                    self.exchange_repo.get_session_exchanges, session.session_id
                )
                
                for exchange in exchanges:
                    await asyncio.to_thread(
                        self.exchange_repo.delete_exchange, exchange.id
                    )
                    deleted_exchanges += 1
                
                # セッション削除
                await asyncio.to_thread(
                    self.session_repo.delete_session, session.session_id
                )
                deleted_sessions += 1
            
            # キャッシュクリア
            self._recent_sessions_cache.clear()
            self._last_cache_update = datetime.now() - self._cache_expiry
            
            cleanup_stats = {
                "deleted_sessions": deleted_sessions,
                "deleted_exchanges": deleted_exchanges,
                "retention_days": retention_days,
                "cutoff_date": cutoff_date.isoformat()
            }
            
            self.logger.info(f"Conversation cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            self.logger.error(f"Conversation cleanup failed: {e}")
            return {"error": str(e)}


async def create_conversation_manager(db_path: str = "yes_man.db") -> ConversationManager:
    """
    会話履歴管理作成ヘルパー
    
    Args:
        db_path: データベースファイルパス
        
    Returns:
        ConversationManager: 会話履歴管理
    """
    manager = ConversationManager(db_path)
    return manager