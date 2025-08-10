"""
Profile Operation Logger Service

This service provides comprehensive logging and diagnostics for all profile operations
including detailed timestamps, performance monitoring, and diagnostic information collection.
"""

import logging
import json
import time
import traceback
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import os
import platform
from contextlib import contextmanager

# Optional dependency for system monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


@dataclass
class ProfileOperationMetrics:
    """Metrics for profile operations."""
    operation_id: str
    operation_type: str  # 'load', 'save', 'validate', 'convert', 'migrate'
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    parameters_processed: int = 0
    file_size_bytes: Optional[int] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None


@dataclass
class DiagnosticInfo:
    """Diagnostic information for troubleshooting."""
    timestamp: datetime
    operation_id: str
    system_info: Dict[str, Any]
    application_state: Dict[str, Any]
    error_context: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None


class ProfileOperationLogger:
    """
    Comprehensive logging service for profile operations with performance monitoring
    and diagnostic information collection.
    """
    
    def __init__(self, log_directory: str = "logs"):
        """
        Initialize the profile operation logger.
        
        Args:
            log_directory: Directory to store log files
        """
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(exist_ok=True)
        
        # Setup loggers
        self._setup_loggers()
        
        # Operation tracking
        self._active_operations: Dict[str, ProfileOperationMetrics] = {}
        self._operation_history: List[ProfileOperationMetrics] = []
        self._lock = threading.Lock()
        
        # Performance monitoring
        self._performance_samples: List[Dict[str, Any]] = []
        self._diagnostic_data: List[DiagnosticInfo] = []
        
        # Initialize system monitoring
        self._init_system_monitoring()
    
    def _setup_loggers(self):
        """Setup specialized loggers for different aspects of profile operations."""
        
        # Main profile operations logger
        self.profile_logger = logging.getLogger('profile_operations')
        self.profile_logger.setLevel(logging.DEBUG)
        
        # Performance logger
        self.performance_logger = logging.getLogger('profile_performance')
        self.performance_logger.setLevel(logging.INFO)
        
        # Diagnostics logger
        self.diagnostics_logger = logging.getLogger('profile_diagnostics')
        self.diagnostics_logger.setLevel(logging.DEBUG)
        
        # Error logger
        self.error_logger = logging.getLogger('profile_errors')
        self.error_logger.setLevel(logging.ERROR)
        
        # Setup file handlers
        self._setup_file_handlers()
    
    def _setup_file_handlers(self):
        """Setup file handlers for different log types."""
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        json_formatter = logging.Formatter('%(message)s')
        
        # Profile operations log
        profile_handler = logging.FileHandler(
            self.log_directory / 'profile_operations.log',
            encoding='utf-8'
        )
        profile_handler.setFormatter(detailed_formatter)
        self.profile_logger.addHandler(profile_handler)
        
        # Performance log (JSON format)
        performance_handler = logging.FileHandler(
            self.log_directory / 'profile_performance.log',
            encoding='utf-8'
        )
        performance_handler.setFormatter(json_formatter)
        self.performance_logger.addHandler(performance_handler)
        
        # Diagnostics log
        diagnostics_handler = logging.FileHandler(
            self.log_directory / 'profile_diagnostics.log',
            encoding='utf-8'
        )
        diagnostics_handler.setFormatter(detailed_formatter)
        self.diagnostics_logger.addHandler(diagnostics_handler)
        
        # Error log
        error_handler = logging.FileHandler(
            self.log_directory / 'profile_errors.log',
            encoding='utf-8'
        )
        error_handler.setFormatter(detailed_formatter)
        self.error_logger.addHandler(error_handler)
    
    def _init_system_monitoring(self):
        """Initialize system monitoring capabilities."""
        try:
            # Get initial system info
            self.system_info = {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
            }
            
            if PSUTIL_AVAILABLE:
                self.system_info.update({
                    'cpu_count': psutil.cpu_count(),
                    'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                    'disk_free_gb': round(psutil.disk_usage('.').free / (1024**3), 2)
                })
            else:
                self.system_info.update({
                    'cpu_count': 'N/A (psutil not available)',
                    'memory_total_gb': 'N/A (psutil not available)',
                    'disk_free_gb': 'N/A (psutil not available)'
                })
        except Exception as e:
            self.profile_logger.warning(f"Failed to initialize system monitoring: {e}")
            self.system_info = {}
    
    def start_operation(self, operation_type: str, context: Dict[str, Any] = None) -> str:
        """
        Start tracking a profile operation.
        
        Args:
            operation_type: Type of operation (load, save, validate, etc.)
            context: Additional context information
            
        Returns:
            Operation ID for tracking
        """
        operation_id = f"{operation_type}_{int(time.time() * 1000)}"
        
        metrics = ProfileOperationMetrics(
            operation_id=operation_id,
            operation_type=operation_type,
            start_time=datetime.now()
        )
        
        with self._lock:
            self._active_operations[operation_id] = metrics
        
        # Log operation start
        self.profile_logger.info(
            f"OPERATION_START: {operation_id} - {operation_type}",
            extra={'operation_id': operation_id, 'context': context or {}}
        )
        
        # Collect initial diagnostic info
        self._collect_diagnostic_info(operation_id, "operation_start", context)
        
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, 
                     error_message: str = None, additional_metrics: Dict[str, Any] = None):
        """
        End tracking a profile operation.
        
        Args:
            operation_id: Operation ID from start_operation
            success: Whether the operation succeeded
            error_message: Error message if operation failed
            additional_metrics: Additional metrics to record
        """
        with self._lock:
            if operation_id not in self._active_operations:
                self.profile_logger.warning(f"Unknown operation ID: {operation_id}")
                return
            
            metrics = self._active_operations[operation_id]
            metrics.end_time = datetime.now()
            metrics.duration_ms = (metrics.end_time - metrics.start_time).total_seconds() * 1000
            metrics.success = success
            metrics.error_message = error_message
            
            # Add additional metrics
            if additional_metrics:
                if 'parameters_processed' in additional_metrics:
                    metrics.parameters_processed = additional_metrics['parameters_processed']
                if 'file_size_bytes' in additional_metrics:
                    metrics.file_size_bytes = additional_metrics['file_size_bytes']
            
            # Collect system metrics
            try:
                if PSUTIL_AVAILABLE:
                    metrics.memory_usage_mb = round(psutil.Process().memory_info().rss / (1024**2), 2)
                    metrics.cpu_usage_percent = round(psutil.Process().cpu_percent(), 2)
            except Exception:
                pass
            
            # Move to history
            self._operation_history.append(metrics)
            del self._active_operations[operation_id]
        
        # Log operation end
        log_level = logging.INFO if success else logging.ERROR
        status = "SUCCESS" if success else "FAILURE"
        
        self.profile_logger.log(
            log_level,
            f"OPERATION_END: {operation_id} - {status} - {metrics.duration_ms:.2f}ms"
        )
        
        # Log performance metrics
        self._log_performance_metrics(metrics)
        
        # Log error if failed
        if not success and error_message:
            self.error_logger.error(
                f"Operation {operation_id} failed: {error_message}",
                extra={'operation_id': operation_id, 'operation_type': metrics.operation_type}
            )
            
            # Collect error diagnostic info
            self._collect_diagnostic_info(operation_id, "operation_error", {
                'error_message': error_message,
                'stack_trace': traceback.format_exc()
            })
    
    @contextmanager
    def operation_context(self, operation_type: str, context: Dict[str, Any] = None):
        """
        Context manager for tracking profile operations.
        
        Args:
            operation_type: Type of operation
            context: Additional context information
        """
        operation_id = self.start_operation(operation_type, context)
        try:
            yield operation_id
            self.end_operation(operation_id, success=True)
        except Exception as e:
            self.end_operation(operation_id, success=False, error_message=str(e))
            raise
    
    def log_operation_step(self, operation_id: str, step: str, details: Dict[str, Any] = None):
        """
        Log a step within an operation.
        
        Args:
            operation_id: Operation ID
            step: Step description
            details: Additional step details
        """
        self.profile_logger.info(
            f"OPERATION_STEP: {operation_id} - {step}",
            extra={'operation_id': operation_id, 'step': step, 'details': details or {}}
        )
    
    def log_validation_result(self, operation_id: str, validation_result: Dict[str, Any]):
        """
        Log validation results with detailed information.
        
        Args:
            operation_id: Operation ID
            validation_result: Validation result details
        """
        is_valid = validation_result.get('is_valid', False)
        log_level = logging.INFO if is_valid else logging.WARNING
        
        self.profile_logger.log(
            log_level,
            f"VALIDATION_RESULT: {operation_id} - {'VALID' if is_valid else 'INVALID'}",
            extra={
                'operation_id': operation_id,
                'validation_result': validation_result
            }
        )
    
    def _log_performance_metrics(self, metrics: ProfileOperationMetrics):
        """Log performance metrics in JSON format."""
        performance_data = {
            'timestamp': metrics.end_time.isoformat(),
            'operation_id': metrics.operation_id,
            'operation_type': metrics.operation_type,
            'duration_ms': metrics.duration_ms,
            'success': metrics.success,
            'parameters_processed': metrics.parameters_processed,
            'file_size_bytes': metrics.file_size_bytes,
            'memory_usage_mb': metrics.memory_usage_mb,
            'cpu_usage_percent': metrics.cpu_usage_percent
        }
        
        self.performance_logger.info(json.dumps(performance_data))
        
        # Store for analysis
        with self._lock:
            self._performance_samples.append(performance_data)
            
            # Keep only recent samples (last 1000)
            if len(self._performance_samples) > 1000:
                self._performance_samples = self._performance_samples[-1000:]
    
    def _collect_diagnostic_info(self, operation_id: str, event_type: str, 
                                context: Dict[str, Any] = None):
        """
        Collect diagnostic information for troubleshooting.
        
        Args:
            operation_id: Operation ID
            event_type: Type of diagnostic event
            context: Additional context information
        """
        try:
            # Collect system state
            system_state = {
                'active_operations': len(self._active_operations),
                'operation_history_count': len(self._operation_history)
            }
            
            if PSUTIL_AVAILABLE:
                system_state.update({
                    'memory_usage': psutil.virtual_memory()._asdict(),
                    'cpu_usage': psutil.cpu_percent(interval=None),
                    'disk_usage': psutil.disk_usage('.')._asdict()
                })
            else:
                system_state.update({
                    'memory_usage': 'N/A (psutil not available)',
                    'cpu_usage': 'N/A (psutil not available)',
                    'disk_usage': 'N/A (psutil not available)'
                })
            
            # Collect application state
            app_state = {
                'event_type': event_type,
                'thread_count': threading.active_count(),
                'log_directory_size': self._get_log_directory_size()
            }
            
            diagnostic_info = DiagnosticInfo(
                timestamp=datetime.now(),
                operation_id=operation_id,
                system_info=system_state,
                application_state=app_state,
                error_context=context
            )
            
            if context and 'stack_trace' in context:
                diagnostic_info.stack_trace = context['stack_trace']
            
            with self._lock:
                self._diagnostic_data.append(diagnostic_info)
                
                # Keep only recent diagnostic data (last 500 entries)
                if len(self._diagnostic_data) > 500:
                    self._diagnostic_data = self._diagnostic_data[-500:]
            
            # Log diagnostic info
            self.diagnostics_logger.debug(
                f"DIAGNOSTIC_INFO: {operation_id} - {event_type}",
                extra={'diagnostic_info': asdict(diagnostic_info)}
            )
            
        except Exception as e:
            self.profile_logger.warning(f"Failed to collect diagnostic info: {e}")
    
    def _get_log_directory_size(self) -> int:
        """Get total size of log directory in bytes."""
        try:
            total_size = 0
            for file_path in self.log_directory.glob('*.log'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except Exception:
            return 0
    
    def get_operation_metrics(self, operation_type: str = None, 
                            hours: int = 24) -> List[ProfileOperationMetrics]:
        """
        Get operation metrics for analysis.
        
        Args:
            operation_type: Filter by operation type (optional)
            hours: Number of hours to look back
            
        Returns:
            List of operation metrics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            filtered_metrics = [
                m for m in self._operation_history
                if m.start_time >= cutoff_time and
                (operation_type is None or m.operation_type == operation_type)
            ]
        
        return filtered_metrics
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance summary for the specified time period.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Performance summary statistics
        """
        metrics = self.get_operation_metrics(hours=hours)
        
        if not metrics:
            return {'message': 'No operations found in the specified time period'}
        
        # Calculate statistics
        durations = [m.duration_ms for m in metrics if m.duration_ms is not None]
        success_count = sum(1 for m in metrics if m.success)
        total_count = len(metrics)
        
        summary = {
            'time_period_hours': hours,
            'total_operations': total_count,
            'successful_operations': success_count,
            'success_rate_percent': round((success_count / total_count) * 100, 2) if total_count > 0 else 0,
            'average_duration_ms': round(sum(durations) / len(durations), 2) if durations else 0,
            'min_duration_ms': min(durations) if durations else 0,
            'max_duration_ms': max(durations) if durations else 0,
            'operations_by_type': {}
        }
        
        # Group by operation type
        for metric in metrics:
            op_type = metric.operation_type
            if op_type not in summary['operations_by_type']:
                summary['operations_by_type'][op_type] = {
                    'count': 0,
                    'success_count': 0,
                    'average_duration_ms': 0
                }
            
            summary['operations_by_type'][op_type]['count'] += 1
            if metric.success:
                summary['operations_by_type'][op_type]['success_count'] += 1
            
            if metric.duration_ms:
                current_avg = summary['operations_by_type'][op_type]['average_duration_ms']
                count = summary['operations_by_type'][op_type]['count']
                summary['operations_by_type'][op_type]['average_duration_ms'] = round(
                    (current_avg * (count - 1) + metric.duration_ms) / count, 2
                )
        
        return summary
    
    def get_diagnostic_data(self, operation_id: str = None, 
                          hours: int = 24) -> List[DiagnosticInfo]:
        """
        Get diagnostic data for troubleshooting.
        
        Args:
            operation_id: Filter by operation ID (optional)
            hours: Number of hours to look back
            
        Returns:
            List of diagnostic information
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            filtered_data = [
                d for d in self._diagnostic_data
                if d.timestamp >= cutoff_time and
                (operation_id is None or d.operation_id == operation_id)
            ]
        
        return filtered_data
    
    def export_diagnostics(self, file_path: str, hours: int = 24):
        """
        Export diagnostic data to a file for analysis.
        
        Args:
            file_path: Path to export file
            hours: Number of hours of data to export
        """
        try:
            metrics = self.get_operation_metrics(hours=hours)
            diagnostics = self.get_diagnostic_data(hours=hours)
            performance_summary = self.get_performance_summary(hours=hours)
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'time_period_hours': hours,
                'system_info': self.system_info,
                'performance_summary': performance_summary,
                'operation_metrics': [asdict(m) for m in metrics],
                'diagnostic_data': [asdict(d) for d in diagnostics]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            self.profile_logger.info(f"Diagnostics exported to {file_path}")
            
        except Exception as e:
            self.error_logger.error(f"Failed to export diagnostics: {e}")
            raise


# Global logger instance
_profile_operation_logger = None

def get_profile_operation_logger() -> ProfileOperationLogger:
    """Get the global profile operation logger instance."""
    global _profile_operation_logger
    if _profile_operation_logger is None:
        _profile_operation_logger = ProfileOperationLogger()
    return _profile_operation_logger