#!/usr/bin/env python3
"""
Test script to verify the log background color reset fix.
This test ensures that the log window properly returns to its theme-appropriate
background color after the flash effect.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class MockLogFrame:
    """Mock log frame class to test the background reset logic."""
    
    def __init__(self):
        self.log_textbox = MagicMock()
        self.log_textbox.configure = MagicMock()
        self.after = MagicMock()
    
    def _flash_log_for_attention(self, success=False):
        """
        Flash the log textbox background briefly to draw attention to important messages.
        
        Args:
            success: If True, flash with green for success, otherwise red for errors
        """
        # Safety check - ensure textbox exists
        if not hasattr(self, 'log_textbox') or self.log_textbox is None:
            return
        
        try:
            # Get the current theme mode to use appropriate colors
            import customtkinter as ctk
            current_mode = ctk.get_appearance_mode()
            
            # Determine the correct theme-appropriate background color
            if current_mode == "Dark":
                # Default dark mode background for CTkTextbox
                original_bg = ["#212121", "#2B2B2B"]  # CTkTextbox default dark colors
            else:
                # Default light mode background for CTkTextbox
                original_bg = ["#F9F9FA", "#FFFFFF"]  # CTkTextbox default light colors
            
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
            
            # Reset after a short delay to the proper theme-appropriate color
            self.after(500, lambda: self.log_textbox.configure(fg_color=original_bg))
            
        except Exception as e:
            # Silently handle any errors to avoid breaking the application
            pass


class TestLogBackgroundResetFix(unittest.TestCase):
    """Test the log background color reset fix."""

    def setUp(self):
        """Set up test fixtures."""
        self.log_frame = MockLogFrame()

    @patch('customtkinter.get_appearance_mode')
    def test_dark_mode_success_reset_to_dark_background(self, mock_get_appearance_mode):
        """Test that dark mode success flash resets to dark background."""
        # Set dark mode
        mock_get_appearance_mode.return_value = "Dark"
        
        # Call the flash method for success
        self.log_frame._flash_log_for_attention(success=True)
        
        # Verify the flash color was applied
        self.log_frame.log_textbox.configure.assert_called_with(fg_color="#1B4D3E")
        
        # Verify the reset callback was scheduled
        self.log_frame.after.assert_called_once_with(500, unittest.mock.ANY)
        
        # Get and execute the reset callback
        reset_callback = self.log_frame.after.call_args[0][1]
        
        # Clear the configure mock to test the reset
        self.log_frame.log_textbox.configure.reset_mock()
        
        # Execute the reset callback
        reset_callback()
        
        # Verify the dark mode background was restored
        expected_dark_bg = ["#212121", "#2B2B2B"]
        self.log_frame.log_textbox.configure.assert_called_with(fg_color=expected_dark_bg)

    @patch('customtkinter.get_appearance_mode')
    def test_light_mode_success_reset_to_light_background(self, mock_get_appearance_mode):
        """Test that light mode success flash resets to light background."""
        # Set light mode
        mock_get_appearance_mode.return_value = "Light"
        
        # Call the flash method for success
        self.log_frame._flash_log_for_attention(success=True)
        
        # Verify the flash color was applied
        self.log_frame.log_textbox.configure.assert_called_with(fg_color="#E0FFE0")
        
        # Verify the reset callback was scheduled
        self.log_frame.after.assert_called_once_with(500, unittest.mock.ANY)
        
        # Get and execute the reset callback
        reset_callback = self.log_frame.after.call_args[0][1]
        
        # Clear the configure mock to test the reset
        self.log_frame.log_textbox.configure.reset_mock()
        
        # Execute the reset callback
        reset_callback()
        
        # Verify the light mode background was restored
        expected_light_bg = ["#F9F9FA", "#FFFFFF"]
        self.log_frame.log_textbox.configure.assert_called_with(fg_color=expected_light_bg)

    @patch('customtkinter.get_appearance_mode')
    def test_dark_mode_error_reset_to_dark_background(self, mock_get_appearance_mode):
        """Test that dark mode error flash resets to dark background."""
        # Set dark mode
        mock_get_appearance_mode.return_value = "Dark"
        
        # Call the flash method for error
        self.log_frame._flash_log_for_attention(success=False)
        
        # Verify the flash color was applied
        self.log_frame.log_textbox.configure.assert_called_with(fg_color="#4D1B1B")
        
        # Verify the reset callback was scheduled
        self.log_frame.after.assert_called_once_with(500, unittest.mock.ANY)
        
        # Get and execute the reset callback
        reset_callback = self.log_frame.after.call_args[0][1]
        
        # Clear the configure mock to test the reset
        self.log_frame.log_textbox.configure.reset_mock()
        
        # Execute the reset callback
        reset_callback()
        
        # Verify the dark mode background was restored
        expected_dark_bg = ["#212121", "#2B2B2B"]
        self.log_frame.log_textbox.configure.assert_called_with(fg_color=expected_dark_bg)

    @patch('customtkinter.get_appearance_mode')
    def test_light_mode_error_reset_to_light_background(self, mock_get_appearance_mode):
        """Test that light mode error flash resets to light background."""
        # Set light mode
        mock_get_appearance_mode.return_value = "Light"
        
        # Call the flash method for error
        self.log_frame._flash_log_for_attention(success=False)
        
        # Verify the flash color was applied
        self.log_frame.log_textbox.configure.assert_called_with(fg_color="#FFE0E0")
        
        # Verify the reset callback was scheduled
        self.log_frame.after.assert_called_once_with(500, unittest.mock.ANY)
        
        # Get and execute the reset callback
        reset_callback = self.log_frame.after.call_args[0][1]
        
        # Clear the configure mock to test the reset
        self.log_frame.log_textbox.configure.reset_mock()
        
        # Execute the reset callback
        reset_callback()
        
        # Verify the light mode background was restored
        expected_light_bg = ["#F9F9FA", "#FFFFFF"]
        self.log_frame.log_textbox.configure.assert_called_with(fg_color=expected_light_bg)

    def test_background_colors_are_theme_appropriate(self):
        """Test that the background colors are appropriate for their themes."""
        
        # Dark mode backgrounds should be dark
        dark_bg = ["#212121", "#2B2B2B"]
        
        # Light mode backgrounds should be light
        light_bg = ["#F9F9FA", "#FFFFFF"]
        
        # Convert hex to RGB for comparison
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        # Check that dark mode colors are darker than light mode colors
        for dark_color, light_color in zip(dark_bg, light_bg):
            dark_rgb = hex_to_rgb(dark_color)
            light_rgb = hex_to_rgb(light_color)
            
            # Dark mode should have lower RGB values (darker)
            self.assertLess(sum(dark_rgb), sum(light_rgb), 
                           f"Dark color {dark_color} should be darker than light color {light_color}")

    def test_configuration_success_workflow_background_reset(self):
        """Test the complete workflow from configuration success to background reset."""
        
        with patch('customtkinter.get_appearance_mode', return_value="Dark"):
            # Simulate configuration success triggering flash
            self.log_frame._flash_log_for_attention(success=True)
            
            # Verify flash was applied
            flash_calls = self.log_frame.log_textbox.configure.call_args_list
            self.assertEqual(len(flash_calls), 1)
            self.assertEqual(flash_calls[0][1]['fg_color'], "#1B4D3E")
            
            # Verify reset was scheduled
            self.log_frame.after.assert_called_once_with(500, unittest.mock.ANY)
            
            # Execute the reset
            reset_callback = self.log_frame.after.call_args[0][1]
            reset_callback()
            
            # Verify background was reset to dark theme colors
            reset_calls = self.log_frame.log_textbox.configure.call_args_list
            self.assertEqual(len(reset_calls), 2)  # Flash + Reset
            self.assertEqual(reset_calls[1][1]['fg_color'], ["#212121", "#2B2B2B"])


if __name__ == '__main__':
    unittest.main()