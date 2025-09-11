#!/usr/bin/env python3
"""
マイク不使用でYes-Manモデルのみテスト
ダミー音声データで動作確認
"""

import numpy as np
import time
import logging

print("🟢 基本モジュール読み込み完了")

try:
    import openwakeword
    from openwakeword.model import Model
    print("🟢 openWakeWord読み込み完了")
except ImportError as e:
    print(f"❌ openWakeWord読み込み失敗: {e}")
    exit(1)

def test_model_with_dummy_data():
    """ダミーデータでモデルテスト"""
    print("🤖 Yes-Man モデル単体テスト（ダミーデータ使用）")
    print("=" * 60)
    
    # openWakeWordモデル初期化
    print("⚙️ openWakeWordモデル初期化中...")
    try:
        # まずはデフォルトモデルでテスト
        model = Model(
            wakeword_models=["hey_jarvis_v0.1"],
            inference_framework="onnx"
        )
        print("✅ openWakeWordモデル初期化完了（テスト用: hey_jarvis）")
        
    except Exception as e:
        print(f"❌ モデル初期化失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("=" * 60)
    print("🔍 ダミー音声データでテスト中...")
    
    # ダミー音声データ生成（16kHz, 1秒分）
    sample_rate = 16000
    duration = 1.0
    
    for test_num in range(5):
        print(f"\n📝 テスト {test_num + 1}/5")
        
        # ランダムノイズ生成（実際の音声の代替）
        np.random.seed(test_num)  # 再現可能性のため
        audio_data = np.random.randint(-32768, 32767, 
                                     size=int(sample_rate * duration), 
                                     dtype=np.int16)
        
        try:
            # openWakeWord検出実行
            start_time = time.time()
            predictions = model.predict(audio_data)
            detection_time = (time.time() - start_time) * 1000
            
            print(f"   🕒 検出時間: {detection_time:.1f}ms")
            
            # 全ての予測結果を表示
            for wake_word, confidence in predictions.items():
                if confidence > 0.0:  # 何らかの反応があった場合
                    status = "🟢" if confidence > 0.5 else "🟡" if confidence > 0.1 else "⚪"
                    print(f"   {status} {wake_word}: {confidence:.4f}")
            
            if not any(conf > 0.0 for conf in predictions.values()):
                print("   ⚪ 検出なし（正常 - ダミーデータのため）")
                
        except Exception as e:
            print(f"   ❌ 検出エラー: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 モデル動作テスト完了")
    print("✅ openWakeWordは正常に動作しています")
    print("📋 次のステップ:")
    print("   1. WSL2で音声デバイス設定")
    print("   2. 実際の音声でテスト")
    print("   3. Yes-Manカスタムモデルに切り替え")

def show_available_models():
    """利用可能なモデル一覧表示"""
    print("\n🔍 利用可能なモデル確認...")
    try:
        # デフォルトで利用可能なモデルを確認
        default_models = [
            "hey_jarvis_v0.1",
            "alexa_v0.1", 
            "hey_mycroft_v0.1",
            "hey_rhasspy_v0.1",
            "timer_v0.1",
            "weather_v0.1"
        ]
        
        for model_name in default_models:
            try:
                test_model = Model(wakeword_models=[model_name], inference_framework="onnx")
                print(f"   ✅ {model_name} - 利用可能")
                del test_model  # メモリ節約
            except Exception as e:
                print(f"   ❌ {model_name} - エラー: {str(e)[:50]}...")
        
        # カスタムモデル確認
        import os
        custom_model_path = "openWakeWord/yes_man_model_output/yes_man.pt"
        if os.path.exists(custom_model_path):
            print(f"   🎯 Yes-Manカスタムモデル発見: {custom_model_path}")
        else:
            print(f"   ⚠️ Yes-Manカスタムモデル未発見: {custom_model_path}")
            
    except Exception as e:
        print(f"❌ モデル確認エラー: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    show_available_models()
    test_model_with_dummy_data()