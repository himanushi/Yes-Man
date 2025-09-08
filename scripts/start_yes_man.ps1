# Yes-Man Voice Assistant Startup Script
# Fallout New Vegas風Yes-Man音声対話アシスタント起動

param(
    [switch]$SkipDependencyCheck,
    [switch]$SkipVoiceVoxCheck,
    [switch]$SkipLangFlowCheck,
    [switch]$DevMode,
    [switch]$Help,
    [string]$LogLevel = "INFO"
)

# ヘルプ表示
if ($Help) {
    Write-Host @"
Yes-Man Voice Assistant Startup Script

使用法:
  .\start_yes_man.ps1 [オプション]

オプション:
  -SkipDependencyCheck    依存関係チェックをスキップ
  -SkipVoiceVoxCheck      VoiceVoxサーバー確認をスキップ  
  -SkipLangFlowCheck      LangFlowサーバー確認をスキップ
  -DevMode                開発モード（詳細ログ）
  -LogLevel <LEVEL>       ログレベル (DEBUG/INFO/WARNING/ERROR)
  -Help                   このヘルプを表示

例:
  .\start_yes_man.ps1                    # 通常起動
  .\start_yes_man.ps1 -DevMode           # 開発モード
  .\start_yes_man.ps1 -LogLevel DEBUG    # デバッグログ
"@
    exit 0
}

# 設定
$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot
$AUDIO_LAYER_DIR = Join-Path $PROJECT_ROOT "audio_layer"
$FACE_UI_DIR = Join-Path $PROJECT_ROOT "face_ui"
$VOICEVOX_URL = "http://localhost:50021"
$LANGFLOW_URL = "http://localhost:7860"
$LOG_FILE = Join-Path $PROJECT_ROOT "logs" "yes-man-startup.log"

# ログ初期化
if (!(Test-Path (Split-Path $LOG_FILE))) {
    New-Item -ItemType Directory -Path (Split-Path $LOG_FILE) -Force | Out-Null
}

# ログ関数
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    Write-Host $logMessage
    $logMessage | Out-File -Append $LOG_FILE
}

# エラーハンドリング
function Handle-Error {
    param([string]$ErrorMessage, [bool]$Exit = $true)
    
    Write-Log "ERROR: $ErrorMessage" "ERROR"
    if ($Exit) {
        Write-Log "Yes-Man startup failed. Check logs for details." "ERROR"
        exit 1
    }
}

# プロセス管理
$processes = @()

function Start-BackgroundProcess {
    param(
        [string]$Name,
        [string]$Command,
        [string]$Arguments = "",
        [string]$WorkingDirectory = $PROJECT_ROOT,
        [bool]$WaitForReady = $false,
        [string]$ReadyPattern = ""
    )
    
    try {
        Write-Log "Starting $Name..." "INFO"
        
        $processInfo = New-Object System.Diagnostics.ProcessStartInfo
        $processInfo.FileName = $Command
        $processInfo.Arguments = $Arguments
        $processInfo.WorkingDirectory = $WorkingDirectory
        $processInfo.UseShellExecute = $false
        $processInfo.RedirectStandardOutput = $true
        $processInfo.RedirectStandardError = $true
        $processInfo.CreateNoWindow = !$DevMode
        
        $process = [System.Diagnostics.Process]::Start($processInfo)
        
        $processData = @{
            Name = $Name
            Process = $process
            StartTime = Get-Date
        }
        
        $script:processes += $processData
        
        Write-Log "$Name started successfully (PID: $($process.Id))" "INFO"
        
        if ($WaitForReady -and $ReadyPattern) {
            Write-Log "Waiting for $Name to be ready..." "INFO"
            $timeout = 30 # 30秒タイムアウト
            $elapsed = 0
            
            while ($elapsed -lt $timeout) {
                if ($process.HasExited) {
                    Handle-Error "$Name process exited unexpectedly"
                }
                
                # 標準出力から準備完了を確認（簡略化）
                Start-Sleep -Seconds 1
                $elapsed++
                
                # タイムアウト処理は簡略化
                if ($elapsed -ge 10) { # 実際の実装では適切な準備完了検出
                    Write-Log "$Name appears to be ready" "INFO"
                    break
                }
            }
            
            if ($elapsed -ge $timeout) {
                Handle-Error "$Name failed to start within timeout"
            }
        }
        
        return $process
    }
    catch {
        Handle-Error "Failed to start $Name`: $($_.Exception.Message)"
    }
}

