import tkinter as tk
import customtkinter as ctk
import json
import os
from services.i18n_service import I18nService

class LanguageSwitchingTest(ctk.CTk):
    """Test application for verifying language switching and translations."""
    
    def __init__(self):
        super().__init__()
        
        self.title("Language Switching Test")
        self.geometry("800x600")
        
        # Initialize I18n service
        self.i18n = I18nService()
        
        # Create UI
        self.create_ui()
        
    def create_ui(self):
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Language selection
        lang_frame = ctk.CTkFrame(main_frame)
        lang_frame.pack(fill="x", padx=10, pady=10)
        
        lang_label = ctk.CTkLabel(lang_frame, text="Select Language:")
        lang_label.pack(side="left", padx=10)
        
        self.lang_var = tk.StringVar(value="en_US")
        
        # Language radio buttons
        en_radio = ctk.CTkRadioButton(
            lang_frame, 
            text="English", 
            variable=self.lang_var, 
            value="en_US",
            command=self.change_language
        )
        en_radio.pack(side="left", padx=10)
        
        pt_radio = ctk.CTkRadioButton(
            lang_frame, 
            text="Português", 
            variable=self.lang_var, 
            value="pt_BR",
            command=self.change_language
        )
        pt_radio.pack(side="left", padx=10)
        
        es_radio = ctk.CTkRadioButton(
            lang_frame, 
            text="Español", 
            variable=self.lang_var, 
            value="es_ES",
            command=self.change_language
        )
        es_radio.pack(side="left", padx=10)
        
        # Translation test sections
        self.create_test_sections(main_frame)
        
    def create_test_sections(self, parent):
        # Create scrollable frame for test sections
        scroll_frame = ctk.CTkScrollableFrame(parent)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # UI Elements section
        self.create_section(scroll_frame, "UI Elements", [
            "app_title", "connection", "parameters", "actions", 
            "serial_log", "config_profiles", "language", "help",
            "personalization", "theme", "restore_defaults"
        ])
        
        # Connection section
        self.create_section(scroll_frame, "Connection", [
            "connection_quality", "auto_reconnect", "reconnecting",
            "reconnection_attempt", "reconnection_countdown", 
            "reconnection_failed", "reconnection_successful"
        ])
        
        # Error Messages section
        self.create_section(scroll_frame, "Error Messages", [
            "error_connection_port_not_found",
            "error_connection_timeout",
            "error_connection_device_disconnected",
            "error_command_invalid_format",
            "suggested_solutions"
        ])
        
        # Toolbar section
        self.create_section(scroll_frame, "Toolbar", [
            "profiles", "save_profile", "load_profile",
            "install_driver", "open_manuals",
            "light_theme", "dark_theme", "system_theme"
        ])
        
        # Log section
        self.create_section(scroll_frame, "Log", [
            "copy_log", "export_log", "clear_log",
            "log_copied", "log_export_success",
            "log_no_content"
        ])
        
    def create_section(self, parent, title, keys):
        # Create a section with a title and translation keys
        section_frame = ctk.CTkFrame(parent)
        section_frame.pack(fill="x", padx=5, pady=10)
        
        # Section title
        title_label = ctk.CTkLabel(
            section_frame, 
            text=title, 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(anchor="w", padx=10, pady=5)
        
        # Create a grid for key-value pairs
        grid_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=5)
        
        # Add header
        key_header = ctk.CTkLabel(
            grid_frame, 
            text="Translation Key", 
            font=ctk.CTkFont(weight="bold")
        )
        key_header.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        value_header = ctk.CTkLabel(
            grid_frame, 
            text="Translated Value", 
            font=ctk.CTkFont(weight="bold")
        )
        value_header.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Add key-value pairs
        self.translation_labels = {}
        
        for i, key in enumerate(keys, 1):
            # Key label
            key_label = ctk.CTkLabel(grid_frame, text=key)
            key_label.grid(row=i, column=0, padx=5, pady=2, sticky="w")
            
            # Value label (will be updated with translations)
            value_label = ctk.CTkLabel(grid_frame, text="")
            value_label.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            
            # Store reference to value label
            self.translation_labels[key] = value_label
        
        # Update translations for this section
        self.update_section_translations(keys)
    
    def update_section_translations(self, keys):
        # Update translations for all keys in a section
        for key in keys:
            if key in self.translation_labels:
                # Get translation with placeholder values if needed
                translated = self.get_formatted_translation(key)
                self.translation_labels[key].configure(text=translated)
    
    def get_formatted_translation(self, key):
        # Get translation with placeholder values for testing
        if key == "reconnection_attempt":
            return self.i18n.get(key).format(current=2, max=5)
        elif key == "reconnection_countdown":
            return self.i18n.get(key).format(seconds=10)
        elif key == "log_export_success":
            return self.i18n.get(key).format(filename="log_20250717.txt")
        elif key == "error_connection_port_not_found":
            return self.i18n.get(key).format(port="COM3")
        elif key == "error_command_invalid_format":
            return self.i18n.get(key).format(command="AT+INVALID")
        elif key == "language_changed":
            return self.i18n.get(key).format(language=self.lang_var.get())
        else:
            return self.i18n.get(key)
    
    def change_language(self):
        # Change language and update all translations
        language = self.lang_var.get()
        self.i18n.set_language(language)
        
        # Update all sections
        for key in self.translation_labels:
            translated = self.get_formatted_translation(key)
            self.translation_labels[key].configure(text=translated)
        
        # Update window title
        self.title(f"Language Switching Test - {self.i18n.get('app_title')}")

if __name__ == "__main__":
    app = LanguageSwitchingTest()
    app.mainloop()