"""
LangFlow起動スクリプト
Ctrl+Cで確実に停止できるように改良
"""

import signal
import sys
import subprocess
import os
from typing import Optional

class LangFlowManager:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
    
    def signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        print(f"\nReceived signal {signum}, shutting down LangFlow...")
        self.stop()
        sys.exit(0)
    
    def start(self, host: str = "127.0.0.1", port: int = 7860):
        """LangFlow開始"""
        # シグナルハンドラー設定
        signal.signal(signal.SIGINT, self.signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            print(f"Starting LangFlow on {host}:{port}")
            
            # LangFlow起動
            cmd = [
                sys.executable, "-m", "langflow", "run",
                "--host", host,
                "--port", str(port),
                "--log-level", "info",
                "--no-open-browser"
            ]
            
            print(f"Executing command: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            self.is_running = True
            print(f"LangFlow started with PID: {self.process.pid}")
            print("Press Ctrl+C to stop")
            
            # ログ出力（stdout と stderr を両方監視）
            import threading
            
            def read_stdout():
                try:
                    for line in self.process.stdout:
                        print(f"[STDOUT] {line.strip()}")
                        if "Open Langflow" in line:
                            print(f"\n✅ LangFlow is ready at http://{host}:{port}\n")
                except Exception as e:
                    print(f"Error reading stdout: {e}")
            
            def read_stderr():
                try:
                    for line in self.process.stderr:
                        print(f"[STDERR] {line.strip()}")
                except Exception as e:
                    print(f"Error reading stderr: {e}")
            
            # 別スレッドでstdout/stderrを読み取り
            stdout_thread = threading.Thread(target=read_stdout, daemon=True)
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            
            stdout_thread.start()
            stderr_thread.start()
            
            try:
                # プロセスの終了を待機
                self.process.wait()
            except KeyboardInterrupt:
                print("\nKeyboard interrupt received...")
                self.stop()
            
        except Exception as e:
            print(f"Failed to start LangFlow: {e}")
            self.stop()
    
    def stop(self):
        """LangFlow停止"""
        if self.process and self.is_running:
            print("Stopping LangFlow...")
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
                print("LangFlow stopped successfully")
            except subprocess.TimeoutExpired:
                print("Force killing LangFlow...")
                self.process.kill()
                self.process.wait()
            except Exception as e:
                print(f"Error stopping LangFlow: {e}")
            finally:
                self.is_running = False
                self.process = None

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Start LangFlow with proper Ctrl+C handling")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=7860, help="Port to bind to")
    
    args = parser.parse_args()
    
    manager = LangFlowManager()
    
    try:
        manager.start(args.host, args.port)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        manager.stop()

if __name__ == "__main__":
    main()