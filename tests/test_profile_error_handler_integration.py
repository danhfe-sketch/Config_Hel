"""
Integration tests for ProfileErrorHandler with other profile system components.

Tests how the error handler integrates with UniversalProfileManager,
DeviceCommunicationManager, and other services to provide comprehensive
error handling and recovery mechanisms.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from services.profile_error_handler import (
    ProfileErrorHandler, DeviceConnectionError, DeviceCommunicationError,
    ParameterValidationError, ProfileFileError, ProfileErrorCategory
)
from services.universal_profile_manager import UniversalProfileManager
from services.device_communication_manager import DeviceCommunicationManager
from models.operation_result import OperationType, ProfileOperationResult
from models.validation_result import ValidationResult


class TestProfileErrorHandlerIntegration:
    """Integration tests for ProfileErrorHandler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ProfileErrorHandler(max_retries=2, base_delay=0.1)
        self.mock_serial_service = Mock()
        self.mock_spec_parser = Mock()
        
        # Create mock services
        self.device_manager = Mock(spec=DeviceCommunicationManager)
        self.profile_manager = Mock(spec=UniversalProfileManager)
    
    def test_device_communication_error_with_retry(self):
        """Test device communication error handling with retry logic."""
        # Simulate a timeout error that should be retried
        timeout_error = Exception("Device communication timeout")
        
        # First attempt should allow retry
        result1 = self.error_handler.handle_device_communication_error(
            timeout_error, "READ_PARAM", "test_param", 0
        )
        
        assert result1.should_retry is True
        assert result1.retry_delay > 0
        assert "timeout" in result1.user_message.lower()
        assert "retrying" in result1.user_message.lower()
        
        # Second attempt should still allow retry
        result2 = self.error_handler.handle_device_communication_error(
            timeout_error, "READ_PARAM", "test_param", 1
        )
        
        assert result2.should_retry is True
        assert result2.retry_delay > result1.retry_delay  # Exponential backoff
        
        # Third attempt should not allow retry (max retries exceeded)
        result3 = self.error_handler.handle_device_communication_error(
            timeout_error, "READ_PARAM", "test_param", 2
        )
        
        assert result3.should_retry is False
        assert result3.retry_delay == 0
        assert "maximum retries" in result3.user_message.lower()
    
    def test_profile_operation_with_multiple_errors(self):
        """Test handling multiple errors during a profile operation."""
        errors = [
            Exception("Device timeout for param1"),
            Exception("Invalid value for param2"),
            Exception("File permission error"),
            Exception("Device busy for param3")
        ]
        
        # Create error summary
        summary = self.error_handler.create_error_summary(errors, "load_from_device")
        
        assert summary["total_errors"] == 4
        assert summary["operation_context"] == "load_from_device"
        assert len(summary["categories"]) > 0
        assert len(summary["suggestions"]) > 0
        
        # Verify different error categories are represented
        categories = summary["categories"]
        category_names = list(categories.keys())
        
        # Should have communication and validation errors at minimum
        assert any("communication" in cat for cat in category_names)
        assert len(summary["suggestions"]) > 5  # Should have multiple suggestions
    
    def test_validation_error_handling_with_context(self):
        """Test validation error handling with parameter context."""
        validation_result = ValidationResult(is_valid=False)
        validation_result.add_error("IP address format is invalid")
        validation_result.add_error("Port number out of range (1-65535)")
        validation_result.add_warning("Using default timeout value")
        
        result = self.error_handler.handle_validation_error(
            validation_result, "server_config", "192.168.1.999:99999"
        )
        
        assert result.should_retry is False  # Validation errors don't retry
        assert result.category == ProfileErrorCategory.PARAMETER_VALIDATION
        assert "server_config" in result.user_message
        assert "IP address format" in result.user_message
        assert "Port number out of range" in result.user_message
        
        # Check suggestions are relevant to the error
        suggestions_text = " ".join(result.suggestions).lower()
        assert "ip address" in suggestions_text
        assert "port number" in suggestions_text or "range" in suggestions_text
    
    def test_file_operation_error_scenarios(self):
        """Test different file operation error scenarios."""
        test_cases = [
            (PermissionError("Access denied"), "write", "permission"),
            (FileNotFoundError("File not found"), "read", "file path"),
            (OSError("Disk full"), "write", "disk space"),
            (UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"), "read", "encoding")
        ]
        
        for error, operation, expected_suggestion_keyword in test_cases:
            result = self.error_handler.handle_file_operation_error(
                error, "/path/to/profile.json", operation
            )
            
            assert result.should_retry is False
            assert result.category == ProfileErrorCategory.PROFILE_FILE
            assert "/path/to/profile.json" in result.user_message
            
            # Check that appropriate suggestions are provided
            suggestions_text = " ".join(result.suggestions).lower()
            assert expected_suggestion_keyword in suggestions_text
    
    def test_error_recovery_workflow(self):
        """Test a complete error recovery workflow."""
        # Simulate a profile load operation with various errors
        operation_errors = []
        
        # First parameter: timeout (should retry)
        timeout_error = Exception("Device timeout")
        result1 = self.error_handler.handle_device_communication_error(
            timeout_error, "READ_PARAM", "param1", 0
        )
        
        if result1.should_retry:
            # Simulate successful retry
            operation_errors.append(("param1", "timeout", "recovered"))
        
        # Second parameter: validation error (should not retry)
        validation_result = ValidationResult(is_valid=False)
        validation_result.add_error("Invalid format")
        result2 = self.error_handler.handle_validation_error(
            validation_result, "param2", "invalid_value"
        )
        
        operation_errors.append(("param2", "validation", "failed"))
        
        # Third parameter: device busy (should retry)
        busy_error = Exception("Device is busy")
        result3 = self.error_handler.handle_device_communication_error(
            busy_error, "READ_PARAM", "param3", 0
        )
        
        if result3.should_retry:
            operation_errors.append(("param3", "busy", "retry_scheduled"))
        
        # Verify recovery decisions
        assert result1.should_retry is True  # Timeout should retry
        assert result2.should_retry is False  # Validation should not retry
        assert result3.should_retry is True  # Busy should retry
        
        # Verify different retry delays
        assert result3.retry_delay > result1.retry_delay  # Busy errors get longer delay
    
    def test_operation_result_creation_with_errors(self):
        """Test creation of operation results with error information."""
        # Test successful operation result
        success_result = ProfileOperationResult(
            operation_type=OperationType.LOAD_FROM_DEVICE,
            success=True,
            parameters_processed=10,
            parameters_successful=10,
            parameters_failed=0
        )
        
        assert success_result.success is True
        assert success_result.get_success_rate() == 100.0
        
        # Test failed operation result with error handler
        error = DeviceConnectionError("Cannot connect to device")
        failed_result = self.error_handler.create_operation_result_with_error(
            OperationType.SAVE_TO_DEVICE, error, {"port": "COM3"}
        )
        
        assert failed_result.success is False
        assert failed_result.operation_type == OperationType.SAVE_TO_DEVICE
        assert len(failed_result.errors) > 0
        assert "Cannot connect to device" in failed_result.errors[0]
        assert failed_result.details["port"] == "COM3"
        assert "error_category" in failed_result.details
        assert "suggestions" in failed_result.details
    
    def test_retry_count_management(self):
        """Test retry count tracking and management."""
        # Initially no retry counts
        assert self.error_handler.get_retry_count("test_op", "param1") == 0
        
        # Simulate multiple retry attempts
        error = Exception("Device timeout")
        
        for attempt in range(3):
            result = self.error_handler.handle_error(error, "test_op", "param1", attempt)
            
            if result.should_retry:
                expected_count = attempt + 1
                assert self.error_handler.get_retry_count("test_op", "param1") == expected_count
            else:
                # Once retries are exhausted, count should be cleared
                assert self.error_handler.get_retry_count("test_op", "param1") == 0
                break
        
        # Test retry count reset
        self.error_handler.handle_error(error, "test_op", "param2", 0)
        assert self.error_handler.get_retry_count("test_op", "param2") > 0
        
        self.error_handler.reset_retry_counts()
        assert self.error_handler.get_retry_count("test_op", "param2") == 0
    
    def test_error_categorization_accuracy(self):
        """Test accuracy of error categorization for various error types."""
        test_cases = [
            # Connection errors
            (Exception("COM port access denied"), ProfileErrorCategory.DEVICE_CONNECTION),
            (Exception("Serial port not found"), ProfileErrorCategory.DEVICE_CONNECTION),
            (Exception("USB device not found"), ProfileErrorCategory.DEVICE_CONNECTION),
            
            # Communication errors
            (Exception("Device timeout"), ProfileErrorCategory.DEVICE_COMMUNICATION),
            (Exception("Serial read error"), ProfileErrorCategory.DEVICE_COMMUNICATION),
            (Exception("Device is busy"), ProfileErrorCategory.DEVICE_COMMUNICATION),
            
            # Validation errors
            (Exception("Invalid parameter format"), ProfileErrorCategory.PARAMETER_VALIDATION),
            (Exception("Value out of range"), ProfileErrorCategory.PARAMETER_VALIDATION),
            (Exception("Required field missing"), ProfileErrorCategory.PARAMETER_VALIDATION),
            
            # File errors
            (Exception("File not found"), ProfileErrorCategory.PROFILE_FILE),
            (Exception("JSON decode error"), ProfileErrorCategory.PROFILE_FILE),
            (Exception("Directory does not exist"), ProfileErrorCategory.PROFILE_FILE),
            
            # System errors
            (Exception("Memory allocation failed"), ProfileErrorCategory.SYSTEM_ERROR),
            (Exception("Unexpected system error"), ProfileErrorCategory.SYSTEM_ERROR)
        ]
        
        for error, expected_category in test_cases:
            category = self.error_handler._categorize_error(error)
            assert category == expected_category, f"Failed to categorize {error} as {expected_category}"
    
    def test_user_friendly_messages(self):
        """Test that error messages are user-friendly and actionable."""
        test_cases = [
            (DeviceConnectionError("Connection failed"), "connection failed"),
            (DeviceCommunicationError("Timeout"), "timeout"),
            (ParameterValidationError("Invalid value"), "invalid value"),
            (ProfileFileError("File error"), "file error")
        ]
        
        for error, expected_phrase in test_cases:
            result = self.error_handler.handle_error(error, "test_operation", "test_param")
            
            # Check that message contains the error text
            assert expected_phrase in result.user_message.lower()
            
            # Check that suggestions are provided
            assert len(result.suggestions) > 0
            
            # Check that suggestions are actionable (contain action words)
            suggestions_text = " ".join(result.suggestions).lower()
            action_words = ["check", "verify", "try", "ensure", "restart", "update"]
            assert any(word in suggestions_text for word in action_words)
    
    @patch('time.sleep')
    def test_retry_mechanism_integration(self, mock_sleep):
        """Test integration with retry mechanisms."""
        # This test demonstrates how the error handler would be used
        # in a real retry loop
        
        max_attempts = 3
        error = Exception("Device timeout")
        
        for attempt in range(max_attempts):
            result = self.error_handler.handle_device_communication_error(
                error, "READ_PARAM", "test_param", attempt
            )
            
            if result.should_retry and attempt < max_attempts - 1:
                # In real code, this would be where the delay is applied
                assert result.retry_delay > 0
                # Verify exponential backoff
                expected_delay = self.error_handler._calculate_retry_delay(attempt)
                assert result.retry_delay == expected_delay
            else:
                # Final attempt or non-retryable error
                if attempt >= max_attempts - 1:
                    assert result.should_retry is False
                break
    
    def test_comprehensive_error_reporting(self):
        """Test comprehensive error reporting for debugging."""
        error = DeviceConnectionError(
            "Failed to connect to COM3",
            suggestions=["Check device connection", "Verify COM port"],
            context={"port": "COM3", "baud_rate": 9600}
        )
        
        result = self.error_handler.handle_error(error, "device_connection", "connection_test")
        
        # Verify comprehensive information is captured
        assert result.category == ProfileErrorCategory.DEVICE_CONNECTION
        assert result.user_message == "Failed to connect to COM3"
        assert result.suggestions == ["Check device connection", "Verify COM port"]
        assert "device_connection" in result.technical_message
        assert "connection_test" in result.technical_message
        
        # Verify context is preserved
        assert result.context["operation"] == "device_connection"
        assert result.context["parameter"] == "connection_test"
        assert result.context["error_type"] == "DeviceConnectionError"


if __name__ == "__main__":
    pytest.main([__file__])