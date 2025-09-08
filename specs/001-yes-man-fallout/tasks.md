# タスク: Yes-Man音声対話アシスタント

**入力**: `/specs/001-yes-man-fallout/` からの設計ドキュメント
**前提条件**: plan.md（必須）、research.md、data-model.md、contracts/

## 実行フロー（メイン）
設計ドキュメントから以下のタスクを抽出:
- plan.md から技術スタック（Python 3.11, Electron, SQLite）
- data-model.md から5つのエンティティ（ConversationSession, ConversationExchange, AgentSettings, ToolConfiguration, AudioSettings）
- contracts/ から3つのAPI（audio_layer, langflow_integration, face_ui_ipc）
- quickstart.md から4つのテストシナリオ

## 形式: `[ID] [P?] 説明`
- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- 説明に正確なファイルパスを含める

## パス規則
特殊構成: audio_layer(メインPython), face_ui(Electron), langflow_flows(設定)

## フェーズ 3.1: セットアップ
- [ ] T001 プロジェクト構造を作成（audio_layer/, face_ui/, langflow_flows/, tests/）
- [ ] T002 Python仮想環境をwhispercpp[gpu], langflow, requests依存関係で初期化
- [ ] T003 [P] Electron UIをReact依存関係で初期化（face_ui/package.json）
- [ ] T004 [P] リンティングとフォーマットツールを設定（black, pylint, ESLint）

## フェーズ 3.2: テストファースト（TDD）⚠️ 3.3 より前に完了必須
**重要: これらのテストは記述され、実装前に失敗する必要があります**
- [ ] T005 [P] Contract test wake word detection in tests/contract/test_audio_api_wake_word.py
- [ ] T006 [P] Contract test continuous recognition in tests/contract/test_audio_api_continuous.py
- [ ] T007 [P] Contract test TTS synthesis in tests/contract/test_audio_api_tts.py
- [ ] T008 [P] Contract test LangFlow agent execution in tests/contract/test_langflow_integration_agent.py
- [ ] T009 [P] Contract test tool management in tests/contract/test_langflow_integration_tools.py
- [ ] T010 [P] Contract test face state management in tests/contract/test_face_ui_ipc_state.py
- [ ] T011 [P] Integration test basic voice dialogue in tests/integration/test_basic_dialogue.py
- [ ] T012 [P] Integration test calculator task in tests/integration/test_calculator_task.py
- [ ] T013 [P] Integration test timer functionality in tests/integration/test_timer_task.py
- [ ] T014 [P] Integration test GUI settings change in tests/integration/test_gui_settings.py

## フェーズ 3.3: データモデル実装（テスト失敗後のみ）
- [ ] T015 [P] ConversationSession model in audio_layer/database/models/conversation_session.py
- [ ] T016 [P] ConversationExchange model in audio_layer/database/models/conversation_exchange.py
- [ ] T017 [P] AgentSettings model in audio_layer/database/models/agent_settings.py
- [ ] T018 [P] ToolConfiguration model in audio_layer/database/models/tool_configuration.py
- [ ] T019 [P] AudioSettings model in audio_layer/database/models/audio_settings.py
- [ ] T020 データベース初期化とマイグレーション in audio_layer/database/init_db.py

## フェーズ 3.4: 音声レイヤー実装
- [ ] T021 Whisper.cpp統合 in audio_layer/whisper_integration.py
- [ ] T022 ウェイクワード検出 in audio_layer/wake_word_detector.py
- [ ] T023 継続音声認識 in audio_layer/continuous_recognition.py
- [ ] T024 VoiceVox TTS統合 in audio_layer/voicevox_integration.py
- [ ] T025 音声バッファ管理 in audio_layer/audio_buffer.py
- [ ] T026 音声レイヤーメイン in audio_layer/main.py

## フェーズ 3.5: LangFlow統合
- [ ] T027 LangFlowクライアント in audio_layer/langflow_client.py
- [ ] T028 エージェント実行管理 in audio_layer/agent_executor.py
- [ ] T029 ツール管理システム in audio_layer/tool_manager.py
- [ ] T030 会話履歴管理 in audio_layer/conversation_manager.py

