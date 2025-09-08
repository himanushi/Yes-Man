"""
エージェント実行管理

憲法III: テストファーストに従い、contract テストを先に実装済み
LangFlowエージェントの実行状態管理とセッション追跡
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from .langflow_client import LangFlowClient, FlowExecutionRequest, FlowExecutionResult
from .database.models.conversation_session import ConversationSession, ConversationSessionRepository
from .database.models.conversation_exchange import ConversationExchange, ConversationExchangeRepository


class ExecutionStatus(Enum):
    """エージェント実行状態"""
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_USER = "waiting_user"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class AgentContext:
    """エージェント実行コンテキスト"""
    session_id: str
    user_name: Optional[str] = None
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    current_flow_id: str = "yes_man_agent"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionRequest:
    """エージェント実行リクエスト"""
    user_input: str
    session_id: str
    flow_id: Optional[str] = None
    wake_word_confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResponse:
    """エージェント実行レスポンス"""
    success: bool
    agent_response: str
    session_id: str
    execution_time_ms: int
    flow_id: str
    error_message: Optional[str] = None
    requires_tts: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentExecutor:
    """
    LangFlowエージェント実行管理クラス
    
    憲法IV: プライバシーファースト - 会話データは適切に管理
    憲法V: パフォーマンス制約対応 - 応答時間監視
    """
    
    def __init__(self, 
                 langflow_client: LangFlowClient,
                 db_path: str = "yes_man.db"):
        self.client = langflow_client
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # 活動中セッション管理
        self._active_sessions: Dict[str, AgentContext] = {}
        self._execution_status = ExecutionStatus.IDLE
        self._current_session_id: Optional[str] = None
        
        # データベースリポジトリ
        self.session_repo = ConversationSessionRepository(db_path)
        self.exchange_repo = ConversationExchangeRepository(db_path)
        
        # コールバック
        self._response_callbacks: List[Callable[[ExecutionResponse], None]] = []
        
        # パフォーマンス監視
        self._total_executions = 0
        self._successful_executions = 0
    
    def add_response_callback(self, callback: Callable[[ExecutionResponse], None]) -> None:
        """レスポンスコールバック追加"""
        self._response_callbacks.append(callback)
    
    def remove_response_callback(self, callback: Callable[[ExecutionResponse], None]) -> None:
        """レスポンスコールバック削除"""
        if callback in self._response_callbacks:
            self._response_callbacks.remove(callback)
    
    async def start_session(self, user_name: Optional[str] = None) -> str:
        """
        新しい会話セッション開始
        
        Args:
            user_name: ユーザー名
            
        Returns:
            str: セッションID
        """
        session_id = str(uuid.uuid4())
        
        # セッションコンテキスト作成
        context = AgentContext(
            session_id=session_id,
            user_name=user_name
        )
        self._active_sessions[session_id] = context
        
        # データベースにセッション記録
        session = ConversationSession(
            session_id=session_id,
            started_at=datetime.now(),
            user_name=user_name,
            session_status="active"
        )
        await asyncio.to_thread(self.session_repo.create_session, session)
        
        self.logger.info(f"New conversation session started: {session_id}")
        return session_id
    
    async def execute_agent(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        エージェント実行
        
        Args:
            request: 実行リクエスト
            
        Returns:
            ExecutionResponse: 実行結果
        """
        start_time = datetime.now()
        self._execution_status = ExecutionStatus.PROCESSING
        
        try:
            # セッション確認・作成
            if request.session_id not in self._active_sessions:
                await self.start_session()
                request.session_id = list(self._active_sessions.keys())[-1]
            
            context = self._active_sessions[request.session_id]
            self._current_session_id = request.session_id
            
            # LangFlow実行リクエスト構築
            flow_request = FlowExecutionRequest(
                flow_id=request.flow_id or context.current_flow_id,
                input_data={
                    "message": request.user_input,
                    "user_name": context.user_name,
                    "conversation_history": context.conversation_history,
                    **request.metadata
                },
                session_id=request.session_id
            )
            
            # LangFlowエージェント実行
            flow_result = await self.client.execute_flow(flow_request)
            
            # 実行時間計算
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if flow_result.success:
                # 成功レスポンス処理
                response = ExecutionResponse(
                    success=True,
                    agent_response=flow_result.response_text,
                    session_id=request.session_id,
                    execution_time_ms=execution_time_ms,
                    flow_id=flow_request.flow_id,
                    metadata=flow_result.metadata or {}
                )
                
                # 会話履歴更新
                await self._update_conversation_history(
                    context, request, response, request.wake_word_confidence
                )
                
                self._successful_executions += 1
                
            else:
                # エラーレスポンス処理
                response = ExecutionResponse(
                    success=False,
                    agent_response="申し訳ありません、処理中にエラーが発生しました。もう一度お試しください。",
                    session_id=request.session_id,
                    execution_time_ms=execution_time_ms,
                    flow_id=flow_request.flow_id,
                    error_message=flow_result.error_message
                )
            
            # 統計更新
            self._total_executions += 1
            
            # パフォーマンス警告
            if execution_time_ms > 3000:
                self.logger.warning(
                    f"Agent execution exceeded 3s constraint: {execution_time_ms}ms"
                )
            
            # コールバック実行
            for callback in self._response_callbacks:
                try:
                    callback(response)
                except Exception as e:
                    self.logger.error(f"Response callback failed: {e}")
            
            self._execution_status = ExecutionStatus.COMPLETED
            return response
            
        except Exception as e:
            # 予期しないエラー処理
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"Agent execution failed: {e}")
            
            response = ExecutionResponse(
                success=False,
                agent_response="システムエラーが発生しました。",
                session_id=request.session_id,
                execution_time_ms=execution_time_ms,
                flow_id=request.flow_id or "unknown",
                error_message=str(e)
            )
            
            self._total_executions += 1
            self._execution_status = ExecutionStatus.ERROR
            
            return response
        
        finally:
            if self._current_session_id == request.session_id:
                self._current_session_id = None
    
    async def _update_conversation_history(self, 
                                         context: AgentContext,
                                         request: ExecutionRequest,
                                         response: ExecutionResponse,
                                         wake_word_confidence: Optional[float]) -> None:
        """会話履歴更新"""
        try:
            # メモリ内履歴更新
            context.conversation_history.append({
                "role": "user",
                "content": request.user_input,
                "timestamp": datetime.now().isoformat()
            })
            context.conversation_history.append({
                "role": "assistant",
                "content": response.agent_response,
                "timestamp": datetime.now().isoformat()
            })
            
            # 履歴長制限（最新20件）
            if len(context.conversation_history) > 20:
                context.conversation_history = context.conversation_history[-20:]
            
            # データベース記録
            exchange = ConversationExchange(
                session_id=request.session_id,
                exchange_order=len(context.conversation_history) // 2,
                user_input=request.user_input,
                agent_response=response.agent_response,
                response_time_ms=response.execution_time_ms,
                wake_word_confidence=wake_word_confidence,
                langflow_flow_id=response.flow_id
            )
            
            await asyncio.to_thread(self.exchange_repo.create_exchange, exchange)
            
            # セッション統計更新
            await asyncio.to_thread(
                self.session_repo.update_session_stats,
                request.session_id,
                len(context.conversation_history) // 2
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update conversation history: {e}")
    
    async def end_session(self, session_id: str) -> bool:
        """
        会話セッション終了
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: 終了成功
        """
        try:
            if session_id in self._active_sessions:
                # セッション終了記録
                await asyncio.to_thread(
                    self.session_repo.end_session, 
                    session_id
                )
                
                # メモリから削除
                del self._active_sessions[session_id]
                
                if self._current_session_id == session_id:
                    self._current_session_id = None
                    self._execution_status = ExecutionStatus.IDLE
                
                self.logger.info(f"Session ended: {session_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to end session {session_id}: {e}")
            return False
    
    def get_execution_status(self) -> ExecutionStatus:
        """現在の実行状態取得"""
        return self._execution_status
    
    def get_active_session_id(self) -> Optional[str]:
        """アクティブセッションID取得"""
        return self._current_session_id
    
    def get_session_context(self, session_id: str) -> Optional[AgentContext]:
        """セッションコンテキスト取得"""
        return self._active_sessions.get(session_id)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計取得"""
        success_rate = 0.0
        if self._total_executions > 0:
            success_rate = self._successful_executions / self._total_executions
        
        return {
            "total_executions": self._total_executions,
            "successful_executions": self._successful_executions,
            "success_rate": round(success_rate, 3),
            "active_sessions": len(self._active_sessions),
            "current_status": self._execution_status.value,
            "langflow_stats": self.client.get_performance_stats()
        }
    
    async def cleanup(self) -> None:
        """リソースクリーンアップ"""
        # 全セッション終了
        for session_id in list(self._active_sessions.keys()):
            await self.end_session(session_id)
        
        self._execution_status = ExecutionStatus.IDLE
        self._current_session_id = None
        self._response_callbacks.clear()
        
        self.logger.info("Agent executor resources cleaned up")


async def create_agent_executor(langflow_client: LangFlowClient, 
                              db_path: str = "yes_man.db") -> AgentExecutor:
    """
    エージェント実行管理作成ヘルパー
    
    Args:
        langflow_client: LangFlowクライアント
        db_path: データベースファイルパス
        
    Returns:
        AgentExecutor: エージェント実行管理
    """
    executor = AgentExecutor(langflow_client, db_path)
    return executor