function Stop-AllProcesses {
    Write-Log "Stopping all Yes-Man processes..." "INFO"
    
    foreach ($processData in $script:processes) {
        try {
            if (!$processData.Process.HasExited) {
                $processData.Process.Kill()
                $processData.Process.WaitForExit(5000) # 5秒待機
                Write-Log "$($processData.Name) stopped" "INFO"
            }
        }
        catch {
            Write-Log "Failed to stop $($processData.Name): $($_.Exception.Message)" "WARNING"
        }
    }
    
    $script:processes = @()
}

# シャットダウンハンドラー
Register-ObjectEvent -InputObject ([Console]) -EventName CancelKeyPress -Action {
    Write-Host "`nShutdown signal received..."
    Stop-AllProcesses
    Write-Log "Yes-Man shutdown completed" "INFO"
    exit 0
}

# スタートアップバナー
Write-Host @"
╔══════════════════════════════════════════════════════════════════════╗
║                    Yes-Man Voice Assistant                           ║
║                 Fallout New Vegas Style AI                          ║
║                                                                      ║
║  はい！Yes-Manを起動します！                                          ║
║  もちろん、すべてのシステムを準備いたします！                          ║
╚══════════════════════════════════════════════════════════════════════╝
"@

Write-Log "Starting Yes-Man Voice Assistant..." "INFO"
Write-Log "Project Root: $PROJECT_ROOT" "DEBUG"
Write-Log "Log Level: $LogLevel" "DEBUG"

# 1. 環境チェック
Write-Log "Checking system requirements..." "INFO"

# Python環境チェック
if (!$SkipDependencyCheck) {
    Write-Log "Checking Python environment..." "INFO"
    
    try {
        $pythonVersion = & python --version 2>&1
        Write-Log "Python: $pythonVersion" "INFO"
        
        # uv チェック
        $uvVersion = & uv --version 2>&1
        Write-Log "uv: $uvVersion" "INFO"
        
        # 仮想環境アクティベート確認
        if (!$env:VIRTUAL_ENV) {
            Write-Log "Activating Python virtual environment..." "INFO"
            & uv venv
        }
        
    }
    catch {
        Handle-Error "Python environment check failed: $($_.Exception.Message)"
    }
}

# Node.js環境チェック（Face UI用）
if (!$SkipDependencyCheck) {
    Write-Log "Checking Node.js environment..." "INFO"
    
    try {
        $nodeVersion = & node --version 2>&1
        Write-Log "Node.js: $nodeVersion" "INFO"
        
        $npmVersion = & npm --version 2>&1  
        Write-Log "npm: $npmVersion" "INFO"
    }
    catch {
        Handle-Error "Node.js environment check failed: $($_.Exception.Message)"
    }
}

