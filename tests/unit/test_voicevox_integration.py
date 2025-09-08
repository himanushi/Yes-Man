"""
Unit Tests for VoiceVox Integration
VoiceVox TTS統合モジュールのテスト

憲法II: テストファースト - Unit testによる品質保証
憲法I: プライバシー保護 - Yes-Man音声合成の安全性テスト
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import aiohttp
from audio_layer.voicevox_client import VoiceVoxClient, VoiceVoxError
import tempfile
import os


class TestVoiceVoxClient:
    """VoiceVoxClient単体テスト"""
    
    @pytest.fixture
    def voicevox_client(self):
        """VoiceVoxClientインスタンス"""
        return VoiceVoxClient(host="localhost", port=50021, speaker_id=1)
    
    @pytest.fixture
    def mock_speakers_response(self):
        """モックスピーカー情報"""
        return [
            {
                "name": "四国めたん",
                "speaker_uuid": "7ffcb7ce-00ec-4bdc-82cd-45a8889e43ff",
                "styles": [
                    {"name": "ノーマル", "id": 2, "type": "talk"},
                    {"name": "あまあま", "id": 0, "type": "talk"}
                ],
                "version": "0.14.0"
            },
            {
                "name": "ずんだもん",
                "speaker_uuid": "388f246b-8c41-4ac1-8e2d-5d79f3ff56d9", 
                "styles": [
                    {"name": "ノーマル", "id": 3, "type": "talk"},
                    {"name": "あまあま", "id": 1, "type": "talk"}
                ],
                "version": "0.14.0"
            }
        ]
    
    def test_voicevox_client_initialization(self):
        """VoiceVoxClient初期化テスト"""
        # デフォルト設定
        client = VoiceVoxClient()
        assert client.host == "localhost"
        assert client.port == 50021
        assert client.speaker_id == 1
        assert client.base_url == "http://localhost:50021"
        
        # カスタム設定
        client_custom = VoiceVoxClient(
            host="192.168.1.100",
            port=50022,
            speaker_id=3,
            timeout=15.0
        )
        assert client_custom.host == "192.168.1.100"
        assert client_custom.port == 50022
        assert client_custom.speaker_id == 3
        assert client_custom.timeout == 15.0
        assert client_custom.base_url == "http://192.168.1.100:50022"
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, voicevox_client, mock_speakers_response):
        """初期化成功テスト"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # バージョン情報モック
            version_response = Mock()
            version_response.status = 200
            version_response.text = AsyncMock(return_value="0.14.0")
            
            # スピーカー情報モック
            speakers_response = Mock()
            speakers_response.status = 200
            speakers_response.json = AsyncMock(return_value=mock_speakers_response)
            
            mock_get.side_effect = [version_response, speakers_response]
            
            success = await voicevox_client.initialize()
            
            assert success is True
            assert voicevox_client.version == "0.14.0"
            assert voicevox_client.speakers == mock_speakers_response
            assert voicevox_client.is_connected is True
    
    @pytest.mark.asyncio
    async def test_initialize_connection_error(self, voicevox_client):
        """接続エラー時の初期化テスト"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = aiohttp.ClientError("Connection refused")
            
            success = await voicevox_client.initialize()
            
            assert success is False
            assert voicevox_client.is_connected is False
    
    @pytest.mark.asyncio
    async def test_initialize_timeout_error(self, voicevox_client):
        """タイムアウトエラーテスト"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError()
            
            success = await voicevox_client.initialize()
            
            assert success is False
            assert voicevox_client.is_connected is False
    
    @pytest.mark.asyncio
    async def test_check_health_success(self, voicevox_client):
        """ヘルスチェック成功テスト"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            health_response = Mock()
            health_response.status = 200
            mock_get.return_value.__aenter__.return_value = health_response
            
            is_healthy = await voicevox_client.check_health()
            
            assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_check_health_failure(self, voicevox_client):
        """ヘルスチェック失敗テスト"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = aiohttp.ClientError("Service unavailable")
            
            is_healthy = await voicevox_client.check_health()
            
            assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_success(self, voicevox_client):
        """音声合成成功テスト"""
        text = "はい！こんにちは、Yes-Manです！"
        mock_audio_data = b"mock_audio_data_wav_format"
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # audio_query レスポンス
            query_response = Mock()
            query_response.status = 200
            query_response.json = AsyncMock(return_value={
                "accent_phrases": [],
                "speedScale": 1.0,
                "pitchScale": 0.0,
                "intonationScale": 1.0,
                "volumeScale": 1.0,
                "prePhonemeLength": 0.1,
                "postPhonemeLength": 0.1,
                "outputSamplingRate": 24000,
                "outputStereo": False,
                "kana": "ハイ！コンニチハ、イエスマンデス！"
            })
            
            # synthesis レスポンス
            synthesis_response = Mock()
            synthesis_response.status = 200
            synthesis_response.read = AsyncMock(return_value=mock_audio_data)
            
            mock_post.side_effect = [
                AsyncMock(__aenter__=AsyncMock(return_value=query_response)),
                AsyncMock(__aenter__=AsyncMock(return_value=synthesis_response))
            ]
            
            result = await voicevox_client.synthesize_speech(text)
            
            assert result['success'] is True
            assert result['audio_data'] == mock_audio_data
            assert result['text'] == text
            assert result['speaker_id'] == 1
            assert result['format'] == 'wav'
            assert result['duration'] > 0
            
            # プライバシー保護チェック
            assert 'internal_query' not in result
            assert 'raw_response' not in result
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_empty_text(self, voicevox_client):
        """空テキストの音声合成テスト"""
        result = await voicevox_client.synthesize_speech("")
        
        assert result['success'] is False
        assert 'empty' in result['error'].lower()
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_long_text(self, voicevox_client):
        """長文テキストの音声合成テスト"""
        # 1000文字の長文
        long_text = "はい！" * 200  # 1000文字
        
        with patch.object(voicevox_client, '_synthesize_chunk') as mock_chunk:
            mock_chunk.return_value = {
                'success': True,
                'audio_data': b'mock_chunk_data',
                'duration': 2.0
            }
            
            result = await voicevox_client.synthesize_speech(long_text)
            
            assert result['success'] is True
            # 複数チャンクに分割されることを確認
            assert mock_chunk.call_count > 1
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_query_error(self, voicevox_client):
        """audio_queryエラーテスト"""
        text = "テストテキスト"
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # audio_query エラーレスポンス
            query_response = Mock()
            query_response.status = 400
            query_response.text = AsyncMock(return_value="Bad Request")
            
            mock_post.return_value.__aenter__.return_value = query_response
            
            result = await voicevox_client.synthesize_speech(text)
            
            assert result['success'] is False
            assert 'audio_query' in result['error'].lower()
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_synthesis_error(self, voicevox_client):
        """synthesis APIエラーテスト"""
        text = "テストテキスト"
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # audio_query 成功
            query_response = Mock()
            query_response.status = 200
            query_response.json = AsyncMock(return_value={"speedScale": 1.0})
            
            # synthesis エラー
            synthesis_response = Mock()
            synthesis_response.status = 500
            synthesis_response.text = AsyncMock(return_value="Internal Server Error")
            
            mock_post.side_effect = [
                AsyncMock(__aenter__=AsyncMock(return_value=query_response)),
                AsyncMock(__aenter__=AsyncMock(return_value=synthesis_response))
            ]
            
            result = await voicevox_client.synthesize_speech(text)
            
            assert result['success'] is False
            assert 'synthesis' in result['error'].lower()
    
    @pytest.mark.asyncio
    async def test_get_speakers_success(self, voicevox_client, mock_speakers_response):
        """スピーカー情報取得成功テスト"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            speakers_response = Mock()
            speakers_response.status = 200
            speakers_response.json = AsyncMock(return_value=mock_speakers_response)
            mock_get.return_value.__aenter__.return_value = speakers_response
            
            speakers = await voicevox_client.get_speakers()
            
            assert speakers == mock_speakers_response
            assert len(speakers) == 2
            assert speakers[0]['name'] == "四国めたん"
            assert speakers[1]['name'] == "ずんだもん"
    
    @pytest.mark.asyncio
    async def test_get_speakers_error(self, voicevox_client):
        """スピーカー情報取得エラーテスト"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = aiohttp.ClientError("Network error")
            
            speakers = await voicevox_client.get_speakers()
            
            assert speakers == []
    
    def test_set_speaker_id_valid(self, voicevox_client):
        """有効スピーカーID設定テスト"""
        voicevox_client.set_speaker_id(3)
        assert voicevox_client.speaker_id == 3
    
    def test_set_speaker_id_invalid(self, voicevox_client):
        """無効スピーカーID設定テスト"""
        with pytest.raises(ValueError, match="Speaker ID must be non-negative"):
            voicevox_client.set_speaker_id(-1)
    
    def test_set_speech_parameters_valid(self, voicevox_client):
        """音声パラメータ設定テスト"""
        voicevox_client.set_speech_parameters(
            speed_scale=1.5,
            pitch_scale=0.2,
            intonation_scale=1.2,
            volume_scale=0.8
        )
        
        assert voicevox_client.speech_parameters['speedScale'] == 1.5
        assert voicevox_client.speech_parameters['pitchScale'] == 0.2
        assert voicevox_client.speech_parameters['intonationScale'] == 1.2
        assert voicevox_client.speech_parameters['volumeScale'] == 0.8
    
    def test_set_speech_parameters_invalid(self, voicevox_client):
        """無効音声パラメータ設定テスト"""
        with pytest.raises(ValueError, match="Speed scale must be positive"):
            voicevox_client.set_speech_parameters(speed_scale=0)
        
        with pytest.raises(ValueError, match="Volume scale must be between 0 and 2"):
            voicevox_client.set_speech_parameters(volume_scale=3.0)
    
    def test_split_text_into_chunks(self, voicevox_client):
        """テキストチャンク分割テスト"""
        # 短いテキスト
        short_text = "短いテキストです。"
        chunks = voicevox_client._split_text_into_chunks(short_text, max_length=100)
        assert len(chunks) == 1
        assert chunks[0] == short_text
        
        # 長いテキスト
        long_text = "これは非常に長いテキストです。" * 10
        chunks = voicevox_client._split_text_into_chunks(long_text, max_length=50)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 50
    
    def test_estimate_duration(self, voicevox_client):
        """再生時間推定テスト"""
        # 日本語テキスト
        text = "はい、こんにちはYes-Manです！"
        duration = voicevox_client._estimate_duration(text)
        
        assert duration > 0
        assert duration < 10  # 10秒以下の妥当な推定値
    
    def test_validate_text_success(self, voicevox_client):
        """テキスト検証成功テスト"""
        valid_text = "こんにちは、Yes-Manです！"
        
        # 例外が発生しないことを確認
        voicevox_client._validate_text(valid_text)
    
    def test_validate_text_empty(self, voicevox_client):
        """空テキスト検証テスト"""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            voicevox_client._validate_text("")
    
    def test_validate_text_too_long(self, voicevox_client):
        """長すぎるテキスト検証テスト"""
        long_text = "あ" * 1001  # 1001文字
        
        with pytest.raises(ValueError, match="Text is too long"):
            voicevox_client._validate_text(long_text)
    
    @pytest.mark.asyncio
    async def test_cleanup_success(self, voicevox_client):
        """クリーンアップ成功テスト"""
        # セッション開始状態をモック
        voicevox_client.session = Mock()
        voicevox_client.session.close = AsyncMock()
        
        await voicevox_client.cleanup()
        
        assert voicevox_client.session is None
        assert voicevox_client.is_connected is False
    
    def test_get_client_info(self, voicevox_client):
        """クライアント情報取得テスト"""
        info = voicevox_client.get_client_info()
        
        assert 'host' in info
        assert 'port' in info
        assert 'speaker_id' in info
        assert 'is_connected' in info
        assert 'version' in info
        assert info['host'] == "localhost"
        assert info['port'] == 50021
        assert info['speaker_id'] == 1
    
    def test_get_performance_metrics(self, voicevox_client):
        """パフォーマンス指標取得テスト"""
        metrics = voicevox_client.get_performance_metrics()
        
        assert 'total_syntheses' in metrics
        assert 'average_synthesis_time' in metrics
        assert 'success_rate' in metrics
        assert 'total_audio_duration' in metrics
        assert metrics['total_syntheses'] >= 0
        assert metrics['average_synthesis_time'] >= 0.0
        assert 0.0 <= metrics['success_rate'] <= 1.0


