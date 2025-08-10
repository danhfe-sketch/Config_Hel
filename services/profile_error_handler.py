"""
Profile Error Handler for the LT32 PRO Universal Profile System.

This module provides centralized error management for all profile operations,
including user-friendly error messages, resolution suggestions, and retry logic
for transient device communication errors.
"""

import time
import logging
from typing import Dict, Optional, List, Callable, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from models.operation_result import ProfileOperationResult, ParameterOperationResult, OperationType
from models.validation_result import ValidationResult


class ProfileErrorCategory(Enum):
    """Categories of errors that can occur during profile operations."""
    DEVICE_CONNECTION = "device_connection"
    DEVICE_COMMUNICATION = "device_communication"
    PARAMETER_VALIDATION = "parameter_validation"
    PROFILE_FILE = "profile_file"
    PROFILE_FORMAT = "profile_format"
    PARAMETER_SPECIFICATION = "parameter_specification"
    OPERATION_CANCELLED = "operation_cancelled"
    SYSTEM_ERROR = "system_error"


class ProfileErrorSeverity(Enum):
    """Severity levels for profile errors."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorHandlingResult:
    """Result of error handling operation."""
    should_retry: bool
    retry_delay: float
    user_message: str
    technical_message: str
    suggestions: List[str]
    category: ProfileErrorCategory
    severity: ProfileErrorSeverity
    context: Dict[str, Any]


class ProfileError(Exception):
    """Base exception for profile-specific errors."""
    
    def __init__(self, message: str, category: ProfileErrorCategory, 
                 severity: ProfileErrorSeverity = ProfileErrorSeverity.ERROR,
                 suggestions: Optional[List[str]] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.suggestions = suggestions or []
        self.context = context or {}


class DeviceConnectionError(ProfileError):
    """Error related to device connection issues."""
    
    def __init__(self, message: str, suggestions: Optional[List[str]] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ProfileErrorCategory.DEVICE_CONNECTION, 
                        ProfileErrorSeverity.ERROR, suggestions, context)


class DeviceCommunicationError(ProfileError):
    """Error related to device communication issues."""
    
    def __init__(self, message: str, severity: ProfileErrorSeverity = ProfileErrorSeverity.ERROR,
                 suggestions: Optional[List[str]] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ProfileErrorCategory.DEVICE_COMMUNICATION, 
                        severity, suggestions, context)


class ParameterValidationError(ProfileError):
    """Error related to parameter validation issues."""
    
    def __init__(self, message: str, suggestions: Optional[List[str]] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ProfileErrorCategory.PARAMETER_VALIDATION, 
                        ProfileErrorSeverity.ERROR, suggestions, context)


class ProfileFileError(ProfileError):
    """Error related to profile file operations."""
    
    def __init__(self, message: str, suggestions: Optional[List[str]] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ProfileErrorCategory.PROFILE_FILE, 
                        ProfileErrorSeverity.ERROR, suggestions, context)


class ProfileErrorHandler:
    """
    Centralized error handler for profile operations.
    
    Provides error categorization, retry logic with exponential backoff,
    user-friendly error messages, and resolution suggestions.
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 30.0):
        """
        Initialize the profile error handler.
        
        Args:
            max_retries: Maximum number of retry attempts for transient errors
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay between retries (seconds)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.logger = logging.getLogger(__name__)
        
        # Track retry attempts for different operations
        self.retry_counts: Dict[str, int] = {}
        
        # Device error patterns and their meanings
        self.device_error_patterns = {
            "timeout": "Device communication timeout",
            "error": "Device command error",
            "invalid": "Invalid command format",
            "busy": "Device is busy",
            "nodata": "No data available",
            "fail": "Command execution failed",
            "unknown": "Unknown device response"
        }
    
    def handle_error(self, error: Exception, operation_context: str,
                    parameter_name: Optional[str] = None,
                    attempt_number: int = 0) -> ErrorHandlingResult:
        """
        Handle an error with appropriate categorization and response.
        
        Args:
            error: The exception that occurred
            operation_context: Context of the operation (e.g., "load_from_device")
            parameter_name: Name of parameter being processed (if applicable)
            attempt_number: Current attempt number (0-based)
            
        Returns:
            ErrorHandlingResult with handling decision and user messages
        """
        category = self._categorize_error(error)
        severity = self._determine_severity(error, category)
        
        # Create context key for retry tracking
        context_key = f"{operation_context}:{parameter_name or 'general'}"
        
        # Determine if we should retry
        should_retry = self._should_retry_error(error, category, attempt_number)
        retry_delay = self._calculate_retry_delay(attempt_number) if should_retry else 0.0
        
        # Generate user-friendly messages
        user_message = self._create_user_message(error, category, parameter_name)
        technical_message = self._create_technical_message(error, operation_context, parameter_name)
        suggestions = self._get_resolution_suggestions(error, category, parameter_name)
        
        # Log the error
        self._log_error(error, category, severity, operation_context, parameter_name, attempt_number)
        
        # Update retry count
        if should_retry:
            self.retry_counts[context_key] = attempt_number + 1
        else:
            self.retry_counts.pop(context_key, None)
        
        return ErrorHandlingResult(
            should_retry=should_retry,
            retry_delay=retry_delay,
            user_message=user_message,
            technical_message=technical_message,
            suggestions=suggestions,
            category=category,
            severity=severity,
            context={
                "operation": operation_context,
                "parameter": parameter_name,
                "attempt": attempt_number,
                "error_type": type(error).__name__
            }
        )
    
    def handle_device_communication_error(self, error: Exception, command: str,
                                        parameter_name: str, attempt: int) -> ErrorHandlingResult:
        """
        Handle device communication errors with specific retry logic.
        
        Args:
            error: The communication error
            command: The device command that failed
            parameter_name: Name of the parameter being processed
            attempt: Current attempt number
            
        Returns:
            ErrorHandlingResult with communication-specific handling
        """
        context = {
            "command": command,
            "parameter": parameter_name,
            "attempt": attempt
        }
        
        # Check for specific communication error patterns
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            return self._handle_timeout_error(error, command, parameter_name, attempt, context)
        elif "busy" in error_str or "device is busy" in error_str:
            return self._handle_busy_error(error, command, parameter_name, attempt, context)
        elif "invalid response" in error_str or "malformed" in error_str:
            return self._handle_invalid_response_error(error, command, parameter_name, attempt, context)
        else:
            return self._handle_generic_communication_error(error, command, parameter_name, attempt, context)
    
    def handle_validation_error(self, validation_result: ValidationResult,
                              parameter_name: str, value: Any) -> ErrorHandlingResult:
        """
        Handle parameter validation errors.
        
        Args:
            validation_result: The validation result with errors
            parameter_name: Name of the parameter that failed validation
            value: The value that failed validation
            
        Returns:
            ErrorHandlingResult for validation error
        """
        # Create a validation error with detailed information
        error_messages = "; ".join(validation_result.errors)
        error = ParameterValidationError(
            f"Validation failed for parameter '{parameter_name}': {error_messages}",
            context={
                "parameter": parameter_name,
                "value": value,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings
            }
        )
        
        suggestions = [
            f"Check the value format for parameter '{parameter_name}'",
            "Refer to the Parameter UI List for valid values",
            "Use default values if unsure about the correct format"
        ]
        
        # Add specific suggestions based on validation errors
        for error_msg in validation_result.errors:
            if "range" in error_msg.lower():
                suggestions.append("Ensure the value is within the allowed range")
            elif "format" in error_msg.lower():
                suggestions.append("Check the value format (e.g., IP address, number)")
            elif "required" in error_msg.lower():
                suggestions.append("Provide a value for this required parameter")
        
        return ErrorHandlingResult(
            should_retry=False,  # Validation errors don't benefit from retry
            retry_delay=0.0,
            user_message=f"Invalid value for '{parameter_name}': {error_messages}",
            technical_message=f"Parameter validation failed: {error_messages}",
            suggestions=suggestions,
            category=ProfileErrorCategory.PARAMETER_VALIDATION,
            severity=ProfileErrorSeverity.ERROR,
            context=error.context
        )
    
    def handle_file_operation_error(self, error: Exception, file_path: str,
                                  operation: str) -> ErrorHandlingResult:
        """
        Handle profile file operation errors.
        
        Args:
            error: The file operation error
            file_path: Path to the file that caused the error
            operation: Type of operation (read/write)
            
        Returns:
            ErrorHandlingResult for file operation error
        """
        error_str = str(error).lower()
        suggestions = []
        
        if "permission" in error_str or "access" in error_str:
            suggestions.extend([
                "Check file permissions and access rights",
                "Ensure the file is not open in another application",
                "Try running the application as administrator",
                "Choose a different file location"
            ])
        elif "not found" in error_str or "no such file" in error_str:
            if operation == "read":
                suggestions.extend([
                    "Verify the file path is correct",
                    "Check if the file exists",
                    "Browse to select the correct file"
                ])
            else:
                suggestions.extend([
                    "Verify the directory exists",
                    "Create the directory if it doesn't exist",
                    "Choose a different save location"
                ])
        elif "disk" in error_str or "space" in error_str:
            suggestions.extend([
                "Free up disk space",
                "Choose a different drive or location",
                "Delete unnecessary files"
            ])
        else:
            suggestions.extend([
                "Check file format and encoding",
                "Verify file is not corrupted",
                "Try a different file location"
            ])
        
        user_message = f"File {operation} error: {file_path}"
        if "permission" in error_str or "access" in error_str:
            user_message += " (Permission denied)"
        elif "not found" in error_str:
            user_message += " (File not found)"
        
        return ErrorHandlingResult(
            should_retry=False,  # File errors typically don't benefit from retry
            retry_delay=0.0,
            user_message=user_message,
            technical_message=f"File {operation} failed for {file_path}: {error}",
            suggestions=suggestions,
            category=ProfileErrorCategory.PROFILE_FILE,
            severity=ProfileErrorSeverity.ERROR,
            context={
                "file_path": file_path,
                "operation": operation,
                "error_type": type(error).__name__
            }
        )
    
    def create_operation_result_with_error(self, operation_type: OperationType,
                                         error: Exception,
                                         context: Optional[Dict[str, Any]] = None) -> ProfileOperationResult:
        """
        Create a ProfileOperationResult for a failed operation.
        
        Args:
            operation_type: Type of operation that failed
            error: The error that occurred
            context: Additional context information
            
        Returns:
            ProfileOperationResult with error information
        """
        error_handling = self.handle_error(error, operation_type.value)
        
        result = ProfileOperationResult(
            operation_type=operation_type,
            success=False
        )
        
        result.add_error(error_handling.user_message)
        
        # Add technical details if available
        if context:
            for key, value in context.items():
                result.add_detail(key, value)
        
        result.add_detail("error_category", error_handling.category.value)
        result.add_detail("error_severity", error_handling.severity.value)
        result.add_detail("suggestions", error_handling.suggestions)
        
        return result
    
    def create_parameter_result_with_error(self, parameter_name: str, error: Exception,
                                         context: Optional[Dict[str, Any]] = None) -> ParameterOperationResult:
        """
        Create a ParameterOperationResult for a failed parameter operation.
        
        Args:
            parameter_name: Name of the parameter that failed
            error: The error that occurred
            context: Additional context information
            
        Returns:
            ParameterOperationResult with error information
        """
        error_handling = self.handle_error(error, "parameter_operation", parameter_name)
        
        return ParameterOperationResult(
            parameter_name=parameter_name,
            success=False,
            error_message=error_handling.user_message
        )
    
    def _categorize_error(self, error: Exception) -> ProfileErrorCategory:
        """Categorize an error based on its type and message."""
        if isinstance(error, ProfileError):
            return error.category
        
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Device connection errors
        if any(keyword in error_str for keyword in [
            "connection", "port", "access denied", "permission denied", 
            "device not found", "no such file or directory"
        ]) and any(keyword in error_str for keyword in ["com", "serial", "usb"]):
            return ProfileErrorCategory.DEVICE_CONNECTION
        
        # Device communication errors
        elif any(keyword in error_str for keyword in [
            "timeout", "read", "write", "serial", "communication", "busy", "device"
        ]):
            return ProfileErrorCategory.DEVICE_COMMUNICATION
        
        # Parameter validation errors
        elif any(keyword in error_str for keyword in [
            "validation", "invalid", "format", "range", "required"
        ]) or "validation" in error_type:
            return ProfileErrorCategory.PARAMETER_VALIDATION
        
        # Profile file errors
        elif any(keyword in error_str for keyword in [
            "file", "directory", "path", "json", "encoding"
        ]):
            return ProfileErrorCategory.PROFILE_FILE
        
        # Parameter specification errors
        elif any(keyword in error_str for keyword in [
            "specification", "parsing", "markdown"
        ]) and not any(keyword in error_str for keyword in ["validation", "invalid", "format"]):
            return ProfileErrorCategory.PARAMETER_SPECIFICATION
        
        # Operation cancelled
        elif any(keyword in error_str for keyword in [
            "cancelled", "canceled", "interrupted", "stopped"
        ]):
            return ProfileErrorCategory.OPERATION_CANCELLED
        
        # Default to system error
        return ProfileErrorCategory.SYSTEM_ERROR   
 
    def _determine_severity(self, error: Exception, category: ProfileErrorCategory) -> ProfileErrorSeverity:
        """Determine the severity of an error."""
        if isinstance(error, ProfileError):
            return error.severity
        
        # Critical errors that prevent operation
        if category in [ProfileErrorCategory.DEVICE_CONNECTION, ProfileErrorCategory.SYSTEM_ERROR]:
            return ProfileErrorSeverity.CRITICAL
        
        # Errors that affect operation but may be recoverable
        elif category in [ProfileErrorCategory.DEVICE_COMMUNICATION, ProfileErrorCategory.PROFILE_FILE]:
            return ProfileErrorSeverity.ERROR
        
        # Validation errors are typically user-correctable
        elif category == ProfileErrorCategory.PARAMETER_VALIDATION:
            return ProfileErrorSeverity.ERROR  # Changed from WARNING to ERROR
        
        # Default to error
        return ProfileErrorSeverity.ERROR
    
    def _should_retry_error(self, error: Exception, category: ProfileErrorCategory, 
                           attempt: int) -> bool:
        """Determine if an error should be retried."""
        # Don't retry if we've exceeded max attempts
        if attempt >= self.max_retries:
            return False
        
        # Don't retry validation or file errors
        if category in [ProfileErrorCategory.PARAMETER_VALIDATION, 
                       ProfileErrorCategory.PROFILE_FILE,
                       ProfileErrorCategory.PARAMETER_SPECIFICATION]:
            return False
        
        # Don't retry cancelled operations
        if category == ProfileErrorCategory.OPERATION_CANCELLED:
            return False
        
        # Retry communication errors
        if category == ProfileErrorCategory.DEVICE_COMMUNICATION:
            error_str = str(error).lower()
            # Retry timeouts and busy errors
            return any(keyword in error_str for keyword in ["timeout", "busy", "temporary"])
        
        # Don't retry connection errors by default (they need manual intervention)
        if category == ProfileErrorCategory.DEVICE_CONNECTION:
            return False
        
        # Default to not retrying
        return False
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay using exponential backoff."""
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
    
    def _create_user_message(self, error: Exception, category: ProfileErrorCategory,
                           parameter_name: Optional[str] = None) -> str:
        """Create a user-friendly error message."""
        if isinstance(error, ProfileError):
            return str(error)
        
        param_context = f" for parameter '{parameter_name}'" if parameter_name else ""
        
        if category == ProfileErrorCategory.DEVICE_CONNECTION:
            return f"Cannot connect to device{param_context}. Please check your device connection."
        
        elif category == ProfileErrorCategory.DEVICE_COMMUNICATION:
            return f"Communication error with device{param_context}. The device may be busy or not responding."
        
        elif category == ProfileErrorCategory.PARAMETER_VALIDATION:
            return f"Invalid parameter value{param_context}. Please check the value format."
        
        elif category == ProfileErrorCategory.PROFILE_FILE:
            return f"Profile file error{param_context}. Please check file permissions and location."
        
        elif category == ProfileErrorCategory.PARAMETER_SPECIFICATION:
            return f"Parameter specification error{param_context}. The Parameter UI List may be invalid."
        
        elif category == ProfileErrorCategory.OPERATION_CANCELLED:
            return f"Operation was cancelled{param_context}."
        
        else:
            return f"An unexpected error occurred{param_context}: {str(error)}"
    
    def _create_technical_message(self, error: Exception, operation_context: str,
                                parameter_name: Optional[str] = None) -> str:
        """Create a technical error message for logging."""
        param_info = f" (parameter: {parameter_name})" if parameter_name else ""
        return f"Error in {operation_context}{param_info}: {type(error).__name__}: {str(error)}"
    
    def _get_resolution_suggestions(self, error: Exception, category: ProfileErrorCategory,
                                  parameter_name: Optional[str] = None) -> List[str]:
        """Get resolution suggestions based on error category."""
        if isinstance(error, ProfileError) and error.suggestions:
            return error.suggestions
        
        suggestions = []
        
        if category == ProfileErrorCategory.DEVICE_CONNECTION:
            suggestions.extend([
                "Check that the LT32 PRO device is connected via USB",
                "Verify the correct COM port is selected",
                "Ensure no other applications are using the COM port",
                "Try unplugging and reconnecting the device",
                "Check Device Manager for available COM ports",
                "Install or update device drivers if necessary"
            ])
        
        elif category == ProfileErrorCategory.DEVICE_COMMUNICATION:
            suggestions.extend([
                "Check that the device is powered on and responsive",
                "Verify the device is not busy with another operation",
                "Try reducing communication speed or timeout settings",
                "Check for electromagnetic interference",
                "Restart the device and try again",
                "Verify device firmware is compatible"
            ])
        
        elif category == ProfileErrorCategory.PARAMETER_VALIDATION:
            suggestions.extend([
                "Check the parameter value format and range",
                "Refer to the Parameter UI List for valid values",
                "Use default values if unsure about the correct format",
                "Verify IP addresses are in correct format (e.g., 192.168.1.1)",
                "Check that port numbers are within valid range (1-65535)"
            ])
            
            if parameter_name:
                suggestions.append(f"Review the specification for parameter '{parameter_name}'")
        
        elif category == ProfileErrorCategory.PROFILE_FILE:
            suggestions.extend([
                "Check file permissions and access rights",
                "Ensure the file is not open in another application",
                "Verify the file path exists and is accessible",
                "Try saving to a different location",
                "Check available disk space",
                "Verify file format is valid JSON"
            ])
        
        elif category == ProfileErrorCategory.PARAMETER_SPECIFICATION:
            suggestions.extend([
                "Check that the Parameter UI List file exists and is readable",
                "Verify the Parameter UI List format is correct",
                "Update the Parameter UI List if it's outdated",
                "Check for syntax errors in the markdown file"
            ])
        
        elif category == ProfileErrorCategory.OPERATION_CANCELLED:
            suggestions.extend([
                "Restart the operation if needed",
                "Check if the operation was intentionally cancelled",
                "Ensure stable device connection before retrying"
            ])
        
        else:  # SYSTEM_ERROR
            suggestions.extend([
                "Restart the application and try again",
                "Check system resources and available memory",
                "Verify all required files and dependencies are present",
                "Contact support if the problem persists"
            ])
        
        return suggestions
    
    def _log_error(self, error: Exception, category: ProfileErrorCategory,
                  severity: ProfileErrorSeverity, operation_context: str,
                  parameter_name: Optional[str] = None, attempt: int = 0) -> None:
        """Log error with appropriate level based on severity."""
        param_info = f" (parameter: {parameter_name})" if parameter_name else ""
        attempt_info = f" (attempt {attempt + 1})" if attempt > 0 else ""
        
        log_message = f"{operation_context}{param_info}{attempt_info}: {category.value} - {str(error)}"
        
        if severity == ProfileErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif severity == ProfileErrorSeverity.ERROR:
            self.logger.error(log_message)
        elif severity == ProfileErrorSeverity.WARNING:
            self.logger.warning(log_message)
        else:  # INFO
            self.logger.info(log_message)
    
    def _handle_timeout_error(self, error: Exception, command: str, parameter_name: str,
                            attempt: int, context: Dict[str, Any]) -> ErrorHandlingResult:
        """Handle timeout errors with specific retry logic."""
        should_retry = attempt < self.max_retries
        retry_delay = self._calculate_retry_delay(attempt) if should_retry else 0.0
        
        user_message = f"Device timeout while processing '{parameter_name}'. "
        if should_retry:
            user_message += f"Retrying in {retry_delay:.1f} seconds..."
        else:
            user_message += "Maximum retries exceeded."
        
        suggestions = [
            "Check device power and connection stability",
            "Verify the device is not busy with another operation",
            "Try reducing communication speed",
            "Check for electromagnetic interference"
        ]
        
        return ErrorHandlingResult(
            should_retry=should_retry,
            retry_delay=retry_delay,
            user_message=user_message,
            technical_message=f"Timeout for command '{command}' on parameter '{parameter_name}': {error}",
            suggestions=suggestions,
            category=ProfileErrorCategory.DEVICE_COMMUNICATION,
            severity=ProfileErrorSeverity.WARNING if should_retry else ProfileErrorSeverity.ERROR,
            context=context
        )
    
    def _handle_busy_error(self, error: Exception, command: str, parameter_name: str,
                         attempt: int, context: Dict[str, Any]) -> ErrorHandlingResult:
        """Handle device busy errors with backoff."""
        should_retry = attempt < self.max_retries
        # Use longer delay for busy errors
        retry_delay = self._calculate_retry_delay(attempt) * 1.5 if should_retry else 0.0
        
        user_message = f"Device is busy processing '{parameter_name}'. "
        if should_retry:
            user_message += f"Waiting {retry_delay:.1f} seconds before retry..."
        else:
            user_message += "Device remains busy after multiple attempts."
        
        suggestions = [
            "Wait for the device to complete its current operation",
            "Check if another application is communicating with the device",
            "Restart the device if it appears stuck",
            "Reduce the number of concurrent operations"
        ]
        
        return ErrorHandlingResult(
            should_retry=should_retry,
            retry_delay=retry_delay,
            user_message=user_message,
            technical_message=f"Device busy for command '{command}' on parameter '{parameter_name}': {error}",
            suggestions=suggestions,
            category=ProfileErrorCategory.DEVICE_COMMUNICATION,
            severity=ProfileErrorSeverity.WARNING,
            context=context
        )
    
    def _handle_invalid_response_error(self, error: Exception, command: str, parameter_name: str,
                                     attempt: int, context: Dict[str, Any]) -> ErrorHandlingResult:
        """Handle invalid device response errors."""
        # Invalid responses typically don't benefit from retry
        should_retry = False
        retry_delay = 0.0
        
        user_message = f"Invalid response from device for parameter '{parameter_name}'. The device may not support this parameter or the command format is incorrect."
        
        suggestions = [
            "Verify the parameter is supported by your device firmware",
            "Check the Parameter UI List for correct command format",
            "Update device firmware if available",
            "Skip this parameter if it's optional"
        ]
        
        return ErrorHandlingResult(
            should_retry=should_retry,
            retry_delay=retry_delay,
            user_message=user_message,
            technical_message=f"Invalid response for command '{command}' on parameter '{parameter_name}': {error}",
            suggestions=suggestions,
            category=ProfileErrorCategory.DEVICE_COMMUNICATION,
            severity=ProfileErrorSeverity.ERROR,
            context=context
        )
    
    def _handle_generic_communication_error(self, error: Exception, command: str, parameter_name: str,
                                          attempt: int, context: Dict[str, Any]) -> ErrorHandlingResult:
        """Handle generic communication errors."""
        should_retry = attempt < self.max_retries
        retry_delay = self._calculate_retry_delay(attempt) if should_retry else 0.0
        
        user_message = f"Communication error for parameter '{parameter_name}'. "
        if should_retry:
            user_message += f"Retrying in {retry_delay:.1f} seconds..."
        else:
            user_message += "Unable to communicate with device."
        
        suggestions = [
            "Check device connection and power",
            "Verify COM port settings",
            "Restart the device and try again",
            "Check for cable or connection issues"
        ]
        
        return ErrorHandlingResult(
            should_retry=should_retry,
            retry_delay=retry_delay,
            user_message=user_message,
            technical_message=f"Communication error for command '{command}' on parameter '{parameter_name}': {error}",
            suggestions=suggestions,
            category=ProfileErrorCategory.DEVICE_COMMUNICATION,
            severity=ProfileErrorSeverity.ERROR,
            context=context
        )
    
    def reset_retry_counts(self) -> None:
        """Reset all retry counts. Useful when starting a new operation."""
        self.retry_counts.clear()
    
    def get_retry_count(self, operation_context: str, parameter_name: Optional[str] = None) -> int:
        """Get the current retry count for a specific operation/parameter."""
        context_key = f"{operation_context}:{parameter_name or 'general'}"
        return self.retry_counts.get(context_key, 0)
    
    def create_error_summary(self, errors: List[Exception], 
                           operation_context: str) -> Dict[str, Any]:
        """
        Create a summary of multiple errors for reporting.
        
        Args:
            errors: List of errors that occurred
            operation_context: Context of the operation
            
        Returns:
            Dictionary containing error summary
        """
        if not errors:
            return {"total_errors": 0, "categories": {}, "suggestions": []}
        
        categories = {}
        all_suggestions = set()
        
        for error in errors:
            category = self._categorize_error(error)
            category_name = category.value
            
            if category_name not in categories:
                categories[category_name] = {
                    "count": 0,
                    "errors": [],
                    "severity": ProfileErrorSeverity.INFO.value
                }
            
            categories[category_name]["count"] += 1
            categories[category_name]["errors"].append(str(error))
            
            # Update severity to highest level
            error_severity = self._determine_severity(error, category)
            if error_severity.value == "critical":
                categories[category_name]["severity"] = "critical"
            elif error_severity.value == "error" and categories[category_name]["severity"] != "critical":
                categories[category_name]["severity"] = "error"
            elif error_severity.value == "warning" and categories[category_name]["severity"] not in ["critical", "error"]:
                categories[category_name]["severity"] = "warning"
            
            # Collect suggestions
            suggestions = self._get_resolution_suggestions(error, category)
            all_suggestions.update(suggestions)
        
        return {
            "total_errors": len(errors),
            "categories": categories,
            "suggestions": list(all_suggestions),
            "operation_context": operation_context
        }