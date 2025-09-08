"""
ウェイクワード検出

憲法III: テストファーストに従い、contract テストを先に実装済み
spec.md FR-002: ウェイクワード「Yes-Man」検出
憲法V: パフォーマンス制約 - ウェイクワード検出<1秒
"""

import numpy as np
import logging
import asyncio
import threading
import time
from typing import Optional, Callable, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import deque
import re

from .whisper_integration import WhisperIntegration, WhisperConfig
from .database.models.agent_settings import AgentSettingsRepository


@dataclass 
class WakeWordConfig:
    """ウェイクワード検出設定"""
    wake_word: str = "Yes-Man"
    alternative_forms: List[str] = None  # ["イエスマン", "Yes Man", "Yesman"]
    confidence_threshold: float = 0.8  # data-model.md: 信頼度閾値
    detection_window_ms: int = 3000  # 検出ウィンドウ（ミリ秒）
    cooldown_ms: int = 2000  # 連続検出防止クールダウン
    max_audio_buffer_seconds: int = 3  # 憲法IV: 3秒循環バッファ
    sample_rate: int = 16000
    
    def __post_init__(self):
        if self.alternative_forms is None:
            self.alternative_forms = [
                "イエスマン",  # 日本語
                "Yes Man",     # スペース区切り
                "Yesman",      # 連続
                "yes-man",     # 小文字
                "YES-MAN"      # 大文字
            ]


