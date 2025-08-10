"""
Enhanced Profile Error Handler - Comprehensive error management for profile operations.

This module provides centralized error handling for profile operations with:
1. Error categorization (critical, non-critical, user confirmation required)
2. Consistent error management across operations
3. Detailed logging for non-critical issues
4. Single confirmation dialog for user decisions
5. Translation support for all user-facing messages
"""

import logging
import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from pathlib import Path

from services.i18n_service import I18nService
from ui.custom_dialogs import CTkMessageBox, show_info, show_warning, show_error


class ErrorCategory(Enum):
    """Categories of profile-related errors."""
    CRITICAL = "critical"           # Stop operation, show error dialog
    NON_CRITICAL = "non_critical"   # Log only, continue operation
    USER_CONFIRMATION = "user_confirmation"  # Single confirmation dialog


class ErrorType(Enum):
    """Types of errors that can occur during profile operations."""
    # File-related errors
    FILE_NOT_FOUND = "file_not_found"
    FILE_PERMISSION_DENIED = "file_permission_denied"
    FILE_CORRUPTED = "file_corrupted"
    FILE_ACCESS_ERROR = "file_access_error"
    
    # Device-related errors
    DEVICE_CONNECTION_LOST = "device_connection_lost"
    DEVICE_TIMEOUT = "device_timeout"
    DEVICE_COMMUNICATION_ERROR = "device_communication_error"
    DEVICE_BUSY = "device_busy"
    
    # Parameter-related errors
    PARAMETER_VALIDATION_FAILED = "parameter_validation_failed"
    PARAMETER_NOT_FOUND = "parameter_not_found"
    PARAMETER_READ_FAILED = "parameter_read_failed"
    PARAMETER_WRITE_FAILED = "parameter_write_failed"
    
    # Profile format errors
    PROFILE_FORMAT_INVALID = "profile_format_invalid"
    PROFILE_SECTION_MISSING = "profile_section_missing"
    PROFILE_CONVERSION_FAILED = "profile_conversion_failed"
    
    # Operation errors
    OPERATION_CANCELLED = "operation_cancelled"
    OPERATION_TIMEOUT = "operation_timeout"
    OPERATION_FAILED = "operation_failed"
    
    # System errors
    MEMORY_ERROR = "memory_error"
    THREAD_ERROR = "thread_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ProfileOperationContext:
    """Context information for profile operations."""
    operation_type: str  # 'load_from_device', 'load_to_device', 'load_to_ui', 'save_from_ui'
    operation_id: str
    file_path: Optional[str] = None
    parameters: Dict[str, str] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    current_parameter: Optional[str] = None
    progress_callback: Optional[Callable] = None
    completion_callback: Optional[Callable] = None
    cancellation_token: Optional[threading.Event] = None


@dataclass
class ProfileError:
    """Represents a profile operation error."""
    error_type: ErrorType
    category: ErrorCategory
    message: str
    details: str = ""
    context: Optional[ProfileOperationContext] = None
    timestamp: datetime = field(default_factory=datetime.now)
    exception: Optional[Exception] = None
    suggested_actions: List[str] = field(default_factory=list)
    recovery_possible: bool = False


@dataclass
class ErrorSummary:
    """Summary of errors for an operation."""
    operation_id: str
    operation_type: str
    total_errors: int = 0
    critical_errors: int = 0
    non_critical_errors: int = 0
    user_confirmations: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    detailed_errors: List[ProfileError] = field(default_factory=list)
    operation_successful: bool = False
    recovery_actions_taken: int = 0


