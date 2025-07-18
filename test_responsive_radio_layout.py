#!/usr/bin/env python3
"""
Test responsive radio button layout at different window sizes.
"""

import customtkinter as ctk
from services.i18n_service import I18nService
from services.validation_service import ValidationService
from ui.parameter_factory import ParameterFactory

class ResponsiveRadioLayoutTest(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Responsive Radio Button Layout Test")
        self.geometry("800x500")
        
        # Initialize services
        self.i18n = I18nService()
        self.i18n.set_language('pt_BR')
        self.validation_service = ValidationService(self.i18n)
        
        def log_command(command):
            print(f"Command: {command}")
        
        # Create parameter factory
        self.factory = ParameterFactory(self.validation_service, self.i18n, log_command)
        
        # Create layout
        self.create_layout()
        
        # Create test widgets
        self.create_test_widgets()
    
    def create_layout(self):
        """Create the main layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        
        # Main scrollable frame
        self.main_frame = ctk.CTkScrollableFrame(self, label_text="Responsive Radio Button Test")
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Control frame
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.control_frame.grid_columnconfigure(0, weight=1)
        
        # Instructions
        instructions = ctk.CTkLabel(
            self.control_frame,
            text="Test different window sizes using the buttons below. Radio buttons should remain visible.",
            font=ctk.CTkFont(size=12)
        )
        instructions.grid(row=0, column=0, padx=10, pady=10)
        
        # Size control buttons
        button_frame = ctk.CTkFrame(self.control_frame)
        button_frame.grid(row=1, column=0, padx=10, pady=(0, 10))
        
        ctk.CTkButton(button_frame, text="Large (1000x600)", 
                     command=lambda: self.resize_window(1000, 600)).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkButton(button_frame, text="Medium (700x500)", 
                     command=lambda: self.resize_window(700, 500)).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(button_frame, text="Small (500x400)", 
                     command=lambda: self.resize_window(500, 400)).grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkButton(button_frame, text="Very Small (400x350)", 
                     command=lambda: self.resize_window(400, 350)).grid(row=0, column=3, padx=5, pady=5)
    
    def create_test_widgets(self):
        """Create test radio button widgets."""
        # Test all radio parameters
        radio_params = ['ignition_type', 'lock_type', 'transmission_mode']
        
        row = 0
        for param_name in radio_params:
            param = self.factory.create_parameter(param_name)
            if param:
                # Parameter title
                definition = self.factory.get_parameter_definition(param_name)
                title_text = self.i18n.get(definition.display_label, definition.display_label)
                
                title_label = ctk.CTkLabel(
                    self.main_frame, 
                    text=f"{title_text} ({param_name})", 
                    font=ctk.CTkFont(size=14, weight="bold")
                )
                title_label.grid(row=row, column=0, padx=10, pady=(20, 5), sticky="w")
                row += 1
                
                # Parameter widget
                widget = param.create_widget(self.main_frame)
                widget.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
                row += 1
                
                # Current value display
                value_label = ctk.CTkLabel(
                    self.main_frame,
                    text=f"Current value: {param.get_value()}",
                    font=ctk.CTkFont(size=10)
                )
                value_label.grid(row=row, column=0, padx=10, pady=(0, 10), sticky="w")
                row += 1
        
        # Instructions at the bottom
        final_instructions = ctk.CTkLabel(
            self.main_frame,
            text="Resize the window using the buttons below to test responsiveness.\nBoth radio button options should remain visible at all sizes.",
            font=ctk.CTkFont(size=12),
            justify="center"
        )
        final_instructions.grid(row=row, column=0, padx=10, pady=20)
    
    def resize_window(self, width, height):
        """Resize the window to test responsive behavior."""
        self.geometry(f"{width}x{height}")
        print(f"Window resized to {width}x{height}")
        
        # Force update to ensure layout recalculates
        self.update_idletasks()

def main():
    """Run the responsive radio layout test."""
    print("Starting Responsive Radio Button Layout Test...")
    print("Use the buttons to resize the window and check if radio buttons remain visible.")
    app = ResponsiveRadioLayoutTest()
    app.mainloop()

if __name__ == "__main__":
    main()