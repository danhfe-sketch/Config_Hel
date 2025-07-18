"""
Test script for theme persistence across application restarts.

This script tests the ThemeService's ability to save and restore theme settings
across application restarts, ensuring user preferences are maintained.
"""

import unittest
import os
import json
import tempfile
import tkinter as tk
import customtkinter as ctk
from unittest.mock import patch, MagicMock

# Add the project root to the path so we can import the modules
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.theme_service import ThemeService
from services.app_config_service import AppConfigService

class ThemePersistenceTest(unittest.TestCase):
    """Test theme persistence across application restarts."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Create a temporary config file path
        self.config_path = os.path.join(self.temp_dir.name, "app_config.json")
        
        # Create a mock app
        self.app = MagicMock()
        self.app.root = ctk.CTk()
        self.app.root.withdraw()  # Hide the window
        
        # Patch AppConfigService to use our test path
        self.app_config_patcher = patch('services.app_config_service.AppConfigService._get_config_path', 
                                        return_value=self.config_path)
        self.app_config_patcher.start()
        
        # Create ThemeService instance
        self.theme_service = ThemeService(self.app)
        
        # Store original appearance mode
        self.original_mode = ctk.get_appearance_mode()
    
    def tearDown(self):
        """Clean up after test."""
        # Restore original appearance mode
        ctk.set_appearance_mode(self.original_mode)
        
        # Stop patchers
        self.app_config_patcher.stop()
        
        # Clean up temporary directory
        self.temp_dir.cleanup()
        
        # Destroy the root window
        self.app.root.destroy()
    
    def test_theme_save_and_load(self):
        """Test saving and loading theme settings."""
        # Set theme to dark
        self.theme_service.set_theme("Dark")
        
        # Verify theme was set
        self.assertEqual(self.theme_service.current_theme, "Dark")
        self.assertEqual(ctk.get_appearance_mode(), "Dark")
        
        # Verify config file was created
        self.assertTrue(os.path.exists(self.config_path))
        
        # Read the config file directly
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Verify config contains the correct theme
        self.assertEqual(config["theme"], "Dark")
        
        # Create a new ThemeService instance to simulate application restart
        new_theme_service = ThemeService(self.app)
        
        # Load theme (happens automatically in __init__)
        
        # Verify theme was loaded correctly
        self.assertEqual(new_theme_service.current_theme, "Dark")
        self.assertEqual(ctk.get_appearance_mode(), "Dark")
    
    def test_theme_change_persistence(self):
        """Test theme changes are persisted."""
        # Set initial theme to light
        self.theme_service.set_theme("Light")
        self.assertEqual(self.theme_service.current_theme, "Light")
        
        # Change theme to dark
        self.theme_service.set_theme("Dark")
        self.assertEqual(self.theme_service.current_theme, "Dark")
        
        # Create a new ThemeService instance to simulate application restart
        new_theme_service = ThemeService(self.app)
        
        # Verify the new theme was loaded
        self.assertEqual(new_theme_service.current_theme, "Dark")
        
        # Change theme to system
        new_theme_service.set_theme("System")
        self.assertEqual(new_theme_service.current_theme, "System")
        
        # Create another ThemeService instance
        another_theme_service = ThemeService(self.app)
        
        # Verify the latest theme was loaded
        self.assertEqual(another_theme_service.current_theme, "System")
    
    def test_invalid_config_file(self):
        """Test handling of invalid config file."""
        # Create an invalid config file
        with open(self.config_path, 'w') as f:
            f.write("This is not valid JSON")
        
        # Create ThemeService instance
        invalid_theme_service = ThemeService(self.app)
        
        # Verify default theme was used
        self.assertEqual(invalid_theme_service.current_theme, "System")
    
    def test_missing_config_file(self):
        """Test handling of missing config file."""
        # Ensure config file doesn't exist
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        
        # Create ThemeService instance
        missing_theme_service = ThemeService(self.app)
        
        # Verify default theme was used
        self.assertEqual(missing_theme_service.current_theme, "System")
    
    def test_theme_methods(self):
        """Test theme service methods."""
        # Reset to default theme first
        self.theme_service.reset_to_default()
        
        # Test get_current_theme
        self.assertEqual(self.theme_service.get_current_theme(), "System")
        
        # Test get_available_themes
        self.assertEqual(self.theme_service.get_available_themes(), ["Light", "Dark", "System"])
        
        # Test set_theme
        self.theme_service.set_theme("Dark")
        self.assertEqual(self.theme_service.get_current_theme(), "Dark")
        
        # Test reset_to_default
        self.theme_service.reset_to_default()
        self.assertEqual(self.theme_service.get_current_theme(), "System")
    
    def test_system_theme_detection(self):
        """Test system theme detection."""
        # This test is limited since we can't easily change the system theme
        # during a test, but we can verify the method exists and returns a value
        
        # Set theme to system
        self.theme_service.set_theme("System")
        
        # Test is_dark_mode_active
        is_dark = self.theme_service.is_dark_mode_active()
        self.assertIsInstance(is_dark, bool)

if __name__ == '__main__':
    unittest.main()