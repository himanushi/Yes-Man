/**
 * Python-Electron IPC ブリッジサービス
 * 
 * Python音声レイヤーとElectron UIの双方向通信
 * 憲法V: パフォーマンス最適化 - 効率的なメッセージング
 */

import { 
  FaceState, 
  FaceExpression,
  WakeWordEvent,
  SpeechEvent,
  AgentResponseEvent,
  TTSEvent,
  LogEntry,
  SystemStatus 
} from '../types';

// WebSocket接続設定
const WS_URL = 'ws://localhost:8765';
const RECONNECT_INTERVAL = 3000; // 3秒
const MAX_RECONNECT_ATTEMPTS = 10;

// メッセージ型定義
interface IPCMessage {
  type: string;
  data: any;
  timestamp: string;
  source: 'python' | 'electron';
  id?: string;
}

// イベントリスナー型定義
type EventListener<T = any> = (data: T) => void;

export class IPCBridge {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private isConnected = false;
  
  // イベントリスナーマップ
  private listeners: Map<string, EventListener[]> = new Map();
  
  // メッセージキュー（未接続時のメッセージ保存）
  private messageQueue: IPCMessage[] = [];
  
  // ハートビート
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private lastHeartbeat: number = 0;

  constructor() {
    this.initializeConnection();
  }

  /**
   * WebSocket接続初期化
   */
  private initializeConnection(): void {
    try {
      console.log('Initializing IPC bridge connection...');
      
      this.ws = new WebSocket(WS_URL);
      
      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.scheduleReconnect();
    }
  }

  /**
   * 接続オープン処理
   */
  private handleOpen(): void {
    console.log('IPC bridge connected to Python layer');
    
    this.isConnected = true;
    this.reconnectAttempts = 0;
    
    // ハートビート開始
    this.startHeartbeat();
    
    // キューに溜まったメッセージを送信
    this.flushMessageQueue();
    
    // 接続イベントを発火
    this.emit('connection', { connected: true });
  }

  /**
   * メッセージ受信処理
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const message: IPCMessage = JSON.parse(event.data);
      
      // ハートビート更新
      this.lastHeartbeat = Date.now();
      
      console.debug('IPC message received:', message.type, message.data);
      
      // メッセージタイプ別の処理
      switch (message.type) {
        case 'wake_word_detected':
          this.emit('wakeWordDetected', message.data as WakeWordEvent);
          break;
          
        case 'user_speech_start':
          this.emit('userSpeechStart', message.data as SpeechEvent);
          break;
          
        case 'user_speech_end':
          this.emit('userSpeechEnd', message.data as SpeechEvent);
          break;
          
        case 'agent_response':
          this.emit('agentResponse', message.data as AgentResponseEvent);
          break;
          
        case 'tts_start':
          this.emit('ttsStart', message.data as TTSEvent);
          break;
          
        case 'tts_end':
          this.emit('ttsEnd', message.data as TTSEvent);
          break;
          
        case 'system_status':
          this.emit('systemStatus', message.data as SystemStatus);
          break;
          
        case 'log_entry':
          this.emit('logEntry', message.data as LogEntry);
          break;
          
        case 'error':
          console.error('Python layer error:', message.data);
          this.emit('error', message.data);
          break;
          
        case 'heartbeat':
          // ハートビートレスポンス - 何もしない
          break;
          
        default:
          console.warn('Unknown IPC message type:', message.type);
          this.emit('unknownMessage', message);
          break;
      }
      
    } catch (error) {
      console.error('Failed to parse IPC message:', error);
    }
  }

  /**
   * 接続クローズ処理
   */
  private handleClose(): void {
    console.log('IPC bridge connection closed');
    
    this.isConnected = false;
    this.stopHeartbeat();
    
    // 接続イベントを発火
    this.emit('connection', { connected: false });
    
    // 再接続試行
    this.scheduleReconnect();
  }

  /**
   * エラー処理
   */
  private handleError(error: Event): void {
    console.error('IPC bridge WebSocket error:', error);
    this.emit('error', { message: 'WebSocket connection error', error });
  }

