#!/usr/bin/env python3
"""
Test script for ConfigurationReaderService.

This script tests the basic functionality of the ConfigurationReaderService
including parameter query command generation, response parsing, and error handling.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.configuration_reader_service import ConfigurationReaderService, ParameterReadResult, ParsedResponse
from services.i18n_service import I18nService


class MockApp:
    """Mock application for testing."""
    def __init__(self):
        self.log_messages = []
        
    def after(self, delay, callback, *args):
        """Mock after method."""
        callback(*args)
        
    class MockLogFrame:
        def __init__(self, app):
            self.app = app
            
        def log_message(self, message):
            self.app.log_messages.append(message.strip())
    
    class MockSerialService:
        def __init__(self):
            self.is_connected = True
            
        def send_command(self, command):
            pass
    
    def __init__(self):
        self.log_messages = []
        self.log_frame = self.MockLogFrame(self)
        self.serial_service = self.MockSerialService()


def test_service_initialization():
    """Test service initialization."""
    print("Testing ConfigurationReaderService initialization...")
    
    app = MockApp()
    i18n = I18nService()
    
    service = ConfigurationReaderService(app, i18n)
    
    # Test that service is properly initialized
    assert not service.is_reading_in_progress()
    assert service.get_supported_parameters()
    assert len(service.parameter_query_commands) > 0
    assert len(service.response_patterns) > 0
    
    print("✓ Service initialization test passed")


def test_parameter_support():
    """Test parameter support validation."""
    print("Testing parameter support validation...")
    
    app = MockApp()
    i18n = I18nService()
    service = ConfigurationReaderService(app, i18n)
    
    # Test supported parameters
    assert service.validate_parameter_support('apn_config')
    assert service.validate_parameter_support('server_config')
    assert service.validate_parameter_support('device_info')
    
    # Test unsupported parameter
    assert not service.validate_parameter_support('nonexistent_parameter')
    
    print("✓ Parameter support validation test passed")


def test_query_command_generation():
    """Test query command generation."""
    print("Testing query command generation...")
    
    app = MockApp()
    i18n = I18nService()
    service = ConfigurationReaderService(app, i18n)
    
    # Test getting query commands
    apn_command = service.get_parameter_query_command('apn_config')
    assert apn_command is not None
    assert len(apn_command) == 2
    assert apn_command[0] == 'ATSMS:APN#'
    assert apn_command[1] == 'get_apn'
    
    server_command = service.get_parameter_query_command('server_config')
    assert server_command is not None
    assert server_command[0] == 'ATSMS:SERVER#'
    assert server_command[1] == 'get_server'
    
    print("✓ Query command generation test passed")


def test_response_parsing():
    """Test response parsing functionality."""
    print("Testing response parsing...")
    
    app = MockApp()
    i18n = I18nService()
    service = ConfigurationReaderService(app, i18n)
    
    # Test APN response parsing
    apn_response = "APN:cmnet,user,password"
    parsed = service.parse_device_response("ATSMS:APN#", apn_response, "get_apn")
    
    assert parsed.success
    assert 'apn_server' in parsed.parsed_values
    assert parsed.parsed_values['apn_server'] == 'cmnet'
    assert parsed.parsed_values['apn_user'] == 'user'
    assert parsed.parsed_values['apn_password'] == 'password'
    
    # Test IMEI response parsing
    imei_response = "IMEI:868022038821794"
    parsed = service.parse_device_response("ATSMS:CXCS#IMEI", imei_response, "get_imei")
    
    assert parsed.success
    assert 'imei' in parsed.parsed_values
    assert parsed.parsed_values['imei'] == '868022038821794'
    
    # Test server response parsing
    server_response = "SERVER:0,58.61.154.247,7018,0"
    parsed = service.parse_device_response("ATSMS:SERVER#", server_response, "get_server")
    
    assert parsed.success
    assert 'server_address' in parsed.parsed_values
    assert parsed.parsed_values['server_address'] == '58.61.154.247'
    assert parsed.parsed_values['server_port'] == '7018'
    
    print("✓ Response parsing test passed")


def test_error_handling():
    """Test error handling functionality."""
    print("Testing error handling...")
    
    app = MockApp()
    i18n = I18nService()
    service = ConfigurationReaderService(app, i18n)
    
    # Test parsing invalid response
    invalid_response = "INVALID_RESPONSE_FORMAT"
    parsed = service.parse_device_response("ATSMS:APN#", invalid_response, "get_apn")
    
    assert not parsed.success
    assert parsed.error_message is not None
    
    # Test specific error messages
    timeout_error = service._get_specific_error_message('apn_config', 'Command timeout')
    assert 'timeout' in timeout_error.lower() or 'time' in timeout_error.lower()
    
    parse_error = service._get_specific_error_message('server_config', 'Response does not match expected pattern')
    assert 'format' in parse_error.lower() or 'parse' in parse_error.lower()
    
    print("✓ Error handling test passed")


def test_parameter_read_result():
    """Test ParameterReadResult functionality."""
    print("Testing ParameterReadResult...")
    
    # Test successful result
    success_result = ParameterReadResult(
        parameter_name='test_param',
        success=True,
        value='test_value',
        error_message=None,
        raw_response='TEST:test_value'
    )
    
    assert success_result.success
    assert success_result.value == 'test_value'
    assert success_result.error_message is None
    
    # Test failed result
    failed_result = ParameterReadResult(
        parameter_name='test_param',
        success=False,
        value=None,
        error_message='Test error',
        raw_response=''
    )
    
    assert not failed_result.success
    assert failed_result.value is None
    assert failed_result.error_message == 'Test error'
    
    print("✓ ParameterReadResult test passed")


def run_all_tests():
    """Run all tests."""
    print("Running ConfigurationReaderService tests...\n")
    
    try:
        test_service_initialization()
        test_parameter_support()
        test_query_command_generation()
        test_response_parsing()
        test_error_handling()
        test_parameter_read_result()
        
        print("\n✅ All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)