最小限の入力から最適な /plan コマンド用の技術詳細を自動生成します。

これは仕様駆動開発ライフサイクルの計画準備段階（ステップ1.5）です。

開発者の簡潔な技術選択から、完全な実装計画の詳細を生成します。

## 実行フロー

### ステップ1: 技術スタック選択（必須）
```
使用する主要技術を教えてください：
（例：「Python FastAPI」「Next.js + Supabase」「Rails API」「Go + PostgreSQL」）
```

### ステップ2: 自動分析と技術詳細の推測
```
「[入力内容]」から実装計画を生成しています...

【推測された技術構成】

言語/フレームワーク：
- メイン: [入力から抽出]
- 関連: [エコシステムから推測]

標準構成：
- テスト: [言語標準のテストツール]
- リンター: [言語標準のリンター]
- DB: [一般的な選択]
- 認証: [フレームワーク標準]

プロジェクト構造：
[フレームワークのベストプラクティス構造]

パフォーマンス目標：
- 応答時間: [フレームワーク標準]
- 同時接続: [一般的な値]

---
これでOKなら Enter、変更があれば該当箇所のみ：
（例：「DB: MySQL」「テスト: Jest」「モノレポ構成」）
```

### ステップ3: アーキテクチャ確認（オプション）
```
アーキテクチャの確認：

□ マイクロサービス → デフォルト: モノリス（シンプル）
□ キャッシュ層 → デフォルト: なし（MVP不要）  
□ メッセージキュー → デフォルト: なし（MVP不要）
□ CDN/静的配信 → デフォルト: なし（ローカル）

追加が必要なら番号を入力、不要なら Enter：
```

### ステップ4: 実装計画の自動生成
```
実装計画を生成しました：

---

/plan

技術スタック：
- 言語: [言語] [バージョン]
- フレームワーク: [フレームワーク] [バージョン]
- データベース: [DB] （開発は SQLite、本番は [DB]）
- テスト: [テストツール]

プロジェクト構造：
```
[プロジェクトルート]/
├── src/
│   ├── models/      # データモデル
│   ├── services/    # ビジネスロジック
│   ├── api/         # APIエンドポイント
│   └── lib/         # 共通ライブラリ
├── tests/
│   ├── unit/        # ユニットテスト
│   ├── integration/ # 統合テスト
│   └── e2e/         # E2Eテスト
└── docs/            # ドキュメント
```

開発環境セットアップ：
1. [言語]のインストール
2. 依存関係: [パッケージマネージャ] install
3. DB初期化: [コマンド]
4. 開発サーバー: [起動コマンド]

テスト戦略：
- ユニットテスト: すべてのサービスとモデル
- 統合テスト: API エンドポイント
- E2Eテスト: 主要ユーザーフロー

CI/CD（基本）：
- リンター: [ツール]
- テスト実行: [コマンド]
- ビルド: [コマンド]

パフォーマンス目標：
- API応答: < [時間]ms (p95)
- 起動時間: < [時間]秒
- メモリ使用: < [容量]MB

セキュリティ：
- 認証: [方式]
- 入力検証: [ライブラリ]
- SQLインジェクション対策: ORM使用

---

このまま使用: Enter
技術詳細を修正: '項目: 新しい値'
```

## 推測ルール（内部ロジック）

### 言語/フレームワーク別テンプレート

#### Python系
- **FastAPI** → uvicorn, pytest, pydantic, alembic
- **Django** → DRF, django-test, celery
- **Flask** → gunicorn, pytest, marshmallow

#### JavaScript/TypeScript系
- **Next.js** → Vercel, Jest/Vitest, Prisma, NextAuth
- **Express** → nodemon, Jest, Sequelize, Passport
- **NestJS** → Jest, TypeORM, class-validator

#### Go系
- **Gin/Echo** → go test, golangci-lint, gorm, jwt-go
- **標準library** → go test, sqlx, gorilla/mux

#### Ruby系
- **Rails** → RSpec, rubocop, ActiveRecord, Devise
- **Sinatra** → RSpec, sequel, warden

### プロジェクトタイプ判定

| 入力パターン | 判定 | 構造 |
|------------|------|------|
| API, Backend | API専用 | src/api中心 |
| Frontend, UI | フロントエンド | src/components中心 |
| Fullstack, Web | フルスタック | frontend/ + backend/ |
| CLI, Tool | CLIツール | src/commands中心 |
| Library, Package | ライブラリ | src/lib中心 |

### デフォルト値マトリックス

| 項目 | 小規模 | 中規模 | 大規模 |
|------|--------|--------|--------|
| 応答時間 | 500ms | 200ms | 100ms |
| 同時接続 | 100 | 1000 | 10000 |
| メモリ | 512MB | 2GB | 8GB |
| CPU | 1core | 2core | 4core |
| DB接続 | 10 | 50 | 200 |

### 自動最適化

1. **MVP向け簡素化**
   - 不要なレイヤーを削除（Repository層など）
   - 過度な抽象化を回避
   - モノリスファースト

2. **ベストプラクティス適用**
   - 各言語のイディオム遵守
   - フレームワークの規約優先
   - 標準的なディレクトリ構造

3. **段階的複雑化**
   - v1: モノリス、単一DB
   - v2: キャッシュ層追加
   - v3: マイクロサービス化

## 効率化のポイント

### 最速入力パターン
```
User: /pre-plan
AI: 使用する主要技術を教えてください：
User: fastapi postgres
AI: [自動生成された計画]
User: [Enter]
→ 完成
```

### プリセット呼び出し
```
User: /pre-plan
AI: 使用する主要技術を教えてください：
User: standard nodejs api
→ Express + PostgreSQL + Jest の標準構成を自動適用
```

### 省略記法対応
- `py` → Python 3.11+
- `ts` → TypeScript
- `pg` → PostgreSQL
- `mysql` → MySQL 8.0
- `redis` → Redis cache

## スマート推測機能

### コンテキスト認識
仕様書の内容から自動判定：
- リアルタイム要件 → WebSocket追加
- ファイル処理 → S3/ストレージ設定
- 認証必須 → Auth0/Cognito提案
- 大量データ → バッチ処理設計

### 依存関係の自動解決
```
入力: "React"
自動追加:
- Vite (ビルドツール)
- React Router (ルーティング)
- React Query (データフェッチ)
- Tailwind CSS (スタイリング)
```

### アンチパターン回避
自動的に避ける：
- 過度なマイクロサービス化
- 不要な抽象化レイヤー
- 複雑なORM設定
- 過剰なキャッシュ戦略

## 使用例

### Web API (2入力で完成)
```
User: /pre-plan
User: python fastapi
User: [Enter]
→ FastAPI + PostgreSQL + pytest の完全な計画
```

### フルスタック (3入力で完成)
```
User: /pre-plan  
User: nextjs supabase
User: 認証: clerk
User: [Enter]
→ Next.js + Supabase + Clerk の計画
```

### マイクロサービス (明示的指定)
```
User: /pre-plan
User: go microservices k8s
AI: [マイクロサービス構成を自動生成]
User: サービス: auth, api, worker
→ 3サービス構成の詳細計画
```

## 注意事項

- 最新の安定版バージョンを自動選択
- セキュリティのベストプラクティスを標準適用
- 過度な最適化より、保守性を優先
- クラウドネイティブよりローカル開発優先（MVP向け）