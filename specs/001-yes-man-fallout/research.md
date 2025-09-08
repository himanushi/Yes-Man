# 研究報告: Yes-Man音声対話システム

## 研究課題解決

### TTS音声エンジン選択
**Decision**: VoiceVox ローカルAPI使用  
**Rationale**: 
- 完全ローカル実行でプライバシー保護
- 日本語音声の高品質
- キャラクターボイス選択可能
- REST API簡単統合
- 無料利用可能

**Alternatives considered**: 
- Windows SAPI: 品質が低い
- Azure Speech: クラウド依存、有料
- Google TTS: クラウド依存、プライバシー問題

### Yes-Man具体的性格特性・台詞パターン
**Decision**: 陽気で協力的、肯定的な応答パターン  
**Rationale**: 
- Fallout NewVegasオリジナルキャラクターに忠実
- 「はい！」「もちろんです！」「喜んで！」等の頻繁な肯定表現
- 丁寧語使用だが親しみやすい口調
- 失敗やエラーも前向きに表現

**Alternatives considered**: 
- より正式な敬語: キャラクター性が薄れる
- カジュアル口調: ゲームキャラクターとの乖離

### 対応言語
**Decision**: 日本語メイン、英語サブサポート  
**Rationale**: 
- VoiceVoxは日本語特化
- Whisper.cppは多言語対応だが日本語で最適化
- 開発効率とメンテナンス性重視

**Alternatives considered**: 
- 多言語対応: 開発コスト増、品質分散
- 英語のみ: 日本語ユーザー除外

## 技術選択研究

### Whisper.cpp最適化設定
**Decision**: mediumモデル + CUDA最適化  
**Rationale**: 
- GTX 4060で十分な性能
- 精度と速度のバランス
- 常時監視に適したメモリ効率

**Best practices**: 
- 3秒循環バッファでメモリ管理
- GPU並列処理で低レイテンシ
- VAD併用で省電力化

### LangFlow統合パターン
**Decision**: REST API経由での統合  
**Rationale**: 
- 疎結合でメンテナンス性向上
- LangFlow独立アップデート可能
- エラー時の影響範囲限定

**Best practices**: 
- SQLiteデータベース共有
- フロー設定のバージョン管理
- API障害時のフォールバック

### Electron音声連携
**Decision**: IPC (Inter-Process Communication)  
**Rationale**: 
- Python ↔ JavaScript間の効率的通信
- リアルタイム音声状態同期
- セキュアな内部通信

**Best practices**: 
- ZeroMQ使用でメッセージキュー
- 音声状態の4段階管理（待機、聞取中、処理中、発話中）
- エラー時の自動復旧機能

## パフォーマンス最適化研究

### CPU使用率30%以下達成
**Decision**: マルチレベル最適化戦略  
**Approaches**: 
- Whisper.cpp C++実装の効率性活用
- VAD使用による無音時処理停止
- GPU処理でCPU負荷軽減
- 循環バッファでメモリ効率化

### 常時監視プライバシー保護
**Decision**: メモリ内循環バッファ + 完全削除  
**Implementation**: 
- 3秒固定サイズバッファ
- ウェイクワード検出まで一時保存のみ
- プロセス終了時メモリ完全クリア
- ディスク書き込み完全禁止

## 統合アーキテクチャ結論

### システム構成
```
[マイク] → [Whisper.cpp] → [ウェイクワード検出] 
    ↓
[音声認識] → [LangFlow API] → [Yes-Man応答生成]
    ↓
[VoiceVox API] → [音声合成] → [スピーカー]
    ↓
[Electron IPC] → [顔アニメーション表示]
```

### データフロー
1. 循環音声バッファ（メモリ内3秒）
2. ウェイクワード検出（信頼度0.8+）
3. 継続音声録音→テキスト変換
4. LangFlowエージェント実行
5. SQLite会話履歴保存
6. VoiceVox音声生成
7. Electron顔アニメ連動

**全NEEDS CLARIFICATION解決完了** ✅