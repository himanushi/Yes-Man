"""
音声バッファ管理

憲法IV: プライバシーファースト - メモリ内のみ、3秒循環バッファ
憲法V: パフォーマンス制約 - 効率的なメモリ管理
spec.md: 音声データ処理の中核コンポーネント
"""

import numpy as np
import logging
import threading
import time
from typing import Optional, Callable, List, Tuple, Any, Dict
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timedelta
import queue
import uuid


@dataclass
class AudioBufferConfig:
    """音声バッファ設定"""
    sample_rate: int = 16000  # サンプリングレート
    chunk_size: int = 1024  # チャンクサイズ
    max_buffer_seconds: int = 3  # 憲法IV: 3秒循環バッファ
    dtype: str = "float32"  # データ型
    channels: int = 1  # モノラル
    buffer_overflow_action: str = "overwrite"  # overflow | discard | overwrite
    silence_threshold: float = 0.01  # 無音判定閾値
    energy_window_size: int = 512  # エネルギー計算ウィンドウ
    enable_real_time_processing: bool = True
    processing_interval_ms: int = 50  # リアルタイム処理間隔


@dataclass  
class AudioChunk:
    """音声チャンクデータ"""
    chunk_id: str
    data: np.ndarray
    timestamp: datetime
    sample_rate: int
    energy_level: float
    is_speech: bool
    duration_ms: int


class CircularAudioBuffer:
    """
    循環音声バッファ
    
    憲法IV: プライバシーファースト - 固定サイズ循環バッファでメモリ効率化
    """
    
    def __init__(self, max_size: int, sample_rate: int):
        self.max_size = max_size
        self.sample_rate = sample_rate
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._overflow_count = 0
        self._total_samples = 0
    
    def add_samples(self, samples: np.ndarray) -> bool:
        """
        サンプル追加
        
        Args:
            samples: 音声サンプル配列
            
        Returns:
            bool: 追加成功
        """
        try:
            with self._lock:
                # オーバーフロー検出
                if len(self._buffer) + len(samples) > self.max_size:
                    self._overflow_count += 1
                
                # 循環バッファに追加（古いデータは自動削除）
                self._buffer.extend(samples)
                self._total_samples += len(samples)
                
                return True
                
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to add samples: {e}")
            return False
    
    def get_snapshot(self) -> np.ndarray:
        """
        バッファスナップショット取得
        
        憲法IV: コピーを返してメモリ安全性確保
        
        Returns:
            np.ndarray: バッファデータコピー
        """
        with self._lock:
            return np.array(list(self._buffer), dtype=np.float32)
    
    def get_latest(self, duration_seconds: float) -> np.ndarray:
        """
        最新の指定時間分データ取得
        
        Args:
            duration_seconds: 取得時間（秒）
            
        Returns:
            np.ndarray: 最新データ
        """
        samples_needed = int(duration_seconds * self.sample_rate)
        
        with self._lock:
            buffer_array = np.array(list(self._buffer), dtype=np.float32)
            
            if len(buffer_array) >= samples_needed:
                return buffer_array[-samples_needed:]
            else:
                return buffer_array
    
    def clear(self) -> None:
        """バッファクリア"""
        with self._lock:
            self._buffer.clear()
    
    def get_size(self) -> int:
        """現在のバッファサイズ取得"""
        with self._lock:
            return len(self._buffer)
    
    def get_duration_seconds(self) -> float:
        """現在のバッファ時間長取得"""
        return self.get_size() / self.sample_rate if self.sample_rate > 0 else 0.0
    
    def get_statistics(self) -> Dict[str, Any]:
        """バッファ統計取得"""
        with self._lock:
            return {
                "current_size": len(self._buffer),
                "max_size": self.max_size,
                "utilization_ratio": len(self._buffer) / self.max_size if self.max_size > 0 else 0,
                "duration_seconds": self.get_duration_seconds(),
                "overflow_count": self._overflow_count,
                "total_samples_processed": self._total_samples
            }


