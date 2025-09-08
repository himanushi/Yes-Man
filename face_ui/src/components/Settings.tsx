/**
 * Yes-Man 設定画面コンポーネント
 * 
 * システム設定とカスタマイズ機能
 * 憲法II: シンプルで直感的なインターフェース
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSystemStore } from '../store/systemStore';
import { AppSettings, LogLevel } from '../types';
import './Settings.css';

interface SettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

const Settings: React.FC<SettingsProps> = ({ isOpen, onClose }) => {
  const { settings, updateSettings, systemStatus, addLog } = useSystemStore();
  
  // ローカル設定状態（保存前の編集用）
  const [localSettings, setLocalSettings] = useState<AppSettings>({ ...settings });
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [activeTab, setActiveTab] = useState<'face' | 'audio' | 'system' | 'advanced'>('face');

  // 設定変更検知
  useEffect(() => {
    const hasChanges = JSON.stringify(localSettings) !== JSON.stringify(settings);
    setHasUnsavedChanges(hasChanges);
  }, [localSettings, settings]);

  // 設定をリセット
  const resetToDefaults = () => {
    const defaultSettings: AppSettings = {
      faceSize: 300,
      animationSpeed: 1.0,
      enableBlinking: true,
      enableGlow: true,
      alwaysOnTop: false,
      transparency: 0.95,
      position: { x: 50, y: 50 },
      wakeWordEnabled: true,
      wakeWordKeyword: 'Yes-Man',
      wakeWordThreshold: 0.8,
      ttsEnabled: true,
      ttsSpeakerId: 1,
      ttsSpeed: 1.0,
      ttsVolume: 0.8,
      debugMode: false,
      logLevel: 'info',
      autoStart: false
    };
    
    setLocalSettings(defaultSettings);
    addLog({
      level: 'info',
      message: 'Settings reset to defaults',
      timestamp: new Date().toISOString(),
      source: 'Settings'
    });
  };

  // 設定保存
  const saveSettings = () => {
    updateSettings(localSettings);
    setHasUnsavedChanges(false);
    
    addLog({
      level: 'info',
      message: 'Settings saved successfully',
      timestamp: new Date().toISOString(),
      source: 'Settings'
    });
  };

  // 設定キャンセル
  const cancelChanges = () => {
    setLocalSettings({ ...settings });
    setHasUnsavedChanges(false);
  };

  // 設定値更新ヘルパー
  const updateLocalSetting = <K extends keyof AppSettings>(
    key: K, 
    value: AppSettings[K]
  ) => {
    setLocalSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  // 顔表示設定タブ
  const renderFaceTab = () => (
    <div className="settings-tab-content">
      <div className="setting-group">
        <h3>顔表示設定</h3>
        
        <div className="setting-item">
          <label>顔サイズ</label>
          <div className="range-input">
            <input
              type="range"
              min="150"
              max="500"
              value={localSettings.faceSize}
              onChange={(e) => updateLocalSetting('faceSize', parseInt(e.target.value))}
            />
            <span className="range-value">{localSettings.faceSize}px</span>
          </div>
        </div>

        <div className="setting-item">
          <label>アニメーション速度</label>
          <div className="range-input">
            <input
              type="range"
              min="0.1"
              max="3.0"
              step="0.1"
              value={localSettings.animationSpeed}
              onChange={(e) => updateLocalSetting('animationSpeed', parseFloat(e.target.value))}
            />
            <span className="range-value">{localSettings.animationSpeed.toFixed(1)}x</span>
          </div>
        </div>

        <div className="setting-item checkbox">
          <label>
            <input
              type="checkbox"
              checked={localSettings.enableBlinking}
              onChange={(e) => updateLocalSetting('enableBlinking', e.target.checked)}
            />
            <span className="checkmark"></span>
            瞬きアニメーション
          </label>
        </div>

        <div className="setting-item checkbox">
          <label>
            <input
              type="checkbox"
              checked={localSettings.enableGlow}
              onChange={(e) => updateLocalSetting('enableGlow', e.target.checked)}
            />
            <span className="checkmark"></span>
            光エフェクト
          </label>
        </div>
      </div>

      <div className="setting-group">
        <h3>ウィンドウ設定</h3>
        
        <div className="setting-item checkbox">
          <label>
            <input
              type="checkbox"
              checked={localSettings.alwaysOnTop}
              onChange={(e) => updateLocalSetting('alwaysOnTop', e.target.checked)}
            />
            <span className="checkmark"></span>
            常に最前面
          </label>
        </div>

        <div className="setting-item">
          <label>透明度</label>
          <div className="range-input">
            <input
              type="range"
              min="0.3"
              max="1.0"
              step="0.05"
              value={localSettings.transparency}
              onChange={(e) => updateLocalSetting('transparency', parseFloat(e.target.value))}
            />
            <span className="range-value">{Math.round(localSettings.transparency * 100)}%</span>
          </div>
        </div>
      </div>
    </div>
  );

  // 音声設定タブ
  const renderAudioTab = () => (
    <div className="settings-tab-content">
      <div className="setting-group">
        <h3>ウェイクワード設定</h3>
        
        <div className="setting-item checkbox">
          <label>
            <input
              type="checkbox"
              checked={localSettings.wakeWordEnabled}
              onChange={(e) => updateLocalSetting('wakeWordEnabled', e.target.checked)}
            />
            <span className="checkmark"></span>
            ウェイクワード有効
          </label>
        </div>

        <div className="setting-item">
          <label>ウェイクワード</label>
          <input
            type="text"
            value={localSettings.wakeWordKeyword}
            onChange={(e) => updateLocalSetting('wakeWordKeyword', e.target.value)}
            disabled={!localSettings.wakeWordEnabled}
            className="text-input"
          />
        </div>

        <div className="setting-item">
          <label>検出閾値</label>
          <div className="range-input">
            <input
              type="range"
              min="0.3"
              max="1.0"
              step="0.05"
              value={localSettings.wakeWordThreshold}
              onChange={(e) => updateLocalSetting('wakeWordThreshold', parseFloat(e.target.value))}
              disabled={!localSettings.wakeWordEnabled}
            />
            <span className="range-value">{localSettings.wakeWordThreshold.toFixed(2)}</span>
          </div>
        </div>
      </div>

      <div className="setting-group">
        <h3>音声合成設定</h3>
        
        <div className="setting-item checkbox">
          <label>
            <input
              type="checkbox"
              checked={localSettings.ttsEnabled}
              onChange={(e) => updateLocalSetting('ttsEnabled', e.target.checked)}
            />
            <span className="checkmark"></span>
            TTS有効
          </label>
        </div>

        <div className="setting-item">
          <label>スピーカー</label>
          <select
            value={localSettings.ttsSpeakerId}
            onChange={(e) => updateLocalSetting('ttsSpeakerId', parseInt(e.target.value))}
            disabled={!localSettings.ttsEnabled}
            className="select-input"
          >
            <option value={1}>四国めたん (ノーマル)</option>
            <option value={2}>ずんだもん (ノーマル)</option>
            <option value={3}>春日部つむぎ (ノーマル)</option>
            <option value={8}>春日部つむぎ (おしとやか)</option>
            <option value={20}>WhiteCUL (ノーマル)</option>
          </select>
        </div>

        <div className="setting-item">
          <label>再生速度</label>
          <div className="range-input">
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={localSettings.ttsSpeed}
              onChange={(e) => updateLocalSetting('ttsSpeed', parseFloat(e.target.value))}
              disabled={!localSettings.ttsEnabled}
            />
            <span className="range-value">{localSettings.ttsSpeed.toFixed(1)}x</span>
          </div>
        </div>

        <div className="setting-item">
          <label>音量</label>
          <div className="range-input">
            <input
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              value={localSettings.ttsVolume}
              onChange={(e) => updateLocalSetting('ttsVolume', parseFloat(e.target.value))}
              disabled={!localSettings.ttsEnabled}
            />
            <span className="range-value">{Math.round(localSettings.ttsVolume * 100)}%</span>
          </div>
        </div>
      </div>
    </div>
  );

  // システム設定タブ
  const renderSystemTab = () => (
    <div className="settings-tab-content">
      <div className="setting-group">
        <h3>システム設定</h3>
        
        <div className="setting-item checkbox">
          <label>
            <input
              type="checkbox"
              checked={localSettings.autoStart}
              onChange={(e) => updateLocalSetting('autoStart', e.target.checked)}
            />
            <span className="checkmark"></span>
            自動起動
          </label>
        </div>

        <div className="setting-item">
          <label>ログレベル</label>
          <select
            value={localSettings.logLevel}
            onChange={(e) => updateLocalSetting('logLevel', e.target.value as LogLevel)}
            className="select-input"
          >
            <option value="debug">DEBUG</option>
            <option value="info">INFO</option>
            <option value="warn">WARN</option>
            <option value="error">ERROR</option>
          </select>
        </div>
      </div>

      <div className="setting-group">
        <h3>接続状態</h3>
        <div className="connection-status-grid">
          <div className={`status-card ${systemStatus?.pythonLayerConnected ? 'connected' : 'disconnected'}`}>
            <div className="status-indicator"></div>
            <div className="status-info">
              <span className="status-name">Python Layer</span>
              <span className="status-text">
                {systemStatus?.pythonLayerConnected ? '接続済み' : '未接続'}
              </span>
            </div>
          </div>
          
          <div className={`status-card ${systemStatus?.voicevoxConnected ? 'connected' : 'disconnected'}`}>
            <div className="status-indicator"></div>
            <div className="status-info">
              <span className="status-name">VoiceVox</span>
              <span className="status-text">
                {systemStatus?.voicevoxConnected ? '接続済み' : '未接続'}
              </span>
            </div>
          </div>
          
          <div className={`status-card ${systemStatus?.langflowConnected ? 'connected' : 'disconnected'}`}>
            <div className="status-indicator"></div>
            <div className="status-info">
              <span className="status-name">LangFlow</span>
              <span className="status-text">
                {systemStatus?.langflowConnected ? '接続済み' : '未接続'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // 詳細設定タブ
  const renderAdvancedTab = () => (
    <div className="settings-tab-content">
      <div className="setting-group">
        <h3>開発者設定</h3>
        
        <div className="setting-item checkbox">
          <label>
            <input
              type="checkbox"
              checked={localSettings.debugMode}
              onChange={(e) => updateLocalSetting('debugMode', e.target.checked)}
            />
            <span className="checkmark"></span>
            デバッグモード
          </label>
        </div>

        <div className="setting-group">
          <h3>システム情報</h3>
          <div className="system-info">
            <div className="info-item">
              <span className="info-label">バージョン:</span>
              <span className="info-value">1.0.0</span>
            </div>
            {window.electronDebug && (
              <>
                <div className="info-item">
                  <span className="info-label">Electron:</span>
                  <span className="info-value">{window.electronDebug.versions.electron}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Node:</span>
                  <span className="info-value">{window.electronDebug.versions.node}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">プラットフォーム:</span>
                  <span className="info-value">{window.electronDebug.platform}</span>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="setting-group">
          <h3>危険な操作</h3>
          <button 
            className="danger-button"
            onClick={resetToDefaults}
          >
            設定をリセット
          </button>
        </div>
      </div>
    </div>
  );

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="settings-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="settings-modal"
          initial={{ opacity: 0, scale: 0.9, y: 50 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 50 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* ヘッダー */}
          <div className="settings-header">
            <h2>Yes-Man 設定</h2>
            <button className="close-button" onClick={onClose}>
              ✕
            </button>
          </div>

          {/* タブナビゲーション */}
          <div className="settings-tabs">
            <button
              className={`tab-button ${activeTab === 'face' ? 'active' : ''}`}
              onClick={() => setActiveTab('face')}
            >
              🎭 顔表示
            </button>
            <button
              className={`tab-button ${activeTab === 'audio' ? 'active' : ''}`}
              onClick={() => setActiveTab('audio')}
            >
              🎤 音声
            </button>
            <button
              className={`tab-button ${activeTab === 'system' ? 'active' : ''}`}
              onClick={() => setActiveTab('system')}
            >
              ⚙️ システム
            </button>
            <button
              className={`tab-button ${activeTab === 'advanced' ? 'active' : ''}`}
              onClick={() => setActiveTab('advanced')}
            >
              🔧 詳細
            </button>
          </div>

          {/* タブコンテンツ */}
          <div className="settings-content">
            {activeTab === 'face' && renderFaceTab()}
            {activeTab === 'audio' && renderAudioTab()}
            {activeTab === 'system' && renderSystemTab()}
            {activeTab === 'advanced' && renderAdvancedTab()}
          </div>

          {/* フッター */}
          <div className="settings-footer">
            <div className="unsaved-indicator">
              {hasUnsavedChanges && (
                <span className="unsaved-text">未保存の変更があります</span>
              )}
            </div>
            <div className="footer-buttons">
              <button 
                className="secondary-button"
                onClick={cancelChanges}
                disabled={!hasUnsavedChanges}
              >
                キャンセル
              </button>
              <button 
                className="primary-button"
                onClick={saveSettings}
                disabled={!hasUnsavedChanges}
              >
                保存
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default Settings;