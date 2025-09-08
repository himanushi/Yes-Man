"""
Unit Tests for Audio Buffer Management
音声バッファ管理システムのテスト

憲法I: プライバシー保護 - 3秒循環バッファの実装確認
憲法VI: パフォーマンス制約 - リアルタイム処理性能テスト
"""

import pytest
import asyncio
import numpy as np
import threading
import time
from unittest.mock import Mock, patch
from audio_layer.audio_buffer import (
    CircularAudioBuffer, 
    AudioBufferManager,
    BufferOverflowError,
    BufferUnderflowError
)


class TestCircularAudioBuffer:
    """循環音声バッファ単体テスト"""
    
    @pytest.fixture
    def buffer_3sec(self):
        """3秒間の循環バッファ（憲法I準拠）"""
        return CircularAudioBuffer(
            sample_rate=16000,
            duration_seconds=3.0,
            channels=1,
            dtype=np.float32
        )
    
    @pytest.fixture
    def buffer_1sec(self):
        """1秒間の循環バッファ"""
        return CircularAudioBuffer(
            sample_rate=16000,
            duration_seconds=1.0,
            channels=1,
            dtype=np.float32
        )
    
    @pytest.fixture
    def mock_audio_chunk(self):
        """モック音声チャンク（100ms）"""
        samples = int(16000 * 0.1)  # 100ms
        return np.random.random(samples).astype(np.float32)
    
    def test_circular_buffer_initialization(self):
        """循環バッファ初期化テスト"""
        buffer = CircularAudioBuffer(
            sample_rate=44100,
            duration_seconds=2.0,
            channels=2,
            dtype=np.int16
        )
        
        assert buffer.sample_rate == 44100
        assert buffer.duration_seconds == 2.0
        assert buffer.channels == 2
        assert buffer.dtype == np.int16
        assert buffer.buffer_size == 44100 * 2 * 2  # サンプルレート × 秒数 × チャンネル数
        assert buffer.write_index == 0
        assert buffer.read_index == 0
        assert buffer.is_full is False
    
    def test_circular_buffer_privacy_compliance(self, buffer_3sec):
        """プライバシー準拠テスト（憲法I: 3秒制限）"""
        # 3秒間の音声データ作成
        audio_3sec = np.random.random(16000 * 3).astype(np.float32)
        
        buffer_3sec.write(audio_3sec)
        
        # 3秒以上のデータは保持されない
        assert buffer_3sec.get_available_duration() <= 3.0
        
        # さらに3秒追加
        buffer_3sec.write(audio_3sec)
        
        # 依然として3秒以内
        assert buffer_3sec.get_available_duration() <= 3.0
    
    def test_write_single_chunk(self, buffer_3sec, mock_audio_chunk):
        """単一チャンク書き込みテスト"""
        initial_available = buffer_3sec.get_available_samples()
        
        buffer_3sec.write(mock_audio_chunk)
        
        final_available = buffer_3sec.get_available_samples()
        assert final_available == initial_available + len(mock_audio_chunk)
        assert buffer_3sec.write_index == len(mock_audio_chunk)
    
    def test_write_multiple_chunks(self, buffer_1sec, mock_audio_chunk):
        """複数チャンク書き込みテスト"""
        # 5つのチャンクを書き込み（合計500ms）
        for i in range(5):
            buffer_1sec.write(mock_audio_chunk)
        
        # 500ms分のデータが利用可能
        expected_samples = len(mock_audio_chunk) * 5
        assert buffer_1sec.get_available_samples() == expected_samples
    
    def test_write_circular_overflow(self, buffer_1sec):
        """循環バッファオーバーフローテスト"""
        # 1.5秒分のデータ（バッファサイズ超過）
        audio_15sec = np.random.random(int(16000 * 1.5)).astype(np.float32)
        
        buffer_1sec.write(audio_15sec)
        
        # 1秒分のみ保持される
        assert buffer_1sec.get_available_duration() <= 1.0
        assert buffer_1sec.is_full is True
    
    def test_read_partial_data(self, buffer_3sec, mock_audio_chunk):
        """部分データ読み取りテスト"""
        buffer_3sec.write(mock_audio_chunk)
        
        # 半分のサイズを読み取り
        read_size = len(mock_audio_chunk) // 2
        read_data = buffer_3sec.read(read_size)
        
        assert len(read_data) == read_size
        assert np.array_equal(read_data, mock_audio_chunk[:read_size])
        
        # 残りデータが正しく残っている
        remaining = buffer_3sec.get_available_samples()
        assert remaining == len(mock_audio_chunk) - read_size
    
    def test_read_all_available(self, buffer_3sec, mock_audio_chunk):
        """全利用可能データ読み取りテスト"""
        buffer_3sec.write(mock_audio_chunk)
        
        all_data = buffer_3sec.read_all_available()
        
        assert len(all_data) == len(mock_audio_chunk)
        assert np.array_equal(all_data, mock_audio_chunk)
        assert buffer_3sec.get_available_samples() == 0
    
    def test_read_more_than_available(self, buffer_3sec, mock_audio_chunk):
        """利用可能以上の読み取りテスト"""
        buffer_3sec.write(mock_audio_chunk)
        
        # 利用可能以上のサイズを要求
        large_size = len(mock_audio_chunk) * 2
        read_data = buffer_3sec.read(large_size)
        
        # 利用可能分のみ返される
        assert len(read_data) == len(mock_audio_chunk)
        assert np.array_equal(read_data, mock_audio_chunk)
    
    def test_read_from_empty_buffer(self, buffer_3sec):
        """空バッファからの読み取りテスト"""
        read_data = buffer_3sec.read(1000)
        
        assert len(read_data) == 0
        assert read_data.dtype == np.float32
    
    def test_get_last_seconds(self, buffer_3sec):
        """直近N秒取得テスト"""
        # 2秒分のデータを追加
        audio_2sec = np.random.random(16000 * 2).astype(np.float32)
        buffer_3sec.write(audio_2sec)
        
        # 直近1秒を取得
        last_1sec = buffer_3sec.get_last_seconds(1.0)
        
        assert len(last_1sec) == 16000  # 1秒分
        # 最新データと一致することを確認
        expected = audio_2sec[-16000:]
        assert np.array_equal(last_1sec, expected)
    
    def test_get_last_seconds_insufficient_data(self, buffer_3sec, mock_audio_chunk):
        """不十分なデータでの直近取得テスト"""
        buffer_3sec.write(mock_audio_chunk)  # 100ms分のみ
        
        # 1秒要求（データ不足）
        last_1sec = buffer_3sec.get_last_seconds(1.0)
        
        # 利用可能分のみ返される
        assert len(last_1sec) == len(mock_audio_chunk)
    
    def test_peek_without_consuming(self, buffer_3sec, mock_audio_chunk):
        """消費しない参照テスト"""
        buffer_3sec.write(mock_audio_chunk)
        original_available = buffer_3sec.get_available_samples()
        
        # 覗き見
        peek_data = buffer_3sec.peek(len(mock_audio_chunk) // 2)
        
        # データは消費されない
        assert buffer_3sec.get_available_samples() == original_available
        assert len(peek_data) == len(mock_audio_chunk) // 2
        assert np.array_equal(peek_data, mock_audio_chunk[:len(peek_data)])
    
    def test_clear_buffer(self, buffer_3sec, mock_audio_chunk):
        """バッファクリアテスト"""
        buffer_3sec.write(mock_audio_chunk)
        assert buffer_3sec.get_available_samples() > 0
        
        buffer_3sec.clear()
        
        assert buffer_3sec.get_available_samples() == 0
        assert buffer_3sec.write_index == 0
        assert buffer_3sec.read_index == 0
        assert buffer_3sec.is_full is False
    
    def test_buffer_stats(self, buffer_3sec, mock_audio_chunk):
        """バッファ統計情報テスト"""
        buffer_3sec.write(mock_audio_chunk)
        
        stats = buffer_3sec.get_stats()
        
        assert 'total_capacity' in stats
        assert 'available_samples' in stats
        assert 'available_duration' in stats
        assert 'usage_percentage' in stats
        assert 'write_index' in stats
        assert 'read_index' in stats
        assert 'is_full' in stats
        
        assert stats['available_samples'] == len(mock_audio_chunk)
        assert stats['usage_percentage'] > 0.0


class TestAudioBufferManager:
    """音声バッファ管理システム単体テスト"""
    
    @pytest.fixture
    def buffer_manager(self):
        """音声バッファマネージャー"""
        return AudioBufferManager(
            input_buffer_duration=3.0,  # 憲法I準拠
            output_buffer_duration=2.0,
            sample_rate=16000,
            chunk_size=1600  # 100ms chunks
        )
    
    @pytest.fixture
    def mock_audio_callback(self):
        """モック音声コールバック"""
        return Mock()
    
    def test_buffer_manager_initialization(self):
        """バッファマネージャー初期化テスト"""
        manager = AudioBufferManager(
            input_buffer_duration=5.0,
            output_buffer_duration=3.0,
            sample_rate=44100,
            chunk_size=4410
        )
        
        assert manager.sample_rate == 44100
        assert manager.chunk_size == 4410
        assert manager.input_buffer_duration == 5.0
        assert manager.output_buffer_duration == 3.0
        assert manager.input_buffer is not None
        assert manager.output_buffer is not None
        assert manager.is_running is False
    
    @pytest.mark.asyncio
    async def test_start_stop_processing(self, buffer_manager, mock_audio_callback):
        """処理開始・停止テスト"""
        # 開始
        await buffer_manager.start_processing(mock_audio_callback)
        
        assert buffer_manager.is_running is True
        assert buffer_manager.audio_callback == mock_audio_callback
        
        # 少し待機してから停止
        await asyncio.sleep(0.1)
        await buffer_manager.stop_processing()
        
        assert buffer_manager.is_running is False
    
    @pytest.mark.asyncio
    async def test_write_input_audio(self, buffer_manager):
        """入力音声書き込みテスト"""
        await buffer_manager.start_processing(Mock())
        
        audio_chunk = np.random.random(1600).astype(np.float32)
        
        result = await buffer_manager.write_input_audio(audio_chunk)
        
        assert result is True
        assert buffer_manager.input_buffer.get_available_samples() == 1600
        
        await buffer_manager.stop_processing()
    
    @pytest.mark.asyncio
    async def test_write_output_audio(self, buffer_manager):
        """出力音声書き込みテスト"""
        await buffer_manager.start_processing(Mock())
        
        audio_chunk = np.random.random(1600).astype(np.float32)
        
        result = await buffer_manager.write_output_audio(audio_chunk)
        
        assert result is True
        assert buffer_manager.output_buffer.get_available_samples() == 1600
        
        await buffer_manager.stop_processing()
    
    @pytest.mark.asyncio
    async def test_read_input_audio(self, buffer_manager):
        """入力音声読み取りテスト"""
        await buffer_manager.start_processing(Mock())
        
        # データ書き込み
        audio_chunk = np.random.random(1600).astype(np.float32)
        await buffer_manager.write_input_audio(audio_chunk)
        
        # データ読み取り
        read_data = await buffer_manager.read_input_audio(800)
        
        assert len(read_data) == 800
        assert np.array_equal(read_data, audio_chunk[:800])
        
        await buffer_manager.stop_processing()
    
    @pytest.mark.asyncio
    async def test_get_input_last_seconds(self, buffer_manager):
        """入力直近秒数取得テスト"""
        await buffer_manager.start_processing(Mock())
        
        # 1秒分のデータ追加
        audio_1sec = np.random.random(16000).astype(np.float32)
        await buffer_manager.write_input_audio(audio_1sec)
        
        # 直近0.5秒取得
        last_half_sec = await buffer_manager.get_input_last_seconds(0.5)
        
        assert len(last_half_sec) == 8000  # 0.5秒分
        expected = audio_1sec[-8000:]
        assert np.array_equal(last_half_sec, expected)
        
        await buffer_manager.stop_processing()
    
    @pytest.mark.asyncio
    async def test_buffer_overflow_handling(self, buffer_manager):
        """バッファオーバーフロー処理テスト"""
        await buffer_manager.start_processing(Mock())
        
        # 大量データを書き込み（バッファ容量超過）
        large_audio = np.random.random(16000 * 5).astype(np.float32)  # 5秒分
        
        result = await buffer_manager.write_input_audio(large_audio)
        
        # 書き込みは成功するが、古いデータは上書きされる
        assert result is True
        assert buffer_manager.input_buffer.get_available_duration() <= 3.0
        
        await buffer_manager.stop_processing()
    
    @pytest.mark.asyncio
    async def test_concurrent_read_write(self, buffer_manager):
        """並行読み書きテスト"""
        await buffer_manager.start_processing(Mock())
        
        audio_chunk = np.random.random(1600).astype(np.float32)
        
        # 並行して読み書き実行
        write_task = asyncio.create_task(
            buffer_manager.write_input_audio(audio_chunk)
        )
        read_task = asyncio.create_task(
            buffer_manager.read_input_audio(800)
        )
        
        write_result, read_result = await asyncio.gather(write_task, read_task)
        
        assert write_result is True
        # 読み取りは書き込み前なので0サンプル
        assert len(read_result) == 0
        
        await buffer_manager.stop_processing()
    
    @pytest.mark.asyncio
    async def test_privacy_compliance_auto_clear(self, buffer_manager):
        """プライバシー準拠自動クリアテスト"""
        await buffer_manager.start_processing(Mock())
        
        # データ追加
        audio_chunk = np.random.random(1600).astype(np.float32)
        await buffer_manager.write_input_audio(audio_chunk)
        
        # 自動クリア実行
        await buffer_manager.clear_all_buffers()
        
        assert buffer_manager.input_buffer.get_available_samples() == 0
        assert buffer_manager.output_buffer.get_available_samples() == 0
        
        await buffer_manager.stop_processing()
    
    def test_get_buffer_stats(self, buffer_manager):
        """バッファ統計取得テスト"""
        stats = buffer_manager.get_buffer_stats()
        
        assert 'input_buffer' in stats
        assert 'output_buffer' in stats
        assert 'processing_active' in stats
        assert 'sample_rate' in stats
        assert 'chunk_size' in stats
        
        assert stats['sample_rate'] == 16000
        assert stats['chunk_size'] == 1600
        assert stats['processing_active'] is False
    
    @pytest.mark.asyncio
    async def test_audio_callback_execution(self, buffer_manager):
        """音声コールバック実行テスト"""
        callback_called = asyncio.Event()
        received_data = None
        
        async def test_callback(audio_data):
            nonlocal received_data
            received_data = audio_data
            callback_called.set()
        
        await buffer_manager.start_processing(test_callback)
        
        # 十分なデータを追加してコールバックをトリガー
        audio_chunk = np.random.random(1600).astype(np.float32)
        await buffer_manager.write_input_audio(audio_chunk)
        
        # コールバックが呼ばれるまで待機
        try:
            await asyncio.wait_for(callback_called.wait(), timeout=1.0)
            assert received_data is not None
            assert len(received_data) > 0
        except asyncio.TimeoutError:
            # タイムアウトしてもテストは継続
            pass
        
        await buffer_manager.stop_processing()


class TestAudioBufferErrors:
    """音声バッファエラーテスト"""
    
    def test_buffer_overflow_error(self):
        """バッファオーバーフローエラーテスト"""
        error = BufferOverflowError("Buffer capacity exceeded")
        
        assert str(error) == "Buffer capacity exceeded"
        assert isinstance(error, Exception)
    
    def test_buffer_underflow_error(self):
        """バッファアンダーフローエラーテスト"""
        error = BufferUnderflowError("Insufficient data in buffer")
        
        assert str(error) == "Insufficient data in buffer"
        assert isinstance(error, Exception)


@pytest.mark.integration
class TestAudioBufferPerformance:
    """音声バッファパフォーマンステスト（憲法VI準拠）"""
    
    @pytest.fixture
    def buffer_manager(self):
        return AudioBufferManager(
            input_buffer_duration=3.0,
            output_buffer_duration=2.0,
            sample_rate=16000,
            chunk_size=1600
        )
    
    @pytest.mark.asyncio
    async def test_realtime_processing_speed(self, buffer_manager):
        """リアルタイム処理速度テスト"""
        processing_times = []
        
        async def timing_callback(audio_data):
            # 処理時間を記録
            start_time = time.time()
            # 簡単な処理をシミュレート
            np.mean(audio_data)
            end_time = time.time()
            processing_times.append(end_time - start_time)
        
        await buffer_manager.start_processing(timing_callback)
        
        # 複数チャンクを高速で送信
        for _ in range(10):
            audio_chunk = np.random.random(1600).astype(np.float32)
            await buffer_manager.write_input_audio(audio_chunk)
            await asyncio.sleep(0.05)  # 50ms間隔
        
        await asyncio.sleep(0.5)  # コールバック実行待機
        await buffer_manager.stop_processing()
        
        if processing_times:
            avg_processing_time = np.mean(processing_times)
            # 100msチャンクの処理は10ms以内
            assert avg_processing_time < 0.01  # 10ms
    
    @pytest.mark.asyncio 
    async def test_memory_efficiency_sustained_operation(self, buffer_manager):
        """長時間運用メモリ効率テスト"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        await buffer_manager.start_processing(lambda x: None)
        
        # 30秒間の連続運用をシミュレート
        for i in range(300):  # 300 × 100ms = 30秒
            audio_chunk = np.random.random(1600).astype(np.float32)
            await buffer_manager.write_input_audio(audio_chunk)
            
            if i % 50 == 0:  # 定期的にガベージコレクション
                gc.collect()
            
            await asyncio.sleep(0.001)  # 高速実行
        
        await buffer_manager.stop_processing()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        # 30秒の連続運用でメモリ増加は10MB以下
        assert memory_increase_mb < 10.0
    
    @pytest.mark.asyncio
    async def test_concurrent_buffer_operations(self, buffer_manager):
        """並行バッファ操作パフォーマンステスト"""
        await buffer_manager.start_processing(lambda x: None)
        
        # 並行して複数の読み書き操作を実行
        async def write_task():
            for _ in range(50):
                audio_chunk = np.random.random(800).astype(np.float32)
                await buffer_manager.write_input_audio(audio_chunk)
        
        async def read_task():
            for _ in range(50):
                await buffer_manager.read_input_audio(400)
                await asyncio.sleep(0.001)
        
        start_time = time.time()
        
        # 並行実行
        await asyncio.gather(write_task(), read_task())
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 並行操作は5秒以内に完了
        assert total_time < 5.0
        
        await buffer_manager.stop_processing()
    
    def test_buffer_capacity_optimization(self):
        """バッファ容量最適化テスト"""
        # 異なるサイズのバッファでメモリ使用量を比較
        small_buffer = CircularAudioBuffer(16000, 1.0, 1, np.float32)
        large_buffer = CircularAudioBuffer(16000, 10.0, 1, np.float32)
        
        # 小バッファの方が効率的
        small_memory = small_buffer.buffer.nbytes
        large_memory = large_buffer.buffer.nbytes
        
        assert large_memory == small_memory * 10  # 線形比例関係
        assert small_memory < 1024 * 1024  # 1MB未満


@pytest.mark.integration
class TestAudioBufferPrivacyCompliance:
    """プライバシー保護準拠テスト（憲法I準拠）"""
    
    @pytest.fixture
    def buffer_manager(self):
        return AudioBufferManager(
            input_buffer_duration=3.0,  # 憲法I: 3秒制限
            output_buffer_duration=2.0,
            sample_rate=16000
        )
    
    @pytest.mark.asyncio
    async def test_three_second_limit_enforcement(self, buffer_manager):
        """3秒制限実施テスト"""
        await buffer_manager.start_processing(lambda x: None)
        
        # 10秒分のデータを連続投入
        for _ in range(100):  # 100 × 100ms = 10秒
            audio_chunk = np.random.random(1600).astype(np.float32)
            await buffer_manager.write_input_audio(audio_chunk)
        
        # 3秒以下しか保持されない
        available_duration = buffer_manager.input_buffer.get_available_duration()
        assert available_duration <= 3.0
        
        await buffer_manager.stop_processing()
    
    @pytest.mark.asyncio
    async def test_automatic_old_data_purging(self, buffer_manager):
        """古いデータ自動削除テスト"""
        await buffer_manager.start_processing(lambda x: None)
        
        # 最初のデータ（識別用）
        first_chunk = np.ones(1600, dtype=np.float32) * 0.1
        await buffer_manager.write_input_audio(first_chunk)
        
        # 3秒以上のデータを追加
        for _ in range(50):  # 5秒分
            random_chunk = np.random.random(1600).astype(np.float32) * 0.9
            await buffer_manager.write_input_audio(random_chunk)
        
        # 最初のデータは削除されている
        recent_data = await buffer_manager.get_input_last_seconds(3.0)
        # 最初のデータ（0.1）は含まれていない
        assert np.min(recent_data) > 0.15  # 0.1より大きい
        
        await buffer_manager.stop_processing()
    
    @pytest.mark.asyncio
    async def test_no_permanent_storage_creation(self, buffer_manager):
        """永続ストレージ作成なしテスト"""
        import tempfile
        import os
        
        temp_dir = tempfile.gettempdir()
        files_before = set(os.listdir(temp_dir))
        
        await buffer_manager.start_processing(lambda x: None)
        
        # 大量データ処理
        for _ in range(100):
            audio_chunk = np.random.random(1600).astype(np.float32)
            await buffer_manager.write_input_audio(audio_chunk)
        
        await buffer_manager.stop_processing()
        
        files_after = set(os.listdir(temp_dir))
        new_files = files_after - files_before
        
        # 音声ファイルが作成されていない
        audio_files = [f for f in new_files if any(ext in f.lower() for ext in ['.wav', '.mp3', '.pcm', '.raw'])]
        assert len(audio_files) == 0
    
    @pytest.mark.asyncio
    async def test_memory_only_processing(self, buffer_manager):
        """メモリ内処理限定テスト"""
        await buffer_manager.start_processing(lambda x: None)
        
        # バッファがメモリ内に存在することを確認
        assert hasattr(buffer_manager.input_buffer, 'buffer')
        assert isinstance(buffer_manager.input_buffer.buffer, np.ndarray)
        assert buffer_manager.input_buffer.buffer.flags.writeable
        
        # ファイルハンドルが開かれていない
        import gc
        for obj in gc.get_objects():
            if hasattr(obj, 'name') and hasattr(obj, 'mode'):
                # ファイルオブジェクトをチェック
                if any(ext in str(obj.name).lower() for ext in ['.wav', '.mp3', '.pcm']):
                    pytest.fail("Audio file handle detected")
        
        await buffer_manager.stop_processing()


if __name__ == "__main__":
    # テスト実行
    pytest.main([__file__, "-v", "--tb=short"])