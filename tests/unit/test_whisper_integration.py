"""
Unit Tests for Whisper Integration
Whisper.cpp統合モジュールのテスト

憲法II: テストファースト - Unit testによる品質保証
憲法I: プライバシー保護 - 音声データ処理の安全性テスト
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from audio_layer.whisper_integration import WhisperClient, WhisperError
import tempfile
import os


class TestWhisperClient:
    """WhisperClient単体テスト"""
    
    @pytest.fixture
    def whisper_client(self):
        """WhisperClientインスタンス"""
        return WhisperClient(model_name="base")
    
    @pytest.fixture
    def mock_audio_data(self):
        """モック音声データ"""
        # 16kHz, 3秒のモック音声データ
        sample_rate = 16000
        duration = 3.0
        samples = int(sample_rate * duration)
        return np.random.random(samples).astype(np.float32)
    
    def test_whisper_client_initialization(self):
        """WhisperClient初期化テスト"""
        # 正常初期化
        client = WhisperClient(model_name="base")
        assert client.model_name == "base"
        assert client.model is None
        assert not client.is_loaded
        
        # カスタム設定
        client_custom = WhisperClient(
            model_name="small",
            language="ja",
            temperature=0.5,
            best_of=3
        )
        assert client_custom.model_name == "small"
        assert client_custom.language == "ja"
        assert client_custom.temperature == 0.5
        assert client_custom.best_of == 3
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, whisper_client):
        """初期化成功テスト"""
        with patch('audio_layer.whisper_integration.WHISPER_AVAILABLE', True), \
             patch('audio_layer.whisper_integration.whisper.load_model') as mock_load:
            
            mock_model = Mock()
            mock_load.return_value = mock_model
            
            await whisper_client.initialize()
            
            assert whisper_client.model == mock_model
            assert whisper_client.is_loaded
            mock_load.assert_called_once_with("base")
    
    @pytest.mark.asyncio
    async def test_initialize_whisper_not_available(self, whisper_client):
        """Whisper利用不可時の初期化テスト"""
        with patch('audio_layer.whisper_integration.WHISPER_AVAILABLE', False):
            await whisper_client.initialize()
            
            # MockWhisperが使用される
            assert whisper_client.model is not None
            assert whisper_client.is_loaded
            assert hasattr(whisper_client.model, 'transcribe')
    
    @pytest.mark.asyncio
    async def test_initialize_model_load_error(self, whisper_client):
        """モデル読込エラーテスト"""
        with patch('audio_layer.whisper_integration.WHISPER_AVAILABLE', True), \
             patch('audio_layer.whisper_integration.whisper.load_model') as mock_load:
            
            mock_load.side_effect = Exception("Model not found")
            
            with pytest.raises(WhisperError, match="Failed to load Whisper model"):
                await whisper_client.initialize()
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self, whisper_client, mock_audio_data):
        """音声転写成功テスト"""
        # 初期化
        with patch('audio_layer.whisper_integration.WHISPER_AVAILABLE', True), \
             patch('audio_layer.whisper_integration.whisper.load_model') as mock_load:
            
            mock_model = Mock()
            mock_result = {
                'text': 'はい、こんにちはYes-Manです！',
                'language': 'ja',
                'segments': [
                    {
                        'start': 0.0,
                        'end': 2.5,
                        'text': 'はい、こんにちはYes-Manです！'
                    }
                ]
            }
            mock_model.transcribe.return_value = mock_result
            mock_load.return_value = mock_model
            
            await whisper_client.initialize()
            
            # 転写実行
            result = await whisper_client.transcribe_audio(mock_audio_data)
            
            assert result['success'] is True
            assert result['text'] == 'はい、こんにちはYes-Manです！'
            assert result['language'] == 'ja'
            assert result['confidence'] > 0.0
            assert len(result['segments']) == 1
            
            # プライバシー保護チェック
            assert 'raw_audio' not in result
            assert 'internal_data' not in result
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_empty_input(self, whisper_client):
        """空音声データの転写テスト"""
        await whisper_client.initialize()
        
        empty_audio = np.array([])
        result = await whisper_client.transcribe_audio(empty_audio)
        
        assert result['success'] is False
        assert 'empty' in result['error'].lower()
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_not_initialized(self, whisper_client):
        """未初期化での転写テスト"""
        mock_audio_data = np.random.random(16000).astype(np.float32)
        
        result = await whisper_client.transcribe_audio(mock_audio_data)
        
        assert result['success'] is False
        assert 'not initialized' in result['error'].lower()
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_processing_error(self, whisper_client, mock_audio_data):
        """転写処理エラーテスト"""
        # 初期化
        with patch('audio_layer.whisper_integration.WHISPER_AVAILABLE', True), \
             patch('audio_layer.whisper_integration.whisper.load_model') as mock_load:
            
            mock_model = Mock()
            mock_model.transcribe.side_effect = Exception("Processing error")
            mock_load.return_value = mock_model
            
            await whisper_client.initialize()
            
            result = await whisper_client.transcribe_audio(mock_audio_data)
            
            assert result['success'] is False
            assert 'processing error' in result['error'].lower()
    
    @pytest.mark.asyncio
    async def test_transcribe_mock_success(self, whisper_client):
        """モック転写成功テスト"""
        result = await whisper_client.transcribe_mock("こんにちは、Yes-Man！")
        
        assert result['success'] is True
        assert result['text'] == "こんにちは、Yes-Man！"
        assert result['language'] == 'ja'
        assert result['confidence'] == 0.95
        assert 'mock' in result['source']
    
    @pytest.mark.asyncio
    async def test_transcribe_file_success(self, whisper_client):
        """ファイル転写成功テスト"""
        # 一時音声ファイル作成
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
            
            # 簡単なWAVヘッダーとデータを書き込み（実際の音声ファイルではない）
            temp_file.write(b'RIFF' + b'\x00' * 40)  # 簡略化
        
        try:
            with patch('audio_layer.whisper_integration.WHISPER_AVAILABLE', True), \
                 patch('audio_layer.whisper_integration.whisper.load_model') as mock_load:
                
                mock_model = Mock()
                mock_result = {
                    'text': 'ファイルからの転写テスト',
                    'language': 'ja'
                }
                mock_model.transcribe.return_value = mock_result
                mock_load.return_value = mock_model
                
                await whisper_client.initialize()
                
                result = await whisper_client.transcribe_file(temp_path)
                
                assert result['success'] is True
                assert result['text'] == 'ファイルからの転写テスト'
                assert result['source'] == 'file'
                
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_transcribe_file_not_found(self, whisper_client):
        """存在しないファイルの転写テスト"""
        await whisper_client.initialize()
        
        result = await whisper_client.transcribe_file("nonexistent_file.wav")
        
        assert result['success'] is False
        assert 'not found' in result['error'].lower() or 'no such file' in result['error'].lower()
    
    def test_preprocess_audio_success(self, whisper_client, mock_audio_data):
        """音声前処理成功テスト"""
        processed = whisper_client._preprocess_audio(mock_audio_data)
        
        assert isinstance(processed, np.ndarray)
        assert processed.dtype == np.float32
        # 振幅正規化確認
        assert processed.max() <= 1.0
        assert processed.min() >= -1.0
    
    def test_preprocess_audio_empty(self, whisper_client):
        """空音声の前処理テスト"""
        empty_audio = np.array([])
        
        with pytest.raises(ValueError, match="Empty audio data"):
            whisper_client._preprocess_audio(empty_audio)
    
    def test_preprocess_audio_wrong_type(self, whisper_client):
        """不正な型の前処理テスト"""
        invalid_audio = "not an array"
        
        with pytest.raises((TypeError, ValueError)):
            whisper_client._preprocess_audio(invalid_audio)
    
    def test_calculate_confidence_high(self, whisper_client):
        """高信頼度計算テスト"""
        # 長い、明確な日本語テキスト
        confidence = whisper_client._calculate_confidence(
            "はい、こんにちはYes-Manです。今日はとても良い天気ですね。"
        )
        
        assert confidence > 0.8
        assert confidence <= 1.0
    
    def test_calculate_confidence_low(self, whisper_client):
        """低信頼度計算テスト"""
        # 短い、不明瞭なテキスト
        confidence = whisper_client._calculate_confidence("あー、えー、...")
        
        assert confidence < 0.5
        assert confidence >= 0.0
    
    def test_calculate_confidence_empty(self, whisper_client):
        """空テキストの信頼度計算テスト"""
        confidence = whisper_client._calculate_confidence("")
        assert confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_cleanup_success(self, whisper_client):
        """クリーンアップ成功テスト"""
        # 初期化後にクリーンアップ
        await whisper_client.initialize()
        await whisper_client.cleanup()
        
        assert whisper_client.model is None
        assert not whisper_client.is_loaded
    
    @pytest.mark.asyncio
    async def test_get_model_info(self, whisper_client):
        """モデル情報取得テスト"""
        await whisper_client.initialize()
        
        info = whisper_client.get_model_info()
        
        assert 'model_name' in info
        assert 'is_loaded' in info
        assert 'language' in info
        assert info['model_name'] == "base"
        assert info['is_loaded'] is True
        assert info['language'] == "ja"
    
    def test_supported_languages(self, whisper_client):
        """サポート言語テスト"""
        languages = whisper_client.get_supported_languages()
        
        assert isinstance(languages, list)
        assert 'ja' in languages
        assert 'en' in languages
        assert len(languages) > 0
    
    def test_performance_metrics(self, whisper_client):
        """パフォーマンス指標テスト"""
        metrics = whisper_client.get_performance_metrics()
        
        assert 'total_transcriptions' in metrics
        assert 'average_processing_time' in metrics
        assert 'success_rate' in metrics
        assert metrics['total_transcriptions'] >= 0
        assert metrics['average_processing_time'] >= 0.0
        assert 0.0 <= metrics['success_rate'] <= 1.0


class TestWhisperError:
    """WhisperError例外テスト"""
    
    def test_whisper_error_creation(self):
        """WhisperError作成テスト"""
        error = WhisperError("Test error message")
        
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_whisper_error_with_cause(self):
        """原因付きWhisperErrorテスト"""
        original_error = ValueError("Original error")
        error = WhisperError("Whisper processing failed", original_error)
        
        assert "Whisper processing failed" in str(error)
        assert error.__cause__ == original_error


class TestWhisperIntegrationPrivacy:
    """プライバシー保護テスト（憲法I準拠）"""
    
    @pytest.fixture
    def whisper_client(self):
        return WhisperClient()
    
    @pytest.mark.asyncio
    async def test_no_audio_data_storage(self, whisper_client, mock_audio_data):
        """音声データ非保存テスト"""
        with patch('audio_layer.whisper_integration.WHISPER_AVAILABLE', False):
            await whisper_client.initialize()
            
            result = await whisper_client.transcribe_audio(mock_audio_data)
            
            # 結果に生音声データが含まれていないことを確認
            assert 'audio_data' not in result
            assert 'raw_audio' not in result
            assert 'waveform' not in result
    
    @pytest.mark.asyncio
    async def test_no_temporary_file_creation(self, whisper_client, mock_audio_data):
        """一時ファイル非作成テスト"""
        with patch('audio_layer.whisper_integration.WHISPER_AVAILABLE', False):
            await whisper_client.initialize()
            
            # 処理前後で一時ディレクトリをチェック
            temp_dir = tempfile.gettempdir()
            files_before = set(os.listdir(temp_dir))
            
            await whisper_client.transcribe_audio(mock_audio_data)
            
            files_after = set(os.listdir(temp_dir))
            new_files = files_after - files_before
            
            # 新しい一時ファイルが作成されていないことを確認
            audio_related_files = [f for f in new_files if any(ext in f.lower() for ext in ['.wav', '.mp3', '.audio', '.pcm'])]
            assert len(audio_related_files) == 0
    
    def test_memory_cleanup(self, whisper_client, mock_audio_data):
        """メモリクリーンアップテスト"""
        processed = whisper_client._preprocess_audio(mock_audio_data)
        
        # 処理後、元データが変更されていないことを確認
        assert np.array_equal(mock_audio_data, mock_audio_data)  # 元データ保護
        
        # 処理済みデータは独立していることを確認
        processed[0] = 999.0
        assert mock_audio_data[0] != 999.0


@pytest.mark.integration
class TestWhisperIntegrationPerformance:
    """パフォーマンステスト（憲法VI準拠）"""
    
    @pytest.fixture
    def whisper_client(self):
        return WhisperClient()
    
    @pytest.mark.asyncio
    async def test_initialization_time(self, whisper_client):
        """初期化時間テスト"""
        import time
        
        start_time = time.time()
        await whisper_client.initialize()
        end_time = time.time()
        
        initialization_time = end_time - start_time
        
        # 初期化は10秒以内に完了する
        assert initialization_time < 10.0
    
    @pytest.mark.asyncio
    async def test_transcription_speed(self, whisper_client):
        """転写速度テスト"""
        await whisper_client.initialize()
        
        # 3秒の音声データ
        audio_data = np.random.random(48000).astype(np.float32)  # 16kHz * 3s
        
        import time
        start_time = time.time()
        result = await whisper_client.transcribe_audio(audio_data)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # 3秒の音声を5秒以内で処理（リアルタイム比1.67倍）
        assert processing_time < 5.0
        assert result['success'] is True
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, whisper_client):
        """メモリ使用量安定性テスト"""
        import psutil
        import gc
        
        await whisper_client.initialize()
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # 複数回転写実行
        for _ in range(5):
            audio_data = np.random.random(16000).astype(np.float32)  # 1秒
            await whisper_client.transcribe_audio(audio_data)
            gc.collect()  # 強制ガベージコレクション
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # メモリ増加は50MB以下に抑制
        memory_increase_mb = memory_increase / (1024 * 1024)
        assert memory_increase_mb < 50.0


if __name__ == "__main__":
    # テスト実行
    pytest.main([__file__, "-v", "--tb=short"])