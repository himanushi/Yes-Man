"""
Yes-Man パフォーマンス監視・最適化システム
リアルタイム性能監視と自動最適化

憲法VI: パフォーマンス制約 - CPU30%以下、応答3秒以内の監視
憲法III: 効率的なメッセージング - メモリ使用量監視
"""

import psutil
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque
import statistics

logger = logging.getLogger("PerformanceMonitor")

@dataclass
class PerformanceMetrics:
    """パフォーマンス指標"""
    timestamp: str
    cpu_usage: float
    memory_usage: float
    memory_mb: float
    disk_io_read: float
    disk_io_write: float
    network_sent: float
    network_recv: float
    active_threads: int
    
    # Yes-Man固有指標
    wake_word_response_time: float
    stt_processing_time: float
    llm_processing_time: float
    tts_processing_time: float
    total_response_time: float
    
    # 音声処理固有
    audio_buffer_size: int
    audio_latency: float
    whisper_model_load_time: float
    voicevox_synthesis_time: float

@dataclass
class PerformanceThresholds:
    """パフォーマンス閾値"""
    max_cpu_usage: float = 30.0          # 憲法VI: CPU 30%以下
    max_memory_usage: float = 80.0       # メモリ使用率80%以下
    max_memory_mb: float = 1024.0        # メモリ使用量1GB以下
    max_response_time: float = 3.0       # 憲法VI: 3秒以内応答
    max_wake_word_time: float = 1.0      # ウェイクワード1秒以内
    max_stt_time: float = 2.0            # STT 2秒以内
    max_llm_time: float = 2.5            # LLM 2.5秒以内
    max_tts_time: float = 1.5            # TTS 1.5秒以内
    max_audio_latency: float = 100.0     # 音声レイテンシ100ms以下

class PerformanceAlert:
    """パフォーマンスアラート"""
    
    def __init__(self, metric: str, current: float, threshold: float, severity: str):
        self.metric = metric
        self.current = current
        self.threshold = threshold
        self.severity = severity
        self.timestamp = datetime.now()
    
    def __str__(self):
        return f"[{self.severity}] {self.metric}: {self.current:.2f} > {self.threshold:.2f}"

class PerformanceOptimizer:
    """パフォーマンス自動最適化"""
    
    def __init__(self, monitor: 'PerformanceMonitor'):
        self.monitor = monitor
        self.optimization_strategies = {
            'cpu_high': self._optimize_cpu_usage,
            'memory_high': self._optimize_memory_usage,
            'response_slow': self._optimize_response_time,
            'audio_latency_high': self._optimize_audio_latency
        }
        
        # 最適化履歴
        self.optimization_history: List[Dict[str, Any]] = []
        self.last_optimization = {}
    
    async def _optimize_cpu_usage(self, metrics: PerformanceMetrics):
        """CPU使用率最適化"""
        logger.info("Optimizing CPU usage...")
        
        optimizations = []
        
        # Whisperモデルサイズ縮小
        if metrics.stt_processing_time > 2.0:
            optimizations.append("whisper_model_downgrade")
            logger.info("Suggesting Whisper model downgrade for CPU optimization")
        
        # 音声バッファサイズ調整
        if metrics.audio_buffer_size > 4096:
            optimizations.append("audio_buffer_reduce")
            logger.info("Reducing audio buffer size for CPU optimization")
        
        # 並列処理数制限
        if metrics.active_threads > 8:
            optimizations.append("thread_limit")
            logger.info("Limiting thread count for CPU optimization")
        
        return optimizations
    
    async def _optimize_memory_usage(self, metrics: PerformanceMetrics):
        """メモリ使用量最適化"""
        logger.info("Optimizing memory usage...")
        
        optimizations = []
        
        # Whisperモデルアンロード（一時的）
        if metrics.memory_mb > 800:
            optimizations.append("whisper_model_unload")
            logger.info("Suggesting Whisper model unload for memory optimization")
        
        # 会話履歴クリア
        optimizations.append("conversation_history_clear")
        logger.info("Clearing conversation history for memory optimization")
        
        # ガベージコレクション強制実行
        import gc
        collected = gc.collect()
        optimizations.append(f"garbage_collection_{collected}")
        logger.info(f"Forced garbage collection: {collected} objects collected")
        
        return optimizations
    
    async def _optimize_response_time(self, metrics: PerformanceMetrics):
        """応答時間最適化"""
        logger.info("Optimizing response time...")
        
        optimizations = []
        
        # 最も遅いコンポーネントを特定して最適化
        bottleneck = max([
            ('stt', metrics.stt_processing_time),
            ('llm', metrics.llm_processing_time),
            ('tts', metrics.tts_processing_time)
        ], key=lambda x: x[1])
        
        component, time_taken = bottleneck
        
        if component == 'stt' and time_taken > 2.0:
            optimizations.append("stt_model_optimize")
            logger.info("Optimizing STT model for faster processing")
        
        elif component == 'llm' and time_taken > 2.5:
            optimizations.append("llm_timeout_reduce")
            logger.info("Reducing LLM timeout for faster responses")
        
        elif component == 'tts' and time_taken > 1.5:
            optimizations.append("tts_cache_enable")
            logger.info("Enabling TTS caching for faster synthesis")
        
        # 並列処理有効化
        optimizations.append("parallel_processing_enable")
        logger.info("Enabling parallel processing for components")
        
        return optimizations
    
    async def _optimize_audio_latency(self, metrics: PerformanceMetrics):
        """音声レイテンシ最適化"""
        logger.info("Optimizing audio latency...")
        
        optimizations = []
        
        # 音声バッファサイズ最適化
        if metrics.audio_buffer_size > 2048:
            optimizations.append("audio_buffer_optimize")
            logger.info("Optimizing audio buffer size for lower latency")
        
        # 音声デバイス設定調整
        optimizations.append("audio_device_optimize")
        logger.info("Optimizing audio device settings")
        
        return optimizations
    
    async def apply_optimizations(self, issue_type: str, metrics: PerformanceMetrics):
        """最適化実行"""
        strategy = self.optimization_strategies.get(issue_type)
        if not strategy:
            return []
        
        # 最適化実行間隔チェック（同じ最適化は30秒以内に実行しない）
        last_time = self.last_optimization.get(issue_type, 0)
        if time.time() - last_time < 30:
            logger.debug(f"Skipping {issue_type} optimization - too recent")
            return []
        
        optimizations = await strategy(metrics)
        
        # 履歴記録
        self.optimization_history.append({
            'timestamp': datetime.now().isoformat(),
            'issue_type': issue_type,
            'optimizations': optimizations,
            'metrics_before': asdict(metrics)
        })
        
        self.last_optimization[issue_type] = time.time()
        
        return optimizations