  /**
   * 再接続スケジュール
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      console.error('Max reconnection attempts reached. Giving up.');
      this.emit('connectionFailed', { 
        attempts: this.reconnectAttempts,
        maxAttempts: MAX_RECONNECT_ATTEMPTS 
      });
      return;
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    
    this.reconnectAttempts++;
    const delay = RECONNECT_INTERVAL * Math.pow(1.5, this.reconnectAttempts - 1);
    
    console.log(`Scheduling reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.initializeConnection();
    }, delay);
  }

  /**
   * ハートビート開始
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected) {
        this.sendMessage({
          type: 'heartbeat',
          data: { timestamp: Date.now() },
          timestamp: new Date().toISOString(),
          source: 'electron'
        });
        
        // ハートビートタイムアウトチェック
        if (Date.now() - this.lastHeartbeat > 30000) { // 30秒
          console.warn('Heartbeat timeout detected');
          this.ws?.close();
        }
      }
    }, 10000); // 10秒間隔
  }

  /**
   * ハートビート停止
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * メッセージ送信
   */
  private sendMessage(message: IPCMessage): void {
    if (!message.id) {
      message.id = this.generateMessageId();
    }
    
    if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message));
        console.debug('IPC message sent:', message.type, message.data);
      } catch (error) {
        console.error('Failed to send IPC message:', error);
        this.messageQueue.push(message);
      }
    } else {
      // 未接続時はキューに保存
      this.messageQueue.push(message);
      console.debug('IPC message queued:', message.type);
    }
  }

  /**
   * キューメッセージ送信
   */
  private flushMessageQueue(): void {
    if (this.messageQueue.length === 0) return;
    
    console.log(`Sending ${this.messageQueue.length} queued messages`);
    
    const messages = [...this.messageQueue];
    this.messageQueue = [];
    
    messages.forEach(message => {
      this.sendMessage(message);
    });
  }

  /**
   * メッセージID生成
   */
  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * イベントリスナー登録
   */
  public on<T = any>(event: string, listener: EventListener<T>): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(listener);
  }

  /**
   * イベントリスナー削除
   */
  public off<T = any>(event: string, listener?: EventListener<T>): void {
    const eventListeners = this.listeners.get(event);
    if (!eventListeners) return;
    
    if (listener) {
      const index = eventListeners.indexOf(listener);
      if (index !== -1) {
        eventListeners.splice(index, 1);
      }
    } else {
      this.listeners.delete(event);
    }
  }

  /**
   * イベント発火
   */
  private emit<T = any>(event: string, data: T): void {
    const eventListeners = this.listeners.get(event);
    if (!eventListeners) return;
    
    eventListeners.forEach(listener => {
      try {
        listener(data);
      } catch (error) {
        console.error(`Error in event listener for ${event}:`, error);
      }
    });
  }

  // === Public API ===

  /**
   * 顔状態変更送信
   */
  public sendFaceStateChange(state: FaceState, expression?: FaceExpression): void {
    this.sendMessage({
      type: 'face_state_change',
      data: { state, expression },
      timestamp: new Date().toISOString(),
      source: 'electron'
    });
  }

  /**
   * ユーザー入力送信（手動入力用）
   */
  public sendUserInput(text: string, sessionId?: string): void {
    this.sendMessage({
      type: 'user_input',
      data: { text, sessionId },
      timestamp: new Date().toISOString(),
      source: 'electron'
    });
  }

  /**
   * システム制御コマンド送信
   */
  public sendSystemCommand(command: string, params?: any): void {
    this.sendMessage({
      type: 'system_command',
      data: { command, params },
      timestamp: new Date().toISOString(),
      source: 'electron'
    });
  }

  /**
   * 設定変更送信
   */
  public sendSettingsUpdate(settings: any): void {
    this.sendMessage({
      type: 'settings_update',
      data: settings,
      timestamp: new Date().toISOString(),
      source: 'electron'
    });
  }

  /**
   * ログ送信
   */
  public sendLog(level: string, message: string, data?: any): void {
    this.sendMessage({
      type: 'log_entry',
      data: {
        level,
        message,
        data,
        source: 'UI',
        timestamp: new Date().toISOString()
      } as LogEntry,
      timestamp: new Date().toISOString(),
      source: 'electron'
    });
  }

  /**
   * 接続状態取得
   */
  public isConnectionActive(): boolean {
    return this.isConnected && this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * 接続統計取得
   */
  public getConnectionStats(): {
    connected: boolean;
    reconnectAttempts: number;
    queuedMessages: number;
    lastHeartbeat: number;
  } {
    return {
      connected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts,
      queuedMessages: this.messageQueue.length,
      lastHeartbeat: this.lastHeartbeat
    };
  }

  /**
   * 接続強制再試行
   */
  public forceReconnect(): void {
    this.reconnectAttempts = 0;
    
    if (this.ws) {
      this.ws.close();
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    setTimeout(() => {
      this.initializeConnection();
    }, 1000);
  }

  /**
   * リソースクリーンアップ
   */
  public cleanup(): void {
    console.log('Cleaning up IPC bridge...');
    
    this.stopHeartbeat();
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.listeners.clear();
    this.messageQueue = [];
    this.isConnected = false;
  }
}

// シングルトンインスタンス
let ipcBridgeInstance: IPCBridge | null = null;

/**
 * IPCブリッジインスタンス取得
 */
export const getIPCBridge = (): IPCBridge => {
  if (!ipcBridgeInstance) {
    ipcBridgeInstance = new IPCBridge();
  }
  return ipcBridgeInstance;
};

/**
 * IPCブリッジクリーンアップ
 */
export const cleanupIPCBridge = (): void => {
  if (ipcBridgeInstance) {
    ipcBridgeInstance.cleanup();
    ipcBridgeInstance = null;
  }
};

export default IPCBridge;