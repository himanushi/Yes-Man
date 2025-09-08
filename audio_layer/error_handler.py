"""
Yes-Man エラーハンドリング統合システム
全コンポーネントの統一エラー処理とフォールバック

憲法I: プライバシー保護 - エラーログも個人情報無し
憲法III: パフォーマンス制約 - エラー処理も高速化
憲法VIII: 指示に従う - Yes-Man風エラーメッセージ
"""

import logging
import traceback
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Union
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager, contextmanager

class ErrorSeverity(Enum):
    """エラー重要度"""
    LOW = "low"           # 軽微 - ログのみ
    MEDIUM = "medium"     # 中程度 - フォールバック実行
    HIGH = "high"         # 重大 - コンポーネント再起動
    CRITICAL = "critical" # 致命的 - システム停止

class ErrorCategory(Enum):
    """エラーカテゴリ"""
    AUDIO_INPUT = "audio_input"       # 音声入力関連
    AUDIO_OUTPUT = "audio_output"     # 音声出力関連
    WHISPER = "whisper"               # STT処理関連
    VOICEVOX = "voicevox"            # TTS処理関連
    LANGFLOW = "langflow"             # エージェント処理関連
    IPC = "ipc"                       # UI通信関連
    SYSTEM = "system"                 # システム全体
    NETWORK = "network"               # 外部API通信
    DATABASE = "database"             # データベース操作

@dataclass
class ErrorEvent:
    """エラーイベント情報"""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    component: str
    timestamp: str
    exception_type: Optional[str] = None
    traceback: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    recovery_action: Optional[str] = None
    user_message: Optional[str] = None

