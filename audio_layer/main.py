"""
音声レイヤーメイン

憲法III: テストファーストに従い、すべてのコンポーネント統合
spec.md: 音声対話システムの中核
憲法IV: プライバシーファースト - メモリ内処理のみ
憲法V: パフォーマンス制約対応
"""

import asyncio
import logging
import threading
import time
import signal
import sys
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
import json
import uuid

# 音声レイヤーコンポーネント
from .whisper_integration import WhisperIntegration, WhisperConfig
from .wake_word_detector import WakeWordDetector, WakeWordConfig
from .continuous_recognition import ContinuousRecognition, ContinuousRecognitionConfig
from .voicevox_integration import VoiceVoxIntegration, VoiceVoxConfig
from .audio_buffer import AudioBufferManager, AudioBufferConfig, AudioChunk

# データベース
from .database.models.conversation_session import ConversationSession, ConversationSessionRepository
from .database.models.conversation_exchange import ConversationExchange, ConversationExchangeRepository
from .database.models.agent_settings import AgentSettingsRepository


@dataclass
class AudioLayerConfig:
    """音声レイヤー全体設定"""
    # Whisper設定
    whisper_model_size: str = "medium"
    whisper_use_gpu: bool = True
    whisper_language: str = "ja"
    
    # ウェイクワード設定
    wake_word: str = "Yes-Man"
    wake_word_confidence_threshold: float = 0.8
    wake_word_cooldown_ms: int = 2000
    
    # 継続音声認識設定
    continuous_max_duration_seconds: int = 30
    continuous_silence_timeout_seconds: int = 5
    
    # VoiceVox設定
    voicevox_api_url: str = "http://localhost:50021"
    voicevox_speaker_id: int = 1
    voicevox_speed: float = 1.1
    voicevox_volume: float = 0.9
    voicevox_intonation: float = 1.2
    
    # 音声バッファ設定
    buffer_max_seconds: int = 3  # 憲法IV: 3秒循環バッファ
    buffer_sample_rate: int = 16000
    buffer_enable_real_time: bool = True
    
    # システム設定
    enable_automatic_session_management: bool = True
    session_timeout_minutes: int = 30
    log_level: str = "INFO"


