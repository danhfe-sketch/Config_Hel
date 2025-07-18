#!/usr/bin/env python3
"""
Integration test for Task 3.4: Radio button group controls in the main application

This test verifies that the radio button groups are properly integrated into the 
main ParametersFrame and work correctly within the full application context.
"""

import sys
import os
sys.path.append('.')

import customtkinter as ctk
from ui.parameters_frame import ParametersFrame
from services.i18n_service import I18nService


class MockSerialService:
    """Mock serial service for testing."""
    
    def __init__(self):
        self.sent_commands = []
        self.is_connected = True
    
    def send_command(self, command: str):
        """Mock send command method."""
        self.sent_commands.append(command)
        print(f"Mock Serial: {command}")


class MockMaster:
    """Mock master window for testing."""
    
    def __init__(self):
        self.serial_service = MockSerialService()


def test_radio_buttons_in_parameters_frame():
    """Test that radio button groups are properly integrated in ParametersFrame."""
    print("=== Testing Radio Button Integration in ParametersFrame ===")
    
    # Create services
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create main window for testing
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.withdraw()  # Hide the window
    
    # Add serial service to root for compatibility
    root.serial_service = MockSerialService()
    
    try:
        # Create ParametersFrame using root as master
        params_frame = ParametersFrame(root, i18n)
        
        # Verify that radio parameters are in the parameter widgets
        expected_radio_params = ['lock_type', 'ignition_type', 'transmission_mode']
        
        for param_name in expected_radio_params:
            assert param_name in params_frame.parameter_widgets, f"Radio parameter {param_name} not found in parameter_widgets"
            parameter = params_frame.parameter_widgets[param_name]
            assert parameter is not None, f"Parameter {param_name} is None"
            print(f"  ✓ {param_name} parameter found and created")
        
        # Test getting all parameter values (should include radio parameters)
        all_values = params_frame.get_all_parameter_values()
        
        for param_name in expected_radio_params:
            assert param_name in all_values, f"Radio parameter {param_name} not in get_all_parameter_values()"
            value = all_values[param_name]
            assert value is not None, f"Radio parameter {param_name} has None value"
            print(f"  ✓ {param_name} current value: {value}")
        
        # Test setting parameter values
        test_values = {
            'lock_type': 'Card',
            'ignition_type': 'Analog',
            'transmission_mode': 'UDP'
        }
        
        params_frame.set_all_parameter_values(test_values)
        
        # Verify values were set
        updated_values = params_frame.get_all_parameter_values()
        for param_name, expected_value in test_values.items():
            actual_value = updated_values.get(param_name)
            assert actual_value == expected_value, f"Expected {param_name}={expected_value}, got {actual_value}"
            print(f"  ✓ {param_name} set to: {actual_value}")
        
        # Test sending commands
        print("\n  Testing command sending:")
        initial_command_count = len(root.serial_service.sent_commands)
        
        # Send commands for each radio parameter
        for param_name in expected_radio_params:
            parameter = params_frame.parameter_widgets[param_name]
            parameter.send_command()
        
        # Verify commands were sent
        final_command_count = len(root.serial_service.sent_commands)
        commands_sent = final_command_count - initial_command_count
        assert commands_sent == len(expected_radio_params), f"Expected {len(expected_radio_params)} commands, got {commands_sent}"
        
        # Verify command format
        recent_commands = root.serial_service.sent_commands[-commands_sent:]
        expected_command_patterns = {
            'lock_type': 'ATSMS:SZCS#LOCKTYPE=',
            'ignition_type': 'ATSMS:SZCS#ACCLINE=',
            'transmission_mode': 'ATSMS:SZCS#PROTOCOL='
        }
        
        for command in recent_commands:
            found_pattern = False
            for param_name, pattern in expected_command_patterns.items():
                if pattern in command:
                    print(f"  ✓ {param_name} command: {command}")
                    found_pattern = True
                    break
            assert found_pattern, f"Command '{command}' doesn't match any expected pattern"
        
        print("\n✅ Radio button integration test passed!")
        
    finally:
        root.destroy()


def test_radio_button_groups_in_ui():
    """Test that radio button groups are properly organized in UI groups."""
    print("\n=== Testing Radio Button Group Organization ===")
    
    # Create services
    i18n = I18nService()
    i18n.set_language('en_US')
    
    # Create main window for testing
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.withdraw()  # Hide the window
    
    # Add serial service to root for compatibility
    root.serial_service = MockSerialService()
    
    try:
        # Create ParametersFrame using root as master
        params_frame = ParametersFrame(root, i18n)
        
        # Check that parameter factory has the correct groups
        factory = params_frame.parameter_factory
        groups = factory.get_all_groups()
        
        # Verify expected groups exist
        expected_groups = ['security', 'sensors', 'communication']
        for group_name in expected_groups:
            assert group_name in groups, f"Group {group_name} not found"
            group = groups[group_name]
            assert group is not None, f"Group {group_name} is None"
            print(f"  ✓ Group '{group_name}' exists")
        
        # Verify radio parameters are in correct groups
        group_param_mapping = {
            'security': ['lock_type'],
            'sensors': ['ignition_type'],
            'communication': ['transmission_mode']
        }
        
        for group_name, expected_params in group_param_mapping.items():
            group = groups[group_name]
            group_param_names = [param.definition.name for param in group.parameters]
            
            for param_name in expected_params:
                assert param_name in group_param_names, f"Parameter {param_name} not found in group {group_name}"
                print(f"  ✓ {param_name} is in {group_name} group")
        
        print("\n✅ Radio button group organization test passed!")
        
    finally:
        root.destroy()


def main():
    """Run all integration tests."""
    print("Testing Task 3.4: Radio Button Groups Integration")
    print("=" * 60)
    
    try:
        test_radio_buttons_in_parameters_frame()
        test_radio_button_groups_in_ui()
        
        print("\n" + "=" * 60)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("\nTask 3.4 Implementation Summary:")
        print("✅ Lock Type radio buttons (PIN/Card) - implemented in Security group")
        print("✅ Ignition Type radio buttons (Digital/Analog) - implemented in Sensors group")
        print("✅ Protocol radio buttons (TCP/UDP) - implemented in Communication group")
        print("\nFeatures verified:")
        print("✅ Proper integration with ParametersFrame")
        print("✅ Correct AT command generation")
        print("✅ Value get/set functionality")
        print("✅ Proper UI group organization")
        print("✅ Command sending functionality")
        
        return True
        
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)