# データモデル: Yes-Man音声対話システム

## エンティティ定義

### ConversationSession
**目的**: ユーザーとの一連の対話セッション管理

```sql
CREATE TABLE conversation_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME NULL,
    user_name TEXT NULL,
    total_exchanges INTEGER DEFAULT 0,
    session_status TEXT DEFAULT 'active' -- active, completed, interrupted
);
```

**バリデーション**:
- session_id: UUID v4形式
- session_status: enum('active', 'completed', 'interrupted')
- started_at ≤ ended_at

### ConversationExchange  
**目的**: 個別の発話と応答のペア

```sql
CREATE TABLE conversation_exchanges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    exchange_order INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    wake_word_confidence REAL,
    user_input TEXT NOT NULL,
    agent_response TEXT NOT NULL,
    response_time_ms INTEGER,
    voicevox_speaker_id INTEGER DEFAULT 1,
    langflow_flow_id TEXT,
    FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id)
);
```

**バリデーション**:
- wake_word_confidence: 0.0-1.0
- response_time_ms: > 0
- voicevox_speaker_id: VoiceVoxの有効なスピーカーID

### AgentSettings
**目的**: Yes-Manエージェントの設定管理

```sql
CREATE TABLE agent_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    data_type TEXT DEFAULT 'string', -- string, integer, float, boolean, json
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT DEFAULT 'system'
);
```

**主要設定項目**:
- `yes_man_personality_prompt`: メインキャラクタープロンプト
- `wake_word_confidence_threshold`: ウェイクワード信頼度閾値(0.8)
- `response_timeout_seconds`: 応答タイムアウト(30)
- `silence_detection_seconds`: 会話終了判定(5)
- `voicevox_default_speaker`: デフォルトスピーカーID

### ToolConfiguration
**目的**: 利用可能なツールの設定管理

```sql
CREATE TABLE tool_configurations (
    tool_name TEXT PRIMARY KEY,
    is_enabled BOOLEAN DEFAULT TRUE,
    priority_order INTEGER DEFAULT 0,
    config_json TEXT, -- ツール固有の設定JSON
    description TEXT,
    last_used_at DATETIME NULL,
    usage_count INTEGER DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**デフォルトツール**:
- `calculator`: 基本計算機能
- `timer`: タイマー機能
- `weather`: 天気情報（将来拡張）
- `datetime`: 日時情報

### AudioSettings
**目的**: 音声処理関連の設定

```sql
CREATE TABLE audio_settings (
    setting_name TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,
    setting_type TEXT DEFAULT 'string',
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**主要設定**:
- `microphone_device_id`: マイクデバイス識別子
- `whisper_model_size`: Whisperモデルサイズ(medium)
- `audio_buffer_seconds`: 音声バッファサイズ(3)
- `noise_reduction_enabled`: ノイズリダクション有効化
- `vad_sensitivity`: 音声検出感度

## 関係性

### セッション ← 交換
- 1つのConversationSessionは複数のConversationExchangeを持つ（1:N）
- session_idでリンク

### 設定 → 音声処理
- AgentSettings、AudioSettingsは全セッションで共有
- リアルタイム設定変更可能

### ツール ← 使用履歴
- ToolConfigurationは使用統計を管理
- last_used_at、usage_countで使用パターン分析

## 状態遷移

### セッション状態
```
[開始] → active → completed
         ↓
      interrupted
```

### 音声認識状態（アプリケーションレベル）
```
waiting → listening → processing → speaking → waiting
```

## インデックス

```sql
-- パフォーマンス最適化
CREATE INDEX idx_conversation_exchanges_session_timestamp 
ON conversation_exchanges(session_id, timestamp);

CREATE INDEX idx_conversation_exchanges_timestamp 
ON conversation_exchanges(timestamp);

CREATE INDEX idx_agent_settings_updated_at 
ON agent_settings(updated_at);

CREATE INDEX idx_tool_configurations_enabled_priority 
ON tool_configurations(is_enabled, priority_order);
```

## データ保持ポリシー

### 会話履歴
- **保持期間**: 90日間（設定可能）
- **削除方式**: 自動削除バッチ処理
- **プライバシー**: 音声データは保存しない、テキストのみ

### 設定データ
- **保持期間**: 永続（手動削除まで）
- **バックアップ**: 設定変更時の自動スナップショット

### 統計データ
- **保持期間**: 1年間
- **匿名化**: 個人識別情報除外

## データ移行

### 初期セットアップ
1. テーブル作成
2. デフォルト設定投入
3. 基本ツール設定
4. VoiceVoxスピーカー情報同期

### バージョンアップ
- SQLiteスキーママイグレーション
- 既存データ互換性保持
- 設定デフォルト値の更新