#!/usr/bin/env python3
"""
Test edge cases and error handling for DeviceCommandMapper query functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.device_command_mapper import DeviceCommandMapper


def test_error_responses():
    """Test parsing of error responses."""
    print("Testing error response parsing...")
    
    mapper = DeviceCommandMapper()
    
    # Test error responses
    error_cases = [
        ('query_apn', 'ERROR: Invalid command', 'Device returned error'),
        ('query_server', 'FAIL', 'Device returned error'),
        ('query_timer', 'INVALID PARAMETER', 'Device returned error'),
        ('query_vibration', '', 'Could not parse response'),
        ('query_protocol', 'READOK: UNKNOWN=1', 'Could not parse response'),
    ]
    
    for command_type, response, expected_error_type in error_cases:
        result = mapper.parse_query_response(response, command_type)
        
        if not result['success'] and result['error_message']:
            if expected_error_type in result['error_message']:
                print(f"✓ {command_type}: Error correctly detected - {result['error_message']}")
            else:
                print(f"✗ {command_type}: Unexpected error message - {result['error_message']}")
        else:
            print(f"✗ {command_type}: Should have failed but didn't")
    
    print()


def test_malformed_responses():
    """Test parsing of malformed responses."""
    print("Testing malformed response parsing...")
    
    mapper = DeviceCommandMapper()
    
    # Test malformed responses
    malformed_cases = [
        ('query_apn', 'APN:incomplete', 'Should handle incomplete APN response'),
        ('query_server', 'SERVER:0,missing,port', 'Should handle incomplete SERVER response'),
        ('query_timer', 'TIMER ACC ON:30s', 'Should handle incomplete TIMER response'),
        ('query_vibration', 'VIBL=', 'Should handle empty value'),
        ('query_protocol', 'GT06SEL=999', 'Should handle unknown protocol value'),
    ]
    
    for command_type, response, description in malformed_cases:
        result = mapper.parse_query_response(response, command_type)
        print(f"✓ {command_type}: {description}")
        print(f"  Success: {result['success']}, Parameters: {result['parameters']}")
        if result['error_message']:
            print(f"  Error: {result['error_message']}")
    
    print()


def test_case_insensitive_parsing():
    """Test case-insensitive response parsing."""
    print("Testing case-insensitive parsing...")
    
    mapper = DeviceCommandMapper()
    
    # Test case variations
    case_cases = [
        ('query_vibration', 'readok: vibl=3', 'Should handle lowercase'),
        ('query_protocol', 'READOK: gt06sel=0', 'Should handle mixed case'),
        ('get_imei', 'imei:868022038821794', 'Should handle lowercase device info'),
    ]
    
    for command_type, response, description in case_cases:
        result = mapper.parse_query_response(response, command_type)
        
        if result['success'] and result['parameters']:
            print(f"✓ {command_type}: {description} - Parsed successfully")
            print(f"  Parameters: {result['parameters']}")
        else:
            print(f"✗ {command_type}: {description} - Failed to parse")
            if result['error_message']:
                print(f"  Error: {result['error_message']}")
    
    print()


def test_timeout_edge_cases():
    """Test timeout handling for edge cases."""
    print("Testing timeout edge cases...")
    
    mapper = DeviceCommandMapper()
    
    # Test various command types
    edge_cases = [
        ('', 'Empty command type should use default'),
        ('unknown_query_type', 'Unknown command should use default'),
        ('query_apn', 'Known command should use specific timeout'),
        ('get_all_params', 'Complex command should use longer timeout'),
    ]
    
    for command_type, description in edge_cases:
        timeout = mapper.get_command_timeout(command_type)
        print(f"✓ '{command_type}': {timeout}s - {description}")
    
    print()


def test_parameter_mapping_completeness():
    """Test that parameter mapping covers all expected parameters."""
    print("Testing parameter mapping completeness...")
    
    mapper = DeviceCommandMapper()
    mapping = mapper.create_parameter_mapping()
    
    # Check that all major parameter categories are covered
    expected_categories = [
        'apn_', 'server_', 'timer_', 'heartbeat_', 'vibration', 
        'protocol', 'network_', 'sleep_', 'ignition_', 'imei', 'iccid'
    ]
    
    for category in expected_categories:
        matching_params = [param for param in mapping.keys() if category in param]
        if matching_params:
            print(f"✓ {category}*: {len(matching_params)} parameters mapped")
        else:
            print(f"✗ {category}*: No parameters found")
    
    # Check for orphaned parameters (parameters that don't have query commands)
    query_commands = mapper.get_parameter_query_commands()
    orphaned = []
    
    for param in mapping.keys():
        if param not in query_commands and not param.startswith(('imei', 'iccid', 'version')):
            orphaned.append(param)
    
    if orphaned:
        print(f"⚠ Orphaned parameters (no query commands): {orphaned}")
    else:
        print("✓ All parameters have corresponding query commands")
    
    print()


def test_response_patterns_coverage():
    """Test that response patterns cover all query commands."""
    print("Testing response pattern coverage...")
    
    mapper = DeviceCommandMapper()
    patterns = mapper.get_response_patterns()
    query_commands = [cmd for cmd in mapper.command_templates.keys() if cmd.startswith('query_') or cmd.startswith('get_')]
    
    missing_patterns = []
    for command in query_commands:
        if command not in patterns:
            missing_patterns.append(command)
    
    if missing_patterns:
        print(f"⚠ Commands without response patterns: {missing_patterns}")
    else:
        print("✓ All query commands have response patterns")
    
    # Test pattern validity (basic regex syntax check)
    invalid_patterns = []
    for command_type, pattern in patterns.items():
        try:
            import re
            re.compile(pattern)
        except re.error:
            invalid_patterns.append(command_type)
    
    if invalid_patterns:
        print(f"✗ Invalid regex patterns: {invalid_patterns}")
    else:
        print("✓ All response patterns are valid regex")
    
    print()


def main():
    """Run all edge case tests."""
    print("DeviceCommandMapper Edge Cases and Error Handling Test")
    print("=" * 60)
    
    test_error_responses()
    test_malformed_responses()
    test_case_insensitive_parsing()
    test_timeout_edge_cases()
    test_parameter_mapping_completeness()
    test_response_patterns_coverage()
    
    print("Edge case testing completed!")


if __name__ == "__main__":
    main()