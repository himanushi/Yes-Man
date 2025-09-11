#!/usr/bin/env python3
"""
段階的インポートデバッグ
"""

import sys
print("🔍 個別モジュールインポートテスト")

try:
    print("📝 testing audio_layer.__init__...")
    import audio_layer
    print("✅ audio_layer.__init__ 完了")
except Exception as e:
    print(f"❌ audio_layer.__init__ 失敗: {e}")
    import traceback
    traceback.print_exc()

try:
    print("📝 testing whisper_integration...")
    from audio_layer.whisper_integration import WhisperIntegration
    print("✅ whisper_integration 完了")
except Exception as e:
    print(f"❌ whisper_integration 失敗: {e}")

try:
    print("📝 testing openwakeword...")
    import openwakeword
    print("✅ openwakeword インポート完了")
except Exception as e:
    print(f"❌ openwakeword インポート失敗: {e}")

try:
    print("📝 testing database models...")
    from audio_layer.database.models.agent_settings import AgentSettingsRepository
    print("✅ database models 完了")
except Exception as e:
    print(f"❌ database models 失敗: {e}")

print("🎯 完了")