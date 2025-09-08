"""
Unit Tests for IPC Server
Python-Electron IPC通信サーバーのテスト

憲法II: テストファースト - IPC通信の信頼性確保
憲法VI: パフォーマンス制約 - 低レイテンシ通信テスト
"""

import pytest
import asyncio
import json
import websockets
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from audio_layer.ipc_server import (
    IPCServer,
    MessageType, 
    IPCMessage,
    WakeWordEvent,
    SpeechEvent,
    AgentResponseEvent,
    TTSEvent,
    SystemStatus
)


class TestIPCMessage:
    """IPCメッセージデータクラステスト"""
    
    def test_ipc_message_creation(self):
        """IPCメッセージ作成テスト"""
        message = IPCMessage(
            type="test_message",
            data={"key": "value"},
            timestamp="2025-09-08T12:00:00",
            source="test",
            id="msg_123"
        )
        
        assert message.type == "test_message"
        assert message.data == {"key": "value"}
        assert message.timestamp == "2025-09-08T12:00:00"
        assert message.source == "test"
        assert message.id == "msg_123"
    
    def test_wake_word_event_creation(self):
        """ウェイクワードイベント作成テスト"""
        event = WakeWordEvent(
            keyword="Yes-Man",
            confidence=0.95,
            audio_duration=1.2,
            timestamp="2025-09-08T12:00:00"
        )
        
        assert event.keyword == "Yes-Man"
        assert event.confidence == 0.95
        assert event.audio_duration == 1.2
        assert event.timestamp == "2025-09-08T12:00:00"
    
    def test_speech_event_creation(self):
        """音声イベント作成テスト"""
        event = SpeechEvent(
            session_id="session_123",
            audio_level=0.8,
            duration=2.5,
            text="こんにちは",
            timestamp="2025-09-08T12:00:00"
        )
        
        assert event.session_id == "session_123"
        assert event.audio_level == 0.8
        assert event.duration == 2.5
        assert event.text == "こんにちは"
        assert event.timestamp == "2025-09-08T12:00:00"
    
    def test_agent_response_event_creation(self):
        """エージェント応答イベント作成テスト"""
        event = AgentResponseEvent(
            session_id="session_123",
            text="はい！もちろんです！",
            response_time=1.5,
            context_type="greeting",
            confidence=0.9,
            timestamp="2025-09-08T12:00:00"
        )
        
        assert event.session_id == "session_123"
        assert event.text == "はい！もちろんです！"
        assert event.response_time == 1.5
        assert event.context_type == "greeting"
        assert event.confidence == 0.9
    
    def test_system_status_creation(self):
        """システム状態作成テスト"""
        status = SystemStatus(
            cpu_usage=25.0,
            memory_usage=60.0,
            whisper_active=True,
            voicevox_active=True,
            langflow_active=True,
            wake_word_sensitivity=0.8,
            last_wake_word="Yes-Man",
            session_count=1,
            uptime=3600,
            timestamp="2025-09-08T12:00:00"
        )
        
        assert status.cpu_usage == 25.0
        assert status.memory_usage == 60.0
        assert status.whisper_active is True
        assert status.voicevox_active is True
        assert status.langflow_active is True
        assert status.wake_word_sensitivity == 0.8
        assert status.last_wake_word == "Yes-Man"
        assert status.session_count == 1
        assert status.uptime == 3600


