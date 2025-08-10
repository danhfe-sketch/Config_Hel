"""
Unit tests for the ProfileErrorHandler class.

Tests error categorization, retry logic, user-friendly messages,
and resolution suggestions for various error scenarios.
"""

import pytest
import time
from unittest.mock import Mock, patch
from services.profile_error_handler import (
    ProfileErrorHandler, ProfileError, DeviceConnectionError, 
    DeviceCommunicationError, ParameterValidationError, ProfileFileError,
    ProfileErrorCategory, ProfileErrorSeverity, ErrorHandlingResult
)
from models.operation_result import OperationType, ProfileOperationResult, ParameterOperationResult
from models.validation_result import ValidationResult


class TestProfileErrorHandler:
    """Test cases for ProfileErrorHandler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ProfileErrorHandler(max_retries=3, base_delay=0.1, max_delay=1.0)
    
    def test_initialization(self):
        """Test ProfileErrorHandler initialization."""
        handler = ProfileErrorHandler(max_retries=5, base_delay=2.0, max_delay=60.0)
        
        assert handler.max_retries == 5
        assert handler.base_delay == 2.0
        assert handler.max_delay == 60.0
        assert len(handler.retry_counts) == 0
        assert len(handler.device_error_patterns) > 0
    
    def test_categorize_device_connection_error(self):
        """Test categorization of device connection errors."""
        # Test various connection error patterns
        connection_errors = [
            Exception("COM port access denied"),
            Exception("Serial port not found"),
            Exception("USB device not found"),
            Exception("Permission denied on /dev/ttyUSB0")
        ]
        
        for error in connection_errors:
            category = self.error_handler._categorize_error(error)
            assert category == ProfileErrorCategory.DEVICE_CONNECTION
    
    def test_categorize_device_communication_error(self):
        """Test categorization of device communication errors."""
        # Test various communication error patterns
        comm_errors = [
            Exception("Device timeout"),
            Exception("Serial read error"),
            Exception("Communication failed"),
            Exception("Device is busy")
        ]
        
        for error in comm_errors:
            category = self.error_handler._categorize_error(error)
            assert category == ProfileErrorCategory.DEVICE_COMMUNICATION
    
    def test_categorize_validation_error(self):
        """Test categorization of validation errors."""
        validation_errors = [
            Exception("Invalid parameter format"),
            Exception("Value out of range"),
            Exception("Required field missing"),
            ParameterValidationError("Invalid IP address")
        ]
        
        for error in validation_errors:
            category = self.error_handler._categorize_error(error)
            assert category == ProfileErrorCategory.PARAMETER_VALIDATION
    
    def test_categorize_file_error(self):
        """Test categorization of file errors."""
        file_errors = [
            Exception("File not found"),
            Exception("JSON decode error"),
            Exception("Directory does not exist"),
            ProfileFileError("Cannot write profile file")
        ]
        
        for error in file_errors:
            category = self.error_handler._categorize_error(error)
            assert category == ProfileErrorCategory.PROFILE_FILE
    
    def test_categorize_profile_error_types(self):
        """Test categorization of ProfileError subclasses."""
        errors = [
            DeviceConnectionError("Connection failed"),
            DeviceCommunicationError("Timeout"),
            ParameterValidationError("Invalid value"),
            ProfileFileError("File error")
        ]
        
        expected_categories = [
            ProfileErrorCategory.DEVICE_CONNECTION,
            ProfileErrorCategory.DEVICE_COMMUNICATION,
            ProfileErrorCategory.PARAMETER_VALIDATION,
            ProfileErrorCategory.PROFILE_FILE
        ]
        
        for error, expected_category in zip(errors, expected_categories):
            category = self.error_handler._categorize_error(error)
            assert category == expected_category
    
    def test_determine_severity(self):
        """Test error severity determination."""
        # Test different error categories and their severities
        test_cases = [
            (DeviceConnectionError("Connection failed"), ProfileErrorSeverity.ERROR),  # ProfileError uses its own severity
            (DeviceCommunicationError("Timeout"), ProfileErrorSeverity.ERROR),
            (ParameterValidationError("Invalid value"), ProfileErrorSeverity.ERROR),
            (ProfileFileError("File error"), ProfileErrorSeverity.ERROR),
            (Exception("System error"), ProfileErrorSeverity.CRITICAL)  # SYSTEM_ERROR category
        ]
        
        for error, expected_severity in test_cases:
            category = self.error_handler._categorize_error(error)
            severity = self.error_handler._determine_severity(error, category)
            assert severity == expected_severity, f"Failed for {error}: got {severity}, expected {expected_severity}"
    
    def test_should_retry_error(self):
        """Test retry decision logic."""
        # Test cases: (error, category, attempt, should_retry)
        test_cases = [
            # Communication errors should retry within limits
            (Exception("timeout"), ProfileErrorCategory.DEVICE_COMMUNICATION, 0, True),
            (Exception("device busy"), ProfileErrorCategory.DEVICE_COMMUNICATION, 1, True),
            (Exception("timeout"), ProfileErrorCategory.DEVICE_COMMUNICATION, 3, False),  # Max retries exceeded
            
            # Validation errors should not retry
            (Exception("invalid value"), ProfileErrorCategory.PARAMETER_VALIDATION, 0, False),
            
            # File errors should not retry
            (Exception("file not found"), ProfileErrorCategory.PROFILE_FILE, 0, False),
            
            # Connection errors should not retry (need manual intervention)
            (Exception("port access denied"), ProfileErrorCategory.DEVICE_CONNECTION, 0, False),
            
            # Cancelled operations should not retry
            (Exception("cancelled"), ProfileErrorCategory.OPERATION_CANCELLED, 0, False)
        ]
        
        for error, category, attempt, expected_retry in test_cases:
            should_retry = self.error_handler._should_retry_error(error, category, attempt)
            assert should_retry == expected_retry, f"Failed for {error}, {category}, attempt {attempt}"
    
    def test_calculate_retry_delay(self):
        """Test retry delay calculation with exponential backoff."""
        handler = ProfileErrorHandler(base_delay=1.0, max_delay=10.0)
        
        # Test exponential backoff
        assert handler._calculate_retry_delay(0) == 1.0  # 1.0 * 2^0
        assert handler._calculate_retry_delay(1) == 2.0  # 1.0 * 2^1
        assert handler._calculate_retry_delay(2) == 4.0  # 1.0 * 2^2
        assert handler._calculate_retry_delay(3) == 8.0  # 1.0 * 2^3
        
        # Test max delay cap
        assert handler._calculate_retry_delay(10) == 10.0  # Capped at max_delay
    
    def test_handle_error_basic(self):
        """Test basic error handling."""
        error = Exception("Test error")
        result = self.error_handler.handle_error(error, "test_operation")
        
        assert isinstance(result, ErrorHandlingResult)
        assert result.category == ProfileErrorCategory.SYSTEM_ERROR
        assert result.severity == ProfileErrorSeverity.CRITICAL
        assert "Test error" in result.user_message
        assert "test_operation" in result.technical_message
        assert len(result.suggestions) > 0
    
    def test_handle_error_with_parameter(self):
        """Test error handling with parameter context."""
        error = Exception("Parameter error")
        result = self.error_handler.handle_error(error, "load_from_device", "test_param")
        
        assert "test_param" in result.technical_message
        assert result.context["parameter"] == "test_param"
        assert result.context["operation"] == "load_from_device"
    
    def test_handle_error_retry_logic(self):
        """Test error handling retry logic."""
        # Create a communication error that should retry
        error = Exception("Device timeout")
        
        # First attempt should allow retry
        result1 = self.error_handler.handle_error(error, "test_op", "param1", 0)
        assert result1.should_retry is True
        assert result1.retry_delay > 0
        
        # After max retries, should not retry
        result2 = self.error_handler.handle_error(error, "test_op", "param1", 3)
        assert result2.should_retry is False
        assert result2.retry_delay == 0
    
    def test_handle_device_communication_error_timeout(self):
        """Test handling of device timeout errors."""
        error = Exception("Device communication timeout")
        result = self.error_handler.handle_device_communication_error(
            error, "READ_PARAM", "test_param", 0
        )
        
        assert result.should_retry is True
        assert result.retry_delay > 0
        assert "timeout" in result.user_message.lower()
        assert "retrying" in result.user_message.lower()
        assert result.category == ProfileErrorCategory.DEVICE_COMMUNICATION
        assert result.severity == ProfileErrorSeverity.WARNING
    
    def test_handle_device_communication_error_busy(self):
        """Test handling of device busy errors."""
        error = Exception("Device is busy")
        result = self.error_handler.handle_device_communication_error(
            error, "WRITE_PARAM", "test_param", 0
        )
        
        assert result.should_retry is True
        assert result.retry_delay > 0
        assert "busy" in result.user_message.lower()
        assert result.category == ProfileErrorCategory.DEVICE_COMMUNICATION
        assert result.severity == ProfileErrorSeverity.WARNING
    
    def test_handle_device_communication_error_invalid_response(self):
        """Test handling of invalid response errors."""
        error = Exception("Invalid response from device")
        result = self.error_handler.handle_device_communication_error(
            error, "READ_PARAM", "test_param", 0
        )
        
        assert result.should_retry is False
        assert result.retry_delay == 0
        assert "invalid response" in result.user_message.lower()
        assert result.category == ProfileErrorCategory.DEVICE_COMMUNICATION
        assert result.severity == ProfileErrorSeverity.ERROR
    
    def test_handle_validation_error(self):
        """Test handling of validation errors."""
        validation_result = ValidationResult(is_valid=False)
        validation_result.add_error("Value out of range")
        validation_result.add_error("Invalid format")
        
        result = self.error_handler.handle_validation_error(
            validation_result, "test_param", "invalid_value"
        )
        
        assert result.should_retry is False
        assert result.retry_delay == 0
        assert "test_param" in result.user_message
        assert "Value out of range" in result.user_message
        assert result.category == ProfileErrorCategory.PARAMETER_VALIDATION
        assert result.severity == ProfileErrorSeverity.ERROR
        assert len(result.suggestions) > 0
    
    def test_handle_file_operation_error_permission(self):
        """Test handling of file permission errors."""
        error = PermissionError("Access denied")
        result = self.error_handler.handle_file_operation_error(
            error, "/path/to/profile.json", "write"
        )
        
        assert result.should_retry is False
        assert "Permission denied" in result.user_message
        assert result.category == ProfileErrorCategory.PROFILE_FILE
        assert "permission" in result.suggestions[0].lower()
    
    def test_handle_file_operation_error_not_found(self):
        """Test handling of file not found errors."""
        error = FileNotFoundError("File not found")
        result = self.error_handler.handle_file_operation_error(
            error, "/path/to/profile.json", "read"
        )
        
        assert result.should_retry is False
        assert "File not found" in result.user_message
        assert result.category == ProfileErrorCategory.PROFILE_FILE
        assert any("file path" in suggestion.lower() for suggestion in result.suggestions)
    
    def test_create_operation_result_with_error(self):
        """Test creation of ProfileOperationResult with error."""
        error = Exception("Test operation failed")
        result = self.error_handler.create_operation_result_with_error(
            OperationType.LOAD_FROM_DEVICE, error, {"test_context": "value"}
        )
        
        assert isinstance(result, ProfileOperationResult)
        assert result.success is False
        assert result.operation_type == OperationType.LOAD_FROM_DEVICE
        assert len(result.errors) > 0
        assert "Test operation failed" in result.errors[0]
        assert result.details["test_context"] == "value"
        assert "error_category" in result.details
        assert "suggestions" in result.details
    
    def test_create_parameter_result_with_error(self):
        """Test creation of ParameterOperationResult with error."""
        error = Exception("Parameter operation failed")
        result = self.error_handler.create_parameter_result_with_error(
            "test_param", error, {"test_context": "value"}
        )
        
        assert isinstance(result, ParameterOperationResult)
        assert result.success is False
        assert result.parameter_name == "test_param"
        assert result.error_message is not None  # Just check that there's an error message
    
    def test_retry_count_tracking(self):
        """Test retry count tracking."""
        # Initially no retry counts
        assert self.error_handler.get_retry_count("test_op", "param1") == 0
        
        # Handle error with retry
        error = Exception("Device timeout")
        self.error_handler.handle_error(error, "test_op", "param1", 0)
        
        # Should track retry count
        assert self.error_handler.get_retry_count("test_op", "param1") == 1
        
        # Handle error without retry
        error = Exception("Invalid value")
        self.error_handler.handle_error(error, "test_op", "param2", 0)
        
        # Should not track retry count for non-retryable errors
        assert self.error_handler.get_retry_count("test_op", "param2") == 0
        
        # Reset retry counts
        self.error_handler.reset_retry_counts()
        assert self.error_handler.get_retry_count("test_op", "param1") == 0
    
    def test_create_error_summary(self):
        """Test creation of error summary."""
        errors = [
            Exception("Device timeout"),
            Exception("Invalid parameter value"),
            Exception("File not found"),
            Exception("Another timeout")
        ]
        
        summary = self.error_handler.create_error_summary(errors, "test_operation")
        
        assert summary["total_errors"] == 4
        assert summary["operation_context"] == "test_operation"
        assert len(summary["categories"]) > 0
        assert len(summary["suggestions"]) > 0
        
        # Check that categories are properly counted
        categories = summary["categories"]
        assert any(cat["count"] >= 2 for cat in categories.values())  # Should have multiple timeouts
    
    def test_create_error_summary_empty(self):
        """Test creation of error summary with no errors."""
        summary = self.error_handler.create_error_summary([], "test_operation")
        
        assert summary["total_errors"] == 0
        assert len(summary["categories"]) == 0
        assert len(summary["suggestions"]) == 0
    
    def test_user_message_creation(self):
        """Test creation of user-friendly messages."""
        test_cases = [
            (Exception("Connection failed"), ProfileErrorCategory.DEVICE_CONNECTION, 
             "Cannot connect to device"),
            (Exception("Timeout"), ProfileErrorCategory.DEVICE_COMMUNICATION, 
             "Communication error with device"),
            (Exception("Invalid value"), ProfileErrorCategory.PARAMETER_VALIDATION, 
             "Invalid parameter value"),
            (Exception("File error"), ProfileErrorCategory.PROFILE_FILE, 
             "Profile file error")
        ]
        
        for error, category, expected_text in test_cases:
            message = self.error_handler._create_user_message(error, category, "test_param")
            assert expected_text in message
            assert "test_param" in message
    
    def test_resolution_suggestions(self):
        """Test resolution suggestions for different error categories."""
        test_cases = [
            (ProfileErrorCategory.DEVICE_CONNECTION, ["Check that the LT32 PRO device is connected"]),
            (ProfileErrorCategory.DEVICE_COMMUNICATION, ["Check that the device is powered on"]),
            (ProfileErrorCategory.PARAMETER_VALIDATION, ["Check the parameter value format"]),
            (ProfileErrorCategory.PROFILE_FILE, ["Check file permissions"])
        ]
        
        for category, expected_keywords in test_cases:
            error = Exception("Test error")
            suggestions = self.error_handler._get_resolution_suggestions(error, category, "test_param")
            
            assert len(suggestions) > 0
            assert any(keyword in " ".join(suggestions).lower() for keyword in 
                      [keyword.lower() for keyword in expected_keywords])
    
    @patch('time.sleep')
    def test_retry_delay_execution(self, mock_sleep):
        """Test that retry delays are actually applied."""
        # This test verifies the retry delay mechanism
        # In actual implementation, the delay would be handled by the calling code
        error = Exception("Device timeout")
        result = self.error_handler.handle_device_communication_error(
            error, "READ_PARAM", "test_param", 0
        )
        
        assert result.should_retry is True
        assert result.retry_delay > 0
        
        # The actual sleep would be called by the retry mechanism in the calling code
        # Here we just verify the delay value is calculated correctly
        expected_delay = self.error_handler._calculate_retry_delay(0)
        assert result.retry_delay == expected_delay
    
    def test_profile_error_with_suggestions(self):
        """Test ProfileError with custom suggestions."""
        custom_suggestions = ["Custom suggestion 1", "Custom suggestion 2"]
        error = ParameterValidationError(
            "Custom validation error",
            suggestions=custom_suggestions,
            context={"custom_key": "custom_value"}
        )
        
        result = self.error_handler.handle_error(error, "test_operation")
        
        assert result.suggestions == custom_suggestions
        assert result.category == ProfileErrorCategory.PARAMETER_VALIDATION
        assert "Custom validation error" in result.user_message
    
    def test_logging_integration(self):
        """Test that errors are properly logged."""
        with patch.object(self.error_handler.logger, 'critical') as mock_log:  # Changed to critical since system errors are critical
            error = Exception("Test error for logging")
            self.error_handler.handle_error(error, "test_operation", "test_param")
            
            # Verify that logging was called
            mock_log.assert_called_once()
            log_call_args = mock_log.call_args[0][0]
            assert "test_operation" in log_call_args
            assert "test_param" in log_call_args
            assert "Test error for logging" in log_call_args


class TestProfileErrorClasses:
    """Test cases for ProfileError exception classes."""
    
    def test_profile_error_base(self):
        """Test ProfileError base class."""
        error = ProfileError(
            "Test error",
            ProfileErrorCategory.SYSTEM_ERROR,
            ProfileErrorSeverity.ERROR,
            ["Suggestion 1", "Suggestion 2"],
            {"key": "value"}
        )
        
        assert str(error) == "Test error"
        assert error.category == ProfileErrorCategory.SYSTEM_ERROR
        assert error.severity == ProfileErrorSeverity.ERROR
        assert error.suggestions == ["Suggestion 1", "Suggestion 2"]
        assert error.context == {"key": "value"}
    
    def test_device_connection_error(self):
        """Test DeviceConnectionError class."""
        error = DeviceConnectionError("Connection failed", ["Check connection"])
        
        assert str(error) == "Connection failed"
        assert error.category == ProfileErrorCategory.DEVICE_CONNECTION
        assert error.severity == ProfileErrorSeverity.ERROR
        assert error.suggestions == ["Check connection"]
    
    def test_device_communication_error(self):
        """Test DeviceCommunicationError class."""
        error = DeviceCommunicationError(
            "Communication failed", 
            ProfileErrorSeverity.WARNING,
            ["Check device"]
        )
        
        assert str(error) == "Communication failed"
        assert error.category == ProfileErrorCategory.DEVICE_COMMUNICATION
        assert error.severity == ProfileErrorSeverity.WARNING
        assert error.suggestions == ["Check device"]
    
    def test_parameter_validation_error(self):
        """Test ParameterValidationError class."""
        error = ParameterValidationError("Invalid value", ["Check format"])
        
        assert str(error) == "Invalid value"
        assert error.category == ProfileErrorCategory.PARAMETER_VALIDATION
        assert error.severity == ProfileErrorSeverity.ERROR
        assert error.suggestions == ["Check format"]
    
    def test_profile_file_error(self):
        """Test ProfileFileError class."""
        error = ProfileFileError("File error", ["Check permissions"])
        
        assert str(error) == "File error"
        assert error.category == ProfileErrorCategory.PROFILE_FILE
        assert error.severity == ProfileErrorSeverity.ERROR
        assert error.suggestions == ["Check permissions"]


if __name__ == "__main__":
    pytest.main([__file__])