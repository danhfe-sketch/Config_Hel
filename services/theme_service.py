import json
import os
import customtkinter as ctk
from utils.helpers import resource_path
from services.app_config_service import AppConfigService

class ThemeService:
    """Handles application theme management with persistence."""
    
    THEME_OPTIONS = ["Light", "Dark", "System"]
    
    def __init__(self, app_instance):
        """Initialize the ThemeService with reference to the main app."""
        self.app = app_instance
        self.current_theme = "System"  # Default theme
        
        # Use the centralized app config service
        self.app_config = AppConfigService()
        
        # Log initialization
        print("Theme service initialized")
        if hasattr(self.app, 'log_frame') and self.app.log_frame:
            self.app.log_frame.log_message("Theme service initialized\n")
        
        # Load saved theme preference on initialization
        self.load_saved_theme()
    
    def set_theme(self, theme: str) -> None:
        """
        Set the application theme and apply it immediately.
        
        Args:
            theme (str): Theme name - must be one of THEME_OPTIONS
        """
        if theme not in self.THEME_OPTIONS:
            raise ValueError(f"Invalid theme '{theme}'. Must be one of: {self.THEME_OPTIONS}")
        
        self.current_theme = theme
        
        # Apply theme to CustomTkinter
        ctk.set_appearance_mode(theme)
        
        # Save theme preference for persistence
        self.save_theme_preference(theme)
        
        # Log the theme change
        if hasattr(self.app, 'log_frame') and self.app.log_frame:
            self.app.log_frame.log_message(f"Theme changed to: {theme}\n")
    
    def get_current_theme(self) -> str:
        """
        Get the currently active theme.
        
        Returns:
            str: Current theme name
        """
        return self.current_theme
    
    def get_available_themes(self) -> list:
        """
        Get list of available theme options.
        
        Returns:
            list: Available theme names
        """
        return self.THEME_OPTIONS.copy()
    
    def load_saved_theme(self) -> None:
        """Load theme preference from centralized app config and apply it."""
        try:
            # Get theme from app config service
            saved_theme = self.app_config.get_theme()
            
            # Validate saved theme
            if saved_theme in self.THEME_OPTIONS:
                self.current_theme = saved_theme
                ctk.set_appearance_mode(saved_theme)
            else:
                # Invalid theme in config, use default
                self.current_theme = "System"
                ctk.set_appearance_mode("System")
            
            # Log the loaded theme
            print(f"Loaded theme: {self.current_theme}")
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"Loaded theme: {self.current_theme}\n")
                
        except Exception as e:
            # Error loading config, use default theme
            print(f"Error loading theme config: {e}")
            self.current_theme = "System"
            ctk.set_appearance_mode("System")
    
    def save_theme_preference(self, theme: str) -> None:
        """
        Save theme preference to centralized app config.
        
        Args:
            theme (str): Theme name to save
        """
        try:
            # Save theme using app config service
            self.app_config.set_theme(theme)
            
            # Log the save
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"Theme preference saved: {theme}\n")
                
        except Exception as e:
            error_msg = f"Error saving theme preference: {e}"
            print(error_msg)
            # Log error if log frame is available
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def reset_to_default(self) -> None:
        """Reset theme to default (System) and save preference."""
        self.set_theme("System")
    
    def is_dark_mode_active(self) -> bool:
        """
        Check if dark mode is currently active.
        
        Returns:
            bool: True if dark mode is active, False otherwise
        """
        if self.current_theme == "Dark":
            return True
        elif self.current_theme == "Light":
            return False
        else:  # System theme
            # For system theme, we can check the current appearance mode
            return ctk.get_appearance_mode() == "Dark"