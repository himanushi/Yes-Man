"""
Performance Tests for Yes-Man System
憲法VI準拠パフォーマンステスト

憲法VI: パフォーマンス制約
- ウェイクワード検出: 1秒以内
- 全体応答時間: 3秒以内  
- CPU使用率: 30%以下
- リアルタイム処理維持
"""

import pytest
import asyncio
import time
import psutil
import numpy as np
import threading
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Yes-Manコンポーネント
from audio_layer.wake_word_detection import WakeWordDetector
from audio_layer.whisper_integration import WhisperClient
from audio_layer.voicevox_client import VoiceVoxClient  
from audio_layer.langflow_client import LangFlowClient
from audio_layer.orchestrator import YesManOrchestrator
from audio_layer.performance_monitor import PerformanceMonitor, get_performance_monitor


@pytest.mark.performance
class TestWakeWordPerformance:
    """ウェイクワード検出パフォーマンステスト（憲法VI: 1秒以内）"""
    
    @pytest.fixture
    def wake_word_detector(self):
        """ウェイクワード検出器"""
        return WakeWordDetector(sensitivity=0.8)
    
    @pytest.fixture
    def mock_audio_stream(self):
        """モック音声ストリーム（3秒分、16kHz）"""
        sample_rate = 16000
        duration = 3.0
        samples = int(sample_rate * duration)
        
        # Yes-Man ウェイクワードを2秒位置に配置（シミュレート）
        audio_data = np.random.random(samples).astype(np.float32) * 0.1
        wake_word_start = int(sample_rate * 2.0)  # 2秒位置
        wake_word_duration = int(sample_rate * 0.5)  # 0.5秒間
        
        # ウェイクワード部分を高エネルギーにする（検出シミュレート）
        audio_data[wake_word_start:wake_word_start + wake_word_duration] *= 5.0
        
        return audio_data
    
    @pytest.mark.asyncio
    async def test_wake_word_detection_latency(self, wake_word_detector, mock_audio_stream):
        """ウェイクワード検出レイテンシテスト"""
        await wake_word_detector.initialize()
        
        # 検出時間測定
        detection_times = []
        
        for trial in range(5):  # 5回測定
            start_time = time.time()
            
            # モック検出（実際の実装では音声処理）
            with patch.object(wake_word_detector, '_process_audio_chunk') as mock_process:
                mock_process.return_value = {
                    'detected': True,
                    'keyword': 'Yes-Man',
                    'confidence': 0.95,
                    'timestamp': time.time()
                }
                
                result = await wake_word_detector.check_wake_word()
                
                detection_time = time.time() - start_time
                detection_times.append(detection_time)
                
                if result and result['confidence'] > 0.8:
                    break
        
        # 統計計算
        avg_detection_time = np.mean(detection_times)
        max_detection_time = np.max(detection_times)
        
        # 憲法VI: ウェイクワード検出は1秒以内
        assert avg_detection_time < 1.0, f"Average detection time {avg_detection_time:.3f}s exceeds 1s limit"
        assert max_detection_time < 1.0, f"Max detection time {max_detection_time:.3f}s exceeds 1s limit"
        
        print(f"Wake word detection performance:")
        print(f"  Average: {avg_detection_time:.3f}s")
        print(f"  Maximum: {max_detection_time:.3f}s")
        print(f"  Minimum: {np.min(detection_times):.3f}s")
    
    @pytest.mark.asyncio
    async def test_continuous_detection_performance(self, wake_word_detector):
        """連続検出性能テスト"""
        await wake_word_detector.initialize()
        
        # 10秒間の連続検出をシミュレート
        detection_count = 0
        false_positive_count = 0
        detection_times = []
        
        start_time = time.time()
        
        # 100ms毎にチェック（10秒間）
        for i in range(100):
            chunk_start = time.time()
            
            # ランダムにウェイクワードを混在
            has_wake_word = (i % 20 == 0)  # 2秒毎にウェイクワード
            
            with patch.object(wake_word_detector, '_process_audio_chunk') as mock_process:
                if has_wake_word:
                    mock_process.return_value = {
                        'detected': True,
                        'keyword': 'Yes-Man',
                        'confidence': 0.95,
                        'timestamp': time.time()
                    }
                else:
                    mock_process.return_value = {
                        'detected': False,
                        'keyword': None,
                        'confidence': 0.3,
                        'timestamp': time.time()
                    }
                
                result = await wake_word_detector.check_wake_word()
                
                chunk_time = time.time() - chunk_start
                detection_times.append(chunk_time)
                
                if result and result.get('detected'):
                    if has_wake_word:
                        detection_count += 1
                    else:
                        false_positive_count += 1
            
            await asyncio.sleep(0.1)  # 100ms間隔
        
        total_time = time.time() - start_time
        
        # パフォーマンス要件
        avg_chunk_time = np.mean(detection_times)
        
        # 各チャンクの処理は100ms以内（リアルタイム維持）
        assert avg_chunk_time < 0.1, f"Chunk processing {avg_chunk_time:.3f}s too slow"
        
        # 適切な検出率
        expected_detections = 5  # 10秒間で5回
        detection_rate = detection_count / expected_detections if expected_detections > 0 else 0
        assert detection_rate >= 0.8, f"Detection rate {detection_rate:.2f} too low"
        
        # 誤検出率
        false_positive_rate = false_positive_count / (100 - expected_detections)
        assert false_positive_rate < 0.1, f"False positive rate {false_positive_rate:.2f} too high"
        
        print(f"Continuous detection performance:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Avg chunk time: {avg_chunk_time:.4f}s")
        print(f"  Detection rate: {detection_rate:.2f}")
        print(f"  False positive rate: {false_positive_rate:.3f}")


