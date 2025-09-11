#!/usr/bin/env python3
"""
Yes-Man ウェイクワード検出テスト

使用方法:
1. マイクに向かって「Hey Jarvis」と話してください（テスト用）
2. 将来的に「Yes Man」モデルが完成したら置き換え予定
"""

import logging
import numpy as np
import pyaudio
import time
from audio_layer.wake_word_detector import WakeWordDetector, WakeWordConfig

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_wake_word_detection():
    """ウェイクワード検出テスト"""
    print("🤖 Yes-Man ウェイクワード検出テスト開始")
    print("=" * 50)
    
    # 設定
    config = WakeWordConfig(
        use_openwakeword=True,
        openwakeword_threshold=0.5,
        confidence_threshold=0.5
    )
    
    print("⚙️ 検出器初期化中...")
    # 検出器初期化
    detector = WakeWordDetector(config)
    
    print("=" * 50)
    print("📢 マイクに向かって「Yes Man」と話してください")
    print("🔄 フォールバック: 「Hey Jarvis」でもテスト可能")
    print("🔴 Ctrl+C で終了")
    print("=" * 50)
    
    # 音声入力設定
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    
    audio = pyaudio.PyAudio()
    
    try:
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        print("🎤 音声入力開始...")
        print("🟢 検出システム稼働中...")
        
        while True:
            try:
                # 音声データ読み取り（約1秒分）
                frames = []
                for _ in range(0, int(RATE / CHUNK)):
                    data = stream.read(CHUNK)
                    frames.append(data)
                
                # numpy配列に変換
                audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
                
                # ウェイクワード検出
                start_time = time.time()
                confidence, text = detector._detect_wake_word(audio_data)
                detection_time = (time.time() - start_time) * 1000
                
                if confidence > config.confidence_threshold:
                    print(f"✅ ウェイクワード検出!")
                    print(f"   信頼度: {confidence:.3f}")
                    print(f"   テキスト: {text}")
                    print(f"   検出時間: {detection_time:.1f}ms")
                    print("-" * 40)
                else:
                    # 低い信頼度も表示（デバッグ用）
                    if confidence > 0.1:
                        print(f"🟡 検出: {confidence:.3f} | {text[:20]}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ エラー: {e}")
                time.sleep(1)
    
    finally:
        print("\n🔴 テスト終了")
        stream.stop_stream()
        stream.close()
        audio.terminate()

if __name__ == "__main__":
    setup_logging()
    test_wake_word_detection()