/**
 * Yes-Man Face UI エントリーポイント
 * 
 * Reactアプリケーションの起動とElectron統合
 */

import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';

// React 18 Strict Mode での開発時警告抑制
const isDev = process.env.NODE_ENV === 'development';

// ルート要素取得
const container = document.getElementById('root');
if (!container) {
  throw new Error('Root element not found');
}

// React Root作成
const root = createRoot(container);

// アプリケーション起動
root.render(
  isDev ? (
    <React.StrictMode>
      <App />
    </React.StrictMode>
  ) : (
    <App />
  )
);

// Electron環境での追加設定
if (window.yesManAPI) {
  console.log('Yes-Man Face UI started in Electron environment');
  
  // Electron固有の初期化処理
  window.addEventListener('beforeunload', () => {
    // クリーンアップ処理
    if (window.yesManAPI?.audio?.removeAudioListeners) {
      window.yesManAPI.audio.removeAudioListeners();
    }
    if (window.yesManAPI?.system?.removeSystemListeners) {
      window.yesManAPI.system.removeSystemListeners();
    }
  });
  
} else {
  console.log('Yes-Man Face UI started in browser environment');
  
  // ブラウザ環境でのデモ用モックAPI
  (window as any).yesManAPI = {
    face: {
      setState: async (state: string) => {
        console.log('Mock: Face state set to', state);
        return { success: true };
      },
      onStateChange: (callback: Function) => {
        console.log('Mock: Face state listener added');
      },
      removeStateListener: () => {
        console.log('Mock: Face state listener removed');
      }
    },
    system: {
      getStatus: async () => ({
        pythonLayerConnected: false,
        voicevoxConnected: false,
        langflowConnected: false,
        timestamp: new Date().toISOString()
      }),
      startPythonLayer: async () => ({
        success: false,
        message: 'Not available in browser mode'
      }),
      stopPythonLayer: async () => ({
        success: false,
        message: 'Not available in browser mode'
      }),
      quit: async () => {
        console.log('Mock: Quit requested');
      },
      onPythonLayerStatus: (callback: Function) => {
        console.log('Mock: Python layer status listener added');
      },
      onPythonLog: (callback: Function) => {
        console.log('Mock: Python log listener added');
      },
      removeSystemListeners: () => {
        console.log('Mock: System listeners removed');
      }
    },
    window: {
      minimize: async () => {
        console.log('Mock: Window minimize');
      },
      maximize: async () => {
        console.log('Mock: Window maximize');
      },
      close: async () => {
        console.log('Mock: Window close');
      }
    },
    log: {
      info: async (message: string, data?: any) => {
        console.log(`[INFO] ${message}`, data);
      },
      warn: async (message: string, data?: any) => {
        console.warn(`[WARN] ${message}`, data);
      },
      error: async (message: string, data?: any) => {
        console.error(`[ERROR] ${message}`, data);
      },
      debug: async (message: string, data?: any) => {
        console.debug(`[DEBUG] ${message}`, data);
      }
    },
    settings: {
      get: async (key: string) => {
        const stored = localStorage.getItem(`yes-man-setting-${key}`);
        return stored ? JSON.parse(stored) : null;
      },
      set: async (key: string, value: any) => {
        localStorage.setItem(`yes-man-setting-${key}`, JSON.stringify(value));
      },
      getAll: async () => ({}),
      onSettingChange: (callback: Function) => {
        console.log('Mock: Setting change listener added');
      },
      removeSettingListener: () => {
        console.log('Mock: Setting change listener removed');
      }
    },
    audio: {
      onWakeWordDetected: (callback: Function) => {
        console.log('Mock: Wake word listener added');
      },
      onUserSpeechStart: (callback: Function) => {
        console.log('Mock: Speech start listener added');
      },
      onUserSpeechEnd: (callback: Function) => {
        console.log('Mock: Speech end listener added');
      },
      onAgentResponse: (callback: Function) => {
        console.log('Mock: Agent response listener added');
      },
      onTTSStart: (callback: Function) => {
        console.log('Mock: TTS start listener added');
      },
      onTTSEnd: (callback: Function) => {
        console.log('Mock: TTS end listener added');
      },
      removeAudioListeners: () => {
        console.log('Mock: Audio listeners removed');
      }
    },
    utils: {
      getVersion: async () => '1.0.0-mock',
      getPlatform: () => navigator.platform,
      getNodeVersion: () => 'N/A',
      getElectronVersion: () => 'N/A'
    }
  };
}

// パフォーマンス監視（開発時のみ）
if (isDev && 'performance' in window && 'measureUserAgentSpecificMemory' in performance) {
  // メモリ使用量監視
  setInterval(async () => {
    try {
      const memory = await (performance as any).measureUserAgentSpecificMemory();
      if (memory.bytes > 100 * 1024 * 1024) { // 100MB超過
        console.warn('High memory usage detected:', memory.bytes / 1024 / 1024, 'MB');
      }
    } catch (error) {
      // measureUserAgentSpecificMemory が利用できない場合は無視
    }
  }, 30000); // 30秒間隔
}

// エラーハンドリング
window.addEventListener('error', (event) => {
  console.error('Global error:', event.error);
  if (window.yesManAPI?.log?.error) {
    window.yesManAPI.log.error('Global error caught', {
      message: event.error?.message,
      stack: event.error?.stack,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno
    });
  }
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason);
  if (window.yesManAPI?.log?.error) {
    window.yesManAPI.log.error('Unhandled promise rejection', {
      reason: event.reason?.toString(),
      stack: event.reason?.stack
    });
  }
});

console.log('Yes-Man Face UI initialization complete');