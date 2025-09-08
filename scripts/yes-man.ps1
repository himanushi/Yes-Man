# Yes-Man音声対話アシスタント PowerShellスクリプト

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Yes-Man音声対話アシスタント - 利用可能なコマンド:" -ForegroundColor Green
    Write-Host ""
    Write-Host "セットアップ:" -ForegroundColor Yellow
    Write-Host "  .\scripts\yes-man.ps1 install         - 依存関係インストール"
    Write-Host "  .\scripts\yes-man.ps1 install-dev     - 開発用依存関係も含めてインストール"
    Write-Host ""
    Write-Host "テスト:" -ForegroundColor Yellow
    Write-Host "  .\scripts\yes-man.ps1 test            - 全テスト実行"
    Write-Host "  .\scripts\yes-man.ps1 test-contract   - Contract テスト実行"
    Write-Host "  .\scripts\yes-man.ps1 test-integration - Integration テスト実行"
    Write-Host "  .\scripts\yes-man.ps1 test-unit       - Unit テスト実行"
    Write-Host ""
    Write-Host "動作確認:" -ForegroundColor Yellow
    Write-Host "  .\scripts\yes-man.ps1 check-voicevox   - VoiceVox接続確認"
    Write-Host "  .\scripts\yes-man.ps1 check-database   - データベース初期化確認"
    Write-Host "  .\scripts\yes-man.ps1 check-audio      - 音声バッファ動作確認"
    Write-Host "  .\scripts\yes-man.ps1 check-wake-word  - ウェイクワード検出器確認"
    Write-Host "  .\scripts\yes-man.ps1 check-all        - 全コンポーネント動作確認"
    Write-Host ""
    Write-Host "実行:" -ForegroundColor Yellow
    Write-Host "  .\scripts\yes-man.ps1 run              - Yes-Man音声レイヤー起動"
    Write-Host "  .\scripts\yes-man.ps1 debug            - デバッグモードで起動"
    Write-Host ""
    Write-Host "開発:" -ForegroundColor Yellow
    Write-Host "  .\scripts\yes-man.ps1 dev              - 開発用ツール実行（black, pylint）"
    Write-Host "  .\scripts\yes-man.ps1 format           - コードフォーマット"
    Write-Host "  .\scripts\yes-man.ps1 lint             - リント実行"
    Write-Host "  .\scripts\yes-man.ps1 clean            - 一時ファイル削除"
}

function Install-Dependencies {
    Write-Host "=== 依存関係インストール ===" -ForegroundColor Green
    uv pip install -e .
}

function Install-DevDependencies {
    Write-Host "=== 開発用依存関係インストール ===" -ForegroundColor Green
    uv pip install -e .[test,dev]
}

function Test-All {
    Write-Host "=== 全テスト実行 ===" -ForegroundColor Green
    uv run pytest tests/ -v
}

function Test-Contract {
    Write-Host "=== Contract テスト実行 ===" -ForegroundColor Green
    uv run pytest tests/contract/ -v
}

function Test-Integration {
    Write-Host "=== Integration テスト実行 ===" -ForegroundColor Green
    uv run pytest tests/integration/ -v
}

function Test-Unit {
    Write-Host "=== Unit テスト実行 ===" -ForegroundColor Green
    uv run pytest tests/unit/ -v
}