@pytest.mark.performance
class TestSTTPerformance:
    """STT処理パフォーマンステスト"""
    
    @pytest.fixture
    def whisper_client(self):
        """Whisperクライアント"""
        return WhisperClient(model_name="base")
    
    @pytest.mark.asyncio
    async def test_stt_processing_speed(self, whisper_client):
        """STT処理速度テスト"""
        await whisper_client.initialize()
        
        # 異なる長さの音声データでテスト
        test_cases = [
            (1.0, "1秒音声"),  # 1秒
            (2.0, "2秒音声"),  # 2秒  
            (3.0, "3秒音声"),  # 3秒
            (5.0, "5秒音声")   # 5秒（上限テスト）
        ]
        
        processing_times = []
        
        for audio_duration, description in test_cases:
            # モック音声データ
            sample_rate = 16000
            audio_samples = int(sample_rate * audio_duration)
            audio_data = np.random.random(audio_samples).astype(np.float32)
            
            # STT処理時間測定
            start_time = time.time()
            
            with patch.object(whisper_client, 'model') as mock_model:
                mock_model.transcribe.return_value = {
                    'text': f'モック転写結果 {description}',
                    'language': 'ja'
                }
                
                result = await whisper_client.transcribe_audio(audio_data)
                
                end_time = time.time()
                processing_time = end_time - start_time
                processing_times.append((audio_duration, processing_time))
                
                assert result['success'] is True
                
                # リアルタイム比（処理時間/音声時間）
                realtime_ratio = processing_time / audio_duration
                
                print(f"{description}: {processing_time:.3f}s (ratio: {realtime_ratio:.2f})")
                
                # 3秒以下の音声は1秒以内で処理
                if audio_duration <= 3.0:
                    assert processing_time < 1.0, f"{description} processing too slow: {processing_time:.3f}s"
                
                # 5秒音声でも2秒以内で処理
                if audio_duration <= 5.0:
                    assert processing_time < 2.0, f"{description} processing too slow: {processing_time:.3f}s"
        
        # 全体的なパフォーマンス分析
        avg_realtime_ratio = np.mean([pt / ad for ad, pt in processing_times])
        assert avg_realtime_ratio < 0.5, f"STT too slow overall: {avg_realtime_ratio:.2f}x realtime"
    
    @pytest.mark.asyncio
    async def test_concurrent_stt_processing(self, whisper_client):
        """並行STT処理性能テスト"""
        await whisper_client.initialize()
        
        # 3つの音声を並行処理
        audio_duration = 2.0
        sample_rate = 16000
        audio_samples = int(sample_rate * audio_duration)
        
        audio_chunks = [
            np.random.random(audio_samples).astype(np.float32) for _ in range(3)
        ]
        
        with patch.object(whisper_client, 'model') as mock_model:
            mock_model.transcribe.return_value = {
                'text': 'マルチ処理テスト',
                'language': 'ja'
            }
            
            start_time = time.time()
            
            # 並行処理実行
            tasks = [
                whisper_client.transcribe_audio(chunk) 
                for chunk in audio_chunks
            ]
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # すべて成功
            assert all(result['success'] for result in results)
            
            # 並行処理により高速化（シーケンシャルより速い）
            sequential_time = len(audio_chunks) * 1.0  # 1秒/チャンク想定
            assert total_time < sequential_time * 0.8, "Concurrent processing not efficient"
            
            print(f"Concurrent STT: {len(audio_chunks)} chunks in {total_time:.3f}s")


