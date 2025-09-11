#!/usr/bin/env python3
"""
シンプルなYes-Man ウェイクワード検出テスト
Whisper不使用、openWakeWordのみ
"""

import logging
import numpy as np
import pyaudio
import time

print("🟢 基本モジュール読み込み完了")

try:
    import openwakeword
    from openwakeword.model import Model
    print("🟢 openWakeWord読み込み完了")
except ImportError as e:
    print(f"❌ openWakeWord読み込み失敗: {e}")
    exit(1)

def test_simple_wake_word():
    """シンプルなウェイクワード検出テスト"""
    print("🤖 Yes-Man シンプルウェイクワード検出テスト")
    print("=" * 50)
    
    # openWakeWordモデル初期化
    print("⚙️ openWakeWordモデル初期化中...")
    try:
        # カスタムモデルパス
        model_path = "openWakeWord/yes_man_model_output/yes_man.pt"
        
        # テスト：まずはデフォルトモデルで動作確認
        model = Model(
            wakeword_models=["hey_jarvis_v0.1"],
            inference_framework="onnx"
        )
        print("✅ openWakeWordモデル初期化完了（テスト用: hey_jarvis）")
        
    except Exception as e:
        print(f"❌ モデル初期化失敗: {e}")
        return
    
    # 音声設定
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    
    print("🎤 音声入力初期化中...")
    audio = pyaudio.PyAudio()
    
    try:
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        print("✅ 音声ストリーム初期化完了")
        
        print("=" * 50)
        print("📢 マイクに向かって「Hey Jarvis」と話してください（テスト用）")
        print("🔴 Ctrl+C で終了")
        print("🟢 検出システム稼働中...")
        print("=" * 50)
        
        while True:
            try:
                # 音声データ読み取り（約1秒分）
                frames = []
                for _ in range(0, int(RATE / CHUNK)):
                    data = stream.read(CHUNK)
                    frames.append(data)
                
                # numpy配列に変換
                audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
                
                # openWakeWord検出
                start_time = time.time()
                predictions = model.predict(audio_data)
                detection_time = (time.time() - start_time) * 1000
                
                # 結果確認
                for wake_word, confidence in predictions.items():
                    if confidence > 0.5:  # 閾値
                        print(f"✅ ウェイクワード検出!")
                        print(f"   ワード: {wake_word}")
                        print(f"   信頼度: {confidence:.3f}")
                        print(f"   検出時間: {detection_time:.1f}ms")
                        print("-" * 40)
                    elif confidence > 0.1:  # 低信頼度も表示
                        print(f"🟡 {wake_word}: {confidence:.3f}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ 検出エラー: {e}")
                time.sleep(1)
    
    finally:
        print("\n🔴 テスト終了")
        stream.stop_stream()
        stream.close()
        audio.terminate()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_simple_wake_word()