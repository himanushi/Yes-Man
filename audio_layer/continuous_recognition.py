"""
継続音声認識

憲法III: テストファーストに従い、contract テストを先に実装済み
spec.md FR-003: 継続音声認識
憲法IV: プライバシーファースト - メモリ内処理のみ
憲法V: パフォーマンス制約 - 応答時間<3秒
"""

import numpy as np
import logging
import asyncio
import threading
import time
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import uuid
import queue

from .whisper_integration import WhisperIntegration, WhisperConfig
from .database.models.agent_settings import AgentSettingsRepository


@dataclass
class ContinuousRecognitionConfig:
    """継続音声認識設定"""
    max_duration_seconds: int = 30  # 最大録音時間
    silence_timeout_seconds: int = 5  # 無音での自動停止時間
    chunk_duration_ms: int = 1000  # 音声チャンク時間
    min_speech_duration_ms: int = 500  # 最低発話時間
    confidence_threshold: float = 0.6  # 音声認識信頼度閾値
    sample_rate: int = 16000
    update_frequency_ms: int = 500  # リアルタイム更新頻度
    vad_threshold: float = 0.6  # Voice Activity Detection閾値
    buffer_size_seconds: int = 10  # 音声バッファサイズ


@dataclass
class RecognitionSession:
    """音声認識セッション"""
    session_id: str
    recognition_session_id: str
    started_at: datetime
    status: str = "in_progress"  # in_progress, completed, error
    current_text: str = ""
    confidence: float = 0.0
    elapsed_seconds: float = 0.0
    final_text: str = ""
    error_message: str = ""
    max_duration: int = 30
    silence_timeout: int = 5
    last_speech_time: Optional[datetime] = None
    audio_buffer: deque = field(default_factory=deque)
    processing_lock: threading.Lock = field(default_factory=threading.Lock)