function Check-VoiceVox {
    Write-Host "=== VoiceVox接続確認 ===" -ForegroundColor Green
    try {
        $result = uv run python -c "import requests; r = requests.get('http://localhost:50021/version', timeout=5); print('VoiceVox:', 'OK' if r.status_code == 200 else 'NG'); print('バージョン:', r.json() if r.status_code == 200 else 'N/A')" 2>$null
        if ($result) {
            Write-Host $result -ForegroundColor Cyan
        } else {
            Write-Host "VoiceVox未起動" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "VoiceVox接続エラー: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Check-Database {
    Write-Host "=== データベース初期化確認 ===" -ForegroundColor Green
    try {
        $result = uv run python -c "from audio_layer.database.init_db import init_database; init_database(); print('データベース初期化: OK')"
        Write-Host $result -ForegroundColor Cyan
    }
    catch {
        Write-Host "データベースエラー: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Check-Audio {
    Write-Host "=== 音声バッファ動作確認 ===" -ForegroundColor Green
    try {
        $result = uv run python -c "from audio_layer.audio_buffer import AudioBufferManager; import numpy as np; bm = AudioBufferManager(); bm.add_audio_data(np.random.random(1600).astype(np.float32)); print('音声バッファ: OK'); bm.cleanup()"
        Write-Host $result -ForegroundColor Cyan
    }
    catch {
        Write-Host "音声バッファエラー: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Check-WakeWord {
    Write-Host "=== ウェイクワード検出器確認 ===" -ForegroundColor Green
    try {
        $result = uv run python -c "from audio_layer.wake_word_detector import WakeWordDetector; wd = WakeWordDetector(); print('ウェイクワード検出器: OK'); print('設定:', wd.get_statistics()['wake_word']); wd.cleanup()"
        Write-Host $result -ForegroundColor Cyan
    }
    catch {
        Write-Host "ウェイクワード検出器エラー: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Check-All {
    Check-VoiceVox
    Check-Database
    Check-Audio
    Check-WakeWord
    Write-Host "=== 全コンポーネント確認完了 ===" -ForegroundColor Green
}

function Run-YesMan {
    Write-Host "=== Yes-Man音声レイヤー起動 ===" -ForegroundColor Green
    Write-Host "Ctrl+Cで停止" -ForegroundColor Yellow
    uv run python audio_layer/main.py
}

function Run-Debug {
    Write-Host "=== デバッグモード起動 ===" -ForegroundColor Green
    Write-Host "Ctrl+Cで停止" -ForegroundColor Yellow
    $env:PYTHONPATH = "."
    uv run python -c "import logging; logging.basicConfig(level=logging.DEBUG); exec(open('audio_layer/main.py').read())"
}

function Run-Dev {
    Write-Host "=== コード品質チェック ===" -ForegroundColor Green
    Write-Host "Black チェック中..." -ForegroundColor Yellow
    uv run black audio_layer/ --check
    
    Write-Host "Pylint 実行中..." -ForegroundColor Yellow
    uv run pylint audio_layer/
    
    Write-Host "MyPy 実行中..." -ForegroundColor Yellow
    uv run mypy audio_layer/
}

function Format-Code {
    Write-Host "=== コードフォーマット ===" -ForegroundColor Green
    uv run black audio_layer/
}

function Run-Lint {
    Write-Host "=== リント実行 ===" -ForegroundColor Green
    uv run pylint audio_layer/
}

function Clean-Files {
    Write-Host "=== クリーンアップ ===" -ForegroundColor Green
    
    # Python キャッシュファイル削除
    Get-ChildItem -Path . -Recurse -Name "*.pyc" | Remove-Item -Force
    Get-ChildItem -Path . -Recurse -Name "__pycache__" -Directory | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Name "*.log" | Remove-Item -Force
    
    # テストキャッシュ削除
    if (Test-Path ".pytest_cache") { Remove-Item ".pytest_cache" -Recurse -Force }
    if (Test-Path ".mypy_cache") { Remove-Item ".mypy_cache" -Recurse -Force }
    
    # ビルドファイル削除
    if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
    if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
    Get-ChildItem -Path . -Recurse -Name "*.egg-info" -Directory | Remove-Item -Recurse -Force
    
    Write-Host "クリーンアップ完了" -ForegroundColor Cyan
}

# メインロジック
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install" { Install-Dependencies }
    "install-dev" { Install-DevDependencies }
    "test" { Test-All }
    "test-contract" { Test-Contract }
    "test-integration" { Test-Integration }
    "test-unit" { Test-Unit }
    "check-voicevox" { Check-VoiceVox }
    "check-database" { Check-Database }
    "check-audio" { Check-Audio }
    "check-wake-word" { Check-WakeWord }
    "check-all" { Check-All }
    "run" { Run-YesMan }
    "debug" { Run-Debug }
    "dev" { Run-Dev }
    "format" { Format-Code }
    "lint" { Run-Lint }
    "clean" { Clean-Files }
    default {
        Write-Host "不明なコマンド: $Command" -ForegroundColor Red
        Write-Host "利用可能なコマンドは 'help' で確認してください。" -ForegroundColor Yellow
    }
}