import unittest
import tkinter as tk
import customtkinter as ctk
from services.i18n_service import I18nService
from services.validation_service import ValidationService
from ui.parameter_factory import ParameterFactory, NumericParameter

class TestValidationDisplay(unittest.TestCase):
    """Test that validation errors are displayed correctly."""
    
    def setUp(self):
        """Set up the test environment."""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the window
        self.i18n = I18nService('pt_BR')  # Use Portuguese for testing
        self.validation_service = ValidationService(self.i18n)
        
        # Create a mock send_command_callback
        def mock_send_command(command):
            print(f"Mock send command: {command}")
        
        self.parameter_factory = ParameterFactory(
            self.validation_service,
            self.i18n,
            mock_send_command
        )
    
    def tearDown(self):
        """Clean up after the test."""
        self.root.destroy()
    
    def test_server_port_validation_display(self):
        """Test that server_port validation errors are displayed correctly."""
        # Create the server_port parameter
        server_port_param = self.parameter_factory.create_parameter('server_port')
        self.assertIsNotNone(server_port_param, "server_port parameter should be created")
        
        # Create the widget
        frame = ctk.CTkFrame(self.root)
        param_widget = server_port_param.create_widget(frame)
        
        # Set an invalid value
        server_port_param.set_value('99999')  # Above maximum (65535)
        
        # Simulate focus out event
        server_port_param._on_focus_out(None)
        
        # Check that the error message is displayed
        self.assertIsNotNone(server_port_param.error_label, "Error label should exist")
        error_text = server_port_param.error_label.cget("text")
        self.assertNotEqual(error_text, "", "Error message should not be empty")
        self.assertIn("65535", error_text, "Error message should mention the maximum value")
        
        print("Server port validation display test passed!")
        print(f"Error message: {error_text}")
        print(f"Error label text color: {server_port_param.error_label.cget('text_color')}")
    
    def test_key_release_validation(self):
        """Test that validation is triggered on key release."""
        # Create the server_port parameter
        server_port_param = self.parameter_factory.create_parameter('server_port')
        
        # Create the widget
        frame = ctk.CTkFrame(self.root)
        param_widget = server_port_param.create_widget(frame)
        
        # Set an invalid value
        server_port_param.set_value('99999')  # Above maximum (65535)
        
        # Simulate key release event
        server_port_param._on_key_release(None)
        
        # Check that the error message is displayed
        error_text = server_port_param.error_label.cget("text")
        self.assertNotEqual(error_text, "", "Error message should not be empty")
        
        print("Key release validation test passed!")
        print(f"Error message: {error_text}")

if __name__ == "__main__":
    unittest.main()