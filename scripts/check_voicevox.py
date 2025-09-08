#!/usr/bin/env python3
"""
VoiceVox接続テストスクリプト
"""

import requests
import json
import sys
from typing import Dict, Any

VOICEVOX_URL = "http://localhost:50021"

def test_voicevox_connection() -> bool:
    """VoiceVoxサーバー接続テスト"""
    try:
        # バージョン取得
        response = requests.get(f"{VOICEVOX_URL}/version", timeout=3)
        if response.status_code == 200:
            print(f"✓ VoiceVox server is running (version: {response.text.strip()})")
            return True
        else:
            print(f"✗ VoiceVox server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ VoiceVox server not responding: {e}")
        return False

def test_voicevox_speakers() -> bool:
    """スピーカー一覧取得テスト"""
    try:
        response = requests.get(f"{VOICEVOX_URL}/speakers", timeout=3)
        if response.status_code == 200:
            speakers = response.json()
            print(f"✓ Available speakers: {len(speakers)}")
            for i, speaker in enumerate(speakers[:3]):  # 最初の3つ表示
                print(f"   {i+1}. {speaker['name']} (ID: {speaker['speaker_uuid']})")
            if len(speakers) > 3:
                print(f"   ... and {len(speakers) - 3} more speakers")
            return True
        else:
            print(f"✗ Speakers endpoint returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Speakers test failed: {e}")
        return False

def test_voicevox_synthesis() -> bool:
    """音声合成テスト"""
    try:
        # クエリ生成
        text = "テストメッセージです"
        query_response = requests.post(
            f"{VOICEVOX_URL}/audio_query",
            params={"text": text, "speaker": 1},
            timeout=5
        )
        
        if query_response.status_code != 200:
            print(f"✗ Audio query failed with status {query_response.status_code}")
            return False
        
        # 音声合成
        synthesis_response = requests.post(
            f"{VOICEVOX_URL}/synthesis",
            params={"speaker": 1},
            json=query_response.json(),
            timeout=10
        )
        
        if synthesis_response.status_code == 200:
            audio_size = len(synthesis_response.content)
            print(f"✓ Voice synthesis successful ({audio_size} bytes)")
            return True
        else:
            print(f"✗ Synthesis failed with status {synthesis_response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Synthesis test failed: {e}")
        return False

def main():
    """メインテスト実行"""
    print("=== VoiceVox Connection Test ===")
    
    tests = [
        ("Connection", test_voicevox_connection),
        ("Speakers", test_voicevox_speakers),
        ("Synthesis", test_voicevox_synthesis),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name} Test:")
        if test_func():
            passed += 1
        else:
            # 接続テスト失敗時は後続スキップ
            if test_name == "Connection":
                print("\nSkipping remaining tests due to connection failure.")
                print("\nTo start VoiceVox:")
                print("1. Download from: https://voicevox.hiroshiba.jp/")
                print("2. Install and run the application")
                print("3. Ensure it's running on http://localhost:50021")
                break
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 VoiceVox is ready for Yes-Man!")
        return 0
    else:
        print("⚠️  Some tests failed. Please check VoiceVox setup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())