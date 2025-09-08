# Yes-Man 開発ガイドライン

すべての機能計画から自動生成。最終更新: 2025-09-08

## アクティブテクノロジー
- Python 3.11 + JavaScript/TypeScript (Electron) + whispercpp[gpu], langflow, requests, electron, react (feature/001-yes-man-fallout)
- SQLite (LangFlow統合) (feature/001-yes-man-fallout)

## プロジェクト構造
```
audio_layer/              # Python音声処理メイン
├── whisper_streaming.py  # STT + ウェイクワード検出
├── voicevox_client.py    # TTS
├── langflow_client.py    # エージェント連携
├── database/             # SQLiteデータ管理
└── main.py              # メインループ

face_ui/                 # Electron顔アニメーション
├── src/
│   ├── YesManFace.jsx   # 顔コンポーネント
│   ├── hooks/           # React hooks
│   └── App.jsx
├── main.js              # Electron main
└── package.json

langflow_flows/          # エージェント設定
├── yes_man_agent.json   # メインエージェント
└── tools/               # ツール設定

tests/                   # テスト
├── unit/
├── integration/
└── e2e/
```

## コマンド
```bash
# Python音声レイヤー
cd audio_layer && python main.py

# テスト実行
pytest tests/ && ruff check audio_layer/

# 顔UI開発
cd face_ui && npm start

# LangFlow起動（Ctrl+C対応版）
uv run yes-man-start-langflow --host 127.0.0.1 --port 7860

# VoiceVox確認
curl http://localhost:50021/speakers
```

## コードスタイル
- **Python**: ruff + mypy, type hints必須
- **JavaScript/TypeScript**: ESLint + Prettier
- **コミット**: 実装前にテスト作成（TDD必須）
- **命名**: Yes-Man風の親しみやすいコメント

## 重要な実装原則
- **プライバシー**: 音声データはメモリ内のみ、ディスク保存禁止
- **パフォーマンス**: CPU使用率30%以下、ウェイクワード検出1秒以内
- **リアルタイム**: 音声応答3秒以内、GPU最適化活用
- **エラーハンドリング**: VoiceVoxやWhisperの障害に対するフォールバック

## Yes-Man固有の開発ガイド
- **キャラクター性**: Fallout NewVegasのYes-Manに忠実
- **応答パターン**: 「はい！」「もちろんです！」等の肯定的表現
- **音声合成**: VoiceVoxローカルAPI使用、スピーカーID選択可能
- **常時監視**: 3秒循環バッファでプライバシー保護

## 最近の変更
- feature/001-yes-man-fallout: Added Python 3.11 + JavaScript/TypeScript (Electron) + whispercpp[gpu], langflow, requests, electron, react

<!-- 手動追加開始 -->
## 開発注意事項
- **実行制限**: `uv run yes-man` を自動実行禁止（ユーザーが手動実行のみ）
- **依存関係管理**: `uv add` 使用禁止 - pyproject.tomlに直接追加

## API設定
- **OpenAI API Key**: `.env`ファイルに`OPENAI_API_KEY=your_key_here`を設定
- **LangFlow**: OpenAI gpt-5-miniモデルを使用（yes_man_agent.json）
<!-- 手動追加終了 -->