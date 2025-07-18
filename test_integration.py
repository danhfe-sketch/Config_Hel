"""
Integration tests for the LT32Pro Configurator application.

This test suite verifies complete workflows and interactions between different components
of the application, ensuring that all parts work together correctly.
"""

import unittest
import tkinter as tk
import customtkinter as ctk
import os
import sys
import time
import threading
import json
from unittest.mock import MagicMock, patch

# Add the project root to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import application modules
from services.i18n_service import I18nService
from services.validation_service import ValidationService
from services.config_service import ConfigService
from services.error_handling_service import ErrorHandlingService
from services.device_command_mapper import DeviceCommandMapper
from services.serial_service import SerialService
from services.theme_service import ThemeService

class IntegrationTest(unittest.TestCase):
    """Test complete workflows and component interactions."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        # Create a mock root window
        cls.root = ctk.CTk()
        cls.root.withdraw()  # Hide the window
        
        # Initialize services
        cls.i18n = I18nService()
        cls.device_command_mapper = DeviceCommandMapper()
        
        # Create a mock app with required attributes
        cls.app = MagicMock()
        cls.app.root = cls.root
        
        # Create log frame mock
        cls.app.log_frame = MagicMock()
        cls.app.log_frame.log_message = MagicMock()
        
        # Create connection frame mock
        cls.app.connection_frame = MagicMock()
        cls.app.connection_frame.update_status = MagicMock()
        cls.app.connection_frame.update_connection_indicator = MagicMock()
        
        # Create parameters frame mock
        cls.app.params_frame = MagicMock()
        cls.app.params_frame.get_all_parameter_values = MagicMock(return_value={
            'apn_server': 'internet',
            'apn_user': 'user',
            'apn_password': 'password',
            'timer_ign_on': '30',
            'timer_ign_off': '300',
            'vibration': '3',
            'sensitivity': '5',
            'curve_sensor': 'Auto',
            'ignition_type': 'Digital',
            'lock_type': 'PIN'
        })
        
        # Initialize services on the app
        cls.app.i18n = cls.i18n
        cls.app.device_command_mapper = cls.device_command_mapper
        cls.app.error_handler = ErrorHandlingService(cls.app)
        cls.app.serial_service = SerialService(cls.app)
        cls.app.theme_service = ThemeService(cls.app)
        cls.app.config_service = ConfigService(cls.app)
        cls.app.validation_service = ValidationService(cls.i18n)

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        cls.root.destroy()

    def setUp(self):
        """Set up before each test."""
        # Reset mocks
        self.app.log_frame.log_message.reset_mock()
        self.app.connection_frame.update_status.reset_mock()
        self.app.connection_frame.update_connection_indicator.reset_mock()
        
        # Reset serial service state
        self.app.serial_service.is_connected = False
        self.app.serial_service.serial_port = None
        
        # Create a test config file path
        self.test_config_path = "test_config.lt32config"
        
        # Create a test theme config path
        self.test_theme_path = "test_theme.json"

    def tearDown(self):
        """Clean up after each test."""
        # Remove test files if they exist
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)
        
        if os.path.exists(self.test_theme_path):
            os.remove(self.test_theme_path)

    @patch('serial.Serial')
    def test_connection_workflow(self, mock_serial):
        """Test the complete connection workflow."""
        # Setup mock serial port
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.is_open = True
        mock_serial_instance.in_waiting = 0
        
        # Test connection
        self.app.serial_service.connect("COM1")
        
        # Verify connection was established
        self.assertTrue(self.app.serial_service.is_connected)
        self.app.connection_frame.update_status.assert_called_with(True)
        self.app.connection_frame.update_connection_indicator.assert_called_with(True)
        
        # Simulate device response with IMEI
        mock_serial_instance.in_waiting = 20
        mock_serial_instance.readline.return_value = b"IMEI: 123456789012345\r\n"
        
        # Call the read method directly since we're not running the thread
        self.app.serial_service.process_device_response("IMEI: 123456789012345")
        
        # Verify IMEI was extracted
        self.assertEqual(self.app.serial_service.device_info['imei'], "123456789012345")
        
        # Test disconnection
        self.app.serial_service.disconnect()
        
        # Verify disconnection
        self.assertFalse(self.app.serial_service.is_connected)
        self.app.connection_frame.update_status.assert_called_with(False)
        self.app.connection_frame.update_connection_indicator.assert_called_with(False)

    @patch('services.config_service.open', create=True)
    @patch('services.config_service.json.dump')
    @patch('services.config_service.filedialog.asksaveasfilename')
    def test_save_profile_workflow(self, mock_save_dialog, mock_json_dump, mock_open):
        """Test the complete save profile workflow."""
        # Setup mocks
        mock_save_dialog.return_value = self.test_config_path
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Call save profile
        self.app.config_service.save_profile()
        
        # Verify file dialog was called
        mock_save_dialog.assert_called_once()
        
        # Verify json.dump was called
        mock_json_dump.assert_called_once()
        
        # Verify the first argument to json.dump is a dictionary with expected structure
        config_data = mock_json_dump.call_args[0][0]
        self.assertIsInstance(config_data, dict)
        self.assertIn("version", config_data)
        self.assertIn("created_at", config_data)
        self.assertIn("apn_config", config_data)
        
        # Verify log message was shown
        self.app.log_frame.log_message.assert_called()

    @patch('services.config_service.open', create=True)
    @patch('services.config_service.json.load')
    @patch('services.config_service.filedialog.askopenfilename')
    def test_load_profile_workflow(self, mock_open_dialog, mock_json_load, mock_open):
        """Test the complete load profile workflow."""
        # Setup mocks
        mock_open_dialog.return_value = self.test_config_path
        mock_json_load.return_value = {
            "version": "1.0",
            "created_at": "2025-07-17T10:00:00",
            "apn_config": {
                "server": "test.apn",
                "user": "testuser",
                "password": "testpass"
            },
            "communication": {
                "transmission_mode": "TCP"
            },
            "device_parameters": {
                "vibration": "5",
                "sensitivity": "8"
            }
        }
        
        # Call load profile
        self.app.config_service.load_profile()
        
        # Verify file dialog was called
        mock_open_dialog.assert_called_once()
        
        # Verify json.load was called
        mock_json_load.assert_called_once()
        
        # Verify log message was shown
        self.app.log_frame.log_message.assert_called()

    @patch('serial.Serial')
    def test_send_command_workflow(self, mock_serial):
        """Test the complete send command workflow."""
        # Setup mock serial port
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.is_open = True
        
        # Connect to device
        self.app.serial_service.connect("COM1")
        
        # Send a command
        command = "ATSMS:APN,internet,,#"
        self.app.serial_service.send_command(command)
        
        # Verify command was sent
        mock_serial_instance.write.assert_called_once()
        self.app.log_frame.log_message.assert_called()
        
        # Simulate device response
        self.app.serial_service.process_device_response("APN:internet,,")
        
        # Disconnect
        self.app.serial_service.disconnect()

    @patch('serial.Serial')
    def test_bulk_operations_workflow(self, mock_serial):
        """Test the complete bulk operations workflow."""
        # Setup mock serial port
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.is_open = True
        
        # Connect to device
        self.app.serial_service.connect("COM1")
        
        # Mock queue processing to avoid threading issues
        self.app.serial_service._process_command_queue = MagicMock()
        
        # Send all parameters
        self.app.serial_service.send_all_parameters()
        
        # Verify queue_commands was called
        self.assertTrue(self.app.serial_service.queue_processing)
        
        # Check device configuration
        self.app.serial_service.check_device_configuration()
        
        # Verify queue_commands was called again
        self.assertTrue(self.app.serial_service.queue_processing)
        
        # Disconnect
        self.app.serial_service.disconnect()

    @patch('services.theme_service.open', create=True)
    @patch('services.theme_service.json.dump')
    @patch('services.theme_service.json.load')
    def test_theme_persistence_workflow(self, mock_json_load, mock_json_dump, mock_open):
        """Test the theme persistence workflow."""
        # Setup mocks
        mock_json_load.return_value = {"theme": "Dark"}
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Set theme service config path
        self.app.theme_service.config_path = self.test_theme_path
        
        # Set theme
        self.app.theme_service.set_theme("Dark")
        
        # Verify theme was set
        self.assertEqual(self.app.theme_service.current_theme, "Dark")
        
        # Verify theme was saved
        mock_json_dump.assert_called()
        
        # Load theme
        theme = self.app.theme_service.get_current_theme()
        
        # Verify theme was loaded
        self.assertEqual(theme, "Dark")

    def test_validation_integration(self):
        """Test validation integration with other components."""
        # Test numeric parameter validation
        result = self.app.validation_service.validate_parameter("vibration", "300")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, "MAX_VALUE")
        
        # Test text parameter validation
        result = self.app.validation_service.validate_parameter("apn_server", "")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, "REQUIRED_FIELD")
        
        # Test dropdown parameter validation
        result = self.app.validation_service.validate_parameter("curve_sensor", "Invalid")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, "INVALID_SELECTION")
        
        # Test radio parameter validation
        result = self.app.validation_service.validate_parameter("ignition_type", "Invalid")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, "INVALID_SELECTION")

    def test_language_switching_integration(self):
        """Test language switching integration."""
        # Set language to English
        self.app.i18n.set_language("en_US")
        
        # Verify language was set by checking a translation
        connect_text = self.app.i18n.get("connect")
        self.assertEqual(connect_text, "Connect")
        
        # Verify language was saved in app config
        self.assertEqual(self.app.i18n.app_config.get_language(), "en_US")
        
        # Switch to Portuguese
        self.app.i18n.set_language("pt_BR")
        
        # Verify language was changed by checking a translation
        connect_text = self.app.i18n.get("connect")
        self.assertEqual(connect_text, "Conectar")
        
        # Verify language was saved in app config
        self.assertEqual(self.app.i18n.app_config.get_language(), "pt_BR")
        
        # Switch to Spanish
        self.app.i18n.set_language("es_ES")
        
        # Verify language was changed by checking a translation
        connect_text = self.app.i18n.get("connect")
        self.assertEqual(connect_text, "Conectar")

    def test_error_handling_integration(self):
        """Test error handling integration."""
        # Reset mocks
        self.app.log_frame.log_message.reset_mock()
        
        # Manually trigger error handling
        self.app.error_handler.handle_error(
            self.app.error_handler.CONN_ERROR_PORT_NOT_FOUND,
            self.app.error_handler.SEVERITY_ERROR,
            {'port': 'COM1'}
        )
        
        # Verify error was logged
        self.app.log_frame.log_message.assert_called()
        
        # We don't test connection status update here as it depends on implementation details

    def test_command_mapping_integration(self):
        """Test command mapping integration."""
        # Get a command for a parameter
        command = self.app.device_command_mapper.get_command("vibration", "3")
        
        # Verify command format
        self.assertEqual(command, "ATSMS:SZCS#VIBL=3#")
        
        # Get a command with context
        command = self.app.device_command_mapper.get_command(
            "timer_ign_on", 
            "30", 
            {"timer_ign_off": "300"}
        )
        
        # Verify command format
        self.assertEqual(command, "ATSMS:TIMER,30,300#")
        
        # Get bulk commands
        parameters = {
            'apn_server': 'internet',
            'apn_user': 'user',
            'apn_password': 'password',
            'timer_ign_on': '30',
            'timer_ign_off': '300'
        }
        
        commands = self.app.device_command_mapper.get_bulk_commands(parameters)
        
        # Verify commands were generated
        self.assertGreater(len(commands), 0)
        self.assertIn("ATSMS:APN,internet,,#", commands)

if __name__ == '__main__':
    unittest.main()