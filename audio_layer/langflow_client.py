"""
LangFlowクライアント

憲法III: テストファーストに従い、contract テストを先に実装済み
LangFlowサーバーとのHTTP通信でエージェント実行を管理
"""

import requests
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
from datetime import datetime


@dataclass
class LangFlowConfig:
    """LangFlow設定"""
    base_url: str = "http://localhost:7860"
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    default_flow_id: str = "yes_man_agent"


@dataclass
class FlowExecutionRequest:
    """フロー実行リクエスト"""
    flow_id: str
    input_data: Dict[str, Any]
    stream: bool = False
    session_id: Optional[str] = None


@dataclass
class FlowExecutionResult:
    """フロー実行結果"""
    success: bool
    response_text: str
    execution_time_ms: int
    flow_id: str
    session_id: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LangFlowClient:
    """
    LangFlowサーバーとの通信クライアント
    
    憲法II: シンプルなHTTP API統合
    憲法V: パフォーマンス監視と制約遵守
    """
    
    def __init__(self, config: Optional[LangFlowConfig] = None):
        self.config = config or LangFlowConfig()
        self.logger = logging.getLogger(__name__)
        self._session: Optional[aiohttp.ClientSession] = None
        
        # パフォーマンスメトリクス
        self._total_requests: int = 0
        self._successful_requests: int = 0
        self._average_response_time_ms: float = 0.0
        self._last_response_time_ms: Optional[int] = None
    
    async def initialize(self) -> bool:
        """
        LangFlowクライアント初期化
        
        Returns:
            bool: 初期化成功
        """
        try:
            # aiohttp セッション作成
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
            
            # LangFlowサーバー接続確認
            health_check = await self._health_check()
            if health_check:
                self.logger.info("LangFlow client initialized successfully")
                return True
            else:
                self.logger.error("LangFlow server health check failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize LangFlow client: {e}")
            return False
    
    async def _health_check(self) -> bool:
        """LangFlowサーバー健康状態チェック"""
        try:
            if not self._session:
                return False
            
            url = f"{self.config.base_url}/health"
            async with self._session.get(url) as response:
                return response.status == 200
                
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False
    
    async def execute_flow(self, request: FlowExecutionRequest) -> FlowExecutionResult:
        """
        LangFlowフロー実行
        
        Args:
            request: フロー実行リクエスト
            
        Returns:
            FlowExecutionResult: 実行結果
        """
        if not self._session:
            raise RuntimeError("LangFlow client not initialized")
        
        start_time = datetime.now()
        
        for attempt in range(self.config.max_retries):
            try:
                result = await self._execute_flow_request(request)
                
                # パフォーマンス更新
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                self._update_performance_metrics(execution_time, success=result.success)
                result.execution_time_ms = execution_time
                
                return result
                
            except Exception as e:
                self.logger.warning(f"Flow execution attempt {attempt + 1} failed: {e}")
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    # 最終リトライ失敗
                    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                    self._update_performance_metrics(execution_time, success=False)
                    
                    return FlowExecutionResult(
                        success=False,
                        response_text="",
                        execution_time_ms=execution_time,
                        flow_id=request.flow_id,
                        session_id=request.session_id,
                        error_message=f"All {self.config.max_retries} attempts failed: {e}"
                    )
    
    async def _execute_flow_request(self, request: FlowExecutionRequest) -> FlowExecutionResult:
        """フロー実行のHTTPリクエスト実行"""
        url = f"{self.config.base_url}/api/v1/run/{request.flow_id}"
        
        payload = {
            "input_value": request.input_data.get("message", ""),
            "stream": request.stream,
            "tweaks": {},
        }
        
        if request.session_id:
            payload["session_id"] = request.session_id
        
        self.logger.debug(f"Executing flow {request.flow_id} with payload: {payload}")
        
        async with self._session.post(url, json=payload) as response:
            response_data = await response.json()
            
            if response.status == 200:
                # 成功レスポンス処理
                output_text = self._extract_output_text(response_data)
                
                return FlowExecutionResult(
                    success=True,
                    response_text=output_text,
                    execution_time_ms=0,  # 後で更新
                    flow_id=request.flow_id,
                    session_id=request.session_id,
                    metadata=response_data
                )
            else:
                # エラーレスポンス処理
                error_msg = response_data.get("error", f"HTTP {response.status}")
                
                return FlowExecutionResult(
                    success=False,
                    response_text="",
                    execution_time_ms=0,  # 後で更新
                    flow_id=request.flow_id,
                    session_id=request.session_id,
                    error_message=error_msg
                )
    
    def _extract_output_text(self, response_data: Dict[str, Any]) -> str:
        """LangFlowレスポンスからテキスト出力を抽出"""
        try:
            # LangFlow API レスポンス形式に応じて調整
            outputs = response_data.get("outputs", [])
            if outputs:
                # 最初の出力の結果を取得
                first_output = outputs[0]
                if isinstance(first_output, dict):
                    # 'results' フィールドから text を抽出
                    results = first_output.get("results", {})
                    if isinstance(results, dict) and "message" in results:
                        message = results["message"]
                        if isinstance(message, dict) and "text" in message:
                            return message["text"]
                        elif isinstance(message, str):
                            return message
                    
                    # 直接 text フィールドを確認
                    if "text" in first_output:
                        return first_output["text"]
                        
                elif isinstance(first_output, str):
                    return first_output
            
            # フォールバック: レスポンス全体から推定
            if "message" in response_data:
                return str(response_data["message"])
            
            return "レスポンス解析エラー"
            
        except Exception as e:
            self.logger.error(f"Failed to extract output text: {e}")
            return f"テキスト抽出エラー: {e}"
    
    async def list_flows(self) -> List[Dict[str, Any]]:
        """利用可能なフローリスト取得"""
        try:
            if not self._session:
                raise RuntimeError("Client not initialized")
            
            url = f"{self.config.base_url}/api/v1/flows"
            async with self._session.get(url) as response:
                if response.status == 200:
                    flows = await response.json()
                    return flows if isinstance(flows, list) else []
                else:
                    self.logger.error(f"Failed to list flows: HTTP {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Failed to list flows: {e}")
            return []
    
    async def check_flow_exists(self, flow_id: str) -> bool:
        """指定フローの存在確認"""
        try:
            flows = await self.list_flows()
            return any(flow.get("id") == flow_id for flow in flows)
        except Exception:
            return False
    
    def _update_performance_metrics(self, response_time_ms: int, success: bool) -> None:
        """パフォーマンスメトリクス更新"""
        self._total_requests += 1
        self._last_response_time_ms = response_time_ms
        
        if success:
            self._successful_requests += 1
        
        # 移動平均更新
        if self._average_response_time_ms == 0:
            self._average_response_time_ms = response_time_ms
        else:
            alpha = 0.1
            self._average_response_time_ms = (
                alpha * response_time_ms + 
                (1 - alpha) * self._average_response_time_ms
            )
        
        # パフォーマンス警告
        if response_time_ms > 3000:  # 3秒超過
            self.logger.warning(
                f"LangFlow response exceeded 3s constraint: {response_time_ms}ms"
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計取得"""
        success_rate = 0.0
        if self._total_requests > 0:
            success_rate = self._successful_requests / self._total_requests
        
        return {
            "total_requests": self._total_requests,
            "successful_requests": self._successful_requests,
            "success_rate": round(success_rate, 3),
            "average_response_time_ms": round(self._average_response_time_ms, 2),
            "last_response_time_ms": self._last_response_time_ms,
            "meets_constraint": self._average_response_time_ms < 3000  # 憲法V: <3秒
        }
    
    async def cleanup(self) -> None:
        """リソースクリーンアップ"""
        if self._session:
            await self._session.close()
            self._session = None
        
        self.logger.info("LangFlow client resources cleaned up")


async def create_langflow_client(base_url: str = "http://localhost:7860") -> LangFlowClient:
    """
    LangFlowクライアント作成ヘルパー
    
    Args:
        base_url: LangFlowサーバーURL
        
    Returns:
        LangFlowClient: 初期化済みクライアント
    """
    config = LangFlowConfig(base_url=base_url)
    client = LangFlowClient(config)
    
    if await client.initialize():
        return client
    else:
        await client.cleanup()
        raise RuntimeError("Failed to create LangFlow client")


# 同期版ラッパー（後方互換性用）
def create_sync_langflow_client(base_url: str = "http://localhost:7860") -> LangFlowClient:
    """同期版クライアント作成（非推奨）"""
    import asyncio
    
    async def _create():
        return await create_langflow_client(base_url)
    
    return asyncio.run(_create())