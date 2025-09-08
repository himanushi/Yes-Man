/**
 * TypeScript型定義
 * 
 * Yes-Man顔UIの型定義
 */

// 顔状態
export type FaceState = 
  | 'idle'           // 待機中
  | 'listening'      // 音声認識中
  | 'thinking'       // エージェント処理中
  | 'speaking'       // TTS再生中
  | 'error'          // エラー状態
  | 'sleeping';      // スリープ状態

// 表情
export type FaceExpression =
  | 'neutral'        // 中性
  | 'happy'          // 嬉しい
  | 'excited'        // 興奮
  | 'confused'       // 困惑
  | 'sad'            // 悲しい
  | 'angry'          // 怒り
  | 'surprised';     // 驚き

// アニメーション状態
export interface AnimationState {
  eyeBlinkRate: number;      // 瞬きの頻度 (0-1)
  eyeOpenness: number;       // 目の開き具合 (0-1)
  mouthMovement: number;     // 口の動き (0-1)
  headTilt: number;          // 首の傾き (-1 to 1)
  glowIntensity: number;     // 光る強さ (0-1)
  pulseSpeed: number;        // パルスの速度 (0-2)
}

// システム状態
export interface SystemStatus {
  pythonLayerConnected: boolean;
  voicevoxConnected: boolean;
  langflowConnected: boolean;
  currentSession?: string;
  timestamp: string;
}

// 音声イベントデータ
export interface WakeWordEvent {
  confidence: number;
  timestamp: string;
  keyword: string;
}

export interface SpeechEvent {
  text?: string;
  duration?: number;
  timestamp: string;
}

export interface AgentResponseEvent {
  text: string;
  executionTimeMs: number;
  sessionId: string;
  timestamp: string;
}

export interface TTSEvent {
  text: string;
  duration?: number;
  speakerId?: number;
  timestamp: string;
}

// ログレベル
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

// ログエントリ
export interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  source?: string;
  data?: any;
}

// 設定項目
export interface AppSettings {
  // 顔表示設定
  faceSize: number;                 // 顔サイズ (50-200)
  animationSpeed: number;           // アニメーション速度 (0.5-2.0)
  enableBlinking: boolean;          // 瞬きを有効化
  enableGlow: boolean;              // 光エフェクトを有効化
  
  // ウィンドウ設定
  alwaysOnTop: boolean;            // 常に最前面
  transparency: number;             // 透明度 (0-1)
  position: { x: number; y: number }; // ウィンドウ位置
  
  // 音声設定
  wakeWordEnabled: boolean;         // ウェイクワード有効化
  wakeWordKeyword: string;          // ウェイクワード
  wakeWordThreshold: number;        // 検出閾値 (0-1)
  
  // TTS設定
  ttsEnabled: boolean;              // TTS有効化
  ttsSpeakerId: number;            // VoiceVoxスピーカーID
  ttsSpeed: number;                // 再生速度 (0.5-2.0)
  ttsVolume: number;               // 音量 (0-1)
  
  // その他
  debugMode: boolean;               // デバッグモード
  logLevel: LogLevel;              // ログレベル
  autoStart: boolean;               // 自動起動
}

// 顔コンポーネントのプロパティ
export interface FaceAnimationProps {
  state: FaceState;
  expression: FaceExpression;
  animationState: AnimationState;
  className?: string;
  size?: number;
  onStateChange?: (state: FaceState) => void;
}

// 設定コンポーネントのプロパティ
export interface SettingsProps {
  settings: AppSettings;
  onSettingsChange: (settings: Partial<AppSettings>) => void;
  onClose: () => void;
}

// システム状態ストア
export interface SystemStore {
  // 状態
  faceState: FaceState;
  expression: FaceExpression;
  animationState: AnimationState;
  systemStatus: SystemStatus | null;
  settings: AppSettings;
  logs: LogEntry[];
  
  // アクション
  setFaceState: (state: FaceState) => void;
  setExpression: (expression: FaceExpression) => void;
  updateAnimationState: (state: Partial<AnimationState>) => void;
  updateSystemStatus: (status: Partial<SystemStatus>) => void;
  updateSettings: (settings: Partial<AppSettings>) => void;
  addLog: (entry: LogEntry) => void;
  clearLogs: () => void;
  
  // 音声イベント処理
  handleWakeWordDetected: (event: WakeWordEvent) => void;
  handleUserSpeechStart: (event: SpeechEvent) => void;
  handleUserSpeechEnd: (event: SpeechEvent) => void;
  handleAgentResponse: (event: AgentResponseEvent) => void;
  handleTTSStart: (event: TTSEvent) => void;
  handleTTSEnd: (event: TTSEvent) => void;
}

// API関数型
export interface YesManAPI {
  face: {
    setState: (state: FaceState) => Promise<{ success: boolean }>;
    onStateChange: (callback: (data: any) => void) => void;
    removeStateListener: () => void;
  };
  
  system: {
    getStatus: () => Promise<SystemStatus>;
    startPythonLayer: () => Promise<{ success: boolean; message: string }>;
    stopPythonLayer: () => Promise<{ success: boolean; message: string }>;
    quit: () => Promise<void>;
    onPythonLayerStatus: (callback: (data: any) => void) => void;
    onPythonLog: (callback: (data: LogEntry) => void) => void;
    removeSystemListeners: () => void;
  };
  
  window: {
    minimize: () => Promise<void>;
    maximize: () => Promise<void>;
    close: () => Promise<void>;
  };
  
  log: {
    info: (message: string, data?: any) => Promise<void>;
    warn: (message: string, data?: any) => Promise<void>;
    error: (message: string, data?: any) => Promise<void>;
    debug: (message: string, data?: any) => Promise<void>;
  };
  
  settings: {
    get: (key: string) => Promise<any>;
    set: (key: string, value: any) => Promise<void>;
    getAll: () => Promise<AppSettings>;
    onSettingChange: (callback: (data: any) => void) => void;
    removeSettingListener: () => void;
  };
  
  audio: {
    onWakeWordDetected: (callback: (data: WakeWordEvent) => void) => void;
    onUserSpeechStart: (callback: (data: SpeechEvent) => void) => void;
    onUserSpeechEnd: (callback: (data: SpeechEvent) => void) => void;
    onAgentResponse: (callback: (data: AgentResponseEvent) => void) => void;
    onTTSStart: (callback: (data: TTSEvent) => void) => void;
    onTTSEnd: (callback: (data: TTSEvent) => void) => void;
    removeAudioListeners: () => void;
  };
  
  utils: {
    getVersion: () => Promise<string>;
    getPlatform: () => string;
    getNodeVersion: () => string;
    getElectronVersion: () => string;
  };
}

// Window型拡張（global API）
declare global {
  interface Window {
    yesManAPI: YesManAPI;
    electronDebug?: {
      versions: any;
      platform: string;
      arch: string;
    };
  }
}