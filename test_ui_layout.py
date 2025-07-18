#!/usr/bin/env python3
"""
Test script for UI layout of numeric parameters.
"""

import customtkinter as ctk
from services.i18n_service import I18nService
from services.validation_service import ValidationService
from ui.parameter_factory import ParameterFactory

class TestApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Test Numeric Parameters Layout")
        self.geometry("800x600")
        
        # Initialize services
        self.i18n = I18nService()
        self.i18n.set_language('pt_BR')
        self.validation_service = ValidationService(self.i18n)
        
        def mock_send_command(command):
            print(f"Would send command: {command}")
        
        # Create parameter factory
        self.factory = ParameterFactory(self.validation_service, self.i18n, mock_send_command)
        
        # Create scrollable frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Test Parameters")
        self.scrollable_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Test parameters
        test_params = ['vibration', 'sensitivity', 'timer_ign_on', 'timer_ign_off', 'heartbeat_ign_on', 'heartbeat_ign_off']
        
        for i, param_name in enumerate(test_params):
            param = self.factory.create_parameter(param_name)
            if param:
                widget = param.create_widget(self.scrollable_frame)
                widget.pack(fill="x", padx=10, pady=5)

def test_ui():
    """Test the UI layout."""
    app = TestApp()
    app.mainloop()

if __name__ == "__main__":
    test_ui()