class ProfileErrorHandler:
    """
    Comprehensive error management for profile operations.
    
    Features:
    - Error categorization (critical, non-critical, user confirmation required)
    - Consistent error management across operations
    - Detailed logging for non-critical issues
    - Single confirmation dialog for user decisions
    - Translation support for all user-facing messages
    """
    
    def __init__(self, parent_widget=None, i18n_service: Optional[I18nService] = None):
        """
        Initialize the ProfileErrorHandler.
        
        Args:
            parent_widget: Parent widget for dialogs
            i18n_service: Translation service instance
        """
        self.parent_widget = parent_widget
        self.i18n_service = i18n_service or I18nService()
        
        # Setup logging
        self._setup_logging()
        
        # Error tracking
        self._operation_errors: Dict[str, List[ProfileError]] = {}
        self._error_lock = threading.Lock()
        
        # Error categorization rules
        self._init_error_categorization()
        
        # Translation keys
        self._register_translation_keys()
        
        # User confirmation cache to avoid duplicate dialogs
        self._confirmation_cache: Dict[str, bool] = {}
        
        self.logger.info("ProfileErrorHandler initialized")
    
    def _setup_logging(self):
        """Setup logging for profile errors."""
        # Create logger for profile errors
        self.logger = logging.getLogger('profile_errors')
        self.logger.setLevel(logging.DEBUG)
        
        # Create file handler if it doesn't exist
        if not self.logger.handlers:
            # Ensure logs directory exists
            Path('logs').mkdir(exist_ok=True)
            
            handler = logging.FileHandler('logs/profile_errors.log', encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _init_error_categorization(self):
        """Initialize error categorization rules."""
        self.error_categories = {
            # Critical errors - stop operation, show dialog
            ErrorType.FILE_NOT_FOUND: ErrorCategory.CRITICAL,
            ErrorType.FILE_PERMISSION_DENIED: ErrorCategory.CRITICAL,
            ErrorType.FILE_CORRUPTED: ErrorCategory.CRITICAL,
            ErrorType.DEVICE_CONNECTION_LOST: ErrorCategory.CRITICAL,
            ErrorType.PROFILE_FORMAT_INVALID: ErrorCategory.CRITICAL,
            ErrorType.MEMORY_ERROR: ErrorCategory.CRITICAL,
            ErrorType.THREAD_ERROR: ErrorCategory.CRITICAL,
            
            # Non-critical errors - log only, continue operation
            ErrorType.PARAMETER_READ_FAILED: ErrorCategory.NON_CRITICAL,
            ErrorType.PARAMETER_NOT_FOUND: ErrorCategory.NON_CRITICAL,
            ErrorType.DEVICE_TIMEOUT: ErrorCategory.NON_CRITICAL,
            ErrorType.PARAMETER_VALIDATION_FAILED: ErrorCategory.NON_CRITICAL,
            
            # User confirmation required
            ErrorType.FILE_ACCESS_ERROR: ErrorCategory.USER_CONFIRMATION,
            ErrorType.DEVICE_BUSY: ErrorCategory.USER_CONFIRMATION,
            ErrorType.OPERATION_TIMEOUT: ErrorCategory.USER_CONFIRMATION,
            ErrorType.PROFILE_CONVERSION_FAILED: ErrorCategory.USER_CONFIRMATION,
            
            # Default category
            ErrorType.UNKNOWN_ERROR: ErrorCategory.CRITICAL,
        }
        
        # Suggested actions for each error type
        self.error_suggestions = {
            ErrorType.FILE_NOT_FOUND: [
                "Check that the file path is correct",
                "Verify the file exists in the specified location",
                "Try browsing for the file manually"
            ],
            ErrorType.FILE_PERMISSION_DENIED: [
                "Run the application as administrator",
                "Check file permissions and ownership",
                "Ensure the file is not open in another application"
            ],
            ErrorType.FILE_CORRUPTED: [
                "Try using a backup copy of the profile",
                "Recreate the profile from device settings",
                "Check if the file was partially downloaded"
            ],
            ErrorType.DEVICE_CONNECTION_LOST: [
                "Check the physical connection to the device",
                "Verify the device is powered on",
                "Try reconnecting to the device"
            ],
            ErrorType.DEVICE_TIMEOUT: [
                "Check if the device is responding",
                "Try increasing the timeout settings",
                "Verify the device is not busy with another operation"
            ],
            ErrorType.PARAMETER_READ_FAILED: [
                "Try reading the parameter individually",
                "Check if the parameter exists on the device",
                "Verify the device connection is stable"
            ],
            ErrorType.PARAMETER_WRITE_FAILED: [
                "Verify the parameter value is valid",
                "Check if the device accepts this parameter",
                "Try writing the parameter individually"
            ],
            ErrorType.PROFILE_FORMAT_INVALID: [
                "Check the profile file format",
                "Try opening the file in a text editor",
                "Use a different profile file"
            ]
        }
    
    def _register_translation_keys(self):
        """Register translation keys for error messages."""
        self.translation_keys = {
            # Error dialog titles
            'critical_error_title': 'Critical Error',
            'operation_error_title': 'Operation Error',
            'confirmation_required_title': 'Confirmation Required',
            'error_summary_title': 'Operation Summary',
            
            # Error messages
            'file_not_found_msg': 'Profile file not found: {file_path}',
            'file_permission_denied_msg': 'Permission denied accessing file: {file_path}',
            'file_corrupted_msg': 'Profile file appears to be corrupted: {file_path}',
            'device_connection_lost_msg': 'Connection to device was lost during operation',
            'device_timeout_msg': 'Device operation timed out for parameter: {parameter}',
            'parameter_read_failed_msg': 'Failed to read parameter: {parameter}',
            'parameter_write_failed_msg': 'Failed to write parameter: {parameter}',
            'profile_format_invalid_msg': 'Invalid profile file format',
            'operation_cancelled_msg': 'Operation was cancelled by user',
            'unknown_error_msg': 'An unexpected error occurred: {details}',
            
            # Confirmation messages
            'continue_with_errors_msg': 'Continue operation despite {error_count} non-critical errors?',
            'retry_failed_operation_msg': 'Operation failed. Would you like to retry?',
            'overwrite_file_msg': 'File already exists. Do you want to overwrite it?',
            'device_busy_retry_msg': 'Device is busy. Would you like to wait and retry?',
            
            # Summary messages
            'operation_completed_msg': 'Operation completed with {error_count} errors and {warning_count} warnings',
            'operation_failed_msg': 'Operation failed due to critical errors',
            'recovery_actions_msg': '{recovery_count} recovery actions were taken',
            
            # Buttons
            'ok': 'OK',
            'cancel': 'Cancel',
            'retry': 'Retry',
            'continue': 'Continue',
            'abort': 'Abort',
            'yes': 'Yes',
            'no': 'No',
            
            # Suggestions
            'suggested_actions': 'Suggested actions:',
            'error_details': 'Error details:',
            'see_logs_for_details': 'See logs for detailed information',
        }
    
    def handle_error(self, error_type: ErrorType, message: str, 
                    context: Optional[ProfileOperationContext] = None,
                    details: str = "", exception: Optional[Exception] = None) -> bool:
        """
        Handle a profile operation error.
        
        Args:
            error_type: Type of error that occurred
            message: Human-readable error message
            context: Operation context information
            details: Additional error details
            exception: Original exception if available
            
        Returns:
            True if operation should continue, False if it should stop
        """
        # Determine error category
        category = self.error_categories.get(error_type, ErrorCategory.CRITICAL)
        
        # Create error object
        error = ProfileError(
            error_type=error_type,
            category=category,
            message=message,
            details=details,
            context=context,
            exception=exception,
            suggested_actions=self.error_suggestions.get(error_type, []),
            recovery_possible=category != ErrorCategory.CRITICAL
        )
        
        # Track the error
        self._track_error(error)
        
        # Handle based on category
        if category == ErrorCategory.CRITICAL:
            return self._handle_critical_error(error)
        elif category == ErrorCategory.NON_CRITICAL:
            return self._handle_non_critical_error(error)
        elif category == ErrorCategory.USER_CONFIRMATION:
            return self._handle_user_confirmation_error(error)
        
        return False
    
    def _track_error(self, error: ProfileError):
        """Track an error for the operation."""
        with self._error_lock:
            operation_id = error.context.operation_id if error.context else "unknown"
            
            if operation_id not in self._operation_errors:
                self._operation_errors[operation_id] = []
            
            self._operation_errors[operation_id].append(error)
    
    def _handle_critical_error(self, error: ProfileError) -> bool:
        """
        Handle a critical error that stops the operation.
        
        Args:
            error: The critical error
            
        Returns:
            False (operation should stop)
        """
        # Log the critical error
        self.logger.error(f"CRITICAL ERROR: {error.message}")
        if error.details:
            self.logger.error(f"Details: {error.details}")
        if error.exception:
            self.logger.error(f"Exception: {str(error.exception)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Show error dialog
        self._show_critical_error_dialog(error)
        
        return False
    
    def _handle_non_critical_error(self, error: ProfileError) -> bool:
        """
        Handle a non-critical error by logging it.
        
        Args:
            error: The non-critical error
            
        Returns:
            True (operation should continue)
        """
        # Log the non-critical error
        self.logger.warning(f"NON-CRITICAL ERROR: {error.message}")
        if error.details:
            self.logger.warning(f"Details: {error.details}")
        
        # Log suggested actions
        if error.suggested_actions:
            self.logger.info(f"Suggested actions: {', '.join(error.suggested_actions)}")
        
        return True
    
    def _handle_user_confirmation_error(self, error: ProfileError) -> bool:
        """
        Handle an error that requires user confirmation.
        
        Args:
            error: The error requiring confirmation
            
        Returns:
            True if user chooses to continue, False otherwise
        """
        # Log the error
        self.logger.warning(f"USER CONFIRMATION REQUIRED: {error.message}")
        if error.details:
            self.logger.warning(f"Details: {error.details}")
        
        # Check confirmation cache to avoid duplicate dialogs
        cache_key = f"{error.error_type.value}_{error.message}"
        if cache_key in self._confirmation_cache:
            return self._confirmation_cache[cache_key]
        
        # Show confirmation dialog
        result = self._show_confirmation_dialog(error)
        
        # Cache the result
        self._confirmation_cache[cache_key] = result
        
        return result
    
    def _show_critical_error_dialog(self, error: ProfileError):
        """Show a critical error dialog."""
        if not self.parent_widget:
            return
        
        title = self._get_translated_text('critical_error_title')
        
        # Get error-specific message
        message_key = f"{error.error_type.value}_msg"
        message = self._get_translated_text(message_key, {
            'file_path': error.context.file_path if error.context else '',
            'parameter': error.context.current_parameter if error.context else '',
            'details': error.details
        })
        
        # Add suggested actions
        full_message = message
        if error.suggested_actions:
            suggestions_title = self._get_translated_text('suggested_actions')
            full_message += f"\n\n{suggestions_title}\n"
            for i, action in enumerate(error.suggested_actions, 1):
                full_message += f"{i}. {action}\n"
        
        # Add details if available
        if error.details:
            details_title = self._get_translated_text('error_details')
            full_message += f"\n{details_title}\n{error.details}"
        
        show_error(self.parent_widget, title, full_message)
    
    def _show_confirmation_dialog(self, error: ProfileError) -> bool:
        """
        Show a confirmation dialog for user decision.
        
        Args:
            error: The error requiring confirmation
            
        Returns:
            True if user confirms to continue, False otherwise
        """
        if not self.parent_widget:
            return False
        
        title = self._get_translated_text('confirmation_required_title')
        
        # Get error-specific confirmation message
        if error.error_type == ErrorType.DEVICE_BUSY:
            message = self._get_translated_text('device_busy_retry_msg')
        elif error.error_type == ErrorType.OPERATION_TIMEOUT:
            message = self._get_translated_text('retry_failed_operation_msg')
        elif error.error_type == ErrorType.FILE_ACCESS_ERROR:
            message = self._get_translated_text('overwrite_file_msg')
        else:
            message = f"{error.message}\n\nDo you want to continue?"
        
        # Add details if available
        if error.details:
            message += f"\n\nDetails: {error.details}"
        
        # Add suggested actions
        if error.suggested_actions:
            suggestions_title = self._get_translated_text('suggested_actions')
            message += f"\n\n{suggestions_title}\n"
            for i, action in enumerate(error.suggested_actions, 1):
                message += f"{i}. {action}\n"
        
        # Show confirmation dialog
        dialog = CTkMessageBox(
            master=self.parent_widget,
            title=title,
            message=message,
            icon="question",
            option_1=self._get_translated_text('yes'),
            option_2=self._get_translated_text('no')
        )
        
        result = dialog.get()
        return result == self._get_translated_text('yes')
    
    def create_error_summary(self, operation_id: str) -> ErrorSummary:
        """
        Create a summary of errors for an operation.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            ErrorSummary with comprehensive error analysis
        """
        with self._error_lock:
            errors = self._operation_errors.get(operation_id, [])
        
        # Count errors by category
        critical_errors = len([e for e in errors if e.category == ErrorCategory.CRITICAL])
        non_critical_errors = len([e for e in errors if e.category == ErrorCategory.NON_CRITICAL])
        user_confirmations = len([e for e in errors if e.category == ErrorCategory.USER_CONFIRMATION])
        
        # Count errors by type
        errors_by_type = {}
        for error in errors:
            error_type = error.error_type.value
            errors_by_type[error_type] = errors_by_type.get(error_type, 0) + 1
        
        # Determine operation success
        operation_successful = critical_errors == 0
        
        # Get operation type
        operation_type = "unknown"
        if errors and errors[0].context:
            operation_type = errors[0].context.operation_type
        
        return ErrorSummary(
            operation_id=operation_id,
            operation_type=operation_type,
            total_errors=len(errors),
            critical_errors=critical_errors,
            non_critical_errors=non_critical_errors,
            user_confirmations=user_confirmations,
            errors_by_type=errors_by_type,
            detailed_errors=errors,
            operation_successful=operation_successful,
            recovery_actions_taken=0  # This would be tracked separately
        )
    
    def show_error_summary(self, operation_id: str):
        """
        Show a summary dialog of all errors for an operation.
        
        Args:
            operation_id: Operation identifier
        """
        if not self.parent_widget:
            return
        
        summary = self.create_error_summary(operation_id)
        
        if summary.total_errors == 0:
            # No errors to show
            return
        
        title = self._get_translated_text('error_summary_title')
        
        # Build summary message
        if summary.operation_successful:
            message = self._get_translated_text('operation_completed_msg', {
                'error_count': summary.non_critical_errors,
                'warning_count': summary.user_confirmations
            })
        else:
            message = self._get_translated_text('operation_failed_msg')
        
        # Add error breakdown
        details_lines = [
            f"Total errors: {summary.total_errors}",
            f"Critical errors: {summary.critical_errors}",
            f"Non-critical errors: {summary.non_critical_errors}",
            f"User confirmations: {summary.user_confirmations}"
        ]
        
        # Add error types breakdown
        if summary.errors_by_type:
            details_lines.append("\nError types:")
            for error_type, count in summary.errors_by_type.items():
                details_lines.append(f"  {error_type.replace('_', ' ').title()}: {count}")
        
        # Add recent errors (last 5)
        if summary.detailed_errors:
            details_lines.append("\nRecent errors:")
            for error in summary.detailed_errors[-5:]:
                timestamp = error.timestamp.strftime("%H:%M:%S")
                details_lines.append(f"  [{timestamp}] {error.message}")
        
        full_message = message + "\n\n" + "\n".join(details_lines)
        
        # Add suggestion to check logs
        full_message += f"\n\n{self._get_translated_text('see_logs_for_details')}"
        
        # Show appropriate dialog based on severity
        if summary.critical_errors > 0:
            show_error(self.parent_widget, title, full_message)
        else:
            show_warning(self.parent_widget, title, full_message)
    
    def clear_operation_errors(self, operation_id: str):
        """Clear all errors for an operation."""
        with self._error_lock:
            if operation_id in self._operation_errors:
                del self._operation_errors[operation_id]
        
        # Clear confirmation cache for this operation
        keys_to_remove = [k for k in self._confirmation_cache.keys() if operation_id in k]
        for key in keys_to_remove:
            del self._confirmation_cache[key]
    
    def log_non_critical_issue(self, issue: str, context: Optional[ProfileOperationContext] = None,
                              details: str = ""):
        """
        Log a non-critical issue without showing a dialog.
        
        Args:
            issue: Issue description
            context: Operation context
            details: Additional details
        """
        # Use a non-critical error type for logging
        self.handle_error(
            error_type=ErrorType.PARAMETER_VALIDATION_FAILED,  # This is categorized as non-critical
            message=issue,
            context=context,
            details=details
        )
    
    def request_user_confirmation(self, message: str, context: Optional[ProfileOperationContext] = None) -> bool:
        """
        Request user confirmation for an operation.
        
        Args:
            message: Confirmation message
            context: Operation context
            
        Returns:
            True if user confirms, False otherwise
        """
        # Use a user confirmation error type
        return self.handle_error(
            error_type=ErrorType.OPERATION_TIMEOUT,  # This is categorized as user confirmation
            message=message,
            context=context
        )
    
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
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get overall error statistics across all operations.
        
        Returns:
            Dictionary with error statistics
        """
        with self._error_lock:
            total_operations = len(self._operation_errors)
            total_errors = sum(len(errors) for errors in self._operation_errors.values())
            
            # Count by category
            critical_count = 0
            non_critical_count = 0
            confirmation_count = 0
            
            # Count by type
            type_counts = {}
            
            for errors in self._operation_errors.values():
                for error in errors:
                    if error.category == ErrorCategory.CRITICAL:
                        critical_count += 1
                    elif error.category == ErrorCategory.NON_CRITICAL:
                        non_critical_count += 1
                    elif error.category == ErrorCategory.USER_CONFIRMATION:
                        confirmation_count += 1
                    
                    error_type = error.error_type.value
                    type_counts[error_type] = type_counts.get(error_type, 0) + 1
            
            return {
                'total_operations': total_operations,
                'total_errors': total_errors,
                'critical_errors': critical_count,
                'non_critical_errors': non_critical_count,
                'user_confirmations': confirmation_count,
                'errors_by_type': type_counts,
                'average_errors_per_operation': total_errors / max(total_operations, 1)
            }