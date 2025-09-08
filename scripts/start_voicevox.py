#!/usr/bin/env python3
"""
VoiceVox自動起動スクリプト
"""

import subprocess
import os
import time
import requests
import sys


def find_voicevox_executable():
    """VoiceVox実行ファイルを検索"""
    # 一般的なインストール場所
    common_paths = [
        r"C:\Users\ma5an\AppData\Local\Programs\VOICEVOX\VOICEVOX.exe",
        r"C:\Program Files\VOICEVOX\VOICEVOX.exe", 
        r"C:\Program Files (x86)\VOICEVOX\VOICEVOX.exe",
        r"C:\Users\ma5an\Desktop\VOICEVOX.exe",
        # Portable版
        r"C:\VOICEVOX\VOICEVOX.exe",
        r".\VOICEVOX.exe"
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None


def check_voicevox_running():
    """VoiceVoxが起動中かチェック"""
    try:
        response = requests.get('http://localhost:50021/version', timeout=5)
        return response.status_code == 200
    except:
        return False


def start_voicevox():
    """VoiceVox起動"""
    if check_voicevox_running():
        print("OK: VoiceVox は既に起動しています")
        return True
    
    print("VoiceVox実行ファイルを検索中...")
    exe_path = find_voicevox_executable()
    
    if not exe_path:
        print("ERROR: VoiceVoxが見つかりません")
        print("以下の場所にVOICEVOX.exeがあるか確認してください:")
        print("- AppData/Local/Programs/VOICEVOX/")
        print("- Program Files/VOICEVOX/")
        print("- デスクトップ")
        return False
    
    print(f"FOUND: VoiceVoxを発見: {exe_path}")
    print("STARTING: VoiceVoxを起動中...")
    
    try:
        # バックグラウンドで起動
        subprocess.Popen([exe_path], 
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        
        # API起動まで待機
        print("WAITING: VoiceVox APIの起動を待機中...")
        for i in range(30):  # 30秒まで待機
            time.sleep(1)
            if check_voicevox_running():
                print("SUCCESS: VoiceVox API起動完了!")
                return True
            print(f"   起動中... ({i+1}/30)")
        
        print("ERROR: VoiceVox API起動がタイムアウトしました")
        return False
        
    except Exception as e:
        print(f"ERROR: VoiceVox起動エラー: {e}")
        return False


def main():
    """メイン実行"""
    print("=== VoiceVox 自動起動スクリプト ===")
    
    if start_voicevox():
        print("SUCCESS: VoiceVoxの準備完了!")
        print("http://localhost:50021 でAPIにアクセス可能です")
        return 0
    else:
        print("FAILED: VoiceVoxの起動に失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())