"""
Yes-Man IPC サーバー
Python音声レイヤー ⟷ Electron UI 通信

憲法VI: パフォーマンス最適化 - WebSocket非同期通信
憲法VIII: 指示に従う - ElectronUI連携の確実な実装
"""

import asyncio
import websockets
import json
import logging
import signal
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageType(Enum):
    # From Python to Electron
    WAKE_WORD_DETECTED = "wake_word_detected"
    USER_SPEECH_START = "user_speech_start"
    USER_SPEECH_END = "user_speech_end"
    AGENT_RESPONSE = "agent_response"
    TTS_START = "tts_start"
    TTS_END = "tts_end"
    SYSTEM_STATUS = "system_status"
    LOG_ENTRY = "log_entry"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    
    # From Electron to Python
    FACE_STATE_CHANGE = "face_state_change"
    USER_INPUT = "user_input"
    SYSTEM_COMMAND = "system_command"
    SETTINGS_UPDATE = "settings_update"

@dataclass
class IPCMessage:
    """IPC メッセージ形式"""
    type: str
    data: Dict[str, Any]
    timestamp: str
    source: str
    id: Optional[str] = None

@dataclass
class WakeWordEvent:
    """ウェイクワード検出イベント"""
    keyword: str
    confidence: float
    audio_duration: float
    timestamp: str

@dataclass
class SpeechEvent:
    """音声イベント"""
    session_id: str
    audio_level: float
    duration: Optional[float] = None
    text: Optional[str] = None
    timestamp: Optional[str] = None

@dataclass
class AgentResponseEvent:
    """エージェント応答イベント"""
    session_id: str
    text: str
    response_time: float
    context_type: str
    confidence: float
    timestamp: str

@dataclass
class TTSEvent:
    """TTS イベント"""
    session_id: str
    text: str
    voice_id: str
    duration: Optional[float] = None
    timestamp: str

@dataclass
class SystemStatus:
    """システム状態"""
    cpu_usage: float
    memory_usage: float
    whisper_active: bool
    voicevox_active: bool
    langflow_active: bool
    wake_word_sensitivity: float
    last_wake_word: Optional[str]
    session_count: int
    uptime: int
    timestamp: str

