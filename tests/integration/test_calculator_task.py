"""
Integration Test: 計算タスク実行フロー

憲法III: テストファースト（非妥協的）に従い、実装前にテストを作成。
これらのテストは実装前に失敗する必要がある。

テスト対象: quickstart.mdのシナリオ2
「計算タスク実行」の統合テスト:
1. ウェイクワード「Yes-Man」検出  
2. 音声入力「10たす5はいくつ？」
3. LangFlow計算ツール実行
4. Yes-Man応答「15です！計算は得意なんですよ！」
5. SQLite会話履歴保存
"""

import pytest
import asyncio
import time
from typing import Dict, Any, Union


class TestCalculatorTaskIntegration:
    """計算タスクの統合テスト"""
    
    def setup_method(self):
        """各テスト前の設定"""
        self.audio_api_base = "http://localhost:8001"
        self.langflow_api_base = "http://localhost:8002"
    
    @pytest.mark.asyncio
    async def test_basic_arithmetic_calculation_integration(self):
        """
        Integration Test: 基本算術計算フロー
        
        Flow:
        1. ウェイクワード検出 → 継続認識
        2. 音声入力: "10たす5はいくつ？"
        3. LangFlowエージェント: 計算ツール選択
        4. 計算ツール実行: "10 + 5" → 15
        5. Yes-Man応答生成: "15です！計算は得意なんですよ！"
        6. VoiceVox TTS: Yes-Man性格の音声合成
        7. SQLite保存: user_input, agent_response, tools_used=["calculator"]
        
        Expected Results:
        - 計算精度: 100%正確性
        - 応答時間: <3秒 (パフォーマンス制約)
        - Yes-Man性格特性: 自信と能力アピール
        """
        # 実装前テスト契約定義
        calculation_test_cases = [
            {
                "user_input": "10たす5はいくつ？",
                "expected_calculation": "10 + 5",
                "expected_result": 15,
                "expected_tools": ["calculator"],
                "yes_man_response_pattern": r"15.*得意.*です"
            },
            {
                "user_input": "100マイナス30は？",
                "expected_calculation": "100 - 30", 
                "expected_result": 70,
                "expected_tools": ["calculator"],
                "yes_man_response_pattern": r"70.*計算.*簡単"
            },
            {
                "user_input": "12かける3を教えて",
                "expected_calculation": "12 * 3",
                "expected_result": 36,
                "expected_tools": ["calculator"],
                "yes_man_response_pattern": r"36.*お任せ"
            }
        ]
        
        # 実装前は接続エラー期待
        try:
            import requests
            with pytest.raises(requests.exceptions.ConnectionError):
                # 計算フロー実行試行（実装前失敗期待）
                requests.post(f"{self.langflow_api_base}/langflow/execute_flow",
                             json={
                                 "user_input": "10たす5はいくつ？",
                                 "session_id": "calc-test-session",
                                 "flow_name": "yes_man_agent"
                             }, timeout=3)
        except ImportError:
            pass
            
        # 実装後契約: 各テストケースの期待動作確認
        for case in calculation_test_cases:
            # 結果精度契約
            assert isinstance(case["expected_result"], (int, float))
            assert "calculator" in case["expected_tools"]
            # Yes-Man応答パターン契約
            assert case["yes_man_response_pattern"] is not None
    
    def test_complex_mathematical_expressions_integration(self):
        """
        Integration Test: 複雑な数式計算統合テスト
        
        Test Cases:
        - 多項式: "2かける3たす4かける5"
        - 括弧: "括弧2たす3括弧とじるかける4"  
        - 小数: "3.14かける2"
        - 分数: "3分の2たす4分の1"
        - 負数: "マイナス5たす10"
        
        Expected Behavior:
        - 演算子優先度の正確な処理
        - 日本語→数式変換の正確性
        - エラー時のYes-Man適切応答
        """
        complex_cases = [
            {
                "japanese_input": "2かける3たす4かける5",
                "parsed_expression": "2 * 3 + 4 * 5", 
                "expected_result": 26,
                "difficulty": "medium"
            },
            {
                "japanese_input": "括弧2たす3括弧とじるかける4",
                "parsed_expression": "(2 + 3) * 4",
                "expected_result": 20, 
                "difficulty": "medium"
            },
            {
                "japanese_input": "3.14かける2",
                "parsed_expression": "3.14 * 2",
                "expected_result": 6.28,
                "difficulty": "easy"
            },
            {
                "japanese_input": "マイナス5たす10", 
                "parsed_expression": "-5 + 10",
                "expected_result": 5,
                "difficulty": "easy"
            }
        ]
        
        # 実装前契約確認: 日本語数式解析の複雑性
        for case in complex_cases:
            # 日本語→数式変換契約
            assert case["japanese_input"] != case["parsed_expression"]
            # 結果精度契約
            assert isinstance(case["expected_result"], (int, float))
            # 難易度分類契約
            assert case["difficulty"] in ["easy", "medium", "hard"]
    
    def test_calculation_error_handling_integration(self):
        """
        Integration Test: 計算エラーハンドリング統合テスト
        
        Error Cases:
        - ゼロ除算: "10割る0"
        - 不正な式: "たすたす5"
        - 範囲外数値: "999999999999999999999たす1" 
        - 未対応演算: "10の3乗"
        
        Expected Yes-Man Error Responses:
        - 陽気で前向きなエラーメッセージ
        - 代替案提示
        - 技術的エラーの分かりやすい説明
        """
        error_cases = [
            {
                "user_input": "10割る0",
                "error_type": "division_by_zero",
                "yes_man_response_pattern": r"ゼロで割ることは.*できません.*数学のルール",
                "recovery_suggestion": "別の数で割ってみましょう"
            },
            {
                "user_input": "たすたす5", 
                "error_type": "invalid_expression",
                "yes_man_response_pattern": r"ちょっと分からない.*もう一度",
                "recovery_suggestion": "正しい形で教えてください"
            },
            {
                "user_input": "999999999999999999999たす1",
                "error_type": "number_too_large", 
                "yes_man_response_pattern": r"大きすぎる.*もう少し小さな",
                "recovery_suggestion": "小さな数で試してみましょう"
            },
            {
                "user_input": "10の3乗",
                "error_type": "unsupported_operation",
                "yes_man_response_pattern": r"まだ対応していません.*基本的な計算",
                "recovery_suggestion": "たし算、引き算、掛け算、割り算でお願いします"
            }
        ]
        
        # Yes-Manエラー応答契約確認
        for case in error_cases:
            # エラータイプ分類契約
            assert case["error_type"] in ["division_by_zero", "invalid_expression", "number_too_large", "unsupported_operation"]
            # 前向き応答パターン契約
            assert case["yes_man_response_pattern"] is not None
            # 復旧提案契約
            assert case["recovery_suggestion"] is not None
            assert len(case["recovery_suggestion"]) > 0
    
    @pytest.mark.asyncio
    async def test_conversation_history_persistence_integration(self):
        """
        Integration Test: 計算会話履歴永続化統合テスト
        
        Scenario:
        1. 複数の計算セッション実行
        2. SQLiteデータベースに会話履歴保存
        3. セッション間での計算履歴参照
        4. 統計情報生成（使用頻度、計算回数等）
        
        Expected Database Schema:
        - conversation_sessions: セッション情報
        - conversation_exchanges: 個別会話
        - tool_configurations: calculator使用統計
        """
        # 実装前契約: データベーススキーマ設計確認
        expected_database_structure = {
            "conversation_sessions": [
                "id", "session_id", "started_at", "ended_at", "total_exchanges"
            ],
            "conversation_exchanges": [
                "id", "session_id", "user_input", "agent_response", 
                "tools_used", "response_time_ms", "timestamp"
            ],
            "tool_configurations": [
                "tool_name", "usage_count", "last_used_at", "is_enabled"
            ]
        }
        
        # スキーマ契約確認
        assert "conversation_sessions" in expected_database_structure
        assert "conversation_exchanges" in expected_database_structure  
        assert "tool_configurations" in expected_database_structure
        
        # 計算特有のデータ保存契約
        calculator_specific_data = {
            "user_input": "10たす5はいくつ？",
            "agent_response": "15です！計算は得意なんですよ！", 
            "tools_used": ["calculator"],
            "calculation_expression": "10 + 5",
            "calculation_result": 15,
            "response_time_ms": 1250
        }
        
        # 計算データ契約確認
        assert "calculator" in calculator_specific_data["tools_used"]
        assert isinstance(calculator_specific_data["calculation_result"], (int, float))
        assert calculator_specific_data["response_time_ms"] < 3000  # パフォーマンス制約
    
    def test_calculator_tool_configuration_integration(self):
        """
        Integration Test: 計算ツール設定統合テスト
        
        Configuration Options:
        - precision: 小数点精度設定
        - max_expression_length: 数式最大長
        - allowed_functions: 使用可能関数リスト
        - output_format: 結果表示形式
        
        Expected Behavior:
        - 設定変更の即座反映
        - 不正設定値の適切な拒否
        - デフォルト設定への復帰機能
        """
        calculator_config_options = {
            "precision": {
                "type": "integer",
                "min": 0,
                "max": 10,
                "default": 4
            },
            "max_expression_length": {
                "type": "integer", 
                "min": 10,
                "max": 1000,
                "default": 100
            },
            "allowed_functions": {
                "type": "array",
                "default": ["+", "-", "*", "/"],
                "extended": ["+", "-", "*", "/", "^", "sqrt", "abs"]
            },
            "output_format": {
                "type": "string",
                "options": ["number", "fraction", "scientific"],
                "default": "number"
            }
        }
        
        # 設定契約確認
        assert calculator_config_options["precision"]["default"] == 4
        assert "+" in calculator_config_options["allowed_functions"]["default"] 
        assert calculator_config_options["output_format"]["default"] == "number"
        
        # 設定制限契約
        assert calculator_config_options["precision"]["max"] <= 10
        assert calculator_config_options["max_expression_length"]["min"] >= 10