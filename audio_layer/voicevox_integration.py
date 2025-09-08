"""
VoiceVox TTS統合

憲法III: テストファーストに従い、contract テストを先に実装済み
spec.md FR-004: TTS音声合成
憲法V: パフォーマンス制約 - 合成時間<3秒
Yes-Man性格: 陽気で協力的な音声特性
"""

import requests
import base64
import logging
import asyncio
import threading
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import uuid
import queue
import io
import wave

try:
    import sounddevice as sd
    import numpy as np
    AUDIO_PLAYBACK_AVAILABLE = True
except ImportError:
    # 開発時のモック用
    AUDIO_PLAYBACK_AVAILABLE = False
    import numpy as np

from .database.models.agent_settings import AgentSettingsRepository


@dataclass
class VoiceVoxConfig:
    """VoiceVox TTS設定"""
    api_base_url: str = "http://localhost:50021"
    default_speaker_id: int = 1  # Yes-Man用スピーカー
    default_speed: float = 1.1  # 軽快な話速
    default_volume: float = 0.9  # 適度な音量
    default_intonation: float = 1.2  # 表現豊かなイントネーション
    default_pre_phoneme_length: float = 0.1
    default_post_phoneme_length: float = 0.1
    timeout_seconds: int = 10  # API呼び出しタイムアウト
    max_text_length: int = 500  # 最大テキスト長
    synthesis_timeout_seconds: int = 3  # 憲法V: パフォーマンス制約
    audio_format: str = "wav"  # 音声フォーマット
    sample_rate: int = 24000  # VoiceVoxデフォルト


@dataclass
class Speaker:
    """スピーカー情報"""
    id: int
    name: str
    styles: List[Dict[str, Any]]


@dataclass
class SynthesisRequest:
    """音声合成リクエスト"""
    request_id: str
    text: str
    speaker_id: int
    speed: float
    volume: float
    intonation: float
    pre_phoneme_length: float
    post_phoneme_length: float
    created_at: datetime
    status: str = "pending"  # pending, processing, completed, error
    audio_data: Optional[bytes] = None
    duration_seconds: float = 0.0
    synthesis_time_ms: int = 0
    error_message: str = ""