class TestVoiceVoxError:
    """VoiceVoxError例外テスト"""
    
    def test_voicevox_error_creation(self):
        """VoiceVoxError作成テスト"""
        error = VoiceVoxError("Test error message")
        
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_voicevox_error_with_cause(self):
        """原因付きVoiceVoxErrorテスト"""
        original_error = aiohttp.ClientError("Network error")
        error = VoiceVoxError("VoiceVox synthesis failed", original_error)
        
        assert "VoiceVox synthesis failed" in str(error)
        assert error.__cause__ == original_error


class TestVoiceVoxIntegrationPrivacy:
    """プライバシー保護テスト（憲法I準拠）"""
    
    @pytest.fixture
    def voicevox_client(self):
        return VoiceVoxClient()
    
    @pytest.mark.asyncio
    async def test_no_text_logging(self, voicevox_client):
        """テキスト内容ログ出力なしテスト"""
        text = "秘密の情報を含むテキスト"
        
        with patch('audio_layer.voicevox_client.logger') as mock_logger:
            # 合成失敗をシミュレート
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_post.side_effect = aiohttp.ClientError("Network error")
                
                await voicevox_client.synthesize_speech(text)
                
                # ログにテキスト内容が含まれていないことを確認
                logged_messages = []
                for call in mock_logger.error.call_args_list + mock_logger.warning.call_args_list:
                    logged_messages.extend(call[0])
                
                for message in logged_messages:
                    assert "秘密の情報" not in str(message)
    
    @pytest.mark.asyncio
    async def test_no_temporary_audio_files(self, voicevox_client):
        """一時音声ファイル非作成テスト"""
        text = "テストテキスト"
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # 成功レスポンスをモック
            query_response = Mock()
            query_response.status = 200
            query_response.json = AsyncMock(return_value={"speedScale": 1.0})
            
            synthesis_response = Mock()
            synthesis_response.status = 200
            synthesis_response.read = AsyncMock(return_value=b"mock_audio_data")
            
            mock_post.side_effect = [
                AsyncMock(__aenter__=AsyncMock(return_value=query_response)),
                AsyncMock(__aenter__=AsyncMock(return_value=synthesis_response))
            ]
            
            # 処理前後で一時ディレクトリをチェック
            temp_dir = tempfile.gettempdir()
            files_before = set(os.listdir(temp_dir))
            
            result = await voicevox_client.synthesize_speech(text)
            
            files_after = set(os.listdir(temp_dir))
            new_files = files_after - files_before
            
            # 新しい音声ファイルが作成されていないことを確認
            audio_files = [f for f in new_files if any(ext in f.lower() for ext in ['.wav', '.mp3', '.audio'])]
            assert len(audio_files) == 0
    
    def test_sensitive_data_not_stored(self, voicevox_client):
        """機密データ非保存テスト"""
        # クライアント内部に機密データが保存されていないことを確認
        client_vars = vars(voicevox_client)
        
        sensitive_keys = ['password', 'token', 'key', 'secret', 'credential']
        for key, value in client_vars.items():
            for sensitive in sensitive_keys:
                assert sensitive not in key.lower()


