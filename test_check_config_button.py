#!/usr/bin/env python3
"""
Test script to verify the "Checar configuração" button functionality.
This test verifies that the button properly connects to ConfigurationReaderService
and provides comprehensive logging and error handling.
"""

import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.serial_service import SerialService
from services.configuration_reader_service import ConfigurationReaderService, ConfigurationReadResult
from services.i18n_service import I18nService
from ui.actions_frame import ActionsFrame
from datetime import datetime


class TestCheckConfigurationButton(unittest.TestCase):
    """Test the "Checar configuração" button functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock app
        self.mock_app = MagicMock()
        self.mock_app.log_frame = MagicMock()
        self.mock_app.log_frame.log_message = MagicMock()
        self.mock_app.after = MagicMock()
        
        # Create I18n service
        self.i18n = I18nService()
        
        # Create serial service with mock app
        self.serial_service = SerialService(self.mock_app)
        self.serial_service.is_connected = True  # Simulate connected state
        
        # Create actions frame
        self.actions_frame = ActionsFrame(None, self.i18n, self.serial_service)

    def test_check_configuration_button_exists(self):
        """Test that the check configuration button exists and has correct text."""
        self.assertIsNotNone(self.actions_frame.check_config_button)
        expected_text = self.i18n.get("check_config")
        self.assertEqual(self.actions_frame.check_config_button.cget("text"), expected_text)

    def test_check_configuration_requires_connection(self):
        """Test that check configuration requires device connection."""
        # Set disconnected state
        self.serial_service.is_connected = False
        
        # Mock showwarning to capture the warning
        with patch('ui.actions_frame.showwarning') as mock_warning:
            self.actions_frame.check_configuration()
            
            # Verify warning was shown
            mock_warning.assert_called_once()
            args, kwargs = mock_warning.call_args
            self.assertEqual(kwargs['title'], self.i18n.get("error"))
            self.assertEqual(kwargs['message'], self.i18n.get("not_connected_error"))

    def test_check_configuration_calls_serial_service(self):
        """Test that check configuration calls the serial service method."""
        # Mock the serial service method
        self.serial_service.check_device_configuration = MagicMock()
        
        # Call the button action
        self.actions_frame.check_configuration()
        
        # Verify the serial service method was called
        self.serial_service.check_device_configuration.assert_called_once()

    def test_serial_service_check_device_configuration(self):
        """Test the serial service check_device_configuration method."""
        # Mock configuration reader
        mock_config_reader = MagicMock()
        self.serial_service.configuration_reader = mock_config_reader
        
        # Call the method
        self.serial_service.check_device_configuration()
        
        # Verify configuration reader was called
        mock_config_reader.read_all_configurations.assert_called_once()
        
        # Verify the call includes completion callback and progress dialog
        args, kwargs = mock_config_reader.read_all_configurations.call_args
        self.assertIn('completion_callback', kwargs)
        self.assertIn('show_progress_dialog', kwargs)
        self.assertTrue(kwargs['show_progress_dialog'])

    def test_configuration_reader_initialization(self):
        """Test that configuration reader is properly initialized."""
        # Clear existing configuration reader
        self.serial_service.configuration_reader = None
        
        # Mock the initialize method
        self.serial_service.initialize_configuration_reader = MagicMock()
        
        # Call check_device_configuration
        self.serial_service.check_device_configuration()
        
        # Verify initialization was called
        self.serial_service.initialize_configuration_reader.assert_called_once()

    def test_completion_callback_success(self):
        """Test the completion callback for successful configuration reading."""
        # Create a successful result
        result = ConfigurationReadResult(
            success=True,
            parameters_read=[],
            total_parameters=10,
            failed_parameters=[],
            read_duration=2.5,
            timestamp=datetime.now()
        )
        
        # Mock operation confirmation service
        self.mock_app.operation_confirmation_service = MagicMock()
        
        # Mock configuration reader and capture the completion callback
        mock_config_reader = MagicMock()
        self.serial_service.configuration_reader = mock_config_reader
        
        # Call the method to set up the callback
        self.serial_service.check_device_configuration()
        
        # Get the completion callback
        args, kwargs = mock_config_reader.read_all_configurations.call_args
        completion_callback = kwargs['completion_callback']
        
        # Call the completion callback with success result
        completion_callback(result, None)
        
        # Verify success message was logged
        self.mock_app.log_frame.log_message.assert_called()
        logged_messages = [call[0][0] for call in self.mock_app.log_frame.log_message.call_args_list]
        success_logged = any("Configuration reading completed successfully" in msg for msg in logged_messages)
        self.assertTrue(success_logged, "Success message should be logged")

    def test_completion_callback_failure(self):
        """Test the completion callback for failed configuration reading."""
        # Create a failed result
        result = ConfigurationReadResult(
            success=False,
            parameters_read=[],
            total_parameters=0,
            failed_parameters=['apn_config', 'server_config'],
            read_duration=1.0,
            timestamp=datetime.now()
        )
        
        error_message = "Failed to read device configuration"
        
        # Mock configuration reader and capture the completion callback
        mock_config_reader = MagicMock()
        self.serial_service.configuration_reader = mock_config_reader
        
        # Call the method to set up the callback
        self.serial_service.check_device_configuration()
        
        # Get the completion callback
        args, kwargs = mock_config_reader.read_all_configurations.call_args
        completion_callback = kwargs['completion_callback']
        
        # Call the completion callback with failure result
        completion_callback(result, error_message)
        
        # Verify error message was logged
        self.mock_app.log_frame.log_message.assert_called()
        logged_messages = [call[0][0] for call in self.mock_app.log_frame.log_message.call_args_list]
        error_logged = any("ERROR:" in msg and error_message in msg for msg in logged_messages)
        self.assertTrue(error_logged, "Error message should be logged")

    def test_error_handling_when_config_reader_unavailable(self):
        """Test error handling when configuration reader is not available."""
        # Set configuration reader to None and mock initialization to fail
        self.serial_service.configuration_reader = None
        self.serial_service.initialize_configuration_reader = MagicMock()
        
        # Call the method
        self.serial_service.check_device_configuration()
        
        # Verify error message was logged
        self.mock_app.log_frame.log_message.assert_called()
        logged_messages = [call[0][0] for call in self.mock_app.log_frame.log_message.call_args_list]
        error_logged = any("Configuration reader service not available" in msg for msg in logged_messages)
        self.assertTrue(error_logged, "Error message should be logged when config reader unavailable")

    def test_exception_handling_in_check_configuration(self):
        """Test exception handling in check_device_configuration method."""
        # Mock configuration reader to raise an exception
        mock_config_reader = MagicMock()
        mock_config_reader.read_all_configurations.side_effect = Exception("Test exception")
        self.serial_service.configuration_reader = mock_config_reader
        
        # Call the method
        self.serial_service.check_device_configuration()
        
        # Verify exception was logged
        self.mock_app.log_frame.log_message.assert_called()
        logged_messages = [call[0][0] for call in self.mock_app.log_frame.log_message.call_args_list]
        error_logged = any("Failed to start configuration reading" in msg for msg in logged_messages)
        self.assertTrue(error_logged, "Exception should be logged")


if __name__ == '__main__':
    unittest.main()