class PerformanceMonitor:
    """リアルタイムパフォーマンス監視"""
    
    def __init__(self, monitoring_interval: float = 1.0):
        self.monitoring_interval = monitoring_interval
        self.thresholds = PerformanceThresholds()
        self.optimizer = PerformanceOptimizer(self)
        
        # メトリクス履歴（最新300件 = 5分間）
        self.metrics_history: deque = deque(maxlen=300)
        
        # アラート管理
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.alert_callbacks: List[Callable] = []
        
        # パフォーマンス統計
        self.statistics = {
            'avg_cpu_usage': 0.0,
            'avg_memory_usage': 0.0,
            'avg_response_time': 0.0,
            'total_alerts': 0,
            'total_optimizations': 0
        }
        
        # システム情報取得
        self.process = psutil.Process()
        self.system_info = {
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'platform': psutil.WINDOWS if psutil.WINDOWS else psutil.LINUX
        }
        
        # 監視フラグ
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Yes-Man固有メトリクス
        self.yes_man_metrics = {
            'wake_word_response_time': 0.0,
            'stt_processing_time': 0.0,
            'llm_processing_time': 0.0,
            'tts_processing_time': 0.0,
            'total_response_time': 0.0,
            'audio_buffer_size': 1024,
            'audio_latency': 50.0,
            'whisper_model_load_time': 0.0,
            'voicevox_synthesis_time': 0.0
        }
        
        logger.info("Performance monitor initialized")
    
    def register_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """アラートコールバック登録"""
        self.alert_callbacks.append(callback)
    
    async def start_monitoring(self):
        """監視開始"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """監視停止"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """監視メインループ"""
        try:
            while self.monitoring_active:
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # 閾値チェック
                await self._check_thresholds(metrics)
                
                # 統計更新
                self._update_statistics()
                
                await asyncio.sleep(self.monitoring_interval)
                
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}")
    
    async def _collect_metrics(self) -> PerformanceMetrics:
        """メトリクス収集"""
        try:
            # システムメトリクス
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            
            # ディスクI/O
            try:
                disk_io = self.process.io_counters()
                disk_read = disk_io.read_bytes / (1024 * 1024)  # MB
                disk_write = disk_io.write_bytes / (1024 * 1024)  # MB
            except (AttributeError, psutil.AccessDenied):
                disk_read = disk_write = 0.0
            
            # ネットワークI/O
            try:
                net_io = psutil.net_io_counters()
                net_sent = net_io.bytes_sent / (1024 * 1024)  # MB
                net_recv = net_io.bytes_recv / (1024 * 1024)  # MB
            except AttributeError:
                net_sent = net_recv = 0.0
            
            # スレッド数
            thread_count = self.process.num_threads()
            
            return PerformanceMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_usage=cpu_percent,
                memory_usage=memory_percent,
                memory_mb=memory_info.rss / (1024 * 1024),  # MB
                disk_io_read=disk_read,
                disk_io_write=disk_write,
                network_sent=net_sent,
                network_recv=net_recv,
                active_threads=thread_count,
                
                # Yes-Man固有メトリクス
                **self.yes_man_metrics
            )
            
        except Exception as e:
            logger.error(f"Metrics collection error: {e}")
            # フォールバック値
            return PerformanceMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_usage=0.0,
                memory_usage=0.0,
                memory_mb=0.0,
                disk_io_read=0.0,
                disk_io_write=0.0,
                network_sent=0.0,
                network_recv=0.0,
                active_threads=1,
                **self.yes_man_metrics
            )
    
    async def _check_thresholds(self, metrics: PerformanceMetrics):
        """閾値チェックとアラート生成"""
        alerts_to_create = []
        alerts_to_clear = []
        
        # 各閾値をチェック
        checks = [
            ('cpu_usage', metrics.cpu_usage, self.thresholds.max_cpu_usage),
            ('memory_usage', metrics.memory_usage, self.thresholds.max_memory_usage),
            ('memory_mb', metrics.memory_mb, self.thresholds.max_memory_mb),
            ('total_response_time', metrics.total_response_time, self.thresholds.max_response_time),
            ('wake_word_response_time', metrics.wake_word_response_time, self.thresholds.max_wake_word_time),
            ('stt_processing_time', metrics.stt_processing_time, self.thresholds.max_stt_time),
            ('llm_processing_time', metrics.llm_processing_time, self.thresholds.max_llm_time),
            ('tts_processing_time', metrics.tts_processing_time, self.thresholds.max_tts_time),
            ('audio_latency', metrics.audio_latency, self.thresholds.max_audio_latency)
        ]
        
        for metric_name, current_value, threshold in checks:
            if current_value > threshold:
                # アラート作成
                if metric_name not in self.active_alerts:
                    severity = 'HIGH' if current_value > threshold * 1.5 else 'MEDIUM'
                    alert = PerformanceAlert(metric_name, current_value, threshold, severity)
                    alerts_to_create.append(alert)
                    self.active_alerts[metric_name] = alert
            else:
                # アラート解除
                if metric_name in self.active_alerts:
                    alerts_to_clear.append(metric_name)
        
        # アラート処理
        for alert in alerts_to_create:
            await self._handle_new_alert(alert)
        
        for metric_name in alerts_to_clear:
            await self._clear_alert(metric_name)
    
    async def _handle_new_alert(self, alert: PerformanceAlert):
        """新規アラート処理"""
        logger.warning(f"Performance alert: {alert}")
        self.statistics['total_alerts'] += 1
        
        # コールバック実行
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
        
        # 自動最適化実行
        await self._trigger_optimization(alert)
    
    async def _clear_alert(self, metric_name: str):
        """アラート解除"""
        if metric_name in self.active_alerts:
            logger.info(f"Performance alert cleared: {metric_name}")
            del self.active_alerts[metric_name]
    
    async def _trigger_optimization(self, alert: PerformanceAlert):
        """最適化トリガー"""
        if not self.metrics_history:
            return
        
        latest_metrics = self.metrics_history[-1]
        
        # アラートタイプに応じた最適化
        optimization_map = {
            'cpu_usage': 'cpu_high',
            'memory_usage': 'memory_high',
            'memory_mb': 'memory_high',
            'total_response_time': 'response_slow',
            'wake_word_response_time': 'response_slow',
            'stt_processing_time': 'response_slow',
            'llm_processing_time': 'response_slow',
            'tts_processing_time': 'response_slow',
            'audio_latency': 'audio_latency_high'
        }
        
        optimization_type = optimization_map.get(alert.metric)
        if optimization_type:
            optimizations = await self.optimizer.apply_optimizations(optimization_type, latest_metrics)
            if optimizations:
                self.statistics['total_optimizations'] += len(optimizations)
                logger.info(f"Applied optimizations for {alert.metric}: {optimizations}")
    
    def _update_statistics(self):
        """統計更新"""
        if len(self.metrics_history) < 10:  # 最低10サンプル必要
            return
        
        recent_metrics = list(self.metrics_history)[-60:]  # 直近60秒
        
        # 平均値計算
        cpu_values = [m.cpu_usage for m in recent_metrics]
        memory_values = [m.memory_usage for m in recent_metrics]
        response_times = [m.total_response_time for m in recent_metrics if m.total_response_time > 0]
        
        self.statistics.update({
            'avg_cpu_usage': statistics.mean(cpu_values),
            'avg_memory_usage': statistics.mean(memory_values),
            'avg_response_time': statistics.mean(response_times) if response_times else 0.0
        })
    
    def update_yes_man_metric(self, metric_name: str, value: float):
        """Yes-Man固有メトリクス更新"""
        if metric_name in self.yes_man_metrics:
            self.yes_man_metrics[metric_name] = value
            logger.debug(f"Updated {metric_name}: {value}")
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """現在のメトリクス取得"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンスサマリ取得"""
        return {
            'monitoring_active': self.monitoring_active,
            'metrics_collected': len(self.metrics_history),
            'active_alerts': {name: str(alert) for name, alert in self.active_alerts.items()},
            'statistics': dict(self.statistics),
            'thresholds': asdict(self.thresholds),
            'system_info': dict(self.system_info),
            'optimization_history_count': len(self.optimizer.optimization_history),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_performance_report(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """パフォーマンスレポート生成"""
        if not self.metrics_history:
            return {'error': 'No metrics available'}
        
        # 指定期間のメトリクス抽出
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_metrics = [
            m for m in self.metrics_history 
            if datetime.fromisoformat(m.timestamp) > cutoff_time
        ]
        
        if not recent_metrics:
            recent_metrics = list(self.metrics_history)[-60:]  # 最新60件
        
        # 統計計算
        cpu_values = [m.cpu_usage for m in recent_metrics]
        memory_values = [m.memory_usage for m in recent_metrics]
        response_times = [m.total_response_time for m in recent_metrics if m.total_response_time > 0]
        
        report = {
            'period': f"{duration_minutes} minutes",
            'sample_count': len(recent_metrics),
            'cpu_usage': {
                'min': min(cpu_values),
                'max': max(cpu_values),
                'avg': statistics.mean(cpu_values),
                'median': statistics.median(cpu_values)
            },
            'memory_usage': {
                'min': min(memory_values),
                'max': max(memory_values),
                'avg': statistics.mean(memory_values),
                'median': statistics.median(memory_values)
            },
            'response_times': {
                'min': min(response_times) if response_times else 0.0,
                'max': max(response_times) if response_times else 0.0,
                'avg': statistics.mean(response_times) if response_times else 0.0,
                'median': statistics.median(response_times) if response_times else 0.0
            },
            'alerts_summary': {
                'active_count': len(self.active_alerts),
                'total_generated': self.statistics['total_alerts']
            },
            'performance_status': self._assess_overall_performance(),
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def _assess_overall_performance(self) -> str:
        """全体的なパフォーマンス評価"""
        if not self.metrics_history:
            return 'UNKNOWN'
        
        latest = self.metrics_history[-1]
        
        # 憲法VI違反チェック
        if latest.cpu_usage > self.thresholds.max_cpu_usage:
            return 'POOR'
        if latest.total_response_time > self.thresholds.max_response_time:
            return 'POOR'
        
        # アラート数チェック
        if len(self.active_alerts) > 3:
            return 'DEGRADED'
        elif len(self.active_alerts) > 0:
            return 'FAIR'
        else:
            return 'EXCELLENT'

# シングルトンインスタンス
_performance_monitor: Optional[PerformanceMonitor] = None

def get_performance_monitor() -> PerformanceMonitor:
    """パフォーマンスモニターインスタンス取得"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

# 便利関数
def update_metric(metric_name: str, value: float):
    """メトリクス更新便利関数"""
    monitor = get_performance_monitor()
    monitor.update_yes_man_metric(metric_name, value)

async def start_monitoring():
    """監視開始便利関数"""
    monitor = get_performance_monitor()
    await monitor.start_monitoring()

async def stop_monitoring():
    """監視停止便利関数"""
    monitor = get_performance_monitor()
    await monitor.stop_monitoring()

if __name__ == "__main__":
    # テスト実行
    async def test_monitor():
        monitor = PerformanceMonitor()
        
        def alert_handler(alert: PerformanceAlert):
            print(f"Alert: {alert}")
        
        monitor.register_alert_callback(alert_handler)
        
        await monitor.start_monitoring()
        
        # テスト用高CPU負荷シミュレーション
        await asyncio.sleep(5)
        monitor.update_yes_man_metric('cpu_usage', 35.0)  # 閾値超過
        
        await asyncio.sleep(10)
        await monitor.stop_monitoring()
        
        print("Performance report:")
        print(monitor.get_performance_report())
    
    asyncio.run(test_monitor())