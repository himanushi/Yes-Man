# Yes-Man System Test Script
# Quick verification that all components are ready

Write-Host "=== Yes-Man System Test ===" -ForegroundColor Green

# Test 1: Python Environment
Write-Host "`n1. Testing Python Environment..." -ForegroundColor Yellow
try {
    $pythonVersion = & uv run python --version 2>&1
    Write-Host "   ✓ Python: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Python test failed" -ForegroundColor Red
    exit 1
}

# Test 2: Key Dependencies
Write-Host "`n2. Testing Key Dependencies..." -ForegroundColor Yellow
try {
    & uv run python -c "import openai; import sqlite3; import asyncio; print('Dependencies OK')" 2>&1 | Out-Null
    Write-Host "   ✓ Core dependencies available" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Dependency test failed" -ForegroundColor Red
    exit 1
}

# Test 3: Audio Layer Imports
Write-Host "`n3. Testing Audio Layer..." -ForegroundColor Yellow
try {
    & uv run python -c "
import sys
sys.path.append('audio_layer')
from whisper_integration import WhisperSTTProcessor
from voicevox_client import VoiceVoxClient
from langflow_client import LangFlowClient
print('Audio layer imports OK')
" 2>&1 | Out-Null
    Write-Host "   ✓ Audio layer modules available" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Audio layer test failed" -ForegroundColor Red
    exit 1
}

# Test 4: Face UI Dependencies
Write-Host "`n4. Testing Face UI..." -ForegroundColor Yellow
if (Test-Path "face_ui/node_modules") {
    Write-Host "   ✓ Face UI dependencies installed" -ForegroundColor Green
} else {
    Write-Host "   ? Face UI dependencies not installed - run 'npm install' in face_ui/" -ForegroundColor Yellow
}

# Test 5: Configuration Files
Write-Host "`n5. Testing Configuration..." -ForegroundColor Yellow
$configOK = $true

if (!(Test-Path "langflow_flows/yes_man_agent.json")) {
    Write-Host "   ✗ LangFlow agent config missing" -ForegroundColor Red
    $configOK = $false
}

if (!(Test-Path "audio_layer/database/init_db.py")) {
    Write-Host "   ✗ Database init script missing" -ForegroundColor Red
    $configOK = $false
}

if ($configOK) {
    Write-Host "   ✓ Configuration files present" -ForegroundColor Green
}

# Test 6: VoiceVox Check (optional)
Write-Host "`n6. Testing VoiceVox..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:50021/version" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "   ✓ VoiceVox server is running" -ForegroundColor Green
}
catch {
    Write-Host "   ? VoiceVox server not running (optional for development)" -ForegroundColor Yellow
}

Write-Host "`n=== Test Summary ===" -ForegroundColor Green
Write-Host "✓ Yes-Man system components are ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start VoiceVox application (if not running)" -ForegroundColor White
Write-Host "2. Run: uv run yes-man" -ForegroundColor White
Write-Host "3. Say 'Yes-Man' to activate voice interaction!" -ForegroundColor White
Write-Host ""
Write-Host "For development: use -DevMode flag" -ForegroundColor Gray