"""
Test script for the AppConfigService.

This script tests the AppConfigService's ability to save and load application settings
such as theme and language preferences.
"""

import unittest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

# Add the project root to the path so we can import the modules
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.app_config_service import AppConfigService

class AppConfigServiceTest(unittest.TestCase):
    """Test the AppConfigService."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Create a temporary config file path
        self.config_path = os.path.join(self.temp_dir.name, "app_config.json")
        
        # Create AppConfigService instance
        self.app_config = AppConfigService()
        
        # Patch the _get_config_path method to use our test path
        patcher = patch.object(self.app_config, '_get_config_path', return_value=self.config_path)
        self.addCleanup(patcher.stop)
        patcher.start()
        
        # Reload config to ensure it's using our test path
        self.app_config.config = self.app_config._load_config()
    
    def tearDown(self):
        """Clean up after test."""
        # Clean up temporary directory
        self.temp_dir.cleanup()
    
    def test_theme_save_and_load(self):
        """Test saving and loading theme settings."""
        # Set theme to dark
        self.app_config.set_theme("Dark")
        
        # Verify config file was created
        self.assertTrue(os.path.exists(self.config_path))
        
        # Read the config file directly
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Verify config contains the correct theme
        self.assertEqual(config["theme"], "Dark")
        
        # Create a new AppConfigService instance to simulate application restart
        new_app_config = AppConfigService()
        
        # Patch the _get_config_path method to use our test path
        patcher = patch.object(new_app_config, '_get_config_path', return_value=self.config_path)
        self.addCleanup(patcher.stop)
        patcher.start()
        
        # Reload config to ensure it's using our test path
        new_app_config.config = new_app_config._load_config()
        
        # Verify theme was loaded correctly
        self.assertEqual(new_app_config.get_theme(), "Dark")
    
    def test_language_save_and_load(self):
        """Test saving and loading language settings."""
        # Set language to English
        self.app_config.set_language("en_US")
        
        # Verify config file was created
        self.assertTrue(os.path.exists(self.config_path))
        
        # Read the config file directly
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Verify config contains the correct language
        self.assertEqual(config["language"], "en_US")
        
        # Create a new AppConfigService instance to simulate application restart
        new_app_config = AppConfigService()
        
        # Patch the _get_config_path method to use our test path
        patcher = patch.object(new_app_config, '_get_config_path', return_value=self.config_path)
        self.addCleanup(patcher.stop)
        patcher.start()
        
        # Reload config to ensure it's using our test path
        new_app_config.config = new_app_config._load_config()
        
        # Verify language was loaded correctly
        self.assertEqual(new_app_config.get_language(), "en_US")
    
    def test_multiple_settings(self):
        """Test saving and loading multiple settings."""
        # Set both theme and language
        self.app_config.set_theme("Dark")
        self.app_config.set_language("en_US")
        
        # Verify config file was created
        self.assertTrue(os.path.exists(self.config_path))
        
        # Read the config file directly
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Verify config contains both settings
        self.assertEqual(config["theme"], "Dark")
        self.assertEqual(config["language"], "en_US")
        
        # Create a new AppConfigService instance to simulate application restart
        new_app_config = AppConfigService()
        
        # Patch the _get_config_path method to use our test path
        patcher = patch.object(new_app_config, '_get_config_path', return_value=self.config_path)
        self.addCleanup(patcher.stop)
        patcher.start()
        
        # Reload config to ensure it's using our test path
        new_app_config.config = new_app_config._load_config()
        
        # Verify both settings were loaded correctly
        self.assertEqual(new_app_config.get_theme(), "Dark")
        self.assertEqual(new_app_config.get_language(), "en_US")
    
    def test_default_values(self):
        """Test default values when no config file exists."""
        # Ensure config file doesn't exist
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        
        # Create a new AppConfigService instance
        new_app_config = AppConfigService()
        
        # Patch the _get_config_path method to use our test path
        patcher = patch.object(new_app_config, '_get_config_path', return_value=self.config_path)
        self.addCleanup(patcher.stop)
        patcher.start()
        
        # Reload config to ensure it's using our test path
        new_app_config.config = new_app_config._load_config()
        
        # Verify default values are returned
        self.assertEqual(new_app_config.get_theme(), "System")
        self.assertEqual(new_app_config.get_language(), "pt_BR")
    
    def test_invalid_config_file(self):
        """Test handling of invalid config file."""
        # Create an invalid config file
        with open(self.config_path, 'w') as f:
            f.write("This is not valid JSON")
        
        # Create a new AppConfigService instance
        new_app_config = AppConfigService()
        
        # Patch the _get_config_path method to use our test path
        patcher = patch.object(new_app_config, '_get_config_path', return_value=self.config_path)
        self.addCleanup(patcher.stop)
        patcher.start()
        
        # Reload config to ensure it's using our test path
        new_app_config.config = new_app_config._load_config()
        
        # Verify default values are returned
        self.assertEqual(new_app_config.get_theme(), "System")
        self.assertEqual(new_app_config.get_language(), "pt_BR")

if __name__ == '__main__':
    unittest.main()