# タスク: [機能名]

**入力**: `/specs/[###-feature-name]/` からの設計ドキュメント
**前提条件**: plan.md（必須）、research.md、data-model.md、contracts/

## 実行フロー（メイン）
```
1. 機能ディレクトリから plan.md を読み込み
   → 見つからない場合: エラー「実装計画が見つかりません」
   → 抽出: 技術スタック、ライブラリ、構造
2. オプションの設計ドキュメントを読み込み:
   → data-model.md: エンティティを抽出 → モデルタスク
   → contracts/: 各ファイル → コントラクトテストタスク
   → research.md: 決定を抽出 → セットアップタスク
3. カテゴリ別にタスクを生成:
   → セットアップ: プロジェクト初期化、依存関係、リンティング
   → テスト: コントラクトテスト、統合テスト
   → コア: モデル、サービス、CLI コマンド
   → 統合: DB、ミドルウェア、ログ
   → 仕上げ: ユニットテスト、パフォーマンス、ドキュメント
4. タスクルールを適用:
   → 異なるファイル = 並列用の [P] をマーク
   → 同じファイル = 順次実行（[P] なし）
   → 実装前にテスト（TDD）
5. タスクに順次番号を付ける（T001、T002...）
6. 依存関係グラフを生成
7. 並列実行の例を作成
8. タスクの完全性を検証:
   → すべてのコントラクトにテストがあるか？
   → すべてのエンティティにモデルがあるか？
   → すべてのエンドポイントが実装されているか？
9. 戻り値: 成功（実行準備完了）
```

## 形式: `[ID] [P?] 説明`
- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- 説明に正確なファイルパスを含める

## パス規則
- **単一プロジェクト**: リポジトリルートの `src/`、`tests/`
- **Web アプリ**: `backend/src/`、`frontend/src/`
- **モバイル**: `api/src/`、`ios/src/` または `android/src/`
- 以下のパスは単一プロジェクトを想定 - plan.md の構造に基づいて調整

## フェーズ 3.1: セットアップ
- [ ] T001 実装計画に従ってプロジェクト構造を作成
- [ ] T002 [言語] プロジェクトを [フレームワーク] 依存関係で初期化
- [ ] T003 [P] リンティングとフォーマットツールを設定

## フェーズ 3.2: テストファースト（TDD）⚠️ 3.3 より前に完了必須
**重要: これらのテストは記述され、実装前に失敗する必要があります**
- [ ] T004 [P] Contract test POST /api/users in tests/contract/test_users_post.py
- [ ] T005 [P] Contract test GET /api/users/{id} in tests/contract/test_users_get.py
- [ ] T006 [P] Integration test user registration in tests/integration/test_registration.py
- [ ] T007 [P] Integration test auth flow in tests/integration/test_auth.py

## フェーズ 3.3: コア実装（テスト失敗後のみ）
- [ ] T008 [P] User model in src/models/user.py
- [ ] T009 [P] UserService CRUD in src/services/user_service.py
- [ ] T010 [P] CLI --create-user in src/cli/user_commands.py
- [ ] T011 POST /api/users endpoint
- [ ] T012 GET /api/users/{id} endpoint
- [ ] T013 Input validation
- [ ] T014 Error handling and logging

## フェーズ 3.4: 統合
- [ ] T015 Connect UserService to DB
- [ ] T016 Auth middleware
- [ ] T017 Request/response logging
- [ ] T018 CORS and security headers

## フェーズ 3.5: 仕上げ
- [ ] T019 [P] Unit tests for validation in tests/unit/test_validation.py
- [ ] T020 Performance tests (<200ms)
- [ ] T021 [P] Update docs/api.md
- [ ] T022 Remove duplication
- [ ] T023 Run manual-testing.md

## 依存関係
- 実装（T008-T014）前にテスト（T004-T007）
- T008 が T009、T015 をブロック
- T016 が T018 をブロック
- 仕上げ（T019-T023）前に実装

## 並列実行例
```
# Launch T004-T007 together:
Task: "Contract test POST /api/users in tests/contract/test_users_post.py"
Task: "Contract test GET /api/users/{id} in tests/contract/test_users_get.py"
Task: "Integration test registration in tests/integration/test_registration.py"
Task: "Integration test auth in tests/integration/test_auth.py"
```

## 注意
- [P] タスク = 異なるファイル、依存関係なし
- 実装前にテストの失敗を確認
- 各タスク後にコミット
- 避ける: 曖昧なタスク、同ファイルの競合

## タスク生成ルール
*main() 実行中に適用*

1. **コントラクトから**:
   - 各コントラクトファイル → コントラクトテストタスク [P]
   - 各エンドポイント → 実装タスク
   
2. **データモデルから**:
   - 各エンティティ → モデル作成タスク [P]
   - リレーション → サービス層タスク
   
3. **ユーザーストーリーから**:
   - 各ストーリー → 統合テスト [P]
   - クイックスタートシナリオ → 検証タスク

4. **順序**:
   - セットアップ → テスト → モデル → サービス → エンドポイント → 仕上げ
   - 依存関係が並列実行をブロック

## 検証チェックリスト
*ゲート: 戻る前に main() でチェック*

- [ ] すべてのコントラクトに対応するテストがある
- [ ] すべてのエンティティにモデルタスクがある
- [ ] すべてのテストが実装前に来る
- [ ] 並列タスクが真に独立している
- [ ] 各タスクが正確なファイルパスを指定している
- [ ] 他の [P] タスクと同じファイルを変更するタスクがない