class AudioBufferManager:
    """
    音声バッファ管理クラス
    
    憲法IV: プライバシーファースト - メモリ内処理のみ
    憲法V: パフォーマンス制約対応
    """
    
    def __init__(self, config: Optional[AudioBufferConfig] = None):
        self.config = config or AudioBufferConfig()
        self.logger = logging.getLogger(__name__)
        
        # メイン循環バッファ
        buffer_size = int(self.config.sample_rate * self.config.max_buffer_seconds)
        self.main_buffer = CircularAudioBuffer(buffer_size, self.config.sample_rate)
        
        # チャンクキュー（リアルタイム処理用）
        self._chunk_queue: queue.Queue = queue.Queue(maxsize=100)
        self._chunk_processors: List[Callable[[AudioChunk], None]] = []
        self._processor_lock = threading.Lock()
        
        # リアルタイム処理スレッド
        self._processing_thread: Optional[threading.Thread] = None
        self._stop_processing = False
        
        # パフォーマンスメトリクス
        self._processed_chunks = 0
        self._dropped_chunks = 0
        self._average_processing_time_ms = 0.0
        self._last_activity_time = datetime.now()
        
        # 音声検出
        self._speech_detector = SpeechDetector(
            silence_threshold=self.config.silence_threshold,
            window_size=self.config.energy_window_size
        )
        
        # 初期化
        if self.config.enable_real_time_processing:
            self._start_real_time_processing()
        
        self.logger.info(f"Audio buffer manager initialized: {self.config.max_buffer_seconds}s buffer")
    
    def add_audio_data(self, audio_data: np.ndarray) -> bool:
        """
        音声データ追加
        
        Args:
            audio_data: 音声データ配列
            
        Returns:
            bool: 追加成功
        """
        try:
            # データ型変換
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # メイン循環バッファに追加
            if not self.main_buffer.add_samples(audio_data):
                return False
            
            # リアルタイム処理用チャンク作成
            if self.config.enable_real_time_processing:
                self._create_and_queue_chunk(audio_data)
            
            # アクティビティ時刻更新
            self._last_activity_time = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add audio data: {e}")
            return False
    
    def get_buffer_snapshot(self) -> np.ndarray:
        """
        バッファスナップショット取得
        
        Returns:
            np.ndarray: バッファデータ
        """
        return self.main_buffer.get_snapshot()
    
    def get_latest_audio(self, duration_seconds: float) -> np.ndarray:
        """
        最新音声データ取得
        
        Args:
            duration_seconds: 取得時間（秒）
            
        Returns:
            np.ndarray: 最新音声データ
        """
        return self.main_buffer.get_latest(duration_seconds)
    
    def register_chunk_processor(self, processor: Callable[[AudioChunk], None]) -> str:
        """
        チャンクプロセッサ登録
        
        Args:
            processor: チャンク処理関数
            
        Returns:
            str: プロセッサID
        """
        processor_id = str(uuid.uuid4())
        
        with self._processor_lock:
            # プロセッサにIDを付加して管理
            setattr(processor, '_processor_id', processor_id)
            self._chunk_processors.append(processor)
        
        self.logger.info(f"Registered chunk processor: {processor_id}")
        return processor_id
    
    def unregister_chunk_processor(self, processor_id: str) -> bool:
        """
        チャンクプロセッサ登録解除
        
        Args:
            processor_id: プロセッサID
            
        Returns:
            bool: 解除成功
        """
        try:
            with self._processor_lock:
                self._chunk_processors = [
                    p for p in self._chunk_processors 
                    if getattr(p, '_processor_id', None) != processor_id
                ]
            
            self.logger.info(f"Unregistered chunk processor: {processor_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister processor: {e}")
            return False
    
    def _create_and_queue_chunk(self, audio_data: np.ndarray) -> None:
        """音声チャンク作成とキューイング"""
        try:
            # エネルギーレベル計算
            energy_level = self._speech_detector.calculate_energy(audio_data)
            
            # 音声検出
            is_speech = self._speech_detector.detect_speech(audio_data)
            
            # チャンク作成
            chunk = AudioChunk(
                chunk_id=str(uuid.uuid4()),
                data=audio_data.copy(),  # コピーでプライバシー保護
                timestamp=datetime.now(),
                sample_rate=self.config.sample_rate,
                energy_level=energy_level,
                is_speech=is_speech,
                duration_ms=int(len(audio_data) * 1000 / self.config.sample_rate)
            )
            
            # キューに追加
            try:
                self._chunk_queue.put_nowait(chunk)
            except queue.Full:
                # キューが満杯の場合は古いチャンクを破棄
                try:
                    self._chunk_queue.get_nowait()
                    self._chunk_queue.put_nowait(chunk)
                    self._dropped_chunks += 1
                except queue.Empty:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Failed to create audio chunk: {e}")
    
    def _start_real_time_processing(self) -> None:
        """リアルタイム処理開始"""
        self._processing_thread = threading.Thread(
            target=self._real_time_processing_loop,
            daemon=True
        )
        self._processing_thread.start()
    
    def _real_time_processing_loop(self) -> None:
        """リアルタイム処理ループ"""
        while not self._stop_processing:
            try:
                # チャンクを取得（タイムアウト付き）
                try:
                    chunk = self._chunk_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # 処理開始時刻
                start_time = datetime.now()
                
                # 登録されたプロセッサで処理
                with self._processor_lock:
                    processors = list(self._chunk_processors)  # コピーで安全性確保
                
                for processor in processors:
                    try:
                        processor(chunk)
                    except Exception as e:
                        self.logger.error(f"Chunk processor error: {e}")
                
                # 処理時間計測
                processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                self._update_processing_metrics(processing_time_ms)
                
                # チャンクデータクリア（プライバシー保護）
                chunk.data = None
                self._processed_chunks += 1
                
                # 処理間隔調整
                time.sleep(self.config.processing_interval_ms / 1000.0)
                
            except Exception as e:
                self.logger.error(f"Real-time processing error: {e}")
                time.sleep(0.1)
    
    def _update_processing_metrics(self, processing_time_ms: int) -> None:
        """処理メトリクス更新"""
        # 移動平均更新
        if self._average_processing_time_ms == 0:
            self._average_processing_time_ms = processing_time_ms
        else:
            alpha = 0.1
            self._average_processing_time_ms = (
                alpha * processing_time_ms + 
                (1 - alpha) * self._average_processing_time_ms
            )
    
    def clear_buffer(self) -> None:
        """
        バッファクリア
        
        憲法IV: プライバシー保護のため完全削除
        """
        self.main_buffer.clear()
        
        # チャンクキューもクリア
        while not self._chunk_queue.empty():
            try:
                chunk = self._chunk_queue.get_nowait()
                chunk.data = None  # メモリクリア
            except queue.Empty:
                break
        
        self.logger.info("Audio buffer cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        バッファ統計取得
        
        Returns:
            Dict: 統計情報
        """
        buffer_stats = self.main_buffer.get_statistics()
        
        return {
            "buffer": buffer_stats,
            "processing": {
                "processed_chunks": self._processed_chunks,
                "dropped_chunks": self._dropped_chunks,
                "average_processing_time_ms": round(self._average_processing_time_ms, 2),
                "queue_size": self._chunk_queue.qsize(),
                "active_processors": len(self._chunk_processors)
            },
            "activity": {
                "last_activity": self._last_activity_time.isoformat(),
                "seconds_since_activity": (datetime.now() - self._last_activity_time).total_seconds()
            },
            "config": {
                "max_buffer_seconds": self.config.max_buffer_seconds,
                "sample_rate": self.config.sample_rate,
                "real_time_processing": self.config.enable_real_time_processing
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
        
        # バッファクリア
        self.clear_buffer()
        
        # プロセッサクリア
        with self._processor_lock:
            self._chunk_processors.clear()
        
        self.logger.info("Audio buffer manager cleaned up")


class SpeechDetector:
    """
    音声検出クラス
    
    Voice Activity Detection機能
    """
    
    def __init__(self, silence_threshold: float = 0.01, window_size: int = 512):
        self.silence_threshold = silence_threshold
        self.window_size = window_size
        self.logger = logging.getLogger(__name__)
    
    def calculate_energy(self, audio_data: np.ndarray) -> float:
        """
        音声エネルギーレベル計算
        
        Args:
            audio_data: 音声データ
            
        Returns:
            float: エネルギーレベル
        """
        try:
            # RMS計算
            return float(np.sqrt(np.mean(audio_data ** 2)))
        except Exception as e:
            self.logger.debug(f"Energy calculation error: {e}")
            return 0.0
    
    def detect_speech(self, audio_data: np.ndarray) -> bool:
        """
        音声検出
        
        Args:
            audio_data: 音声データ
            
        Returns:
            bool: 音声検出あり
        """
        try:
            energy = self.calculate_energy(audio_data)
            return energy > self.silence_threshold
        except Exception as e:
            self.logger.debug(f"Speech detection error: {e}")
            return False
    
    def get_speech_segments(self, audio_data: np.ndarray, 
                          sample_rate: int) -> List[Tuple[float, float]]:
        """
        音声セグメント検出
        
        Args:
            audio_data: 音声データ
            sample_rate: サンプリングレート
            
        Returns:
            List[Tuple[float, float]]: (開始時間, 終了時間)のリスト
        """
        try:
            segments = []
            in_speech = False
            speech_start = 0.0
            
            # ウィンドウごとに音声検出
            for i in range(0, len(audio_data), self.window_size):
                window = audio_data[i:i + self.window_size]
                current_time = i / sample_rate
                
                is_speech = self.detect_speech(window)
                
                if is_speech and not in_speech:
                    # 音声開始
                    in_speech = True
                    speech_start = current_time
                elif not is_speech and in_speech:
                    # 音声終了
                    in_speech = False
                    segments.append((speech_start, current_time))
            
            # 最後まで音声が続いていた場合
            if in_speech:
                segments.append((speech_start, len(audio_data) / sample_rate))
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Speech segmentation error: {e}")
            return []


def create_audio_buffer_manager(max_buffer_seconds: int = 3,
                              sample_rate: int = 16000,
                              enable_real_time: bool = True) -> AudioBufferManager:
    """
    音声バッファ管理インスタンス作成ヘルパー
    
    Args:
        max_buffer_seconds: 最大バッファ時間
        sample_rate: サンプリングレート
        enable_real_time: リアルタイム処理有効
        
    Returns:
        AudioBufferManager: 初期化済みインスタンス
    """
    config = AudioBufferConfig(
        max_buffer_seconds=max_buffer_seconds,
        sample_rate=sample_rate,
        enable_real_time_processing=enable_real_time
    )
    
    return AudioBufferManager(config)