@pytest.mark.integration
class TestVoiceVoxIntegrationPerformance:
    """パフォーマンステスト（憲法VI準拠）"""
    
    @pytest.fixture
    def voicevox_client(self):
        return VoiceVoxClient()
    
    @pytest.mark.asyncio
    async def test_initialization_speed(self, voicevox_client):
        """初期化速度テスト"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            version_response = Mock()
            version_response.status = 200
            version_response.text = AsyncMock(return_value="0.14.0")
            
            speakers_response = Mock()
            speakers_response.status = 200
            speakers_response.json = AsyncMock(return_value=[])
            
            mock_get.side_effect = [version_response, speakers_response]
            
            import time
            start_time = time.time()
            await voicevox_client.initialize()
            end_time = time.time()
            
            initialization_time = end_time - start_time
            
            # 初期化は3秒以内に完了
            assert initialization_time < 3.0
    
    @pytest.mark.asyncio
    async def test_synthesis_speed(self, voicevox_client):
        """音声合成速度テスト"""
        text = "はい！こんにちは、Yes-Manです！今日もお疲れ様です！"
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # 標準的な合成時間をシミュレート
            async def mock_synthesis_delay(*args, **kwargs):
                await asyncio.sleep(0.5)  # 0.5秒の処理時間
                response = Mock()
                response.status = 200
                if 'audio_query' in str(args):
                    response.json = AsyncMock(return_value={"speedScale": 1.0})
                else:
                    response.read = AsyncMock(return_value=b"mock_audio_data")
                return AsyncMock(__aenter__=AsyncMock(return_value=response))
            
            mock_post.side_effect = mock_synthesis_delay
            
            import time
            start_time = time.time()
            result = await voicevox_client.synthesize_speech(text)
            end_time = time.time()
            
            synthesis_time = end_time - start_time
            
            # 音声合成は2秒以内に完了（憲法VI: TTS 1.5秒以内の余裕を含む）
            assert synthesis_time < 2.0
            assert result['success'] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_synthesis(self, voicevox_client):
        """並行音声合成テスト"""
        texts = [
            "はい！テスト1です！",
            "もちろん！テスト2ですね！",
            "そうです！テスト3です！"
        ]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            async def mock_response(*args, **kwargs):
                response = Mock()
                response.status = 200
                if 'audio_query' in str(args):
                    response.json = AsyncMock(return_value={"speedScale": 1.0})
                else:
                    response.read = AsyncMock(return_value=b"mock_audio_data")
                return AsyncMock(__aenter__=AsyncMock(return_value=response))
            
            mock_post.side_effect = mock_response
            
            import time
            start_time = time.time()
            
            # 並行実行
            tasks = [voicevox_client.synthesize_speech(text) for text in texts]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # 並行処理により、シーケンシャルよりも高速
            assert total_time < 3.0  # 3つの合成を3秒以内
            assert all(result['success'] for result in results)
    
    @pytest.mark.asyncio
    async def test_memory_efficiency(self, voicevox_client):
        """メモリ効率テスト"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # 複数回音声合成実行
        text = "メモリ効率テスト用のテキストです。"
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            async def mock_response(*args, **kwargs):
                response = Mock()
                response.status = 200
                if 'audio_query' in str(args):
                    response.json = AsyncMock(return_value={"speedScale": 1.0})
                else:
                    # 1MBのモック音声データ
                    response.read = AsyncMock(return_value=b"x" * (1024 * 1024))
                return AsyncMock(__aenter__=AsyncMock(return_value=response))
            
            mock_post.side_effect = mock_response
            
            for _ in range(10):
                result = await voicevox_client.synthesize_speech(text)
                assert result['success'] is True
                gc.collect()  # 強制ガベージコレクション
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        # メモリ増加は20MB以下に抑制
        assert memory_increase_mb < 20.0