class IPCServer:
    """WebSocket IPC サーバー"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.event_handlers: Dict[str, Callable] = {}
        self.running = False
        self.server = None
        self.heartbeat_task = None
        
        # システム状態管理
        self.system_status = SystemStatus(
            cpu_usage=0.0,
            memory_usage=0.0,
            whisper_active=False,
            voicevox_active=False,
            langflow_active=False,
            wake_word_sensitivity=0.8,
            last_wake_word=None,
            session_count=0,
            uptime=0,
            timestamp=datetime.now().isoformat()
        )
        
        # メッセージ統計
        self.message_stats = {
            'sent': 0,
            'received': 0,
            'errors': 0
        }
    
    def register_handler(self, message_type: str, handler: Callable):
        """イベントハンドラー登録"""
        self.event_handlers[message_type] = handler
        logger.info(f"Handler registered for: {message_type}")
    
    async def start_server(self):
        """サーバー開始"""
        logger.info(f"Starting IPC server on {self.host}:{self.port}")
        
        try:
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10,
                max_size=10**6  # 1MB max message size
            )
            
            self.running = True
            
            # ハートビート開始
            self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())
            
            logger.info("IPC server started successfully")
            
            # シグナルハンドラー設定
            loop = asyncio.get_event_loop()
            for sig in [signal.SIGTERM, signal.SIGINT]:
                loop.add_signal_handler(sig, self.stop_server)
            
            await self.server.wait_closed()
            
        except Exception as e:
            logger.error(f"Failed to start IPC server: {e}")
            raise
    
    async def handle_client(self, websocket, path):
        """クライアント接続処理"""
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client connected from {client_addr}")
        
        self.clients.add(websocket)
        self.system_status.session_count = len(self.clients)
        
        try:
            # 接続通知
            await self.send_to_client(websocket, {
                'type': MessageType.SYSTEM_STATUS.value,
                'data': asdict(self.system_status),
                'timestamp': datetime.now().isoformat(),
                'source': 'python'
            })
            
            async for message in websocket:
                await self.process_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_addr} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_addr}: {e}")
        finally:
            self.clients.discard(websocket)
            self.system_status.session_count = len(self.clients)
    
    async def process_message(self, websocket, raw_message: str):
        """受信メッセージ処理"""
        try:
            data = json.loads(raw_message)
            message = IPCMessage(
                type=data.get('type'),
                data=data.get('data', {}),
                timestamp=data.get('timestamp'),
                source=data.get('source'),
                id=data.get('id')
            )
            
            self.message_stats['received'] += 1
            logger.debug(f"Received message: {message.type}")
            
            # ハートビート処理
            if message.type == MessageType.HEARTBEAT.value:
                await self.send_to_client(websocket, {
                    'type': MessageType.HEARTBEAT.value,
                    'data': {'response_time': datetime.now().isoformat()},
                    'timestamp': datetime.now().isoformat(),
                    'source': 'python'
                })
                return
            
            # 登録されたハンドラーがあれば実行
            handler = self.event_handlers.get(message.type)
            if handler:
                try:
                    result = await handler(message.data) if asyncio.iscoroutinefunction(handler) else handler(message.data)
                    if result:
                        await self.send_to_client(websocket, {
                            'type': f"{message.type}_response",
                            'data': result,
                            'timestamp': datetime.now().isoformat(),
                            'source': 'python'
                        })
                except Exception as e:
                    logger.error(f"Handler error for {message.type}: {e}")
                    await self.send_error(websocket, f"Handler error: {str(e)}")
            else:
                logger.warning(f"No handler for message type: {message.type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            await self.send_error(websocket, "Invalid JSON format")
            self.message_stats['errors'] += 1
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send_error(websocket, f"Processing error: {str(e)}")
            self.message_stats['errors'] += 1
    
    async def send_to_client(self, websocket, message: Dict[str, Any]):
        """クライアントへメッセージ送信"""
        try:
            if 'id' not in message:
                message['id'] = f"msg_{datetime.now().timestamp()}_{id(message)}"
            
            await websocket.send(json.dumps(message, ensure_ascii=False))
            self.message_stats['sent'] += 1
            
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Attempted to send to closed connection")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.message_stats['errors'] += 1
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """全クライアントへブロードキャスト"""
        if not self.clients:
            logger.debug("No clients to broadcast to")
            return
        
        if 'id' not in message:
            message['id'] = f"broadcast_{datetime.now().timestamp()}_{id(message)}"
        
        message_json = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        
        for client in self.clients:
            try:
                await client.send(message_json)
                self.message_stats['sent'] += 1
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Failed to broadcast to client: {e}")
                disconnected.add(client)
                self.message_stats['errors'] += 1
        
        # 切断されたクライアントを削除
        self.clients -= disconnected
        self.system_status.session_count = len(self.clients)
    
    async def send_error(self, websocket, error_message: str):
        """エラーメッセージ送信"""
        await self.send_to_client(websocket, {
            'type': MessageType.ERROR.value,
            'data': {'message': error_message},
            'timestamp': datetime.now().isoformat(),
            'source': 'python'
        })
    
    async def heartbeat_loop(self):
        """ハートビート定期送信"""
        while self.running:
            try:
                await asyncio.sleep(10)  # 10秒間隔
                if self.clients:
                    await self.broadcast_message({
                        'type': MessageType.HEARTBEAT.value,
                        'data': {
                            'server_time': datetime.now().isoformat(),
                            'connected_clients': len(self.clients),
                            'uptime': self.get_uptime()
                        },
                        'timestamp': datetime.now().isoformat(),
                        'source': 'python'
                    })
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
    
    def get_uptime(self) -> int:
        """アップタイム取得（秒）"""
        # 実装簡略化: 固定値返却
        return 3600
    
    def stop_server(self):
        """サーバー停止"""
        logger.info("Stopping IPC server...")
        self.running = False
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        
        if self.server:
            self.server.close()
    
    def update_system_status(self, **kwargs):
        """システム状態更新"""
        for key, value in kwargs.items():
            if hasattr(self.system_status, key):
                setattr(self.system_status, key, value)
        
        self.system_status.timestamp = datetime.now().isoformat()
    
    async def send_wake_word_detected(self, keyword: str, confidence: float, audio_duration: float):
        """ウェイクワード検出通知"""
        event = WakeWordEvent(
            keyword=keyword,
            confidence=confidence,
            audio_duration=audio_duration,
            timestamp=datetime.now().isoformat()
        )
        
        await self.broadcast_message({
            'type': MessageType.WAKE_WORD_DETECTED.value,
            'data': asdict(event),
            'timestamp': datetime.now().isoformat(),
            'source': 'python'
        })
        
        # システム状態更新
        self.update_system_status(last_wake_word=keyword)
    
    async def send_user_speech_start(self, session_id: str, audio_level: float):
        """ユーザー音声開始通知"""
        event = SpeechEvent(
            session_id=session_id,
            audio_level=audio_level,
            timestamp=datetime.now().isoformat()
        )
        
        await self.broadcast_message({
            'type': MessageType.USER_SPEECH_START.value,
            'data': asdict(event),
            'timestamp': datetime.now().isoformat(),
            'source': 'python'
        })
    
    async def send_user_speech_end(self, session_id: str, text: str, duration: float):
        """ユーザー音声終了通知"""
        event = SpeechEvent(
            session_id=session_id,
            audio_level=0.0,
            duration=duration,
            text=text,
            timestamp=datetime.now().isoformat()
        )
        
        await self.broadcast_message({
            'type': MessageType.USER_SPEECH_END.value,
            'data': asdict(event),
            'timestamp': datetime.now().isoformat(),
            'source': 'python'
        })
    
    async def send_agent_response(self, session_id: str, text: str, response_time: float, context_type: str, confidence: float):
        """エージェント応答通知"""
        event = AgentResponseEvent(
            session_id=session_id,
            text=text,
            response_time=response_time,
            context_type=context_type,
            confidence=confidence,
            timestamp=datetime.now().isoformat()
        )
        
        await self.broadcast_message({
            'type': MessageType.AGENT_RESPONSE.value,
            'data': asdict(event),
            'timestamp': datetime.now().isoformat(),
            'source': 'python'
        })
    
    async def send_tts_start(self, session_id: str, text: str, voice_id: str):
        """TTS開始通知"""
        event = TTSEvent(
            session_id=session_id,
            text=text,
            voice_id=voice_id,
            timestamp=datetime.now().isoformat()
        )
        
        await self.broadcast_message({
            'type': MessageType.TTS_START.value,
            'data': asdict(event),
            'timestamp': datetime.now().isoformat(),
            'source': 'python'
        })
    
    async def send_tts_end(self, session_id: str, text: str, voice_id: str, duration: float):
        """TTS終了通知"""
        event = TTSEvent(
            session_id=session_id,
            text=text,
            voice_id=voice_id,
            duration=duration,
            timestamp=datetime.now().isoformat()
        )
        
        await self.broadcast_message({
            'type': MessageType.TTS_END.value,
            'data': asdict(event),
            'timestamp': datetime.now().isoformat(),
            'source': 'python'
        })
    
    async def send_log_entry(self, level: str, message: str, data: Optional[Dict] = None):
        """ログエントリ送信"""
        log_entry = {
            'level': level,
            'message': message,
            'data': data or {},
            'source': 'Python',
            'timestamp': datetime.now().isoformat()
        }
        
        await self.broadcast_message({
            'type': MessageType.LOG_ENTRY.value,
            'data': log_entry,
            'timestamp': datetime.now().isoformat(),
            'source': 'python'
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報取得"""
        return {
            'connected_clients': len(self.clients),
            'message_stats': self.message_stats.copy(),
            'system_status': asdict(self.system_status),
            'server_running': self.running,
            'handlers_registered': len(self.event_handlers)
        }

# シングルトンインスタンス
_ipc_server: Optional[IPCServer] = None

def get_ipc_server() -> IPCServer:
    """IPCサーバーインスタンス取得"""
    global _ipc_server
    if _ipc_server is None:
        _ipc_server = IPCServer()
    return _ipc_server

def start_ipc_server_background():
    """IPCサーバーをバックグラウンドで開始"""
    def run_server():
        server = get_ipc_server()
        asyncio.run(server.start_server())
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    # テスト実行
    async def main():
        server = IPCServer()
        
        # テスト用ハンドラー
        def handle_user_input(data):
            print(f"User input received: {data}")
            return {"status": "processed", "echo": data}
        
        server.register_handler(MessageType.USER_INPUT.value, handle_user_input)
        
        await server.start_server()
    
    asyncio.run(main())