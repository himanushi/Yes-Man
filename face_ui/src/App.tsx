/**
 * Yes-Man 顔UI メインアプリケーション
 * 
 * Fallout New Vegas風の音声アシスタントUI
 * 憲法II: シンプルで直感的なインターフェース
 */

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import FaceAnimation from './components/FaceAnimation';
import { useSystemStore, initializeSystemStore, cleanupSystemStore } from './store/systemStore';
import './App.css';

const App: React.FC = () => {
  // システム状態管理
  const {
    faceState,
    expression,
    animationState,
    systemStatus,
    settings,
    logs,
    setFaceState,
    addLog
  } = useSystemStore();

  // ローカル状態
  const [showDebug, setShowDebug] = useState(settings.debugMode);
  const [showLogs, setShowLogs] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  // 初期化処理
  useEffect(() => {
    const initialize = async () => {
      try {
        addLog({
          level: 'info',
          message: 'Yes-Man Face UI starting...',
          timestamp: new Date().toISOString(),
          source: 'App'
        });

        // システムストア初期化
        initializeSystemStore();

        // システム状態取得
        if (window.yesManAPI) {
          try {
            const status = await window.yesManAPI.system.getStatus();
            useSystemStore.getState().updateSystemStatus(status);
          } catch (error) {
            addLog({
              level: 'warn',
              message: 'Failed to get initial system status',
              timestamp: new Date().toISOString(),
              source: 'App',
              data: error
            });
          }
        }

        setIsInitialized(true);

        addLog({
          level: 'info',
          message: 'Yes-Man Face UI initialized successfully',
          timestamp: new Date().toISOString(),
          source: 'App'
        });

      } catch (error) {
        addLog({
          level: 'error',
          message: 'Failed to initialize Yes-Man Face UI',
          timestamp: new Date().toISOString(),
          source: 'App',
          data: error
        });

        setFaceState('error');
      }
    };

    initialize();

    // クリーンアップ
    return () => {
      cleanupSystemStore();
    };
  }, [addLog, setFaceState]);

  // デバッグモード切り替え
  useEffect(() => {
    setShowDebug(settings.debugMode);
  }, [settings.debugMode]);

  // キーボードショートカット
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      // Ctrl+D: デバッグ表示切り替え
      if (event.ctrlKey && event.key === 'd') {
        event.preventDefault();
        setShowDebug(!showDebug);
      }
      
      // Ctrl+L: ログ表示切り替え
      if (event.ctrlKey && event.key === 'l') {
        event.preventDefault();
        setShowLogs(!showLogs);
      }
      
      // Ctrl+R: 状態リセット
      if (event.ctrlKey && event.key === 'r') {
        event.preventDefault();
        setFaceState('idle');
        useSystemStore.getState().setExpression('neutral');
      }
      
      // Escape: ログ/デバッグ画面を閉じる
      if (event.key === 'Escape') {
        setShowLogs(false);
        setShowDebug(false);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [showDebug, showLogs, setFaceState]);

  // 顔状態変更ハンドラー
  const handleFaceStateChange = (newState: any) => {
    addLog({
      level: 'debug',
      message: `Face state changed via component: ${newState}`,
      timestamp: new Date().toISOString(),
      source: 'FaceAnimation'
    });
  };

  // ログをレベル別にフィルタリング
  const getFilteredLogs = (level?: string) => {
    if (!level) return logs;
    return logs.filter(log => log.level === level);
  };

  // 接続状態インジケータ
  const renderConnectionStatus = () => (
    <div className="connection-status">
      <div className={`status-indicator ${systemStatus?.pythonLayerConnected ? 'connected' : 'disconnected'}`}>
        <span className="indicator-dot"></span>
        <span className="indicator-label">Python Layer</span>
      </div>
      {systemStatus?.voicevoxConnected !== undefined && (
        <div className={`status-indicator ${systemStatus.voicevoxConnected ? 'connected' : 'disconnected'}`}>
          <span className="indicator-dot"></span>
          <span className="indicator-label">VoiceVox</span>
        </div>
      )}
      {systemStatus?.langflowConnected !== undefined && (
        <div className={`status-indicator ${systemStatus.langflowConnected ? 'connected' : 'disconnected'}`}>
          <span className="indicator-dot"></span>
          <span className="indicator-label">LangFlow</span>
        </div>
      )}
    </div>
  );

  // ログビュー
  const renderLogs = () => (
    <motion.div
      className="logs-container"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
    >
      <div className="logs-header">
        <h3>System Logs</h3>
        <button 
          className="close-button"
          onClick={() => setShowLogs(false)}
        >
          ×
        </button>
      </div>
      
      <div className="logs-filter">
        <button 
          className={`filter-button ${!showDebug ? 'active' : ''}`}
          onClick={() => setShowDebug(false)}
        >
          All
        </button>
        <button 
          className={`filter-button error ${showDebug ? 'active' : ''}`}
          onClick={() => setShowDebug(true)}
        >
          Errors
        </button>
      </div>
      
      <div className="logs-content">
        {getFilteredLogs(showDebug ? 'error' : undefined)
          .slice(-50) // 最新50件
          .map((log, index) => (
            <div key={index} className={`log-entry log-${log.level}`}>
              <span className="log-time">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className="log-source">[{log.source}]</span>
              <span className="log-level">{log.level.toUpperCase()}</span>
              <span className="log-message">{log.message}</span>
            </div>
          ))}
      </div>
      
      <div className="logs-footer">
        <button onClick={() => useSystemStore.getState().clearLogs()}>
          Clear Logs
        </button>
        <span className="logs-count">
          {logs.length} entries
        </span>
      </div>
    </motion.div>
  );

  // デバッグ情報
  const renderDebugInfo = () => (
    <motion.div
      className="debug-info"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="debug-section">
        <h4>Face State</h4>
        <div>Current: {faceState}</div>
        <div>Expression: {expression}</div>
      </div>
      
      <div className="debug-section">
        <h4>Animation</h4>
        <div>Eye Blink Rate: {animationState.eyeBlinkRate.toFixed(2)}</div>
        <div>Eye Openness: {animationState.eyeOpenness.toFixed(2)}</div>
        <div>Mouth Movement: {animationState.mouthMovement.toFixed(2)}</div>
        <div>Glow Intensity: {animationState.glowIntensity.toFixed(2)}</div>
      </div>
      
      <div className="debug-section">
        <h4>System</h4>
        <div>Initialized: {isInitialized ? 'Yes' : 'No'}</div>
        <div>Debug Mode: {settings.debugMode ? 'On' : 'Off'}</div>
        <div>Log Level: {settings.logLevel}</div>
      </div>
    </motion.div>
  );

  // 初期化中画面
  if (!isInitialized) {
    return (
      <div className="app-loading">
        <motion.div
          className="loading-spinner"
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        >
          <div className="spinner-ring"></div>
        </motion.div>
        <motion.div
          className="loading-text"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          Initializing Yes-Man...
        </motion.div>
      </div>
    );
  }

  return (
    <div className={`app ${faceState}`}>
      {/* メインコンテンツ */}
      <div className="main-content">
        <FaceAnimation
          state={faceState}
          expression={expression}
          animationState={animationState}
          size={settings.faceSize}
          onStateChange={handleFaceStateChange}
          className="main-face"
        />
      </div>

      {/* 接続状態インジケータ */}
      <div className="status-bar">
        {renderConnectionStatus()}
      </div>

      {/* デバッグ情報 */}
      <AnimatePresence>
        {showDebug && renderDebugInfo()}
      </AnimatePresence>

      {/* ログビュー */}
      <AnimatePresence>
        {showLogs && renderLogs()}
      </AnimatePresence>

      {/* コントロールパネル */}
      <div className="control-panel">
        <button
          className="control-button debug"
          onClick={() => setShowDebug(!showDebug)}
          title="Toggle Debug (Ctrl+D)"
        >
          🔧
        </button>
        
        <button
          className="control-button logs"
          onClick={() => setShowLogs(!showLogs)}
          title="Show Logs (Ctrl+L)"
        >
          📋
        </button>
        
        <button
          className="control-button reset"
          onClick={() => setFaceState('idle')}
          title="Reset State (Ctrl+R)"
        >
          🔄
        </button>

        {window.yesManAPI && (
          <button
            className="control-button close"
            onClick={() => window.yesManAPI?.window.close()}
            title="Close Application"
          >
            ✕
          </button>
        )}
      </div>

      {/* バージョン情報（デバッグモード時のみ） */}
      {showDebug && (
        <div className="version-info">
          <div>Yes-Man Face UI v1.0.0</div>
          {window.electronDebug && (
            <div>
              <div>Electron: {window.electronDebug.versions.electron}</div>
              <div>Node: {window.electronDebug.versions.node}</div>
              <div>Platform: {window.electronDebug.platform}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default App;