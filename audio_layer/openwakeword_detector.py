"""
openWakeWord-based wake word detection implementation for Yes-Man
"""

import logging
import threading
import time
from typing import Callable, Optional
import numpy as np
import pyaudio

import openwakeword
from openwakeword.model import Model


class OpenWakeWordDetector:
    """openWakeWordによる高性能ウェイクワード検出"""
    
    def __init__(self, 
                 confidence_threshold: float = 0.5,
                 keywords: Optional[list] = None):
        """
        Args:
            confidence_threshold: 検出閾値 (0.0-1.0)
            keywords: 使用するキーワード（None = 全て）
        """
        self.logger = logging.getLogger(__name__)
        self.confidence_threshold = confidence_threshold
        self.keywords = keywords
        
        # 音声設定
        self.sample_rate = 16000  # openWakeWordの要求仕様
        self.chunk_size = 1280    # 80ms @ 16kHz
        self.channels = 1
        
        # 状態管理
        self.is_listening = False
        self.model: Optional[Model] = None
        self.audio_stream: Optional[pyaudio.Stream] = None
        self.pyaudio: Optional[pyaudio.PyAudio] = None
        self.listen_thread: Optional[threading.Thread] = None
        
        self._initialize_model()
    
    def _initialize_model(self):
        """openWakeWordモデル初期化"""
        try:
            self.logger.info("Downloading openWakeWord models...")
            openwakeword.utils.download_models()
            
            # モデル初期化
            if self.keywords:
                # 特定キーワードのみ
                self.model = Model(wakeword_models=self.keywords)
                self.logger.info(f"Loaded specific models: {self.keywords}")
            else:
                # 全ての事前学習済みモデル
                self.model = Model()
                self.logger.info("Loaded all pre-trained models")
                
            self.logger.info(f"Available wake words: {list(self.model.prediction_buffer.keys())}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize openWakeWord model: {e}")
            raise
    
    def start_detection(self, callback: Callable[[str, float], None]):
        """ウェイクワード検出開始
        
        Args:
            callback: 検出時のコールバック関数 (wake_word: str, confidence: float)
        """
        if self.is_listening:
            self.logger.warning("Wake word detection already running")
            return
        
        self.detection_callback = callback
        
        try:
            # PyAudio初期化
            self.pyaudio = pyaudio.PyAudio()
            
            # 音声ストリーム開始
            self.audio_stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=None
            )
            
            self.is_listening = True
            
            # 検出スレッド開始
            self.listen_thread = threading.Thread(
                target=self._detection_loop,
                daemon=True
            )
            self.listen_thread.start()
            
            self.logger.info(f"openWakeWord detection started (threshold: {self.confidence_threshold})")
            
        except Exception as e:
            self.logger.error(f"Failed to start wake word detection: {e}")
            self.stop_detection()
            raise
    
    def _detection_loop(self):
        """メインの検出ループ"""
        self.logger.info("Wake word detection loop started")
        
        try:
            while self.is_listening:
                # 80ms分の音声データ読み取り
                audio_data = self.audio_stream.read(self.chunk_size, exception_on_overflow=False)
                
                # NumPy配列に変換
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # ウェイクワード検出実行
                predictions = self.model.predict(audio_array)
                
                # 検出結果をチェック
                for wake_word, confidence in predictions.items():
                    if confidence >= self.confidence_threshold:
                        self.logger.info(f"Wake word detected: '{wake_word}' (confidence: {confidence:.3f})")
                        
                        # コールバック実行
                        try:
                            self.detection_callback(wake_word, confidence)
                        except Exception as e:
                            self.logger.error(f"Error in detection callback: {e}")
                
                # CPU使用率制御
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error in detection loop: {e}")
        finally:
            self.logger.info("Wake word detection loop ended")
    
    def stop_detection(self):
        """ウェイクワード検出停止"""
        if not self.is_listening:
            return
        
        self.logger.info("Stopping wake word detection...")
        self.is_listening = False
        
        # スレッド終了待機
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread.join(timeout=2.0)
        
        # 音声ストリーム終了
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except Exception as e:
                self.logger.warning(f"Error closing audio stream: {e}")
            finally:
                self.audio_stream = None
        
        # PyAudio終了
        if self.pyaudio:
            try:
                self.pyaudio.terminate()
            except Exception as e:
                self.logger.warning(f"Error terminating PyAudio: {e}")
            finally:
                self.pyaudio = None
        
        self.logger.info("Wake word detection stopped")
    
    def get_available_models(self) -> dict:
        """利用可能なモデル一覧取得"""
        if self.model:
            return dict(self.model.prediction_buffer)
        return {}
    
    def set_threshold(self, threshold: float):
        """検出閾値変更"""
        if 0.0 <= threshold <= 1.0:
            self.confidence_threshold = threshold
            self.logger.info(f"Confidence threshold updated to {threshold}")
        else:
            raise ValueError("Threshold must be between 0.0 and 1.0")


class YesManWakeWordDetector(OpenWakeWordDetector):
    """Yes-Man専用のウェイクワード検出器"""
    
    def __init__(self, confidence_threshold: float = 0.6):
        """Yes-Man用の高精度設定で初期化"""
        
        # 全ての事前学習済みモデルを使用（まず利用可能なものを確認）
        super().__init__(
            confidence_threshold=confidence_threshold,
            keywords=None  # 全てのモデルを使用
        )
        
        self.logger.info("Yes-Man wake word detector initialized with fallback models")
        self.logger.info("Note: Using 'hey jarvis' or 'alexa' as temporary wake words until custom 'Yes-Man' model is trained")


def test_openwakeword():
    """openWakeWord テスト関数"""
    import signal
    import sys
    
    def signal_handler(signum, frame):
        print("\nStopping wake word detection...")
        detector.stop_detection()
        sys.exit(0)
    
    def on_wake_word_detected(wake_word: str, confidence: float):
        print(f"🎯 Wake word detected: '{wake_word}' (confidence: {confidence:.3f})")
    
    # シグナルハンドラー設定
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        print("Testing openWakeWord detection...")
        detector = YesManWakeWordDetector(confidence_threshold=0.5)
        print(f"Available models: {list(detector.get_available_models().keys())}")
        print("Say 'Hey Jarvis' or 'Alexa' to test detection...")
        print("Press Ctrl+C to stop")
        
        detector.start_detection(on_wake_word_detected)
        
        # メインスレッドを維持
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        if 'detector' in locals():
            detector.stop_detection()


if __name__ == "__main__":
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_openwakeword()