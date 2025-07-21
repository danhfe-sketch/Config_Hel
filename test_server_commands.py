import unittest
import tkinter as tk
import customtkinter as ctk
from services.i18n_service import I18nService
from services.validation_service import ValidationService
from ui.parameter_factory import ParameterFactory, TextParameter, NumericParameter

class TestServerCommands(unittest.TestCase):
    """Test the server parameter commands."""
    
    def setUp(self):
        """Set up the test environment."""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the window
        self.i18n = I18nService()
        self.validation_service = ValidationService(self.i18n)
        
        # Create a mock send_command_callback that stores the last command
        self.last_command = None
        def mock_send_command(command):
            self.last_command = command
            print(f"Mock send command: {command}")
        
        self.parameter_factory = ParameterFactory(
            self.validation_service,
            self.i18n,
            mock_send_command
        )
    
    def tearDown(self):
        """Clean up after the test."""
        self.root.destroy()
    
    def test_server_ip_command_template(self):
        """Test that the server_ip command template is correctly defined."""
        # Get the server_ip parameter definition
        server_ip_def = self.parameter_factory.parameter_definitions.get('server_ip')
        
        # Check that the command template is correctly defined
        self.assertIsNotNone(server_ip_def, "server_ip parameter definition not found")
        self.assertEqual(server_ip_def.at_command_template, 'ATSMS:SERVER,0,{value},8080,0#',
                         "server_ip command template incorrect")
        
        # Test that the template can be formatted without errors
        try:
            command = server_ip_def.at_command_template.format(value='192.168.1.1')
            self.assertEqual(command, 'ATSMS:SERVER,0,192.168.1.1,8080,0#',
                            "Formatted command incorrect")
            print("Server IP command template test passed!")
            print(f"Command template: {server_ip_def.at_command_template}")
            print(f"Formatted command: {command}")
        except KeyError as e:
            self.fail(f"KeyError when formatting command: {e}")
    
    def test_server_port_command_template(self):
        """Test that the server_port command template is correctly defined."""
        # Get the server_port parameter definition
        server_port_def = self.parameter_factory.parameter_definitions.get('server_port')
        
        # Check that the command template is correctly defined
        self.assertIsNotNone(server_port_def, "server_port parameter definition not found")
        self.assertEqual(server_port_def.at_command_template, 'ATSMS:SERVER,0,0.0.0.0,{value},0#',
                         "server_port command template incorrect")
        
        # Test that the template can be formatted without errors
        try:
            command = server_port_def.at_command_template.format(value='8080')
            self.assertEqual(command, 'ATSMS:SERVER,0,0.0.0.0,8080,0#',
                            "Formatted command incorrect")
            print("Server port command template test passed!")
            print(f"Command template: {server_port_def.at_command_template}")
            print(f"Formatted command: {command}")
        except KeyError as e:
            self.fail(f"KeyError when formatting command: {e}")

if __name__ == "__main__":
    unittest.main()