#!/usr/bin/env python3
"""
Yes-Man ウェイクワード検出デバッグ版

段階的に初期化してどこで止まるか確認
"""

import sys
print("🟢 Python起動完了")

try:
    import logging
    print("🟢 logging インポート完了")

    import numpy as np
    print("🟢 numpy インポート完了")

    import pyaudio
    print("🟢 pyaudio インポート完了")

    print("🔄 audio_layer モジュールインポート中...")
    from audio_layer.wake_word_detector import WakeWordDetector, WakeWordConfig
    print("🟢 WakeWordDetector インポート完了")

except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)

def debug_initialization():
    """段階的初期化デバッグ"""
    print("\n" + "="*50)
    print("🔧 デバッグ: 段階的初期化開始")
    print("="*50)
    
    try:
        print("📝 Step 1: ログ設定...")
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        print("✅ ログ設定完了")
        
        print("📝 Step 2: 設定作成...")
        config = WakeWordConfig(
            use_openwakeword=True,
            openwakeword_threshold=0.5,
            confidence_threshold=0.5
        )
        print("✅ 設定作成完了")
        
        print("📝 Step 3: WakeWordDetector初期化...")
        print("   ⏳ これに時間がかかる可能性があります...")
        detector = WakeWordDetector(config)
        print("✅ WakeWordDetector初期化完了")
        
        print("📝 Step 4: PyAudio初期化...")
        audio = pyaudio.PyAudio()
        print("✅ PyAudio初期化完了")
        
        print("📝 Step 5: マイク設定確認...")
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        print("✅ マイクストリーム作成完了")
        
        # クリーンアップ
        stream.close()
        audio.terminate()
        
        print("\n🎉 全ての初期化が完了しました！")
        print("メインのテストスクリプトが動作するはずです。")
        
    except Exception as e:
        import traceback
        print(f"\n❌ エラーが発生: {e}")
        print(f"詳細: {traceback.format_exc()}")
        return False
        
    return True

if __name__ == "__main__":
    print("🤖 Yes-Man ウェイクワードデバッグ開始")
    success = debug_initialization()
    
    if success:
        print("\n✅ デバッグ完了 - メインテストを実行してください:")
        print("uv run test_wake_word.py")
    else:
        print("\n❌ 問題が検出されました")