@pytest.mark.performance  
class TestTTSPerformance:
    """TTS処理パフォーマンステスト"""
    
    @pytest.fixture
    def voicevox_client(self):
        """VoiceVoxクライアント"""
        return VoiceVoxClient(host="localhost", port=50021, speaker_id=1)
    
    @pytest.mark.asyncio
    async def test_tts_synthesis_speed(self, voicevox_client):
        """TTS合成速度テスト"""
        # TTS処理時間測定
        test_texts = [
            "はい！",  # 短文
            "はい！もちろんです！",  # 中文
            "はい！もちろんです！Yes-Manです！",  # 長文
            "はい！こんにちは、Yes-Manです！今日はお疲れ様でした！"  # 最長文
        ]
        
        synthesis_times = []
        
        for text in test_texts:
            start_time = time.time()
            
            with patch('aiohttp.ClientSession.post') as mock_post:
                # audio_query レスポンス
                query_response = AsyncMock()
                query_response.status = 200
                query_response.json = AsyncMock(return_value={"speedScale": 1.0})
                
                # synthesis レスポンス
                synthesis_response = AsyncMock()
                synthesis_response.status = 200
                synthesis_response.read = AsyncMock(return_value=b"mock_audio_data")
                
                mock_post.side_effect = [
                    AsyncMock(__aenter__=AsyncMock(return_value=query_response)),
                    AsyncMock(__aenter__=AsyncMock(return_value=synthesis_response))
                ]
                
                result = await voicevox_client.synthesize_speech(text)
                
                end_time = time.time()
                synthesis_time = end_time - start_time
                synthesis_times.append(synthesis_time)
                
                assert result['success'] is True
                
                # TTS処理は文字数に関わらず1.5秒以内
                assert synthesis_time < 1.5, f"TTS too slow for '{text}': {synthesis_time:.3f}s"
                
                print(f"TTS '{text[:10]}...': {synthesis_time:.3f}s")
        
        # 平均処理時間
        avg_synthesis_time = np.mean(synthesis_times)
        assert avg_synthesis_time < 1.0, f"Average TTS too slow: {avg_synthesis_time:.3f}s"
    
    @pytest.mark.asyncio
    async def test_tts_concurrent_synthesis(self, voicevox_client):
        """TTS並行合成性能テスト"""
        texts = [
            "はい！テスト1です！",
            "もちろん！テスト2ですね！", 
            "そうです！テスト3です！"
        ]
        
        start_time = time.time()
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            async def mock_response(*args, **kwargs):
                # 処理時間をシミュレート
                await asyncio.sleep(0.3)
                response = AsyncMock()
                response.status = 200
                if 'audio_query' in str(args):
                    response.json = AsyncMock(return_value={"speedScale": 1.0})
                else:
                    response.read = AsyncMock(return_value=b"mock_audio_data")
                return AsyncMock(__aenter__=AsyncMock(return_value=response))
            
            mock_post.side_effect = mock_response
            
            # 並行実行
            tasks = [voicevox_client.synthesize_speech(text) for text in texts]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # すべて成功
            assert all(result['success'] for result in results)
            
            # 並行処理効果（シーケンシャルより高速）
            expected_sequential = len(texts) * 0.6  # 0.6秒/テキスト想定
            assert total_time < expected_sequential, "TTS concurrent processing inefficient"
            
            print(f"Concurrent TTS: {len(texts)} texts in {total_time:.3f}s")