class TestIPCServer:
    """IPCサーバー単体テスト"""
    
    @pytest.fixture
    def ipc_server(self):
        """IPCサーバーインスタンス"""
        return IPCServer(host="localhost", port=8765)
    
    @pytest.fixture
    async def mock_websocket(self):
        """モックWebSocketクライアント"""
        websocket = AsyncMock()
        websocket.remote_address = ("127.0.0.1", 12345)
        websocket.send = AsyncMock()
        websocket.closed = False
        return websocket
    
    def test_ipc_server_initialization(self):
        """IPCサーバー初期化テスト"""
        server = IPCServer(host="192.168.1.100", port=9000)
        
        assert server.host == "192.168.1.100"
        assert server.port == 9000
        assert server.running is False
        assert server.server is None
        assert len(server.clients) == 0
        assert len(server.event_handlers) == 0
        assert len(server.message_queue) == 0
        
        # システム状態の初期値確認
        assert server.system_status.cpu_usage == 0.0
        assert server.system_status.memory_usage == 0.0
        assert server.system_status.whisper_active is False
        assert server.system_status.session_count == 0
    
    def test_register_handler(self, ipc_server):
        """イベントハンドラー登録テスト"""
        def test_handler(data):
            return {"status": "handled", "data": data}
        
        ipc_server.register_handler("test_event", test_handler)
        
        assert "test_event" in ipc_server.event_handlers
        assert ipc_server.event_handlers["test_event"] == test_handler
    
    @pytest.mark.asyncio
    async def test_send_to_client_success(self, ipc_server, mock_websocket):
        """クライアントへのメッセージ送信成功テスト"""
        message = {
            "type": "test_message",
            "data": {"key": "value"},
            "timestamp": datetime.now().isoformat(),
            "source": "python"
        }
        
        await ipc_server.send_to_client(mock_websocket, message)
        
        # 送信が呼ばれたことを確認
        mock_websocket.send.assert_called_once()
        
        # 送信データの確認
        sent_data = mock_websocket.send.call_args[0][0]
        parsed_data = json.loads(sent_data)
        
        assert parsed_data["type"] == "test_message"
        assert parsed_data["data"]["key"] == "value"
        assert parsed_data["source"] == "python"
        assert "id" in parsed_data  # メッセージIDが自動生成される
        
        # 統計更新確認
        assert ipc_server.message_stats['sent'] == 1
    
    @pytest.mark.asyncio
    async def test_send_to_client_connection_closed(self, ipc_server, mock_websocket):
        """接続切断時の送信テスト"""
        mock_websocket.send.side_effect = websockets.exceptions.ConnectionClosed(None, None)
        
        message = {"type": "test", "data": {}, "timestamp": "", "source": "python"}
        
        # 例外が発生しないことを確認
        await ipc_server.send_to_client(mock_websocket, message)
        
        # エラー統計が更新されないことを確認（警告のみ）
        assert ipc_server.message_stats['errors'] == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, ipc_server):
        """ブロードキャストメッセージテスト"""
        # モッククライアントを追加
        client1 = AsyncMock()
        client2 = AsyncMock()
        client3 = AsyncMock()
        
        # 1つのクライアントで送信エラーをシミュレート
        client2.send.side_effect = websockets.exceptions.ConnectionClosed(None, None)
        
        ipc_server.clients = {client1, client2, client3}
        
        message = {
            "type": "broadcast_test",
            "data": {"message": "hello all"},
            "timestamp": datetime.now().isoformat(),
            "source": "python"
        }
        
        await ipc_server.broadcast_message(message)
        
        # 正常なクライアントには送信
        client1.send.assert_called_once()
        client3.send.assert_called_once()
        
        # エラーのクライアントは削除される
        assert client2 not in ipc_server.clients
        assert len(ipc_server.clients) == 2
    
    @pytest.mark.asyncio
    async def test_process_message_heartbeat(self, ipc_server, mock_websocket):
        """ハートビートメッセージ処理テスト"""
        raw_message = json.dumps({
            "type": "heartbeat",
            "data": {"timestamp": "2025-09-08T12:00:00"},
            "timestamp": "2025-09-08T12:00:00",
            "source": "electron",
            "id": "msg_123"
        })
        
        await ipc_server.process_message(mock_websocket, raw_message)
        
        # ハートビートレスポンスが送信される
        mock_websocket.send.assert_called_once()
        
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_data["type"] == "heartbeat"
        assert "response_time" in sent_data["data"]
    
    @pytest.mark.asyncio
    async def test_process_message_with_handler(self, ipc_server, mock_websocket):
        """ハンドラー付きメッセージ処理テスト"""
        # テストハンドラー登録
        test_result = {"status": "processed"}
        test_handler = Mock(return_value=test_result)
        ipc_server.register_handler("test_event", test_handler)
        
        raw_message = json.dumps({
            "type": "test_event",
            "data": {"input": "test_data"},
            "timestamp": "2025-09-08T12:00:00",
            "source": "electron"
        })
        
        await ipc_server.process_message(mock_websocket, raw_message)
        
        # ハンドラーが呼ばれる
        test_handler.assert_called_once_with({"input": "test_data"})
        
        # レスポンスが送信される
        mock_websocket.send.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_message_invalid_json(self, ipc_server, mock_websocket):
        """無効JSON処理テスト"""
        raw_message = "invalid json {{"
        
        await ipc_server.process_message(mock_websocket, raw_message)
        
        # エラーレスポンスが送信される
        mock_websocket.send.assert_called()
        
        # エラー統計更新
        assert ipc_server.message_stats['errors'] == 1
    
    @pytest.mark.asyncio
    async def test_send_wake_word_detected(self, ipc_server):
        """ウェイクワード検出送信テスト"""
        # クライアント追加
        mock_client = AsyncMock()
        ipc_server.clients.add(mock_client)
        
        await ipc_server.send_wake_word_detected("Yes-Man", 0.95, 1.2)
        
        # ブロードキャスト送信確認
        mock_client.send.assert_called_once()
        
        sent_data = json.loads(mock_client.send.call_args[0][0])
        assert sent_data["type"] == "wake_word_detected"
        assert sent_data["data"]["keyword"] == "Yes-Man"
        assert sent_data["data"]["confidence"] == 0.95
        assert sent_data["data"]["audio_duration"] == 1.2
        
        # システム状態更新確認
        assert ipc_server.system_status.last_wake_word == "Yes-Man"
    
    @pytest.mark.asyncio
    async def test_send_user_speech_start(self, ipc_server):
        """ユーザー音声開始送信テスト"""
        mock_client = AsyncMock()
        ipc_server.clients.add(mock_client)
        
        await ipc_server.send_user_speech_start("session_123", 0.8)
        
        mock_client.send.assert_called_once()
        
        sent_data = json.loads(mock_client.send.call_args[0][0])
        assert sent_data["type"] == "user_speech_start"
        assert sent_data["data"]["session_id"] == "session_123"
        assert sent_data["data"]["audio_level"] == 0.8
    
    @pytest.mark.asyncio
    async def test_send_user_speech_end(self, ipc_server):
        """ユーザー音声終了送信テスト"""
        mock_client = AsyncMock()
        ipc_server.clients.add(mock_client)
        
        await ipc_server.send_user_speech_end("session_123", "こんにちは", 2.5)
        
        mock_client.send.assert_called_once()
        
        sent_data = json.loads(mock_client.send.call_args[0][0])
        assert sent_data["type"] == "user_speech_end"
        assert sent_data["data"]["session_id"] == "session_123"
        assert sent_data["data"]["text"] == "こんにちは"
        assert sent_data["data"]["duration"] == 2.5
    
    @pytest.mark.asyncio
    async def test_send_agent_response(self, ipc_server):
        """エージェント応答送信テスト"""
        mock_client = AsyncMock()
        ipc_server.clients.add(mock_client)
        
        await ipc_server.send_agent_response(
            "session_123",
            "はい！こんにちはYes-Manです！",
            1.5,
            "greeting",
            0.9
        )
        
        mock_client.send.assert_called_once()
        
        sent_data = json.loads(mock_client.send.call_args[0][0])
        assert sent_data["type"] == "agent_response"
        assert sent_data["data"]["session_id"] == "session_123"
        assert sent_data["data"]["text"] == "はい！こんにちはYes-Manです！"
        assert sent_data["data"]["response_time"] == 1.5
        assert sent_data["data"]["context_type"] == "greeting"
        assert sent_data["data"]["confidence"] == 0.9
    
    @pytest.mark.asyncio
    async def test_send_tts_start(self, ipc_server):
        """TTS開始送信テスト"""
        mock_client = AsyncMock()
        ipc_server.clients.add(mock_client)
        
        await ipc_server.send_tts_start("session_123", "テスト音声です", "1")
        
        mock_client.send.assert_called_once()
        
        sent_data = json.loads(mock_client.send.call_args[0][0])
        assert sent_data["type"] == "tts_start"
        assert sent_data["data"]["session_id"] == "session_123"
        assert sent_data["data"]["text"] == "テスト音声です"
        assert sent_data["data"]["voice_id"] == "1"
    
    @pytest.mark.asyncio
    async def test_send_tts_end(self, ipc_server):
        """TTS終了送信テスト"""
        mock_client = AsyncMock()
        ipc_server.clients.add(mock_client)
        
        await ipc_server.send_tts_end("session_123", "テスト音声です", "1", 3.2)
        
        mock_client.send.assert_called_once()
        
        sent_data = json.loads(mock_client.send.call_args[0][0])
        assert sent_data["type"] == "tts_end"
        assert sent_data["data"]["session_id"] == "session_123"
        assert sent_data["data"]["text"] == "テスト音声です"
        assert sent_data["data"]["voice_id"] == "1"
        assert sent_data["data"]["duration"] == 3.2
    
    @pytest.mark.asyncio
    async def test_send_log_entry(self, ipc_server):
        """ログエントリ送信テスト"""
        mock_client = AsyncMock()
        ipc_server.clients.add(mock_client)
        
        await ipc_server.send_log_entry(
            "INFO",
            "Test log message",
            {"component": "test"}
        )
        
        mock_client.send.assert_called_once()
        
        sent_data = json.loads(mock_client.send.call_args[0][0])
        assert sent_data["type"] == "log_entry"
        assert sent_data["data"]["level"] == "INFO"
        assert sent_data["data"]["message"] == "Test log message"
        assert sent_data["data"]["data"]["component"] == "test"
        assert sent_data["data"]["source"] == "Python"
    
    def test_update_system_status(self, ipc_server):
        """システム状態更新テスト"""
        initial_timestamp = ipc_server.system_status.timestamp
        
        ipc_server.update_system_status(
            cpu_usage=25.5,
            memory_usage=65.0,
            whisper_active=True
        )
        
        assert ipc_server.system_status.cpu_usage == 25.5
        assert ipc_server.system_status.memory_usage == 65.0
        assert ipc_server.system_status.whisper_active is True
        # タイムスタンプが更新される
        assert ipc_server.system_status.timestamp != initial_timestamp
    
    def test_get_stats(self, ipc_server):
        """統計情報取得テスト"""
        # モッククライアント追加
        mock_client = AsyncMock()
        ipc_server.clients.add(mock_client)
        
        # メッセージ統計設定
        ipc_server.message_stats['sent'] = 10
        ipc_server.message_stats['received'] = 15
        ipc_server.message_stats['errors'] = 2
        
        # ハンドラー登録
        ipc_server.register_handler("test", lambda x: x)
        
        stats = ipc_server.get_stats()
        
        assert stats['connected_clients'] == 1
        assert stats['message_stats']['sent'] == 10
        assert stats['message_stats']['received'] == 15
        assert stats['message_stats']['errors'] == 2
        assert stats['server_running'] is False
        assert stats['handlers_registered'] == 1
        assert 'system_status' in stats


