#!/usr/bin/env python3
"""
Test script for DeviceCommandMapper query command functionality.

This script tests the new query command features added to DeviceCommandMapper:
- Parameter query commands
- Response pattern matching
- Command-to-parameter mapping
- Timeout handling
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.device_command_mapper import DeviceCommandMapper


def test_query_commands():
    """Test that query commands are properly generated."""
    print("Testing query command generation...")
    
    mapper = DeviceCommandMapper()
    
    # Test basic query commands
    test_cases = [
        ('query_apn', 'ATSMS:APN#'),
        ('query_server', 'ATSMS:SERVER#'),
        ('query_timer', 'ATSMS:TIMER#'),
        ('query_heartbeat', 'ATSMS:HBT#'),
        ('query_vibration', 'ATSMS:SZCS#VIBL'),
        ('query_protocol', 'ATSMS:CXCS#GT06SEL'),
        ('query_network', 'ATSMS:SZCS#NETSELECT'),
        ('query_sleep_mode', 'ATSMS:SZCS#SLPDISCONNECT'),
        ('query_ignition', 'ATSMS:SZCS#ACCLINE#ACC_CFG'),
    ]
    
    for param_name, expected_command in test_cases:
        try:
            command = mapper.get_command(param_name, None)
            if command == expected_command:
                print(f"✓ {param_name}: {command}")
            else:
                print(f"✗ {param_name}: Expected '{expected_command}', got '{command}'")
        except Exception as e:
            print(f"✗ {param_name}: Error - {str(e)}")
    
    print()


def test_response_parsing():
    """Test response parsing for different command types."""
    print("Testing response parsing...")
    
    mapper = DeviceCommandMapper()
    
    # Test cases with sample device responses
    test_cases = [
        # APN response
        ('query_apn', 'APN:cmnet,user,pass', {
            'apn_server': 'cmnet',
            'apn_user': 'user', 
            'apn_password': 'pass'
        }),
        
        # Server response
        ('query_server', 'SERVER:0,192.168.1.100,8080,0', {
            'server_type': '0',
            'server_address': '192.168.1.100',
            'server_port': '8080',
            'server_protocol': '0',
            'server_ip': '192.168.1.100'
        }),
        
        # Timer response
        ('query_timer', 'TIMER ACC ON:30s,ACC OFF:300s', {
            'timer_ign_on': '30',
            'timer_ign_off': '300'
        }),
        
        # Heartbeat response
        ('query_heartbeat', 'HBT ACC ON:180s,ACC OFF:180s', {
            'heartbeat_ign_on': '180',
            'heartbeat_ign_off': '180'
        }),
        
        # Vibration response
        ('query_vibration', 'READOK: VIBL=3', {
            'vibration': '3'
        }),
        
        # Protocol response
        ('query_protocol', 'READOK: GT06SEL=0', {
            'gt06_protocol': 'GT06-0x60'
        }),
        
        # Network response
        ('query_network', 'READOK: NETSELECT=1', {
            'network_select': '4G'
        }),
        
        # Sleep mode response
        ('query_sleep_mode', 'READOK: SLPDISCONNECT=1', {
            'sleep_mode': 'Sleep'
        }),
        
        # Ignition response
        ('query_ignition', 'READOK: ACCLINE=0#ACC_CFG=0-000-000', {
            'ignition_type': 'Digital',
            'ignition_config': '0-000-000'
        }),
        
        # Device info responses
        ('get_imei', 'READOK: IMEI=868022038821794', {
            'imei': '868022038821794'
        }),
        
        ('get_iccid', 'READOK: ICCID=89860000192397786063', {
            'iccid': '89860000192397786063'
        }),
    ]
    
    for command_type, response, expected_params in test_cases:
        try:
            result = mapper.parse_query_response(response, command_type)
            
            if result['success']:
                # Check if all expected parameters are present and correct
                all_correct = True
                for key, expected_value in expected_params.items():
                    if key not in result['parameters'] or result['parameters'][key] != expected_value:
                        all_correct = False
                        print(f"✗ {command_type}: Parameter '{key}' - Expected '{expected_value}', got '{result['parameters'].get(key, 'MISSING')}'")
                        break
                
                if all_correct:
                    print(f"✓ {command_type}: Parsed correctly")
                    print(f"  Parameters: {result['parameters']}")
            else:
                print(f"✗ {command_type}: Parsing failed - {result.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            print(f"✗ {command_type}: Exception - {str(e)}")
    
    print()


def test_timeout_settings():
    """Test timeout settings for different command types."""
    print("Testing timeout settings...")
    
    mapper = DeviceCommandMapper()
    
    # Test timeout retrieval
    test_commands = [
        'query_apn', 'query_server', 'query_timer', 'query_heartbeat',
        'query_vibration', 'get_imei', 'get_iccid', 'get_all_params'
    ]
    
    for command_type in test_commands:
        timeout = mapper.get_command_timeout(command_type)
        print(f"✓ {command_type}: {timeout}s timeout")
    
    # Test default timeout for unknown command
    default_timeout = mapper.get_command_timeout('unknown_command')
    print(f"✓ unknown_command: {default_timeout}s timeout (default)")
    
    print()


def test_parameter_mapping():
    """Test parameter to query command mapping."""
    print("Testing parameter mapping...")
    
    mapper = DeviceCommandMapper()
    mapping = mapper.create_parameter_mapping()
    
    # Test some key mappings
    test_cases = [
        ('apn_server', ['query_apn']),
        ('server_ip', ['query_server']),
        ('timer_ign_on', ['query_timer']),
        ('heartbeat_ign_on', ['query_heartbeat']),
        ('vibration', ['query_vibration']),
        ('protocol', ['query_protocol']),
        ('imei', ['get_imei']),
    ]
    
    for param_name, expected_queries in test_cases:
        if param_name in mapping:
            if mapping[param_name] == expected_queries:
                print(f"✓ {param_name}: {mapping[param_name]}")
            else:
                print(f"✗ {param_name}: Expected {expected_queries}, got {mapping[param_name]}")
        else:
            print(f"✗ {param_name}: Not found in mapping")
    
    print(f"Total parameters mapped: {len(mapping)}")
    print()


def test_check_config_commands():
    """Test the updated check config commands."""
    print("Testing check config commands...")
    
    mapper = DeviceCommandMapper()
    commands = mapper.get_check_config_commands()
    
    print(f"Total check config commands: {len(commands)}")
    
    # Verify some key commands are present
    command_types = [cmd_type for _, cmd_type in commands]
    expected_types = [
        'query_apn', 'query_server', 'query_timer', 'query_heartbeat',
        'query_vibration', 'query_protocol', 'query_network'
    ]
    
    for expected_type in expected_types:
        if expected_type in command_types:
            print(f"✓ {expected_type}: Present in check config commands")
        else:
            print(f"✗ {expected_type}: Missing from check config commands")
    
    print()


def main():
    """Run all tests."""
    print("DeviceCommandMapper Query Commands Test")
    print("=" * 50)
    
    test_query_commands()
    test_response_parsing()
    test_timeout_settings()
    test_parameter_mapping()
    test_check_config_commands()
    
    print("Test completed!")


if __name__ == "__main__":
    main()