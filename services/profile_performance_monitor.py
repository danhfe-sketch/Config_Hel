"""
Profile Performance Monitor - Performance monitoring and metrics collection for profile operations.

This module provides comprehensive performance monitoring, memory usage tracking,
and execution time profiling for profile operations to optimize performance
and identify bottlenecks.

Requirements addressed:
- 1.5: Optimize performance for large profile operations
- 2.6: Optimize thread management and resource cleanup
- 3.5: Fine-tune progress update frequency
- 4.5: Monitor data integrity performance
- 4.6: Optimize universal format operations
- 5.4: Balance responsiveness and performance
"""

import time
import threading
import os
import logging
import gc
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

# Optional psutil import for memory monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None
from collections import defaultdict, deque
from enum import Enum


class PerformanceMetricType(Enum):
    """Types of performance metrics to track."""
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    THREAD_COUNT = "thread_count"
    PROGRESS_UPDATE_FREQUENCY = "progress_update_frequency"
    PARAMETER_PROCESSING_RATE = "parameter_processing_rate"
    FILE_IO_PERFORMANCE = "file_io_performance"
    UI_RESPONSIVENESS = "ui_responsiveness"


@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""
    metric_type: PerformanceMetricType
    operation_id: str
    operation_type: str
    timestamp: datetime
    value: float
    unit: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationPerformanceProfile:
    """Performance profile for a complete operation."""
    operation_id: str
    operation_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration: float = 0.0
    peak_memory_usage: float = 0.0
    average_memory_usage: float = 0.0
    parameters_processed: int = 0
    parameters_per_second: float = 0.0
    progress_updates_sent: int = 0
    progress_update_frequency: float = 0.0
    thread_count_peak: int = 0
    file_io_operations: int = 0
    file_io_total_time: float = 0.0
    ui_freeze_events: int = 0
    ui_freeze_total_time: float = 0.0
    success: bool = False
    error_message: Optional[str] = None
    optimization_recommendations: List[str] = field(default_factory=list)


