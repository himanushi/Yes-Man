/**
 * システム状態管理ストア (Zustand)
 * 
 * Yes-Man システム全体の状態管理
 * 憲法V: パフォーマンス最適化 - 効率的な状態管理
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import {
  FaceState,
  FaceExpression,
  AnimationState,
  SystemStatus,
  AppSettings,
  LogEntry,
  SystemStore,
  WakeWordEvent,
  SpeechEvent,
  AgentResponseEvent,
  TTSEvent,
  LogLevel
} from '../types';

// デフォルトアニメーション状態
const defaultAnimationState: AnimationState = {
  eyeBlinkRate: 0.3,
  eyeOpenness: 1.0,
  mouthMovement: 0.0,
  headTilt: 0.0,
  glowIntensity: 0.8,
  pulseSpeed: 1.0
};

// デフォルト設定
const defaultSettings: AppSettings = {
  // 顔表示設定
  faceSize: 300,
  animationSpeed: 1.0,
  enableBlinking: true,
  enableGlow: true,
  
  // ウィンドウ設定
  alwaysOnTop: false,
  transparency: 0.95,
  position: { x: 50, y: 50 },
  
  // 音声設定
  wakeWordEnabled: true,
  wakeWordKeyword: 'Yes-Man',
  wakeWordThreshold: 0.8,
  
  // TTS設定
  ttsEnabled: true,
  ttsSpeakerId: 1,
  ttsSpeed: 1.0,
  ttsVolume: 0.8,
  
  // その他
  debugMode: process.env.NODE_ENV === 'development',
  logLevel: 'info',
  autoStart: false
};

// ログ最大保持数
const MAX_LOG_ENTRIES = 1000;

export const useSystemStore = create<SystemStore>()(
  devtools(
    persist(
      (set, get) => ({
        // === 状態 ===
        faceState: 'idle',
        expression: 'neutral',
        animationState: { ...defaultAnimationState },
        systemStatus: null,
        settings: { ...defaultSettings },
        logs: [],

        // === アクション ===
        setFaceState: (state: FaceState) => {
          set((prevState) => {
            // 状態変更時のアニメーション調整
            const newAnimationState = { ...prevState.animationState };
            
            switch (state) {
              case 'listening':
                newAnimationState.glowIntensity = 1.0;
                newAnimationState.pulseSpeed = 1.5;
                newAnimationState.eyeOpenness = 1.2;
                break;
                
              case 'thinking':
                newAnimationState.glowIntensity = 0.6;
                newAnimationState.pulseSpeed = 0.8;
                newAnimationState.eyeBlinkRate = 0.5;
                break;
                
              case 'speaking':
                newAnimationState.mouthMovement = 0.8;
                newAnimationState.pulseSpeed = 2.0;
                newAnimationState.glowIntensity = 1.0;
                break;
                
              case 'error':
                newAnimationState.glowIntensity = 1.0;
                newAnimationState.pulseSpeed = 3.0;
                newAnimationState.eyeBlinkRate = 0.8;
                break;
                
              case 'sleeping':
                newAnimationState.eyeOpenness = 0.2;
                newAnimationState.glowIntensity = 0.3;
                newAnimationState.pulseSpeed = 0.3;
                newAnimationState.eyeBlinkRate = 0.1;
                break;
                
              case 'idle':
              default:
                newAnimationState.eyeOpenness = 1.0;
                newAnimationState.mouthMovement = 0.0;
                newAnimationState.glowIntensity = 0.8;
                newAnimationState.pulseSpeed = 1.0;
                newAnimationState.eyeBlinkRate = 0.3;
                break;
            }

            // ログ記録
            get().addLog({
              level: 'info',
              message: `Face state changed: ${prevState.faceState} → ${state}`,
              timestamp: new Date().toISOString(),
              source: 'SystemStore'
            });

            return {
              faceState: state,
              animationState: newAnimationState
            };
          });

          // Electronに状態変更を通知
          if (window.yesManAPI) {
            window.yesManAPI.face.setState(state).catch(console.error);
          }
        },

        setExpression: (expression: FaceExpression) => {
          set({ expression });
          
          get().addLog({
            level: 'debug',
            message: `Expression changed: ${expression}`,
            timestamp: new Date().toISOString(),
            source: 'SystemStore'
          });
        },

        updateAnimationState: (newState: Partial<AnimationState>) => {
          set((prevState) => ({
            animationState: {
              ...prevState.animationState,
              ...newState
            }
          }));
        },

        updateSystemStatus: (status: Partial<SystemStatus>) => {
          set((prevState) => ({
            systemStatus: prevState.systemStatus
              ? { ...prevState.systemStatus, ...status }
              : { 
                  pythonLayerConnected: false,
                  voicevoxConnected: false,
                  langflowConnected: false,
                  timestamp: new Date().toISOString(),
                  ...status 
                }
          }));
        },

        updateSettings: (newSettings: Partial<AppSettings>) => {
          set((prevState) => {
            const updatedSettings = {
              ...prevState.settings,
              ...newSettings
            };

            // 設定変更をElectronに通知
            if (window.yesManAPI) {
              Object.entries(newSettings).forEach(([key, value]) => {
                window.yesManAPI.settings.set(key, value).catch(console.error);
              });
            }

            get().addLog({
              level: 'info',
              message: `Settings updated: ${Object.keys(newSettings).join(', ')}`,
              timestamp: new Date().toISOString(),
              source: 'SystemStore',
              data: newSettings
            });

            return { settings: updatedSettings };
          });
        },

        addLog: (entry: LogEntry) => {
          set((prevState) => {
            const newLogs = [...prevState.logs, entry];
            
            // ログ数制限
            if (newLogs.length > MAX_LOG_ENTRIES) {
              newLogs.splice(0, newLogs.length - MAX_LOG_ENTRIES);
            }
            
            // コンソールにも出力
            const logLevel = entry.level;
            const message = `[${entry.source || 'System'}] ${entry.message}`;
            
            switch (logLevel) {
              case 'error':
                console.error(message, entry.data);
                break;
              case 'warn':
                console.warn(message, entry.data);
                break;
              case 'debug':
                console.debug(message, entry.data);
                break;
              case 'info':
              default:
                console.log(message, entry.data);
                break;
            }
            
            // Electronのメインプロセスにもログ送信
            if (window.yesManAPI) {
              window.yesManAPI.log[logLevel](entry.message, entry.data).catch(console.error);
            }

            return { logs: newLogs };
          });
        },

        clearLogs: () => {
          set({ logs: [] });
          get().addLog({
            level: 'info',
            message: 'Logs cleared',
            timestamp: new Date().toISOString(),
            source: 'SystemStore'
          });
        },

        // === 音声イベント処理 ===
        handleWakeWordDetected: (event: WakeWordEvent) => {
          get().addLog({
            level: 'info',
            message: `Wake word detected: ${event.keyword} (confidence: ${event.confidence})`,
            timestamp: event.timestamp,
            source: 'AudioLayer',
            data: event
          });

          // 顔状態を変更
          get().setFaceState('listening');
          get().setExpression('excited');
        },

        handleUserSpeechStart: (event: SpeechEvent) => {
          get().addLog({
            level: 'debug',
            message: 'User speech started',
            timestamp: event.timestamp,
            source: 'AudioLayer'
          });

          // リスニング状態継続
          if (get().faceState !== 'listening') {
            get().setFaceState('listening');
          }
        },

        handleUserSpeechEnd: (event: SpeechEvent) => {
          get().addLog({
            level: 'info',
            message: `User speech ended: "${event.text || 'No text'}"`,
            timestamp: event.timestamp,
            source: 'AudioLayer',
            data: event
          });

          // 思考状態に変更
          get().setFaceState('thinking');
          get().setExpression('neutral');
        },

        handleAgentResponse: (event: AgentResponseEvent) => {
          get().addLog({
            level: 'info',
            message: `Agent response: "${event.text}" (${event.executionTimeMs}ms)`,
            timestamp: event.timestamp,
            source: 'AgentExecutor',
            data: event
          });

          // 発話状態に変更
          get().setFaceState('speaking');
          get().setExpression('happy');
        },

        handleTTSStart: (event: TTSEvent) => {
          get().addLog({
            level: 'debug',
            message: `TTS started: "${event.text}"`,
            timestamp: event.timestamp,
            source: 'VoiceVox',
            data: event
          });

          // 発話状態継続
          if (get().faceState !== 'speaking') {
            get().setFaceState('speaking');
          }
        },

        handleTTSEnd: (event: TTSEvent) => {
          get().addLog({
            level: 'debug',
            message: 'TTS ended',
            timestamp: event.timestamp,
            source: 'VoiceVox'
          });

          // アイドル状態に戻る
          get().setFaceState('idle');
          get().setExpression('neutral');
        }
      }),
      
      {
        name: 'yes-man-system-store',
        partialize: (state) => ({
          settings: state.settings,
          // ログは永続化しない（メモリのみ）
        })
      }
    ),
    
    {
      name: 'SystemStore',
      enabled: process.env.NODE_ENV === 'development'
    }
  )
);

// ストア初期化関数
export const initializeSystemStore = () => {
  const store = useSystemStore.getState();
  
  // 初期化ログ
  store.addLog({
    level: 'info',
    message: 'System store initialized',
    timestamp: new Date().toISOString(),
    source: 'SystemStore'
  });

  // Electronイベントリスナー設定
  if (window.yesManAPI) {
    // Python音声レイヤー状態監視
    window.yesManAPI.system.onPythonLayerStatus((data) => {
      store.updateSystemStatus({
        pythonLayerConnected: data.connected,
        timestamp: new Date().toISOString()
      });
      
      if (!data.connected) {
        store.setFaceState('error');
        store.setExpression('sad');
      }
    });

    // Python音声レイヤーログ監視
    window.yesManAPI.system.onPythonLog((logEntry) => {
      store.addLog({
        ...logEntry,
        source: 'PythonLayer'
      });
    });

    // 音声イベントリスナー設定
    window.yesManAPI.audio.onWakeWordDetected(store.handleWakeWordDetected);
    window.yesManAPI.audio.onUserSpeechStart(store.handleUserSpeechStart);
    window.yesManAPI.audio.onUserSpeechEnd(store.handleUserSpeechEnd);
    window.yesManAPI.audio.onAgentResponse(store.handleAgentResponse);
    window.yesManAPI.audio.onTTSStart(store.handleTTSStart);
    window.yesManAPI.audio.onTTSEnd(store.handleTTSEnd);

    store.addLog({
      level: 'info',
      message: 'Electron event listeners configured',
      timestamp: new Date().toISOString(),
      source: 'SystemStore'
    });
  } else {
    store.addLog({
      level: 'warn',
      message: 'Electron API not available - running in browser mode',
      timestamp: new Date().toISOString(),
      source: 'SystemStore'
    });
  }
};

// ストアクリーンアップ関数
export const cleanupSystemStore = () => {
  if (window.yesManAPI) {
    window.yesManAPI.audio.removeAudioListeners();
    window.yesManAPI.system.removeSystemListeners();
    window.yesManAPI.face.removeStateListener();
    
    const store = useSystemStore.getState();
    store.addLog({
      level: 'info',
      message: 'System store cleaned up',
      timestamp: new Date().toISOString(),
      source: 'SystemStore'
    });
  }
};