class YesManErrorHandler:
    """Yes-Man統合エラーハンドラー"""
    
    def __init__(self):
        self.logger = logging.getLogger("YesManErrorHandler")
        self.error_count: Dict[str, int] = {}
        self.error_callbacks: Dict[ErrorCategory, Callable] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
        self.recovery_strategies: Dict[ErrorCategory, Callable] = {}
        self.max_retry_count = 3
        self.error_threshold = 10  # 同一エラーの上限
        
        # Yes-Man風エラーメッセージテンプレート
        self.yes_man_messages = {
            ErrorCategory.AUDIO_INPUT: [
                "はい、マイクの調子がちょっと悪いようですが、もう一度試してみましょう！",
                "おっと、音声の受信で少し問題が起きましたが、大丈夫です！",
                "はい、音声入力でちょっとしたトラブルがありましたが、きっと解決しますよ！"
            ],
            ErrorCategory.AUDIO_OUTPUT: [
                "はい、スピーカーの調子を確認していますが、少々お待ちください！",
                "音声出力で小さな問題が発生しましたが、すぐに直りますよ！",
                "はい、音の出力でちょっと手間取っていますが、頑張ります！"
            ],
            ErrorCategory.WHISPER: [
                "はい、音声認識でちょっとした計算をしていますが、もう少しお待ちください！",
                "音声の解析で少し時間がかかっていますが、必ず理解しますよ！",
                "はい、お話の内容を一生懸命理解しようとしていますので、少々お待ちを！"
            ],
            ErrorCategory.VOICEVOX: [
                "はい、声の準備でちょっと時間がかかっていますが、もうすぐですよ！",
                "音声合成の調整をしていますが、きっと良い声で話せます！",
                "はい、話す準備をしているところですが、少々お待ちください！"
            ],
            ErrorCategory.LANGFLOW: [
                "はい、回答を考えるのに少し時間がかかっていますが、必ず良いお答えをしますよ！",
                "思考回路でちょっとした整理をしていますが、もうすぐ準備完了です！",
                "はい、最適な回答を準備していますので、もう少しだけお待ちください！"
            ],
            ErrorCategory.IPC: [
                "はい、画面との連携でちょっとした調整をしていますが、すぐに直りますよ！",
                "システム間の通信で小さな問題がありましたが、必ず解決します！",
                "はい、内部の連携を整えていますので、少々お待ちください！"
            ],
            ErrorCategory.SYSTEM: [
                "はい、システム全体の調子を確認していますが、必ず復旧しますよ！",
                "全体的な調整をしていますが、すぐに正常に戻りますので安心してください！",
                "はい、システムの最適化をしていますが、もうすぐ完了します！"
            ]
        }
        
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """デフォルトハンドラー設定"""
        # 各カテゴリのデフォルト復旧戦略
        self.recovery_strategies = {
            ErrorCategory.AUDIO_INPUT: self._recover_audio_input,
            ErrorCategory.AUDIO_OUTPUT: self._recover_audio_output,
            ErrorCategory.WHISPER: self._recover_whisper,
            ErrorCategory.VOICEVOX: self._recover_voicevox,
            ErrorCategory.LANGFLOW: self._recover_langflow,
            ErrorCategory.IPC: self._recover_ipc,
            ErrorCategory.SYSTEM: self._recover_system
        }
    
    def register_callback(self, category: ErrorCategory, callback: Callable):
        """エラーカテゴリ別コールバック登録"""
        self.error_callbacks[category] = callback
        self.logger.info(f"Error callback registered for {category.value}")
    
    def register_fallback(self, component: str, fallback_handler: Callable):
        """フォールバックハンドラー登録"""
        self.fallback_handlers[component] = fallback_handler
        self.logger.info(f"Fallback handler registered for {component}")
    
    def handle_error(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        message: str,
        component: str,
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorEvent:
        """統合エラー処理"""
        
        error_key = f"{category.value}:{component}"
        self.error_count[error_key] = self.error_count.get(error_key, 0) + 1
        
        # エラーイベント作成
        error_event = ErrorEvent(
            category=category,
            severity=severity,
            message=message,
            component=component,
            timestamp=datetime.now().isoformat(),
            exception_type=type(exception).__name__ if exception else None,
            traceback=traceback.format_exc() if exception else None,
            context=context or {},
            user_message=self._generate_user_message(category, severity)
        )
        
        # ログ出力
        self._log_error(error_event)
        
        # 重要度別処理
        if severity == ErrorSeverity.CRITICAL:
            self._handle_critical_error(error_event)
        elif severity == ErrorSeverity.HIGH:
            self._handle_high_severity_error(error_event)
        elif severity == ErrorSeverity.MEDIUM:
            self._handle_medium_severity_error(error_event)
        
        # エラー回数チェック
        if self.error_count[error_key] > self.error_threshold:
            self._handle_error_threshold_exceeded(error_event, error_key)
        
        # カテゴリ別コールバック実行
        callback = self.error_callbacks.get(category)
        if callback:
            try:
                callback(error_event)
            except Exception as e:
                self.logger.error(f"Error in callback for {category.value}: {e}")
        
        return error_event
    
    def _generate_user_message(self, category: ErrorCategory, severity: ErrorSeverity) -> str:
        """Yes-Man風ユーザーメッセージ生成"""
        import random
        
        messages = self.yes_man_messages.get(category)
        if not messages:
            return "はい、ちょっとした問題が発生しましたが、必ず解決しますよ！"
        
        base_message = random.choice(messages)
        
        # 重要度による追加メッセージ
        if severity == ErrorSeverity.HIGH:
            base_message += " システムが自動的に復旧を試みています！"
        elif severity == ErrorSeverity.CRITICAL:
            base_message += " 緊急対応中ですが、必ず直りますので安心してください！"
        
        return base_message
    
    def _log_error(self, error_event: ErrorEvent):
        """エラーログ出力"""
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_event.severity, logging.ERROR)
        
        log_message = f"[{error_event.category.value}] {error_event.component}: {error_event.message}"
        
        if error_event.context:
            # 個人情報を除去したコンテキスト
            safe_context = self._sanitize_context(error_event.context)
            log_message += f" Context: {safe_context}"
        
        self.logger.log(log_level, log_message)
        
        if error_event.traceback and log_level >= logging.ERROR:
            self.logger.debug(f"Traceback for {error_event.component}:\\n{error_event.traceback}")
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """コンテキストから個人情報除去"""
        sanitized = {}
        
        # 除去対象キー
        sensitive_keys = {'audio_data', 'text_content', 'user_id', 'session_data'}
        
        for key, value in context.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 100:
                sanitized[key] = f"[DATA: {len(value)} chars]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _handle_critical_error(self, error_event: ErrorEvent):
        """致命的エラー処理"""
        self.logger.critical(f"CRITICAL ERROR in {error_event.component}: {error_event.message}")
        
        # 緊急停止フラグ設定など
        error_event.recovery_action = "system_restart_required"
    
    def _handle_high_severity_error(self, error_event: ErrorEvent):
        """重大エラー処理"""
        self.logger.error(f"HIGH severity error in {error_event.component}")
        
        # 復旧戦略実行
        recovery_strategy = self.recovery_strategies.get(error_event.category)
        if recovery_strategy:
            try:
                recovery_result = recovery_strategy(error_event)
                error_event.recovery_action = recovery_result
            except Exception as e:
                self.logger.error(f"Recovery strategy failed: {e}")
                error_event.recovery_action = "recovery_failed"
    
    def _handle_medium_severity_error(self, error_event: ErrorEvent):
        """中程度エラー処理"""
        # フォールバック実行
        fallback = self.fallback_handlers.get(error_event.component)
        if fallback:
            try:
                fallback(error_event)
                error_event.recovery_action = "fallback_executed"
            except Exception as e:
                self.logger.error(f"Fallback handler failed: {e}")
                error_event.recovery_action = "fallback_failed"
    
    def _handle_error_threshold_exceeded(self, error_event: ErrorEvent, error_key: str):
        """エラー頻発時処理"""
        self.logger.warning(f"Error threshold exceeded for {error_key}")
        error_event.recovery_action = "component_disabled_temporarily"
        
        # エラーカウンタリセット
        self.error_count[error_key] = 0
    
    # === 復旧戦略実装 ===
    
    def _recover_audio_input(self, error_event: ErrorEvent) -> str:
        """音声入力復旧"""
        self.logger.info("Attempting audio input recovery...")
        # マイクデバイス再初期化、代替デバイス選択等
        return "audio_input_device_reset"
    
    def _recover_audio_output(self, error_event: ErrorEvent) -> str:
        """音声出力復旧"""
        self.logger.info("Attempting audio output recovery...")
        # スピーカーデバイス再初期化等
        return "audio_output_device_reset"
    
    def _recover_whisper(self, error_event: ErrorEvent) -> str:
        """Whisper復旧"""
        self.logger.info("Attempting Whisper recovery...")
        # モデル再読込、フォールバックモードに切替等
        return "whisper_model_reloaded"
    
    def _recover_voicevox(self, error_event: ErrorEvent) -> str:
        """VoiceVox復旧"""
        self.logger.info("Attempting VoiceVox recovery...")
        # VoiceVoxサーバー再接続、代替音声合成等
        return "voicevox_reconnected"
    
    def _recover_langflow(self, error_event: ErrorEvent) -> str:
        """LangFlow復旧"""
        self.logger.info("Attempting LangFlow recovery...")
        # LangFlowサーバー再接続、基本応答モード切替等
        return "langflow_reconnected"
    
    def _recover_ipc(self, error_event: ErrorEvent) -> str:
        """IPC通信復旧"""
        self.logger.info("Attempting IPC recovery...")
        # WebSocket再接続等
        return "ipc_reconnected"
    
    def _recover_system(self, error_event: ErrorEvent) -> str:
        """システム復旧"""
        self.logger.info("Attempting system recovery...")
        # システム全体の状態チェックと復旧
        return "system_health_check_completed"
    
    # === コンテキストマネージャ ===
    
    @contextmanager
    def handle_component_errors(self, component: str, category: ErrorCategory):
        """コンポーネント用エラーハンドリングコンテキスト"""
        try:
            yield
        except Exception as e:
            severity = self._determine_severity(e, category)
            self.handle_error(
                category=category,
                severity=severity,
                message=str(e),
                component=component,
                exception=e
            )
            raise  # 必要に応じて再発生
    
    @asynccontextmanager
    async def handle_async_component_errors(self, component: str, category: ErrorCategory):
        """非同期コンポーネント用エラーハンドリングコンテキスト"""
        try:
            yield
        except Exception as e:
            severity = self._determine_severity(e, category)
            self.handle_error(
                category=category,
                severity=severity,
                message=str(e),
                component=component,
                exception=e
            )
            raise
    
    def _determine_severity(self, exception: Exception, category: ErrorCategory) -> ErrorSeverity:
        """例外とカテゴリから重要度を判定"""
        
        # 致命的エラーパターン
        critical_exceptions = (SystemExit, KeyboardInterrupt, MemoryError)
        if isinstance(exception, critical_exceptions):
            return ErrorSeverity.CRITICAL
        
        # 高重要度エラーパターン
        high_severity_exceptions = (ConnectionError, TimeoutError, OSError)
        if isinstance(exception, high_severity_exceptions):
            return ErrorSeverity.HIGH
        
        # カテゴリ別重要度判定
        if category in (ErrorCategory.SYSTEM, ErrorCategory.IPC):
            return ErrorSeverity.HIGH
        elif category in (ErrorCategory.WHISPER, ErrorCategory.VOICEVOX, ErrorCategory.LANGFLOW):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def get_error_stats(self) -> Dict[str, Any]:
        """エラー統計取得"""
        return {
            'total_errors': sum(self.error_count.values()),
            'error_by_component': dict(self.error_count),
            'registered_callbacks': len(self.error_callbacks),
            'registered_fallbacks': len(self.fallback_handlers),
            'timestamp': datetime.now().isoformat()
        }
    
    def reset_error_counts(self):
        """エラーカウンタリセット"""
        self.error_count.clear()
        self.logger.info("Error counts reset")

# シングルトンインスタンス
_error_handler: Optional[YesManErrorHandler] = None

def get_error_handler() -> YesManErrorHandler:
    """エラーハンドラーインスタンス取得"""
    global _error_handler
    if _error_handler is None:
        _error_handler = YesManErrorHandler()
    return _error_handler

# 便利関数
def handle_error(category: ErrorCategory, severity: ErrorSeverity, message: str, 
                component: str, exception: Optional[Exception] = None,
                context: Optional[Dict[str, Any]] = None) -> ErrorEvent:
    """グローバルエラーハンドリング関数"""
    handler = get_error_handler()
    return handler.handle_error(category, severity, message, component, exception, context)

def with_error_handling(category: ErrorCategory, component: str):
    """エラーハンドリングデコレータ"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                handler = get_error_handler()
                async with handler.handle_async_component_errors(component, category):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                handler = get_error_handler()
                with handler.handle_component_errors(component, category):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator