/**
 * Electron Main Process
 * 
 * Yes-Man顔UIのメインプロセス
 * 憲法II: シンプルなElectronアーキテクチャ
 */

const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');
const isDev = require('electron-is-dev');
const { spawn } = require('child_process');

class YesManElectronApp {
  constructor() {
    this.mainWindow = null;
    this.pythonProcess = null;
    this.isQuitting = false;
    
    // IPC通信設定
    this.setupIPCHandlers();
  }

  /**
   * メインウィンドウ作成
   */
  createWindow() {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;
    
    // ウィンドウサイズ設定（顔表示用）
    const windowWidth = 400;
    const windowHeight = 500;
    
    this.mainWindow = new BrowserWindow({
      width: windowWidth,
      height: windowHeight,
      x: width - windowWidth - 50, // 右端に配置
      y: 50, // 上部に配置
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        enableRemoteModule: false,
        preload: path.join(__dirname, 'preload.js')
      },
      frame: true, // フレーム表示
      resizable: true,
      minimizable: true,
      maximizable: false,
      alwaysOnTop: false, // 常に最前面は無効
      backgroundColor: '#1a1a1a',
      title: 'Yes-Man Voice Assistant',
      icon: path.join(__dirname, 'assets', 'icon.png'), // アイコン設定
      show: false // 初期は非表示
    });

    // React開発サーバーまたはビルド済みファイル読み込み
    const startUrl = isDev 
      ? 'http://localhost:3000' 
      : `file://${path.join(__dirname, '../build/index.html')}`;
    
    this.mainWindow.loadURL(startUrl);

    // ウィンドウ準備完了後に表示
    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow.show();
      
      // 開発時はDevToolsを開く
      if (isDev) {
        this.mainWindow.webContents.openDevTools();
      }
    });

    // ウィンドウ閉じる時の処理
    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
    });

    // ウィンドウ最小化時の処理
    this.mainWindow.on('minimize', () => {
      console.log('Window minimized');
    });

    // ウィンドウ復元時の処理
    this.mainWindow.on('restore', () => {
      console.log('Window restored');
    });
  }

  /**
   * IPC通信ハンドラー設定
   */
  setupIPCHandlers() {
    // 顔状態変更
    ipcMain.handle('set-face-state', async (event, state) => {
      console.log('Face state changed:', state);
      // Python音声レイヤーに状態通知
      this.notifyPythonLayer('face_state_changed', { state });
      return { success: true };
    });

    // システム状態取得
    ipcMain.handle('get-system-status', async () => {
      return {
        pythonLayerConnected: this.pythonProcess !== null,
        timestamp: new Date().toISOString()
      };
    });

    // Python音声レイヤー開始
    ipcMain.handle('start-python-layer', async () => {
      return await this.startPythonLayer();
    });

    // Python音声レイヤー停止
    ipcMain.handle('stop-python-layer', async () => {
      return await this.stopPythonLayer();
    });

    // アプリ終了
    ipcMain.handle('quit-app', async () => {
      this.isQuitting = true;
      await this.cleanup();
      app.quit();
    });

    // ウィンドウ制御
    ipcMain.handle('minimize-window', async () => {
      if (this.mainWindow) {
        this.mainWindow.minimize();
      }
    });

    ipcMain.handle('maximize-window', async () => {
      if (this.mainWindow) {
        if (this.mainWindow.isMaximized()) {
          this.mainWindow.unmaximize();
        } else {
          this.mainWindow.maximize();
        }
      }
    });

    // ログメッセージ受信
    ipcMain.handle('log-message', async (event, level, message, data) => {
      console.log(`[${level.toUpperCase()}] ${message}`, data || '');
    });
  }

  /**
   * Python音声レイヤー開始
   */
  async startPythonLayer() {
    if (this.pythonProcess) {
      console.log('Python layer already running');
      return { success: true, message: 'Already running' };
    }

    try {
      console.log('Starting Python audio layer...');
      
      // uv run yes-man コマンドでPython音声レイヤー起動
      const pythonCmd = 'uv';
      const pythonArgs = ['run', 'yes-man'];
      
      this.pythonProcess = spawn(pythonCmd, pythonArgs, {
        cwd: path.join(__dirname, '../../'), // プロジェクトルートディレクトリ
        stdio: ['pipe', 'pipe', 'pipe']
      });

      // 標準出力ログ
      this.pythonProcess.stdout.on('data', (data) => {
        const message = data.toString().trim();
        console.log('[Python Layer]', message);
        
        // UIに音声レイヤーログ送信
        if (this.mainWindow) {
          this.mainWindow.webContents.send('python-log', {
            level: 'info',
            message: message,
            timestamp: new Date().toISOString()
          });
        }
      });

      // 標準エラーログ
      this.pythonProcess.stderr.on('data', (data) => {
        const message = data.toString().trim();
        console.error('[Python Layer Error]', message);
        
        if (this.mainWindow) {
          this.mainWindow.webContents.send('python-log', {
            level: 'error',
            message: message,
            timestamp: new Date().toISOString()
          });
        }
      });

      // プロセス終了処理
      this.pythonProcess.on('close', (code) => {
        console.log(`Python layer exited with code ${code}`);
        this.pythonProcess = null;
        
        if (this.mainWindow && !this.isQuitting) {
          this.mainWindow.webContents.send('python-layer-status', {
            connected: false,
            exitCode: code
          });
        }
      });

      // プロセスエラー処理
      this.pythonProcess.on('error', (error) => {
        console.error('Failed to start Python layer:', error);
        this.pythonProcess = null;
        
        if (this.mainWindow) {
          this.mainWindow.webContents.send('python-layer-status', {
            connected: false,
            error: error.message
          });
        }
      });

      // 起動成功通知
      setTimeout(() => {
        if (this.mainWindow) {
          this.mainWindow.webContents.send('python-layer-status', {
            connected: true
          });
        }
      }, 2000);

      return { 
        success: true, 
        message: 'Python layer started successfully' 
      };

    } catch (error) {
      console.error('Failed to start Python layer:', error);
      return { 
        success: false, 
        message: error.message 
      };
    }
  }

  /**
   * Python音声レイヤー停止
   */
  async stopPythonLayer() {
    if (!this.pythonProcess) {
      return { success: true, message: 'Not running' };
    }

    try {
      console.log('Stopping Python audio layer...');
      
      // GracefulにプロセスVIEW
      this.pythonProcess.kill('SIGTERM');
      
      // 5秒後に強制終了
      setTimeout(() => {
        if (this.pythonProcess) {
          console.log('Force killing Python process...');
          this.pythonProcess.kill('SIGKILL');
        }
      }, 5000);

      this.pythonProcess = null;

      if (this.mainWindow) {
        this.mainWindow.webContents.send('python-layer-status', {
          connected: false
        });
      }

      return { 
        success: true, 
        message: 'Python layer stopped' 
      };

    } catch (error) {
      console.error('Failed to stop Python layer:', error);
      return { 
        success: false, 
        message: error.message 
      };
    }
  }

  /**
   * Python音声レイヤーに通知送信
   */
  notifyPythonLayer(event, data) {
    // TODO: IPCまたはHTTP APIでPython側に通知
    // 現在は標準入力経由で通知（簡易実装）
    if (this.pythonProcess && this.pythonProcess.stdin) {
      try {
        const message = JSON.stringify({ event, data }) + '\n';
        this.pythonProcess.stdin.write(message);
      } catch (error) {
        console.error('Failed to notify Python layer:', error);
      }
    }
  }

  /**
   * アプリケーション初期化
   */
  async initialize() {
    // アプリ準備完了時
    app.whenReady().then(() => {
      this.createWindow();

      // macOS: Dockクリック時の処理
      app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
          this.createWindow();
        }
      });
    });

    // 全ウィンドウ閉じた時の処理
    app.on('window-all-closed', () => {
      // macOS以外では終了
      if (process.platform !== 'darwin') {
        app.quit();
      }
    });

    // アプリ終了前処理
    app.on('before-quit', (event) => {
      if (!this.isQuitting) {
        event.preventDefault();
        this.cleanup().then(() => {
          this.isQuitting = true;
          app.quit();
        });
      }
    });
  }

  /**
   * クリーンアップ処理
   */
  async cleanup() {
    console.log('Cleaning up application...');
    
    // Python音声レイヤー停止
    if (this.pythonProcess) {
      await this.stopPythonLayer();
    }
    
    // ウィンドウ閉じる
    if (this.mainWindow) {
      this.mainWindow.close();
    }
  }
}

// アプリケーション起動
const yesManApp = new YesManElectronApp();
yesManApp.initialize().catch(console.error);

module.exports = yesManApp;