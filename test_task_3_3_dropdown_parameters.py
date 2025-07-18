#!/usr/bin/env python3
"""
Test script for Task 3.3: Add dropdown parameter controls (Heart Beat, Curve Sensor)

This test verifies:
1. Heart Beat interval dropdown with options (30s, 1min, 5min, etc.)
2. Curve Sensor dropdown with Enabled/Disabled/Auto options  
3. Dropdown change handlers that trigger appropriate device commands
"""

import sys
import os
sys.path.append('.')

from ui.parameter_factory import ParameterFactory, DropdownParameter
from services.validation_service import ValidationService
from services.i18n_service import I18nService


def test_dropdown_parameter_creation():
    """Test that dropdown parameters are created correctly."""
    print("=== Testing Dropdown Parameter Creation ===")
    
    # Initialize services
    i18n = I18nService()
    validation_service = ValidationService(i18n)
    
    commands_sent = []
    def capture_command(cmd):
        commands_sent.append(cmd)
        print(f"Command captured: {cmd}")
    
    factory = ParameterFactory(validation_service, i18n, capture_command)
    
    # Test heartbeat interval dropdown
    print("\n1. Testing Heartbeat Interval Dropdown:")
    heartbeat_param = factory.create_parameter('heartbeat_interval')
    
    assert heartbeat_param is not None, "Heartbeat parameter should be created"
    assert isinstance(heartbeat_param, DropdownParameter), "Should be DropdownParameter"
    assert heartbeat_param.definition.param_type == 'dropdown', "Should be dropdown type"
    
    expected_heartbeat_values = ['30s', '1min', '5min', '10min', '30min', '1hr', '2hr', '6hr', '12hr', '24hr']
    actual_heartbeat_values = heartbeat_param.definition.validation_rules.get('allowed_values', [])
    
    print(f"Expected values: {expected_heartbeat_values}")
    print(f"Actual values: {actual_heartbeat_values}")
    assert actual_heartbeat_values == expected_heartbeat_values, "Heartbeat values should match expected"
    
    print("✓ Heartbeat interval dropdown created correctly")
    
    # Test curve sensor dropdown
    print("\n2. Testing Curve Sensor Dropdown:")
    curve_param = factory.create_parameter('curve_sensor')
    
    assert curve_param is not None, "Curve sensor parameter should be created"
    assert isinstance(curve_param, DropdownParameter), "Should be DropdownParameter"
    assert curve_param.definition.param_type == 'dropdown', "Should be dropdown type"
    
    expected_curve_values = ['Enabled', 'Disabled', 'Auto']
    actual_curve_values = curve_param.definition.validation_rules.get('allowed_values', [])
    
    print(f"Expected values: {expected_curve_values}")
    print(f"Actual values: {actual_curve_values}")
    assert actual_curve_values == expected_curve_values, "Curve sensor values should match expected"
    
    print("✓ Curve sensor dropdown created correctly")
    
    return heartbeat_param, curve_param, commands_sent


def test_dropdown_command_generation():
    """Test that dropdown parameters generate correct AT commands."""
    print("\n=== Testing Command Generation ===")
    
    # Initialize services
    i18n = I18nService()
    validation_service = ValidationService(i18n)
    
    commands_sent = []
    def capture_command(cmd):
        commands_sent.append(cmd)
        print(f"Command generated: {cmd}")
    
    factory = ParameterFactory(validation_service, i18n, capture_command)
    
    # Test heartbeat interval commands
    print("\n1. Testing Heartbeat Interval Commands:")
    heartbeat_param = factory.create_parameter('heartbeat_interval')
    
    # Mock widget to simulate dropdown selection
    class MockDropdown:
        def __init__(self, value):
            self.value = value
        def get(self):
            return self.value
    
    # Test different heartbeat interval values
    test_values = ['30s', '1min', '5min', '1hr']
    for value in test_values:
        heartbeat_param.widget = MockDropdown(value)
        heartbeat_param.send_command()
        expected_cmd = f"ATSMS:HBT,{value}#"
        assert commands_sent[-1] == expected_cmd, f"Expected {expected_cmd}, got {commands_sent[-1]}"
        print(f"✓ {value} -> {commands_sent[-1]}")
    
    # Test curve sensor commands
    print("\n2. Testing Curve Sensor Commands:")
    curve_param = factory.create_parameter('curve_sensor')
    
    test_values = ['Enabled', 'Disabled', 'Auto']
    for value in test_values:
        curve_param.widget = MockDropdown(value)
        curve_param.send_command()
        expected_cmd = f"ATSMS:SZCS#CURVE={value}#"
        assert commands_sent[-1] == expected_cmd, f"Expected {expected_cmd}, got {commands_sent[-1]}"
        print(f"✓ {value} -> {commands_sent[-1]}")
    
    print(f"\nTotal commands generated: {len(commands_sent)}")
    return commands_sent


