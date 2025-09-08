"""
マイク入力管理
"""

import pyaudio
import numpy as np
import threading
import logging
from typing import Optional, Callable
from dataclasses import dataclass

@dataclass
class MicrophoneConfig:
    """マイク設定"""
    sample_rate: int = 16000
    chunk_size: int = 1024
    channels: int = 1
    format: int = pyaudio.paFloat32
    device_index: Optional[int] = None

class MicrophoneInput:
    """マイク入力クラス"""
    
    def __init__(self, config: Optional[MicrophoneConfig] = None):
        self.config = config or MicrophoneConfig()
        self.logger = logging.getLogger(__name__)
        self.pyaudio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.callback: Optional[Callable[[np.ndarray], None]] = None
        self._is_recording = False
        self._recording_thread: Optional[threading.Thread] = None
        
    def start_recording(self, callback: Callable[[np.ndarray], None]) -> bool:
        """
        録音開始
        
        Args:
            callback: 音声データを受け取るコールバック関数
            
        Returns:
            bool: 開始成功
        """
        if self._is_recording:
            self.logger.warning("Already recording")
            return False
            
        try:
            self.callback = callback
            
            # ストリーム開設
            self.stream = self.pyaudio.open(
                format=self.config.format,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=self.config.device_index,
                frames_per_buffer=self.config.chunk_size
            )
            
            # 録音スレッド開始
            self._is_recording = True
            self._recording_thread = threading.Thread(
                target=self._recording_loop,
                daemon=True
            )
            self._recording_thread.start()
            
            self.logger.info("Microphone recording started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            return False
    
    def _recording_loop(self):
        """録音ループ"""
        while self._is_recording:
            try:
                # マイクから音声データ読み取り
                data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
                
                # numpy配列に変換
                audio_array = np.frombuffer(data, dtype=np.float32)
                
                # コールバック呼び出し
                if self.callback:
                    self.callback(audio_array)
                    
            except Exception as e:
                self.logger.error(f"Recording error: {e}")
                
    def stop_recording(self):
        """録音停止"""
        self._is_recording = False
        
        if self._recording_thread:
            self._recording_thread.join(timeout=1.0)
            
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        self.logger.info("Microphone recording stopped")
        
    def cleanup(self):
        """クリーンアップ"""
        self.stop_recording()
        self.pyaudio.terminate()
        
    def list_devices(self):
        """利用可能なオーディオデバイス一覧"""
        info = self.pyaudio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        devices = []
        for i in range(num_devices):
            device_info = self.pyaudio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                devices.append({
                    'index': i,
                    'name': device_info.get('name'),
                    'channels': device_info.get('maxInputChannels')
                })
                
        return devices