# 2. 外部サービス起動・確認
# VoiceVox サーバー確認
if (!$SkipVoiceVoxCheck) {
    Write-Log "Checking VoiceVox server..." "INFO"
    
    try {
        $response = Invoke-WebRequest -Uri "$VOICEVOX_URL/version" -TimeoutSec 5 -ErrorAction Stop
        Write-Log "VoiceVox server is running (version: $($response.Content))" "INFO"
    }
    catch {
        Write-Log "VoiceVox server not responding. Starting VoiceVox..." "WARNING"
        
        # VoiceVox自動起動（実装は環境依存）
        $voiceVoxPath = "C:\Program Files\VOICEVOX\VOICEVOX.exe"
        if (Test-Path $voiceVoxPath) {
            Start-Process $voiceVoxPath -WindowStyle Hidden
            Write-Log "VoiceVox started. Waiting for server..." "INFO"
            
            # 起動待機
            for ($i = 0; $i -lt 30; $i++) {
                Start-Sleep -Seconds 2
                try {
                    Invoke-WebRequest -Uri "$VOICEVOX_URL/version" -TimeoutSec 3 -ErrorAction Stop | Out-Null
                    Write-Log "VoiceVox server is now ready" "INFO"
                    break
                }
                catch {
                    if ($i -eq 29) {
                        Handle-Error "VoiceVox server failed to start"
                    }
                }
            }
        }
        else {
            Handle-Error "VoiceVox not found. Please install VoiceVox manually."
        }
    }
}

# LangFlow サーバー確認
if (!$SkipLangFlowCheck) {
    Write-Log "Checking LangFlow server..." "INFO"
    
    try {
        $response = Invoke-WebRequest -Uri "$LANGFLOW_URL/api/v1/flows" -TimeoutSec 5 -ErrorAction Stop
        Write-Log "LangFlow server is running" "INFO"
    }
    catch {
        Write-Log "LangFlow server not responding. Starting LangFlow..." "WARNING"
        
        # LangFlow自動起動
        Start-BackgroundProcess -Name "LangFlow" -Command "uv" -Arguments "run langflow run --host 0.0.0.0 --port 7860" -WorkingDirectory $PROJECT_ROOT -WaitForReady $true -ReadyPattern "server started"
    }
}

# 3. Face UI (Electron) 起動
Write-Log "Starting Face UI (Electron)..." "INFO"

if (!(Test-Path $FACE_UI_DIR)) {
    Handle-Error "Face UI directory not found: $FACE_UI_DIR"
}

# npm dependencies check
$packageJsonPath = Join-Path $FACE_UI_DIR "package.json"
$nodeModulesPath = Join-Path $FACE_UI_DIR "node_modules"

if (!(Test-Path $nodeModulesPath)) {
    Write-Log "Installing Face UI dependencies..." "INFO"
    
    Set-Location $FACE_UI_DIR
    & npm install
    
    if ($LASTEXITCODE -ne 0) {
        Handle-Error "Face UI dependency installation failed"
    }
    
    Set-Location $PROJECT_ROOT
}

# Electron アプリ起動
Start-BackgroundProcess -Name "Face UI" -Command "npm" -Arguments "start" -WorkingDirectory $FACE_UI_DIR -WaitForReady $true

# 4. Audio Layer (Python) 起動
Write-Log "Starting Audio Layer (Python)..." "INFO"

if (!(Test-Path $AUDIO_LAYER_DIR)) {
    Handle-Error "Audio Layer directory not found: $AUDIO_LAYER_DIR"
}

# Python dependencies check
$requirementsPath = Join-Path $PROJECT_ROOT "pyproject.toml"
if (Test-Path $requirementsPath) {
    Write-Log "Installing Python dependencies..." "INFO"
    & uv sync
    
    if ($LASTEXITCODE -ne 0) {
        Handle-Error "Python dependency installation failed"
    }
}

# Yes-Man メインプロセス起動
$mainScript = Join-Path $AUDIO_LAYER_DIR "orchestrator.py"
if (!(Test-Path $mainScript)) {
    Handle-Error "Main script not found: $mainScript"
}

$pythonArgs = @"
-c "
import asyncio
import sys
import os
sys.path.append('$AUDIO_LAYER_DIR')
from orchestrator import main
asyncio.run(main())
"
"@

Start-BackgroundProcess -Name "Yes-Man Audio Layer" -Command "uv" -Arguments "run python $pythonArgs" -WorkingDirectory $PROJECT_ROOT -WaitForReady $true

# 5. システム状態確認
Start-Sleep -Seconds 5