class VoiceVoxIntegration:
    """
    VoiceVox TTS統合クラス
    
    Yes-Man性格に適した音声合成
    憲法V: パフォーマンス制約対応
    """
    
    def __init__(self, config: Optional[VoiceVoxConfig] = None):
        self.config = config or VoiceVoxConfig()
        self.logger = logging.getLogger(__name__)
        self._speakers_cache: Optional[List[Speaker]] = None
        self._is_connected = False
        
        # 合成キュー
        self._synthesis_queue: queue.Queue = queue.Queue()
        self._synthesis_requests: Dict[str, SynthesisRequest] = {}
        self._requests_lock = threading.Lock()
        
        # パフォーマンスメトリクス
        self._total_syntheses = 0
        self._successful_syntheses = 0
        self._average_synthesis_time_ms = 0.0
        
        # 音声再生
        self._playback_sessions: Dict[str, Dict[str, Any]] = {}
        self._playback_lock = threading.Lock()
        
        # バックグラウンド処理
        self._processing_thread: Optional[threading.Thread] = None
        self._stop_processing = False
        
        # 設定読み込み
        self._load_settings()
        
        # 初期化
        self._initialize()
    
    def _load_settings(self) -> None:
        """データベースから設定読み込み"""
        try:
            repo = AgentSettingsRepository()
            config = repo.get_yes_man_config()
            
            # Yes-Man音声設定
            if "tts_speaker_id" in config:
                self.config.default_speaker_id = config["tts_speaker_id"]
            
            if "tts_speed" in config:
                self.config.default_speed = config["tts_speed"]
                
            if "tts_volume" in config:
                self.config.default_volume = config["tts_volume"]
                
            if "tts_intonation" in config:
                self.config.default_intonation = config["tts_intonation"]
                
            self.logger.info(
                f"TTS settings loaded: speaker_id={self.config.default_speaker_id}, "
                f"speed={self.config.default_speed}"
            )
                
        except Exception as e:
            self.logger.warning(f"Failed to load TTS settings, using defaults: {e}")
    
    def _initialize(self) -> None:
        """VoiceVox統合初期化"""
        try:
            # VoiceVox接続確認
            self._check_voicevox_connection()
            
            # スピーカー一覧取得
            self._load_speakers()
            
            # バックグラウンド処理開始
            self._start_background_processing()
            
            self.logger.info("VoiceVox integration initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize VoiceVox integration: {e}")
    
    def _check_voicevox_connection(self) -> bool:
        """VoiceVox API接続確認"""
        try:
            response = requests.get(
                f"{self.config.api_base_url}/version",
                timeout=self.config.timeout_seconds
            )
            
            if response.status_code == 200:
                version_info = response.json()
                self.logger.info(f"Connected to VoiceVox: {version_info}")
                self._is_connected = True
                return True
            else:
                self.logger.error(f"VoiceVox connection failed: {response.status_code}")
                self._is_connected = False
                return False
                
        except Exception as e:
            self.logger.error(f"VoiceVox connection error: {e}")
            self._is_connected = False
            return False
    
    def _load_speakers(self) -> None:
        """スピーカー一覧読み込み"""
        try:
            response = requests.get(
                f"{self.config.api_base_url}/speakers",
                timeout=self.config.timeout_seconds
            )
            
            if response.status_code == 200:
                speakers_data = response.json()
                self._speakers_cache = [
                    Speaker(
                        id=speaker.get("speaker_uuid", speaker.get("id", i)),
                        name=speaker.get("name", f"Speaker {i}"),
                        styles=speaker.get("styles", [])
                    )
                    for i, speaker in enumerate(speakers_data)
                ]
                
                self.logger.info(f"Loaded {len(self._speakers_cache)} speakers")
                
                # デフォルトスピーカー確認
                self._validate_default_speaker()
                
            else:
                self.logger.error(f"Failed to load speakers: {response.status_code}")
                self._speakers_cache = []
                
        except Exception as e:
            self.logger.error(f"Speaker loading error: {e}")
            self._speakers_cache = []
    
    def _validate_default_speaker(self) -> None:
        """デフォルトスピーカー妥当性確認"""
        if not self._speakers_cache:
            return
        
        speaker_ids = [speaker.id for speaker in self._speakers_cache]
        if self.config.default_speaker_id not in speaker_ids:
            self.logger.warning(
                f"Default speaker ID {self.config.default_speaker_id} not available. "
                f"Using speaker ID {speaker_ids[0]}"
            )
            self.config.default_speaker_id = speaker_ids[0]
    
    def get_speakers(self) -> List[Dict[str, Any]]:
        """
        利用可能スピーカー取得
        
        Returns:
            List[Dict]: スピーカー一覧
        """
        if not self._speakers_cache:
            self._load_speakers()
        
        if not self._speakers_cache:
            return []
        
        return [
            {
                "id": speaker.id,
                "name": speaker.name,
                "styles": speaker.styles
            }
            for speaker in self._speakers_cache
        ]
    
    def synthesize_text(self, text: str, 
                       speaker_id: Optional[int] = None,
                       speed: Optional[float] = None,
                       volume: Optional[float] = None,
                       intonation: Optional[float] = None) -> Dict[str, Any]:
        """
        テキスト音声合成
        
        Args:
            text: 合成対象テキスト
            speaker_id: スピーカーID
            speed: 話速
            volume: 音量
            intonation: イントネーション
            
        Returns:
            Dict: {
                "status": str,
                "audio_data": str (base64),
                "duration_seconds": float,
                "synthesis_time_ms": int,
                "request_id": str
            }
        """
        if not text or not text.strip():
            return {
                "status": "error",
                "error": "empty_text",
                "message": "Text cannot be empty"
            }
        
        if len(text) > self.config.max_text_length:
            return {
                "status": "error",
                "error": "text_too_long",
                "message": f"Text exceeds maximum length of {self.config.max_text_length} characters"
            }
        
        if not self._is_connected:
            self._check_voicevox_connection()
            if not self._is_connected:
                return {
                    "status": "error",
                    "error": "voicevox_unavailable",
                    "message": "VoiceVox API is not available"
                }
        
        # パラメータ設定
        final_speaker_id = speaker_id or self.config.default_speaker_id
        final_speed = speed or self.config.default_speed
        final_volume = volume or self.config.default_volume
        final_intonation = intonation or self.config.default_intonation
        
        # スピーカーID妥当性確認
        if not self._is_valid_speaker_id(final_speaker_id):
            return {
                "status": "error",
                "error": "invalid_speaker_id",
                "message": f"Invalid speaker ID: {final_speaker_id}",
                "available_speakers": [s.id for s in (self._speakers_cache or [])]
            }
        
        try:
            start_time = datetime.now()
            
            # 音声合成実行
            audio_data = self._perform_synthesis(
                text=text,
                speaker_id=final_speaker_id,
                speed=final_speed,
                volume=final_volume,
                intonation=final_intonation
            )
            
            synthesis_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # パフォーマンス制約チェック
            if synthesis_time_ms > self.config.synthesis_timeout_seconds * 1000:
                self.logger.warning(
                    f"TTS synthesis exceeded {self.config.synthesis_timeout_seconds}s constraint: {synthesis_time_ms}ms"
                )
            
            # 音声データをbase64エンコード
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 音声長計算
            duration_seconds = self._calculate_audio_duration(audio_data)
            
            # メトリクス更新
            self._update_metrics(synthesis_time_ms, True)
            
            self.logger.info(
                f"TTS synthesis completed: text='{text[:50]}...', "
                f"duration={duration_seconds:.2f}s, time={synthesis_time_ms}ms"
            )
            
            return {
                "status": "success",
                "audio_data": audio_base64,
                "duration_seconds": round(duration_seconds, 2),
                "synthesis_time_ms": synthesis_time_ms,
                "request_id": str(uuid.uuid4())
            }
            
        except Exception as e:
            self.logger.error(f"TTS synthesis failed: {e}")
            self._update_metrics(0, False)
            
            return {
                "status": "error",
                "error": "synthesis_failed",
                "message": str(e)
            }
    
    def _perform_synthesis(self, text: str, speaker_id: int, 
                          speed: float, volume: float, intonation: float) -> bytes:
        """音声合成実行"""
        try:
            # 音韻生成
            audio_query_response = requests.post(
                f"{self.config.api_base_url}/audio_query",
                params={"text": text, "speaker": speaker_id},
                timeout=self.config.timeout_seconds
            )
            
            if audio_query_response.status_code != 200:
                raise Exception(f"Audio query failed: {audio_query_response.status_code}")
            
            audio_query = audio_query_response.json()
            
            # パラメータ調整
            audio_query["speedScale"] = speed
            audio_query["volumeScale"] = volume
            audio_query["intonationScale"] = intonation
            audio_query["prePhonemeLength"] = self.config.default_pre_phoneme_length
            audio_query["postPhonemeLength"] = self.config.default_post_phoneme_length
            
            # 音声合成
            synthesis_response = requests.post(
                f"{self.config.api_base_url}/synthesis",
                params={"speaker": speaker_id},
                json=audio_query,
                timeout=self.config.timeout_seconds
            )
            
            if synthesis_response.status_code != 200:
                raise Exception(f"Synthesis failed: {synthesis_response.status_code}")
            
            return synthesis_response.content
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"VoiceVox API error: {e}")
        except Exception as e:
            raise Exception(f"Synthesis error: {e}")
    
    def _is_valid_speaker_id(self, speaker_id: int) -> bool:
        """スピーカーID妥当性確認"""
        if not self._speakers_cache:
            return True  # キャッシュがない場合は許可
        
        return any(speaker.id == speaker_id for speaker in self._speakers_cache)
    
    def _calculate_audio_duration(self, audio_data: bytes) -> float:
        """音声データ長計算"""
        try:
            # WAVファイルの長さを計算
            with io.BytesIO(audio_data) as audio_io:
                with wave.open(audio_io, 'rb') as wav_file:
                    frames = wav_file.getnframes()
                    sample_rate = wav_file.getframerate()
                    return frames / sample_rate if sample_rate > 0 else 0.0
                    
        except Exception as e:
            self.logger.debug(f"Audio duration calculation failed: {e}")
            # フォールバック: データサイズから推定
            return len(audio_data) / (self.config.sample_rate * 2)  # 16bit mono想定
    
    def play_audio(self, audio_data: str, volume: float = 1.0, 
                   blocking: bool = False) -> Dict[str, Any]:
        """
        音声再生
        
        Args:
            audio_data: base64エンコード音声データ
            volume: 再生音量
            blocking: 再生完了まで待機
            
        Returns:
            Dict: {
                "status": str,
                "playback_id": str,
                "message": str
            }
        """
        if not AUDIO_PLAYBACK_AVAILABLE:
            return {
                "status": "error",
                "playback_id": "",
                "message": "Audio playback not available (sounddevice not installed)"
            }
        
        try:
            # base64デコード
            audio_bytes = base64.b64decode(audio_data)
            playback_id = str(uuid.uuid4())
            
            # 再生セッション作成
            with self._playback_lock:
                self._playback_sessions[playback_id] = {
                    "status": "playing",
                    "volume": volume,
                    "started_at": datetime.now()
                }
            
            # 音声再生実行
            self._execute_audio_playback(audio_bytes, volume, playback_id, blocking)
            
            return {
                "status": "playing" if not blocking else "completed",
                "playback_id": playback_id,
                "message": "Audio playback started successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Audio playback failed: {e}")
            return {
                "status": "error",
                "playback_id": "",
                "message": f"Playback failed: {str(e)}"
            }
    
    def _execute_audio_playback(self, audio_bytes: bytes, volume: float, 
                               playback_id: str, blocking: bool) -> None:
        """音声再生実行"""
        try:
            # WAVデータから音声配列取得
            with io.BytesIO(audio_bytes) as audio_io:
                with wave.open(audio_io, 'rb') as wav_file:
                    sample_rate = wav_file.getframerate()
                    frames = wav_file.readframes(wav_file.getnframes())
                    audio_array = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            
            # 音量調整
            audio_array *= volume
            
            # 再生実行
            if blocking:
                sd.play(audio_array, sample_rate)
                sd.wait()
                
                # セッション状態更新
                with self._playback_lock:
                    if playback_id in self._playback_sessions:
                        self._playback_sessions[playback_id]["status"] = "completed"
            else:
                # 非同期再生
                def playback_thread():
                    try:
                        sd.play(audio_array, sample_rate)
                        sd.wait()
                        
                        with self._playback_lock:
                            if playback_id in self._playback_sessions:
                                self._playback_sessions[playback_id]["status"] = "completed"
                                
                    except Exception as e:
                        self.logger.error(f"Async playback error: {e}")
                        with self._playback_lock:
                            if playback_id in self._playback_sessions:
                                self._playback_sessions[playback_id]["status"] = "error"
                
                thread = threading.Thread(target=playback_thread, daemon=True)
                thread.start()
                
        except Exception as e:
            self.logger.error(f"Audio playback execution error: {e}")
            
            with self._playback_lock:
                if playback_id in self._playback_sessions:
                    self._playback_sessions[playback_id]["status"] = "error"
    
    async def synthesize_text_async(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        非同期テキスト音声合成
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.synthesize_text,
            text,
            kwargs.get('speaker_id'),
            kwargs.get('speed'),
            kwargs.get('volume'),
            kwargs.get('intonation')
        )
    
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
                # 再生セッションクリーンアップ
                self._cleanup_completed_playbacks()
                
                # 定期的なVoiceVox接続確認
                if time.time() % 60 < 1:  # 1分毎
                    self._check_voicevox_connection()
                
                time.sleep(1.0)
                
            except Exception as e:
                self.logger.error(f"Background processing error: {e}")
                time.sleep(5.0)
    
    def _cleanup_completed_playbacks(self) -> None:
        """完了した再生セッションクリーンアップ"""
        try:
            with self._playback_lock:
                completed_sessions = []
                for playback_id, session in self._playback_sessions.items():
                    if session["status"] in ["completed", "error"]:
                        # 5分経過したセッションを削除
                        elapsed = (datetime.now() - session["started_at"]).total_seconds()
                        if elapsed > 300:
                            completed_sessions.append(playback_id)
                
                for playback_id in completed_sessions:
                    del self._playback_sessions[playback_id]
                    
        except Exception as e:
            self.logger.debug(f"Playback cleanup error: {e}")
    
    def _update_metrics(self, synthesis_time_ms: int, success: bool) -> None:
        """パフォーマンスメトリクス更新"""
        self._total_syntheses += 1
        
        if success:
            self._successful_syntheses += 1
            
            # 移動平均更新
            if self._average_synthesis_time_ms == 0:
                self._average_synthesis_time_ms = synthesis_time_ms
            else:
                alpha = 0.1
                self._average_synthesis_time_ms = (
                    alpha * synthesis_time_ms + 
                    (1 - alpha) * self._average_synthesis_time_ms
                )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        TTS統計取得
        
        Returns:
            Dict: 統計情報
        """
        with self._playback_lock:
            active_playbacks = len(self._playback_sessions)
        
        return {
            "voicevox_connected": self._is_connected,
            "available_speakers": len(self._speakers_cache) if self._speakers_cache else 0,
            "total_syntheses": self._total_syntheses,
            "successful_syntheses": self._successful_syntheses,
            "success_rate": round(
                self._successful_syntheses / max(self._total_syntheses, 1), 2
            ),
            "average_synthesis_time_ms": round(self._average_synthesis_time_ms, 2),
            "meets_performance_constraint": self._average_synthesis_time_ms < 3000,
            "active_playbacks": active_playbacks,
            "config": {
                "default_speaker_id": self.config.default_speaker_id,
                "default_speed": self.config.default_speed,
                "default_volume": self.config.default_volume,
                "api_base_url": self.config.api_base_url
            }
        }
    
    def cleanup(self) -> None:
        """
        リソースクリーンアップ
        """
        # 処理停止
        self._stop_processing = True
        
        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)
        
        # 再生セッションクリア
        with self._playback_lock:
            self._playback_sessions.clear()
        
        # 合成リクエストクリア
        with self._requests_lock:
            self._synthesis_requests.clear()
        
        self.logger.info("VoiceVox integration cleaned up")


def create_voicevox_instance(api_base_url: str = "http://localhost:50021",
                           speaker_id: int = 1) -> VoiceVoxIntegration:
    """
    VoiceVoxインスタンス作成ヘルパー
    
    Args:
        api_base_url: VoiceVox API URL
        speaker_id: デフォルトスピーカーID
        
    Returns:
        VoiceVoxIntegration: 初期化済みインスタンス
    """
    config = VoiceVoxConfig(
        api_base_url=api_base_url,
        default_speaker_id=speaker_id
    )
    
    return VoiceVoxIntegration(config)