class TestIPCServerIntegration:
    """IPC サーバー統合テスト"""
    
    @pytest.mark.asyncio
    async def test_client_connection_lifecycle(self):
        """クライアント接続ライフサイクルテスト"""
        server = IPCServer(host="localhost", port=8766)
        
        # モッククライアント作成
        mock_websocket = AsyncMock()
        mock_websocket.remote_address = ("127.0.0.1", 12345)
        mock_websocket.__aiter__.return_value = iter([])  # 空のメッセージリスト
        
        # handle_clientをテスト
        with patch.object(server, 'send_to_client') as mock_send:
            try:
                await server.handle_client(mock_websocket, "/")
            except StopAsyncIteration:
                pass  # 空のイテレータによる正常終了
        
        # 接続通知が送信される
        mock_send.assert_called()
        call_args = mock_send.call_args[0]
        assert call_args[0] == mock_websocket
        sent_message = call_args[1]
        assert sent_message['type'] == 'system_status'
    
    @pytest.mark.asyncio
    async def test_message_processing_pipeline(self):
        """メッセージ処理パイプラインテスト"""
        server = IPCServer()
        
        # ハンドラー登録
        processed_data = []
        
        def test_handler(data):
            processed_data.append(data)
            return {"status": "handled", "received": data}
        
        server.register_handler("test_pipeline", test_handler)
        
        # モック WebSocket
        mock_websocket = AsyncMock()
        
        # テストメッセージ
        test_message = json.dumps({
            "type": "test_pipeline",
            "data": {"input": "pipeline_test"},
            "timestamp": "2025-09-08T12:00:00",
            "source": "electron"
        })
        
        await server.process_message(mock_websocket, test_message)
        
        # ハンドラーが正しく呼ばれた
        assert len(processed_data) == 1
        assert processed_data[0]["input"] == "pipeline_test"
        
        # レスポンスが送信された
        mock_websocket.send.assert_called()


