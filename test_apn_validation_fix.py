"""
Test APN Server Validation Fix

This script tests that the APN server validation is now working correctly
using the validation service instead of the custom method.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.i18n_service import I18nService
from services.validation_service import ValidationService


def test_apn_validation_fix():
    """Test that APN server validation now works correctly."""
    print("=== Testing APN Server Validation Fix ===")
    
    # Initialize services
    i18n = I18nService()
    i18n.set_language('pt_BR')
    validation_service = ValidationService(i18n)
    
    # Test cases that should be handled correctly now
    test_cases = [
        # Valid cases
        ('google.com', True, 'Valid domain'),
        ('192.168.1.1', True, 'Valid IP address'),
        ('server.example.com', True, 'Valid subdomain'),
        ('example.co.uk', True, 'Valid domain with country code'),
        ('test-server.com', True, 'Valid domain with hyphen'),
        
        # Invalid cases that should now be caught
        ('localhost', False, 'Single word hostname (invalid by regex)'),
        ('invalid..domain', False, 'Double dots'),
        ('999.999.999.999', False, 'Invalid IP address'),
        ('256.256.256.256', False, 'Invalid IP address (out of range)'),
        ('', False, 'Empty string'),
        ('domain_with_underscore.com', False, 'Underscore not allowed'),
        ('-invalid-start.com', False, 'Cannot start with hyphen'),
        ('invalid-end-.com', False, 'Cannot end with hyphen'),
    ]
    
    print("Testing validation service APN server validation:")
    print("-" * 60)
    
    all_passed = True
    for test_value, expected_valid, description in test_cases:
        try:
            result = validation_service.validate_parameter('apn_server', test_value)
            actual_valid = result.is_valid
            
            status = "✓" if actual_valid == expected_valid else "✗"
            print(f"{status} '{test_value}' -> {actual_valid} ({description})")
            
            if not result.is_valid and result.error_message:
                print(f"    Error: {result.error_message}")
            
            if actual_valid != expected_valid:
                print(f"    MISMATCH: Expected {expected_valid}, got {actual_valid}")
                all_passed = False
                
        except Exception as e:
            print(f"✗ '{test_value}' -> ERROR: {e}")
            all_passed = False
    
    print("-" * 60)
    if all_passed:
        print("🎉 All APN server validation tests passed!")
    else:
        print("❌ Some tests failed - validation may need adjustment")
    
    return all_passed


def test_validation_service_pattern():
    """Test the validation service regex pattern directly."""
    print("\n=== Testing Validation Service Regex Pattern ===")
    
    i18n = I18nService()
    i18n.set_language('pt_BR')
    validation_service = ValidationService(i18n)
    
    # Get the APN server validation info
    apn_info = validation_service.get_parameter_info('apn_server')
    if apn_info and 'pattern' in apn_info:
        pattern = apn_info['pattern']
        print(f"APN server regex pattern: {pattern}")
        
        # Test the pattern directly
        import re
        regex = re.compile(pattern)
        
        test_cases = [
            'google.com',
            '192.168.1.1',
            'server.example.com',
            'localhost',
            'invalid..domain',
            '999.999.999.999'
        ]
        
        print("Direct regex pattern testing:")
        for test_value in test_cases:
            match = bool(regex.match(test_value))
            print(f"  '{test_value}' -> {match}")
    else:
        print("No regex pattern found for apn_server")


def simulate_ui_validation():
    """Simulate how the UI validation would work now."""
    print("\n=== Simulating UI Validation ===")
    
    # Initialize services like the UI does
    i18n = I18nService()
    i18n.set_language('pt_BR')
    validation_service = ValidationService(i18n)
    
    def simulate_send_apn_server_command(value):
        """Simulate the send_apn_server_command method."""
        print(f"Simulating APN server validation for: '{value}'")
        
        if value:
            # Use validation service for proper APN server validation
            validation_result = validation_service.validate_parameter('apn_server', value)
            if not validation_result.is_valid:
                print(f"❌ Validation failed: {validation_result.error_message}")
                return False
            else:
                print("✓ Validation passed")
                print(f"Would send command: AT+APNSRV={value}")
                return True
        else:
            print("Empty value - would send empty command")
            return True
    
    # Test various inputs
    test_inputs = [
        'google.com',
        '192.168.1.1', 
        'invalid..domain',
        '256.256.256.256',
        'localhost',
        ''
    ]
    
    print("Simulating UI validation behavior:")
    for test_input in test_inputs:
        print(f"\nTesting input: '{test_input}'")
        simulate_send_apn_server_command(test_input)


if __name__ == "__main__":
    print("Testing APN Server Validation Fix")
    print("=" * 50)
    
    success = test_apn_validation_fix()
    test_validation_service_pattern()
    simulate_ui_validation()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ APN server validation fix appears to be working correctly!")
        print("The validation service is now being used instead of the custom method.")
        print("Invalid IP addresses and malformed domains should now be properly rejected.")
    else:
        print("⚠️  Some validation tests failed - please review the results above.")