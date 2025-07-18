#!/usr/bin/env python3
"""
Visual test for Task 3.4: Radio button group controls (Lock Type, Ignition Type, Protocol)

This test creates a visual window to verify that the radio button groups are properly displayed
and functional in the actual application UI.
"""

import sys
import os
sys.path.append('.')

import customtkinter as ctk
from ui.parameter_factory import ParameterFactory
from services.validation_service import ValidationService
from services.i18n_service import I18nService


class RadioButtonTestApp:
    """Test application to visually verify radio button groups."""
    
    def __init__(self):
        # Create services
        self.i18n = I18nService()
        self.i18n.set_language('en_US')
        self.validation = ValidationService(self.i18n)
        
        # Store sent commands for display
        self.sent_commands = []
        
        # Create parameter factory
        self.factory = ParameterFactory(
            self.validation, 
            self.i18n, 
            self._command_callback
        )
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("Task 3.4: Radio Button Groups Test")
        self.root.geometry("800x600")
        
        # Set appearance
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        
        self._create_ui()
    
    def _command_callback(self, command: str):
        """Callback for when commands are sent."""
        self.sent_commands.append(command)
        print(f"Command sent: {command}")
        
        # Update the command log display
        self._update_command_log()
    
    def _create_ui(self):
        """Create the test UI."""
        # Main container
        main_frame = ctk.CTkScrollableFrame(self.root, label_text="Radio Button Groups Test")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            main_frame, 
            text="Task 3.4: Radio Button Group Controls", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.grid(row=0, column=0, pady=(0, 20), sticky="w")
        
        # Description
        desc = ctk.CTkLabel(
            main_frame,
            text="This test verifies the implementation of radio button groups for Lock Type, Ignition Type, and Protocol selection.",
            font=ctk.CTkFont(size=12),
            wraplength=750
        )
        desc.grid(row=1, column=0, pady=(0, 20), sticky="w")
        
        # Create parameter groups
        self._create_parameter_groups(main_frame)
        
        # Command log section
        self._create_command_log(main_frame)
        
        # Test buttons
        self._create_test_buttons(main_frame)
    
    def _create_parameter_groups(self, parent):
        """Create the parameter groups with radio buttons."""
        # Security Settings Group (Lock Type)
        security_group = self.factory.create_group('security', 'Security Settings')
        lock_type_param = self.factory.create_parameter('lock_type')
        if lock_type_param:
            security_group.add_parameter(lock_type_param)
            security_widget = security_group.create_widget(parent)
            security_widget.grid(row=2, column=0, pady=10, sticky="ew")
        
        # Sensor Configuration Group (Ignition Type)
        sensor_group = self.factory.create_group('sensors', 'Sensor Configuration')
        ignition_param = self.factory.create_parameter('ignition_type')
        if ignition_param:
            sensor_group.add_parameter(ignition_param)
            sensor_widget = sensor_group.create_widget(parent)
            sensor_widget.grid(row=3, column=0, pady=10, sticky="ew")
        
        # Communication Settings Group (Protocol)
        comm_group = self.factory.create_group('communication', 'Communication Settings')
        protocol_param = self.factory.create_parameter('transmission_mode')
        if protocol_param:
            comm_group.add_parameter(protocol_param)
            comm_widget = comm_group.create_widget(parent)
            comm_widget.grid(row=4, column=0, pady=10, sticky="ew")
        
        # Store parameters for testing
        self.parameters = {
            'lock_type': lock_type_param,
            'ignition_type': ignition_param,
            'transmission_mode': protocol_param
        }
    
    def _create_command_log(self, parent):
        """Create command log display."""
        log_frame = ctk.CTkFrame(parent)
        log_frame.grid(row=5, column=0, pady=20, sticky="ew")
        log_frame.grid_columnconfigure(0, weight=1)
        
        log_title = ctk.CTkLabel(log_frame, text="Command Log", font=ctk.CTkFont(weight="bold"))
        log_title.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.command_log = ctk.CTkTextbox(log_frame, height=150)
        self.command_log.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        # Clear log button
        clear_btn = ctk.CTkButton(log_frame, text="Clear Log", command=self._clear_log)
        clear_btn.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")
    
    def _create_test_buttons(self, parent):
        """Create test buttons."""
        test_frame = ctk.CTkFrame(parent)
        test_frame.grid(row=6, column=0, pady=20, sticky="ew")
        test_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        test_title = ctk.CTkLabel(test_frame, text="Test Functions", font=ctk.CTkFont(weight="bold"))
        test_title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")
        
        # Test buttons
        test_values_btn = ctk.CTkButton(
            test_frame, 
            text="Test Get Values", 
            command=self._test_get_values
        )
        test_values_btn.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        test_set_btn = ctk.CTkButton(
            test_frame, 
            text="Test Set Values", 
            command=self._test_set_values
        )
        test_set_btn.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        test_validation_btn = ctk.CTkButton(
            test_frame, 
            text="Test Validation", 
            command=self._test_validation
        )
        test_validation_btn.grid(row=1, column=2, padx=10, pady=10, sticky="ew")
    
    def _update_command_log(self):
        """Update the command log display."""
        self.command_log.delete("1.0", "end")
        for i, command in enumerate(self.sent_commands, 1):
            self.command_log.insert("end", f"{i}. {command}\n")
        
        # Scroll to bottom
        self.command_log.see("end")
    
    def _clear_log(self):
        """Clear the command log."""
        self.sent_commands.clear()
        self.command_log.delete("1.0", "end")
    
    def _test_get_values(self):
        """Test getting current values from radio buttons."""
        values = {}
        for name, param in self.parameters.items():
            if param:
                values[name] = param.get_value()
        
        result = "Current Values:\n"
        for name, value in values.items():
            result += f"  {name}: {value}\n"
        
        print(result)
        self.command_log.insert("end", f"\n{result}")
        self.command_log.see("end")
    
    def _test_set_values(self):
        """Test setting values in radio buttons."""
        test_values = {
            'lock_type': 'Card',
            'ignition_type': 'Analog', 
            'transmission_mode': 'UDP'
        }
        
        result = "Setting test values:\n"
        for name, value in test_values.items():
            if name in self.parameters and self.parameters[name]:
                self.parameters[name].set_value(value)
                result += f"  {name}: {value}\n"
        
        print(result)
        self.command_log.insert("end", f"\n{result}")
        self.command_log.see("end")
    
    def _test_validation(self):
        """Test validation of radio button values."""
        test_cases = [
            ('lock_type', 'PIN', True),
            ('lock_type', 'Invalid', False),
            ('ignition_type', 'Digital', True),
            ('ignition_type', 'Invalid', False),
            ('transmission_mode', 'TCP', True),
            ('transmission_mode', 'HTTP', False),
        ]
        
        result = "Validation Tests:\n"
        for param_name, value, expected_valid in test_cases:
            validation_result = self.validation.validate_parameter(param_name, value)
            status = "✓" if validation_result.is_valid == expected_valid else "✗"
            result += f"  {status} {param_name}='{value}': {'Valid' if validation_result.is_valid else 'Invalid'}\n"
            if not validation_result.is_valid:
                result += f"    Error: {validation_result.error_message}\n"
        
        print(result)
        self.command_log.insert("end", f"\n{result}")
        self.command_log.see("end")
    
    def run(self):
        """Run the test application."""
        print("Starting Radio Button Groups Visual Test...")
        print("Instructions:")
        print("1. Verify that all three radio button groups are displayed")
        print("2. Test clicking different radio buttons in each group")
        print("3. Click 'Send' buttons to verify AT commands are generated")
        print("4. Use test buttons to verify get/set functionality")
        print("5. Close window when testing is complete")
        print()
        
        self.root.mainloop()


def main():
    """Run the visual test."""
    try:
        app = RadioButtonTestApp()
        app.run()
        print("\nVisual test completed successfully!")
        return True
    except Exception as e:
        print(f"Visual test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)