@pytest.mark.integration
class TestIPCServerPerformance:
    """IPCサーバーパフォーマンステスト（憲法VI準拠）"""
    
    @pytest.mark.asyncio
    async def test_message_processing_latency(self):
        """メッセージ処理レイテンシテスト"""
        server = IPCServer()
        
        # 高速ハンドラー登録
        def fast_handler(data):
            return {"status": "processed"}
        
        server.register_handler("latency_test", fast_handler)
        
        mock_websocket = AsyncMock()
        
        # 複数メッセージの処理時間測定
        import time
        processing_times = []
        
        for i in range(10):
            test_message = json.dumps({
                "type": "latency_test",
                "data": {"index": i},
                "timestamp": "2025-09-08T12:00:00",
                "source": "electron"
            })
            
            start_time = time.time()
            await server.process_message(mock_websocket, test_message)
            end_time = time.time()
            
            processing_times.append(end_time - start_time)
        
        # 平均処理時間が10ms以下
        avg_time = sum(processing_times) / len(processing_times)
        assert avg_time < 0.01  # 10ms
        
        # 最大処理時間が50ms以下
        max_time = max(processing_times)
        assert max_time < 0.05  # 50ms
    
    @pytest.mark.asyncio
    async def test_concurrent_client_handling(self):
        """並行クライアント処理テスト"""
        server = IPCServer()
        
        # 複数クライアントをシミュレート
        clients = []
        for i in range(5):
            client = AsyncMock()
            client.remote_address = ("127.0.0.1", 12345 + i)
            clients.append(client)
            server.clients.add(client)
        
        # ブロードキャストメッセージ
        message = {
            "type": "performance_test",
            "data": {"message": "concurrent test"},
            "timestamp": "2025-09-08T12:00:00",
            "source": "python"
        }
        
        import time
        start_time = time.time()
        
        await server.broadcast_message(message)
        
        end_time = time.time()
        broadcast_time = end_time - start_time
        
        # 5クライアントへのブロードキャストが100ms以内
        assert broadcast_time < 0.1  # 100ms
        
        # すべてのクライアントが送信を受けた
        for client in clients:
            client.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_high_frequency_messaging(self):
        """高頻度メッセージングテスト"""
        server = IPCServer()
        
        message_count = 0
        
        def counting_handler(data):
            nonlocal message_count
            message_count += 1
            return {"count": message_count}
        
        server.register_handler("high_freq", counting_handler)
        
        mock_websocket = AsyncMock()
        
        # 1秒間に100メッセージを処理
        import time
        start_time = time.time()
        
        for i in range(100):
            test_message = json.dumps({
                "type": "high_freq",
                "data": {"index": i},
                "timestamp": "2025-09-08T12:00:00",
                "source": "electron"
            })
            
            await server.process_message(mock_websocket, test_message)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 100メッセージを1秒以内で処理
        assert total_time < 1.0
        
        # すべてのメッセージが処理された
        assert message_count == 100
        
        # 送信統計確認
        assert server.message_stats['received'] == 100
    
    @pytest.mark.asyncio
    async def test_memory_efficiency_sustained_messaging(self):
        """長期間メッセージング メモリ効率テスト"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        server = IPCServer()
        
        def memory_handler(data):
            # 簡単な処理
            return {"processed": len(str(data))}
        
        server.register_handler("memory_test", memory_handler)
        
        mock_websocket = AsyncMock()
        
        # 1000メッセージを処理
        for i in range(1000):
            test_message = json.dumps({
                "type": "memory_test",
                "data": {"index": i, "payload": "x" * 100},
                "timestamp": "2025-09-08T12:00:00",
                "source": "electron"
            })
            
            await server.process_message(mock_websocket, test_message)
            
            if i % 100 == 0:
                gc.collect()  # 定期的なガベージコレクション
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        # メモリ増加は5MB以下
        assert memory_increase_mb < 5.0


@pytest.mark.integration
class TestIPCServerYesManIntegration:
    """Yes-Man固有統合テスト"""
    
    @pytest.mark.asyncio
    async def test_yes_man_conversation_flow(self):
        """Yes-Man会話フロー統合テスト"""
        server = IPCServer()
        
        # 会話フローを記録
        conversation_events = []
        
        # モッククライアント
        mock_client = AsyncMock()
        server.clients.add(mock_client)
        
        # 1. ウェイクワード検出
        await server.send_wake_word_detected("Yes-Man", 0.95, 1.0)
        conversation_events.append("wake_word")
        
        # 2. ユーザー音声開始
        await server.send_user_speech_start("session_123", 0.8)
        conversation_events.append("speech_start")
        
        # 3. ユーザー音声終了（STT結果）
        await server.send_user_speech_end("session_123", "こんにちは", 2.0)
        conversation_events.append("speech_end")
        
        # 4. エージェント応答
        await server.send_agent_response(
            "session_123",
            "はい！こんにちはYes-Manです！",
            1.2,
            "greeting",
            0.9
        )
        conversation_events.append("agent_response")
        
        # 5. TTS開始
        await server.send_tts_start("session_123", "はい！こんにちはYes-Manです！", "1")
        conversation_events.append("tts_start")
        
        # 6. TTS終了
        await server.send_tts_end("session_123", "はい！こんにちはYes-Manです！", "1", 2.5)
        conversation_events.append("tts_end")
        
        # 全イベントが順序よく処理された
        expected_flow = [
            "wake_word",
            "speech_start", 
            "speech_end",
            "agent_response",
            "tts_start",
            "tts_end"
        ]
        
        assert conversation_events == expected_flow
        
        # 各イベントでクライアントに送信された
        assert mock_client.send.call_count == 6
    
    @pytest.mark.asyncio
    async def test_yes_man_error_handling_flow(self):
        """Yes-Manエラー処理フロー統合テスト"""
        server = IPCServer()
        
        mock_client = AsyncMock()
        server.clients.add(mock_client)
        
        # エラーログ送信
        await server.send_log_entry(
            "ERROR",
            "Whisper processing failed",
            {"component": "whisper", "error_type": "timeout"}
        )
        
        # システム状態更新（エラー状態）
        server.update_system_status(
            whisper_active=False,
            cpu_usage=5.0  # 処理停止により低下
        )
        
        # エラーが適切に通知された
        mock_client.send.assert_called()
        
        sent_data = json.loads(mock_client.send.call_args[0][0])
        assert sent_data["type"] == "log_entry"
        assert sent_data["data"]["level"] == "ERROR"
        assert "Whisper processing failed" in sent_data["data"]["message"]
    
    @pytest.mark.asyncio 
    async def test_yes_man_system_monitoring(self):
        """Yes-Manシステム監視統合テスト"""
        server = IPCServer()
        
        # システム状態を段階的に更新
        updates = [
            {"cpu_usage": 15.0, "whisper_active": True},
            {"cpu_usage": 25.0, "voicevox_active": True},
            {"cpu_usage": 30.0, "langflow_active": True, "session_count": 1},
            {"cpu_usage": 20.0, "session_count": 0}  # セッション終了
        ]
        
        for update in updates:
            server.update_system_status(**update)
        
        # 最終状態確認
        final_status = server.system_status
        assert final_status.cpu_usage == 20.0
        assert final_status.whisper_active is True
        assert final_status.voicevox_active is True
        assert final_status.langflow_active is True
        assert final_status.session_count == 0


if __name__ == "__main__":
    # テスト実行
    pytest.main([__file__, "-v", "--tb=short"])