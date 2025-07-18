#!/usr/bin/env python3
"""
Comprehensive test for Task 3.2: Numeric Parameter Controls
Tests vibration, timers, and sensitivity controls with validation.
"""

import customtkinter as ctk
from services.i18n_service import I18nService
from services.validation_service import ValidationService
from ui.parameter_factory import ParameterFactory

def test_vibration_parameter():
    """Test vibration level control (0-255 range)."""
    print("Testing Vibration Parameter:")
    
    i18n = I18nService()
    i18n.set_language('pt_BR')
    validation_service = ValidationService(i18n)
    
    # Test validation ranges
    test_cases = [
        (-1, False, "Below minimum"),
        (0, True, "Minimum value"),
        (128, True, "Default value"),
        (255, True, "Maximum value"),
        (256, False, "Above maximum"),
        ("abc", False, "Invalid string"),
        ("128", True, "Valid string number")
    ]
    
    for value, expected_valid, description in test_cases:
        result = validation_service.validate_parameter('vibration', value)
        status = "✓" if result.is_valid == expected_valid else "✗"
        print(f"  {status} {description}: {value} -> {'Valid' if result.is_valid else 'Invalid'}")
        if not result.is_valid:
            print(f"    Error: {result.error_message}")
    
    print()

def test_sensitivity_parameter():
    """Test sensitivity level control (1-10 range)."""
    print("Testing Sensitivity Parameter:")
    
    i18n = I18nService()
    i18n.set_language('pt_BR')
    validation_service = ValidationService(i18n)
    
    # Test validation ranges
    test_cases = [
        (0, False, "Below minimum"),
        (1, True, "Minimum value"),
        (5, True, "Default value"),
        (10, True, "Maximum value"),
        (11, False, "Above maximum"),
        ("abc", False, "Invalid string"),
        ("5", True, "Valid string number")
    ]
    
    for value, expected_valid, description in test_cases:
        result = validation_service.validate_parameter('sensitivity', value)
        status = "✓" if result.is_valid == expected_valid else "✗"
        print(f"  {status} {description}: {value} -> {'Valid' if result.is_valid else 'Invalid'}")
        if not result.is_valid:
            print(f"    Error: {result.error_message}")
    
    print()

def test_timer_parameters():
    """Test timer setting controls with appropriate ranges."""
    print("Testing Timer Parameters:")
    
    i18n = I18nService()
    i18n.set_language('pt_BR')
    validation_service = ValidationService(i18n)
    
    timer_params = {
        'timer_ign_on': {'min': 1, 'max': 65500, 'default': 30},
        'timer_ign_off': {'min': 1, 'max': 65500, 'default': 300},
        'heartbeat_ign_on': {'min': 60, 'max': 300, 'default': 60},
        'heartbeat_ign_off': {'min': 60, 'max': 300, 'default': 300}
    }
    
    for param_name, config in timer_params.items():
        print(f"  Testing {param_name}:")
        
        test_cases = [
            (config['min'] - 1, False, "Below minimum"),
            (config['min'], True, "Minimum value"),
            (config['default'], True, "Default value"),
            (config['max'], True, "Maximum value"),
            (config['max'] + 1, False, "Above maximum"),
            ("abc", False, "Invalid string"),
            (str(config['default']), True, "Valid string number")
        ]
        
        for value, expected_valid, description in test_cases:
            result = validation_service.validate_parameter(param_name, value)
            status = "✓" if result.is_valid == expected_valid else "✗"
            print(f"    {status} {description}: {value} -> {'Valid' if result.is_valid else 'Invalid'}")
            if not result.is_valid and expected_valid:
                print(f"      Error: {result.error_message}")
        print()

def test_parameter_creation():
    """Test parameter widget creation."""
    print("Testing Parameter Widget Creation:")
    
    i18n = I18nService()
    i18n.set_language('pt_BR')
    validation_service = ValidationService(i18n)
    
    def mock_send_command(command):
        print(f"    Command would be sent: {command}")
    
    factory = ParameterFactory(validation_service, i18n, mock_send_command)
    
    test_params = ['vibration', 'sensitivity', 'timer_ign_on', 'timer_ign_off', 'heartbeat_ign_on', 'heartbeat_ign_off']
    
    for param_name in test_params:
        param = factory.create_parameter(param_name)
        if param:
            print(f"  ✓ {param_name}: Widget created successfully")
            definition = factory.get_parameter_definition(param_name)
            print(f"    - AT Command: {definition.at_command_template}")
            print(f"    - Default Value: {definition.default_value}")
            print(f"    - Display Label: {i18n.get(definition.display_label)}")
        else:
            print(f"  ✗ {param_name}: Failed to create widget")
    
    print()

def test_command_generation():
    """Test AT command generation."""
    print("Testing AT Command Generation:")
    
    i18n = I18nService()
    i18n.set_language('pt_BR')
    validation_service = ValidationService(i18n)
    
    commands_sent = []
    
    def capture_command(command):
        commands_sent.append(command)
    
    factory = ParameterFactory(validation_service, i18n, capture_command)
    
    # Test command generation for each parameter
    test_cases = [
        ('vibration', 128, 'ATSMS:SZCS#VIBL=128#'),
        ('sensitivity', 5, 'ATSMS:SZCS#SENSITIVITY=5#'),
        ('timer_ign_on', 30, 'ATSMS:TIMER,30,#'),
        ('timer_ign_off', 300, 'ATSMS:TIMER,,300#'),
        ('heartbeat_ign_on', 60, 'ATSMS:HBT,60,#'),
        ('heartbeat_ign_off', 300, 'ATSMS:HBT,,300#')
    ]
    
    for param_name, test_value, expected_command in test_cases:
        param = factory.create_parameter(param_name)
        if param:
            # Simulate setting value and sending command
            param.set_value(test_value)
            param.send_command()
            
            if commands_sent and commands_sent[-1] == expected_command:
                print(f"  ✓ {param_name}: Command generated correctly")
                print(f"    Expected: {expected_command}")
                print(f"    Got: {commands_sent[-1]}")
            else:
                print(f"  ✗ {param_name}: Command generation failed")
                print(f"    Expected: {expected_command}")
                print(f"    Got: {commands_sent[-1] if commands_sent else 'No command'}")
        else:
            print(f"  ✗ {param_name}: Parameter creation failed")
    
    print()

def main():
    """Run all tests for Task 3.2."""
    print("=" * 60)
    print("TASK 3.2: NUMERIC PARAMETER CONTROLS TEST")
    print("=" * 60)
    print()
    
    test_vibration_parameter()
    test_sensitivity_parameter()
    test_timer_parameters()
    test_parameter_creation()
    test_command_generation()
    
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()