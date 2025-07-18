#!/usr/bin/env python3
"""
Test script for Task 3.4: Radio button group controls (Lock Type, Ignition Type, Protocol)

This test verifies that the radio button groups are properly implemented and functional.
"""

import sys
import os
sys.path.append('.')

import customtkinter as ctk
from ui.parameter_factory import ParameterFactory, RadioParameter
from services.validation_service import ValidationService
from services.i18n_service import I18nService


def test_radio_parameter_definitions():
    """Test that radio parameters are properly defined."""
    print("=== Testing Radio Parameter Definitions ===")
    
    # Create services
    i18n = I18nService()
    i18n.set_language('en_US')
    validation = ValidationService(i18n)
    factory = ParameterFactory(validation, i18n, lambda x: print(f"Command sent: {x}"))
    
    # Test each required radio parameter
    required_radio_params = {
        'lock_type': ['PIN', 'Card'],
        'ignition_type': ['Digital', 'Analog'], 
        'transmission_mode': ['TCP', 'UDP']
    }
    
    for param_name, expected_values in required_radio_params.items():
        print(f"\nTesting {param_name}:")
        
        # Check parameter definition exists
        definition = factory.get_parameter_definition(param_name)
        assert definition is not None, f"Parameter definition for {param_name} not found"
        print(f"  ✓ Definition exists")
        
        # Check parameter type is radio
        assert definition.param_type == 'radio', f"Parameter {param_name} should be radio type, got {definition.param_type}"
        print(f"  ✓ Type is 'radio'")
        
        # Check allowed values
        allowed_values = definition.validation_rules.get('allowed_values', [])
        assert allowed_values == expected_values, f"Expected {expected_values}, got {allowed_values}"
        print(f"  ✓ Allowed values: {allowed_values}")
        
        # Check AT command template
        assert definition.at_command_template, f"AT command template missing for {param_name}"
        print(f"  ✓ AT command template: {definition.at_command_template}")
        
        # Test parameter creation
        parameter = factory.create_parameter(param_name)
        assert parameter is not None, f"Failed to create parameter {param_name}"
        assert isinstance(parameter, RadioParameter), f"Parameter {param_name} should be RadioParameter instance"
        print(f"  ✓ Parameter creation successful")
    
    print("\n✅ All radio parameter definitions are correct!")


def test_radio_parameter_validation():
    """Test radio parameter validation."""
    print("\n=== Testing Radio Parameter Validation ===")
    
    # Create services
    i18n = I18nService()
    i18n.set_language('en_US')
    validation = ValidationService(i18n)
    
    test_cases = [
        ('lock_type', 'PIN', True),
        ('lock_type', 'Card', True),
        ('lock_type', 'Invalid', False),
        ('ignition_type', 'Digital', True),
        ('ignition_type', 'Analog', True),
        ('ignition_type', 'Invalid', False),
        ('transmission_mode', 'TCP', True),
        ('transmission_mode', 'UDP', True),
        ('transmission_mode', 'HTTP', False),
    ]
    
    for param_name, value, should_be_valid in test_cases:
        result = validation.validate_parameter(param_name, value)
        if should_be_valid:
            assert result.is_valid, f"Expected {param_name}='{value}' to be valid, but got: {result.error_message}"
            print(f"  ✓ {param_name}='{value}' is valid")
        else:
            assert not result.is_valid, f"Expected {param_name}='{value}' to be invalid, but it was accepted"
            print(f"  ✓ {param_name}='{value}' is invalid (as expected)")
    
    print("\n✅ All radio parameter validation tests passed!")


