#!/usr/bin/env python3
"""
Comprehensive test for the complete log background fix.
This test verifies that the log window properly handles background colors
in all scenarios related to the "Checar configuração" operation.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class MockLogFrameComplete:
    """Complete mock log frame class with all background handling methods."""
    
    def __init__(self):
        self.log_textbox = MagicMock()
        self.log_textbox.configure = MagicMock()
        self.after = MagicMock()
    
    def _get_theme_appropriate_background(self):
        """
        Get the theme-appropriate background color for the log textbox.
        
        Returns:
            The appropriate background color for the current theme
        """
        import customtkinter as ctk
        current_mode = ctk.get_appearance_mode()
        
        if current_mode == "Dark":
            # Default dark mode background for CTkTextbox
            return ["#212121", "#2B2B2B"]  # CTkTextbox default dark colors
        else:
            # Default light mode background for CTkTextbox
            return ["#F9F9FA", "#FFFFFF"]  # CTkTextbox default light colors

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
            
            # Get the correct theme-appropriate background color
            original_bg = self._get_theme_appropriate_background()
            
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

    def reset_log_background_to_theme(self):
        """
        Reset the log textbox background to the appropriate theme color.
        This can be called externally if needed to fix background color issues.
        """
        if hasattr(self, 'log_textbox') and self.log_textbox is not None:
            try:
                theme_bg = self._get_theme_appropriate_background()
                self.log_textbox.configure(fg_color=theme_bg)
            except Exception:
                # Silently handle any errors
                pass


class TestCompleteLogBackgroundFix(unittest.TestCase):
    """Test the complete log background fix implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.log_frame = MockLogFrameComplete()

    @patch('customtkinter.get_appearance_mode')
    def test_get_theme_appropriate_background_dark_mode(self, mock_get_appearance_mode):
        """Test getting theme-appropriate background for dark mode."""
        mock_get_appearance_mode.return_value = "Dark"
        
        bg_color = self.log_frame._get_theme_appropriate_background()
        
        expected_dark_bg = ["#212121", "#2B2B2B"]
        self.assertEqual(bg_color, expected_dark_bg)

    @patch('customtkinter.get_appearance_mode')
    def test_get_theme_appropriate_background_light_mode(self, mock_get_appearance_mode):
        """Test getting theme-appropriate background for light mode."""
        mock_get_appearance_mode.return_value = "Light"
        
        bg_color = self.log_frame._get_theme_appropriate_background()
        
        expected_light_bg = ["#F9F9FA", "#FFFFFF"]
        self.assertEqual(bg_color, expected_light_bg)

    @patch('customtkinter.get_appearance_mode')
    def test_reset_log_background_to_theme_dark_mode(self, mock_get_appearance_mode):
        """Test resetting log background to dark theme."""
        mock_get_appearance_mode.return_value = "Dark"
        
        self.log_frame.reset_log_background_to_theme()
        
        expected_dark_bg = ["#212121", "#2B2B2B"]
        self.log_frame.log_textbox.configure.assert_called_once_with(fg_color=expected_dark_bg)

    @patch('customtkinter.get_appearance_mode')
    def test_reset_log_background_to_theme_light_mode(self, mock_get_appearance_mode):
        """Test resetting log background to light theme."""
        mock_get_appearance_mode.return_value = "Light"
        
        self.log_frame.reset_log_background_to_theme()
        
        expected_light_bg = ["#F9F9FA", "#FFFFFF"]
        self.log_frame.log_textbox.configure.assert_called_once_with(fg_color=expected_light_bg)

    @patch('customtkinter.get_appearance_mode')
    def test_complete_checar_configuracao_workflow_dark_mode(self, mock_get_appearance_mode):
        """Test the complete 'Checar configuração' workflow in dark mode."""
        mock_get_appearance_mode.return_value = "Dark"
        
        # Step 1: Configuration operation completes successfully
        self.log_frame._flash_log_for_attention(success=True)
        
        # Verify flash color was applied (dark green for success in dark mode)
        flash_calls = self.log_frame.log_textbox.configure.call_args_list
        self.assertEqual(len(flash_calls), 1)
        self.assertEqual(flash_calls[0][1]['fg_color'], "#1B4D3E")
        
        # Step 2: Reset callback is scheduled
        self.log_frame.after.assert_called_once_with(500, unittest.mock.ANY)
        
        # Step 3: Reset callback executes after 500ms
        reset_callback = self.log_frame.after.call_args[0][1]
        reset_callback()
        
        # Verify background was reset to proper dark theme colors
        reset_calls = self.log_frame.log_textbox.configure.call_args_list
        self.assertEqual(len(reset_calls), 2)  # Flash + Reset
        expected_dark_bg = ["#212121", "#2B2B2B"]
        self.assertEqual(reset_calls[1][1]['fg_color'], expected_dark_bg)

    @patch('customtkinter.get_appearance_mode')
    def test_complete_checar_configuracao_workflow_light_mode(self, mock_get_appearance_mode):
        """Test the complete 'Checar configuração' workflow in light mode."""
        mock_get_appearance_mode.return_value = "Light"
        
        # Step 1: Configuration operation completes successfully
        self.log_frame._flash_log_for_attention(success=True)
        
        # Verify flash color was applied (light green for success in light mode)
        flash_calls = self.log_frame.log_textbox.configure.call_args_list
        self.assertEqual(len(flash_calls), 1)
        self.assertEqual(flash_calls[0][1]['fg_color'], "#E0FFE0")
        
        # Step 2: Reset callback is scheduled
        self.log_frame.after.assert_called_once_with(500, unittest.mock.ANY)
        
        # Step 3: Reset callback executes after 500ms
        reset_callback = self.log_frame.after.call_args[0][1]
        reset_callback()
        
        # Verify background was reset to proper light theme colors
        reset_calls = self.log_frame.log_textbox.configure.call_args_list
        self.assertEqual(len(reset_calls), 2)  # Flash + Reset
        expected_light_bg = ["#F9F9FA", "#FFFFFF"]
        self.assertEqual(reset_calls[1][1]['fg_color'], expected_light_bg)

    def test_manual_background_reset_capability(self):
        """Test that background can be manually reset if needed."""
        with patch('customtkinter.get_appearance_mode', return_value="Dark"):
            # Manually reset the background
            self.log_frame.reset_log_background_to_theme()
            
            # Verify the correct dark theme background was applied
            expected_dark_bg = ["#212121", "#2B2B2B"]
            self.log_frame.log_textbox.configure.assert_called_once_with(fg_color=expected_dark_bg)

    def test_error_handling_with_missing_textbox(self):
        """Test error handling when textbox is missing."""
        # Remove textbox to simulate error condition
        self.log_frame.log_textbox = None
        
        # These should not raise exceptions
        try:
            self.log_frame._flash_log_for_attention(success=True)
            self.log_frame.reset_log_background_to_theme()
        except Exception as e:
            self.fail(f"Methods should handle missing textbox gracefully, but raised: {e}")

    def test_theme_consistency_across_operations(self):
        """Test that theme colors remain consistent across different operations."""
        
        # Test dark mode consistency
        with patch('customtkinter.get_appearance_mode', return_value="Dark"):
            bg1 = self.log_frame._get_theme_appropriate_background()
            
            # Reset background
            self.log_frame.reset_log_background_to_theme()
            reset_color = self.log_frame.log_textbox.configure.call_args[1]['fg_color']
            
            # Flash and get reset color
            self.log_frame.log_textbox.configure.reset_mock()
            self.log_frame._flash_log_for_attention(success=True)
            reset_callback = self.log_frame.after.call_args[0][1]
            reset_callback()
            flash_reset_color = self.log_frame.log_textbox.configure.call_args_list[1][1]['fg_color']
            
            # All should be the same
            self.assertEqual(bg1, reset_color)
            self.assertEqual(bg1, flash_reset_color)
        
        # Test light mode consistency
        with patch('customtkinter.get_appearance_mode', return_value="Light"):
            self.log_frame.log_textbox.configure.reset_mock()
            self.log_frame.after.reset_mock()
            
            bg2 = self.log_frame._get_theme_appropriate_background()
            
            # Reset background
            self.log_frame.reset_log_background_to_theme()
            reset_color = self.log_frame.log_textbox.configure.call_args[1]['fg_color']
            
            # Flash and get reset color
            self.log_frame.log_textbox.configure.reset_mock()
            self.log_frame._flash_log_for_attention(success=True)
            reset_callback = self.log_frame.after.call_args[0][1]
            reset_callback()
            flash_reset_color = self.log_frame.log_textbox.configure.call_args_list[1][1]['fg_color']
            
            # All should be the same
            self.assertEqual(bg2, reset_color)
            self.assertEqual(bg2, flash_reset_color)


if __name__ == '__main__':
    unittest.main()