# Yes-Man音声対話アシスタント クイックスタート

## システム要件確認

### 必須環境
- **OS**: Windows 10+ (推奨), macOS, Linux
- **Python**: 3.11以上
- **GPU**: NVIDIA GPU (CUDA対応) 推奨
- **RAM**: 8GB以上 (Whisperモデル用)
- **ディスク**: 5GB以上の空き容量

### 必須ソフトウェア
1. **VoiceVox アプリケーション**
   - https://voicevox.hiroshiba.jp/ からダウンロード・インストール
   - 起動して http://localhost:50021 でAPI利用可能な状態にする

2. **Node.js** (Electron用)
   - https://nodejs.org/ からLTS版をインストール

## セットアップ手順

### 1. リポジトリクローン
```bash
git clone <repository-url>
cd Yes-Man
git checkout feature/001-yes-man-fallout
```

### 2. Python環境セットアップ
```bash
# 仮想環境作成
python -m venv yes_man_env
source yes_man_env/bin/activate  # Windows: yes_man_env\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# GPU版Whisper.cpp (CUDA対応GPU必須)
pip install whispercpp[gpu]

# LangFlowインストール
pip install langflow
```

### 3. Electron UI セットアップ
```bash
cd face_ui
npm install
cd ..
```

### 4. データベース初期化
```bash
# SQLiteデータベースとテーブル作成
python -m audio_layer.database.init_db
```

### 5. 設定ファイル作成
```bash
# 環境変数ファイル作成
cp .env.example .env

# .envファイルを編集
# OPENAI_API_KEY=your_openai_api_key_here
# LANGFLOW_HOST=localhost
# LANGFLOW_PORT=7860
# VOICEVOX_HOST=localhost
# VOICEVOX_PORT=50021
```

## 初回起動テスト

### 1. VoiceVoxサービス確認
```bash
curl http://localhost:50021/speakers
# スピーカー情報のJSONが返れば成功
```

### 2. LangFlow起動
```bash
langflow run --host 0.0.0.0 --port 7860
# ブラウザで http://localhost:7860 にアクセス可能
```

### 3. Yes-Manエージェント設定
1. LangFlow UI (http://localhost:7860) にアクセス
2. `langflow_flows/yes_man_agent.json` をインポート
3. OpenAI APIキーを設定
4. フローを保存・実行

### 4. Yes-Man起動
```bash
# Yes-Man音声対話システム起動
uv run yes-man
```

### 5. 顔UI起動 (別ターミナル)
```bash
cd face_ui
npm start
```

## 動作確認シナリオ

### シナリオ1: 基本的な音声対話
1. **前提**: すべてのサービスが起動済み
2. **操作**: マイクに向かって「Yes-Man」と発話
3. **期待結果**: 
   - 顔UIが「listening」状態に変化
   - 音声で「はい！何かお手伝いできることはありますか？」と応答
   - 顔アニメーションが口の動きと同期

### シナリオ2: 計算タスク実行
1. **前提**: シナリオ1成功済み
2. **操作**: 「Yes-Man」→「10たす5はいくつ？」と発話
3. **期待結果**:
   - 「15です！計算は得意なんですよ！」等の応答
   - SQLiteに会話履歴が保存される

### シナリオ3: タイマー機能
1. **前提**: Yes-Manが待機状態
2. **操作**: 「Yes-Man」→「3分のタイマーをセットして」と発話
3. **期待結果**:
   - 「3分のタイマーをセットしました！」の応答
   - 3分後にタイマー完了の音声通知

### シナリオ4: GUI設定変更
1. **操作**: 顔UIの設定画面を開く
2. **操作**: VoiceVoxスピーカーIDを変更
3. **期待結果**: 次回の応答で音声が変わる

## トラブルシューティング

### よくある問題と解決方法

#### 1. ウェイクワードが反応しない
**症状**: 「Yes-Man」と言っても反応がない
**解決方法**:
```bash
# マイクデバイス確認
python -c "import pyaudio; pa = pyaudio.PyAudio(); print([pa.get_device_info_by_index(i)['name'] for i in range(pa.get_device_count())])"

# 音声認識テスト
python -m audio_layer.test_whisper
```

#### 2. VoiceVox音声が出ない
**症状**: テキスト応答はあるが音声が聞こえない
**解決方法**:
```bash
# VoiceVox接続テスト
curl -X POST "http://localhost:50021/audio_query?text=テスト&speaker=1" \
     -H "Content-Type: application/json"

# VoiceVoxプロセス確認
# VoiceVoxアプリケーションが起動しているか確認
```

#### 3. GPU認識されない
**症状**: Whisperの処理が異常に遅い
**解決方法**:
```bash
# CUDA確認
nvidia-smi

# PyTorch CUDA確認
python -c "import torch; print(torch.cuda.is_available())"

# Whisper.cpp GPU版再インストール
pip uninstall whispercpp
pip install whispercpp[gpu]
```

#### 4. LangFlowエラー
**症状**: エージェントが応答しない
**解決方法**:
1. LangFlow UIでフロー実行テスト
2. OpenAI APIキーの確認
3. データベース接続の確認

#### 5. 顔UIが表示されない
**症状**: Electronウィンドウが開かない
**解決方法**:
```bash
# Electronプロセス確認
cd face_ui
npm run electron-dev

# ログ確認
# コンソールのエラーメッセージを確認
```

## ログとデバッグ

### ログファイル場所
- **音声レイヤー**: `logs/audio_layer.log`
- **LangFlow**: `logs/langflow_integration.log`
- **顔UI**: Electronコンソール (F12)
- **データベース**: `logs/database.log`

### デバッグモード実行
```bash
# 詳細ログ出力
python audio_layer/main.py --debug --log-level=DEBUG

# 顔UI開発モード
cd face_ui
npm run dev
```

## 設定カスタマイズ

### ウェイクワード変更
```bash
# 設定データベース更新
python -c "
from audio_layer.database.models import AudioSettings
settings = AudioSettings()
settings.update_setting('wake_word', 'Hello Assistant')
"
```

### Yes-Man性格調整
1. LangFlow UIにアクセス
2. Yes-Manエージェントフローを編集
3. プロンプトテンプレートを変更
4. 「よりフレンドリーに」「もっと丁寧に」等

### 音声品質向上
```python
# VoiceVox設定最適化
settings = {
    'speed': 1.1,        # 話速
    'volume': 0.9,       # 音量  
    'intonation': 1.2    # イントネーション
}
```

## パフォーマンス最適化

### CPU使用率30%以下の維持
- Whisperモデルサイズの調整 (medium → small)
- VAD (Voice Activity Detection) の活用
- GPU処理の最大活用

### メモリ使用量削減
- 音声バッファサイズの調整（3秒→2秒）
- 会話履歴の自動クリーンアップ
- 未使用ツールの無効化

## 本格運用準備

### 1. システム起動スクリプト
```bash
# start_yes_man.sh 作成
#!/bin/bash
./scripts/start_all_services.sh
```

### 2. 自動起動設定
- Windows: スタートアップフォルダに登録
- macOS: launchd設定
- Linux: systemd service設定

### 3. ログローテーション
```bash
# ログファイルの自動削除設定
crontab -e
# 0 2 * * * find /path/to/yes-man/logs -name "*.log" -mtime +7 -delete
```

**セットアップ完了！Yes-Manとの音声対話を楽しんでください！** 🎉