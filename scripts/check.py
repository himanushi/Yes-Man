#!/usr/bin/env python3
"""
Yes-Man動作確認スクリプト
"""

import sys
import traceback
import requests


def check_voicevox():
    """VoiceVox接続確認"""
    print("=== VoiceVox接続確認 ===")
    try:
        response = requests.get('http://localhost:50021/version', timeout=5)
        if response.status_code == 200:
            print("VoiceVox: OK")
            print(f"バージョン: {response.json()}")
        else:
            print(f"VoiceVox: NG (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"VoiceVox未起動: {e}")
        return False
    return True


def check_database():
    """データベース初期化確認"""
    print("=== データベース初期化確認 ===")
    try:
        from audio_layer.database.init_db import init_database
        init_database()
        print("データベース初期化: OK")
        return True
    except Exception as e:
        print(f"データベースエラー: {e}")
        traceback.print_exc()
        return False


def check_audio():
    """音声バッファ動作確認"""
    print("=== 音声バッファ動作確認 ===")
    try:
        from audio_layer.audio_buffer import AudioBufferManager
        import numpy as np
        
        buffer_manager = AudioBufferManager()
        test_audio = np.random.random(1600).astype(np.float32)  # 0.1秒分
        result = buffer_manager.add_audio_data(test_audio)
        
        if result:
            stats = buffer_manager.get_statistics()
            print(f"音声バッファ: OK ({stats['buffer']['current_size']} サンプル)")
        else:
            print("音声バッファ: NG")
            return False
            
        buffer_manager.cleanup()
        return True
    except Exception as e:
        print(f"音声バッファエラー: {e}")
        traceback.print_exc()
        return False


def check_wake_word():
    """ウェイクワード検出器確認"""
    print("=== ウェイクワード検出器確認 ===")
    try:
        from audio_layer.wake_word_detector import WakeWordDetector
        import numpy as np
        
        wake_detector = WakeWordDetector()
        stats = wake_detector.get_statistics()
        
        print(f"ウェイクワード検出器: OK")
        print(f"設定されたウェイクワード: {stats['wake_word']}")
        print(f"信頼度閾値: {stats['confidence_threshold']}")
        
        # テスト用音声データで動作確認
        test_audio = np.random.random(16000).astype(np.float32)  # 1秒分
        wake_detector.process_audio_chunk(test_audio)
        print("音声チャンク処理: OK")
        
        wake_detector.cleanup()
        return True
    except Exception as e:
        print(f"ウェイクワード検出器エラー: {e}")
        traceback.print_exc()
        return False


def check_all():
    """全コンポーネント動作確認"""
    print("=== 全コンポーネント動作確認 ===")
    
    results = []
    results.append(check_voicevox())
    results.append(check_database())
    results.append(check_audio())
    results.append(check_wake_word())
    
    success_count = sum(results)
    total_count = len(results)
    
    print("\n=== 確認結果 ===")
    print(f"成功: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("✅ 全コンポーネント正常動作")
        return True
    else:
        print("❌ 一部のコンポーネントでエラー")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "voicevox":
            check_voicevox()
        elif command == "database":
            check_database()
        elif command == "audio":
            check_audio()
        elif command == "wake-word":
            check_wake_word()
        elif command == "all":
            check_all()
        else:
            print(f"不明なコマンド: {command}")
    else:
        check_all()