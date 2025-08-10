"""
Profile Message Manager for handling operation result notifications with batching and logging.

This module provides a centralized system for managing profile operation messages,
including batching multiple notifications, logging non-critical issues, and providing
translation support for all user-facing messages.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime

from ui.custom_dialogs import CTkMessageBox, show_info, show_warning, show_error
from services.i18n_service import I18nService


class MessageType(Enum):
    """Types of messages that can be handled by the message manager."""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


class MessagePriority(Enum):
    """Priority levels for messages."""
    CRITICAL = "critical"      # Show immediately in dialog
    NORMAL = "normal"         # Batch with other messages
    LOW = "low"              # Log only, no dialog


@dataclass
class ProfileMessage:
    """Represents a single profile operation message."""
    message_type: MessageType
    priority: MessagePriority
    title_key: str
    message_key: str
    details: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    operation_context: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchedMessages:
    """Container for batched messages to be shown in a single dialog."""
    operation_type: str
    messages: List[ProfileMessage] = field(default_factory=list)
    success_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    
    def add_message(self, message: ProfileMessage):
        """Add a message to the batch."""
        self.messages.append(message)
        if message.message_type == MessageType.SUCCESS:
            self.success_count += 1
        elif message.message_type == MessageType.WARNING:
            self.warning_count += 1
        elif message.message_type == MessageType.ERROR:
            self.error_count += 1


class ProfileMessageManager:
    """
    Manages profile operation messages with batching, logging, and translation support.
    
    Features:
    - Message batching to combine multiple notifications
    - Logging system for non-critical issues
    - Translation support for all messages
    - Single result dialog per operation
    - Thread-safe operation
    """
    
    def __init__(self, parent_widget=None, i18n_service: Optional[I18nService] = None):
        """
        Initialize the ProfileMessageManager.
        
        Args:
            parent_widget: Parent widget for dialogs
            i18n_service: Translation service instance
        """
        self.parent_widget = parent_widget
        self.i18n_service = i18n_service or I18nService()
        
        # Setup logging
        self._setup_logging()
        
        # Message batching
        self._message_batches: Dict[str, BatchedMessages] = {}
        self._batch_lock = threading.Lock()
        self._batch_timeout = 2.0  # seconds to wait before showing batched messages
        self._batch_timers: Dict[str, threading.Timer] = {}
        
        # Operation tracking
        self._active_operations: Dict[str, str] = {}
        
        # Translation keys
        self._register_translation_keys()
    
    def _setup_logging(self):
        """Setup logging for profile messages."""
        # Create logger for profile messages
        self.logger = logging.getLogger('profile_messages')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler if it doesn't exist
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/profile_messages.log', encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _register_translation_keys(self):
        """Register translation keys used by the message manager."""
        # This would typically be done by updating the translation files
        # For now, we'll define the keys that should be available
        self.translation_keys = {
            # Dialog titles
            'profile_operation_success': 'Operation Successful',
            'profile_operation_warning': 'Operation Warning',
            'profile_operation_error': 'Operation Error',
            'profile_operation_info': 'Operation Information',
            'profile_batch_results': 'Operation Results',
            
            # Operation types
            'load_from_device': 'Load from Device',
            'load_to_device': 'Load to Device',
            'load_to_ui': 'Load to UI',
            'save_from_ui': 'Save from UI',
            
            # Common messages
            'operation_completed_successfully': 'Operation completed successfully',
            'operation_completed_with_warnings': 'Operation completed with {warning_count} warnings',
            'operation_failed': 'Operation failed',
            'multiple_issues_detected': 'Multiple issues detected during operation',
            'see_details_below': 'See details below:',
            'non_critical_issues_logged': 'Non-critical issues have been logged',
            
            # Batch summary
            'batch_summary': 'Summary: {success_count} successful, {warning_count} warnings, {error_count} errors',
            'batch_details': 'Details:',
            
            # Buttons
            'ok': 'OK',
            'close': 'Close',
            'view_logs': 'View Logs',
            
            # Parameter-specific messages
            'parameter_processed': 'Parameter {parameter_name} processed',
            'parameter_failed': 'Failed to process parameter {parameter_name}',
            'parameter_warning': 'Warning for parameter {parameter_name}: {details}',
            'invalid_parameter_value': 'Invalid value for parameter {parameter_name}',
            'parameter_not_found': 'Parameter {parameter_name} not found',
            
            # File operations
            'profile_saved_successfully': 'Profile saved successfully to {file_path}',
            'profile_loaded_successfully': 'Profile loaded successfully from {file_path}',
            'file_not_found': 'File not found: {file_path}',
            'file_permission_error': 'Permission denied accessing file: {file_path}',
            'invalid_profile_format': 'Invalid profile format in file: {file_path}',
            
            # Device operations
            'device_connected': 'Device connected successfully',
            'device_disconnected': 'Device disconnected',
            'device_communication_error': 'Communication error with device',
            'device_timeout': 'Device operation timed out',
            'device_parameter_sent': 'Parameter sent to device: {parameter_name}',
            'device_parameter_received': 'Parameter received from device: {parameter_name}',
        }
    
    def start_operation(self, operation_id: str, operation_type: str):
        """
        Start tracking a new profile operation.
        
        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of operation (load_from_device, save_from_ui, etc.)
        """
        with self._batch_lock:
            self._active_operations[operation_id] = operation_type
            if operation_id not in self._message_batches:
                self._message_batches[operation_id] = BatchedMessages(operation_type)
    
    def add_message(self, operation_id: str, message_type: MessageType, 
                   title_key: str, message_key: str, details: str = "",
                   priority: MessagePriority = MessagePriority.NORMAL,
                   parameters: Optional[Dict[str, Any]] = None):
        """
        Add a message to the specified operation.
        
        Args:
            operation_id: Operation identifier
            message_type: Type of message (success, warning, error, info)
            title_key: Translation key for dialog title
            message_key: Translation key for message text
            details: Additional details for the message
            priority: Message priority level
            parameters: Parameters for message formatting
        """
        message = ProfileMessage(
            message_type=message_type,
            priority=priority,
            title_key=title_key,
            message_key=message_key,
            details=details,
            operation_context=self._active_operations.get(operation_id, "unknown"),
            parameters=parameters or {}
        )
        
        # Log the message
        self._log_message(message)
        
        # Handle based on priority
        if priority == MessagePriority.CRITICAL:
            # Show immediately
            self._show_single_message(message)
        elif priority == MessagePriority.LOW:
            # Log only, don't add to batch
            pass
        else:
            # Add to batch
            with self._batch_lock:
                if operation_id not in self._message_batches:
                    self._message_batches[operation_id] = BatchedMessages(
                        self._active_operations.get(operation_id, "unknown")
                    )
                
                self._message_batches[operation_id].add_message(message)
                
                # Reset batch timer
                if operation_id in self._batch_timers:
                    self._batch_timers[operation_id].cancel()
                
                # Don't auto-show batches, wait for complete_operation
    
    def complete_operation(self, operation_id: str, show_results: bool = True):
        """
        Complete an operation and show batched results.
        
        Args:
            operation_id: Operation identifier
            show_results: Whether to show the results dialog
        """
        with self._batch_lock:
            # Cancel any pending timer
            if operation_id in self._batch_timers:
                self._batch_timers[operation_id].cancel()
                del self._batch_timers[operation_id]
            
            # Show batched messages if requested
            if show_results and operation_id in self._message_batches:
                batch = self._message_batches[operation_id]
                if batch.messages:
                    self._show_batched_messages(batch)
            
            # Clean up
            if operation_id in self._message_batches:
                del self._message_batches[operation_id]
            if operation_id in self._active_operations:
                del self._active_operations[operation_id]
    
    def log_non_critical_issue(self, operation_id: str, issue: str, details: str = ""):
        """
        Log a non-critical issue without showing a dialog.
        
        Args:
            operation_id: Operation identifier
            issue: Issue description
            details: Additional details
        """
        self.add_message(
            operation_id=operation_id,
            message_type=MessageType.WARNING,
            title_key="non_critical_issue",
            message_key="non_critical_issues_logged",
            details=f"{issue}. {details}".strip(),
            priority=MessagePriority.LOW
        )
    
    def show_operation_result(self, operation_id: str, success: bool, 
                            operation_type: str, details: str = ""):
        """
        Show a single operation result dialog.
        
        Args:
            operation_id: Operation identifier
            success: Whether the operation was successful
            operation_type: Type of operation
            details: Additional details
        """
        if success:
            message_type = MessageType.SUCCESS
            title_key = "profile_operation_success"
            message_key = "operation_completed_successfully"
        else:
            message_type = MessageType.ERROR
            title_key = "profile_operation_error"
            message_key = "operation_failed"
        
        self.add_message(
            operation_id=operation_id,
            message_type=message_type,
            title_key=title_key,
            message_key=message_key,
            details=details,
            priority=MessagePriority.CRITICAL,
            parameters={"operation_type": operation_type}
        )
    
    def _log_message(self, message: ProfileMessage):
        """Log a message to the file system."""
        log_level = {
            MessageType.SUCCESS: logging.INFO,
            MessageType.INFO: logging.INFO,
            MessageType.WARNING: logging.WARNING,
            MessageType.ERROR: logging.ERROR
        }.get(message.message_type, logging.INFO)
        
        # Format log message
        translated_message = self._get_translated_text(message.message_key, message.parameters)
        log_text = f"[{message.operation_context}] {translated_message}"
        if message.details:
            log_text += f" - {message.details}"
        
        self.logger.log(log_level, log_text)
    
    def _show_single_message(self, message: ProfileMessage):
        """Show a single message dialog."""
        if not self.parent_widget:
            return
        
        title = self._get_translated_text(message.title_key)
        text = self._get_translated_text(message.message_key, message.parameters)
        
        if message.details:
            text += f"\n\n{message.details}"
        
        # Show appropriate dialog based on message type
        if message.message_type == MessageType.ERROR:
            show_error(self.parent_widget, title, text)
        elif message.message_type == MessageType.WARNING:
            show_warning(self.parent_widget, title, text)
        else:
            show_info(self.parent_widget, title, text)
    
    def _show_batched_messages(self, batch: BatchedMessages):
        """Show a dialog with batched messages."""
        if not self.parent_widget or not batch.messages:
            return
        
        # Determine overall result type
        if batch.error_count > 0:
            dialog_type = MessageType.ERROR
            title_key = "profile_operation_error"
        elif batch.warning_count > 0:
            dialog_type = MessageType.WARNING
            title_key = "profile_operation_warning"
        else:
            dialog_type = MessageType.SUCCESS
            title_key = "profile_operation_success"
        
        # Build message content
        title = self._get_translated_text(title_key)
        
        # Summary line
        summary = self._get_translated_text("batch_summary", {
            "success_count": batch.success_count,
            "warning_count": batch.warning_count,
            "error_count": batch.error_count
        })
        
        # Details
        details_lines = []
        if len(batch.messages) > 1:
            details_lines.append(self._get_translated_text("batch_details"))
            
            for i, msg in enumerate(batch.messages, 1):
                msg_text = self._get_translated_text(msg.message_key, msg.parameters)
                if msg.details:
                    msg_text += f" - {msg.details}"
                details_lines.append(f"{i}. {msg_text}")
        else:
            # Single message
            msg = batch.messages[0]
            msg_text = self._get_translated_text(msg.message_key, msg.parameters)
            if msg.details:
                msg_text += f"\n\n{msg.details}"
            details_lines.append(msg_text)
        
        # Combine summary and details
        full_message = summary
        if details_lines:
            full_message += "\n\n" + "\n".join(details_lines)
        
        # Show dialog
        if dialog_type == MessageType.ERROR:
            show_error(self.parent_widget, title, full_message)
        elif dialog_type == MessageType.WARNING:
            show_warning(self.parent_widget, title, full_message)
        else:
            show_info(self.parent_widget, title, full_message)
    
    def _get_translated_text(self, key: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Get translated text for a key with parameter substitution.
        
        Args:
            key: Translation key
            parameters: Parameters for string formatting
            
        Returns:
            Translated and formatted text
        """
        # Try to get translation from i18n service
        text = self.i18n_service.get(key)
        
        # If not found, try fallback keys
        if text == f"_{key}_":
            text = self.translation_keys.get(key, key)
        
        # Apply parameter substitution
        if parameters:
            try:
                text = text.format(**parameters)
            except (KeyError, ValueError) as e:
                # Log formatting error but don't crash
                self.logger.warning(f"Failed to format message '{key}' with parameters {parameters}: {e}")
        
        return text
    
    def set_parent_widget(self, parent_widget):
        """Set the parent widget for dialogs."""
        self.parent_widget = parent_widget
    
    def get_operation_summary(self, operation_id: str) -> Optional[Dict[str, int]]:
        """
        Get summary of messages for an operation.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            Dictionary with message counts or None if operation not found
        """
        with self._batch_lock:
            if operation_id in self._message_batches:
                batch = self._message_batches[operation_id]
                return {
                    "success": batch.success_count,
                    "warning": batch.warning_count,
                    "error": batch.error_count,
                    "total": len(batch.messages)
                }
        return None
    
    def clear_operation(self, operation_id: str):
        """Clear all messages for an operation without showing results."""
        with self._batch_lock:
            if operation_id in self._batch_timers:
                self._batch_timers[operation_id].cancel()
                del self._batch_timers[operation_id]
            
            if operation_id in self._message_batches:
                del self._message_batches[operation_id]
            if operation_id in self._active_operations:
                del self._active_operations[operation_id]