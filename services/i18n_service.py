import json
import logging
import os
from utils.helpers import resource_path
logger = logging.getLogger(__name__)
from services.app_config_service import AppConfigService

class I18nService:
    """Handles internationalization and language switching."""

    DEFAULT_LANGUAGE = "pt_BR"
    
    def __init__(self, language=None):
        self.language_map = {}
        self.current_language = None
        
        # Use the centralized app config service
        self.app_config = AppConfigService()
        
        # Try to load saved language preference
        if language is None:
            try:
                saved_language = self.app_config.get_language()
                print(f"Loaded saved language preference: {saved_language}")
                language = saved_language if saved_language else self.DEFAULT_LANGUAGE
            except Exception as e:
                print(f"Error loading language preference: {e}")
                language = self.DEFAULT_LANGUAGE
                
        print(f"Initializing I18nService with language: {language}")
        self.set_language(language)

    def set_language(self, language_code):
        """Loads a new language file from the assets/locales directory."""
        locale_path = resource_path(os.path.join('assets', 'locales', f'{language_code}.json'))
        try:
            with open(locale_path, 'r', encoding='utf-8') as f:
                self.language_map = json.load(f)
                self.current_language = language_code
                print(f"Loaded language: {language_code}")
                
                # Save the language preference
                self.app_config.set_language(language_code)
        except FileNotFoundError:
            print(f"Error: Language file not found for code: {language_code}")
            # Fallback to a default or handle the error appropriately
            if not self.language_map: # if no language is loaded at all
                self.language_map = {"error": "Language file missing"}

    def get(self, key, default_value=''):
        """Returns the translated string for a given key."""
        if key in self.language_map:
            value = self.language_map[key]
        else:
            fallback = default_value or f"_{key}_"
            logger.warning(
                "Missing translation key '%s' for language '%s'. Falling back to '%s'.",
                key,
                self.current_language,
                fallback
            )
            value = fallback
        # If the locale file contains escaped newline sequences (e.g. "\\n")
        # convert them to real newlines so dialogs and labels render correctly.
        try:
            if isinstance(value, str):
                value = value.replace('\\n', '\n').replace('\\r', '\r')
        except Exception:
            # If any unexpected type or issue occurs, fall back to the raw value
            pass
        return value
    
    def get_current_language(self):
        """Returns the current language code."""
        return self.current_language