class ContinuousRecognition:
    """
    継続音声認識クラス
    
    憲法IV: プライバシーファースト - メモリ内処理のみ
    憲法V: パフォーマンス制約対応
    """
    
    def __init__(self, config: Optional[ContinuousRecognitionConfig] = None,
                 whisper: Optional[WhisperIntegration] = None):
        self.config = config or ContinuousRecognitionConfig()
        self.logger = logging.getLogger(__name__)
        
        # Whisper統合
        if whisper:
            self.whisper = whisper
        else:
            whisper_config = WhisperConfig(
                model_size="medium",  # 継続認識は精度重視
                use_gpu=True,
                language="ja"
            )
            self.whisper = WhisperIntegration(whisper_config)
        
        # アクティブセッション管理
        self._active_sessions: Dict[str, RecognitionSession] = {}
        self._sessions_lock = threading.Lock()
        
        # パフォーマンスメトリクス
        self._total_sessions = 0
        self._successful_recognitions = 0
        self._average_response_time_ms = 0.0
        
        # 設定読み込み
        self._load_settings()
        
        # バックグラウンド処理スレッド
        self._processing_thread: Optional[threading.Thread] = None
        self._stop_processing = False
        self._start_background_processing()
    
    def _load_settings(self) -> None:
        """データベースから設定読み込み"""
        try:
            repo = AgentSettingsRepository()
            config = repo.get_yes_man_config()
            
            # 設定値更新
            if "continuous_recognition_timeout" in config:
                self.config.max_duration_seconds = config["continuous_recognition_timeout"]
            
            if "silence_timeout_seconds" in config:
                self.config.silence_timeout_seconds = config["silence_timeout_seconds"]
                
            if "recognition_confidence_threshold" in config:
                self.config.confidence_threshold = config["recognition_confidence_threshold"]
                
            self.logger.info(f"Settings loaded: timeout={self.config.max_duration_seconds}s")
                
        except Exception as e:
            self.logger.warning(f"Failed to load settings, using defaults: {e}")
    
    def start_continuous_recognition(self, session_id: str,
                                  max_duration_seconds: Optional[int] = None,
                                  silence_timeout_seconds: Optional[int] = None) -> Dict[str, Any]:
        """
        継続音声認識開始
        
        Args:
            session_id: ウェイクワードセッションID
            max_duration_seconds: 最大録音時間
            silence_timeout_seconds: 無音タイムアウト
            
        Returns:
            Dict: {
                "status": str,
                "recognition_session_id": str,
                "message": str
            }
        """
        try:
            # Whisper初期化確認
            if not self.whisper._is_initialized:
                if not self.whisper.initialize():
                    return {
                        "status": "error",
                        "recognition_session_id": "",
                        "message": "Failed to initialize Whisper"
                    }
            
            # 新しい認識セッション作成
            recognition_session_id = f"recognition-{uuid.uuid4()}"
            
            session = RecognitionSession(
                session_id=session_id,
                recognition_session_id=recognition_session_id,
                started_at=datetime.now(),
                max_duration=max_duration_seconds or self.config.max_duration_seconds,
                silence_timeout=silence_timeout_seconds or self.config.silence_timeout_seconds,
                audio_buffer=deque(maxlen=self.config.sample_rate * self.config.buffer_size_seconds)
            )
            
            # セッション登録
            with self._sessions_lock:
                self._active_sessions[recognition_session_id] = session
            
            self._total_sessions += 1
            
            self.logger.info(
                f"Started continuous recognition: session={recognition_session_id}, "
                f"max_duration={session.max_duration}s, silence_timeout={session.silence_timeout}s"
            )
            
            return {
                "status": "recognizing",
                "recognition_session_id": recognition_session_id,
                "message": "Continuous recognition started successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start continuous recognition: {e}")
            return {
                "status": "error",
                "recognition_session_id": "",
                "message": f"Failed to start recognition: {str(e)}"
            }
    
    def stop_continuous_recognition(self, recognition_session_id: str) -> Dict[str, Any]:
        """
        継続音声認識停止
        
        Args:
            recognition_session_id: 認識セッションID
            
        Returns:
            Dict: {
                "status": str,
                "final_text": str,
                "duration_seconds": float,
                "message": str
            }
        """
        try:
            with self._sessions_lock:
                if recognition_session_id not in self._active_sessions:
                    return {
                        "status": "error",
                        "final_text": "",
                        "duration_seconds": 0.0,
                        "message": "Recognition session not found"
                    }
                
                session = self._active_sessions[recognition_session_id]
            
            # 最終認識処理
            final_result = self._finalize_recognition(session)
            
            # セッション削除（プライバシー保護）
            with self._sessions_lock:
                if recognition_session_id in self._active_sessions:
                    del self._active_sessions[recognition_session_id]
            
            # メトリクス更新
            if session.status == "completed":
                self._successful_recognitions += 1
            
            duration = (datetime.now() - session.started_at).total_seconds()
            
            self.logger.info(
                f"Stopped continuous recognition: session={recognition_session_id}, "
                f"final_text='{final_result[:50]}...', duration={duration:.2f}s"
            )
            
            return {
                "status": session.status,
                "final_text": final_result,
                "duration_seconds": round(duration, 2),
                "message": "Recognition stopped successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to stop continuous recognition: {e}")
            return {
                "status": "error",
                "final_text": "",
                "duration_seconds": 0.0,
                "message": f"Failed to stop recognition: {str(e)}"
            }
    
    def get_recognition_result(self, recognition_session_id: str) -> Dict[str, Any]:
        """
        音声認識結果取得
        
        Args:
            recognition_session_id: 認識セッションID
            
        Returns:
            Dict: {
                "status": str,
                "current_text": str,
                "confidence": float,
                "elapsed_seconds": float
            }
        """
        try:
            with self._sessions_lock:
                if recognition_session_id not in self._active_sessions:
                    return {
                        "status": "error",
                        "current_text": "",
                        "confidence": 0.0,
                        "elapsed_seconds": 0.0,
                        "error": "Recognition session not found"
                    }
                
                session = self._active_sessions[recognition_session_id]
            
            elapsed = (datetime.now() - session.started_at).total_seconds()
            
            return {
                "status": session.status,
                "current_text": session.current_text,
                "confidence": round(session.confidence, 2),
                "elapsed_seconds": round(elapsed, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get recognition result: {e}")
            return {
                "status": "error",
                "current_text": "",
                "confidence": 0.0,
                "elapsed_seconds": 0.0,
                "error": str(e)
            }
    
    def process_audio_chunk(self, recognition_session_id: str, audio_chunk: np.ndarray) -> bool:
        """
        音声チャンク処理
        
        憲法IV: メモリ内処理のみ、即座にバッファ追加
        
        Args:
            recognition_session_id: 認識セッションID
            audio_chunk: 音声データチャンク
            
        Returns:
            bool: 処理成功
        """
        try:
            with self._sessions_lock:
                if recognition_session_id not in self._active_sessions:
                    return False
                
                session = self._active_sessions[recognition_session_id]
            
            # 音声バッファに追加
            with session.processing_lock:
                session.audio_buffer.extend(audio_chunk)
                
                # Voice Activity Detection
                if self._detect_speech(audio_chunk):
                    session.last_speech_time = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process audio chunk: {e}")
            return False
    
    def _start_background_processing(self) -> None:
        """バックグラウンド処理開始"""
        self._processing_thread = threading.Thread(
            target=self._background_processing_loop,
            daemon=True
        )
        self._processing_thread.start()
    
    def _background_processing_loop(self) -> None:
        """バックグラウンド処理ループ"""
        while not self._stop_processing:
            try:
                # 全セッションを処理
                active_session_ids = list(self._active_sessions.keys())
                
                for session_id in active_session_ids:
                    self._process_session(session_id)
                
                # CPU負荷軽減
                time.sleep(self.config.update_frequency_ms / 1000.0)
                
            except Exception as e:
                self.logger.error(f"Background processing error: {e}")
                time.sleep(1.0)
    
    def _process_session(self, recognition_session_id: str) -> None:
        """セッション処理"""
        try:
            with self._sessions_lock:
                if recognition_session_id not in self._active_sessions:
                    return
                
                session = self._active_sessions[recognition_session_id]
            
            # ステータスチェック
            if session.status != "in_progress":
                return
            
            # タイムアウトチェック
            now = datetime.now()
            elapsed = (now - session.started_at).total_seconds()
            
            # 最大時間チェック
            if elapsed >= session.max_duration:
                session.status = "completed"
                self.logger.info(f"Session {recognition_session_id} completed by max duration")
                return
            
            # 無音タイムアウトチェック
            if session.last_speech_time:
                silence_duration = (now - session.last_speech_time).total_seconds()
                if silence_duration >= session.silence_timeout:
                    session.status = "completed"
                    self.logger.info(f"Session {recognition_session_id} completed by silence timeout")
                    return
            
            # 音声認識処理
            self._process_audio_recognition(session)
            
        except Exception as e:
            self.logger.error(f"Session processing error: {e}")
    
    def _process_audio_recognition(self, session: RecognitionSession) -> None:
        """音声認識処理"""
        try:
            with session.processing_lock:
                # バッファから音声データ取得
                if len(session.audio_buffer) < self.config.sample_rate:  # 最低1秒必要
                    return
                
                # 認識対象データ抽出
                audio_data = np.array(list(session.audio_buffer), dtype=np.float32)
                
                # バッファクリア（プライバシー保護）
                session.audio_buffer.clear()
            
            # Whisper音声認識実行
            start_time = datetime.now()
            result = self.whisper.transcribe(audio_data, language="ja")
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 結果更新
            if result.get("text"):
                session.current_text = result["text"].strip()
                session.confidence = result.get("confidence", 0.0)
                session.elapsed_seconds = (datetime.now() - session.started_at).total_seconds()
                
                self.logger.debug(
                    f"Recognition update: '{session.current_text[:50]}...', "
                    f"confidence={session.confidence:.2f}, time={processing_time_ms}ms"
                )
            
            # パフォーマンス制約チェック
            if processing_time_ms > 3000:
                self.logger.warning(
                    f"Recognition processing exceeded 3s constraint: {processing_time_ms}ms"
                )
                
        except Exception as e:
            self.logger.error(f"Audio recognition processing error: {e}")
            session.status = "error"
            session.error_message = str(e)
    
    def _finalize_recognition(self, session: RecognitionSession) -> str:
        """認識結果の最終化"""
        try:
            # 残りのバッファを処理
            with session.processing_lock:
                if len(session.audio_buffer) > 0:
                    audio_data = np.array(list(session.audio_buffer), dtype=np.float32)
                    result = self.whisper.transcribe(audio_data, language="ja")
                    
                    if result.get("text"):
                        # 現在のテキストと結合
                        current = session.current_text.strip()
                        final = result["text"].strip()
                        
                        if current and final:
                            session.final_text = f"{current} {final}"
                        elif final:
                            session.final_text = final
                        else:
                            session.final_text = current
                    else:
                        session.final_text = session.current_text
                    
                    # バッファクリア（プライバシー保護）
                    session.audio_buffer.clear()
                else:
                    session.final_text = session.current_text
            
            # ステータス確定
            if session.status == "in_progress":
                session.status = "completed"
            
            return session.final_text
            
        except Exception as e:
            self.logger.error(f"Failed to finalize recognition: {e}")
            session.status = "error"
            session.error_message = str(e)
            return session.current_text
    
    def _detect_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        音声検出（Voice Activity Detection）
        
        Returns:
            bool: 音声検出あり
        """
        try:
            # RMS計算による簡易VAD
            rms = np.sqrt(np.mean(audio_chunk ** 2))
            return rms > self.config.vad_threshold / 10.0  # 閾値調整
            
        except Exception as e:
            self.logger.debug(f"Speech detection error: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        認識統計取得
        
        Returns:
            Dict: 統計情報
        """
        with self._sessions_lock:
            active_sessions = len(self._active_sessions)
        
        return {
            "total_sessions": self._total_sessions,
            "successful_recognitions": self._successful_recognitions,
            "active_sessions": active_sessions,
            "success_rate": round(
                self._successful_recognitions / max(self._total_sessions, 1), 2
            ),
            "average_response_time_ms": round(self._average_response_time_ms, 2),
            "meets_performance_constraint": self._average_response_time_ms < 3000,
            "config": {
                "max_duration_seconds": self.config.max_duration_seconds,
                "silence_timeout_seconds": self.config.silence_timeout_seconds,
                "confidence_threshold": self.config.confidence_threshold
            }
        }
    
    def cleanup(self) -> None:
        """
        リソースクリーンアップ
        
        憲法IV: メモリ完全クリア
        """
        # 処理停止
        self._stop_processing = True
        
        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)
        
        # 全セッション削除
        with self._sessions_lock:
            for session in self._active_sessions.values():
                with session.processing_lock:
                    session.audio_buffer.clear()
            
            self._active_sessions.clear()
        
        # Whisperクリーンアップ
        if self.whisper:
            self.whisper.cleanup()
        
        self.logger.info("Continuous recognition cleaned up")


def create_continuous_recognition(config: Optional[ContinuousRecognitionConfig] = None) -> ContinuousRecognition:
    """
    継続音声認識インスタンス作成ヘルパー
    
    Args:
        config: 設定オプション
        
    Returns:
        ContinuousRecognition: 初期化済みインスタンス
    """
    return ContinuousRecognition(config)