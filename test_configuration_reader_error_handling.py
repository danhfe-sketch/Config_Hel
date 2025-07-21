#!/usr/bin/env python3
"""
Test script for ConfigurationReaderService enhanced error handling.

This script tests the error handling improvements for configuration reading,
including retry logic, specific error messages, and user-friendly error reporting.
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
        self.connection_frame = Mock()
        self.operation_confirmation_service = Mock()
        
    def after(self, delay, callback, *args):
        """Mock the after method."""
        if callable(callback):
            callback(*args)


def test_retry_logic():
    """Test the retry logic for failed parameter reads."""
    print("Testing retry logic for failed parameter reads...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create configuration reader service
    config_reader = ConfigurationReaderService(app, i18n)
    
    # Mock the _send_command_and_wait method to simulate failures then success
    call_count = 0
    def mock_send_command_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:  # First two attempts fail
            return None  # Simulate timeout
        else:  # Third attempt succeeds
            return "APN:internet.provider.com,user,password#"
    
    config_reader._send_command_and_wait = Mock(side_effect=mock_send_command_side_effect)
    
    # Test reading a parameter with retries
    result = config_reader.read_specific_parameter('apn_config', 'ATSMS:APN#', 'get_apn', max_retries=2)
    
    # Verify retry logic worked
    assert call_count == 3, f"Expected 3 calls (1 initial + 2 retries), got {call_count}"
    assert result.success, "Parameter read should succeed after retries"
    assert result.value is not None, "Parameter value should be extracted"
    
    print("✓ Retry logic test passed")


def test_specific_error_messages():
    """Test specific error messages for different failure types."""
    print("Testing specific error messages...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create configuration reader service
    config_reader = ConfigurationReaderService(app, i18n)
    
    # Test different error types
    test_cases = [
        ('timeout error', 'timeout'),
        ('parse error in response', 'parse'),
        ('connection lost during read', 'connection'),
        ('unknown parameter type', 'unknown parameter'),
        ('generic error message', 'generic')
    ]
    
    for error_msg, expected_type in test_cases:
        specific_msg = config_reader._get_specific_error_message('apn_config', error_msg)
        assert len(specific_msg) > len(error_msg), f"Specific message should be more detailed for {expected_type}"
        assert 'APN Configuration' in specific_msg, "Should include user-friendly parameter name"
        print(f"  ✓ {expected_type} error message: {specific_msg[:50]}...")
    
    print("✓ Specific error messages test passed")


def test_error_resolution_suggestions():
    """Test error resolution suggestions."""
    print("Testing error resolution suggestions...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create configuration reader service
    config_reader = ConfigurationReaderService(app, i18n)
    
    # Test different error types
    error_types = ['timeout', 'parse error', 'connection lost', 'generic error']
    
    for error_type in error_types:
        suggestions = config_reader._get_error_resolution_suggestions('apn_config', error_type)
        assert len(suggestions) > 0, f"Should provide suggestions for {error_type}"
        assert all(isinstance(s, str) and len(s) > 0 for s in suggestions), "All suggestions should be non-empty strings"
        print(f"  ✓ {error_type}: {len(suggestions)} suggestions provided")
    
    print("✓ Error resolution suggestions test passed")


def test_partial_failure_handling():
    """Test graceful handling of partial configuration reads."""
    print("Testing partial failure handling...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create configuration reader service
    config_reader = ConfigurationReaderService(app, i18n)
    
    # Test partial failure guidance
    failed_params = ['timer_settings', 'heartbeat_settings']
    successful_reads = 8
    total_params = 10
    
    # This should not raise an exception
    try:
        config_reader._provide_partial_failure_guidance(failed_params, successful_reads, total_params)
        print("  ✓ Partial failure guidance provided successfully")
    except Exception as e:
        assert False, f"Partial failure guidance should not raise exception: {e}"
    
    # Test complete failure guidance
    all_failed_params = ['device_info', 'apn_config', 'server_config', 'timer_settings']
    
    try:
        config_reader._provide_complete_failure_guidance(all_failed_params)
        print("  ✓ Complete failure guidance provided successfully")
    except Exception as e:
        assert False, f"Complete failure guidance should not raise exception: {e}"
    
    print("✓ Partial failure handling test passed")


def test_error_categorization():
    """Test error categorization functionality."""
    print("Testing error categorization...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create configuration reader service
    config_reader = ConfigurationReaderService(app, i18n)
    
    # Test error categorization
    test_cases = [
        ('Command timeout occurred', 'timeout'),
        ('Failed to parse device response', 'parse_error'),
        ('Connection lost during operation', 'connection_error'),
        ('Invalid response format received', 'invalid_response'),
        ('Unknown parameter requested', 'unknown_parameter'),
        ('Some other error', 'generic_error')
    ]
    
    for error_msg, expected_category in test_cases:
        category = config_reader._categorize_error_type(error_msg)
        assert category == expected_category, f"Expected {expected_category}, got {category} for '{error_msg}'"
        print(f"  ✓ '{error_msg}' → {category}")
    
    print("✓ Error categorization test passed")


def test_detailed_error_summary():
    """Test detailed error summary creation."""
    print("Testing detailed error summary creation...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create configuration reader service
    config_reader = ConfigurationReaderService(app, i18n)
    
    # Test complete failure summary
    all_failed = ['param1', 'param2', 'param3', 'param4']
    summary = config_reader._create_detailed_error_summary(all_failed, 0, 4)
    assert 'completely' in summary.lower(), "Complete failure should mention 'completely'"
    print(f"  ✓ Complete failure: {summary[:50]}...")
    
    # Test partial failure summary (minor issues)
    minor_failed = ['param1']
    summary = config_reader._create_detailed_error_summary(minor_failed, 3, 4)
    assert 'minor' in summary.lower() or '3/4' in summary, "Minor failure should mention minor issues or ratio"
    print(f"  ✓ Minor failure: {summary[:50]}...")
    
    # Test partial failure summary (major issues)
    major_failed = ['param1', 'param2', 'param3']
    summary = config_reader._create_detailed_error_summary(major_failed, 1, 4)
    assert 'major' in summary.lower() or '1/4' in summary, "Major failure should mention major issues or ratio"
    print(f"  ✓ Major failure: {summary[:50]}...")
    
    print("✓ Detailed error summary test passed")


def test_error_statistics():
    """Test error statistics tracking."""
    print("Testing error statistics tracking...")
    
    # Create mock app and services
    app = MockApp()
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create configuration reader service
    config_reader = ConfigurationReaderService(app, i18n)
    
    # Test initial statistics
    stats = config_reader.get_error_statistics()
    assert stats['total_read_attempts'] == 0, "Initial read attempts should be 0"
    assert stats['successful_reads'] == 0, "Initial successful reads should be 0"
    assert stats['failed_reads'] == 0, "Initial failed reads should be 0"
    print("  ✓ Initial statistics correct")
    
    # Simulate some statistics
    config_reader.total_read_attempts = 3
    config_reader.successful_reads = 15
    config_reader.failed_reads = 5
    config_reader.last_read_attempt = datetime.now()
    
    stats = config_reader.get_error_statistics()
    assert stats['total_read_attempts'] == 3, "Read attempts should be tracked"
    assert stats['successful_reads'] == 15, "Successful reads should be tracked"
    assert stats['failed_reads'] == 5, "Failed reads should be tracked"
    assert stats['last_read_attempt'] is not None, "Last read attempt should be tracked"
    print("  ✓ Statistics tracking works correctly")
    
    # Test statistics reset
    config_reader.reset_error_statistics()
    stats = config_reader.get_error_statistics()
    assert stats['total_read_attempts'] == 0, "Statistics should be reset"
    assert stats['successful_reads'] == 0, "Statistics should be reset"
    assert stats['failed_reads'] == 0, "Statistics should be reset"
    print("  ✓ Statistics reset works correctly")
    
    print("✓ Error statistics test passed")


def main():
    """Run all error handling tests."""
    print("=" * 60)
    print("ConfigurationReaderService Enhanced Error Handling Tests")
    print("=" * 60)
    
    try:
        test_retry_logic()
        print()
        
        test_specific_error_messages()
        print()
        
        test_error_resolution_suggestions()
        print()
        
        test_partial_failure_handling()
        print()
        
        test_error_categorization()
        print()
        
        test_detailed_error_summary()
        print()
        
        test_error_statistics()
        print()
        
        print("=" * 60)
        print("✅ All enhanced error handling tests passed!")
        print("=" * 60)
        
        print("\nEnhanced Error Handling Features Verified:")
        print("• Retry logic for failed parameter queries")
        print("• Specific error messages for different failure types")
        print("• Error resolution suggestions for users")
        print("• Graceful handling of partial configuration reads")
        print("• Error categorization and statistics tracking")
        print("• Detailed error summaries with user guidance")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)