def test_dropdown_validation():
    """Test dropdown parameter validation."""
    print("\n=== Testing Dropdown Validation ===")
    
    # Initialize services
    i18n = I18nService()
    validation_service = ValidationService(i18n)
    
    # Test heartbeat interval validation
    print("\n1. Testing Heartbeat Interval Validation:")
    
    # Valid values
    valid_values = ['30s', '1min', '5min', '10min', '30min', '1hr', '2hr', '6hr', '12hr', '24hr']
    for value in valid_values:
        result = validation_service.validate_parameter('heartbeat_interval', value)
        assert result.is_valid, f"Value {value} should be valid"
        print(f"✓ {value} is valid")
    
    # Invalid values
    invalid_values = ['15s', '2min', '3hr', 'invalid']
    for value in invalid_values:
        result = validation_service.validate_parameter('heartbeat_interval', value)
        assert not result.is_valid, f"Value {value} should be invalid"
        print(f"✓ {value} is invalid (as expected)")
    
    # Test curve sensor validation
    print("\n2. Testing Curve Sensor Validation:")
    
    # Valid values
    valid_values = ['Enabled', 'Disabled', 'Auto']
    for value in valid_values:
        result = validation_service.validate_parameter('curve_sensor', value)
        assert result.is_valid, f"Value {value} should be valid"
        print(f"✓ {value} is valid")
    
    # Invalid values
    invalid_values = ['On', 'Off', 'Manual', 'invalid']
    for value in invalid_values:
        result = validation_service.validate_parameter('curve_sensor', value)
        assert not result.is_valid, f"Value {value} should be invalid"
        print(f"✓ {value} is invalid (as expected)")


def test_integration_with_parameters_frame():
    """Test integration with ParametersFrame."""
    print("\n=== Testing Integration with ParametersFrame ===")
    
    try:
        from main import App
        import customtkinter as ctk
        
        # Create app instance
        app = App()
        
        # Check that parameters frame has the dropdown parameters
        params_frame = app.params_frame
        assert hasattr(params_frame, 'parameter_widgets'), "Parameters frame should have parameter_widgets"
        
        widgets = params_frame.parameter_widgets
        print(f"Available parameter widgets: {list(widgets.keys())}")
        
        # Check heartbeat interval
        assert 'heartbeat_interval' in widgets, "Heartbeat interval should be in parameter widgets"
        heartbeat_widget = widgets['heartbeat_interval']
        assert isinstance(heartbeat_widget, DropdownParameter), "Should be DropdownParameter instance"
        print("✓ Heartbeat interval dropdown integrated correctly")
        
        # Check curve sensor
        assert 'curve_sensor' in widgets, "Curve sensor should be in parameter widgets"
        curve_widget = widgets['curve_sensor']
        assert isinstance(curve_widget, DropdownParameter), "Should be DropdownParameter instance"
        print("✓ Curve sensor dropdown integrated correctly")
        
        print("✓ Integration test passed")
        
    except Exception as e:
        print(f"Integration test failed: {e}")
        raise


def main():
    """Run all tests for Task 3.3."""
    print("Testing Task 3.3: Add dropdown parameter controls (Heart Beat, Curve Sensor)")
    print("=" * 80)
    
    try:
        # Test 1: Parameter creation
        heartbeat_param, curve_param, commands = test_dropdown_parameter_creation()
        
        # Test 2: Command generation
        commands = test_dropdown_command_generation()
        
        # Test 3: Validation
        test_dropdown_validation()
        
        # Test 4: Integration
        test_integration_with_parameters_frame()
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("Task 3.3 implementation is working correctly:")
        print("  ✓ Heart Beat interval dropdown with all required options")
        print("  ✓ Curve Sensor dropdown with Enabled/Disabled/Auto options")
        print("  ✓ Dropdown change handlers trigger appropriate device commands")
        print("  ✓ Proper validation and error handling")
        print("  ✓ Integration with main application")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)