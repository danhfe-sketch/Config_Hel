#!/usr/bin/env python3
"""
Integration test for the "Checar configuração" button functionality.
This test verifies the complete workflow including progress indication,
error handling, and comprehensive logging.
"""

import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
import time
import threading
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.serial_service import SerialService
from services.configuration_reader_service import (
    ConfigurationReaderService, 
    ConfigurationReadResult, 
    ParameterReadResult
)
from services.i18n_service import I18nService
from ui.actions_frame import ActionsFrame


class TestCheckConfigurationIntegration(unittest.TestCase):
    """Integration test for the complete check configuration workflow."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock app with all required components
        self.mock_app = MagicMock()
        self.mock_app.log_frame = MagicMock()
        self.mock_app.log_frame.log_message = MagicMock()
        self.mock_app.after = MagicMock(side_effect=lambda delay, func, *args: func(*args))
        
        # Mock operation confirmation service for progress dialogs
        self.mock_app.operation_confirmation_service = MagicMock()
        self.mock_app.operation_confirmation_service.create_progress_dialog = MagicMock(return_value="dialog_id_123")
        self.mock_app.operation_confirmation_service.update_progress = MagicMock()
        self.mock_app.operation_confirmation_service.complete_progress = MagicMock()
        self.mock_app.operation_confirmation_service.set_cancel_callback = MagicMock()
        self.mock_app.operation_confirmation_service.show_success_notification = MagicMock()
        
        # Mock parameters frame for UI updates
        self.mock_app.params_frame = MagicMock()
        self.mock_app.params_frame.parameter_widgets = {}
        self.mock_app.params_frame.apn_server_entry = MagicMock()
        self.mock_app.params_frame.apn_server_entry.get = MagicMock(return_value="old_apn")
        self.mock_app.params_frame.apn_server_entry.delete = MagicMock()
        self.mock_app.params_frame.apn_server_entry.insert = MagicMock()
        self.mock_app.params_frame.apn_server_entry.cget = MagicMock(return_value="#000000")
        self.mock_app.params_frame.apn_server_entry.configure = MagicMock()
        
        # Create I18n service
        self.i18n = I18nService()
        
        # Create serial service with mock app
        self.serial_service = SerialService(self.mock_app)
        self.serial_service.is_connected = True
        
        # Create actions frame
        self.actions_frame = ActionsFrame(None, self.i18n, self.serial_service)

    def test_complete_configuration_reading_workflow(self):
        """Test the complete configuration reading workflow with progress indication."""
        # Create mock configuration reader
        mock_config_reader = MagicMock()
        
        # Create successful parameter read results
        successful_results = [
            ParameterReadResult(
                parameter_name="apn_config",
                success=True,
                value="internet.provider.com,user,pass",
                error_message=None,
                raw_response="APN:internet.provider.com,user,pass#"
            ),
            ParameterReadResult(
                parameter_name="server_config", 
                success=True,
                value="192.168.1.100,8080",
                error_message=None,
                raw_response="SERVER:0,192.168.1.100,8080,0"
            )
        ]
        
        # Create successful configuration read result
        successful_result = ConfigurationReadResult(
            success=True,
            parameters_read=successful_results,
            total_parameters=2,
            failed_parameters=[],
            read_duration=3.2,
            timestamp=datetime.now()
        )
        
        # Mock the read_all_configurations method to call completion callback
        def mock_read_all_configurations(*args, **kwargs):
            completion_callback = kwargs.get('completion_callback')
            if completion_callback:
                # Simulate async completion
                completion_callback(successful_result, None)
        
        mock_config_reader.read_all_configurations = MagicMock(side_effect=mock_read_all_configurations)
        self.serial_service.configuration_reader = mock_config_reader
        
        # Call the check configuration method
        self.actions_frame.check_configuration()
        
        # Verify configuration reader was called with correct parameters
        mock_config_reader.read_all_configurations.assert_called_once()
        args, kwargs = mock_config_reader.read_all_configurations.call_args
        
        # Verify completion callback was provided
        self.assertIn('completion_callback', kwargs)
        self.assertIn('show_progress_dialog', kwargs)
        self.assertTrue(kwargs['show_progress_dialog'])
        
        # Verify success message was logged
        logged_messages = [call[0][0] for call in self.mock_app.log_frame.log_message.call_args_list]
        success_logged = any("Configuration reading completed successfully" in msg for msg in logged_messages)
        self.assertTrue(success_logged, "Success message should be logged")
        
        # Verify success notification was shown
        self.mock_app.operation_confirmation_service.show_success_notification.assert_called_once()

    def test_configuration_reading_with_partial_failures(self):
        """Test configuration reading with some failed parameters."""
        # Create mock configuration reader
        mock_config_reader = MagicMock()
        
        # Create mixed results (some success, some failure)
        mixed_results = [
            ParameterReadResult(
                parameter_name="apn_config",
                success=True,
                value="internet.provider.com,user,pass",
                error_message=None,
                raw_response="APN:internet.provider.com,user,pass#"
            ),
            ParameterReadResult(
                parameter_name="server_config",
                success=False,
                value=None,
                error_message="Command timeout",
                raw_response=""
            )
        ]
        
        # Create partial failure result
        partial_result = ConfigurationReadResult(
            success=True,  # Still success if at least some parameters were read
            parameters_read=mixed_results,
            total_parameters=2,
            failed_parameters=["server_config"],
            read_duration=5.0,
            timestamp=datetime.now()
        )
        
        error_message = "Failed to read 1 parameters: server_config"
        
        # Mock the read_all_configurations method
        def mock_read_all_configurations(*args, **kwargs):
            completion_callback = kwargs.get('completion_callback')
            if completion_callback:
                completion_callback(partial_result, error_message)
        
        mock_config_reader.read_all_configurations = MagicMock(side_effect=mock_read_all_configurations)
        self.serial_service.configuration_reader = mock_config_reader
        
        # Call the check configuration method
        self.actions_frame.check_configuration()
        
        # Verify both success and error messages were logged
        logged_messages = [call[0][0] for call in self.mock_app.log_frame.log_message.call_args_list]
        success_logged = any("Configuration reading completed successfully" in msg for msg in logged_messages)
        self.assertTrue(success_logged, "Success message should be logged for partial success")

    def test_configuration_reading_complete_failure(self):
        """Test configuration reading with complete failure."""
        # Create mock configuration reader
        mock_config_reader = MagicMock()
        
        # Create complete failure result
        failure_result = ConfigurationReadResult(
            success=False,
            parameters_read=[],
            total_parameters=0,
            failed_parameters=["apn_config", "server_config"],
            read_duration=1.0,
            timestamp=datetime.now()
        )
        
        error_message = "Device not responding to configuration queries"
        
        # Mock the read_all_configurations method
        def mock_read_all_configurations(*args, **kwargs):
            completion_callback = kwargs.get('completion_callback')
            if completion_callback:
                completion_callback(failure_result, error_message)
        
        mock_config_reader.read_all_configurations = MagicMock(side_effect=mock_read_all_configurations)
        self.serial_service.configuration_reader = mock_config_reader
        
        # Call the check configuration method
        self.actions_frame.check_configuration()
        
        # Verify error message was logged
        logged_messages = [call[0][0] for call in self.mock_app.log_frame.log_message.call_args_list]
        error_logged = any("ERROR:" in msg and error_message in msg for msg in logged_messages)
        self.assertTrue(error_logged, "Error message should be logged for complete failure")
        
        # Verify success notification was NOT called
        self.mock_app.operation_confirmation_service.show_success_notification.assert_not_called()

    def test_progress_dialog_creation_and_management(self):
        """Test that progress dialog is properly created and managed."""
        # Create mock configuration reader
        mock_config_reader = MagicMock()
        
        # Create a result that will trigger progress dialog
        result = ConfigurationReadResult(
            success=True,
            parameters_read=[],
            total_parameters=5,
            failed_parameters=[],
            read_duration=2.0,
            timestamp=datetime.now()
        )
        
        # Mock the read_all_configurations method
        def mock_read_all_configurations(*args, **kwargs):
            completion_callback = kwargs.get('completion_callback')
            if completion_callback:
                completion_callback(result, None)
        
        mock_config_reader.read_all_configurations = MagicMock(side_effect=mock_read_all_configurations)
        self.serial_service.configuration_reader = mock_config_reader
        
        # Call the check configuration method
        self.actions_frame.check_configuration()
        
        # Verify progress dialog creation was requested
        mock_config_reader.read_all_configurations.assert_called_once()
        args, kwargs = mock_config_reader.read_all_configurations.call_args
        self.assertTrue(kwargs.get('show_progress_dialog', False))

    def test_comprehensive_logging_during_configuration_reading(self):
        """Test that comprehensive logging occurs during configuration reading."""
        # Create mock configuration reader
        mock_config_reader = MagicMock()
        
        # Create detailed results for logging verification
        detailed_results = [
            ParameterReadResult(
                parameter_name="device_info",
                success=True,
                value="IMEI:123456789012345",
                error_message=None,
                raw_response="IMEI:123456789012345"
            ),
            ParameterReadResult(
                parameter_name="apn_config",
                success=True,
                value="internet.provider.com,user,pass",
                error_message=None,
                raw_response="APN:internet.provider.com,user,pass#"
            )
        ]
        
        result = ConfigurationReadResult(
            success=True,
            parameters_read=detailed_results,
            total_parameters=2,
            failed_parameters=[],
            read_duration=4.5,
            timestamp=datetime.now()
        )
        
        # Mock the read_all_configurations method
        def mock_read_all_configurations(*args, **kwargs):
            completion_callback = kwargs.get('completion_callback')
            if completion_callback:
                completion_callback(result, None)
        
        mock_config_reader.read_all_configurations = MagicMock(side_effect=mock_read_all_configurations)
        self.serial_service.configuration_reader = mock_config_reader
        
        # Call the check configuration method
        self.actions_frame.check_configuration()
        
        # Verify comprehensive logging occurred
        self.mock_app.log_frame.log_message.assert_called()
        logged_messages = [call[0][0] for call in self.mock_app.log_frame.log_message.call_args_list]
        
        # Check for key log messages
        success_logged = any("Configuration reading completed successfully" in msg for msg in logged_messages)
        duration_logged = any("4.50 seconds" in msg for msg in logged_messages)
        parameter_count_logged = any("2 parameters" in msg for msg in logged_messages)
        
        self.assertTrue(success_logged, "Success message should be logged")
        self.assertTrue(duration_logged, "Duration should be logged")
        self.assertTrue(parameter_count_logged, "Parameter count should be logged")

    def test_error_handling_for_configuration_reader_exceptions(self):
        """Test error handling when configuration reader throws exceptions."""
        # Create mock configuration reader that throws exception
        mock_config_reader = MagicMock()
        mock_config_reader.read_all_configurations.side_effect = Exception("Mock configuration reader error")
        self.serial_service.configuration_reader = mock_config_reader
        
        # Call the check configuration method
        self.actions_frame.check_configuration()
        
        # Verify exception was caught and logged
        logged_messages = [call[0][0] for call in self.mock_app.log_frame.log_message.call_args_list]
        error_logged = any("Failed to start configuration reading" in msg for msg in logged_messages)
        self.assertTrue(error_logged, "Exception should be caught and logged")


if __name__ == '__main__':
    unittest.main()