"""
Test script for connection error handling improvements.

This script tests the enhanced connection error handling features including:
- Detailed error messages for different connection failure scenarios
- Automatic reconnection attempts with user feedback
- Connection status monitoring with visual indicators
"""

import unittest
import tkinter as tk
import customtkinter as ctk
from unittest.mock import MagicMock, patch
import sys
import os
import time
import threading
import datetime
import serial

# Add the project root to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.error_handling_service import ErrorHandlingService
from services.serial_service import SerialService

class ConnectionErrorHandlingTest(unittest.TestCase):
    """Test connection error handling improvements."""
    
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
        
        # Create connection frame mock
        cls.app.connection_frame = MagicMock()
        cls.app.connection_frame.update_status = MagicMock()
        cls.app.connection_frame.update_connection_indicator = MagicMock()
        cls.app.connection_frame.show_reconnecting_status = MagicMock()
        cls.app.connection_frame.hide_reconnecting_status = MagicMock()
        cls.app.connection_frame.update_reconnection_status = MagicMock()
        cls.app.connection_frame.update_reconnection_countdown = MagicMock()
        cls.app.connection_frame.show_reconnection_failed = MagicMock()
        
        # Initialize services
        cls.app.error_handler = ErrorHandlingService(cls.app)
        cls.app.serial_service = SerialService(cls.app)
    
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
        self.app.connection_frame.show_reconnecting_status.reset_mock()
        self.app.connection_frame.hide_reconnecting_status.reset_mock()
        self.app.connection_frame.update_reconnection_status.reset_mock()
        self.app.connection_frame.update_reconnection_countdown.reset_mock()
        self.app.connection_frame.show_reconnection_failed.reset_mock()
        
        # Reset serial service state
        self.app.serial_service.is_connected = False
        self.app.serial_service.serial_port = None
        
        # Reset error handler state
        self.app.error_handler.reconnect_thread = None
        self.app.error_handler.stop_reconnect = False
        self.app.error_handler.reconnect_attempts = 0
        self.app.error_handler.auto_reconnect_enabled = True
    
    @patch('serial.Serial')
    def test_port_not_found_error(self, mock_serial):
        """Test port not found error handling."""
        # Setup mock to raise FileNotFoundError
        mock_serial.side_effect = serial.SerialException("could not open port 'COM1': FileNotFoundError(2, 'The system cannot find the file specified.', None, 2)")
        
        # Try to connect
        self.app.serial_service.connect("COM1")
        
        # Verify error was logged
        self.app.log_frame.log_message.assert_called()
        
        # Verify connection status was updated
        self.app.connection_frame.update_status.assert_called_with(False)
    
    @patch('serial.Serial')
    def test_port_in_use_error(self, mock_serial):
        """Test port in use error handling."""
        # Setup mock to raise PermissionError
        mock_serial.side_effect = serial.SerialException("could not open port 'COM1': PermissionError(13, 'Access is denied.', None, 5)")
        
        # Try to connect
        self.app.serial_service.connect("COM1")
        
        # Verify error was logged
        self.app.log_frame.log_message.assert_called()
        
        # Verify connection status was updated
        self.app.connection_frame.update_status.assert_called_with(False)
    
    @patch('serial.Serial')
    def test_timeout_error(self, mock_serial):
        """Test connection timeout error handling."""
        # Setup mock serial port
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.is_open = True
        
        # Connect to device
        self.app.serial_service.connect("COM1")
        
        # Reset mocks
        self.app.log_frame.log_message.reset_mock()
        
        # Simulate a timeout by manipulating the last activity time
        self.app.serial_service.last_activity_time = datetime.datetime.now() - datetime.timedelta(minutes=5)
        
        # Manually trigger the error handler
        error_type = self.app.error_handler.CONN_ERROR_TIMEOUT
        context = {'port': 'COM1'}
        self.app.error_handler.handle_error(error_type, self.app.error_handler.SEVERITY_ERROR, context)
        
        # Verify error was logged
        self.app.log_frame.log_message.assert_called()
        
        # Verify reconnection was attempted if auto-reconnect is enabled
        if self.app.error_handler.auto_reconnect_enabled:
            self.app.connection_frame.show_reconnecting_status.assert_called()
    
    @patch('serial.Serial')
    def test_device_disconnected_error(self, mock_serial):
        """Test device disconnected error handling."""
        # Setup mock serial port
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.is_open = True
        
        # Connect to device
        self.app.serial_service.connect("COM1")
        
        # Reset mocks
        self.app.log_frame.log_message.reset_mock()
        
        # Manually trigger the error handler
        error_type = self.app.error_handler.CONN_ERROR_DEVICE_DISCONNECTED
        context = {'port': 'COM1'}
        self.app.error_handler.handle_error(error_type, self.app.error_handler.SEVERITY_ERROR, context)
        
        # Verify error was logged
        self.app.log_frame.log_message.assert_called()
        
        # Verify reconnection was attempted if auto-reconnect is enabled
        if self.app.error_handler.auto_reconnect_enabled:
            self.app.connection_frame.show_reconnecting_status.assert_called()
    
    @patch('serial.Serial')
    def test_signal_lost_error(self, mock_serial):
        """Test signal lost error handling."""
        # Setup mock serial port
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.is_open = True
        
        # Connect to device
        self.app.serial_service.connect("COM1")
        
        # Reset mocks
        self.app.log_frame.log_message.reset_mock()
        
        # Manually trigger the error handler
        error_type = self.app.error_handler.CONN_ERROR_SIGNAL_LOST
        context = {'port': 'COM1'}
        self.app.error_handler.handle_error(error_type, self.app.error_handler.SEVERITY_ERROR, context)
        
        # Verify error was logged
        self.app.log_frame.log_message.assert_called()
        
        # Verify reconnection was attempted if auto-reconnect is enabled
        if self.app.error_handler.auto_reconnect_enabled:
            self.app.connection_frame.show_reconnecting_status.assert_called()
    
    @patch('serial.Serial')
    def test_auto_reconnect_disabled(self, mock_serial):
        """Test behavior when auto-reconnect is disabled."""
        # Setup mock serial port
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.is_open = True
        
        # Connect to device
        self.app.serial_service.connect("COM1")
        
        # Disable auto-reconnect
        self.app.error_handler.set_auto_reconnect(False)
        
        # Reset mocks
        self.app.log_frame.log_message.reset_mock()
        self.app.connection_frame.show_reconnecting_status.reset_mock()
        
        # Manually trigger the error handler
        error_type = self.app.error_handler.CONN_ERROR_DEVICE_DISCONNECTED
        context = {'port': 'COM1'}
        self.app.error_handler.handle_error(error_type, self.app.error_handler.SEVERITY_ERROR, context)
        
        # Verify error was logged
        self.app.log_frame.log_message.assert_called()
        
        # Verify reconnection was NOT attempted
        self.app.connection_frame.show_reconnecting_status.assert_not_called()
    
    @patch('serial.Serial')
    def test_stop_reconnection(self, mock_serial):
        """Test stopping reconnection attempts."""
        # Setup mock serial port
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.is_open = True
        
        # Connect to device
        self.app.serial_service.connect("COM1")
        
        # Manually trigger the error handler to start reconnection
        error_type = self.app.error_handler.CONN_ERROR_DEVICE_DISCONNECTED
        context = {'port': 'COM1'}
        self.app.error_handler.handle_error(error_type, self.app.error_handler.SEVERITY_ERROR, context)
        
        # Reset mocks
        self.app.log_frame.log_message.reset_mock()
        self.app.connection_frame.hide_reconnecting_status.reset_mock()
        
        # Stop reconnection
        self.app.error_handler.stop_reconnection()
        
        # Verify reconnection was stopped
        self.assertTrue(self.app.error_handler.stop_reconnect)
        
        # Verify reconnection UI was hidden
        self.app.connection_frame.hide_reconnecting_status.assert_called()
        
        # Verify log message was shown
        self.app.log_frame.log_message.assert_called()
    
    def test_connection_quality_update(self):
        """Test connection quality updates."""
        # Initial quality should be 100
        self.assertEqual(self.app.error_handler.connection_quality, 100)
        
        # Update quality negatively
        self.app.error_handler._update_connection_quality(-30)
        
        # Verify quality was updated
        self.assertEqual(self.app.error_handler.connection_quality, 70)
        
        # Update quality positively
        self.app.error_handler._update_connection_quality(20)
        
        # Verify quality was updated
        self.assertEqual(self.app.error_handler.connection_quality, 90)
        
        # Verify quality doesn't go below 0
        self.app.error_handler._update_connection_quality(-100)
        self.assertEqual(self.app.error_handler.connection_quality, 0)
        
        # Verify quality doesn't go above 100
        self.app.error_handler._update_connection_quality(200)
        self.assertEqual(self.app.error_handler.connection_quality, 100)
    
    def test_connection_status_message(self):
        """Test connection status message formatting."""
        # Test connected status with quality
        message = self.app.error_handler.get_connection_status_message(True, "COM1", 100)
        self.assertIn("COM1", message)
        self.assertIn("Excellent", message)
        
        message = self.app.error_handler.get_connection_status_message(True, "COM1", 80)
        self.assertIn("COM1", message)
        self.assertIn("Good", message)
        
        message = self.app.error_handler.get_connection_status_message(True, "COM1", 50)
        self.assertIn("COM1", message)
        self.assertIn("Fair", message)
        
        message = self.app.error_handler.get_connection_status_message(True, "COM1", 30)
        self.assertIn("COM1", message)
        self.assertIn("Poor", message)
        
        # Test disconnected status
        message = self.app.error_handler.get_connection_status_message(False)
        self.assertEqual(message, "Disconnected")
    
    def test_parse_error_from_exception(self):
        """Test parsing error types from exceptions."""
        # Test port not found error
        exception = serial.SerialException("could not open port 'COM1': FileNotFoundError(2, 'The system cannot find the file specified.', None, 2)")
        error_type, context = self.app.error_handler.parse_error_from_exception(exception)
        self.assertEqual(error_type, self.app.error_handler.CONN_ERROR_PORT_NOT_FOUND)
        
        # Test port in use error
        exception = serial.SerialException("could not open port 'COM1': PermissionError(13, 'Access is denied.', None, 5)")
        error_type, context = self.app.error_handler.parse_error_from_exception(exception)
        self.assertEqual(error_type, self.app.error_handler.CONN_ERROR_ACCESS_DENIED)
        
        # Test timeout error
        exception = serial.SerialException("timeout")
        error_type, context = self.app.error_handler.parse_error_from_exception(exception)
        self.assertEqual(error_type, self.app.error_handler.CONN_ERROR_TIMEOUT)
        
        # Test disconnected error
        exception = serial.SerialException("device disconnected")
        error_type, context = self.app.error_handler.parse_error_from_exception(exception)
        self.assertEqual(error_type, self.app.error_handler.CONN_ERROR_DEVICE_DISCONNECTED)
        
        # Test signal lost error
        exception = serial.SerialException("connection lost - signal lost")
        error_type, context = self.app.error_handler.parse_error_from_exception(exception)
        self.assertEqual(error_type, self.app.error_handler.CONN_ERROR_SIGNAL_LOST)
        
        # Test unknown error
        exception = Exception("some unknown error")
        error_type, context = self.app.error_handler.parse_error_from_exception(exception)
        self.assertEqual(error_type, self.app.error_handler.CONN_ERROR_UNKNOWN)

if __name__ == '__main__':
    unittest.main()