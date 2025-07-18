"""
Test script for language persistence across application restarts.

This script tests the I18nService's ability to save and restore language settings
across application restarts, ensuring user preferences are maintained.
"""

import unittest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

# Add the project root to the path so we can import the modules
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.i18n_service import I18nService
from services.app_config_service import AppConfigService

class LanguagePersistenceTest(unittest.TestCase):
    """Test language persistence across application restarts."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Create a temporary config file path
        self.config_path = os.path.join(self.temp_dir.name, "app_config.json")
        
        # Patch AppConfigService to use our test path
        self.app_config_patcher = patch('services.app_config_service.AppConfigService._get_config_path', 
                                        return_value=self.config_path)
        self.app_config_patcher.start()
        
        # Create mock locale files
        self.create_mock_locale_files()
        
        # Patch resource_path to use our mock locale files
        self.resource_path_patcher = patch('services.i18n_service.resource_path', 
                                          side_effect=self.mock_resource_path)
        self.resource_path_patcher.start()
        
        # Create I18nService instance
        self.i18n_service = I18nService()
    
    def tearDown(self):
        """Clean up after test."""
        # Stop patchers
        self.app_config_patcher.stop()
        self.resource_path_patcher.stop()
        
        # Clean up temporary directory
        self.temp_dir.cleanup()
    
    def create_mock_locale_files(self):
        """Create mock locale files for testing."""
        # Create locales directory
        locales_dir = os.path.join(self.temp_dir.name, "assets", "locales")
        os.makedirs(locales_dir, exist_ok=True)
        
        # Create English locale file
        en_locale = {
            "test_key": "Test Value",
            "hello": "Hello",
            "app_title": "LT32Pro Device Configurator v1"
        }
        with open(os.path.join(locales_dir, "en_US.json"), 'w', encoding='utf-8') as f:
            json.dump(en_locale, f)
        
        # Create Portuguese locale file
        pt_locale = {
            "test_key": "Valor de Teste",
            "hello": "Olá",
            "app_title": "Configurador de Dispositivos LT32Pro v1"
        }
        with open(os.path.join(locales_dir, "pt_BR.json"), 'w', encoding='utf-8') as f:
            json.dump(pt_locale, f)
        
        # Create Spanish locale file
        es_locale = {
            "test_key": "Valor de Prueba",
            "hello": "Hola",
            "app_title": "Configurador de Dispositivos LT32Pro v1"
        }
        with open(os.path.join(locales_dir, "es_ES.json"), 'w', encoding='utf-8') as f:
            json.dump(es_locale, f)
    
    def mock_resource_path(self, relative_path):
        """Mock resource_path function to use our test directory."""
        # If the path contains 'locales', use our mock locale files
        if "locales" in relative_path:
            # Extract the filename from the path
            filename = os.path.basename(relative_path)
            return os.path.join(self.temp_dir.name, "assets", "locales", filename)
        return relative_path
    
    def test_language_save_and_load(self):
        """Test saving and loading language settings."""
        # Set language to English
        self.i18n_service.set_language("en_US")
        
        # Verify language was set
        self.assertEqual(self.i18n_service.current_language, "en_US")
        self.assertEqual(self.i18n_service.get("hello"), "Hello")
        
        # Verify config file was created
        self.assertTrue(os.path.exists(self.config_path))
        
        # Read the config file directly
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Verify config contains the correct language
        self.assertEqual(config["language"], "en_US")
        
        # Create a new I18nService instance to simulate application restart
        new_i18n_service = I18nService()
        
        # Verify language was loaded correctly
        self.assertEqual(new_i18n_service.current_language, "en_US")
        self.assertEqual(new_i18n_service.get("hello"), "Hello")
    
    def test_language_change_persistence(self):
        """Test language changes are persisted."""
        # Set initial language to English
        self.i18n_service.set_language("en_US")
        self.assertEqual(self.i18n_service.current_language, "en_US")
        
        # Change language to Portuguese
        self.i18n_service.set_language("pt_BR")
        self.assertEqual(self.i18n_service.current_language, "pt_BR")
        self.assertEqual(self.i18n_service.get("hello"), "Olá")
        
        # Create a new I18nService instance to simulate application restart
        new_i18n_service = I18nService()
        
        # Verify the new language was loaded
        self.assertEqual(new_i18n_service.current_language, "pt_BR")
        self.assertEqual(new_i18n_service.get("hello"), "Olá")
        
        # Change language to Spanish
        new_i18n_service.set_language("es_ES")
        self.assertEqual(new_i18n_service.current_language, "es_ES")
        self.assertEqual(new_i18n_service.get("hello"), "Hola")
        
        # Create another I18nService instance
        another_i18n_service = I18nService()
        
        # Verify the latest language was loaded
        self.assertEqual(another_i18n_service.current_language, "es_ES")
        self.assertEqual(another_i18n_service.get("hello"), "Hola")
    
    def test_invalid_config_file(self):
        """Test handling of invalid config file."""
        # Create an invalid config file
        with open(self.config_path, 'w') as f:
            f.write("This is not valid JSON")
        
        # Create I18nService instance
        invalid_i18n_service = I18nService()
        
        # Verify default language was used
        self.assertEqual(invalid_i18n_service.current_language, "pt_BR")
        self.assertEqual(invalid_i18n_service.get("hello"), "Olá")
    
    def test_missing_config_file(self):
        """Test handling of missing config file."""
        # Ensure config file doesn't exist
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        
        # Create I18nService instance
        missing_i18n_service = I18nService()
        
        # Verify default language was used
        self.assertEqual(missing_i18n_service.current_language, "pt_BR")
        self.assertEqual(missing_i18n_service.get("hello"), "Olá")
    
    def test_invalid_language_code(self):
        """Test handling of invalid language code."""
        # Store the original language
        original_language = self.i18n_service.current_language
        
        # Try to set an invalid language code
        self.i18n_service.set_language("invalid_code")
        
        # Verify language was not changed to the invalid code
        self.assertNotEqual(self.i18n_service.current_language, "invalid_code")
        
        # Verify the original language is still used
        self.assertEqual(self.i18n_service.current_language, original_language)

if __name__ == '__main__':
    unittest.main()