class ProfilePerformanceMonitor:
    """
    Performance monitor for profile operations with comprehensive metrics collection.
    
    This class provides real-time performance monitoring, memory usage tracking,
    and optimization recommendations for profile operations.
    """
    
    def __init__(self, max_history_size: int = 1000):
        """
        Initialize the performance monitor.
        
        Args:
            max_history_size: Maximum number of metrics to keep in history
        """
        self.logger = logging.getLogger(__name__)
        self.max_history_size = max_history_size
        
        # Metrics storage
        self.metrics_history: deque = deque(maxlen=max_history_size)
        self.operation_profiles: Dict[str, OperationPerformanceProfile] = {}
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        
        # Performance thresholds
        self.performance_thresholds = {
            PerformanceMetricType.EXECUTION_TIME: 300.0,  # 5 minutes max
            PerformanceMetricType.MEMORY_USAGE: 500.0,    # 500MB max
            PerformanceMetricType.PARAMETER_PROCESSING_RATE: 1.0,  # 1 param/sec min
            PerformanceMetricType.PROGRESS_UPDATE_FREQUENCY: 10.0,  # 10 updates/sec max
            PerformanceMetricType.UI_RESPONSIVENESS: 0.1,  # 100ms max freeze
        }
        
        # Optimization settings
        self.optimal_progress_update_interval = 0.2  # 200ms between updates
        self.optimal_thread_pool_size = min(4, os.cpu_count() or 2)
        self.memory_cleanup_threshold = 100.0  # MB
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_lock = threading.Lock()
        
        # Process monitoring (optional psutil dependency)
        if PSUTIL_AVAILABLE:
            try:
                self.process = psutil.Process()
                self.baseline_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                self.psutil_available = True
            except Exception as e:
                self.process = None
                self.baseline_memory = 0
                self.psutil_available = False
                self.logger.warning(f"psutil initialization failed: {e}")
        else:
            self.process = None
            self.baseline_memory = 0
            self.psutil_available = False
            self.logger.warning("psutil not available, memory monitoring disabled")
        
        self.logger.info("ProfilePerformanceMonitor initialized")
    
    def start_monitoring(self) -> None:
        """Start continuous performance monitoring."""
        with self.monitoring_lock:
            if self.monitoring_active:
                return
                
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                name="PerformanceMonitor",
                daemon=True
            )
            self.monitoring_thread.start()
            
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop continuous performance monitoring."""
        with self.monitoring_lock:
            if not self.monitoring_active:
                return
                
            self.monitoring_active = False
            
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)
            
        self.logger.info("Performance monitoring stopped")
    
    def start_operation_monitoring(self, operation_id: str, operation_type: str, 
                                 expected_parameters: int = 0) -> None:
        """
        Start monitoring a specific operation.
        
        Args:
            operation_id: Unique operation identifier
            operation_type: Type of operation
            expected_parameters: Expected number of parameters to process
        """
        profile = OperationPerformanceProfile(
            operation_id=operation_id,
            operation_type=operation_type,
            start_time=datetime.now()
        )
        
        self.operation_profiles[operation_id] = profile
        
        # Initialize active operation tracking
        self.active_operations[operation_id] = {
            'start_time': time.time(),
            'last_progress_update': time.time(),
            'progress_update_count': 0,
            'parameters_processed': 0,
            'expected_parameters': expected_parameters,
            'memory_samples': [],
            'thread_count_samples': [],
            'file_io_start_times': {},
            'ui_freeze_start': None
        }
        
        self.logger.debug(f"Started monitoring operation: {operation_id}")
    
    def record_progress_update(self, operation_id: str, current_parameter: str = "") -> None:
        """
        Record a progress update event.
        
        Args:
            operation_id: Operation identifier
            current_parameter: Current parameter being processed
        """
        if operation_id not in self.active_operations:
            return
            
        current_time = time.time()
        op_data = self.active_operations[operation_id]
        
        # Update progress tracking
        op_data['progress_update_count'] += 1
        last_update = op_data['last_progress_update']
        update_interval = current_time - last_update
        op_data['last_progress_update'] = current_time
        
        # Record progress update frequency metric
        if update_interval > 0:
            frequency = 1.0 / update_interval
            self._record_metric(
                PerformanceMetricType.PROGRESS_UPDATE_FREQUENCY,
                operation_id,
                self.operation_profiles[operation_id].operation_type,
                frequency,
                "updates/sec",
                {"parameter": current_parameter, "interval": update_interval}
            )
    
    def record_parameter_processed(self, operation_id: str, parameter_name: str, 
                                 processing_time: float) -> None:
        """
        Record a parameter processing event.
        
        Args:
            operation_id: Operation identifier
            parameter_name: Name of processed parameter
            processing_time: Time taken to process parameter
        """
        if operation_id not in self.active_operations:
            return
            
        op_data = self.active_operations[operation_id]
        op_data['parameters_processed'] += 1
        
        # Calculate processing rate
        elapsed_time = time.time() - op_data['start_time']
        if elapsed_time > 0:
            rate = op_data['parameters_processed'] / elapsed_time
            
            self._record_metric(
                PerformanceMetricType.PARAMETER_PROCESSING_RATE,
                operation_id,
                self.operation_profiles[operation_id].operation_type,
                rate,
                "params/sec",
                {"parameter": parameter_name, "processing_time": processing_time}
            )
    
    def record_file_io_start(self, operation_id: str, file_path: str, operation_type: str) -> None:
        """
        Record the start of a file I/O operation.
        
        Args:
            operation_id: Operation identifier
            file_path: Path of file being accessed
            operation_type: Type of I/O operation (read/write)
        """
        if operation_id not in self.active_operations:
            return
            
        io_key = f"{operation_type}_{file_path}"
        self.active_operations[operation_id]['file_io_start_times'][io_key] = time.time()
    
    def record_file_io_end(self, operation_id: str, file_path: str, operation_type: str, 
                          bytes_processed: int = 0) -> None:
        """
        Record the end of a file I/O operation.
        
        Args:
            operation_id: Operation identifier
            file_path: Path of file being accessed
            operation_type: Type of I/O operation (read/write)
            bytes_processed: Number of bytes processed
        """
        if operation_id not in self.active_operations:
            return
            
        io_key = f"{operation_type}_{file_path}"
        start_times = self.active_operations[operation_id]['file_io_start_times']
        
        if io_key in start_times:
            duration = time.time() - start_times[io_key]
            del start_times[io_key]
            
            # Update operation profile
            profile = self.operation_profiles[operation_id]
            profile.file_io_operations += 1
            profile.file_io_total_time += duration
            
            # Record metric
            self._record_metric(
                PerformanceMetricType.FILE_IO_PERFORMANCE,
                operation_id,
                profile.operation_type,
                duration,
                "seconds",
                {
                    "file_path": file_path,
                    "operation_type": operation_type,
                    "bytes_processed": bytes_processed,
                    "throughput": bytes_processed / duration if duration > 0 else 0
                }
            )
    
    def record_ui_freeze_start(self, operation_id: str) -> None:
        """
        Record the start of a UI freeze event.
        
        Args:
            operation_id: Operation identifier
        """
        if operation_id not in self.active_operations:
            return
            
        self.active_operations[operation_id]['ui_freeze_start'] = time.time()
    
    def record_ui_freeze_end(self, operation_id: str) -> None:
        """
        Record the end of a UI freeze event.
        
        Args:
            operation_id: Operation identifier
        """
        if operation_id not in self.active_operations:
            return
            
        op_data = self.active_operations[operation_id]
        freeze_start = op_data.get('ui_freeze_start')
        
        if freeze_start:
            duration = time.time() - freeze_start
            op_data['ui_freeze_start'] = None
            
            # Update operation profile
            profile = self.operation_profiles[operation_id]
            profile.ui_freeze_events += 1
            profile.ui_freeze_total_time += duration
            
            # Record metric
            self._record_metric(
                PerformanceMetricType.UI_RESPONSIVENESS,
                operation_id,
                profile.operation_type,
                duration,
                "seconds",
                {"freeze_duration": duration}
            )
    
    def finish_operation_monitoring(self, operation_id: str, success: bool = True, 
                                  error_message: Optional[str] = None) -> OperationPerformanceProfile:
        """
        Finish monitoring an operation and generate performance profile.
        
        Args:
            operation_id: Operation identifier
            success: Whether operation completed successfully
            error_message: Error message if operation failed
            
        Returns:
            Complete performance profile for the operation
        """
        if operation_id not in self.operation_profiles:
            raise ValueError(f"Operation {operation_id} not found in monitoring")
            
        profile = self.operation_profiles[operation_id]
        op_data = self.active_operations.get(operation_id, {})
        
        # Finalize profile
        profile.end_time = datetime.now()
        profile.total_duration = (profile.end_time - profile.start_time).total_seconds()
        profile.success = success
        profile.error_message = error_message
        
        # Calculate final metrics
        if op_data:
            profile.parameters_processed = op_data['parameters_processed']
            if profile.total_duration > 0:
                profile.parameters_per_second = profile.parameters_processed / profile.total_duration
            
            profile.progress_updates_sent = op_data['progress_update_count']
            if profile.total_duration > 0:
                profile.progress_update_frequency = profile.progress_updates_sent / profile.total_duration
            
            # Memory usage statistics
            memory_samples = op_data.get('memory_samples', [])
            if memory_samples:
                profile.peak_memory_usage = max(memory_samples)
                profile.average_memory_usage = sum(memory_samples) / len(memory_samples)
            
            # Thread count statistics
            thread_samples = op_data.get('thread_count_samples', [])
            if thread_samples:
                profile.thread_count_peak = max(thread_samples)
        
        # Generate optimization recommendations
        profile.optimization_recommendations = self._generate_optimization_recommendations(profile)
        
        # Clean up active operation tracking
        if operation_id in self.active_operations:
            del self.active_operations[operation_id]
        
        self.logger.info(f"Finished monitoring operation {operation_id}: "
                        f"duration={profile.total_duration:.2f}s, "
                        f"params={profile.parameters_processed}, "
                        f"rate={profile.parameters_per_second:.2f} params/sec")
        
        return profile
    
    def get_performance_summary(self, operation_type: Optional[str] = None, 
                              time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """
        Get performance summary statistics.
        
        Args:
            operation_type: Filter by operation type (optional)
            time_window: Time window for analysis (optional)
            
        Returns:
            Dictionary containing performance summary
        """
        # Filter profiles based on criteria
        profiles = list(self.operation_profiles.values())
        
        if operation_type:
            profiles = [p for p in profiles if p.operation_type == operation_type]
            
        if time_window:
            cutoff_time = datetime.now() - time_window
            profiles = [p for p in profiles if p.start_time >= cutoff_time]
        
        if not profiles:
            return {"message": "No operations found matching criteria"}
        
        # Calculate summary statistics
        total_operations = len(profiles)
        successful_operations = len([p for p in profiles if p.success])
        
        durations = [p.total_duration for p in profiles if p.total_duration > 0]
        memory_peaks = [p.peak_memory_usage for p in profiles if p.peak_memory_usage > 0]
        processing_rates = [p.parameters_per_second for p in profiles if p.parameters_per_second > 0]
        
        summary = {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "success_rate": successful_operations / total_operations if total_operations > 0 else 0,
            "performance_metrics": {}
        }
        
        if durations:
            summary["performance_metrics"]["execution_time"] = {
                "average": sum(durations) / len(durations),
                "min": min(durations),
                "max": max(durations),
                "median": sorted(durations)[len(durations) // 2]
            }
        
        if memory_peaks:
            summary["performance_metrics"]["memory_usage"] = {
                "average_peak": sum(memory_peaks) / len(memory_peaks),
                "min_peak": min(memory_peaks),
                "max_peak": max(memory_peaks)
            }
        
        if processing_rates:
            summary["performance_metrics"]["processing_rate"] = {
                "average": sum(processing_rates) / len(processing_rates),
                "min": min(processing_rates),
                "max": max(processing_rates)
            }
        
        # Generate overall recommendations
        summary["optimization_recommendations"] = self._generate_overall_recommendations(profiles)
        
        return summary
    
    def optimize_progress_update_frequency(self, operation_id: str) -> float:
        """
        Calculate optimal progress update frequency for an operation.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            Recommended update interval in seconds
        """
        if operation_id not in self.active_operations:
            return self.optimal_progress_update_interval
            
        op_data = self.active_operations[operation_id]
        
        # Analyze current update frequency
        current_frequency = op_data['progress_update_count']
        elapsed_time = time.time() - op_data['start_time']
        
        if elapsed_time > 0:
            updates_per_second = current_frequency / elapsed_time
            
            # Adjust based on performance thresholds
            if updates_per_second > self.performance_thresholds[PerformanceMetricType.PROGRESS_UPDATE_FREQUENCY]:
                # Too frequent, increase interval
                return min(self.optimal_progress_update_interval * 1.5, 1.0)
            elif updates_per_second < 1.0:
                # Too infrequent, decrease interval
                return max(self.optimal_progress_update_interval * 0.5, 0.05)
        
        return self.optimal_progress_update_interval
    
    def should_trigger_memory_cleanup(self) -> bool:
        """
        Determine if memory cleanup should be triggered.
        
        Returns:
            True if memory cleanup is recommended
        """
        if not self.psutil_available or not self.process:
            return False
            
        try:
            current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - self.baseline_memory
            
            return memory_increase > self.memory_cleanup_threshold
        except Exception:
            return False
    
    def trigger_memory_cleanup(self) -> Tuple[float, float]:
        """
        Trigger memory cleanup and return before/after memory usage.
        
        Returns:
            Tuple of (memory_before_mb, memory_after_mb)
        """
        if not self.psutil_available or not self.process:
            # Just run garbage collection without memory monitoring
            gc.collect()
            return 0.0, 0.0
            
        try:
            memory_before = self.process.memory_info().rss / 1024 / 1024
            
            # Force garbage collection
            gc.collect()
            
            memory_after = self.process.memory_info().rss / 1024 / 1024
            
            self.logger.info(f"Memory cleanup: {memory_before:.1f}MB -> {memory_after:.1f}MB "
                           f"(freed {memory_before - memory_after:.1f}MB)")
            
            return memory_before, memory_after
            
        except Exception as e:
            self.logger.error(f"Memory cleanup failed: {e}")
            return 0.0, 0.0
    
    def get_optimization_recommendations(self, operation_id: str) -> List[str]:
        """
        Get real-time optimization recommendations for an active operation.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        if operation_id not in self.active_operations:
            return recommendations
            
        op_data = self.active_operations[operation_id]
        elapsed_time = time.time() - op_data['start_time']
        
        # Check progress update frequency
        if op_data['progress_update_count'] > 0 and elapsed_time > 0:
            update_frequency = op_data['progress_update_count'] / elapsed_time
            if update_frequency > 10:
                recommendations.append("Reduce progress update frequency to improve performance")
        
        # Check memory usage
        if self.should_trigger_memory_cleanup():
            recommendations.append("Consider triggering memory cleanup")
        
        # Check processing rate
        if op_data['parameters_processed'] > 0 and elapsed_time > 5:
            rate = op_data['parameters_processed'] / elapsed_time
            if rate < 1.0:
                recommendations.append("Parameter processing rate is slow, consider optimization")
        
        return recommendations
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop running in background thread."""
        while self.monitoring_active:
            try:
                # Sample system metrics for active operations
                if self.psutil_available and self.process:
                    current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                else:
                    current_memory = 0.0
                current_threads = threading.active_count()
                
                # Update active operations with current samples
                for operation_id, op_data in self.active_operations.items():
                    op_data['memory_samples'].append(current_memory)
                    op_data['thread_count_samples'].append(current_threads)
                    
                    # Keep only recent samples (last 100)
                    if len(op_data['memory_samples']) > 100:
                        op_data['memory_samples'] = op_data['memory_samples'][-100:]
                    if len(op_data['thread_count_samples']) > 100:
                        op_data['thread_count_samples'] = op_data['thread_count_samples'][-100:]
                
                # Record system-wide metrics
                if self.active_operations:
                    for operation_id in list(self.active_operations.keys()):
                        if operation_id in self.operation_profiles:
                            self._record_metric(
                                PerformanceMetricType.MEMORY_USAGE,
                                operation_id,
                                self.operation_profiles[operation_id].operation_type,
                                current_memory,
                                "MB"
                            )
                            
                            self._record_metric(
                                PerformanceMetricType.THREAD_COUNT,
                                operation_id,
                                self.operation_profiles[operation_id].operation_type,
                                current_threads,
                                "threads"
                            )
                
                # Sleep for monitoring interval
                time.sleep(1.0)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                time.sleep(5.0)  # Longer sleep on error
    
    def _record_metric(self, metric_type: PerformanceMetricType, operation_id: str, 
                      operation_type: str, value: float, unit: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a performance metric."""
        metric = PerformanceMetric(
            metric_type=metric_type,
            operation_id=operation_id,
            operation_type=operation_type,
            timestamp=datetime.now(),
            value=value,
            unit=unit,
            metadata=metadata or {}
        )
        
        self.metrics_history.append(metric)
    
    def _generate_optimization_recommendations(self, profile: OperationPerformanceProfile) -> List[str]:
        """Generate optimization recommendations for a completed operation."""
        recommendations = []
        
        # Execution time recommendations
        if profile.total_duration > self.performance_thresholds[PerformanceMetricType.EXECUTION_TIME]:
            recommendations.append(f"Operation took {profile.total_duration:.1f}s, consider optimizing for large profiles")
        
        # Memory usage recommendations
        if profile.peak_memory_usage > self.performance_thresholds[PerformanceMetricType.MEMORY_USAGE]:
            recommendations.append(f"Peak memory usage {profile.peak_memory_usage:.1f}MB is high, consider memory optimization")
        
        # Processing rate recommendations
        if profile.parameters_per_second < self.performance_thresholds[PerformanceMetricType.PARAMETER_PROCESSING_RATE]:
            recommendations.append(f"Parameter processing rate {profile.parameters_per_second:.2f} params/sec is slow")
        
        # Progress update frequency recommendations
        if profile.progress_update_frequency > self.performance_thresholds[PerformanceMetricType.PROGRESS_UPDATE_FREQUENCY]:
            recommendations.append(f"Progress updates too frequent ({profile.progress_update_frequency:.1f}/sec), reduce frequency")
        
        # UI responsiveness recommendations
        if profile.ui_freeze_total_time > 0:
            recommendations.append(f"UI freezes detected ({profile.ui_freeze_events} events, {profile.ui_freeze_total_time:.2f}s total)")
        
        # File I/O recommendations
        if profile.file_io_operations > 0:
            avg_io_time = profile.file_io_total_time / profile.file_io_operations
            if avg_io_time > 1.0:
                recommendations.append(f"File I/O operations are slow (avg {avg_io_time:.2f}s), consider optimization")
        
        return recommendations
    
    def _generate_overall_recommendations(self, profiles: List[OperationPerformanceProfile]) -> List[str]:
        """Generate overall optimization recommendations based on multiple operations."""
        recommendations = []
        
        if not profiles:
            return recommendations
        
        # Analyze success rates
        success_rate = len([p for p in profiles if p.success]) / len(profiles)
        if success_rate < 0.9:
            recommendations.append(f"Success rate is {success_rate:.1%}, investigate failure causes")
        
        # Analyze average performance
        avg_duration = sum(p.total_duration for p in profiles) / len(profiles)
        if avg_duration > 60:
            recommendations.append(f"Average operation time is {avg_duration:.1f}s, consider performance optimization")
        
        # Analyze memory usage trends
        memory_peaks = [p.peak_memory_usage for p in profiles if p.peak_memory_usage > 0]
        if memory_peaks:
            avg_memory = sum(memory_peaks) / len(memory_peaks)
            if avg_memory > 200:
                recommendations.append(f"Average peak memory usage is {avg_memory:.1f}MB, consider memory optimization")
        
        return recommendations
    
    def export_performance_data(self, file_path: str, operation_type: Optional[str] = None) -> bool:
        """
        Export performance data to a file for analysis.
        
        Args:
            file_path: Path to export file
            operation_type: Filter by operation type (optional)
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            import json
            
            # Prepare data for export
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "operation_profiles": [],
                "metrics_summary": self.get_performance_summary(operation_type)
            }
            
            # Add operation profiles
            for profile in self.operation_profiles.values():
                if operation_type is None or profile.operation_type == operation_type:
                    profile_data = {
                        "operation_id": profile.operation_id,
                        "operation_type": profile.operation_type,
                        "start_time": profile.start_time.isoformat(),
                        "end_time": profile.end_time.isoformat() if profile.end_time else None,
                        "total_duration": profile.total_duration,
                        "peak_memory_usage": profile.peak_memory_usage,
                        "average_memory_usage": profile.average_memory_usage,
                        "parameters_processed": profile.parameters_processed,
                        "parameters_per_second": profile.parameters_per_second,
                        "progress_updates_sent": profile.progress_updates_sent,
                        "progress_update_frequency": profile.progress_update_frequency,
                        "thread_count_peak": profile.thread_count_peak,
                        "file_io_operations": profile.file_io_operations,
                        "file_io_total_time": profile.file_io_total_time,
                        "ui_freeze_events": profile.ui_freeze_events,
                        "ui_freeze_total_time": profile.ui_freeze_total_time,
                        "success": profile.success,
                        "error_message": profile.error_message,
                        "optimization_recommendations": profile.optimization_recommendations
                    }
                    export_data["operation_profiles"].append(profile_data)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Performance data exported to: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export performance data: {e}")
            return False
    
    def clear_history(self, older_than: Optional[timedelta] = None) -> int:
        """
        Clear performance history.
        
        Args:
            older_than: Clear entries older than this timedelta (optional)
            
        Returns:
            Number of entries cleared
        """
        if older_than is None:
            # Clear all
            cleared_count = len(self.metrics_history) + len(self.operation_profiles)
            self.metrics_history.clear()
            self.operation_profiles.clear()
        else:
            # Clear old entries
            cutoff_time = datetime.now() - older_than
            
            # Clear old metrics
            original_metrics_count = len(self.metrics_history)
            self.metrics_history = deque(
                [m for m in self.metrics_history if m.timestamp >= cutoff_time],
                maxlen=self.max_history_size
            )
            
            # Clear old operation profiles
            original_profiles_count = len(self.operation_profiles)
            old_profile_ids = [
                op_id for op_id, profile in self.operation_profiles.items()
                if profile.start_time < cutoff_time
            ]
            for op_id in old_profile_ids:
                del self.operation_profiles[op_id]
            
            cleared_count = (original_metrics_count - len(self.metrics_history) + 
                           original_profiles_count - len(self.operation_profiles))
        
        self.logger.info(f"Cleared {cleared_count} performance history entries")
        return cleared_count