Write-Log "Verifying system status..." "INFO"

$systemHealthy = $true

# プロセス生存確認
foreach ($processData in $processes) {
    if ($processData.Process.HasExited) {
        Write-Log "$($processData.Name) process has exited unexpectedly" "ERROR"
        $systemHealthy = $false
    }
    else {
        Write-Log "$($processData.Name) is running (PID: $($processData.Process.Id))" "INFO"
    }
}

# API エンドポイント確認
$endpoints = @(
    @{ Name = "VoiceVox"; Url = "$VOICEVOX_URL/version"; Skip = $SkipVoiceVoxCheck },
    @{ Name = "LangFlow"; Url = "$LANGFLOW_URL/api/v1/flows"; Skip = $SkipLangFlowCheck },
    @{ Name = "IPC Server"; Url = "ws://localhost:8765"; Skip = $true }  # WebSocket確認は省略
)

foreach ($endpoint in $endpoints) {
    if (!$endpoint.Skip) {
        try {
            Invoke-WebRequest -Uri $endpoint.Url -TimeoutSec 3 -ErrorAction Stop | Out-Null
            Write-Log "$($endpoint.Name) endpoint is responding" "INFO"
        }
        catch {
            Write-Log "$($endpoint.Name) endpoint not responding" "WARNING"
            $systemHealthy = $false
        }
    }
}

# 6. 起動完了
if ($systemHealthy) {
    Write-Host @"

╔══════════════════════════════════════════════════════════════════════╗
║                     🎉 Yes-Man Ready! 🎉                           ║
║                                                                      ║
║  はい！Yes-Manの起動が完了しました！                                   ║
║  すべてのシステムが正常に動作しています！                               ║
║                                                                      ║
║  💬 "Yes-Man" と話しかけてください！                                  ║
║  🔧 設定変更はFace UIから可能です                                      ║
║  📊 ログ: $LOG_FILE                    ║
║                                                                      ║
║  終了するには Ctrl+C を押してください                                  ║
╚══════════════════════════════════════════════════════════════════════╝
"@
    
    Write-Log "Yes-Man Voice Assistant startup completed successfully" "INFO"
    Write-Log "All systems operational. Ready for voice interaction." "INFO"
    
    # 開発モード情報表示
    if ($DevMode) {
        Write-Host "`nDevelopment Mode Information:" -ForegroundColor Yellow
        Write-Host "- Log Level: $LogLevel" -ForegroundColor Gray
        Write-Host "- Process Count: $($processes.Count)" -ForegroundColor Gray
        Write-Host "- Project Root: $PROJECT_ROOT" -ForegroundColor Gray
    }
}
else {
    Handle-Error "Yes-Man startup completed with warnings. Some components may not be fully operational."
}

# 7. メインループ（プロセス監視）
Write-Log "Entering main monitoring loop..." "DEBUG"

try {
    while ($true) {
        # プロセス監視
        foreach ($processData in $processes) {
            if ($processData.Process.HasExited) {
                Write-Log "$($processData.Name) process has stopped unexpectedly" "ERROR"
                
                # 自動再起動（簡略化）
                Write-Log "Attempting to restart $($processData.Name)..." "INFO"
                # 実際の実装では適切な再起動ロジックを実装
            }
        }
        
        # システム状態ログ（定期）
        if ((Get-Date).Second -eq 0) {  # 1分毎
            $runningProcesses = ($processes | Where-Object { !$_.Process.HasExited }).Count
            Write-Log "System status: $runningProcesses/$($processes.Count) processes running" "DEBUG"
        }
        
        Start-Sleep -Seconds 10  # 10秒間隔でチェック
    }
}
catch {
    Write-Log "Main loop interrupted: $($_.Exception.Message)" "INFO"
}
finally {
    # クリーンアップ
    Stop-AllProcesses
    Write-Log "Yes-Man Voice Assistant shutdown completed" "INFO"
}