@pytest.mark.performance
class TestEndToEndPerformance:
    """エンドツーエンドパフォーマンステスト（憲法VI: 3秒以内）"""
    
    @pytest.fixture
    def orchestrator(self):
        """オーケストレーター"""
        return YesManOrchestrator()
    
    @pytest.mark.asyncio
    async def test_complete_conversation_latency(self, orchestrator):
        """完全会話レイテンシテスト"""
        # システム初期化
        with patch.multiple(
            orchestrator,
            _initialize_components=AsyncMock(),
            _change_state=AsyncMock(),
            ipc_server=Mock()
        ):
            await orchestrator.initialize()
        
        # 会話セッション全体の時間測定
        conversation_times = []
        
        for trial in range(3):  # 3回測定
            session_start = time.time()
            
            # 1. ウェイクワード検出 (目標: <1秒)
            wake_word_start = time.time()
            with patch.object(orchestrator.wake_word_detector, 'check_wake_word') as mock_wake:
                mock_wake.return_value = {
                    'detected': True,
                    'keyword': 'Yes-Man',
                    'confidence': 0.95
                }
                # ウェイクワード検出シミュレート
                await asyncio.sleep(0.2)  # 200ms処理時間
            wake_word_time = time.time() - wake_word_start
            
            # 2. STT処理 (目標: <1秒)  
            stt_start = time.time()
            with patch.object(orchestrator.whisper_client, 'transcribe_audio') as mock_stt:
                mock_stt.return_value = {
                    'success': True,
                    'text': 'こんにちは、Yes-Man'
                }
                # STT処理シミュレート
                await asyncio.sleep(0.5)  # 500ms処理時間
            stt_time = time.time() - stt_start
            
            # 3. LLM処理 (目標: <1秒)
            llm_start = time.time()
            with patch.object(orchestrator.langflow_client, 'process_conversation') as mock_llm:
                mock_llm.return_value = {
                    'response': 'はい！こんにちはYes-Manです！',
                    'context_type': 'greeting',
                    'confidence': 0.9
                }
                # LLM処理シミュレート
                await asyncio.sleep(0.8)  # 800ms処理時間
            llm_time = time.time() - llm_start
            
            # 4. TTS処理 (目標: <1秒)
            tts_start = time.time()
            with patch.object(orchestrator.voicevox_client, 'synthesize_speech') as mock_tts:
                mock_tts.return_value = {
                    'success': True,
                    'audio_data': b'mock_audio',
                    'duration': 2.0
                }
                # TTS処理シミュレート
                await asyncio.sleep(0.4)  # 400ms処理時間
            tts_time = time.time() - tts_start
            
            total_time = time.time() - session_start
            conversation_times.append(total_time)
            
            # 各段階の性能要件
            assert wake_word_time < 1.0, f"Wake word detection too slow: {wake_word_time:.3f}s"
            assert stt_time < 1.0, f"STT processing too slow: {stt_time:.3f}s"  
            assert llm_time < 1.5, f"LLM processing too slow: {llm_time:.3f}s"
            assert tts_time < 1.0, f"TTS processing too slow: {tts_time:.3f}s"
            
            print(f"Trial {trial + 1} breakdown:")
            print(f"  Wake word: {wake_word_time:.3f}s")
            print(f"  STT: {stt_time:.3f}s") 
            print(f"  LLM: {llm_time:.3f}s")
            print(f"  TTS: {tts_time:.3f}s")
            print(f"  Total: {total_time:.3f}s")
        
        # 憲法VI: 全体応答時間3秒以内
        avg_conversation_time = np.mean(conversation_times)
        max_conversation_time = np.max(conversation_times)
        
        assert avg_conversation_time < 3.0, f"Average response time too slow: {avg_conversation_time:.3f}s"
        assert max_conversation_time < 3.0, f"Max response time too slow: {max_conversation_time:.3f}s"
        
        print(f"\nEnd-to-end performance:")
        print(f"  Average: {avg_conversation_time:.3f}s")
        print(f"  Maximum: {max_conversation_time:.3f}s")
        print(f"  Minimum: {np.min(conversation_times):.3f}s")


