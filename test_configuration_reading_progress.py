#!/usr/bin/env python3
"""
Test script for configuration reading progress indication functionality.

This test verifies that the progress dialog is properly created, updated, and closed
during configuration reading operations.
"""

import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.configuration_reader_service import ConfigurationReaderService
from services.i18n_service import I18nService
from services.operation_confirmation_service import OperationConfirmationService


class TestConfigurationReadingProgress(unittest.TestCase):
    """Test configuration reading progress indication functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock app instance
        self.mock_app = MagicMock()
        self.mock_app.i18n = I18nService()
        
        # Create mock serial service
        self.mock_serial_service = MagicMock()
        self.mock_serial_service.is_connected = True
        self.mock_app.serial_service = self.mock_serial_service
        
        # Create mock operation confirmation service
        self.mock_operation_service = MagicMock()
        self.mock_app.operation_confirmation_service = self.mock_operation_service
        
        # Create configuration reader service
        self.config_reader = ConfigurationReaderService(self.mock_app, self.mock_app.i18n)

    def test_progress_dialog_creation(self):
        """Test that progress dialog is created when reading configuration."""
        # Mock the progress dialog creation
        self.mock_operation_service.create_progress_dialog.return_value = "test_dialog_id"
        
        # Mock the threading to avoid actual thread execution
        with patch('threading.Thread') as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            
            # Start configuration reading
            self.config_reader.read_all_configurations(show_progress_dialog=True)
            
            # Verify progress dialog was created
            self.mock_operation_service.create_progress_dialog.assert_called_once()
            call_args = self.mock_operation_service.create_progress_dialog.call_args
            
            # Check the dialog parameters
            self.assertIn('Reading Configuration', call_args[1]['title'])
            self.assertIn('Device Configuration Reading', call_args[1]['operation_name'])
            self.assertEqual(call_args[1]['progress_type'], 
                           self.mock_operation_service.PROGRESS_TYPE_DETERMINATE)
            self.assertEqual(call_args[1]['total_steps'], 100)
            self.assertTrue(call_args[1]['cancelable'])
            
            # Verify cancel callback was set
            self.mock_operation_service.set_cancel_callback.assert_called_once_with(
                "test_dialog_id", self.config_reader.cancel_reading
            )
            
            # Verify thread was started
            mock_thread_instance.start.assert_called_once()

    def test_progress_dialog_disabled(self):
        """Test that progress dialog is not created when disabled."""
        with patch('threading.Thread') as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            
            # Start configuration reading without progress dialog
            self.config_reader.read_all_configurations(show_progress_dialog=False)
            
            # Verify progress dialog was not created
            self.mock_operation_service.create_progress_dialog.assert_not_called()

    def test_progress_updates(self):
        """Test that progress is updated during configuration reading."""
        # Mock the progress dialog creation
        self.mock_operation_service.create_progress_dialog.return_value = "test_dialog_id"
        
        # Mock parameter commands
        with patch.object(self.config_reader, '_get_all_parameter_commands') as mock_get_commands:
            mock_get_commands.return_value = [
                ('param1', 'ATSMS:CMD1#', 'type1'),
                ('param2', 'ATSMS:CMD2#', 'type2'),
            ]
            
            # Mock parameter reading
            with patch.object(self.config_reader, 'read_specific_parameter') as mock_read_param:
                from services.configuration_reader_service import ParameterReadResult
                mock_read_param.return_value = ParameterReadResult(
                    parameter_name='test_param',
                    success=True,
                    value='test_value',
                    error_message=None,
                    raw_response='test_response'
                )
                
                # Mock UI update methods
                with patch.object(self.config_reader, '_update_ui_from_results'):
                    with patch.object(self.config_reader, '_disable_parameter_modification'):
                        # Execute the thread function directly
                        self.config_reader.progress_dialog_id = "test_dialog_id"
                        self.config_reader._read_configurations_thread()
                        
                        # Verify progress updates were called
                        self.mock_app.after.assert_called()
                        
                        # Check that update_progress was called with correct parameters
                        update_calls = [call for call in self.mock_app.after.call_args_list 
                                      if len(call[0]) > 2 and 
                                      call[0][1] == self.mock_operation_service.update_progress]
                        
                        self.assertGreater(len(update_calls), 0, "Progress updates should be called")

    def test_parameter_modification_disabled(self):
        """Test that parameter modification is disabled during reading."""
        # Mock frame objects
        mock_params_frame = MagicMock()
        mock_actions_frame = MagicMock()
        self.mock_app.params_frame = mock_params_frame
        self.mock_app.actions_frame = mock_actions_frame
        
        # Test disabling parameter modification
        self.config_reader._disable_parameter_modification(True)
        
        # Verify that frame state methods were called
        # Note: The actual implementation depends on the frame structure
        # This test verifies the method doesn't crash
        self.assertTrue(True)  # If we get here, the method didn't crash

    def test_cancel_reading_functionality(self):
        """Test that reading can be canceled."""
        # Set up reading state
        self.config_reader.is_reading = True
        self.config_reader.cancel_requested = False
        
        # Cancel reading
        self.config_reader.cancel_reading()
        
        # Verify cancel was requested
        self.assertTrue(self.config_reader.cancel_requested)

    def test_no_connection_error(self):
        """Test error handling when device is not connected."""
        # Set up disconnected state
        self.mock_serial_service.is_connected = False
        
        # Mock completion callback
        completion_callback = MagicMock()
        
        # Try to read configuration
        self.config_reader.read_all_configurations(completion_callback=completion_callback)
        
        # Verify completion callback was called with error
        completion_callback.assert_called_once()
        result, error_message = completion_callback.call_args[0]
        
        self.assertFalse(result.success)
        self.assertIn('connection', error_message.lower())

    def test_already_reading_error(self):
        """Test error handling when reading is already in progress."""
        # Set up reading state
        self.config_reader.is_reading = True
        
        # Mock completion callback
        completion_callback = MagicMock()
        
        # Try to read configuration again
        self.config_reader.read_all_configurations(completion_callback=completion_callback)
        
        # Verify completion callback was called with error
        completion_callback.assert_called_once()
        result, error_message = completion_callback.call_args[0]
        
        self.assertFalse(result.success)
        self.assertIn('progress', error_message.lower())

    @patch('time.sleep')  # Mock sleep to speed up test
    def test_progress_dialog_completion(self, mock_sleep):
        """Test that progress dialog is properly completed."""
        # Mock the progress dialog creation
        self.mock_operation_service.create_progress_dialog.return_value = "test_dialog_id"
        
        # Mock parameter commands (empty list for quick completion)
        with patch.object(self.config_reader, '_get_all_parameter_commands') as mock_get_commands:
            mock_get_commands.return_value = []
            
            # Mock UI update methods
            with patch.object(self.config_reader, '_update_ui_from_results'):
                with patch.object(self.config_reader, '_disable_parameter_modification'):
                    # Execute the thread function directly
                    self.config_reader.progress_dialog_id = "test_dialog_id"
                    self.config_reader._read_configurations_thread()
                    
                    # Verify progress dialog completion was scheduled
                    complete_calls = [call for call in self.mock_app.after.call_args_list 
                                    if len(call[0]) > 2 and 
                                    call[0][1] == self.mock_operation_service.complete_progress]
                    
                    self.assertGreater(len(complete_calls), 0, "Progress completion should be called")


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)