## フェーズ 3.6: 顔UI実装
- [ ] T031 [P] 顔アニメーションコンポーネント in face_ui/src/components/FaceAnimation.tsx
- [ ] T032 [P] 設定画面コンポーネント in face_ui/src/components/Settings.tsx
- [ ] T033 [P] システム状態管理 in face_ui/src/store/systemStore.ts
- [ ] T034 Python-ElectronIPCブリッジ in face_ui/src/services/ipcBridge.ts
- [ ] T035 メインElectronプロセス in face_ui/public/electron.js
- [ ] T036 顔UIメインアプリ in face_ui/src/App.tsx

## フェーズ 3.7: LangFlowエージェント設定
- [ ] T037 [P] Yes-Manエージェントフロー設定 in langflow_flows/yes_man_agent.json
- [ ] T038 [P] 計算ツール設定 in langflow_flows/calculator_tool.json
- [ ] T039 [P] タイマーツール設定 in langflow_flows/timer_tool.json
- [ ] T040 [P] 基本対話フロー設定 in langflow_flows/basic_conversation.json

## フェーズ 3.8: システム統合
- [ ] T041 IPC通信インターフェース実装 in audio_layer/ipc_server.py
- [ ] T042 エラーハンドリングとログ設定
- [ ] T043 システム全体の協調処理
- [ ] T044 パフォーマンス最適化（CPU<30%, 応答<3秒）

## フェーズ 3.9: 仕上げ
- [ ] T045 [P] Unit tests for Whisper integration in tests/unit/test_whisper_integration.py
- [ ] T046 [P] Unit tests for VoiceVox integration in tests/unit/test_voicevox_integration.py
- [ ] T047 [P] Unit tests for audio buffer management in tests/unit/test_audio_buffer.py
- [ ] T048 [P] Unit tests for IPC communication in tests/unit/test_ipc_server.py
- [ ] T049 パフォーマンステスト（<1秒ウェイクワード、<3秒応答）
- [ ] T050 プライバシー保護検証（メモリ内のみ、ディスク書き込み禁止）
- [ ] T051 [P] 起動スクリプト作成 in scripts/start_yes_man.sh
- [ ] T052 quickstart.mdテストシナリオ実行
- [ ] T053 コード品質チェックとリファクタリング

## 依存関係
- セットアップ（T001-T004）完了後にテスト作成
- テスト（T005-T014）失敗確認後に実装開始
- データモデル（T015-T020）がすべての実装をブロック
- T021-T026（音声レイヤー）がT027-T030（LangFlow統合）をブロック
- T031-T036（顔UI）がT041（IPC通信）をブロック
- すべての実装完了後に仕上げ（T045-T053）

## 並列実行例
```bash
# セットアップフェーズ:
Task: "Electron UIをReact依存関係で初期化（face_ui/package.json）"
Task: "リンティングとフォーマットツールを設定（black, pylint, ESLint）"

# テストファースト並列実行:
Task: "Contract test wake word detection in tests/contract/test_audio_api_wake_word.py"
Task: "Contract test continuous recognition in tests/contract/test_audio_api_continuous.py" 
Task: "Contract test TTS synthesis in tests/contract/test_audio_api_tts.py"
Task: "Contract test LangFlow agent execution in tests/contract/test_langflow_integration_agent.py"

# データモデル並列実行:
Task: "ConversationSession model in audio_layer/database/models/conversation_session.py"
Task: "ConversationExchange model in audio_layer/database/models/conversation_exchange.py"
Task: "AgentSettings model in audio_layer/database/models/agent_settings.py"
```

## 注意
- [P] タスク = 異なるファイル、依存関係なし
- 実装前にテストの失敗を確認
- 各フェーズ後にコミット推奨
- 避ける: 曖昧なタスク、同ファイルの競合

## 検証チェックリスト
- [x] すべてのコントラクト（3つのAPI）に対応するテストがある
- [x] すべてのエンティティ（5つのモデル）にモデルタスクがある
- [x] すべてのテストが実装前に来る（T005-T014 → T015以降）
- [x] 並列タスクが真に独立している（異なるファイルパス）
- [x] 各タスクが正確なファイルパスを指定している
- [x] 他の [P] タスクと同じファイルを変更するタスクがない