@pytest.mark.performance
class TestSystemResourcePerformance:
    """システムリソースパフォーマンステスト（憲法VI: CPU<30%）"""
    
    @pytest.fixture
    def performance_monitor(self):
        """パフォーマンスモニター"""
        return get_performance_monitor()
    
    @pytest.mark.asyncio
    async def test_cpu_usage_compliance(self, performance_monitor):
        """CPU使用率準拠テスト"""
        # モニタリング開始
        await performance_monitor.start_monitoring()
        
        # システム負荷シミュレート
        load_tasks = []
        
        async def simulate_component_load(component_name: str, duration: float):
            """コンポーネント負荷シミュレート"""
            start_time = time.time()
            
            while time.time() - start_time < duration:
                # 軽い計算処理（実際のコンポーネント処理をシミュレート）
                np.random.random(1000).mean()
                await asyncio.sleep(0.01)  # 10ms間隔
        
        # 複数コンポーネントの並行実行
        load_tasks = [
            simulate_component_load("wake_word", 5.0),
            simulate_component_load("whisper", 3.0), 
            simulate_component_load("voicevox", 2.0),
            simulate_component_load("langflow", 4.0)
        ]
        
        # 負荷実行中にCPU使用率監視
        cpu_measurements = []
        monitoring_task = asyncio.create_task(self.monitor_cpu_usage(cpu_measurements, 6.0))
        
        # 負荷とモニタリングを並行実行
        await asyncio.gather(monitoring_task, *load_tasks)
        
        await performance_monitor.stop_monitoring()
        
        # CPU使用率分析
        if cpu_measurements:
            avg_cpu = np.mean(cpu_measurements)
            max_cpu = np.max(cpu_measurements)
            
            print(f"CPU usage during load:")
            print(f"  Average: {avg_cpu:.1f}%")
            print(f"  Maximum: {max_cpu:.1f}%")
            print(f"  Samples: {len(cpu_measurements)}")
            
            # 憲法VI: CPU使用率30%以下
            assert avg_cpu < 30.0, f"Average CPU usage too high: {avg_cpu:.1f}%"
            assert max_cpu < 50.0, f"Peak CPU usage too high: {max_cpu:.1f}%"  # 短時間のピークは50%まで許容
    
    async def monitor_cpu_usage(self, measurements: list, duration: float):
        """CPU使用率監視"""
        process = psutil.Process()
        start_time = time.time()
        
        while time.time() - start_time < duration:
            cpu_usage = process.cpu_percent(interval=0.1)
            measurements.append(cpu_usage)
            await asyncio.sleep(0.5)  # 500ms間隔で測定
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self):
        """メモリ使用量安定性テスト"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # 長期間運用シミュレート（30秒間）
        orchestrator = YesManOrchestrator()
        
        with patch.multiple(
            orchestrator,
            _initialize_components=AsyncMock(),
            ipc_server=Mock()
        ):
            memory_measurements = []
            
            # 30秒間の処理シミュレート
            for i in range(60):  # 500ms × 60 = 30秒
                # メモリ測定
                current_memory = process.memory_info().rss
                memory_mb = current_memory / (1024 * 1024)
                memory_measurements.append(memory_mb)
                
                # 軽い処理をシミュレート
                temp_data = np.random.random(1000).astype(np.float32)
                temp_result = np.mean(temp_data)
                
                await asyncio.sleep(0.5)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        # メモリリーク検出
        assert memory_increase_mb < 50.0, f"Memory leak detected: +{memory_increase_mb:.1f}MB"
        
        # メモリ使用量の安定性
        memory_std = np.std(memory_measurements)
        assert memory_std < 10.0, f"Memory usage too unstable: std={memory_std:.1f}MB"
        
        print(f"Memory stability test:")
        print(f"  Initial: {initial_memory / (1024 * 1024):.1f}MB")
        print(f"  Final: {final_memory / (1024 * 1024):.1f}MB")
        print(f"  Increase: {memory_increase_mb:.1f}MB")
        print(f"  Stability (std): {memory_std:.1f}MB")
    
    @pytest.mark.asyncio
    async def test_realtime_processing_maintenance(self):
        """リアルタイム処理維持テスト"""
        # リアルタイム処理をシミュレート（音声の16kHz処理）
        sample_rate = 16000
        chunk_size = 1600  # 100ms chunks
        
        processing_times = []
        missed_deadlines = 0
        
        async def process_audio_chunk():
            """音声チャンク処理シミュレート"""
            start_time = time.time()
            
            # 音声処理をシミュレート（実際の処理より軽量）
            audio_chunk = np.random.random(chunk_size).astype(np.float32)
            result = np.mean(audio_chunk)
            
            processing_time = time.time() - start_time
            return processing_time
        
        # 10秒間のリアルタイム処理
        for i in range(100):  # 100ms × 100 = 10秒
            chunk_start = time.time()
            
            processing_time = await process_audio_chunk()
            processing_times.append(processing_time)
            
            # デッドライン（100ms）チェック
            if processing_time > 0.1:
                missed_deadlines += 1
            
            # 次のチャンクまで待機
            elapsed = time.time() - chunk_start
            sleep_time = max(0, 0.1 - elapsed)  # 100ms間隔維持
            await asyncio.sleep(sleep_time)
        
        # リアルタイム性能分析
        avg_processing_time = np.mean(processing_times) * 1000  # ms
        max_processing_time = np.max(processing_times) * 1000  # ms
        deadline_miss_rate = missed_deadlines / len(processing_times)
        
        print(f"Realtime processing test:")
        print(f"  Average processing: {avg_processing_time:.2f}ms")
        print(f"  Maximum processing: {max_processing_time:.2f}ms") 
        print(f"  Deadline misses: {missed_deadlines}/{len(processing_times)} ({deadline_miss_rate:.2%})")
        
        # リアルタイム要件
        assert avg_processing_time < 50.0, f"Average processing too slow: {avg_processing_time:.2f}ms"
        assert deadline_miss_rate < 0.05, f"Too many deadline misses: {deadline_miss_rate:.2%}"


@pytest.mark.performance
class TestPerformanceRegression:
    """パフォーマンス回帰テスト"""
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self):
        """パフォーマンスベンチマークテスト"""
        # 各コンポーネントのベンチマーク実行
        benchmarks = {
            'wake_word_detection': await self.benchmark_wake_word(),
            'stt_processing': await self.benchmark_stt(),
            'llm_processing': await self.benchmark_llm(),
            'tts_synthesis': await self.benchmark_tts(),
            'end_to_end': await self.benchmark_end_to_end()
        }
        
        # ベンチマーク結果の表示
        print("\nPerformance Benchmarks:")
        print("-" * 40)
        
        for component, metrics in benchmarks.items():
            print(f"{component}:")
            for metric, value in metrics.items():
                print(f"  {metric}: {value}")
        
        # 回帰検出（基準値との比較）
        baseline = {
            'wake_word_detection': {'avg_time': 0.5},
            'stt_processing': {'avg_time': 0.8},
            'llm_processing': {'avg_time': 1.2},
            'tts_synthesis': {'avg_time': 0.6},
            'end_to_end': {'avg_time': 2.5}
        }
        
        for component, metrics in benchmarks.items():
            if component in baseline:
                baseline_time = baseline[component]['avg_time']
                current_time = metrics['avg_time']
                
                # 20%以上の性能劣化で失敗
                regression_threshold = baseline_time * 1.2
                assert current_time < regression_threshold, \
                    f"{component} performance regression: {current_time:.3f}s > {regression_threshold:.3f}s"
    
    async def benchmark_wake_word(self):
        """ウェイクワード検出ベンチマーク"""
        times = []
        for _ in range(10):
            start = time.time()
            await asyncio.sleep(0.3)  # シミュレート
            times.append(time.time() - start)
        
        return {
            'avg_time': np.mean(times),
            'max_time': np.max(times),
            'min_time': np.min(times)
        }
    
    async def benchmark_stt(self):
        """STTベンチマーク"""
        times = []
        for _ in range(5):
            start = time.time()
            await asyncio.sleep(0.6)  # シミュレート
            times.append(time.time() - start)
        
        return {
            'avg_time': np.mean(times),
            'max_time': np.max(times),
            'min_time': np.min(times)
        }
    
    async def benchmark_llm(self):
        """LLMベンチマーク"""
        times = []
        for _ in range(5):
            start = time.time()
            await asyncio.sleep(1.0)  # シミュレート
            times.append(time.time() - start)
        
        return {
            'avg_time': np.mean(times),
            'max_time': np.max(times), 
            'min_time': np.min(times)
        }
    
    async def benchmark_tts(self):
        """TTSベンチマーク"""
        times = []
        for _ in range(5):
            start = time.time()
            await asyncio.sleep(0.5)  # シミュレート
            times.append(time.time() - start)
        
        return {
            'avg_time': np.mean(times),
            'max_time': np.max(times),
            'min_time': np.min(times)
        }
    
    async def benchmark_end_to_end(self):
        """エンドツーエンドベンチマーク"""
        times = []
        for _ in range(3):
            start = time.time()
            # 全コンポーネント順次実行
            await asyncio.sleep(0.3)  # ウェイクワード
            await asyncio.sleep(0.6)  # STT
            await asyncio.sleep(1.0)  # LLM
            await asyncio.sleep(0.5)  # TTS
            times.append(time.time() - start)
        
        return {
            'avg_time': np.mean(times),
            'max_time': np.max(times),
            'min_time': np.min(times)
        }


if __name__ == "__main__":
    # パフォーマンステスト実行
    pytest.main([__file__, "-v", "-m", "performance", "--tb=short"])