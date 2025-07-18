#!/usr/bin/env python3
"""
Test script to debug radio button functionality.
"""

import customtkinter as ctk
from services.i18n_service import I18nService
from services.validation_service import ValidationService
from ui.parameter_factory import ParameterFactory

class RadioButtonTestApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Radio Button Test - Tipo de Ignição")
        self.geometry("600x400")
        
        # Initialize services
        self.i18n = I18nService()
        self.i18n.set_language('pt_BR')
        self.validation_service = ValidationService(self.i18n)
        
        # Command log
        self.command_log = []
        
        def log_command(command):
            self.command_log.append(command)
            print(f"Command sent: {command}")
            self.update_status(f"Command sent: {command}")
        
        # Create parameter factory
        self.factory = ParameterFactory(self.validation_service, self.i18n, log_command)
        
        # Create layout
        self.create_layout()
        
        # Create radio button parameters
        self.create_radio_parameters()
    
    def create_layout(self):
        """Create the main layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        
        # Main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Status label
        self.status_label = ctk.CTkLabel(self, text="Status: Ready", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=1, column=0, padx=20, pady=(0, 20))
    
    def create_radio_parameters(self):
        """Create radio button parameters for testing."""
        # Test ignition type parameter
        print("Creating ignition_type parameter...")
        ignition_param = self.factory.create_parameter('ignition_type')
        
        if ignition_param:
            print("✓ ignition_type parameter created successfully")
            
            # Get validation rules to check allowed values
            definition = self.factory.get_parameter_definition('ignition_type')
            print(f"Parameter definition: {definition}")
            print(f"Validation rules: {definition.validation_rules}")
            
            # Create widget
            widget = ignition_param.create_widget(self.main_frame)
            widget.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
            
            # Test buttons
            test_frame = ctk.CTkFrame(self.main_frame)
            test_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
            
            # Get current value button
            get_value_btn = ctk.CTkButton(
                test_frame,
                text="Get Current Value",
                command=lambda: self.test_get_value(ignition_param)
            )
            get_value_btn.grid(row=0, column=0, padx=5, pady=5)
            
            # Set to Digital button
            set_digital_btn = ctk.CTkButton(
                test_frame,
                text="Set to Digital",
                command=lambda: self.test_set_value(ignition_param, "Digital")
            )
            set_digital_btn.grid(row=0, column=1, padx=5, pady=5)
            
            # Set to Analog button
            set_analog_btn = ctk.CTkButton(
                test_frame,
                text="Set to Analog",
                command=lambda: self.test_set_value(ignition_param, "Analog")
            )
            set_analog_btn.grid(row=0, column=2, padx=5, pady=5)
            
            # Send command button
            send_cmd_btn = ctk.CTkButton(
                test_frame,
                text="Send Command",
                command=lambda: self.test_send_command(ignition_param)
            )
            send_cmd_btn.grid(row=0, column=3, padx=5, pady=5)
            
        else:
            print("✗ Failed to create ignition_type parameter")
            error_label = ctk.CTkLabel(self.main_frame, text="Failed to create ignition_type parameter")
            error_label.grid(row=0, column=0, padx=10, pady=10)
    
    def test_get_value(self, parameter):
        """Test getting the current value from radio buttons."""
        value = parameter.get_value()
        self.update_status(f"Current value: {value}")
        print(f"Current value: {value}")
    
    def test_set_value(self, parameter, value):
        """Test setting a value in radio buttons."""
        parameter.set_value(value)
        self.update_status(f"Set value to: {value}")
        print(f"Set value to: {value}")
    
    def test_send_command(self, parameter):
        """Test sending command."""
        parameter.send_command()
        self.update_status("Send command triggered")
        print("Send command triggered")
    
    def update_status(self, message):
        """Update status label."""
        self.status_label.configure(text=f"Status: {message}")

def main():
    """Run the radio button test."""
    print("Starting Radio Button Test...")
    app = RadioButtonTestApp()
    app.mainloop()

if __name__ == "__main__":
    main()