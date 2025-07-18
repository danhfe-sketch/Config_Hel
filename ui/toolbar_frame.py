import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import webbrowser
import os
import subprocess
import platform
import json

class ToolbarFrame(ctk.CTkFrame):
    """
    Toolbar component providing access to configuration profiles, language switching,
    help resources, restore defaults, and personalization options.
    """
    
    def __init__(self, master, i18n, config_service, theme_service):
        super().__init__(master)
        self.i18n = i18n
        self.config_service = config_service
        self.theme_service = theme_service
        self.app = master  # Reference to the main app
        
        self._create_toolbar_elements()
    
    def _create_toolbar_elements(self):
        """Create all toolbar UI elements."""
        # Create a horizontal frame for the toolbar with minimal padding
        toolbar_container = ctk.CTkFrame(self, fg_color="transparent")
        toolbar_container.pack(fill="x", padx=5, pady=(5, 0))
        
        # Left side elements (profiles, language, help)
        left_frame = ctk.CTkFrame(toolbar_container, fg_color="transparent")
        left_frame.pack(side="left", fill="y")
        
        # Configuration Profiles Dropdown
        self.profiles_dropdown = ctk.CTkOptionMenu(
            left_frame,
            values=[
                self.i18n.get("save_profile", "Save Profile"),
                self.i18n.get("load_profile", "Load Profile")
            ],
            command=self._on_profile_action,
            width=120,
            height=28
        )
        self.profiles_dropdown.pack(side="left", padx=5)
        self.profiles_dropdown.set(self.i18n.get("profiles", "Profiles"))
        
        # Language Selector Dropdown
        self.language_dropdown = ctk.CTkOptionMenu(
            left_frame,
            values=[
                "Português",
                "English", 
                "Español"
            ],
            command=self._on_language_change,
            width=100,
            height=28
        )
        self.language_dropdown.pack(side="left", padx=5)
        
        # Set the dropdown to the current language
        language_display_map = {
            "pt_BR": "Português",
            "en_US": "English",
            "es_ES": "Español"
        }
        current_language = self.i18n.get_current_language()
        display_language = language_display_map.get(current_language, "Português")
        self.language_dropdown.set(display_language)
        
        # Help Menu Dropdown
        self.help_dropdown = ctk.CTkOptionMenu(
            left_frame,
            values=[
                self.i18n.get("install_driver", "Install Driver"),
                self.i18n.get("open_manuals", "Open Manuals")
            ],
            command=self._on_help_action,
            width=100,
            height=28
        )
        self.help_dropdown.pack(side="left", padx=5)
        self.help_dropdown.set(self.i18n.get("help", "Help"))
        
        # Right side elements (restore defaults, personalization)
        right_frame = ctk.CTkFrame(toolbar_container, fg_color="transparent")
        right_frame.pack(side="right", fill="y")
        
        # Personalization Button
        self.personalization_button = ctk.CTkButton(
            right_frame,
            text=self.i18n.get("personalization", "Personalization"),
            command=self._on_personalization,
            width=120,
            height=28
        )
        self.personalization_button.pack(side="right", padx=5)
        
        # Restore Defaults Button
        self.restore_button = ctk.CTkButton(
            right_frame,
            text=self.i18n.get("restore_defaults", "Restore Defaults"),
            command=self._on_restore_defaults,
            width=120,
            height=28,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40")
        )
        self.restore_button.pack(side="right", padx=5)
    
    def _on_profile_action(self, choice):
        """Handle configuration profile dropdown actions."""
        try:
            if choice == self.i18n.get("save_profile", "Save Profile"):
                self.config_service.save_profile()
            elif choice == self.i18n.get("load_profile", "Load Profile"):
                self.config_service.load_profile()
            
            # Reset dropdown to default text
            self.profiles_dropdown.set(self.i18n.get("profiles", "Profiles"))
            
        except Exception as e:
            error_msg = f"Profile operation failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            messagebox.showerror("Profile Error", error_msg)
    
    def _on_language_change(self, choice):
        """Handle language selection changes."""
        try:
            # Map display names to language codes
            language_map = {
                "Português": "pt_BR",
                "English": "en_US",
                "Español": "es_ES"
            }
            
            language_code = language_map.get(choice)
            if language_code:
                # Update I18n service
                self.i18n.set_language(language_code)
                
                # Refresh all UI elements immediately
                self._refresh_ui_language()
                
                # Log the language change
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message(f"Language changed to: {choice}\n")
            
        except Exception as e:
            error_msg = f"Language change failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            messagebox.showerror("Language Error", error_msg)
    
    def _on_help_action(self, choice):
        """Handle help menu actions."""
        try:
            if choice == self.i18n.get("install_driver", "Install Driver"):
                self._show_driver_installation_guide()
            elif choice == self.i18n.get("open_manuals", "Open Manuals"):
                self._open_manuals()
            
            # Reset dropdown to default text
            self.help_dropdown.set(self.i18n.get("help", "Help"))
            
        except Exception as e:
            error_msg = f"Help action failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            messagebox.showerror("Help Error", error_msg)
    
    def _show_driver_installation_guide(self):
        """Show driver installation guidance."""
        driver_info = """
Driver Installation Guide:

1. Download the USB-to-Serial driver for your operating system
2. For Windows: Install CH340/CH341 driver
3. For macOS: Install CH34x_Install_V1.5.pkg
4. For Linux: Driver is usually included in kernel

Common driver sources:
- Manufacturer website
- Windows Update
- Device Manager > Update Driver

After installation, restart the application and check available COM ports.
        """
        
        messagebox.showinfo("Driver Installation", driver_info.strip())
        
        if hasattr(self.app, 'log_frame') and self.app.log_frame:
            self.app.log_frame.log_message("Driver installation guide displayed.\n")
    
    def _open_manuals(self):
        """Open equipment manuals."""
        try:
            # Look for PDF manual in the application directory
            manual_files = [
                "Lumini Tracker - LT32 PRO - MANUAL_USUARIO_V.00-032025.pdf",
                "manual.pdf",
                "LT32Pro_Manual.pdf"
            ]
            
            manual_found = False
            for manual_file in manual_files:
                if os.path.exists(manual_file):
                    # Open PDF with default system application
                    if platform.system() == "Windows":
                        os.startfile(manual_file)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", manual_file])
                    else:  # Linux
                        subprocess.run(["xdg-open", manual_file])
                    
                    manual_found = True
                    if hasattr(self.app, 'log_frame') and self.app.log_frame:
                        self.app.log_frame.log_message(f"Manual opened: {manual_file}\n")
                    break
            
            if not manual_found:
                # Fallback: show message with manual information
                manual_info = """
Equipment Manual:

Manual file not found in application directory.

Please check for:
- Lumini Tracker - LT32 PRO - MANUAL_USUARIO_V.00-032025.pdf
- Or download from manufacturer website

For technical support, contact Lumini Tracker support team.
                """
                messagebox.showinfo("Manual", manual_info.strip())
                
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message("Manual file not found - info dialog shown.\n")
        
        except Exception as e:
            error_msg = f"Failed to open manual: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            messagebox.showerror("Manual Error", error_msg)
    
    def _on_restore_defaults(self):
        """Handle restore defaults button click."""
        try:
            # Show confirmation dialog
            result = messagebox.askyesno(
                "Restore Defaults",
                "This will reset all UI fields to their default values.\n\n"
                "This action will not affect device settings.\n\n"
                "Are you sure you want to continue?",
                icon="warning"
            )
            
            if result:
                # Reset UI fields to defaults
                self._reset_ui_to_defaults()
                
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message("UI fields restored to default values.\n")
                
                messagebox.showinfo("Restore Complete", "UI fields have been restored to default values.")
        
        except Exception as e:
            error_msg = f"Restore defaults failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            messagebox.showerror("Restore Error", error_msg)
    
    def _reset_ui_to_defaults(self):
        """Reset all UI fields to their default values."""
        try:
            # Reset parameters frame fields
            if hasattr(self.app, 'params_frame'):
                params_frame = self.app.params_frame
                
                # Reset APN fields
                if hasattr(params_frame, 'apn_server_entry'):
                    params_frame.apn_server_entry.delete(0, "end")
                    params_frame.apn_server_entry.insert(0, "internet.provider.com")
                
                if hasattr(params_frame, 'apn_user_entry'):
                    params_frame.apn_user_entry.delete(0, "end")
                
                if hasattr(params_frame, 'apn_password_entry'):
                    params_frame.apn_password_entry.delete(0, "end")
                
                if hasattr(params_frame, 'trans_mode_var'):
                    params_frame.trans_mode_var.set("TCP")
                
                # Reset other parameter fields as they are implemented
                # This will be extended as more parameters are added
        
        except Exception as e:
            print(f"Error resetting UI fields: {e}")
    
    def _on_personalization(self):
        """Handle personalization button click - open theme selection dialog."""
        try:
            # Create a simple menu with theme options
            theme_menu = tk.Menu(self.app, tearoff=0)
            
            # Add theme options with translations
            theme_translations = {
                "Light": self.i18n.get("light_theme", "Light"),
                "Dark": self.i18n.get("dark_theme", "Dark"),
                "System": self.i18n.get("system_theme", "System")
            }
            
            # Create a function to create theme selection commands with proper closure
            def make_theme_command(theme_name):
                return lambda: self._apply_theme(theme_name)
            
            for theme in self.theme_service.get_available_themes():
                translated_name = theme_translations.get(theme, theme)
                theme_menu.add_command(
                    label=translated_name,
                    command=make_theme_command(theme)
                )
            
            # Get the position of the personalization button
            x = self.personalization_button.winfo_rootx()
            y = self.personalization_button.winfo_rooty() + self.personalization_button.winfo_height()
            
            # Show the menu at the button position
            theme_menu.tk_popup(x, y)
            
        except Exception as e:
            error_msg = f"Personalization failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            messagebox.showerror("Personalization Error", error_msg)
    
    def _apply_theme(self, theme):
        """Apply the selected theme."""
        try:
            # Apply the theme (this will also save the theme preference)
            self.theme_service.set_theme(theme)
            
            # Log the change
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"Theme changed to: {theme}\n")
            
        except Exception as e:
            error_msg = f"Failed to set theme: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            messagebox.showerror("Theme Error", error_msg)
    
    def _get_timestamp(self):
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _refresh_ui_language(self):
        """Refresh all UI elements when language changes."""
        try:
            # Update toolbar elements
            self.update_language_display()
            
            # Update main application title
            self.app.title(self.i18n.get("app_title"))
            
            # Update other UI frames if they have language update methods
            if hasattr(self.app, 'connection_frame') and hasattr(self.app.connection_frame, 'update_language_display'):
                self.app.connection_frame.update_language_display()
            
            if hasattr(self.app, 'params_frame') and hasattr(self.app.params_frame, 'update_language_display'):
                self.app.params_frame.update_language_display()
            
            if hasattr(self.app, 'actions_frame') and hasattr(self.app.actions_frame, 'update_language_display'):
                self.app.actions_frame.update_language_display()
            
            if hasattr(self.app, 'log_frame') and hasattr(self.app.log_frame, 'update_language_display'):
                self.app.log_frame.update_language_display()
            
        except Exception as e:
            print(f"Error refreshing UI language: {e}")
    
    def update_language_display(self):
        """Update toolbar text when language changes."""
        # This method can be called to refresh toolbar text after language changes
        try:
            # Update button text
            self.restore_button.configure(text=self.i18n.get("restore_defaults", "Restore Defaults"))
            self.personalization_button.configure(text=self.i18n.get("personalization", "Personalization"))
            
            # Update dropdown options
            self.profiles_dropdown.configure(values=[
                self.i18n.get("save_profile", "Save Profile"),
                self.i18n.get("load_profile", "Load Profile")
            ])
            self.profiles_dropdown.set(self.i18n.get("profiles", "Profiles"))
            
            self.help_dropdown.configure(values=[
                self.i18n.get("install_driver", "Install Driver"),
                self.i18n.get("open_manuals", "Open Manuals")
            ])
            self.help_dropdown.set(self.i18n.get("help", "Help"))
            
            # Note: The theme menu is recreated when clicked, so its translations 
            # will be updated automatically the next time it's opened
            
        except Exception as e:
            print(f"Error updating toolbar language display: {e}")