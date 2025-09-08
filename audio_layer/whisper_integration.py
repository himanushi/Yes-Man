"""
Whisper.cpp統合

憲法III: テストファーストに従い、contract テストを先に実装済み
research.md: mediumモデル + CUDA最適化決定
憲法V: パフォーマンス制約 - ウェイクワード検出<1秒
"""

import numpy as np
import logging
import asyncio
from typing import Optional, Tuple, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import queue
import threading

import whisper


@dataclass
class WhisperConfig:
    """Whisper.cpp設定"""
    model_size: str = "medium"  # research.md決定
    model_path: Optional[str] = None
    language: str = "ja"  # 日本語メイン
    use_gpu: bool = True  # CUDA最適化
    n_threads: int = 4
    n_processors: int = 1
    beam_size: int = 5
    best_of: int = 5
    temperature: float = 0.0
    word_timestamps: bool = True
    initial_prompt: Optional[str] = None
    vad_threshold: float = 0.6  # Voice Activity Detection閾値
    sample_rate: int = 16000
    chunk_length: int = 30  # 秒


class WhisperIntegration:
    """
    Whisper.cpp音声認識統合クラス
    
    憲法IV: プライバシーファースト - メモリ内処理のみ
    憲法V: パフォーマンス制約対応
    """
    
    def __init__(self, config: Optional[WhisperConfig] = None):
        self.config = config or WhisperConfig()
        self.logger = logging.getLogger(__name__)
        self.model: Optional[Whisper] = None
        self._is_initialized = False
        self._processing_lock = threading.Lock()
        
        # パフォーマンスメトリクス
        self._last_inference_time_ms: Optional[int] = None
        self._total_inferences: int = 0
        self._average_inference_time_ms: float = 0.0
    
    def initialize(self) -> bool:
        """
        Whisperモデル初期化
        
        Returns:
            bool: 初期化成功
        """
        try:
            
            self.logger.info(f"Initializing Whisper model: {self.config.model_size}")
            
            # whisperパッケージを使用してモデルロード
            # GPU利用可能性をチェックしてからデバイス決定
            import torch
            use_cuda = self.config.use_gpu and torch.cuda.is_available()
            device = "cuda" if use_cuda else "cpu"
            
            self.logger.info(f"Loading Whisper model on device: {device}")
            self.model = whisper.load_model(self.config.model_size, device=device)
            
            # GPU利用設定
            if self.config.use_gpu:
                self.logger.info("GPU acceleration enabled")
            
            self._is_initialized = True
            self.logger.info("Whisper model initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Whisper: {e}")
            return False
    
    def transcribe(self, audio_data: np.ndarray, 
                  language: Optional[str] = None) -> Dict[str, Any]:
        """
        音声データをテキストに変換
        
        Args:
            audio_data: 音声データ (16kHz, mono, float32)
            language: 言語コード (None時は設定値使用)
            
        Returns:
            Dict: {
                "text": str,
                "segments": List[Dict],
                "language": str,
                "confidence": float,
                "processing_time_ms": int
            }
        """
        if not self._is_initialized or not self.model:
            raise RuntimeError("Whisper model not initialized")
        
        start_time = datetime.now()
        audio_length = len(audio_data) / self.config.sample_rate
        
        self.logger.info(f"Starting speech recognition ({audio_length:.1f}s audio)")
        
        try:
            with self._processing_lock:
                # 音声データ正規化
                audio_data = self._normalize_audio(audio_data)
                
                # Whisper実行
                result = self.model.transcribe(
                    audio_data,
                    language=language or self.config.language,
                    word_timestamps=self.config.word_timestamps,
                    initial_prompt=self.config.initial_prompt
                )
                
                # 処理時間計測
                processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                self._update_performance_metrics(processing_time_ms)
                
                # 認識結果のログ表示
                recognized_text = result.get("text", "").strip()
                confidence = self._calculate_confidence(result)
                self.logger.info(f"Speech recognition completed ({processing_time_ms}ms): '{recognized_text}' (confidence: {confidence:.2f})")
                
                # 結果構築
                return {
                    "text": result.get("text", "").strip(),
                    "segments": result.get("segments", []),
                    "language": result.get("language", self.config.language),
                    "confidence": self._calculate_confidence(result),
                    "processing_time_ms": processing_time_ms
                }
                
        except Exception as e:
            self.logger.error(f"Transcription failed: {e}")
            return {
                "text": "",
                "segments": [],
                "language": self.config.language,
                "confidence": 0.0,
                "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                "error": str(e)
            }
    
    async def transcribe_async(self, audio_data: np.ndarray,
                              language: Optional[str] = None) -> Dict[str, Any]:
        """
        非同期音声認識
        
        憲法V: パフォーマンス最適化のため非同期処理
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.transcribe,
            audio_data,
            language
        )
    
    def transcribe_stream(self, audio_stream: queue.Queue,
                         callback: Callable[[str], None],
                         language: Optional[str] = None) -> None:
        """
        ストリーミング音声認識
        
        Args:
            audio_stream: 音声データキュー
            callback: 認識結果コールバック
            language: 言語コード
        """
        buffer = []
        buffer_duration_ms = 0
        chunk_duration_ms = 1000  # 1秒チャンク
        
        while True:
            try:
                # キューから音声データ取得
                audio_chunk = audio_stream.get(timeout=1.0)
                
                if audio_chunk is None:  # 終了シグナル
                    break
                
                buffer.append(audio_chunk)
                buffer_duration_ms += len(audio_chunk) * 1000 // self.config.sample_rate
                
                # チャンクサイズに達したら認識実行
                if buffer_duration_ms >= chunk_duration_ms:
                    audio_data = np.concatenate(buffer)
                    result = self.transcribe(audio_data, language)
                    
                    if result["text"]:
                        callback(result["text"])
                    
                    # バッファクリア
                    buffer = []
                    buffer_duration_ms = 0
                    
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Stream transcription error: {e}")
    
    def detect_language(self, audio_data: np.ndarray) -> Tuple[str, float]:
        """
        音声言語検出
        
        Returns:
            Tuple[str, float]: (言語コード, 信頼度)
        """
        if not self._is_initialized or not self.model:
            raise RuntimeError("Whisper model not initialized")
        
        try:
            # 言語検出モードで実行
            audio_normalized = self._normalize_audio(audio_data)
            
            # Whisper使用
            result = self.model.transcribe(
                audio_normalized,
                language=None  # 自動検出
            )
            language = result.get("language", "unknown")
            confidence = self._calculate_confidence(result)
            
            return language, confidence
            
        except Exception as e:
            self.logger.error(f"Language detection failed: {e}")
            return "unknown", 0.0
    
    def _normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """
        音声データ正規化
        
        憲法IV: メモリ内処理のみ、ディスク書き込み禁止
        """
        # float32変換
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # 正規化 (-1.0 to 1.0)
        if audio_data.dtype == np.int16:
            audio_data = audio_data / 32768.0
        elif audio_data.dtype == np.int32:
            audio_data = audio_data / 2147483648.0
        
        # モノラル変換
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # クリッピング
        audio_data = np.clip(audio_data, -1.0, 1.0)
        
        return audio_data
    
    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """
        認識信頼度計算
        
        Returns:
            float: 0.0-1.0の信頼度
        """
        segments = result.get("segments", [])
        if not segments:
            return 0.0
        
        # セグメントの平均確率を信頼度とする
        confidences = []
        for segment in segments:
            if "probability" in segment:
                confidences.append(segment["probability"])
            elif "avg_logprob" in segment:
                # logprobから確率に変換
                prob = np.exp(segment["avg_logprob"])
                confidences.append(min(1.0, max(0.0, prob)))
        
        if confidences:
            return sum(confidences) / len(confidences)
        return 0.5  # デフォルト信頼度
    
    def _update_performance_metrics(self, processing_time_ms: int) -> None:
        """
        パフォーマンスメトリクス更新
        
        憲法V: パフォーマンス監視
        """
        self._last_inference_time_ms = processing_time_ms
        self._total_inferences += 1
        
        # 移動平均更新
        if self._average_inference_time_ms == 0:
            self._average_inference_time_ms = processing_time_ms
        else:
            alpha = 0.1  # 平滑化係数
            self._average_inference_time_ms = (
                alpha * processing_time_ms + 
                (1 - alpha) * self._average_inference_time_ms
            )
        
        # パフォーマンス警告
        if processing_time_ms > 1000:  # 1秒超過
            self.logger.warning(
                f"Whisper inference exceeded 1s constraint: {processing_time_ms}ms"
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        パフォーマンス統計取得
        
        Returns:
            Dict: パフォーマンスメトリクス
        """
        return {
            "last_inference_time_ms": self._last_inference_time_ms,
            "average_inference_time_ms": round(self._average_inference_time_ms, 2),
            "total_inferences": self._total_inferences,
            "model_size": self.config.model_size,
            "use_gpu": self.config.use_gpu,
            "meets_constraint": self._average_inference_time_ms < 1000  # 憲法V: <1秒
        }
    
    def cleanup(self) -> None:
        """
        リソースクリーンアップ
        
        憲法IV: メモリ完全クリア
        """
        if self.model:
            del self.model
            self.model = None
        
        self._is_initialized = False
        self.logger.info("Whisper resources cleaned up")


def create_whisper_instance(model_size: str = "medium",
                           use_gpu: bool = True) -> WhisperIntegration:
    """
    Whisperインスタンス作成ヘルパー
    
    Args:
        model_size: モデルサイズ (tiny/small/medium/large)
        use_gpu: GPU使用フラグ
        
    Returns:
        WhisperIntegration: 初期化済みインスタンス
    """
    config = WhisperConfig(
        model_size=model_size,
        use_gpu=use_gpu
    )
    
    whisper = WhisperIntegration(config)
    
    if whisper.initialize():
        return whisper
    else:
        raise RuntimeError("Failed to create Whisper instance")