def test_radio_parameter_at_commands():
    """Test that radio parameters generate correct AT commands."""
    print("\n=== Testing Radio Parameter AT Commands ===")
    
    # Create services
    i18n = I18nService()
    i18n.set_language('en_US')
    validation = ValidationService(i18n)
    
    sent_commands = []
    def command_callback(command):
        sent_commands.append(command)
        print(f"  Command sent: {command}")
    
    factory = ParameterFactory(validation, i18n, command_callback)
    
    # Test AT command generation for each radio parameter
    test_cases = [
        ('lock_type', 'PIN', 'ATSMS:SZCS#LOCKTYPE=PIN#'),
        ('ignition_type', 'Digital', 'ATSMS:SZCS#ACCLINE=Digital#'),
        ('transmission_mode', 'TCP', 'ATSMS:SZCS#PROTOCOL=TCP#'),
    ]
    
    for param_name, value, expected_command in test_cases:
        print(f"\nTesting {param_name} = {value}:")
        
        # Create parameter
        parameter = factory.create_parameter(param_name)
        assert parameter is not None, f"Failed to create parameter {param_name}"
        
        # Set value
        parameter.set_value(value)
        
        # Get value to verify it was set
        actual_value = parameter.get_value()
        assert actual_value == value, f"Expected value {value}, got {actual_value}"
        print(f"  ✓ Value set correctly: {actual_value}")
        
        # Clear previous commands
        sent_commands.clear()
        
        # Send command
        parameter.send_command()
        
        # Verify command was sent
        assert len(sent_commands) == 1, f"Expected 1 command, got {len(sent_commands)}"
        assert sent_commands[0] == expected_command, f"Expected '{expected_command}', got '{sent_commands[0]}'"
        print(f"  ✓ Correct AT command generated")
    
    print("\n✅ All radio parameter AT command tests passed!")


def test_radio_parameter_ui_creation():
    """Test that radio parameter UI widgets can be created."""
    print("\n=== Testing Radio Parameter UI Creation ===")
    
    # Create services
    i18n = I18nService()
    i18n.set_language('en_US')
    validation = ValidationService(i18n)
    factory = ParameterFactory(validation, i18n, lambda x: None)
    
    # Create a test window
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.withdraw()  # Hide the window
    
    try:
        for param_name in ['lock_type', 'ignition_type', 'transmission_mode']:
            print(f"\nTesting UI creation for {param_name}:")
            
            # Create parameter
            parameter = factory.create_parameter(param_name)
            assert parameter is not None, f"Failed to create parameter {param_name}"
            
            # Create widget
            widget = parameter.create_widget(root)
            assert widget is not None, f"Failed to create widget for {param_name}"
            print(f"  ✓ Widget created successfully")
            
            # Check that radio buttons were created
            assert hasattr(parameter, 'radio_buttons'), f"Radio buttons not created for {param_name}"
            assert len(parameter.radio_buttons) > 0, f"No radio buttons found for {param_name}"
            print(f"  ✓ Radio buttons created: {len(parameter.radio_buttons)} buttons")
            
            # Check that radio variable exists
            assert hasattr(parameter, 'radio_var'), f"Radio variable not created for {param_name}"
            print(f"  ✓ Radio variable created")
            
            # Test getting/setting values
            definition = factory.get_parameter_definition(param_name)
            allowed_values = definition.validation_rules.get('allowed_values', [])
            
            if allowed_values:
                test_value = allowed_values[0]
                parameter.set_value(test_value)
                actual_value = parameter.get_value()
                assert actual_value == test_value, f"Expected {test_value}, got {actual_value}"
                print(f"  ✓ Value get/set works: {actual_value}")
    
    finally:
        root.destroy()
    
    print("\n✅ All radio parameter UI creation tests passed!")


def main():
    """Run all tests for Task 3.4."""
    print("Testing Task 3.4: Radio button group controls (Lock Type, Ignition Type, Protocol)")
    print("=" * 80)
    
    try:
        test_radio_parameter_definitions()
        test_radio_parameter_validation()
        test_radio_parameter_at_commands()
        test_radio_parameter_ui_creation()
        
        print("\n" + "=" * 80)
        print("🎉 ALL TESTS PASSED! Task 3.4 is successfully implemented!")
        print("\nImplemented radio button groups:")
        print("  • Lock Type: PIN/Card selection")
        print("  • Ignition Type: Digital/Analog selection") 
        print("  • Protocol: TCP/UDP selection")
        print("\nFeatures verified:")
        print("  ✓ Parameter definitions with correct allowed values")
        print("  ✓ Input validation for all radio options")
        print("  ✓ Proper AT command generation")
        print("  ✓ UI widget creation with radio buttons")
        print("  ✓ Value get/set functionality")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)