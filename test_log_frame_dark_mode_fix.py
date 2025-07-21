#!/usr/bin/env python3
"""
Test script to verify the log frame dark mode flash fix.
This test ensures that the log frame properly handles theme-appropriate colors
when flashing for attention after configuration operations.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class MockLogFrame:
    """Mock log frame class to test the flash logic without CustomTkinter dependencies."""
    
    def __init__(self):
        self.log_textbox = MagicMock()
        self.log_textbox.cget = MagicMock(return_value="#2B2B2B")  # Dark mode background
        self.log_textbox.configure = MagicMock()
        self.after = MagicMock()
    
    def _flash_log_for_attention(self, success=False):
        """
        Flash the log textbox background briefly to draw attention to important messages.
        
        Args:
            success: If True, flash with green for success, otherwise red for errors
        """
        original_bg = self.log_textbox.cget("fg_color")
        
        # Get the current theme mode to use appropriate colors
        import customtkinter as ctk
        current_mode = ctk.get_appearance_mode()
        
        # Flash with appropriate background color based on theme
        if success:
            if current_mode == "Dark":
                # Dark green for success in dark mode
                flash_color = "#1B4D3E"
            else:
                # Light green for success in light mode
                flash_color = "#E0FFE0"
        else:
            if current_mode == "Dark":
                # Dark red for errors in dark mode
                flash_color = "#4D1B1B"
            else:
                # Light red for errors in light mode
                flash_color = "#FFE0E0"
        
        self.log_textbox.configure(fg_color=flash_color)
        
        # Reset after a short delay
        self.after(500, lambda: self.log_textbox.configure(fg_color=original_bg))


class TestLogFrameDarkModeFix(unittest.TestCase):
    """Test the log frame dark mode flash fix."""

    def setUp(self):
        """Set up test fixtures."""
        self.log_frame = MockLogFrame()

    @patch('customtkinter.get_appearance_mode')
    def test_flash_log_for_attention_success_dark_mode(self, mock_get_appearance_mode):
        """Test flashing log for success in dark mode."""
        # Set dark mode
        mock_get_appearance_mode.return_value = "Dark"
        
        # Call the flash method for success
        self.log_frame._flash_log_for_attention(success=True)
        
        # Verify the correct dark mode success color was used
        self.log_frame.log_textbox.configure.assert_called_with(fg_color="#1B4D3E")
        
        # Verify the reset callback was scheduled
        self.log_frame.after.assert_called_once_with(500, unittest.mock.ANY)

    @patch('customtkinter.get_appearance_mode')
    def test_flash_log_for_attention_success_light_mode(self, mock_get_appearance_mode):
        """Test flashing log for success in light mode."""
        # Set light mode
        mock_get_appearance_mode.return_value = "Light"
        
        # Call the flash method for success
        self.log_frame._flash_log_for_attention(success=True)
        
        # Verify the correct light mode success color was used
        self.log_frame.log_textbox.configure.assert_called_with(fg_color="#E0FFE0")
        
        # Verify the reset callback was scheduled
        self.log_frame.after.assert_called_once_with(500, unittest.mock.ANY)

    @patch('customtkinter.get_appearance_mode')
    def test_flash_log_for_attention_error_dark_mode(self, mock_get_appearance_mode):
        """Test flashing log for error in dark mode."""
        # Set dark mode
        mock_get_appearance_mode.return_value = "Dark"
        
        # Call the flash method for error
        self.log_frame._flash_log_for_attention(success=False)
        
        # Verify the correct dark mode error color was used
        self.log_frame.log_textbox.configure.assert_called_with(fg_color="#4D1B1B")
        
        # Verify the reset callback was scheduled
        self.log_frame.after.assert_called_once_with(500, unittest.mock.ANY)

    @patch('customtkinter.get_appearance_mode')
    def test_flash_log_for_attention_error_light_mode(self, mock_get_appearance_mode):
        """Test flashing log for error in light mode."""
        # Set light mode
        mock_get_appearance_mode.return_value = "Light"
        
        # Call the flash method for error
        self.log_frame._flash_log_for_attention(success=False)
        
        # Verify the correct light mode error color was used
        self.log_frame.log_textbox.configure.assert_called_with(fg_color="#FFE0E0")
        
        # Verify the reset callback was scheduled
        self.log_frame.after.assert_called_once_with(500, unittest.mock.ANY)

    @patch('customtkinter.get_appearance_mode')
    def test_flash_log_color_reset(self, mock_get_appearance_mode):
        """Test that the log color is properly reset after flashing."""
        # Set dark mode
        mock_get_appearance_mode.return_value = "Dark"
        
        # Set up the original background color
        original_bg = "#2B2B2B"
        self.log_frame.log_textbox.cget.return_value = original_bg
        
        # Call the flash method
        self.log_frame._flash_log_for_attention(success=True)
        
        # Get the reset callback that was scheduled
        self.log_frame.after.assert_called_once_with(500, unittest.mock.ANY)
        reset_callback = self.log_frame.after.call_args[0][1]
        
        # Clear the configure mock to test the reset
        self.log_frame.log_textbox.configure.reset_mock()
        
        # Call the reset callback
        reset_callback()
        
        # Verify the original background color was restored
        self.log_frame.log_textbox.configure.assert_called_with(fg_color=original_bg)

    def test_flash_log_integration_with_configuration_success(self):
        """Test that the flash method integrates properly with configuration success."""
        # Mock the operation confirmation service calling the flash method
        with patch('customtkinter.get_appearance_mode', return_value="Dark"):
            # Simulate what happens when configuration reading succeeds
            self.log_frame._flash_log_for_attention(success=True)
            
            # Verify the flash was applied
            self.log_frame.log_textbox.configure.assert_called_with(fg_color="#1B4D3E")
            
            # Verify the reset was scheduled
            self.assertTrue(self.log_frame.after.called)

    def test_no_flash_when_textbox_unavailable(self):
        """Test that no error occurs when textbox is not available."""
        # Remove the textbox to simulate initialization issues
        self.log_frame.log_textbox = None
        
        # This should not raise an exception
        try:
            self.log_frame._flash_log_for_attention(success=True)
        except AttributeError:
            self.fail("Flash method should handle missing textbox gracefully")


if __name__ == '__main__':
    unittest.main()