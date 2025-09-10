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
import queue
from typing import Optional, Callable, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import deque
import re
import os
import json

from .whisper_integration import WhisperIntegration, WhisperConfig
from .database.models.agent_settings import AgentSettingsRepository

try:
    import openwakeword
    from openwakeword.model import Model
    OPENWAKEWORD_AVAILABLE = True
except ImportError:
    OPENWAKEWORD_AVAILABLE = False


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
    
    # openWakeWord設定
    use_openwakeword: bool = True  # openWakeWordモデルを使用
    openwakeword_model_path: str = "openWakeWord/yes_man_model_output/yes_man.pt"
    openwakeword_threshold: float = 0.5  # openWakeWord検出閾値
    
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
        
        # openWakeWordモデル初期化
        self.oww_model = None
        if self.config.use_openwakeword and OPENWAKEWORD_AVAILABLE:
            self._init_openwakeword()
        
        # Whisper統合（フォールバック用）
        if whisper:
            self.whisper = whisper
        else:
            whisper_config = WhisperConfig(
                model_size="small",  # ウェイクワード用は軽量モデル
                use_gpu=True,
                language="ja"
            )
            self.whisper = WhisperIntegration(whisper_config)
        
        # Queue + Threading アーキテクチャ
        self._audio_queue = queue.Queue(maxsize=10)  # 最大10チャンク
        self._processing_thread: Optional[threading.Thread] = None
        
        # 検出状態
        self._is_listening = False
        self._last_detection_time: Optional[datetime] = None
        self._detection_callback: Optional[Callable] = None
        
        # 音声蓄積バッファ（連続音声用）
        self._accumulated_audio = []
        self._last_activity_time: Optional[datetime] = None
        self._silence_threshold_seconds = 1.0  # 1秒無音で区切り
        
        # パフォーマンスメトリクス
        self._detection_count = 0
        self._false_positive_count = 0
        self._average_detection_time_ms = 0.0
        
        # 設定読み込み
        self._load_settings()
    
    def _init_openwakeword(self) -> None:
        """openWakeWordモデル初期化"""
        try:
            model_path = self.config.openwakeword_model_path
            if not os.path.exists(model_path):
                self.logger.warning(f"openWakeWord model not found: {model_path}")
                return
            
            # Yes-Manカスタムモデルのロード
            if os.path.exists(model_path):
                # カスタムモデル辞書を作成
                custom_model_paths = {"yes_man": model_path}
                self.oww_model = Model(
                    wakeword_models=["yes_man"],
                    custom_model_paths=custom_model_paths,
                    inference_framework="onnx"
                )
                self.logger.info(f"Yes-Man custom model loaded: {model_path}")
            else:
                # フォールバック：デフォルトモデル
                self.oww_model = Model(
                    wakeword_models=["hey_jarvis_v0.1"],
                    inference_framework="onnx"
                )
                self.logger.warning("Using fallback model: hey_jarvis")
            self.logger.info("openWakeWord initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize openWakeWord: {e}")
            self.oww_model = None
    
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
            
            # Queue処理スレッド開始
            self._processing_thread = threading.Thread(
                target=self._processing_loop,
                daemon=True
            )
            self._processing_thread.start()
            
            self.logger.info(f"Wake word detection started for '{self.config.wake_word}' (Queue+Threading architecture)")
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
        音声チャンク処理 - Queueに送信
        
        憲法IV: プライバシー保護
        
        Args:
            audio_chunk: 音声データチャンク
        """
        if not self._is_listening:
            return
            
        try:
            # Queueに音声チャンクを送信（ノンブロッキング）
            self._audio_queue.put_nowait(audio_chunk)
        except queue.Full:
            # Queueが満杯の場合は古いデータを破棄（正常動作）
            try:
                self._audio_queue.get_nowait()
                self._audio_queue.put_nowait(audio_chunk)
            except queue.Empty:
                pass
    
    def _processing_loop(self) -> None:
        """Queue処理ループ（バックグラウンドスレッド）"""
        while self._is_listening:
            try:
                # Queueから音声チャンク取得（タイムアウト付き）
                try:
                    audio_chunk = self._audio_queue.get(timeout=0.5)
                except queue.Empty:
                    # 無音期間の処理
                    self._check_silence_timeout()
                    continue
                
                # 音声活動検出
                has_activity = self._has_voice_activity(audio_chunk)
                current_time = datetime.now()
                
                if has_activity:
                    # 音声活動あり：バッファに蓄積
                    self._accumulated_audio.append(audio_chunk)
                    self._last_activity_time = current_time
                    
                    # バッファサイズ制限（憲法IV: プライバシー保護）
                    max_chunks = int(self.config.max_audio_buffer_seconds * 
                                   self.config.sample_rate / len(audio_chunk))
                    if len(self._accumulated_audio) > max_chunks:
                        self._accumulated_audio.pop(0)  # 古いチャンクを削除
                        
                else:
                    # 音声活動なし：無音期間
                    if (self._last_activity_time and 
                        (current_time - self._last_activity_time).total_seconds() > self._silence_threshold_seconds):
                        # 無音期間が閾値を超えた：蓄積音声を処理
                        self._process_accumulated_audio()
                
                # Queueタスク完了
                self._audio_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Processing loop error: {e}")
                time.sleep(1.0)
    
    def _detect_wake_word(self, audio_data: np.ndarray) -> Tuple[float, str]:
        """
        ウェイクワード検出実行
        
        Returns:
            Tuple[float, str]: (信頼度, 検出テキスト)
        """
        try:
            # openWakeWord優先検出
            if self.oww_model is not None:
                return self._detect_with_openwakeword(audio_data)
            
            # Whisperフォールバック
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
    
    def _detect_with_openwakeword(self, audio_data: np.ndarray) -> Tuple[float, str]:
        """
        openWakeWordによる検出
        
        Returns:
            Tuple[float, str]: (信頼度, 検出テキスト)
        """
        try:
            # 音声データを16kHzに変換（必要に応じて）
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)  # モノラル変換
            
            # openWakeWordは16bit intを期待
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            # 検出実行
            prediction = self.oww_model.predict(audio_data)
            
            # Yes-Manモデルの信頼度を取得
            confidence = prediction.get("yes_man", 0.0)
            
            # フォールバック：hey_jarvis
            if confidence == 0.0:
                confidence = prediction.get("hey_jarvis_v0.1", 0.0)
            
            if confidence > self.config.openwakeword_threshold:
                return confidence, "Yes-Man"  # 検出時はYes-Manと報告
            
            return confidence, ""
            
        except Exception as e:
            self.logger.error(f"openWakeWord detection error: {e}")
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
    
    def _check_silence_timeout(self) -> None:
        """無音期間タイムアウトチェック"""
        if (self._last_activity_time and 
            (datetime.now() - self._last_activity_time).total_seconds() > self._silence_threshold_seconds):
            self._process_accumulated_audio()
    
    def _process_accumulated_audio(self) -> None:
        """蓄積された音声データを処理"""
        if not self._accumulated_audio:
            return
        
        # クールダウンチェック
        if self._is_in_cooldown():
            self._clear_accumulated_audio()
            return
        
        # 音声データ結合
        audio_data = np.concatenate(self._accumulated_audio)
        
        # 最小長チェック
        if len(audio_data) < self.config.sample_rate:  # 最低1秒必要
            self._clear_accumulated_audio()
            return
        
        try:
            # ウェイクワード検出実行
            start_time = datetime.now()
            confidence, detected_text = self._detect_wake_word(audio_data)
            detection_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
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
                    # asyncコールバックの場合は別スレッドで実行
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        loop.create_task(self._detection_callback(confidence, detected_text))
                    except RuntimeError:
                        # イベントループがない場合は新しいループで実行
                        asyncio.run(self._detection_callback(confidence, detected_text))
                
                # 検出時刻記録（クールダウン用）
                self._last_detection_time = datetime.now()
            
            # パフォーマンス制約チェック（2秒超過時のみ警告）
            if detection_time_ms > 2000:
                self.logger.warning(
                    f"Wake word detection exceeded 2s: {detection_time_ms}ms"
                )
            
        except Exception as e:
            self.logger.error(f"Wake word processing error: {e}")
        
        finally:
            # バッファクリア（プライバシー保護）
            self._clear_accumulated_audio()
    
    def _clear_accumulated_audio(self) -> None:
        """蓄積音声バッファクリア"""
        self._accumulated_audio.clear()
        self._last_activity_time = None
    
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
        
        # Queue内の残りアイテムをクリア
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        
        # 蓄積音声クリア
        self._clear_accumulated_audio()
        
        if self.whisper:
            self.whisper.cleanup()
        
        self.logger.info("Wake word detector cleaned up")