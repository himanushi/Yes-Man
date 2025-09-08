"""
ツール管理システム

憲法III: テストファーストに従い、contract テストを先に実装済み
LangFlowツール設定とプラグイン管理
"""

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import importlib
import inspect

from .database.models.tool_configuration import ToolConfiguration, ToolConfigurationRepository


class ToolStatus(Enum):
    """ツール状態"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    LOADING = "loading"


@dataclass
class ToolDefinition:
    """ツール定義"""
    name: str
    description: str
    function: Callable
    parameters: Dict[str, Any]
    category: str = "general"
    version: str = "1.0.0"
    author: str = "Yes-Man"
    enabled: bool = True
    priority: int = 0


@dataclass
class ToolExecutionResult:
    """ツール実行結果"""
    success: bool
    result: Any
    execution_time_ms: int
    tool_name: str
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolManager:
    """
    LangFlowツール管理システム
    
    憲法II: シンプルなプラグインアーキテクチャ
    憲法V: パフォーマンス監視付きツール実行
    """
    
    def __init__(self, db_path: str = "yes_man.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.repo = ToolConfigurationRepository(db_path)
        
        # 登録済みツール
        self._tools: Dict[str, ToolDefinition] = {}
        self._tool_status: Dict[str, ToolStatus] = {}
        
        # 実行統計
        self._execution_stats: Dict[str, Dict[str, int]] = {}
        
        # 組み込みツール登録
        self._register_builtin_tools()
    
    def _register_builtin_tools(self) -> None:
        """組み込みツール登録"""
        # 計算機ツール
        def calculator(expression: str) -> str:
            """数式計算ツール"""
            try:
                # セキュリティ: eval使用を制限
                allowed_chars = set('0123456789+-*/()., ')
                if not all(c in allowed_chars for c in expression):
                    return "エラー: 許可されない文字が含まれています"
                
                result = eval(expression)
                return f"計算結果: {result}"
                
            except Exception as e:
                return f"計算エラー: {e}"
        
        # タイマーツール
        def timer(seconds: int) -> str:
            """タイマーツール"""
            if seconds <= 0 or seconds > 3600:
                return "エラー: 1〜3600秒の範囲で指定してください"
            
            return f"{seconds}秒のタイマーを設定しました"
        
        # 時刻確認ツール
        def current_time() -> str:
            """現在時刻取得ツール"""
            now = datetime.now()
            return f"現在の時刻: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # システム情報ツール
        def system_info() -> str:
            """システム情報ツール"""
            return "Yes-Man音声アシスタント v1.0 - 動作中"
        
        # 組み込みツール定義
        builtin_tools = [
            ToolDefinition(
                name="calculator",
                description="数式計算（四則演算）",
                function=calculator,
                parameters={"expression": {"type": "string", "description": "計算式"}},
                category="utility",
                priority=10
            ),
            ToolDefinition(
                name="timer",
                description="指定秒数のタイマー",
                function=timer,
                parameters={"seconds": {"type": "integer", "description": "秒数"}},
                category="utility", 
                priority=9
            ),
            ToolDefinition(
                name="current_time",
                description="現在時刻の確認",
                function=current_time,
                parameters={},
                category="system",
                priority=8
            ),
            ToolDefinition(
                name="system_info",
                description="システム情報表示",
                function=system_info,
                parameters={},
                category="system",
                priority=7
            )
        ]
        
        for tool in builtin_tools:
            self._tools[tool.name] = tool
            self._tool_status[tool.name] = ToolStatus.ENABLED
            self._execution_stats[tool.name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0
            }
    
    async def initialize(self) -> bool:
        """
        ツール管理システム初期化
        
        Returns:
            bool: 初期化成功
        """
        try:
            # データベースからツール設定ロード
            await self._load_tool_configurations()
            
            # 外部ツールプラグイン検索・ロード
            await self._load_external_tools()
            
            self.logger.info(f"Tool manager initialized with {len(self._tools)} tools")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize tool manager: {e}")
            return False
    
    async def _load_tool_configurations(self) -> None:
        """データベースからツール設定ロード"""
        try:
            configs = await asyncio.to_thread(self.repo.get_enabled_tools)
            
            for config in configs:
                tool_name = config.tool_name
                if tool_name in self._tools:
                    tool_def = self._tools[tool_name]
                    
                    # 設定から有効/無効状態更新
                    tool_def.enabled = config.is_enabled
                    tool_def.priority = config.priority_order
                    
                    # JSON設定があれば適用
                    if config.config_json:
                        custom_config = json.loads(config.config_json)
                        if "parameters" in custom_config:
                            tool_def.parameters.update(custom_config["parameters"])
                    
                    # ツール状態更新
                    self._tool_status[tool_name] = (
                        ToolStatus.ENABLED if config.is_enabled 
                        else ToolStatus.DISABLED
                    )
                    
                    self.logger.debug(f"Loaded configuration for tool: {tool_name}")
                    
        except Exception as e:
            self.logger.warning(f"Failed to load tool configurations: {e}")
    
    async def _load_external_tools(self) -> None:
        """外部ツールプラグインロード"""
        # 将来の拡張用: langflow_flows/tools/ からプラグイン読み込み
        try:
            # TODO: プラグインディレクトリから .py ファイルを動的ロード
            self.logger.info("External tool loading not implemented yet")
            
        except Exception as e:
            self.logger.warning(f"External tool loading failed: {e}")
    
    def register_tool(self, tool: ToolDefinition) -> bool:
        """
        ツール登録
        
        Args:
            tool: ツール定義
            
        Returns:
            bool: 登録成功
        """
        try:
            # 関数シグネチャ検証
            if not callable(tool.function):
                raise ValueError("Tool function must be callable")
            
            # 重複チェック
            if tool.name in self._tools:
                self.logger.warning(f"Tool {tool.name} already exists, overriding")
            
            # ツール登録
            self._tools[tool.name] = tool
            self._tool_status[tool.name] = ToolStatus.ENABLED if tool.enabled else ToolStatus.DISABLED
            self._execution_stats[tool.name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0
            }
            
            # データベースに設定保存
            asyncio.create_task(self._save_tool_configuration(tool))
            
            self.logger.info(f"Tool registered: {tool.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register tool {tool.name}: {e}")
            return False
    
    async def _save_tool_configuration(self, tool: ToolDefinition) -> None:
        """ツール設定をデータベースに保存"""
        try:
            config = ToolConfiguration(
                tool_name=tool.name,
                is_enabled=tool.enabled,
                priority_order=tool.priority,
                config_json=json.dumps({
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "category": tool.category,
                    "version": tool.version,
                    "author": tool.author
                }),
                description=tool.description
            )
            
            await asyncio.to_thread(self.repo.save_or_update_tool, config)
            
        except Exception as e:
            self.logger.error(f"Failed to save tool configuration: {e}")
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolExecutionResult:
        """
        ツール実行
        
        Args:
            tool_name: ツール名
            **kwargs: ツールパラメータ
            
        Returns:
            ToolExecutionResult: 実行結果
        """
        start_time = datetime.now()
        
        try:
            # ツール存在確認
            if tool_name not in self._tools:
                return ToolExecutionResult(
                    success=False,
                    result=None,
                    execution_time_ms=0,
                    tool_name=tool_name,
                    error_message=f"Tool '{tool_name}' not found"
                )
            
            tool = self._tools[tool_name]
            
            # 有効性確認
            if self._tool_status[tool_name] != ToolStatus.ENABLED:
                return ToolExecutionResult(
                    success=False,
                    result=None,
                    execution_time_ms=0,
                    tool_name=tool_name,
                    error_message=f"Tool '{tool_name}' is disabled"
                )
            
            # パラメータ検証
            if not self._validate_parameters(tool, kwargs):
                return ToolExecutionResult(
                    success=False,
                    result=None,
                    execution_time_ms=0,
                    tool_name=tool_name,
                    error_message="Invalid parameters"
                )
            
            # ツール実行
            self._tool_status[tool_name] = ToolStatus.LOADING
            
            if asyncio.iscoroutinefunction(tool.function):
                result = await tool.function(**kwargs)
            else:
                result = await asyncio.to_thread(tool.function, **kwargs)
            
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 統計更新
            self._execution_stats[tool_name]["total_calls"] += 1
            self._execution_stats[tool_name]["successful_calls"] += 1
            
            # データベース使用回数更新
            await asyncio.to_thread(self.repo.increment_usage_count, tool_name)
            
            self._tool_status[tool_name] = ToolStatus.ENABLED
            
            return ToolExecutionResult(
                success=True,
                result=result,
                execution_time_ms=execution_time_ms,
                tool_name=tool_name
            )
            
        except Exception as e:
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # エラー統計更新
            if tool_name in self._execution_stats:
                self._execution_stats[tool_name]["total_calls"] += 1
                self._execution_stats[tool_name]["failed_calls"] += 1
            
            if tool_name in self._tool_status:
                self._tool_status[tool_name] = ToolStatus.ERROR
            
            self.logger.error(f"Tool execution failed {tool_name}: {e}")
            
            return ToolExecutionResult(
                success=False,
                result=None,
                execution_time_ms=execution_time_ms,
                tool_name=tool_name,
                error_message=str(e)
            )
    
    def _validate_parameters(self, tool: ToolDefinition, params: Dict[str, Any]) -> bool:
        """ツールパラメータ検証"""
        try:
            # 必要なパラメータが全て提供されているかチェック
            required_params = set(tool.parameters.keys())
            provided_params = set(params.keys())
            
            missing_params = required_params - provided_params
            if missing_params:
                self.logger.warning(f"Missing required parameters: {missing_params}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Parameter validation failed: {e}")
            return False
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """利用可能なツールリスト取得"""
        tools = []
        
        for name, tool in self._tools.items():
            status = self._tool_status.get(name, ToolStatus.DISABLED)
            stats = self._execution_stats.get(name, {})
            
            tools.append({
                "name": name,
                "description": tool.description,
                "category": tool.category,
                "version": tool.version,
                "author": tool.author,
                "enabled": status == ToolStatus.ENABLED,
                "status": status.value,
                "priority": tool.priority,
                "parameters": tool.parameters,
                "usage_stats": stats
            })
        
        # 優先度順にソート
        tools.sort(key=lambda x: x["priority"], reverse=True)
        return tools
    
    def get_enabled_tools(self) -> List[Dict[str, Any]]:
        """有効なツールのみ取得"""
        return [
            tool for tool in self.get_available_tools()
            if tool["enabled"]
        ]
    
    async def enable_tool(self, tool_name: str) -> bool:
        """ツール有効化"""
        try:
            if tool_name not in self._tools:
                return False
            
            self._tools[tool_name].enabled = True
            self._tool_status[tool_name] = ToolStatus.ENABLED
            
            await asyncio.to_thread(self.repo.enable_tool, tool_name)
            
            self.logger.info(f"Tool enabled: {tool_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enable tool {tool_name}: {e}")
            return False
    
    async def disable_tool(self, tool_name: str) -> bool:
        """ツール無効化"""
        try:
            if tool_name not in self._tools:
                return False
            
            self._tools[tool_name].enabled = False
            self._tool_status[tool_name] = ToolStatus.DISABLED
            
            await asyncio.to_thread(self.repo.disable_tool, tool_name)
            
            self.logger.info(f"Tool disabled: {tool_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disable tool {tool_name}: {e}")
            return False
    
    def get_tool_stats(self) -> Dict[str, Any]:
        """ツール統計情報取得"""
        total_tools = len(self._tools)
        enabled_tools = sum(1 for status in self._tool_status.values() 
                          if status == ToolStatus.ENABLED)
        
        total_executions = sum(stats["total_calls"] for stats in self._execution_stats.values())
        successful_executions = sum(stats["successful_calls"] for stats in self._execution_stats.values())
        
        return {
            "total_tools": total_tools,
            "enabled_tools": enabled_tools,
            "disabled_tools": total_tools - enabled_tools,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "execution_stats": self._execution_stats
        }


async def create_tool_manager(db_path: str = "yes_man.db") -> ToolManager:
    """
    ツール管理システム作成ヘルパー
    
    Args:
        db_path: データベースファイルパス
        
    Returns:
        ToolManager: 初期化済みツール管理システム
    """
    manager = ToolManager(db_path)
    
    if await manager.initialize():
        return manager
    else:
        raise RuntimeError("Failed to create tool manager")