"""
Parameter Operation Logger for LT32 PRO Configurator

This module provides comprehensive logging for all parameter operations including
read/write operations, command and response logging, operation statistics, and
log export functionality as specified in task 8.1.

Requirements addressed:
- 9.1: Logging for all parameter read/write operations with timestamps
- 9.2: Command and response logging for troubleshooting
- 9.3: Operation summary logs showing success/failure statistics
- 9.4: Log export functionality for parameter operation records
- 9.5: Detailed error information for failed operations
- 9.6: Parameter operation tracking and history
"""

import logging
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from collections import defaultdict, deque


@dataclass
class ParameterOperationLog:
    """Detailed log entry for a parameter operation."""
    timestamp: datetime
    operation_type: str  # 'read', 'write', 'bulk_read', 'bulk_write'
    parameter_name: str
    command_sent: Optional[str]
    response_received: Optional[str]
    success: bool
    value: Optional[Any]
    error_message: Optional[str]
    duration_ms: float
    session_id: str
    operation_id: str
    retry_count: int = 0
    context: Optional[Dict[str, Any]] = None


@dataclass
class OperationSummary:
    """Summary statistics for parameter operations."""
    session_id: str
    start_time: datetime
    end_time: datetime
    total_operations: int
    successful_operations: int
    failed_operations: int
    total_duration_ms: float
    parameters_processed: List[str]
    error_categories: Dict[str, int]
    operation_types: Dict[str, int]


