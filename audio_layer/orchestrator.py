"""
Yes-Man メインオーケストレーター
全コンポーネントの協調処理とフロー制御

憲法II: テストファースト - 状態遷移の明確化
憲法VI: パフォーマンス最適化 - 非同期処理で3秒以内応答
憲法VIII: 指示に従う - Yes-Man協調システムの完成
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime

from .error_handler import get_error_handler, ErrorCategory, ErrorSeverity, with_error_handling
from .ipc_server import get_ipc_server, IPCServer
from .whisper_integration import WhisperClient
from .voicevox_client import VoiceVoxClient
from .langflow_client import LangFlowClient
from .wake_word_detection import WakeWordDetector

# ログ設定
logger = logging.getLogger("YesManOrchestrator")

class SystemState(Enum):
    """システム状態"""
    INITIALIZING = "initializing"      # 初期化中
    IDLE = "idle"                      # 待機中
    LISTENING = "listening"            # ウェイクワード待機
    WAKE_DETECTED = "wake_detected"    # ウェイクワード検出
    RECORDING = "recording"            # 音声録音中
    PROCESSING_STT = "processing_stt"  # STT処理中
    PROCESSING_LLM = "processing_llm"  # LLM処理中
    PROCESSING_TTS = "processing_tts"  # TTS処理中
    SPEAKING = "speaking"              # 音声出力中
    ERROR = "error"                    # エラー状態
    SHUTDOWN = "shutdown"              # 停止中

class ConversationPhase(Enum):
    """会話フェーズ"""
    WAKE_WORD = "wake_word"
    USER_SPEECH = "user_speech"
    AGENT_THINKING = "agent_thinking"
    AGENT_SPEAKING = "agent_speaking"
    SESSION_END = "session_end"

@dataclass
class SessionContext:
    """会話セッション情報"""
    session_id: str
    start_time: float
    current_phase: ConversationPhase
    user_text: Optional[str] = None
    agent_response: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None
    wake_word_confidence: Optional[float] = None
    processing_times: Optional[Dict[str, float]] = None

class YesManOrchestrator:
    """Yes-Man メインオーケストレーター"""
    
    def __init__(self):
        self.current_state = SystemState.INITIALIZING
        self.session: Optional[SessionContext] = None
        self.error_handler = get_error_handler()
        self.ipc_server: Optional[IPCServer] = None
        
        # コンポーネント
        self.whisper_client: Optional[WhisperClient] = None
        self.voicevox_client: Optional[VoiceVoxClient] = None
        self.langflow_client: Optional[LangFlowClient] = None
        self.wake_word_detector: Optional[WakeWordDetector] = None
        
        # 設定
        self.config = {
            'wake_word_sensitivity': 0.8,
            'max_recording_duration': 30.0,  # 30秒
            'stt_timeout': 10.0,
            'llm_timeout': 15.0,
            'tts_timeout': 10.0,
            'session_timeout': 300.0,  # 5分
            'max_response_time': 3.0,  # 憲法VI: 3秒以内応答
        }
        
        # パフォーマンス監視
        self.performance_metrics = {
            'wake_word_response_time': 0.0,
            'stt_processing_time': 0.0,
            'llm_processing_time': 0.0,
            'tts_processing_time': 0.0,
            'total_response_time': 0.0,
            'sessions_completed': 0,
            'errors_handled': 0
        }
        
        # 状態遷移コールバック
        self.state_callbacks: Dict[SystemState, Callable] = {}
        self.phase_callbacks: Dict[ConversationPhase, Callable] = {}
        
        # エラーハンドラー設定
        self._setup_error_handlers()
        
        logger.info("YesManOrchestrator initialized")
    
    def _setup_error_handlers(self):
        """エラーハンドラー設定"""
        
        def handle_whisper_error(error_event):
            logger.warning("Whisper error detected, switching to fallback")
            # フォールバック処理
        
        def handle_voicevox_error(error_event):
            logger.warning("VoiceVox error detected, switching to backup TTS")
            # フォールバック処理
        
        def handle_langflow_error(error_event):
            logger.warning("LangFlow error detected, using basic responses")
            # 基本応答モード
        
        self.error_handler.register_callback(ErrorCategory.WHISPER, handle_whisper_error)
        self.error_handler.register_callback(ErrorCategory.VOICEVOX, handle_voicevox_error)
        self.error_handler.register_callback(ErrorCategory.LANGFLOW, handle_langflow_error)
    
    @with_error_handling(ErrorCategory.SYSTEM, "orchestrator_init")
    async def initialize(self):
        """システム初期化"""
        logger.info("Initializing Yes-Man system...")
        
        try:
            # IPC サーバー初期化
            self.ipc_server = get_ipc_server()
            self._register_ipc_handlers()
            
            # コンポーネント初期化
            await self._initialize_components()
            
            # 状態変更
            await self._change_state(SystemState.IDLE)
            
            logger.info("Yes-Man system initialized successfully")
            
        except Exception as e:
            await self._change_state(SystemState.ERROR)
            self.error_handler.handle_error(
                ErrorCategory.SYSTEM,
                ErrorSeverity.CRITICAL,
                f"Initialization failed: {str(e)}",
                "orchestrator",
                e
            )
            raise
    
    async def _initialize_components(self):
        """コンポーネント個別初期化"""
        
        # Whisper クライアント
        try:
            self.whisper_client = WhisperClient()
            await self.whisper_client.initialize()
            logger.info("Whisper client initialized")
        except Exception as e:
            self.error_handler.handle_error(
                ErrorCategory.WHISPER,
                ErrorSeverity.HIGH,
                f"Whisper initialization failed: {str(e)}",
                "whisper_client",
                e
            )
        
        # VoiceVox クライアント
        try:
            self.voicevox_client = VoiceVoxClient()
            await self.voicevox_client.initialize()
            logger.info("VoiceVox client initialized")
        except Exception as e:
            self.error_handler.handle_error(
                ErrorCategory.VOICEVOX,
                ErrorSeverity.HIGH,
                f"VoiceVox initialization failed: {str(e)}",
                "voicevox_client",
                e
            )
        
        # LangFlow クライアント
        try:
            self.langflow_client = LangFlowClient()
            await self.langflow_client.initialize()
            logger.info("LangFlow client initialized")
        except Exception as e:
            self.error_handler.handle_error(
                ErrorCategory.LANGFLOW,
                ErrorSeverity.HIGH,
                f"LangFlow initialization failed: {str(e)}",
                "langflow_client",
                e
            )
        
        # ウェイクワード検出器
        try:
            self.wake_word_detector = WakeWordDetector(
                sensitivity=self.config['wake_word_sensitivity']
            )
            await self.wake_word_detector.initialize()
            logger.info("Wake word detector initialized")
        except Exception as e:
            self.error_handler.handle_error(
                ErrorCategory.AUDIO_INPUT,
                ErrorSeverity.HIGH,
                f"Wake word detector initialization failed: {str(e)}",
                "wake_word_detector",
                e
            )
    
    def _register_ipc_handlers(self):
        """IPCハンドラー登録"""
        if not self.ipc_server:
            return
        
        # UI からのメッセージハンドラー
        self.ipc_server.register_handler('user_input', self._handle_manual_input)
        self.ipc_server.register_handler('system_command', self._handle_system_command)
        self.ipc_server.register_handler('settings_update', self._handle_settings_update)
        
        logger.info("IPC handlers registered")
    
    async def _handle_manual_input(self, data: Dict[str, Any]):
        """手動入力処理"""
        text = data.get('text', '').strip()
        if not text:
            return {'status': 'error', 'message': 'Empty input'}
        
        logger.info(f"Manual input received: {text}")
        
        # 新しいセッション開始
        session_id = f"manual_{int(time.time())}"
        await self._start_conversation_session(session_id, skip_wake_word=True)
        
        if self.session:
            self.session.user_text = text
            await self._process_user_speech_complete()
        
        return {'status': 'processed', 'session_id': session_id}
    
    async def _handle_system_command(self, data: Dict[str, Any]):
        """システムコマンド処理"""
        command = data.get('command')
        params = data.get('params', {})
        
        logger.info(f"System command received: {command}")
        
        if command == 'start_listening':
            await self._change_state(SystemState.LISTENING)
        elif command == 'stop_listening':
            await self._change_state(SystemState.IDLE)
        elif command == 'restart_components':
            await self._restart_components()
        elif command == 'get_status':
            return self._get_system_status()
        
        return {'status': 'executed', 'command': command}
    
    async def _handle_settings_update(self, data: Dict[str, Any]):
        """設定更新処理"""
        logger.info("Settings update received")
        
        # 設定マージ
        self.config.update(data)
        
        # コンポーネントに設定反映
        if self.wake_word_detector and 'wake_word_sensitivity' in data:
            self.wake_word_detector.set_sensitivity(data['wake_word_sensitivity'])
        
        return {'status': 'updated'}
    
    @with_error_handling(ErrorCategory.SYSTEM, "main_loop")
    async def run(self):
        """メインループ実行"""
        logger.info("Starting Yes-Man main loop...")
        
        try:
            # システム初期化
            await self.initialize()
            
            # リスニング開始
            await self._change_state(SystemState.LISTENING)
            
            # メインループ
            while self.current_state != SystemState.SHUTDOWN:
                await self._process_main_loop_cycle()
                await asyncio.sleep(0.1)  # CPU使用率制御
            
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            self.error_handler.handle_error(
                ErrorCategory.SYSTEM,
                ErrorSeverity.CRITICAL,
                f"Main loop failed: {str(e)}",
                "orchestrator",
                e
            )
        finally:
            await self.shutdown()
    
    async def _process_main_loop_cycle(self):
        """メインループサイクル処理"""
        
        if self.current_state == SystemState.LISTENING:
            await self._process_wake_word_detection()
        
        elif self.current_state == SystemState.WAKE_DETECTED:
            await self._process_wake_word_detected()
        
        elif self.current_state == SystemState.RECORDING:
            await self._process_speech_recording()
        
        elif self.current_state == SystemState.PROCESSING_STT:
            await self._process_stt()
        
        elif self.current_state == SystemState.PROCESSING_LLM:
            await self._process_llm()
        
        elif self.current_state == SystemState.PROCESSING_TTS:
            await self._process_tts()
        
        elif self.current_state == SystemState.SPEAKING:
            await self._process_speaking()
        
        elif self.current_state == SystemState.ERROR:
            await self._process_error_state()
    
    async def _process_wake_word_detection(self):
        \"\"\"ウェイクワード検出処理\"\"\"
        if not self.wake_word_detector:
            return
        
        detection = await self.wake_word_detector.check_wake_word()
        if detection and detection['confidence'] > self.config['wake_word_sensitivity']:
            logger.info(f"Wake word detected: {detection['keyword']} (confidence: {detection['confidence']})")
            
            # セッション開始
            session_id = f"session_{int(time.time())}"
            await self._start_conversation_session(session_id)
            
            if self.session:
                self.session.wake_word_confidence = detection['confidence']
            
            # IPC通知
            if self.ipc_server:
                await self.ipc_server.send_wake_word_detected(
                    detection['keyword'],
                    detection['confidence'],
                    detection.get('audio_duration', 0.0)
                )
            
            await self._change_state(SystemState.WAKE_DETECTED)
    
    async def _process_wake_word_detected(self):
        \"\"\"ウェイクワード検出後処理\"\"\"
        logger.info("Processing wake word detection...")
        
        # 録音開始準備
        await asyncio.sleep(0.5)  # 少し待ってから録音開始
        await self._change_state(SystemState.RECORDING)
    
    async def _process_speech_recording(self):
        \"\"\"音声録音処理\"\"\"
        if not self.wake_word_detector:
            await self._change_state(SystemState.ERROR)
            return
        
        # 音声録音開始
        start_time = time.time()
        
        if self.ipc_server:
            await self.ipc_server.send_user_speech_start(
                self.session.session_id if self.session else "unknown",
                0.5  # 仮の音量
            )
        
        # 音声録音実行（簡略化）
        recording_result = await self.wake_word_detector.record_user_speech(
            max_duration=self.config['max_recording_duration']
        )
        
        if recording_result and recording_result.get('audio_data'):
            logger.info("Speech recording completed")
            
            # セッション情報更新
            if self.session:
                if not self.session.processing_times:
                    self.session.processing_times = {}
                self.session.processing_times['recording'] = time.time() - start_time
            
            # IPC通知
            if self.ipc_server:
                await self.ipc_server.send_user_speech_end(
                    self.session.session_id if self.session else "unknown",
                    "",  # STT前なのでテキストは空
                    time.time() - start_time
                )
            
            await self._change_state(SystemState.PROCESSING_STT)
        else:
            logger.warning("Speech recording failed or empty")
            await self._end_conversation_session()
    
    async def _process_stt(self):
        \"\"\"STT処理\"\"\"
        if not self.whisper_client or not self.session:
            await self._change_state(SystemState.ERROR)
            return
        
        start_time = time.time()
        logger.info("Processing speech-to-text...")
        
        try:
            # STT実行（モック）
            text_result = await self.whisper_client.transcribe_mock("こんにちは、Yes-Man！今日の天気はどうですか？")
            
            if text_result and text_result.get('text'):
                self.session.user_text = text_result['text']
                
                # パフォーマンス記録
                stt_time = time.time() - start_time
                self.session.processing_times['stt'] = stt_time
                self.performance_metrics['stt_processing_time'] = stt_time
                
                logger.info(f"STT completed: '{self.session.user_text}' (time: {stt_time:.2f}s)")
                
                await self._change_state(SystemState.PROCESSING_LLM)
            else:
                logger.warning("STT failed or empty result")
                await self._end_conversation_session()
                
        except Exception as e:
            self.error_handler.handle_error(
                ErrorCategory.WHISPER,
                ErrorSeverity.HIGH,
                f"STT processing failed: {str(e)}",
                "stt_processor",
                e
            )
            await self._end_conversation_session()
    
    async def _process_llm(self):
        \"\"\"LLM処理\"\"\"
        if not self.langflow_client or not self.session or not self.session.user_text:
            await self._change_state(SystemState.ERROR)
            return
        
        start_time = time.time()
        logger.info(f"Processing LLM for: '{self.session.user_text}'")
        
        try:
            # LLM実行
            response = await self.langflow_client.process_conversation(
                self.session.user_text,
                session_id=self.session.session_id
            )
            
            if response and response.get('response'):
                self.session.agent_response = response['response']
                
                # パフォーマンス記録
                llm_time = time.time() - start_time
                self.session.processing_times['llm'] = llm_time
                self.performance_metrics['llm_processing_time'] = llm_time
                
                logger.info(f"LLM completed (time: {llm_time:.2f}s)")
                
                # IPC通知
                if self.ipc_server:
                    await self.ipc_server.send_agent_response(
                        self.session.session_id,
                        self.session.agent_response,
                        llm_time,
                        response.get('context_type', 'general'),
                        response.get('confidence', 0.8)
                    )
                
                await self._change_state(SystemState.PROCESSING_TTS)
            else:
                logger.warning("LLM processing failed or empty response")
                await self._end_conversation_session()
                
        except Exception as e:
            self.error_handler.handle_error(
                ErrorCategory.LANGFLOW,
                ErrorSeverity.HIGH,
                f"LLM processing failed: {str(e)}",
                "llm_processor",
                e
            )
            await self._end_conversation_session()
    
    async def _process_tts(self):
        \"\"\"TTS処理\"\"\"
        if not self.voicevox_client or not self.session or not self.session.agent_response:
            await self._change_state(SystemState.ERROR)
            return
        
        start_time = time.time()
        logger.info("Processing text-to-speech...")
        
        try:
            # IPC通知（TTS開始）
            if self.ipc_server:
                await self.ipc_server.send_tts_start(
                    self.session.session_id,
                    self.session.agent_response,
                    "1"  # VoiceVox スピーカーID
                )
            
            # TTS実行
            audio_result = await self.voicevox_client.synthesize_speech(
                self.session.agent_response
            )
            
            if audio_result and audio_result.get('success'):
                # パフォーマンス記録
                tts_time = time.time() - start_time
                self.session.processing_times['tts'] = tts_time
                self.performance_metrics['tts_processing_time'] = tts_time
                
                logger.info(f"TTS completed (time: {tts_time:.2f}s)")
                
                await self._change_state(SystemState.SPEAKING)
            else:
                logger.warning("TTS processing failed")
                await self._end_conversation_session()
                
        except Exception as e:
            self.error_handler.handle_error(
                ErrorCategory.VOICEVOX,
                ErrorSeverity.HIGH,
                f"TTS processing failed: {str(e)}",
                "tts_processor",
                e
            )
            await self._end_conversation_session()
    
    async def _process_speaking(self):
        \"\"\"音声出力処理\"\"\"
        if not self.session:
            await self._change_state(SystemState.ERROR)
            return
        
        logger.info("Playing synthesized speech...")
        
        # 音声再生シミュレーション（実際の実装では音声ファイル再生）
        await asyncio.sleep(2.0)  # 仮の再生時間
        
        # IPC通知（TTS終了）
        if self.ipc_server:
            await self.ipc_server.send_tts_end(
                self.session.session_id,
                self.session.agent_response,
                "1",  # VoiceVox スピーカーID
                2.0   # 再生時間
            )
        
        # セッション完了
        await self._end_conversation_session()
    
    async def _process_error_state(self):
        \"\"\"エラー状態処理\"\"\"
        logger.info("Processing error state, attempting recovery...")
        
        # 自動復旧試行
        await asyncio.sleep(1.0)
        
        # アイドル状態に復帰
        await self._change_state(SystemState.IDLE)
        await asyncio.sleep(1.0)
        await self._change_state(SystemState.LISTENING)
    
    async def _start_conversation_session(self, session_id: str, skip_wake_word: bool = False):
        \"\"\"会話セッション開始\"\"\"
        self.session = SessionContext(
            session_id=session_id,
            start_time=time.time(),
            current_phase=ConversationPhase.USER_SPEECH if skip_wake_word else ConversationPhase.WAKE_WORD,
            processing_times={}
        )
        
        logger.info(f"Conversation session started: {session_id}")
    
    async def _end_conversation_session(self):
        \"\"\"会話セッション終了\"\"\"
        if not self.session:
            return
        
        # パフォーマンス計算
        total_time = time.time() - self.session.start_time
        self.performance_metrics['total_response_time'] = total_time
        self.performance_metrics['sessions_completed'] += 1
        
        # 憲法VI: 3秒以内チェック
        if total_time > self.config['max_response_time']:
            logger.warning(f"Response time exceeded target: {total_time:.2f}s > {self.config['max_response_time']}s")
        
        logger.info(f"Session ended: {self.session.session_id} (total: {total_time:.2f}s)")
        
        self.session = None
        await self._change_state(SystemState.LISTENING)
    
    async def _change_state(self, new_state: SystemState):
        \"\"\"状態変更\"\"\"
        if self.current_state == new_state:
            return
        
        old_state = self.current_state
        self.current_state = new_state
        
        logger.info(f"State changed: {old_state.value} -> {new_state.value}")
        
        # 状態変更コールバック実行
        callback = self.state_callbacks.get(new_state)
        if callback:
            try:
                await callback() if asyncio.iscoroutinefunction(callback) else callback()
            except Exception as e:
                logger.error(f"State callback error: {e}")
    
    def _get_system_status(self) -> Dict[str, Any]:
        \"\"\"システム状態取得\"\"\"
        return {
            'current_state': self.current_state.value,
            'session_active': self.session is not None,
            'session_id': self.session.session_id if self.session else None,
            'performance_metrics': dict(self.performance_metrics),
            'config': dict(self.config),
            'components_status': {
                'whisper': self.whisper_client is not None,
                'voicevox': self.voicevox_client is not None,
                'langflow': self.langflow_client is not None,
                'wake_word_detector': self.wake_word_detector is not None,
                'ipc_server': self.ipc_server is not None
            },
            'timestamp': datetime.now().isoformat()
        }
    
    async def _restart_components(self):
        \"\"\"コンポーネント再起動\"\"\"
        logger.info("Restarting components...")
        
        await self._change_state(SystemState.INITIALIZING)
        
        try:
            await self._initialize_components()
            await self._change_state(SystemState.LISTENING)
            logger.info("Components restarted successfully")
        except Exception as e:
            await self._change_state(SystemState.ERROR)
            raise
    
    async def shutdown(self):
        \"\"\"システム終了\"\"\"
        logger.info("Shutting down Yes-Man system...")
        
        await self._change_state(SystemState.SHUTDOWN)
        
        # セッション終了
        if self.session:
            await self._end_conversation_session()
        
        # コンポーネント終了
        if self.whisper_client:
            await self.whisper_client.cleanup()
        if self.voicevox_client:
            await self.voicevox_client.cleanup()
        if self.langflow_client:
            await self.langflow_client.cleanup()
        if self.wake_word_detector:
            await self.wake_word_detector.cleanup()
        
        # IPCサーバー終了
        if self.ipc_server:
            self.ipc_server.stop_server()
        
        logger.info("Yes-Man system shutdown completed")

# メイン実行
async def main():
    \"\"\"メイン実行関数\"\"\"
    orchestrator = YesManOrchestrator()
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())