@pytest.mark.integration  
class TestVoiceVoxYesManIntegration:
    """Yes-Man固有統合テスト"""
    
    @pytest.fixture
    def voicevox_client(self):
        return VoiceVoxClient()
    
    @pytest.mark.asyncio
    async def test_yes_man_style_synthesis(self, voicevox_client):
        """Yes-Man風音声合成テスト"""
        yes_man_texts = [
            "はい！もちろんです！",
            "そうですね！喜んでお手伝いします！",
            "はい、承知いたしました！すぐに対応しますよ！",
            "もちろんです！それは素晴らしいアイデアですね！"
        ]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            async def mock_response(*args, **kwargs):
                response = Mock()
                response.status = 200
                if 'audio_query' in str(args):
                    response.json = AsyncMock(return_value={"speedScale": 1.0})
                else:
                    response.read = AsyncMock(return_value=b"yes_man_audio_data")
                return AsyncMock(__aenter__=AsyncMock(return_value=response))
            
            mock_post.side_effect = mock_response
            
            for text in yes_man_texts:
                result = await voicevox_client.synthesize_speech(text)
                
                assert result['success'] is True
                assert result['audio_data'] == b"yes_man_audio_data"
                assert result['text'] == text
                assert result['character'] == 'Yes-Man'


if __name__ == "__main__":
    # テスト実行
    pytest.main([__file__, "-v", "--tb=short"])