class ParameterOperationLogger:
    """
    Comprehensive logger for parameter operations with statistics and export capabilities.
    
    This logger provides detailed tracking of all parameter operations including:
    - Individual parameter read/write operations
    - Bulk operations with progress tracking
    - Command and response logging for troubleshooting
    - Operation statistics and summaries
    - Export functionality for analysis and record-keeping
    """

    def __init__(self, app_instance=None, max_log_entries: int = 10000):
        """
        Initialize the parameter operation logger.
        
        Args:
            app_instance: Main application instance for UI integration
            max_log_entries: Maximum number of log entries to keep in memory
        """
        self.app = app_instance
        self.max_log_entries = max_log_entries
        
        # Thread-safe logging
        self._lock = threading.Lock()
        
        # Log storage
        self.operation_logs = deque(maxlen=max_log_entries)
        self.session_summaries = {}
        self.current_session_id = self._generate_session_id()
        self.current_operation_id = 0
        
        # Statistics tracking
        self.operation_stats = defaultdict(int)
        self.error_stats = defaultdict(int)
        self.parameter_stats = defaultdict(lambda: {'reads': 0, 'writes': 0, 'errors': 0})
        
        # Session tracking
        self.session_start_time = datetime.now()
        self.active_operations = {}  # Track ongoing operations
        
        # Initialize Python logging
        self._init_python_logging()
        
        # Log the logger initialization
        self.log_system_event("Parameter Operation Logger initialized", {
            'session_id': self.current_session_id,
            'max_entries': max_log_entries,
            'start_time': self.session_start_time.isoformat()
        })

    def _init_python_logging(self):
        """Initialize Python logging for file-based logging."""
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Configure logger
        self.logger = logging.getLogger('parameter_operations')
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # File handler for detailed logs
        log_file = log_dir / f"parameter_operations_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter for detailed logging
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler for important messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _generate_operation_id(self) -> str:
        """Generate a unique operation ID."""
        self.current_operation_id += 1
        return f"op_{self.current_session_id}_{self.current_operation_id:04d}"

    def log_parameter_operation(self, 
                              operation_type: str,
                              parameter_name: str,
                              command_sent: Optional[str] = None,
                              response_received: Optional[str] = None,
                              success: bool = True,
                              value: Optional[Any] = None,
                              error_message: Optional[str] = None,
                              duration_ms: float = 0.0,
                              retry_count: int = 0,
                              context: Optional[Dict[str, Any]] = None) -> str:
        """
        Log a parameter operation with full details.
        
        Args:
            operation_type: Type of operation ('read', 'write', 'bulk_read', 'bulk_write')
            parameter_name: Name of the parameter being operated on
            command_sent: AT command sent to device
            response_received: Response received from device
            success: Whether the operation was successful
            value: Parameter value (for reads) or value being set (for writes)
            error_message: Error message if operation failed
            duration_ms: Operation duration in milliseconds
            retry_count: Number of retries attempted
            context: Additional context information
            
        Returns:
            Operation ID for tracking
        """
        with self._lock:
            operation_id = self._generate_operation_id()
            timestamp = datetime.now()
            
            # Create log entry
            log_entry = ParameterOperationLog(
                timestamp=timestamp,
                operation_type=operation_type,
                parameter_name=parameter_name,
                command_sent=command_sent,
                response_received=response_received,
                success=success,
                value=value,
                error_message=error_message,
                duration_ms=duration_ms,
                session_id=self.current_session_id,
                operation_id=operation_id,
                retry_count=retry_count,
                context=context or {}
            )
            
            # Store in memory
            self.operation_logs.append(log_entry)
            
            # Update statistics
            self._update_statistics(log_entry)
            
            # Log to file
            self._log_to_file(log_entry)
            
            # Log to UI if available
            self._log_to_ui(log_entry)
            
            return operation_id

    def _update_statistics(self, log_entry: ParameterOperationLog):
        """Update operation statistics."""
        # Overall operation stats
        self.operation_stats[log_entry.operation_type] += 1
        self.operation_stats['total'] += 1
        
        if log_entry.success:
            self.operation_stats['successful'] += 1
        else:
            self.operation_stats['failed'] += 1
            
            # Error categorization
            if log_entry.error_message:
                error_category = self._categorize_error(log_entry.error_message)
                self.error_stats[error_category] += 1
        
        # Parameter-specific stats
        param_stats = self.parameter_stats[log_entry.parameter_name]
        if log_entry.operation_type in ['read', 'bulk_read']:
            param_stats['reads'] += 1
        elif log_entry.operation_type in ['write', 'bulk_write']:
            param_stats['writes'] += 1
        
        if not log_entry.success:
            param_stats['errors'] += 1

    def _categorize_error(self, error_message: str) -> str:
        """Categorize error messages for statistics."""
        error_lower = error_message.lower()
        
        if 'timeout' in error_lower or 'no response' in error_lower:
            return 'timeout'
        elif 'connection' in error_lower or 'disconnected' in error_lower:
            return 'connection'
        elif 'invalid' in error_lower or 'format' in error_lower:
            return 'format'
        elif 'permission' in error_lower or 'access' in error_lower:
            return 'permission'
        elif 'validation' in error_lower or 'range' in error_lower:
            return 'validation'
        else:
            return 'other'

    def _log_to_file(self, log_entry: ParameterOperationLog):
        """Log entry to file using Python logging."""
        level = logging.ERROR if not log_entry.success else logging.INFO
        
        # Create detailed log message
        message_parts = [
            f"[{log_entry.operation_type.upper()}]",
            f"Parameter: {log_entry.parameter_name}",
            f"Success: {log_entry.success}",
            f"Duration: {log_entry.duration_ms:.1f}ms",
            f"OpID: {log_entry.operation_id}"
        ]
        
        if log_entry.command_sent:
            message_parts.append(f"Command: {log_entry.command_sent}")
        
        if log_entry.response_received:
            message_parts.append(f"Response: {log_entry.response_received}")
        
        if log_entry.value is not None:
            message_parts.append(f"Value: {log_entry.value}")
        
        if log_entry.error_message:
            message_parts.append(f"Error: {log_entry.error_message}")
        
        if log_entry.retry_count > 0:
            message_parts.append(f"Retries: {log_entry.retry_count}")
        
        message = " | ".join(message_parts)
        self.logger.log(level, message)

    def _log_to_ui(self, log_entry: ParameterOperationLog):
        """Log entry to UI log frame if available."""
        if not self.app or not hasattr(self.app, 'log_frame'):
            return
        
        try:
            # Format message for UI
            timestamp_str = log_entry.timestamp.strftime("%H:%M:%S")
            operation_type = log_entry.operation_type.upper()
            
            if log_entry.success:
                if log_entry.operation_type in ['read', 'bulk_read']:
                    message = f"INFO: [{timestamp_str}] {operation_type} {log_entry.parameter_name}: {log_entry.value} ({log_entry.duration_ms:.1f}ms)"
                else:
                    message = f"INFO: [{timestamp_str}] {operation_type} {log_entry.parameter_name} successful ({log_entry.duration_ms:.1f}ms)"
            else:
                message = f"ERROR: [{timestamp_str}] {operation_type} {log_entry.parameter_name} failed: {log_entry.error_message} ({log_entry.duration_ms:.1f}ms)"
            
            # Add command/response details for debugging
            if log_entry.command_sent:
                self.app.log_frame.log_message(f"DEBUG: Command sent: {log_entry.command_sent}")
            if log_entry.response_received:
                self.app.log_frame.log_message(f"DEBUG: Response received: {log_entry.response_received}")
            
            self.app.log_frame.log_message(message)
            
        except Exception as e:
            # Don't let UI logging errors break the operation
            self.logger.warning(f"Failed to log to UI: {str(e)}")

    def log_bulk_operation_start(self, operation_type: str, parameters: List[str], context: Optional[Dict[str, Any]] = None) -> str:
        """
        Log the start of a bulk operation.
        
        Args:
            operation_type: Type of bulk operation ('bulk_read', 'bulk_write')
            parameters: List of parameter names to be processed
            context: Additional context information
            
        Returns:
            Operation ID for tracking
        """
        operation_id = self._generate_operation_id()
        
        with self._lock:
            self.active_operations[operation_id] = {
                'type': operation_type,
                'parameters': parameters,
                'start_time': datetime.now(),
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'context': context or {}
            }
        
        self.log_system_event(f"Bulk operation started: {operation_type}", {
            'operation_id': operation_id,
            'parameter_count': len(parameters),
            'parameters': parameters,
            'context': context
        })
        
        return operation_id

    def log_bulk_operation_progress(self, operation_id: str, parameter_name: str, success: bool, error_message: Optional[str] = None):
        """
        Log progress of a bulk operation.
        
        Args:
            operation_id: ID of the bulk operation
            parameter_name: Name of the parameter just processed
            success: Whether the parameter operation was successful
            error_message: Error message if operation failed
        """
        with self._lock:
            if operation_id not in self.active_operations:
                return
            
            operation = self.active_operations[operation_id]
            operation['processed'] += 1
            
            if success:
                operation['successful'] += 1
            else:
                operation['failed'] += 1
            
            # Log progress
            progress_pct = (operation['processed'] / len(operation['parameters'])) * 100
            self.log_system_event(f"Bulk operation progress: {operation['type']}", {
                'operation_id': operation_id,
                'parameter': parameter_name,
                'success': success,
                'error': error_message,
                'progress': f"{operation['processed']}/{len(operation['parameters'])} ({progress_pct:.1f}%)",
                'successful': operation['successful'],
                'failed': operation['failed']
            })

    def log_bulk_operation_complete(self, operation_id: str) -> Dict[str, Any]:
        """
        Log completion of a bulk operation and return summary.
        
        Args:
            operation_id: ID of the bulk operation
            
        Returns:
            Dictionary with operation summary
        """
        with self._lock:
            if operation_id not in self.active_operations:
                return {}
            
            operation = self.active_operations[operation_id]
            end_time = datetime.now()
            duration = (end_time - operation['start_time']).total_seconds() * 1000
            
            summary = {
                'operation_id': operation_id,
                'type': operation['type'],
                'total_parameters': len(operation['parameters']),
                'processed': operation['processed'],
                'successful': operation['successful'],
                'failed': operation['failed'],
                'duration_ms': duration,
                'success_rate': (operation['successful'] / operation['processed'] * 100) if operation['processed'] > 0 else 0
            }
            
            # Remove from active operations
            del self.active_operations[operation_id]
            
            self.log_system_event(f"Bulk operation completed: {operation['type']}", summary)
            
            return summary

    def log_system_event(self, event: str, details: Optional[Dict[str, Any]] = None):
        """
        Log a system event related to parameter operations.
        
        Args:
            event: Description of the event
            details: Additional event details
        """
        timestamp = datetime.now()
        
        # Log to file
        message_parts = [f"SYSTEM: {event}"]
        if details:
            message_parts.append(f"Details: {json.dumps(details, default=str)}")
        
        message = " | ".join(message_parts)
        self.logger.info(message)
        
        # Log to UI if available
        if self.app and hasattr(self.app, 'log_frame'):
            try:
                ui_message = f"SYSTEM: [{timestamp.strftime('%H:%M:%S')}] {event}"
                self.app.log_frame.log_message(ui_message)
            except Exception:
                pass  # Don't let UI logging errors break the operation

    def get_operation_statistics(self, time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """
        Get comprehensive operation statistics.
        
        Args:
            time_range: Optional time range to filter statistics (e.g., last hour)
            
        Returns:
            Dictionary with detailed statistics
        """
        with self._lock:
            # Filter logs by time range if specified
            if time_range:
                cutoff_time = datetime.now() - time_range
                filtered_logs = [log for log in self.operation_logs if log.timestamp >= cutoff_time]
            else:
                filtered_logs = list(self.operation_logs)
            
            if not filtered_logs:
                return {
                    'total_operations': 0,
                    'successful_operations': 0,
                    'failed_operations': 0,
                    'success_rate': 0.0,
                    'average_duration_ms': 0.0,
                    'operation_types': {},
                    'error_categories': {},
                    'parameter_stats': {},
                    'time_range': str(time_range) if time_range else 'all_time'
                }
            
            # Calculate statistics
            total_ops = len(filtered_logs)
            successful_ops = sum(1 for log in filtered_logs if log.success)
            failed_ops = total_ops - successful_ops
            
            # Operation types
            op_types = defaultdict(int)
            for log in filtered_logs:
                op_types[log.operation_type] += 1
            
            # Error categories
            error_categories = defaultdict(int)
            for log in filtered_logs:
                if not log.success and log.error_message:
                    category = self._categorize_error(log.error_message)
                    error_categories[category] += 1
            
            # Parameter statistics
            param_stats = defaultdict(lambda: {'reads': 0, 'writes': 0, 'errors': 0, 'avg_duration_ms': 0.0})
            param_durations = defaultdict(list)
            
            for log in filtered_logs:
                param = log.parameter_name
                param_durations[param].append(log.duration_ms)
                
                if log.operation_type in ['read', 'bulk_read']:
                    param_stats[param]['reads'] += 1
                elif log.operation_type in ['write', 'bulk_write']:
                    param_stats[param]['writes'] += 1
                
                if not log.success:
                    param_stats[param]['errors'] += 1
            
            # Calculate average durations
            for param, durations in param_durations.items():
                param_stats[param]['avg_duration_ms'] = sum(durations) / len(durations)
            
            # Overall average duration
            all_durations = [log.duration_ms for log in filtered_logs]
            avg_duration = sum(all_durations) / len(all_durations) if all_durations else 0.0
            
            return {
                'total_operations': total_ops,
                'successful_operations': successful_ops,
                'failed_operations': failed_ops,
                'success_rate': (successful_ops / total_ops * 100) if total_ops > 0 else 0.0,
                'average_duration_ms': avg_duration,
                'operation_types': dict(op_types),
                'error_categories': dict(error_categories),
                'parameter_stats': dict(param_stats),
                'time_range': str(time_range) if time_range else 'all_time',
                'session_id': self.current_session_id,
                'log_count': total_ops
            }

    def export_operation_logs(self, file_path: str, format: str = 'json', time_range: Optional[timedelta] = None) -> bool:
        """
        Export operation logs to a file.
        
        Args:
            file_path: Path to save the exported logs
            format: Export format ('json', 'csv', 'txt')
            time_range: Optional time range to filter logs
            
        Returns:
            True if export was successful, False otherwise
        """
        try:
            with self._lock:
                # Filter logs by time range if specified
                if time_range:
                    cutoff_time = datetime.now() - time_range
                    logs_to_export = [log for log in self.operation_logs if log.timestamp >= cutoff_time]
                else:
                    logs_to_export = list(self.operation_logs)
            
            if not logs_to_export:
                self.logger.warning("No logs to export")
                return False
            
            # Export based on format
            if format.lower() == 'json':
                return self._export_logs_json(file_path, logs_to_export)
            elif format.lower() == 'csv':
                return self._export_logs_csv(file_path, logs_to_export)
            elif format.lower() == 'txt':
                return self._export_logs_txt(file_path, logs_to_export)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            self.logger.error(f"Failed to export logs: {str(e)}")
            return False

    def _export_logs_json(self, file_path: str, logs: List[ParameterOperationLog]) -> bool:
        """Export logs in JSON format."""
        try:
            export_data = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'session_id': self.current_session_id,
                    'log_count': len(logs),
                    'format': 'json'
                },
                'statistics': self.get_operation_statistics(),
                'logs': []
            }
            
            for log in logs:
                log_dict = asdict(log)
                log_dict['timestamp'] = log.timestamp.isoformat()
                export_data['logs'].append(log_dict)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.log_system_event(f"Logs exported to JSON: {file_path}", {
                'log_count': len(logs),
                'file_size_bytes': Path(file_path).stat().st_size
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export logs to JSON: {str(e)}")
            return False

    def _export_logs_csv(self, file_path: str, logs: List[ParameterOperationLog]) -> bool:
        """Export logs in CSV format."""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    'Timestamp', 'Operation Type', 'Parameter Name', 'Success',
                    'Value', 'Command Sent', 'Response Received', 'Error Message',
                    'Duration (ms)', 'Session ID', 'Operation ID', 'Retry Count'
                ])
                
                # Write log entries
                for log in logs:
                    writer.writerow([
                        log.timestamp.isoformat(),
                        log.operation_type,
                        log.parameter_name,
                        log.success,
                        log.value,
                        log.command_sent,
                        log.response_received,
                        log.error_message,
                        log.duration_ms,
                        log.session_id,
                        log.operation_id,
                        log.retry_count
                    ])
            
            self.log_system_event(f"Logs exported to CSV: {file_path}", {
                'log_count': len(logs),
                'file_size_bytes': Path(file_path).stat().st_size
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export logs to CSV: {str(e)}")
            return False

    def _export_logs_txt(self, file_path: str, logs: List[ParameterOperationLog]) -> bool:
        """Export logs in human-readable text format."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write("LT32Pro Parameter Operation Logs\n")
                f.write("=" * 50 + "\n")
                f.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Session ID: {self.current_session_id}\n")
                f.write(f"Total Log Entries: {len(logs)}\n\n")
                
                # Write statistics
                stats = self.get_operation_statistics()
                f.write("Operation Statistics:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Total Operations: {stats['total_operations']}\n")
                f.write(f"Successful: {stats['successful_operations']}\n")
                f.write(f"Failed: {stats['failed_operations']}\n")
                f.write(f"Success Rate: {stats['success_rate']:.1f}%\n")
                f.write(f"Average Duration: {stats['average_duration_ms']:.1f}ms\n\n")
                
                # Write detailed logs
                f.write("Detailed Operation Logs:\n")
                f.write("-" * 25 + "\n\n")
                
                for log in logs:
                    f.write(f"[{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] ")
                    f.write(f"{log.operation_type.upper()} - {log.parameter_name}\n")
                    f.write(f"  Success: {log.success}\n")
                    
                    if log.value is not None:
                        f.write(f"  Value: {log.value}\n")
                    
                    if log.command_sent:
                        f.write(f"  Command: {log.command_sent}\n")
                    
                    if log.response_received:
                        f.write(f"  Response: {log.response_received}\n")
                    
                    if log.error_message:
                        f.write(f"  Error: {log.error_message}\n")
                    
                    f.write(f"  Duration: {log.duration_ms:.1f}ms\n")
                    f.write(f"  Operation ID: {log.operation_id}\n")
                    
                    if log.retry_count > 0:
                        f.write(f"  Retries: {log.retry_count}\n")
                    
                    f.write("\n")
            
            self.log_system_event(f"Logs exported to TXT: {file_path}", {
                'log_count': len(logs),
                'file_size_bytes': Path(file_path).stat().st_size
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export logs to TXT: {str(e)}")
            return False

    def get_recent_operations(self, count: int = 50) -> List[ParameterOperationLog]:
        """
        Get the most recent parameter operations.
        
        Args:
            count: Number of recent operations to return
            
        Returns:
            List of recent operation logs
        """
        with self._lock:
            return list(self.operation_logs)[-count:]

    def get_failed_operations(self, time_range: Optional[timedelta] = None) -> List[ParameterOperationLog]:
        """
        Get all failed operations within a time range.
        
        Args:
            time_range: Optional time range to filter operations
            
        Returns:
            List of failed operation logs
        """
        with self._lock:
            failed_ops = [log for log in self.operation_logs if not log.success]
            
            if time_range:
                cutoff_time = datetime.now() - time_range
                failed_ops = [log for log in failed_ops if log.timestamp >= cutoff_time]
            
            return failed_ops

    def clear_logs(self, keep_statistics: bool = True):
        """
        Clear all operation logs.
        
        Args:
            keep_statistics: Whether to keep current session statistics
        """
        with self._lock:
            if not keep_statistics:
                self.operation_stats.clear()
                self.error_stats.clear()
                self.parameter_stats.clear()
            
            self.operation_logs.clear()
            self.active_operations.clear()
            
            # Start new session
            self.current_session_id = self._generate_session_id()
            self.current_operation_id = 0
            self.session_start_time = datetime.now()
            
            self.log_system_event("Operation logs cleared", {
                'kept_statistics': keep_statistics,
                'new_session_id': self.current_session_id
            })

    def get_session_summary(self) -> OperationSummary:
        """
        Get summary of the current session.
        
        Returns:
            OperationSummary object with session statistics
        """
        with self._lock:
            session_logs = [log for log in self.operation_logs if log.session_id == self.current_session_id]
            
            if not session_logs:
                return OperationSummary(
                    session_id=self.current_session_id,
                    start_time=self.session_start_time,
                    end_time=datetime.now(),
                    total_operations=0,
                    successful_operations=0,
                    failed_operations=0,
                    total_duration_ms=0.0,
                    parameters_processed=[],
                    error_categories={},
                    operation_types={}
                )
            
            successful = sum(1 for log in session_logs if log.success)
            failed = len(session_logs) - successful
            total_duration = sum(log.duration_ms for log in session_logs)
            
            # Get unique parameters processed
            parameters = list(set(log.parameter_name for log in session_logs))
            
            # Error categories
            error_categories = defaultdict(int)
            for log in session_logs:
                if not log.success and log.error_message:
                    category = self._categorize_error(log.error_message)
                    error_categories[category] += 1
            
            # Operation types
            operation_types = defaultdict(int)
            for log in session_logs:
                operation_types[log.operation_type] += 1
            
            return OperationSummary(
                session_id=self.current_session_id,
                start_time=self.session_start_time,
                end_time=datetime.now(),
                total_operations=len(session_logs),
                successful_operations=successful,
                failed_operations=failed,
                total_duration_ms=total_duration,
                parameters_processed=parameters,
                error_categories=dict(error_categories),
                operation_types=dict(operation_types)
            )