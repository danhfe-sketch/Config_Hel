#!/usr/bin/env python3
"""
Test script for ThemeService functionality.
This script tests the core functionality of the ThemeService without requiring the full GUI.
"""

import os
import json
import tempfile
from services.theme_service import ThemeService

class MockApp:
    """Mock application class for testing."""
    def __init__(self):
        self.log_frame = None

def test_theme_service():
    """Test ThemeService functionality."""
    print("Testing ThemeService...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock app
        mock_app = MockApp()
        
        # Override the config path to use temp directory
        original_resource_path = None
        try:
            from utils.helpers import resource_path
            original_resource_path = resource_path
        except ImportError:
            pass
        
        # Create theme service
        theme_service = ThemeService(mock_app)
        theme_service.config_path = os.path.join(temp_dir, "theme_config.json")
        
        # Test 1: Default theme
        print(f"✓ Default theme: {theme_service.get_current_theme()}")
        assert theme_service.get_current_theme() == "System"
        
        # Test 2: Available themes
        available_themes = theme_service.get_available_themes()
        print(f"✓ Available themes: {available_themes}")
        assert "Light" in available_themes
        assert "Dark" in available_themes
        assert "System" in available_themes
        
        # Test 3: Set theme
        theme_service.set_theme("Dark")
        print(f"✓ Theme set to Dark: {theme_service.get_current_theme()}")
        assert theme_service.get_current_theme() == "Dark"
        
        # Test 4: Theme persistence
        assert os.path.exists(theme_service.config_path)
        with open(theme_service.config_path, 'r') as f:
            config_data = json.load(f)
        print(f"✓ Theme saved to config: {config_data['theme']}")
        assert config_data['theme'] == "Dark"
        
        # Test 5: Load saved theme
        new_theme_service = ThemeService(mock_app)
        new_theme_service.config_path = theme_service.config_path
        new_theme_service.load_saved_theme()
        print(f"✓ Theme loaded from config: {new_theme_service.get_current_theme()}")
        assert new_theme_service.get_current_theme() == "Dark"
        
        # Test 6: Invalid theme handling
        try:
            theme_service.set_theme("InvalidTheme")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            print(f"✓ Invalid theme properly rejected: {e}")
        
        # Test 7: Reset to default
        theme_service.reset_to_default()
        print(f"✓ Reset to default: {theme_service.get_current_theme()}")
        assert theme_service.get_current_theme() == "System"
        
        # Test 8: Dark mode detection
        theme_service.set_theme("Dark")
        print(f"✓ Dark mode active (Dark theme): {theme_service.is_dark_mode_active()}")
        
        theme_service.set_theme("Light")
        print(f"✓ Dark mode active (Light theme): {theme_service.is_dark_mode_active()}")
        
        print("\n✅ All ThemeService tests passed!")

if __name__ == "__main__":
    test_theme_service()