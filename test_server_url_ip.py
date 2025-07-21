import unittest
import tkinter as tk
import customtkinter as ctk
from services.i18n_service import I18nService
from services.validation_service import ValidationService
from ui.parameter_factory import ParameterFactory, TextParameter

class TestServerUrlIp(unittest.TestCase):
    """Test the server URL/IP parameter."""
    
    def setUp(self):
        """Set up the test environment."""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the window
        self.i18n = I18nService()
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
    
    def test_server_ip_parameter(self):
        """Test that the server_ip parameter is correctly created as a TextParameter."""
        # Create the server_ip parameter
        server_ip_param = self.parameter_factory.create_parameter('server_ip')
        
        # Check that it's a TextParameter
        self.assertIsInstance(server_ip_param, TextParameter, "server_ip parameter should be a TextParameter")
        
        # Check that it has the correct display label
        self.assertEqual(server_ip_param.definition.display_label, 'server_url_ip', 
                         "server_ip parameter should have display_label 'server_url_ip'")
        
        print("Server IP parameter test passed!")
        print(f"Parameter type: {type(server_ip_param).__name__}")
        print(f"Display label: {server_ip_param.definition.display_label}")

if __name__ == "__main__":
    unittest.main()