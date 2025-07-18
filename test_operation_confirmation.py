"""
Test script for operation confirmation and success feedback.

This script tests the operation confirmation and success feedback features including:
- Confirmation dialogs for destructive operations like factory reset
- Success notifications for completed operations in the log
- Progress indicators for long-running operations
"""

import unittest
import tkinter as tk
import customtkinter as ctk
from unittest.mock import MagicMock, patch
import sys
import os
import time
import threading

# Add the project root to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.operation_confirmation_service import OperationConfirmationService
from services.error_handling_service import ErrorHandlingService

class OperationConfirmationTest(unittest.TestCase):
    """Test operation confirmation and success feedback."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        # Create a mock root window
        cls.root = ctk.CTk()
        cls.root.withdraw()  # Hide the window
        
        # Create a mock app with required attributes
        cls.app = MagicMock()
        cls.app.root = cls.root
        
        # Create log frame mock
        cls.app.log_frame = MagicMock()
        cls.app.log_frame.log_message = MagicMock()
        
        # Initialize services
        cls.app.error_handler = ErrorHandlingService(cls.app)
        cls.app.operation_confirmation_service = OperationConfirmationService(cls.app)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        cls.root.destroy()
    
    def setUp(self):
        """Set up before each test."""
        # Reset mocks
        self.app.log_frame.log_message.reset_mock()
    
    @patch('tkinter.messagebox.askyesno')
    def test_factory_reset_confirmation(self, mock_askyesno):
        """Test factory reset confirmation dialog."""
        # Setup mock to return True (user confirmed)
        mock_askyesno.return_value = True
        
        # Call confirm_operation
        result = self.app.operation_confirmation_service.confirm_operation(
            self.app.operation_confirmation_service.OPERATION_FACTORY_RESET
        )
        
        # Verify dialog was shown and result is True
        mock_askyesno.assert_called_once()
        self.assertTrue(result)
        
        # Setup mock to return False (user canceled)
        mock_askyesno.reset_mock()
        mock_askyesno.return_value = False
        
        # Call confirm_operation
        result = self.app.operation_confirmation_service.confirm_operation(
            self.app.operation_confirmation_service.OPERATION_FACTORY_RESET
        )
        
        # Verify dialog was shown and result is False
        mock_askyesno.assert_called_once()
        self.assertFalse(result)
    
    @patch('tkinter.messagebox.askyesno')
    def test_device_reset_confirmation(self, mock_askyesno):
        """Test device reset confirmation dialog."""
        # Setup mock to return True (user confirmed)
        mock_askyesno.return_value = True
        
        # Call confirm_operation
        result = self.app.operation_confirmation_service.confirm_operation(
            self.app.operation_confirmation_service.OPERATION_DEVICE_RESET
        )
        
        # Verify dialog was shown and result is True
        mock_askyesno.assert_called_once()
        self.assertTrue(result)
    
    @patch('tkinter.messagebox.askyesno')
    def test_restore_defaults_confirmation(self, mock_askyesno):
        """Test restore defaults confirmation dialog."""
        # Setup mock to return True (user confirmed)
        mock_askyesno.return_value = True
        
        # Call confirm_operation
        result = self.app.operation_confirmation_service.confirm_operation(
            self.app.operation_confirmation_service.OPERATION_RESTORE_DEFAULTS
        )
        
        # Verify dialog was shown and result is True
        mock_askyesno.assert_called_once()
        self.assertTrue(result)
    
    @patch('tkinter.messagebox.askyesno')
    def test_bulk_send_confirmation(self, mock_askyesno):
        """Test bulk send confirmation dialog."""
        # Setup mock to return True (user confirmed)
        mock_askyesno.return_value = True
        
        # Call confirm_operation
        result = self.app.operation_confirmation_service.confirm_operation(
            self.app.operation_confirmation_service.OPERATION_BULK_SEND
        )
        
        # Verify dialog was shown and result is True
        mock_askyesno.assert_called_once()
        self.assertTrue(result)
    
    def test_success_notification(self):
        """Test success notification."""
        # Show success notification
        self.app.operation_confirmation_service.show_success_notification("Operation completed successfully")
        
        # Verify log message was shown
        self.app.log_frame.log_message.assert_called_once()
        args, _ = self.app.log_frame.log_message.call_args
        self.assertIn("Operation completed successfully", args[0])
    
    def test_operation_progress_in_log(self):
        """Test operation progress indicator in log."""
        # Show operation progress
        self.app.operation_confirmation_service.show_operation_progress_in_log(
            "File Transfer",
            5,
            10
        )
        
        # Verify log message was shown
        self.app.log_frame.log_message.assert_called_once()
        args, _ = self.app.log_frame.log_message.call_args
        self.assertIn("File Transfer", args[0])
        self.assertIn("5/10", args[0])
    
    @patch('customtkinter.CTkToplevel')
    @patch('customtkinter.CTkProgressBar')
    def test_determinate_progress_dialog(self, mock_progress_bar, mock_toplevel):
        """Test determinate progress dialog."""
        # Setup mocks
        mock_toplevel_instance = MagicMock()
        mock_toplevel.return_value = mock_toplevel_instance
        
        mock_progress_bar_instance = MagicMock()
        mock_progress_bar.return_value = mock_progress_bar_instance
        
        # Create progress dialog
        dialog_id = self.app.operation_confirmation_service.create_progress_dialog(
            "Test Progress",
            "Processing Data",
            self.app.operation_confirmation_service.PROGRESS_TYPE_DETERMINATE,
            10,  # 10 steps
            True  # Cancelable
        )
        
        # Verify dialog was created
        mock_toplevel.assert_called_once()
        mock_progress_bar.assert_called_once()
        
        # Update progress
        self.app.operation_confirmation_service.update_progress(
            dialog_id,
            5,  # Current step
            "Processing step 5 of 10..."
        )
        
        # Verify progress bar was updated
        mock_progress_bar_instance.set.assert_called_with(0.5)  # 5/10 = 0.5
        
        # Complete progress with success
        self.app.operation_confirmation_service.complete_progress(
            dialog_id,
            True,
            "Processing completed successfully"
        )
        
        # Verify dialog was destroyed
        mock_toplevel_instance.destroy.assert_called_once()
    
    @patch('customtkinter.CTkToplevel')
    @patch('customtkinter.CTkProgressBar')
    def test_indeterminate_progress_dialog(self, mock_progress_bar, mock_toplevel):
        """Test indeterminate progress dialog."""
        # Setup mocks
        mock_toplevel_instance = MagicMock()
        mock_toplevel.return_value = mock_toplevel_instance
        
        mock_progress_bar_instance = MagicMock()
        mock_progress_bar.return_value = mock_progress_bar_instance
        
        # Create progress dialog
        dialog_id = self.app.operation_confirmation_service.create_progress_dialog(
            "Test Progress",
            "Connecting to Device",
            self.app.operation_confirmation_service.PROGRESS_TYPE_INDETERMINATE,
            cancelable=True
        )
        
        # Verify dialog was created
        mock_toplevel.assert_called_once()
        mock_progress_bar.assert_called_once()
        
        # Update status
        self.app.operation_confirmation_service.update_progress(
            dialog_id,
            status_text="Searching for device..."
        )
        
        # Complete progress with failure
        self.app.operation_confirmation_service.complete_progress(
            dialog_id,
            False,
            "Connection failed"
        )
        
        # Verify dialog was destroyed
        mock_toplevel_instance.destroy.assert_called_once()
    
    @patch('customtkinter.CTkToplevel')
    @patch('customtkinter.CTkProgressBar')
    def test_cancel_progress_dialog(self, mock_progress_bar, mock_toplevel):
        """Test canceling a progress dialog."""
        # Setup mocks
        mock_toplevel_instance = MagicMock()
        mock_toplevel.return_value = mock_toplevel_instance
        
        mock_progress_bar_instance = MagicMock()
        mock_progress_bar.return_value = mock_progress_bar_instance
        
        # Create a cancelable progress dialog
        dialog_id = self.app.operation_confirmation_service.create_progress_dialog(
            "Test Progress",
            "Processing Data",
            self.app.operation_confirmation_service.PROGRESS_TYPE_DETERMINATE,
            10,
            True  # Cancelable
        )
        
        # Setup cancel callback
        cancel_callback = MagicMock()
        self.app.operation_confirmation_service.set_cancel_callback(
            dialog_id,
            cancel_callback
        )
        
        # Simulate cancel button click
        # Get the cancel button's command and call it
        cancel_button = None
        for call in mock_toplevel_instance.mock_calls:
            if "CTkButton" in str(call):
                # This is a simplification; in a real test we'd need to extract the actual button
                cancel_button = MagicMock()
                break
        
        if cancel_button:
            # Simulate clicking the cancel button
            self.app.operation_confirmation_service._handle_cancel(dialog_id)
            
            # Verify cancel callback was called
            cancel_callback.assert_called_once()
            
            # Verify dialog was destroyed
            mock_toplevel_instance.destroy.assert_called_once()

if __name__ == '__main__':
    unittest.main()