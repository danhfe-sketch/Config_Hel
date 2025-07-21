#!/usr/bin/env python3
"""
Integration test for ConfigurationReaderService error handling with "Checar configuração" button.

This test verifies that the enhanced error handling works correctly when integrated
with the actual configuration reading workflow triggered by the "Checar configuração" button.
"""

import sys
import os
import time
import threading
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.configuration_reader_service import ConfigurationReaderService, ParameterReadResult, ConfigurationReadResult
from services.i18n_service import I18nService


class MockApp:
    """Mock application for testing."""
    
    def __init__(self):
        self.serial_service = Mock()
        self.serial_service.is_connected = True
        self.serial_service.send_command = Mock()
        self.log_frame = Mock()
        self.log_frame.log_message = Mock()
        self.params_frame = Mock()
        self.params_frame.parameter_widgets = {}
        self.connection_frame = Mock()
        self.operation_confirmation_service = Mock()
        self.operation_confirmation_service.create_progress_dialog = Mock(return_value="dialog_id_123")
        self.operation_confirmation_service.update_progress = Mock()
        self.operation_confirmation_service.complete_progress = Mock()
        self.operation_confirmation_service.set_cancel_callback = Mock()
        self.operation_confirmation_service.PROGRESS_TYPE_DETERMINATE = "determinate"
        
        # Track after calls for testing
        self.after_calls = []
        
    def after(self, delay, callback, *args):
        """Mock the after method and track calls."""
        self.after_calls.append((delay, callback, args))
        if callable(callback):
            try:
                callback(*args)
            except Exception as e:
                print(f"Warning: Callback failed: {e}")
    
    def __getattr__(self, name):
        """Return a mock for any missing attributes."""
        return Mock()


