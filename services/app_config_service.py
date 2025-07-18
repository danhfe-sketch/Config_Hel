import json
import os
import sys
from datetime import datetime

class AppConfigService:
    """
    Centralized service for managing application configuration settings.
    Handles saving and loading of theme, language, and other app settings.
    """
    
    CONFIG_FILE = "app_config.json"
    DEFAULT_THEME = "System"
    DEFAULT_LANGUAGE = "pt_BR"
    
    def __init__(self):
        """Initialize the AppConfigService."""
        self.config = self._load_config()
    
    def get_theme(self):
        """Get the saved theme preference."""
        return self.config.get("theme", self.DEFAULT_THEME)
    
    def set_theme(self, theme):
        """Set and save the theme preference."""
        self.config["theme"] = theme
        self.config["last_updated"] = datetime.now().isoformat()
        self._save_config()
    
    def get_language(self):
        """Get the saved language preference."""
        return self.config.get("language", self.DEFAULT_LANGUAGE)
    
    def set_language(self, language):
        """Set and save the language preference."""
        self.config["language"] = language
        self.config["last_updated"] = datetime.now().isoformat()
        self._save_config()
    
    def _load_config(self):
        """Load configuration from file."""
        try:
            config_path = self._get_config_path()
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading app configuration: {e}")
            return {}
    
    def _save_config(self):
        """Save configuration to file."""
        try:
            config_path = self._get_config_path()
            config_dir = os.path.dirname(config_path)
            
            # Ensure directory exists
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            
            # Save the config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
                
            print(f"App configuration saved to {config_path}")
        except Exception as e:
            print(f"Error saving app configuration: {e}")
    
    def _get_config_path(self):
        """Get the path to the configuration file."""
        try:
            # First try to use the user's home directory
            user_home = os.path.expanduser("~")
            app_config_dir = os.path.join(user_home, ".lt32pro_config")
            
            # Test if we can write to this directory
            if not os.path.exists(app_config_dir):
                try:
                    os.makedirs(app_config_dir, exist_ok=True)
                    # Test write access by creating and removing a test file
                    test_file = os.path.join(app_config_dir, "test_write.tmp")
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    return os.path.join(app_config_dir, self.CONFIG_FILE)
                except (PermissionError, OSError):
                    # If we can't write to the home directory, fall back to the application directory
                    print("Cannot write to home directory, falling back to application directory")
            else:
                # Directory exists, test if we can write to it
                try:
                    test_file = os.path.join(app_config_dir, "test_write.tmp")
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    return os.path.join(app_config_dir, self.CONFIG_FILE)
                except (PermissionError, OSError):
                    print("Cannot write to home directory, falling back to application directory")
            
            # Fall back to the application directory
            base_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
            return os.path.join(base_dir, self.CONFIG_FILE)
            
        except Exception as e:
            print(f"Error determining config path: {e}")
            # Last resort: use current directory
            return self.CONFIG_FILE