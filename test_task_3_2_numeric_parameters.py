#!/usr/bin/env python3
"""
Final test for Task 3.2: Visual test of numeric parameter controls.
This creates a simple UI to verify the layout fixes are working.
"""

import customtkinter as ctk
from services.i18n_service import I18nService
from services.validation_service import ValidationService
from ui.parameter_factory import ParameterFactory

class NumericParameterTestApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Task 3.2: Numeric Parameter Controls Test")
        self.geometry("900x700")
        
        # Initialize services
        self.i18n = I18nService()
        self.i18n.set_language('pt_BR')
        self.validation_service = ValidationService(self.i18n)
        
        # Command log
        self.command_log = []
        
        def log_command(command):
            self.command_log.append(command)
            print(f"Command sent: {command}")
            self.update_log_display()
        
        # Create parameter factory
        self.factory = ParameterFactory(self.validation_service, self.i18n, log_command)
        
        # Create main layout
        self.create_layout()
        
        # Create parameter widgets
        self.create_parameter_widgets()
    
    def create_layout(self):
        """Create the main layout."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        
        # Main scrollable frame
        self.main_frame = ctk.CTkScrollableFrame(self, label_text="Numeric Parameter Controls")
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Command log frame
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        
        # Log label
        log_label = ctk.CTkLabel(self.log_frame, text="Command Log:", font=ctk.CTkFont(weight="bold"))
        log_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # Log display
        self.log_display = ctk.CTkTextbox(self.log_frame, height=100)
        self.log_display.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
    
    def create_parameter_widgets(self):
        """Create all numeric parameter widgets."""
        # Group configurations
        groups = [
            {
                'title': 'Sensor Configuration',
                'params': ['vibration', 'sensitivity']
            },
            {
                'title': 'Timer Configuration',
                'params': ['timer_ign_on', 'timer_ign_off', 'heartbeat_ign_on', 'heartbeat_ign_off']
            }
        ]
        
        row = 0
        
        for group in groups:
            # Group title
            title_label = ctk.CTkLabel(
                self.main_frame, 
                text=group['title'], 
                font=ctk.CTkFont(size=16, weight="bold")
            )
            title_label.grid(row=row, column=0, padx=10, pady=(20, 10), sticky="w")
            row += 1
            
            # Group frame
            group_frame = ctk.CTkFrame(self.main_frame)
            group_frame.grid(row=row, column=0, padx=10, pady=(0, 10), sticky="ew")
            group_frame.grid_columnconfigure(0, weight=1)
            row += 1
            
            # Parameters in group
            param_row = 0
            for param_name in group['params']:
                param = self.factory.create_parameter(param_name)
                if param:
                    widget = param.create_widget(group_frame)
                    widget.grid(row=param_row, column=0, padx=10, pady=5, sticky="ew")
                    param_row += 1
        
        # Test button
        test_button = ctk.CTkButton(
            self.main_frame,
            text="Test All Parameters with Default Values",
            command=self.test_all_parameters
        )
        test_button.grid(row=row, column=0, padx=10, pady=20)
    
    def test_all_parameters(self):
        """Test all parameters with their default values."""
        test_params = ['vibration', 'sensitivity', 'timer_ign_on', 'timer_ign_off', 'heartbeat_ign_on', 'heartbeat_ign_off']
        
        for param_name in test_params:
            param = self.factory.create_parameter(param_name)
            if param:
                definition = self.factory.get_parameter_definition(param_name)
                if definition and definition.default_value is not None:
                    # Simulate command generation
                    command = definition.at_command_template.format(value=definition.default_value)
                    self.command_log.append(f"TEST: {command}")
        
        self.update_log_display()
    
    def update_log_display(self):
        """Update the command log display."""
        self.log_display.delete("1.0", ctk.END)
        for command in self.command_log[-10:]:  # Show last 10 commands
            self.log_display.insert(ctk.END, command + "\n")

def main():
    """Run the numeric parameter test application."""
    print("Starting Task 3.2 Numeric Parameter Test...")
    app = NumericParameterTestApp()
    app.mainloop()

if __name__ == "__main__":
    main()