#!/usr/bin/env python3
"""
Simple test to verify that both Digital and Analog radio buttons are visible for ignition type.
"""

import customtkinter as ctk
from services.i18n_service import I18nService
from services.validation_service import ValidationService
from ui.parameter_factory import ParameterFactory

class IgnitionTypeVisibilityTest(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Ignition Type Visibility Test - Tipo de Ignição")
        self.geometry("700x400")
        
        # Initialize services
        self.i18n = I18nService()
        self.i18n.set_language('pt_BR')
        self.validation_service = ValidationService(self.i18n)
        
        def log_command(command):
            print(f"Command: {command}")
            self.status_label.configure(text=f"Command: {command}")
        
        # Create parameter factory
        self.factory = ParameterFactory(self.validation_service, self.i18n, log_command)
        
        # Create layout
        self.create_layout()
        
        # Create ignition type parameter
        self.create_ignition_type_widget()
    
    def create_layout(self):
        """Create the main layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        
        # Main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title = ctk.CTkLabel(
            self.main_frame, 
            text="Ignition Type Radio Button Visibility Test", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=20)
        
        # Instructions
        instructions = ctk.CTkLabel(
            self.main_frame,
            text="Both 'Digital' and 'Analog' radio buttons should be visible below:",
            font=ctk.CTkFont(size=12)
        )
        instructions.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Status label
        self.status_label = ctk.CTkLabel(self, text="Ready", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=1, column=0, padx=20, pady=(0, 20))
    
    def create_ignition_type_widget(self):
        """Create the ignition type parameter widget."""
        # Create ignition_type parameter
        ignition_param = self.factory.create_parameter('ignition_type')
        
        if ignition_param:
            # Get parameter info
            definition = self.factory.get_parameter_definition('ignition_type')
            allowed_values = definition.validation_rules.get('allowed_values', [])
            
            print(f"Creating ignition_type parameter with values: {allowed_values}")
            
            # Create widget
            widget = ignition_param.create_widget(self.main_frame)
            widget.grid(row=2, column=0, padx=20, pady=20, sticky="ew")
            
            # Test buttons
            test_frame = ctk.CTkFrame(self.main_frame)
            test_frame.grid(row=3, column=0, padx=20, pady=20, sticky="ew")
            
            # Current value display
            self.value_label = ctk.CTkLabel(test_frame, text="Current: Digital", font=ctk.CTkFont(size=12))
            self.value_label.grid(row=0, column=0, padx=10, pady=10)
            
            # Test buttons
            digital_btn = ctk.CTkButton(
                test_frame,
                text="Select Digital",
                command=lambda: self.test_selection(ignition_param, "Digital")
            )
            digital_btn.grid(row=0, column=1, padx=10, pady=10)
            
            analog_btn = ctk.CTkButton(
                test_frame,
                text="Select Analog",
                command=lambda: self.test_selection(ignition_param, "Analog")
            )
            analog_btn.grid(row=0, column=2, padx=10, pady=10)
            
            get_value_btn = ctk.CTkButton(
                test_frame,
                text="Get Current Value",
                command=lambda: self.get_current_value(ignition_param)
            )
            get_value_btn.grid(row=0, column=3, padx=10, pady=10)
            
            # Store parameter reference
            self.ignition_param = ignition_param
            
        else:
            error_label = ctk.CTkLabel(
                self.main_frame, 
                text="Failed to create ignition_type parameter",
                text_color="red"
            )
            error_label.grid(row=2, column=0, padx=20, pady=20)
    
    def test_selection(self, parameter, value):
        """Test selecting a specific value."""
        parameter.set_value(value)
        current = parameter.get_value()
        self.value_label.configure(text=f"Current: {current}")
        print(f"Set to {value}, current value: {current}")
    
    def get_current_value(self, parameter):
        """Get and display current value."""
        current = parameter.get_value()
        self.value_label.configure(text=f"Current: {current}")
        print(f"Current value: {current}")

def main():
    """Run the ignition type visibility test."""
    print("Starting Ignition Type Visibility Test...")
    app = IgnitionTypeVisibilityTest()
    app.mainloop()

if __name__ == "__main__":
    main()