class WakeWordDetector:
    """
    ウェイクワード検出クラス
    
    憲法IV: プライバシーファースト - 3秒循環バッファのみ
    憲法V: ウェイクワード検出<1秒制約
    """
    
    def __init__(self, config: Optional[WakeWordConfig] = None,
                 whisper: Optional[WhisperIntegration] = None):
        self.config = config or WakeWordConfig()
        self.logger = logging.getLogger(__name__)
        
        # Whisper統合
        if whisper:
            self.whisper = whisper
        else:
            whisper_config = WhisperConfig(
                model_size="small",  # ウェイクワード用は軽量モデル
                use_gpu=True,
                language="ja"
            )
            self.whisper = WhisperIntegration(whisper_config)
        
        # 循環音声バッファ（憲法IV: メモリ内のみ）
        self._audio_buffer = deque(
            maxlen=self.config.sample_rate * self.config.max_audio_buffer_seconds
        )
        self._buffer_lock = threading.Lock()
        
        # 検出状態
        self._is_listening = False
        self._last_detection_time: Optional[datetime] = None
        self._detection_callback: Optional[Callable] = None
        self._is_processing = False  # 音声認識処理中フラグ
        
        # パフォーマンスメトリクス
        self._detection_count = 0
        self._false_positive_count = 0
        self._average_detection_time_ms = 0.0
        
        # 設定読み込み
        self._load_settings()
    
    def _load_settings(self) -> None:
        """データベースから設定読み込み"""
        try:
            repo = AgentSettingsRepository()
            config = repo.get_yes_man_config()
            
            # 信頼度閾値更新
            if "wake_word_confidence_threshold" in config:
                self.config.confidence_threshold = config["wake_word_confidence_threshold"]
                self.logger.info(f"Confidence threshold set to {self.config.confidence_threshold}")
                
        except Exception as e:
            self.logger.warning(f"Failed to load settings, using defaults: {e}")
    
    def start_listening(self, callback: Callable[[float, str], None]) -> bool:
        """
        ウェイクワード検出開始
        
        Args:
            callback: 検出時コールバック (confidence, detected_text) -> None
            
        Returns:
            bool: 開始成功
        """
        try:
            # Whisper初期化確認
            if not self.whisper._is_initialized:
                if not self.whisper.initialize():
                    self.logger.error("Failed to initialize Whisper")
                    return False
            
            self._detection_callback = callback
            self._is_listening = True
            
            # 検出スレッド開始
            detection_thread = threading.Thread(
                target=self._detection_loop,
                daemon=True
            )
            detection_thread.start()
            
            self.logger.info(f"Wake word detection started for '{self.config.wake_word}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start wake word detection: {e}")
            return False
    
    def stop_listening(self) -> None:
        """ウェイクワード検出停止"""
        self._is_listening = False
        self.logger.info("Wake word detection stopped")
    
    def process_audio_chunk(self, audio_chunk: np.ndarray) -> None:
        """
        音声チャンク処理
        
        憲法IV: 循環バッファでプライバシー保護
        
        Args:
            audio_chunk: 音声データチャンク
        """
        with self._buffer_lock:
            # 循環バッファに追加（古いデータは自動削除）
            self._audio_buffer.extend(audio_chunk)
    
    def _detection_loop(self) -> None:
        """検出ループ（バックグラウンドスレッド）"""
        while self._is_listening:
            try:
                # クールダウンチェック
                if self._is_in_cooldown():
                    time.sleep(0.1)
                    continue
                
                # 処理中の場合はスキップ
                if self._is_processing:
                    time.sleep(0.1)
                    continue
                
                # バッファから音声データ取得
                audio_data = self._get_buffer_snapshot()
                if len(audio_data) < self.config.sample_rate:  # 最低1秒必要
                    time.sleep(0.1)
                    continue
                
                # 音声活動検出（無音かどうかチェック）
                if not self._has_voice_activity(audio_data):
                    time.sleep(0.1)
                    continue
                
                # ウェイクワード検出実行
                self._is_processing = True
                start_time = datetime.now()
                confidence, detected_text = self._detect_wake_word(audio_data)
                detection_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                self._is_processing = False
                
                # 検出結果をログ表示（デバッグ用）
                if detected_text and detected_text.strip():
                    self.logger.debug(f"Detected: '{detected_text}' (confidence: {confidence:.2f})")
                
                # パフォーマンスメトリクス更新
                self._update_metrics(detection_time_ms, confidence)
                
                # 閾値チェック
                if confidence >= self.config.confidence_threshold:
                    self.logger.info(
                        f"Wake word detected: '{detected_text}' "
                        f"(confidence: {confidence:.2f}, time: {detection_time_ms}ms)"
                    )
                    
                    # コールバック実行
                    if self._detection_callback:
                        self._detection_callback(confidence, detected_text)
                    
                    # 検出時刻記録（クールダウン用）
                    self._last_detection_time = datetime.now()
                    
                    # バッファクリア（プライバシー保護）
                    self._clear_buffer()
                
                # パフォーマンス制約チェック
                if detection_time_ms > 1000:
                    self.logger.warning(
                        f"Wake word detection exceeded 1s constraint: {detection_time_ms}ms"
                    )
                
                # CPU負荷軽減のための待機
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Detection loop error: {e}")
                self._is_processing = False  # エラー時もフラグリセット
                time.sleep(1.0)
    
    def _detect_wake_word(self, audio_data: np.ndarray) -> Tuple[float, str]:
        """
        ウェイクワード検出実行
        
        Returns:
            Tuple[float, str]: (信頼度, 検出テキスト)
        """
        try:
            # Whisper音声認識
            result = self.whisper.transcribe(audio_data, language="ja")
            text = result.get("text", "").strip()
            
            if not text:
                return 0.0, ""
            
            # ウェイクワードマッチング
            confidence = self._calculate_wake_word_confidence(text)
            
            return confidence, text
            
        except Exception as e:
            import traceback
            self.logger.error(f"Wake word detection error: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return 0.0, ""
    
    def _calculate_wake_word_confidence(self, text: str) -> float:
        """
        ウェイクワード信頼度計算
        
        Args:
            text: 認識テキスト
            
        Returns:
            float: 0.0-1.0の信頼度
        """
        text_lower = text.lower().replace(" ", "").replace("-", "")
        wake_word_lower = self.config.wake_word.lower().replace(" ", "").replace("-", "")
        
        # 完全一致
        if wake_word_lower in text_lower:
            return 1.0
        
        # 代替形式チェック
        for alt_form in self.config.alternative_forms:
            alt_lower = alt_form.lower().replace(" ", "").replace("-", "")
            if alt_lower in text_lower:
                return 0.9
        
        # 部分一致スコア計算
        # "yes"と"man"が両方含まれる場合
        if "yes" in text_lower and ("man" in text_lower or "マン" in text):
            return 0.8
        
        # レーベンシュタイン距離による類似度
        similarity = self._calculate_similarity(text_lower, wake_word_lower)
        if similarity > 0.7:
            return similarity
        
        return 0.0
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        文字列類似度計算（簡易版）
        
        Returns:
            float: 0.0-1.0の類似度
        """
        # 共通文字数ベースの簡易類似度
        common_chars = sum(1 for c in text2 if c in text1)
        max_len = max(len(text1), len(text2))
        
        if max_len == 0:
            return 0.0
        
        return common_chars / max_len
    
    def _is_in_cooldown(self) -> bool:
        """クールダウン中判定"""
        if not self._last_detection_time:
            return False
        
        elapsed_ms = (datetime.now() - self._last_detection_time).total_seconds() * 1000
        return elapsed_ms < self.config.cooldown_ms
    
    def _get_buffer_snapshot(self) -> np.ndarray:
        """
        バッファスナップショット取得
        
        憲法IV: コピーを返してメモリ安全性確保
        """
        with self._buffer_lock:
            return np.array(list(self._audio_buffer), dtype=np.float32)
    
    def _clear_buffer(self) -> None:
        """
        バッファクリア
        
        憲法IV: プライバシー保護のため検出後即削除
        """
        with self._buffer_lock:
            self._audio_buffer.clear()
    
    def _has_voice_activity(self, audio_data: np.ndarray, threshold: float = 0.01) -> bool:
        """
        音声活動検出
        
        Args:
            audio_data: 音声データ
            threshold: 音声レベル閾値
            
        Returns:
            bool: 音声活動があるか
        """
        if len(audio_data) == 0:
            return False
        
        # RMS（実効値）計算
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        # 閾値と比較
        has_activity = rms > threshold
        
        if has_activity:
            self.logger.debug(f"Voice activity detected: RMS={rms:.4f} (threshold={threshold:.4f})")
        
        return has_activity
    
    def _update_metrics(self, detection_time_ms: int, confidence: float) -> None:
        """パフォーマンスメトリクス更新"""
        self._detection_count += 1
        
        # 移動平均更新
        alpha = 0.1
        if self._average_detection_time_ms == 0:
            self._average_detection_time_ms = detection_time_ms
        else:
            self._average_detection_time_ms = (
                alpha * detection_time_ms + 
                (1 - alpha) * self._average_detection_time_ms
            )
        
        # 偽陽性カウント（低信頼度での誤検出）
        if 0.5 < confidence < self.config.confidence_threshold:
            self._false_positive_count += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        検出統計取得
        
        Returns:
            Dict: 検出統計情報
        """
        return {
            "wake_word": self.config.wake_word,
            "confidence_threshold": self.config.confidence_threshold,
            "detection_count": self._detection_count,
            "false_positive_count": self._false_positive_count,
            "average_detection_time_ms": round(self._average_detection_time_ms, 2),
            "meets_performance_constraint": self._average_detection_time_ms < 1000,
            "is_listening": self._is_listening,
            "buffer_size_seconds": self.config.max_audio_buffer_seconds
        }
    
    async def detect_wake_word_async(self, audio_data: np.ndarray) -> Tuple[float, str]:
        """
        非同期ウェイクワード検出
        
        Args:
            audio_data: 音声データ
            
        Returns:
            Tuple[float, str]: (信頼度, 検出テキスト)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._detect_wake_word,
            audio_data
        )
    
    def cleanup(self) -> None:
        """
        リソースクリーンアップ
        
        憲法IV: メモリ完全クリア
        """
        self.stop_listening()
        self._clear_buffer()
        
        if self.whisper:
            self.whisper.cleanup()
        
        self.logger.info("Wake word detector cleaned up")