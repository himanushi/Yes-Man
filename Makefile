# Yes-Man音声対話アシスタント Makefile

.PHONY: help install test test-contract test-integration test-unit clean dev check-voicevox check-database check-audio check-wake-word run debug

help:
	@echo "Yes-Man音声対話アシスタント - 利用可能なコマンド:"
	@echo ""
	@echo "セットアップ:"
	@echo "  make install         - 依存関係インストール"
	@echo "  make install-dev     - 開発用依存関係も含めてインストール"
	@echo ""
	@echo "テスト:"
	@echo "  make test           - 全テスト実行"
	@echo "  make test-contract  - Contract テスト実行"
	@echo "  make test-integration - Integration テスト実行"
	@echo "  make test-unit      - Unit テスト実行"
	@echo ""
	@echo "動作確認:"
	@echo "  make check-voicevox   - VoiceVox接続確認"
	@echo "  make check-database   - データベース初期化確認"
	@echo "  make check-audio      - 音声バッファ動作確認"
	@echo "  make check-wake-word  - ウェイクワード検出器確認"
	@echo "  make check-all        - 全コンポーネント動作確認"
	@echo ""
	@echo "実行:"
	@echo "  make run             - Yes-Man音声レイヤー起動"
	@echo "  make debug           - デバッグモードで起動"
	@echo ""
	@echo "開発:"
	@echo "  make dev             - 開発用ツール実行（black, pylint）"
	@echo "  make clean           - 一時ファイル削除"

# セットアップ
install:
	uv pip install -e .

install-dev:
	uv pip install -e .[test,dev]

# テスト
test:
	uv run pytest tests/ -v

test-contract:
	uv run pytest tests/contract/ -v

test-integration:
	uv run pytest tests/integration/ -v

test-unit:
	uv run pytest tests/unit/ -v

# 動作確認
check-voicevox:
	@echo "=== VoiceVox接続確認 ==="
	uv run python -c "import requests; r = requests.get('http://localhost:50021/version', timeout=5); print('VoiceVox:', 'OK' if r.status_code == 200 else 'NG'); print('バージョン:', r.json() if r.status_code == 200 else 'N/A')" 2>/dev/null || echo "VoiceVox未起動"

check-database:
	@echo "=== データベース初期化確認 ==="
	uv run python -c "from audio_layer.database.init_db import init_database; init_database(); print('データベース初期化: OK')"

check-audio:
	@echo "=== 音声バッファ動作確認 ==="
	uv run python -c "from audio_layer.audio_buffer import AudioBufferManager; import numpy as np; bm = AudioBufferManager(); bm.add_audio_data(np.random.random(1600).astype(np.float32)); print('音声バッファ: OK'); bm.cleanup()"

check-wake-word:
	@echo "=== ウェイクワード検出器確認 ==="
	uv run python -c "from audio_layer.wake_word_detector import WakeWordDetector; wd = WakeWordDetector(); print('ウェイクワード検出器: OK'); print('設定:', wd.get_statistics()['wake_word']); wd.cleanup()"

check-all: check-voicevox check-database check-audio check-wake-word
	@echo "=== 全コンポーネント確認完了 ==="

# 実行
run:
	@echo "=== Yes-Man音声レイヤー起動 ==="
	@echo "Ctrl+Cで停止"
	uv run python audio_layer/main.py

debug:
	@echo "=== デバッグモード起動 ==="
	@echo "Ctrl+Cで停止"
	PYTHONPATH=. uv run python -c "import logging; logging.basicConfig(level=logging.DEBUG); exec(open('audio_layer/main.py').read())"

# 開発
dev:
	@echo "=== コード品質チェック ==="
	uv run black audio_layer/ --check
	uv run pylint audio_layer/
	uv run mypy audio_layer/

format:
	@echo "=== コードフォーマット ==="
	uv run black audio_layer/

lint:
	@echo "=== リント実行 ==="
	uv run pylint audio_layer/

clean:
	@echo "=== クリーンアップ ==="
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/