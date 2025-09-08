/**
 * Electron Preload Script
 * 
 * レンダラープロセスとメインプロセス間の安全なAPI橋渡し
 * 憲法IV: セキュリティファースト - contextIsolation使用
 */

const { contextBridge, ipcRenderer } = require('electron');

// Yes-Man固有のAPI定義
const yesManAPI = {
  // 顔状態管理
  face: {
    setState: (state) => ipcRenderer.invoke('set-face-state', state),
    onStateChange: (callback) => {
      ipcRenderer.on('face-state-update', (event, data) => callback(data));
    },
    removeStateListener: () => {
      ipcRenderer.removeAllListeners('face-state-update');
    }
  },

  // システム制御
  system: {
    getStatus: () => ipcRenderer.invoke('get-system-status'),
    startPythonLayer: () => ipcRenderer.invoke('start-python-layer'),
    stopPythonLayer: () => ipcRenderer.invoke('stop-python-layer'),
    quit: () => ipcRenderer.invoke('quit-app'),
    
    onPythonLayerStatus: (callback) => {
      ipcRenderer.on('python-layer-status', (event, data) => callback(data));
    },
    
    onPythonLog: (callback) => {
      ipcRenderer.on('python-log', (event, data) => callback(data));
    },
    
    removeSystemListeners: () => {
      ipcRenderer.removeAllListeners('python-layer-status');
      ipcRenderer.removeAllListeners('python-log');
    }
  },

  // ウィンドウ制御
  window: {
    minimize: () => ipcRenderer.invoke('minimize-window'),
    maximize: () => ipcRenderer.invoke('maximize-window'),
    close: () => ipcRenderer.invoke('quit-app')
  },

  // ログ送信
  log: {
    info: (message, data) => ipcRenderer.invoke('log-message', 'info', message, data),
    warn: (message, data) => ipcRenderer.invoke('log-message', 'warn', message, data),
    error: (message, data) => ipcRenderer.invoke('log-message', 'error', message, data),
    debug: (message, data) => ipcRenderer.invoke('log-message', 'debug', message, data)
  },

  // 設定管理
  settings: {
    get: (key) => ipcRenderer.invoke('get-setting', key),
    set: (key, value) => ipcRenderer.invoke('set-setting', key, value),
    getAll: () => ipcRenderer.invoke('get-all-settings'),
    
    onSettingChange: (callback) => {
      ipcRenderer.on('setting-changed', (event, data) => callback(data));
    },
    
    removeSettingListener: () => {
      ipcRenderer.removeAllListeners('setting-changed');
    }
  },

  // 音声関連イベント
  audio: {
    onWakeWordDetected: (callback) => {
      ipcRenderer.on('wake-word-detected', (event, data) => callback(data));
    },
    
    onUserSpeechStart: (callback) => {
      ipcRenderer.on('user-speech-start', (event, data) => callback(data));
    },
    
    onUserSpeechEnd: (callback) => {
      ipcRenderer.on('user-speech-end', (event, data) => callback(data));
    },
    
    onAgentResponse: (callback) => {
      ipcRenderer.on('agent-response', (event, data) => callback(data));
    },
    
    onTTSStart: (callback) => {
      ipcRenderer.on('tts-start', (event, data) => callback(data));
    },
    
    onTTSEnd: (callback) => {
      ipcRenderer.on('tts-end', (event, data) => callback(data));
    },
    
    removeAudioListeners: () => {
      ipcRenderer.removeAllListeners('wake-word-detected');
      ipcRenderer.removeAllListeners('user-speech-start');
      ipcRenderer.removeAllListeners('user-speech-end');
      ipcRenderer.removeAllListeners('agent-response');
      ipcRenderer.removeAllListeners('tts-start');
      ipcRenderer.removeAllListeners('tts-end');
    }
  },

  // ユーティリティ
  utils: {
    getVersion: () => ipcRenderer.invoke('get-app-version'),
    getPlatform: () => process.platform,
    getNodeVersion: () => process.versions.node,
    getElectronVersion: () => process.versions.electron
  }
};

// APIをレンダラープロセスに公開
contextBridge.exposeInMainWorld('yesManAPI', yesManAPI);

// 開発時のデバッグ情報
if (process.env.NODE_ENV === 'development') {
  contextBridge.exposeInMainWorld('electronDebug', {
    versions: process.versions,
    platform: process.platform,
    arch: process.arch
  });
}

console.log('Yes-Man preload script loaded successfully');