def test_complete_failure_scenario():
    """Test complete failure scenario with comprehensive error handling."""
    print("Testing complete failure scenario...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create configuration reader service
    config_reader = ConfigurationReaderService(app, i18n)
    
    # Mock _send_command_and_wait to always return None (timeout)
    config_reader._send_command_and_wait = Mock(return_value=None)
    
    # Track completion callback
    completion_results = []
    def completion_callback(result, error_msg):
        print(f"  Debug: Completion callback called with success={result.success if result else 'None'}")
        completion_results.append((result, error_msg))
    
    # Debug: Check initial state
    print(f"  Debug: Serial service connected: {app.serial_service.is_connected}")
    print(f"  Debug: Has serial service: {hasattr(app, 'serial_service')}")
    
    # Start configuration reading
    config_reader.read_all_configurations(
        completion_callback=completion_callback,
        show_progress_dialog=True
    )
    
    print(f"  Debug: Reading started, is_reading: {config_reader.is_reading}")
    
    # Wait for completion (with timeout)
    timeout = 5.0
    start_time = time.time()
    while len(completion_results) == 0 and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    # Debug output
    print(f"  Debug: Completion results count: {len(completion_results)}")
    print(f"  Debug: Is reading: {config_reader.is_reading}")
    print(f"  Debug: Thread alive: {config_reader.read_thread.is_alive() if config_reader.read_thread else 'No thread'}")
    
    # Force cancellation if thread is still running
    if config_reader.read_thread and config_reader.read_thread.is_alive():
        print("  Debug: Forcing thread cancellation")
        config_reader.cancel_reading()
        config_reader.read_thread.join(timeout=3.0)
        
    # Wait a bit more for any pending callbacks
    time.sleep(0.2)
    
    # Verify results
    assert len(completion_results) == 1, "Should have one completion callback"
    result, error_msg = completion_results[0]
    
    assert not result.success, "Result should indicate failure"
    assert len(result.failed_parameters) > 0, "Should have failed parameters"
    assert len(result.parameters_read) > 0, "Should have parameter read results"
    assert error_msg is not None, "Should have error message"
    assert 'completely' in error_msg.lower(), "Error message should indicate complete failure"
    
    # Verify progress dialog was used
    app.operation_confirmation_service.create_progress_dialog.assert_called_once()
    app.operation_confirmation_service.complete_progress.assert_called_once()
    
    # Verify comprehensive error logging
    log_calls = [call[0][0] for call in app.log_frame.log_message.call_args_list]
    error_logs = [log for log in log_calls if 'ERROR:' in log or 'WARNING:' in log]
    assert len(error_logs) > 0, "Should have error logs"
    
    # Verify troubleshooting guidance was provided
    guidance_logs = [log for log in log_calls if 'Troubleshooting steps:' in log or 'Alternative approaches:' in log]
    assert len(guidance_logs) > 0, "Should provide troubleshooting guidance"
    
    print("  ✓ Complete failure handled with comprehensive error reporting")
    print("  ✓ Progress dialog integration working")
    print("  ✓ Troubleshooting guidance provided")
    print("✓ Complete failure scenario test passed")


def test_partial_failure_scenario():
    """Test partial failure scenario with mixed success/failure results."""
    print("Testing partial failure scenario...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create configuration reader service
    config_reader = ConfigurationReaderService(app, i18n)
    
    # Mock _send_command_and_wait to simulate mixed results
    call_count = 0
    def mock_send_command_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # First few calls succeed, later ones fail
        if call_count <= 3:
            if 'APN#' in args[0]:
                return "APN:internet.provider.com,user,password#"
            elif 'SERVER#' in args[0]:
                return "SERVER:0,192.168.1.100,8080,0#"
            elif 'IMEI' in args[0]:
                return "IMEI:357457040000821"
            else:
                return "OK"
        else:
            return None  # Timeout for later parameters
    
    config_reader._send_command_and_wait = Mock(side_effect=mock_send_command_side_effect)
    
    # Track completion callback
    completion_results = []
    def completion_callback(result, error_msg):
        completion_results.append((result, error_msg))
    
    # Start configuration reading
    config_reader.read_all_configurations(
        completion_callback=completion_callback,
        show_progress_dialog=True
    )
    
    # Wait for completion (with timeout)
    timeout = 5.0
    start_time = time.time()
    while len(completion_results) == 0 and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    # Additional wait to ensure thread completion
    if config_reader.read_thread and config_reader.read_thread.is_alive():
        config_reader.read_thread.join(timeout=2.0)
    
    # Verify results
    assert len(completion_results) == 1, "Should have one completion callback"
    result, error_msg = completion_results[0]
    
    assert result.success, "Result should indicate partial success"
    assert len(result.failed_parameters) > 0, "Should have some failed parameters"
    assert len(result.failed_parameters) < result.total_parameters, "Should have some successful parameters"
    assert error_msg is not None, "Should have error message for partial failure"
    
    # Verify partial failure guidance
    log_calls = [call[0][0] for call in app.log_frame.log_message.call_args_list]
    partial_logs = [log for log in log_calls if 'Partial configuration read completed:' in log]
    assert len(partial_logs) > 0, "Should provide partial failure guidance"
    
    # Verify recommendations were provided
    recommendation_logs = [log for log in log_calls if 'Recommendations:' in log]
    assert len(recommendation_logs) > 0, "Should provide recommendations"
    
    print("  ✓ Partial failure handled with appropriate guidance")
    print("  ✓ Mixed success/failure results processed correctly")
    print("  ✓ Recommendations provided for partial failures")
    print("✓ Partial failure scenario test passed")


def test_retry_logic_integration():
    """Test retry logic integration with actual configuration reading."""
    print("Testing retry logic integration...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create configuration reader service
    config_reader = ConfigurationReaderService(app, i18n)
    
    # Mock _send_command_and_wait to fail first few times then succeed
    call_count = 0
    def mock_send_command_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Fail first 2 attempts, succeed on 3rd
        if call_count <= 2:
            return None  # Timeout
        else:
            if 'APN#' in args[0]:
                return "APN:internet.provider.com,user,password#"
            else:
                return "OK"
    
    config_reader._send_command_and_wait = Mock(side_effect=mock_send_command_side_effect)
    
    # Test single parameter read with retries
    result = config_reader.read_specific_parameter('apn_config', 'ATSMS:APN#', 'get_apn', max_retries=2)
    
    # Verify retry logic worked
    assert call_count == 3, f"Expected 3 calls (1 initial + 2 retries), got {call_count}"
    assert result.success, "Parameter read should succeed after retries"
    
    # Verify retry logging
    log_calls = [call[0][0] for call in app.log_frame.log_message.call_args_list]
    retry_logs = [log for log in log_calls if 'Retrying' in log and 'attempt' in log]
    assert len(retry_logs) >= 2, "Should log retry attempts"
    
    success_logs = [log for log in log_calls if 'Successfully read' in log and 'after' in log and 'attempts' in log]
    assert len(success_logs) >= 1, "Should log successful read after retries"
    
    print("  ✓ Retry logic working correctly")
    print("  ✓ Retry attempts properly logged")
    print("  ✓ Success after retries properly logged")
    print("✓ Retry logic integration test passed")


def test_error_resolution_suggestions_integration():
    """Test error resolution suggestions integration."""
    print("Testing error resolution suggestions integration...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create configuration reader service
    config_reader = ConfigurationReaderService(app, i18n)
    
    # Mock _send_command_and_wait to simulate different error types
    def mock_send_command_side_effect(*args, **kwargs):
        if 'APN#' in args[0]:
            return None  # Timeout error
        elif 'SERVER#' in args[0]:
            return "INVALID_RESPONSE_FORMAT"  # Parse error
        else:
            raise Exception("Connection lost")  # Connection error
    
    config_reader._send_command_and_wait = Mock(side_effect=mock_send_command_side_effect)
    
    # Test different parameter reads to trigger different error types
    test_params = [
        ('apn_config', 'ATSMS:APN#', 'get_apn'),
        ('server_config', 'ATSMS:SERVER#', 'get_server')
    ]
    
    for param_name, command, command_type in test_params:
        result = config_reader.read_specific_parameter(param_name, command, command_type, max_retries=1)
        assert not result.success, f"Parameter {param_name} should fail"
    
    # Verify error resolution suggestions were logged
    log_calls = [call[0][0] for call in app.log_frame.log_message.call_args_list]
    suggestion_logs = [log for log in log_calls if 'Suggestions for resolving' in log]
    assert len(suggestion_logs) > 0, "Should provide error resolution suggestions"
    
    # Verify numbered suggestions were provided
    numbered_suggestions = [log for log in log_calls if log.strip().startswith('INFO:   ') and '. ' in log]
    assert len(numbered_suggestions) > 0, "Should provide numbered suggestions"
    
    print("  ✓ Error resolution suggestions provided for different error types")
    print("  ✓ Suggestions properly formatted and logged")
    print("✓ Error resolution suggestions integration test passed")


def test_progress_dialog_error_handling():
    """Test progress dialog integration with error handling."""
    print("Testing progress dialog error handling...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create configuration reader service
    config_reader = ConfigurationReaderService(app, i18n)
    
    # Mock progress dialog to simulate failure
    app.operation_confirmation_service.create_progress_dialog.side_effect = Exception("Dialog creation failed")
    
    # Mock _send_command_and_wait to return success
    config_reader._send_command_and_wait = Mock(return_value="APN:test,user,pass#")
    
    # Track completion callback
    completion_results = []
    def completion_callback(result, error_msg):
        completion_results.append((result, error_msg))
    
    # Start configuration reading (should handle dialog creation failure gracefully)
    config_reader.read_all_configurations(
        completion_callback=completion_callback,
        show_progress_dialog=True
    )
    
    # Wait for completion (with timeout)
    timeout = 5.0
    start_time = time.time()
    while len(completion_results) == 0 and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    # Additional wait to ensure thread completion
    if config_reader.read_thread and config_reader.read_thread.is_alive():
        config_reader.read_thread.join(timeout=2.0)
    
    # Verify operation completed despite dialog failure
    assert len(completion_results) == 1, "Should complete despite dialog failure"
    result, error_msg = completion_results[0]
    
    # Verify warning about dialog failure was logged
    log_calls = [call[0][0] for call in app.log_frame.log_message.call_args_list]
    dialog_warning_logs = [log for log in log_calls if 'Failed to create progress dialog' in log]
    assert len(dialog_warning_logs) > 0, "Should log dialog creation failure"
    
    print("  ✓ Progress dialog creation failure handled gracefully")
    print("  ✓ Configuration reading continues despite dialog issues")
    print("  ✓ Dialog failure properly logged as warning")
    print("✓ Progress dialog error handling test passed")


def test_cancellation_error_handling():
    """Test error handling during operation cancellation."""
    print("Testing cancellation error handling...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create configuration reader service
    config_reader = ConfigurationReaderService(app, i18n)
    
    # Mock _send_command_and_wait to simulate slow operations
    def slow_command(*args, **kwargs):
        time.sleep(0.1)  # Simulate slow operation
        return "APN:test,user,pass#"
    
    config_reader._send_command_and_wait = Mock(side_effect=slow_command)
    
    # Track completion callback
    completion_results = []
    def completion_callback(result, error_msg):
        completion_results.append((result, error_msg))
    
    # Start configuration reading
    config_reader.read_all_configurations(
        completion_callback=completion_callback,
        show_progress_dialog=False
    )
    
    # Cancel the operation quickly
    time.sleep(0.05)  # Let it start
    config_reader.cancel_reading()
    
    # Wait for completion
    time.sleep(0.3)
    
    # Verify cancellation was handled
    log_calls = [call[0][0] for call in app.log_frame.log_message.call_args_list]
    cancel_logs = [log for log in log_calls if 'canceled' in log.lower()]
    assert len(cancel_logs) > 0, "Should log cancellation"
    
    print("  ✓ Operation cancellation handled correctly")
    print("  ✓ Cancellation properly logged")
    print("✓ Cancellation error handling test passed")


def main():
    """Run all integration tests for error handling."""
    print("=" * 70)
    print("ConfigurationReaderService Error Handling Integration Tests")
    print("=" * 70)
    
    try:
        test_complete_failure_scenario()
        print()
        
        test_partial_failure_scenario()
        print()
        
        test_retry_logic_integration()
        print()
        
        test_error_resolution_suggestions_integration()
        print()
        
        test_progress_dialog_error_handling()
        print()
        
        test_cancellation_error_handling()
        print()
        
        print("=" * 70)
        print("✅ All error handling integration tests passed!")
        print("=" * 70)
        
        print("\nIntegration Test Coverage:")
        print("• Complete failure scenario with comprehensive error reporting")
        print("• Partial failure scenario with mixed success/failure results")
        print("• Retry logic integration with actual configuration reading")
        print("• Error resolution suggestions integration")
        print("• Progress dialog error handling")
        print("• Operation cancellation error handling")
        
        print("\nError Handling Features Verified:")
        print("• Specific error messages for different types of read failures")
        print("• Graceful handling of partial configuration reads")
        print("• Retry logic for failed parameter queries")
        print("• User-friendly error reporting with suggestions for resolution")
        print("• Comprehensive logging and progress indication")
        print("• Robust error handling for UI component failures")
        
    except Exception as e:
        print(f"\n❌ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)