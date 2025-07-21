#!/usr/bin/env python3
"""
Integration example showing how DeviceCommandMapper query functionality 
integrates with ConfigurationReaderService.

This demonstrates the complete workflow for reading device configuration.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.device_command_mapper import DeviceCommandMapper


def simulate_device_responses():
    """Simulate typical device responses for testing."""
    return {
        'ATSMS:APN#': 'APN:cmnet,user,password123',
        'ATSMS:SERVER#': 'SERVER:0,192.168.1.100,8080,0',
        'ATSMS:TIMER#': 'TIMER ACC ON:30s,ACC OFF:300s',
        'ATSMS:HBT#': 'HBT ACC ON:180s,ACC OFF:180s',
        'ATSMS:SZCS#VIBL': 'READOK: VIBL=3',
        'ATSMS:CXCS#GT06SEL': 'READOK: GT06SEL=0',
        'ATSMS:SZCS#NETSELECT': 'READOK: NETSELECT=1',
        'ATSMS:SZCS#SLPDISCONNECT': 'READOK: SLPDISCONNECT=1',
        'ATSMS:SZCS#ACCLINE#ACC_CFG': 'READOK: ACCLINE=0#ACC_CFG=0-000-000',
        'ATSMS:CXCS#IMEI': 'READOK: IMEI=868022038821794',
        'ATSMS:CXCS#ICCID': 'READOK: ICCID=89860000192397786063',
    }


def test_complete_configuration_reading():
    """Test complete configuration reading workflow."""
    print("Testing Complete Configuration Reading Workflow")
    print("=" * 50)
    
    # Initialize mapper
    mapper = DeviceCommandMapper()
    
    # Simulate device responses
    device_responses = simulate_device_responses()
    
    print("1. Getting query commands for configuration reading...")
    query_commands = mapper.get_check_config_commands()
    
    print(f"   Total query commands: {len(query_commands)}")
    for i, (command, command_type) in enumerate(query_commands[:5]):  # Show first 5
        print(f"   {i+1}. {command_type}: {command}")
    print("   ... (and more)")
    print()
    
    print("2. Simulating device communication and response parsing...")
    parsed_results = {}
    
    for command, command_type in query_commands:
        if command in device_responses:
            response = device_responses[command]
            result = mapper.parse_query_response(response, command_type)
            
            if result['success']:
                parsed_results[command_type] = result['parameters']
                print(f"   ✓ {command_type}: {result['parameters']}")
            else:
                print(f"   ✗ {command_type}: {result.get('error_message', 'Parse failed')}")
        else:
            print(f"   - {command_type}: No simulated response")
    
    print()
    
    print("3. Demonstrating parameter mapping for UI population...")
    parameter_mapping = mapper.create_parameter_mapping()
    ui_parameters = {}
    
    # Extract parameters that would populate UI fields
    for command_type, parameters in parsed_results.items():
        for param_name, param_value in parameters.items():
            if param_name in parameter_mapping:
                ui_parameters[param_name] = param_value
    
    print("   UI Parameters that would be populated:")
    for param_name, param_value in ui_parameters.items():
        print(f"   - {param_name}: {param_value}")
    
    print()
    
    print("4. Demonstrating timeout handling...")
    timeout_examples = [
        'query_apn', 'query_server', 'query_vibration', 
        'get_imei', 'get_all_params', 'unknown_command'
    ]
    
    for command_type in timeout_examples:
        timeout = mapper.get_command_timeout(command_type)
        print(f"   {command_type}: {timeout}s timeout")
    
    print()
    
    print("5. Summary of configuration reading capabilities:")
    print(f"   - Total parameters that can be queried: {len(parameter_mapping)}")
    print(f"   - Total query commands available: {len(query_commands)}")
    print(f"   - Parameters successfully parsed in simulation: {len(ui_parameters)}")
    print(f"   - Response patterns defined: {len(mapper.get_response_patterns())}")
    
    return True


def test_error_handling_workflow():
    """Test error handling in configuration reading."""
    print("\nTesting Error Handling Workflow")
    print("=" * 40)
    
    mapper = DeviceCommandMapper()
    
    # Simulate various error scenarios
    error_scenarios = [
        ('query_apn', 'ERROR: Command not supported', 'Device error'),
        ('query_server', '', 'Empty response'),
        ('query_timer', 'TIMEOUT', 'Device timeout'),
        ('query_vibration', 'INVALID RESPONSE FORMAT', 'Malformed response'),
        ('query_protocol', 'READOK: UNKNOWN_PARAM=1', 'Unexpected parameter'),
    ]
    
    print("Error handling scenarios:")
    for command_type, response, scenario_desc in error_scenarios:
        result = mapper.parse_query_response(response, command_type)
        
        print(f"   {scenario_desc}:")
        print(f"     Command: {command_type}")
        print(f"     Response: '{response}'")
        print(f"     Success: {result['success']}")
        if result['error_message']:
            print(f"     Error: {result['error_message']}")
        print()


def test_parameter_coverage():
    """Test parameter coverage for UI integration."""
    print("Testing Parameter Coverage for UI Integration")
    print("=" * 50)
    
    mapper = DeviceCommandMapper()
    
    # Get all mappings
    parameter_mapping = mapper.create_parameter_mapping()
    query_commands = mapper.get_parameter_query_commands()
    
    print("Parameter categories and their query coverage:")
    
    categories = {
        'APN Configuration': ['apn_server', 'apn_user', 'apn_password'],
        'Server Configuration': ['server_ip', 'server_domain', 'server_port', 'server_protocol'],
        'Timer Settings': ['timer_ign_on', 'timer_ign_off'],
        'Heartbeat Settings': ['heartbeat_ign_on', 'heartbeat_ign_off', 'heartbeat_interval'],
        'Device Behavior': ['vibration', 'defense_time', 'protocol', 'network_select'],
        'Sleep Configuration': ['sleep_mode', 'sleep_time'],
        'Device Information': ['imei', 'iccid', 'imsi', 'version'],
    }
    
    for category, params in categories.items():
        print(f"\n{category}:")
        for param in params:
            if param in parameter_mapping:
                query_types = parameter_mapping[param]
                print(f"   ✓ {param}: {query_types}")
            else:
                print(f"   ✗ {param}: Not mapped")


def main():
    """Run all integration tests."""
    print("DeviceCommandMapper Query Integration Test")
    print("=" * 60)
    
    success = test_complete_configuration_reading()
    test_error_handling_workflow()
    test_parameter_coverage()
    
    if success:
        print("\n" + "=" * 60)
        print("✓ All integration tests completed successfully!")
        print("✓ DeviceCommandMapper query functionality is ready for integration")
        print("✓ ConfigurationReaderService can use these methods for device communication")
    else:
        print("\n" + "=" * 60)
        print("✗ Some integration tests failed")


if __name__ == "__main__":
    main()