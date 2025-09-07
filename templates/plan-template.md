# 実装計画: [機能]

**ブランチ**: `feature/[###-feature-name]` | **日付**: [日付] | **仕様**: [link]
**入力**: `/specs/[###-feature-name]/spec.md` からの機能仕様

## 実行フロー (/plan コマンドスコープ)
```
1. 入力パスから機能仕様を読み込み
   → 見つからない場合: エラー「{path} に機能仕様がありません」
2. 技術コンテキストを埋める（NEEDS CLARIFICATION をスキャン）
   → コンテキストからプロジェクトタイプを検出（web=frontend+backend、mobile=app+api）
   → プロジェクトタイプに基づいて構造決定を設定
3. 以下の憲法チェックセクションを評価
   → 違反が存在する場合: 複雑性トラッキングに記録
   → 正当化が不可能な場合: エラー「まずアプローチを簡素化してください」
   → 進捗トラッキングを更新: 初期憲法チェック
4. フェーズ 0 を実行 → research.md
   → NEEDS CLARIFICATION が残っている場合: エラー「未知を解決してください」
5. フェーズ 1 を実行 → contracts、data-model.md、quickstart.md、エージェント固有テンプレートファイル（例: Claude Code 用 `CLAUDE.md`、GitHub Copilot 用 `.github/copilot-instructions.md`、Gemini CLI 用 `GEMINI.md`）
6. 憲法チェックセクションを再評価
   → 新しい違反がある場合: 設計をリファクタリング、フェーズ 1 に戻る
   → 進捗トラッキングを更新: 設計後憲法チェック
7. フェーズ 2 を計画 → タスク生成アプローチを記述（tasks.md は作成しない）
8. 停止 - /tasks コマンドの準備完了
```

**重要**: /plan コマンドはステップ 7 で停止します。フェーズ 2-4 は他のコマンドで実行します:
- フェーズ 2: /tasks コマンドが tasks.md を作成
- フェーズ 3-4: 実装実行（手動またはツール経由）

## 概要
[機能仕様から抽出: 主要要件 + リサーチからの技術アプローチ]

## 技術コンテキスト
**言語/バージョン**: [例: Python 3.11、Swift 5.9、Rust 1.75 または NEEDS CLARIFICATION]  
**主要依存関係**: [例: FastAPI、UIKit、LLVM または NEEDS CLARIFICATION]  
**ストレージ**: [該当する場合、例: PostgreSQL、CoreData、ファイル または N/A]  
**テスト**: [例: pytest、XCTest、cargo test または NEEDS CLARIFICATION]  
**ターゲットプラットフォーム**: [例: Linux サーバー、iOS 15+、WASM または NEEDS CLARIFICATION]
**プロジェクトタイプ**: [single/web/mobile - ソース構造を決定]  
**パフォーマンス目標**: [ドメイン固有、例: 1000 req/s、1M 行/秒、60 fps または NEEDS CLARIFICATION]  
**制約**: [ドメイン固有、例: <200ms p95、<100MB メモリ、オフライン対応 または NEEDS CLARIFICATION]  
**スケール/スコープ**: [ドメイン固有、例: 10k ユーザー、1M LOC、50 スクリーン または NEEDS CLARIFICATION]

## 憲法チェック
*ゲート: フェーズ 0 リサーチ前に合格必須。フェーズ 1 設計後に再チェック。*

**シンプルさ**:
- プロジェクト数: [#] (最大3 - 例: api、cli、tests)
- フレームワークを直接使用？（ラッパークラスなし）
- 単一データモデル？（シリアライゼーションが異なる場合を除き DTO なし）
- パターンを回避？（実証されたニーズなしに Repository/UoW なし）

**アーキテクチャ**:
- すべての機能をライブラリ化？（直接アプリコードなし）
- ライブラリリスト: [各ライブラリの名前 + 目的]
- ライブラリごとの CLI: [--help/--version/--format 付きコマンド]
- ライブラリドキュメント: llms.txt 形式を計画？

**テスト（非妥協的）**:
- RED-GREEN-Refactor サイクルを強制？（テストは最初に失敗する必要がある）
- Git コミットで実装前にテストを表示？
- 順序: Contract→Integration→E2E→Unit を厳密に遵守？
- 実際の依存関係を使用？（実際の DB、モックではない）
- 統合テストの対象: 新しいライブラリ、コントラクト変更、共有スキーマ？
- 禁止: テスト前の実装、RED フェーズのスキップ

**監視可能性**:
- 構造化ログを含む？
- フロントエンドログ → バックエンド？（統一ストリーム）
- エラーコンテキストは十分？

**バージョニング**:
- バージョン番号が割り当てられている？（MAJOR.MINOR.BUILD）
- すべての変更で BUILD をインクリメント？
- 破壊的変更を処理？（並列テスト、移行計画）

## プロジェクト構造

### ドキュメント（この機能）
```
specs/[###-feature]/
├── plan.md              # このファイル (/plan コマンド出力)
├── research.md          # フェーズ 0 出力 (/plan コマンド)
├── data-model.md        # フェーズ 1 出力 (/plan コマンド)
├── quickstart.md        # フェーズ 1 出力 (/plan コマンド)
├── contracts/           # フェーズ 1 出力 (/plan コマンド)
└── tasks.md             # フェーズ 2 出力 (/tasks コマンド - /plan では作成されない)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure]
```

**Structure Decision**: [DEFAULT to Option 1 unless Technical Context indicates web/mobile app]

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `/scripts/update-agent-context.sh [claude|gemini|copilot]` for your AI assistant
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract → contract test task [P]
- Each entity → model creation task [P] 
- Each user story → integration test task
- Implementation tasks to make tests pass

**Ordering Strategy**:
- TDD order: Tests before implementation 
- Dependency order: Models before services before UI
- Mark [P] for parallel execution (independent files)

**Estimated Output**: 25-30 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [ ] Phase 0: Research complete (/plan command)
- [ ] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [ ] Initial Constitution Check: PASS
- [ ] Post-Design Constitution Check: PASS
- [ ] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*