class AudioLayerManager:
    """
    音声レイヤー統合管理クラス
    
    すべての音声コンポーネントを統合し、Yes-Man音声対話システムを実現
    """
    
    def __init__(self, config: Optional[AudioLayerConfig] = None):
        self.config = config or AudioLayerConfig()
        
        # ログ設定
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # 状態管理
        self._is_running = False
        self._current_session: Optional[ConversationSession] = None
        self._shutdown_event = threading.Event()
        
        # コンポーネント
        self.whisper: Optional[WhisperIntegration] = None
        self.wake_word_detector: Optional[WakeWordDetector] = None
        self.continuous_recognition: Optional[ContinuousRecognition] = None
        self.voicevox: Optional[VoiceVoxIntegration] = None
        self.audio_buffer: Optional[AudioBufferManager] = None
        
        # データベースリポジトリ
        self.session_repo = ConversationSessionRepository()
        self.exchange_repo = ConversationExchangeRepository()
        self.settings_repo = AgentSettingsRepository()
        
        # パフォーマンスメトリクス
        self._start_time: Optional[datetime] = None
        self._total_exchanges = 0
        self._successful_wake_word_detections = 0
        self._successful_recognitions = 0
        self._successful_syntheses = 0
        
        # コールバック
        self._wake_word_callback: Optional[Callable] = None
        self._recognition_complete_callback: Optional[Callable] = None
        self._synthesis_complete_callback: Optional[Callable] = None
        
        self.logger.info("Audio layer manager initialized")
    
    def _setup_logging(self) -> None:
        """ログ設定"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('audio_layer.log')
            ]
        )
    
    async def initialize(self) -> bool:
        """
        音声レイヤー初期化
        
        Returns:
            bool: 初期化成功
        """
        try:
            self.logger.info("Initializing audio layer components...")
            
            # 1. Whisper統合初期化
            whisper_config = WhisperConfig(
                model_size=self.config.whisper_model_size,
                use_gpu=self.config.whisper_use_gpu,
                language=self.config.whisper_language
            )
            self.whisper = WhisperIntegration(whisper_config)
            
            if not self.whisper.initialize():
                self.logger.error("Failed to initialize Whisper")
                return False
            
            # 2. 音声バッファ初期化
            buffer_config = AudioBufferConfig(
                max_buffer_seconds=self.config.buffer_max_seconds,
                sample_rate=self.config.buffer_sample_rate,
                enable_real_time_processing=self.config.buffer_enable_real_time
            )
            self.audio_buffer = AudioBufferManager(buffer_config)
            
            # 3. ウェイクワード検出初期化
            wake_word_config = WakeWordConfig(
                wake_word=self.config.wake_word,
                confidence_threshold=self.config.wake_word_confidence_threshold,
                cooldown_ms=self.config.wake_word_cooldown_ms,
                max_audio_buffer_seconds=self.config.buffer_max_seconds
            )
            self.wake_word_detector = WakeWordDetector(wake_word_config, self.whisper)
            
            # 4. 継続音声認識初期化
            continuous_config = ContinuousRecognitionConfig(
                max_duration_seconds=self.config.continuous_max_duration_seconds,
                silence_timeout_seconds=self.config.continuous_silence_timeout_seconds,
                sample_rate=self.config.buffer_sample_rate
            )
            self.continuous_recognition = ContinuousRecognition(continuous_config, self.whisper)
            
            # 5. VoiceVox TTS初期化
            voicevox_config = VoiceVoxConfig(
                api_base_url=self.config.voicevox_api_url,
                default_speaker_id=self.config.voicevox_speaker_id,
                default_speed=self.config.voicevox_speed,
                default_volume=self.config.voicevox_volume,
                default_intonation=self.config.voicevox_intonation
            )
            self.voicevox = VoiceVoxIntegration(voicevox_config)
            
            # 6. コールバック設定
            self._setup_callbacks()
            
            # 7. 音声バッファにプロセッサ登録
            self._register_audio_processors()
            
            self._start_time = datetime.now()
            self.logger.info("Audio layer initialization completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Audio layer initialization failed: {e}")
            return False
    
    def _setup_callbacks(self) -> None:
        """コールバック設定"""
        self._wake_word_callback = self._on_wake_word_detected
        self._recognition_complete_callback = self._on_recognition_complete
        self._synthesis_complete_callback = self._on_synthesis_complete
    
    def _register_audio_processors(self) -> None:
        """音声プロセッサ登録"""
        if self.audio_buffer and self.wake_word_detector:
            # ウェイクワード検出プロセッサ
            def wake_word_processor(chunk: AudioChunk):
                if chunk.is_speech and chunk.data is not None:
                    self.wake_word_detector.process_audio_chunk(chunk.data)
            
            self.audio_buffer.register_chunk_processor(wake_word_processor)
    
    async def start(self) -> bool:
        """
        音声レイヤー開始
        
        Returns:
            bool: 開始成功
        """
        try:
            if self._is_running:
                self.logger.warning("Audio layer is already running")
                return True
            
            self.logger.info("Starting audio layer...")
            
            # ウェイクワード検出開始
            if not self.wake_word_detector.start_listening(self._wake_word_callback):
                self.logger.error("Failed to start wake word detection")
                return False
            
            # 会話セッション作成
            if self.config.enable_automatic_session_management:
                await self._create_conversation_session()
            
            self._is_running = True
            self.logger.info("Audio layer started successfully - listening for wake word")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start audio layer: {e}")
            return False
    
    async def stop(self) -> None:
        """音声レイヤー停止"""
        try:
            if not self._is_running:
                return
            
            self.logger.info("Stopping audio layer...")
            self._is_running = False
            
            # ウェイクワード検出停止
            if self.wake_word_detector:
                self.wake_word_detector.stop_listening()
            
            # 継続音声認識停止
            if self.continuous_recognition:
                # 全てのアクティブセッションを停止
                stats = self.continuous_recognition.get_statistics()
                self.logger.info(f"Stopping {stats['active_sessions']} active recognition sessions")
            
            # 現在のセッション終了
            if self._current_session and self.config.enable_automatic_session_management:
                await self._end_conversation_session()
            
            self._shutdown_event.set()
            self.logger.info("Audio layer stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping audio layer: {e}")
    
    def process_audio_input(self, audio_data: bytes) -> bool:
        """
        音声入力処理
        
        Args:
            audio_data: 音声データ
            
        Returns:
            bool: 処理成功
        """
        try:
            # NumPy配列に変換
            import numpy as np
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # 音声バッファに追加
            if self.audio_buffer:
                return self.audio_buffer.add_audio_data(audio_array)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Audio input processing error: {e}")
            return False
    
    async def _on_wake_word_detected(self, confidence: float, detected_text: str) -> None:
        """ウェイクワード検出時コールバック"""
        try:
            self.logger.info(f"Wake word detected: '{detected_text}' (confidence: {confidence:.2f})")
            self._successful_wake_word_detections += 1
            
            # 継続音声認識開始
            if self._current_session:
                result = self.continuous_recognition.start_continuous_recognition(
                    session_id=self._current_session.session_id,
                    max_duration_seconds=self.config.continuous_max_duration_seconds,
                    silence_timeout_seconds=self.config.continuous_silence_timeout_seconds
                )
                
                if result["status"] == "recognizing":
                    self.logger.info(f"Continuous recognition started: {result['recognition_session_id']}")
                else:
                    self.logger.error(f"Failed to start continuous recognition: {result['message']}")
            
        except Exception as e:
            self.logger.error(f"Wake word callback error: {e}")
    
    async def _on_recognition_complete(self, session_id: str, final_text: str, confidence: float) -> None:
        """音声認識完了時コールバック"""
        try:
            self.logger.info(f"Recognition complete: '{final_text}' (confidence: {confidence:.2f})")
            self._successful_recognitions += 1
            
            # 会話交換記録
            if self._current_session:
                exchange = ConversationExchange(
                    session_id=self._current_session.id,
                    user_input=final_text,
                    user_input_confidence=confidence,
                    exchange_type="voice",
                    created_at=datetime.now()
                )
                
                exchange_id = await self.exchange_repo.create(exchange)
                self.logger.info(f"Conversation exchange recorded: {exchange_id}")
                
                self._total_exchanges += 1
        
        except Exception as e:
            self.logger.error(f"Recognition complete callback error: {e}")
    
    async def _on_synthesis_complete(self, text: str, audio_data: str, duration: float) -> None:
        """音声合成完了時コールバック"""
        try:
            self.logger.info(f"Synthesis complete: '{text[:50]}...', duration: {duration:.2f}s")
            self._successful_syntheses += 1
            
        except Exception as e:
            self.logger.error(f"Synthesis complete callback error: {e}")
    
    async def synthesize_and_speak(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        テキスト合成と発話
        
        Args:
            text: 発話テキスト
            **kwargs: VoiceVox設定オプション
            
        Returns:
            Dict: 合成結果
        """
        try:
            if not self.voicevox:
                return {"status": "error", "message": "VoiceVox not initialized"}
            
            # Yes-Man性格の音声パラメータ適用
            synthesis_params = {
                "speaker_id": kwargs.get("speaker_id", self.config.voicevox_speaker_id),
                "speed": kwargs.get("speed", self.config.voicevox_speed),
                "volume": kwargs.get("volume", self.config.voicevox_volume),
                "intonation": kwargs.get("intonation", self.config.voicevox_intonation)
            }
            
            # 音声合成
            synthesis_result = self.voicevox.synthesize_text(text, **synthesis_params)
            
            if synthesis_result["status"] == "success":
                # 音声再生
                playback_result = self.voicevox.play_audio(
                    synthesis_result["audio_data"],
                    volume=synthesis_params["volume"]
                )
                
                # コールバック呼び出し
                await self._on_synthesis_complete(
                    text, 
                    synthesis_result["audio_data"], 
                    synthesis_result["duration_seconds"]
                )
                
                return {
                    "status": "success",
                    "synthesis_result": synthesis_result,
                    "playback_result": playback_result
                }
            else:
                return synthesis_result
                
        except Exception as e:
            self.logger.error(f"Synthesis and speak error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _create_conversation_session(self) -> None:
        """会話セッション作成"""
        try:
            session = ConversationSession(
                session_id=str(uuid.uuid4()),
                started_at=datetime.now(),
                user_name="User",
                session_status="ACTIVE"
            )
            
            session_id = await self.session_repo.create(session)
            session.id = session_id
            self._current_session = session
            
            self.logger.info(f"Conversation session created: {session.session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to create conversation session: {e}")
    
    async def _end_conversation_session(self) -> None:
        """会話セッション終了"""
        try:
            if self._current_session:
                self._current_session.ended_at = datetime.now()
                self._current_session.total_exchanges = self._total_exchanges
                self._current_session.session_status = "COMPLETED"
                
                await self.session_repo.update(self._current_session)
                
                self.logger.info(f"Conversation session ended: {self._current_session.session_id}")
                self._current_session = None
                
        except Exception as e:
            self.logger.error(f"Failed to end conversation session: {e}")
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """
        システム統計取得
        
        Returns:
            Dict: 統計情報
        """
        uptime_seconds = 0
        if self._start_time:
            uptime_seconds = (datetime.now() - self._start_time).total_seconds()
        
        stats = {
            "system": {
                "is_running": self._is_running,
                "uptime_seconds": round(uptime_seconds, 2),
                "current_session": self._current_session.session_id if self._current_session else None,
                "total_exchanges": self._total_exchanges,
                "successful_wake_word_detections": self._successful_wake_word_detections,
                "successful_recognitions": self._successful_recognitions,
                "successful_syntheses": self._successful_syntheses
            }
        }
        
        # コンポーネント統計
        if self.wake_word_detector:
            stats["wake_word_detector"] = self.wake_word_detector.get_statistics()
        
        if self.continuous_recognition:
            stats["continuous_recognition"] = self.continuous_recognition.get_statistics()
        
        if self.voicevox:
            stats["voicevox"] = self.voicevox.get_statistics()
        
        if self.audio_buffer:
            stats["audio_buffer"] = self.audio_buffer.get_statistics()
        
        if self.whisper:
            stats["whisper"] = self.whisper.get_performance_stats()
        
        return stats
    
    async def cleanup(self) -> None:
        """
        リソースクリーンアップ
        
        憲法IV: メモリ完全クリア
        """
        try:
            self.logger.info("Cleaning up audio layer resources...")
            
            # 停止処理
            await self.stop()
            
            # 各コンポーネントクリーンアップ
            if self.wake_word_detector:
                self.wake_word_detector.cleanup()
            
            if self.continuous_recognition:
                self.continuous_recognition.cleanup()
            
            if self.voicevox:
                self.voicevox.cleanup()
            
            if self.audio_buffer:
                self.audio_buffer.cleanup()
            
            if self.whisper:
                self.whisper.cleanup()
            
            self.logger.info("Audio layer cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")


# シグナルハンドラ
def signal_handler(audio_manager: AudioLayerManager):
    """シグナルハンドラ"""
    def handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        asyncio.create_task(audio_manager.cleanup())
        sys.exit(0)
    return handler


async def main():
    """メイン実行関数"""
    # 設定読み込み
    config = AudioLayerConfig()
    
    # 音声レイヤーマネージャー作成
    audio_manager = AudioLayerManager(config)
    
    # シグナルハンドラ設定
    signal.signal(signal.SIGINT, signal_handler(audio_manager))
    signal.signal(signal.SIGTERM, signal_handler(audio_manager))
    
    try:
        # 初期化
        if not await audio_manager.initialize():
            print("Failed to initialize audio layer")
            return 1
        
        # 開始
        if not await audio_manager.start():
            print("Failed to start audio layer")
            return 1
        
        print("Yes-Man Audio Layer started successfully!")
        print("Listening for wake word: 'Yes-Man'")
        print("Press Ctrl+C to stop...")
        
        # メインループ
        while audio_manager._is_running:
            await asyncio.sleep(1)
            
            # 統計表示（デバッグ用）
            if datetime.now().second % 30 == 0:  # 30秒毎
                stats = audio_manager.get_system_statistics()
                print(f"Uptime: {stats['system']['uptime_seconds']:.0f}s, "
                      f"Wake words: {stats['system']['successful_wake_word_detections']}, "
                      f"Recognitions: {stats['system']['successful_recognitions']}")
        
        return 0
        
    except Exception as e:
        print(f"Audio layer error: {e}")
        return 1
    
    finally:
        await audio_manager.cleanup()


def run_main():
    """エントリーポイント用のラッパー関数"""
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


if __name__ == "__main__":
    run_main()