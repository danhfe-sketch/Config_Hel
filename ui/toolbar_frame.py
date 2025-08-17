import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import webbrowser
import os
import subprocess
import platform
import json
from ui.custom_dialogs import show_info, show_error, show_warning, ask_yes_no

class ToolbarFrame(ctk.CTkFrame):
    """
    Toolbar component providing access to configuration profiles, language switching,
    help resources, restore defaults, and personalization options.
    """
    
    def __init__(self, master, i18n, config_service, theme_service, profile_manager=None):
        super().__init__(master)
        self.i18n = i18n
        self.config_service = config_service
        self.theme_service = theme_service
        self.profile_manager = profile_manager
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
                self.i18n.get("load_profile", "Load Profile"),
                self.i18n.get("load_from_device", "Load from Device"),
                self.i18n.get("load_profile_to_device", "Load Profile to Device")
            ],
            command=self._on_profile_action,
            width=140,
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
            "pt": "Português",
            "en": "English",
            "es": "Español"
        }
        # Fixed dictionary definition
        language_display_map = {
            "pt": "Português",
            "en": "English",
            "es": "Español"
        }
        # Set language dropdown to current language
        current_language = self.i18n.get_current_language()
        display_language = language_display_map.get(current_language, "Português")
        self.language_dropdown.set(display_language)
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
                # Correctly call the profile manager to save the UI state
                self._save_profile_from_ui()
            elif choice == self.i18n.get("load_profile", "Load Profile"):
                self._load_profile_to_ui()
            elif choice == self.i18n.get("load_from_device", "Load from Device"):
                self._load_from_device_to_profile()
            elif choice == self.i18n.get("load_profile_to_device", "Load Profile to Device"):
                self._load_profile_to_device()
            
            # Reset dropdown to default text
            self.profiles_dropdown.set(self.i18n.get("profiles", "Profiles"))
            
        except Exception as e:
            error_msg = f"Profile operation failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            show_error(self.app, "Profile Error", error_msg)
    
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
            show_error(self.app, "Language Error", error_msg)
    
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
            show_error(self.app, "Help Error", error_msg)
    
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
        
        show_info(self.app, "Driver Installation", driver_info.strip())
        
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
                show_info(self.app, "Manual", manual_info.strip())
                
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message("Manual file not found - info dialog shown.\n")
        
        except Exception as e:
            error_msg = f"Failed to open manual: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            show_error(self.app, "Manual Error", error_msg)
    
    def _on_restore_defaults(self):
        """Handle restore defaults button click."""
        try:
            # Show confirmation dialog
            result = ask_yes_no(
                self.app,
                "Restore Defaults",
                "This will reset all UI fields to their default values.\n\n"
                "This action will not affect device settings.\n\n"
                "Are you sure you want to continue?"
            )
            
            if result:
                # Reset UI fields to defaults
                self._reset_ui_to_defaults()
                
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message("UI fields restored to default values.\n")
                
                show_info(self.app, "Restore Complete", "UI fields have been restored to default values.")
        
        except Exception as e:
            error_msg = f"Restore defaults failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            show_error(self.app, "Restore Error", error_msg)
    
    def _reset_ui_to_defaults(self):
        """Reset all UI fields to their default values."""
        try:
            # Reset parameters frame fields
            if hasattr(self.app, 'params_frame'):
                params_frame = self.app.params_frame
                
                # Reset APN fields
                if hasattr(params_frame, 'apn_widgets') and 'apn' in params_frame.apn_widgets:
                    params_frame.apn_widgets['apn'].delete(0, "end")
                    params_frame.apn_widgets['apn'].insert(0, "internet.provider.com")
                
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
            show_error(self.app, "Personalization Error", error_msg)
    
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
            show_error(self.app, "Theme Error", error_msg)
    
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
                self.i18n.get("load_profile", "Load Profile"),
                self.i18n.get("load_from_device", "Load from Device"),
                self.i18n.get("load_profile_to_device", "Load Profile to Device")
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
    
    def _load_from_device_to_profile(self):
        """Load configuration from device and save to profile file."""
        try:
            # Check if ProfileManager is available
            if not hasattr(self.app, 'profile_manager'):
                show_error(
                    self.app,
                    "Profile Manager Error",
                    "Profile manager is not available. Please ensure the application is properly initialized."
                )
                return
            
            # Show file save dialog
            from tkinter import filedialog
            
            profile_path = filedialog.asksaveasfilename(
                title=self.i18n.get("save_device_profile", "Save Device Configuration Profile"),
                defaultextension=".json",
                filetypes=[
                    ("JSON Profile Files", "*.json"),
                    ("All Files", "*.*")
                ]
            )
            
            if not profile_path:
                return  # User canceled
            
            # Show confirmation dialog
            result = ask_yes_no(
                self.app,
                self.i18n.get("load_from_device", "Load from Device"),
                self.i18n.get("load_from_device_confirmation", "This will read the current device configuration and save it to:\n\n{profile_path}\n\nThe device must be connected and responding.\n\nContinue?").format(profile_path=profile_path)
            )
            
            if not result:
                return
            
            # Run the async operation in a separate thread
            import threading
            thread = threading.Thread(target=self._load_from_device_to_profile_worker, args=(profile_path,))
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            error_msg = f"Load from device failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            show_error(self.app, "Load from Device Error", error_msg)
    
    def _load_from_device_to_profile_worker(self, profile_path):
        """Worker method to load from device and save to profile file."""
        try:
            # Use the ConfigurationReaderService directly (same approach as check configuration)
            # This is much faster and more reliable than using the profile manager
            
            # Check if serial service and configuration reader are available
            if not hasattr(self.app, 'serial_service') or not self.app.serial_service.is_connected:
                error_result = ProfileOperationResult(
                    operation_type=OperationType.LOAD_FROM_DEVICE,
                    success=False
                )
                error_result.add_error("Device is not connected")
                self.app.after(0, self._handle_load_from_device_completion, error_result)
                return
                
            serial_service = self.app.serial_service
            if serial_service.configuration_reader is None:
                serial_service.initialize_configuration_reader()
                
            if serial_service.configuration_reader is None:
                error_result = ProfileOperationResult(
                    operation_type=OperationType.LOAD_FROM_DEVICE,
                    success=False
                )
                error_result.add_error("Configuration reader service not available")
                self.app.after(0, self._handle_load_from_device_completion, error_result)
                return
            
            # Define completion callback to handle the results
            def on_completion(result, error_message):
                try:
                    if result.success:
                        # Create a profile from the read parameters
                        from models.universal_profile import UniversalProfile, ProfileMetadata, ParameterValue
                        from datetime import datetime
                        
                        # Create metadata
                        metadata = ProfileMetadata(
                            parameter_spec_version="1.0",
                            created_by="LT32 PRO Configurator - Load from Device",
                            device_model="LT32 PRO"
                        )
                        
                        # Convert read parameters to ParameterValue objects
                        parameter_values = {}
                        successful_reads = 0
                        
                        for param_result in result.parameters_read:
                            if param_result.success and param_result.value is not None:
                                # Get the section mapping for this parameter
                                parameter_mapping = serial_service.configuration_reader._get_parameter_section_mapping()
                                section_info = parameter_mapping.get(param_result.parameter_name)
                                
                                if section_info:
                                    section_name = section_info['section']
                                    param_name = section_info['parameter']
                                    full_param_name = f"{section_name}.{param_name}"
                                else:
                                    # Fallback to original parameter name
                                    full_param_name = param_result.parameter_name
                                
                                parameter_values[full_param_name] = ParameterValue(
                                    value=param_result.value,
                                    source="device"
                                )
                                successful_reads += 1
                        
                        if successful_reads > 0:
                            # Create the profile
                            now = datetime.now()
                            profile = UniversalProfile(
                                name=f"Device Configuration {now.strftime('%Y-%m-%d %H:%M:%S')}",
                                version="1.0",
                                created_at=now,
                                modified_at=now,
                                metadata=metadata,
                                parameters=parameter_values
                            )
                            
                            # Save the profile to file
                            try:
                                import json
                                profile_data = profile.to_dict(for_save=True)
                                
                                with open(profile_path, 'w', encoding='utf-8') as f:
                                    json.dump(profile_data, f, indent=2, ensure_ascii=False)
                                
                                # Import required classes
                                from models.operation_result import ProfileOperationResult, OperationType
                                
                                # Create a success result
                                save_result = ProfileOperationResult(
                                    operation_type=OperationType.LOAD_FROM_DEVICE,
                                    success=True
                                )
                                save_result.profile = profile
                                save_result.add_detail("parameters_read", successful_reads)
                                save_result.add_detail("file_path", profile_path)
                                
                                # Handle completion on the main thread
                                self.app.after(0, self._handle_load_from_device_completion, save_result)
                                
                            except Exception as save_error:
                                # Import required classes
                                from models.operation_result import ProfileOperationResult, OperationType
                                
                                error_result = ProfileOperationResult(
                                    operation_type=OperationType.LOAD_FROM_DEVICE,
                                    success=False
                                )
                                error_result.add_error(f"Failed to save profile to file: {str(save_error)}")
                                self.app.after(0, self._handle_load_from_device_completion, error_result)
                        else:
                            # Import required classes
                            from models.operation_result import ProfileOperationResult, OperationType
                            
                            error_result = ProfileOperationResult(
                                operation_type=OperationType.LOAD_FROM_DEVICE,
                                success=False
                            )
                            error_result.add_error("No parameters could be read from device")
                            self.app.after(0, self._handle_load_from_device_completion, error_result)
                    else:
                        # Import required classes
                        from models.operation_result import ProfileOperationResult, OperationType
                        
                        error_result = ProfileOperationResult(
                            operation_type=OperationType.LOAD_FROM_DEVICE,
                            success=False
                        )
                        error_msg = error_message or "Configuration reading failed"
                        error_result.add_error(error_msg)
                        self.app.after(0, self._handle_load_from_device_completion, error_result)
                        
                except Exception as e:
                    # Import required classes
                    from models.operation_result import ProfileOperationResult, OperationType
                    
                    error_result = ProfileOperationResult(
                        operation_type=OperationType.LOAD_FROM_DEVICE,
                        success=False
                    )
                    error_result.add_error(f"Error processing configuration reading results: {str(e)}")
                    self.app.after(0, self._handle_load_from_device_completion, error_result)
            
            # Start configuration reading with progress indication (same as check_device_configuration)
            serial_service.configuration_reader.read_all_configurations(
                completion_callback=on_completion,
                show_progress_dialog=True
            )
            
        except Exception as e:
            # Handle unexpected errors
            from models.operation_result import ProfileOperationResult, OperationType
            error_result = ProfileOperationResult(
                operation_type=OperationType.LOAD_FROM_DEVICE,
                success=False
            )
            error_result.add_error(str(e))
            self.app.after(0, self._handle_load_from_device_completion, error_result)

    def _handle_load_from_device_completion(self, result):
        """Handle the completion of loading from device, ensuring UI updates are on the main thread."""
        try:
            if result.success:
                # Show simple success message without profile details
                success_msg = self.i18n.get("load_from_device_success_simple", "Configuração do dispositivo carregada com sucesso!")

                # Localized title
                title = self.i18n.get("load_from_device", "Load from Device")
                show_info(self.app, title, success_msg)

                # Note: UI is already updated by ConfigurationReaderService.read_all_configurations()
                # No need to call _update_ui_from_device_configuration again as it would duplicate the process
                # The configuration reading service handles both parameter reading and UI updates
                
                # Log success
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message(f"Device configuration loaded to profile successfully\n")
            else:
                # Show error message
                error_msg = "Failed to load device configuration:\n\n"
                if hasattr(result, 'errors') and result.errors:
                    error_msg += "\n".join(result.errors)
                else:
                    error_msg += "Unknown error occurred"
                error_title = self.i18n.get("operation_failed", "Operation failed")
                show_error(self.app, error_title, error_msg)
                
                # Log error
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    log_msg = "ERROR: Device configuration load failed"
                    if result.errors:
                        log_msg += f": {result.errors[0]}"
                    self.app.log_frame.log_message(f"{log_msg}\n")
        
        except Exception as e:
            print(f"Error in completion callback: {e}")
    
    def _load_profile_to_device(self):
        """Load configuration from profile file and deploy to device."""
        try:
            # Check if ProfileManager is available
            if not hasattr(self.app, 'profile_manager'):
                show_error(
                    self.app,
                    "Profile Manager Error",
                    "Profile manager is not available. Please ensure the application is properly initialized."
                )
                return
            
            # Show file open dialog
            from tkinter import filedialog
            
            profile_path = filedialog.askopenfilename(
                title=self.i18n.get("load_profile_to_device", "Load Profile to Device"),
                filetypes=[
                    ("JSON Profile Files", "*.json"),
                    ("All Files", "*.*")
                ]
            )
            
            if not profile_path:
                return  # User canceled
            
            # Show confirmation dialog
            result = ask_yes_no(
                self.app,
                "Load Profile to Device",
                f"This will load the profile from:\n\n{profile_path}\n\n"
                "and deploy it to the device.\n\n"
                "Continue?"
            )
            
            if not result:
                return
            
            # Run the async operation in a separate thread
            import threading
            thread = threading.Thread(target=self._load_profile_to_device_worker, args=(profile_path,))
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            error_msg = f"Load profile to device failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            show_error(self.app, "Load Profile to Device Error", error_msg)
    
    def _load_profile_to_device_worker(self, profile_path):
        """Worker method to load profile from file and deploy to device."""
        try:
            import asyncio
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Load profile from file
            load_result = loop.run_until_complete(self.app.profile_manager.load_from_file(profile_path))
            
            if not load_result.success:
                # Handle load failure
                self.app.after(0, self._handle_load_to_device_completion, load_result)
                return
            
            # Mark all parameters as modified so they will be written to device
            # This is necessary because save_to_device only writes modified parameters
            if hasattr(self.app.profile_manager, '_current_profile') and self.app.profile_manager._current_profile:
                for param_name, param_value in self.app.profile_manager._current_profile.parameters.items():
                    param_value.is_modified = True
                    param_value.source = "user"  # Mark as user-initiated to ensure deployment
            
            # Save the loaded profile to device
            save_result = loop.run_until_complete(self.app.profile_manager.save_to_device())
            
            # Add profile path to result details for display purposes
            if save_result.success:
                save_result.add_detail('profile_path', profile_path)
            
            # Handle completion on the main thread
            self.app.after(0, self._handle_load_to_device_completion, save_result)
            
        except Exception as e:
            # Handle unexpected errors
            from models.operation_result import ProfileOperationResult, OperationType
            error_result = ProfileOperationResult(
                operation_type=OperationType.SAVE_TO_DEVICE,
                success=False
            )
            error_result.add_error(str(e))
            self.app.after(0, self._handle_load_to_device_completion, error_result)
        finally:
            if 'loop' in locals():
                loop.close()

    def _handle_load_to_device_completion(self, result):
        """Handle the completion of loading to device, ensuring UI updates are on the main thread."""
        try:
            # Get recovery context from ProfileManager if available
            recovery_context = getattr(result, 'recovery_context', {})
            
            if result.success:
                # Check if this was a complete success or partial success
                failed_parameters = result.get_failed_parameters()
                if failed_parameters and len(failed_parameters) > 0:
                    # Partial success - show recovery summary
                    recovery_summary = self.app.profile_manager.create_recovery_summary(recovery_context)
                    
                    # Show partial success dialog with recovery details
                    # TODO: Fix profile_error_handler access - should be imported or accessed through app
                    # user_feedback = profile_error_handler.create_recovery_summary_dialog(recovery_summary)
                    
                    from ui.profile_success_dialog import show_profile_success_dialog
                    success_msg = f"Profile deployment partially successful!\n\n"
                    
                    # Get profile path from details or profile name
                    profile_path = result.details.get('profile_path', '')
                    if not profile_path and result.profile:
                        profile_path = result.profile.name
                    if profile_path:
                        success_msg += f"Profile: {os.path.basename(profile_path)}\n"
                    
                    success_msg += f"Parameters configured: {result.parameters_processed}\n"
                    success_msg += f"Parameters failed: {len(failed_parameters)}\n"
                    success_msg += f"Success rate: {recovery_summary.get('success_rate_percent', 0):.1f}%\n\n"
                    
                    if failed_parameters:
                        success_msg += "Failed parameters:\n"
                        for failed_param in failed_parameters[:5]:  # Show first 5
                            success_msg += f"• {failed_param.parameter_name}\n"
                        if len(failed_parameters) > 5:
                            success_msg += f"... and {len(failed_parameters) - 5} more\n"
                        success_msg += "\nThese parameters may need to be configured manually."
                    
                    show_profile_success_dialog(self.app, "Profile Deployment Partially Complete", success_msg)
                    
                    # Update recovery statistics
                    self.app.profile_manager.update_recovery_statistics(recovery_summary)
                else:
                    # Complete success
                    from ui.profile_success_dialog import show_profile_success_dialog
                    success_msg = f"Profile deployed successfully!\n\n"
                    
                    # Get profile path from details or profile name
                    profile_path = result.details.get('profile_path', '')
                    if not profile_path and result.profile:
                        profile_path = result.profile.name
                    if profile_path:
                        success_msg += f"Profile: {os.path.basename(profile_path)}\n"
                    
                    success_msg += f"Parameters configured: {result.parameters_processed}"
                    
                    show_profile_success_dialog(self.app, "Profile Deployment Complete", success_msg)
                
                # Log success with recovery details
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    profile_path = result.details.get('profile_path', '')
                    if not profile_path and result.profile:
                        profile_path = result.profile.name
                    
                    log_msg = f"Profile deployed to device"
                    if profile_path:
                        log_msg += f": {profile_path}"
                    if failed_parameters:
                        log_msg += f" (with {len(failed_parameters)} failed parameters)"
                    self.app.log_frame.log_message(f"INFO: {log_msg}\n")
            else:
                # Handle deployment failure with comprehensive error recovery
                recovery_summary = self.app.profile_manager.create_recovery_summary(recovery_context)
                
                # Create detailed error report
                # TODO: Fix profile_error_handler access - should be imported or accessed through app
                # error_report = profile_error_handler.create_error_report(
                #     ProfileOperationType.DEPLOY_PROFILE,
                #     result.errors if result.errors else []
                # )
                
                # Show recovery summary dialog for failed operations
                if recovery_summary.get('partial_success', False):
                    # Some parameters were successful despite overall failure
                    # TODO: Fix profile_error_handler access - should be imported or accessed through app
                    # user_feedback = profile_error_handler.create_recovery_summary_dialog(recovery_summary)
                    
                    from ui.profile_error_dialog import show_profile_error_dialog
                    error_msg = f"Profile deployment failed but some parameters were configured:\n\n"
                    error_msg += f"Successful parameters: {recovery_summary.get('successful_parameters', 0)}\n"
                    error_msg += f"Failed parameters: {recovery_summary.get('failed_parameters', 0)}\n"
                    error_msg += f"Success rate: {recovery_summary.get('success_rate_percent', 0):.1f}%\n\n"
                    error_msg += f"Primary error: {result.errors[0] if result.errors else 'Unknown error'}\n\n"
                    error_msg += "Check the log for detailed recovery information."
                    
                    show_profile_error_dialog(self.app, "Profile Deployment Partially Failed", error_msg)
                else:
                    # Complete failure - check error type for appropriate dialog
                    if result.details and result.details.get('error_code') in ['DEVICE_NOT_CONNECTED', 'NO_SERIAL_SERVICE']:
                        # Show connection error dialog
                        from ui.profile_connection_error_dialog import show_profile_connection_error_dialog
                        error_msg = f"Failed to deploy profile to device:\n\n{result.errors[0] if result.errors else 'Unknown error'}"
                        show_profile_connection_error_dialog(self.app, "Connection Error", error_msg)
                    else:
                        # Show general error dialog with recovery information
                        from ui.profile_error_dialog import show_profile_error_dialog
                        error_msg = f"Failed to deploy profile to device:\n\n{result.errors[0] if result.errors else 'Unknown error'}"
                        
                        if recovery_summary.get('recovery_actions', 0) > 0:
                            error_msg += f"\n\nRecovery attempts made: {recovery_summary.get('recovery_actions', 0)}"
                            error_msg += "\nCheck the log for detailed recovery information."
                        
                        show_profile_error_dialog(self.app, "Profile Deployment Failed", error_msg)
                # Update recovery statistics
                self.app.profile_manager.update_recovery_statistics(recovery_summary)
                
                # Log error with recovery context
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    log_msg = f"Profile deployment failed: {result.errors[0] if result.errors else 'Unknown error'}"
                    if recovery_summary.get('recovery_actions', 0) > 0:
                        log_msg += f" (after {recovery_summary.get('recovery_actions', 0)} recovery attempts)"
                    self.app.log_frame.log_message(f"ERROR: {log_msg}\n")

        except Exception as e:
            # Handle callback errors gracefully
            error_msg = f"Error in completion callback: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            print(error_msg)
    
    def _load_profile_to_ui(self):
        """Load configuration from profile file and populate UI fields."""
        try:
            # Check if ProfileManager is available
            if not hasattr(self.app, 'profile_manager'):
                show_error(
                    self.app,
                    "Profile Manager Error",
                    "Profile manager is not available. Please ensure the application is properly initialized."
                )
                return
            
            # Show file open dialog
            from tkinter import filedialog
            profile_path = filedialog.askopenfilename(
                title=self.i18n.get("load_profile", "Load Profile"),
                filetypes=[
                    ("JSON Profile Files", "*.json"),
                    ("All Files", "*.*")
                ]
            )
            
            if not profile_path:
                return  # User canceled
            
            # Run the async operation in a separate thread
            import threading
            thread = threading.Thread(target=self._load_profile_to_ui_worker, args=(profile_path,))
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            error_msg = f"Load profile to UI failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            show_error(self.app, "Load Profile to UI Error", error_msg)
    
    def _load_profile_to_ui_worker(self, profile_path):
        """Worker method to load profile from file and populate UI fields."""
        try:
            import asyncio
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Load profile from file
            load_result = loop.run_until_complete(self.app.profile_manager.load_from_file(profile_path))
            
            if not load_result.success:
                # Handle load failure
                self.app.after(0, self._handle_load_profile_to_ui_completion, load_result)
                return
            
            # Populate UI fields from the loaded profile
            ui_field_values = {}
            populate_result = self.app.profile_manager.populate_ui_fields(ui_field_values)
            
            # Update UI with the field values
            self.app.after(0, self._update_ui_with_values, ui_field_values, populate_result)
            
        except Exception as e:
            # Handle unexpected errors
            from models.operation_result import ProfileOperationResult, OperationType
            error_result = ProfileOperationResult(
                operation_type=OperationType.LOAD_FROM_FILE,
                success=False
            )
            error_result.add_error(str(e))
            self.app.after(0, self._handle_load_profile_to_ui_completion, error_result)
        finally:
            if 'loop' in locals():
                loop.close()
    
    def _update_ui_with_values(self, ui_field_values, populate_result):
        """Update UI fields with values from profile."""
        try:
            # Update UI fields with the values
            if hasattr(self.app, 'params_frame'):
                self.app.params_frame.update_fields_from_dict(ui_field_values)
            
            # Log success
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message("INFO: Profile loaded to UI successfully via toolbar\n")
        except Exception as e:
            error_msg = f"Failed to update UI with profile values: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            show_error(self.app, "Load Profile to UI Error", error_msg)
    
    def _handle_load_profile_to_ui_completion(self, result):
        """Handle the completion of loading profile to UI."""
        try:
            if result.success:
                # Show success message
                success_msg = "Profile loaded to UI successfully!"
                show_info(self.app, "Load Profile to UI", success_msg)
                
                # Log success
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message("INFO: Profile loaded to UI successfully via toolbar\n")
            else:
                # Show error message
                error_msg = "Failed to load profile to UI:\n\n"
                if hasattr(result, 'errors') and result.errors:
                    error_msg += "\n".join(result.errors)
                else:
                    error_msg += "Unknown error occurred"
                show_error(self.app, "Load Profile to UI Failed", error_msg)
                
                # Log error
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    log_msg = "ERROR: Profile load to UI failed"
                    if result.errors:
                        log_msg += f": {result.errors[0]}"
                    self.app.log_frame.log_message(f"{log_msg}\n")
        
        except Exception as e:
            print(f"Error in completion callback: {e}")
    
    def _save_profile_from_ui(self):
        """Save the current UI state to a profile file."""
        try:
            # Check if ProfileManager is available
            if not hasattr(self.app, 'profile_manager'):
                show_error(
                    self.app,
                    "Profile Manager Error",
                    "Profile manager is not available. Please ensure the application is properly initialized."
                )
                return
            
            # Show file save dialog
            from tkinter import filedialog
            profile_path = filedialog.asksaveasfilename(
                title=self.i18n.get("save_profile", "Save Profile"),
                defaultextension=".json",
                filetypes=[
                    ("JSON Profile Files", "*.json"),
                    ("All Files", "*.*")
                ]
            )
            
            if not profile_path:
                return  # User canceled
            
            # Run the async operation in a separate thread
            import threading
            thread = threading.Thread(target=self._save_profile_from_ui_worker, args=(profile_path,))
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            error_msg = f"Save profile from UI failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            show_error(self.app, "Save Profile Error", error_msg)
    
    def _save_profile_from_ui_worker(self, profile_path):
        """Worker method to save profile from UI."""
        try:
            import asyncio
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Extract UI field values
            ui_field_values = {}
            if hasattr(self.app, 'params_frame'):
                # Get values from UI fields
                ui_field_values = self.app.params_frame.get_all_field_values()
            
            # Extract values using profile manager
            extract_result = self.app.profile_manager.extract_ui_field_values(ui_field_values)
            
            if not extract_result.is_valid:
                # Handle extraction failure
                from models.operation_result import OperationType
                error_result = ProfileOperationResult(
                    operation_type=OperationType.SAVE_TO_FILE,
                    success=False
                )
                error_result.add_error("Failed to extract UI field values: " + "; ".join(extract_result.errors))
                self.app.after(0, self._handle_save_profile_completion, error_result)
                return
            
            # Save the profile to file
            save_result = loop.run_until_complete(self.app.profile_manager.save_to_file(profile_path))
            
            # Handle completion on the main thread
            self.app.after(0, self._handle_save_profile_completion, save_result)
            
        except Exception as e:
            # Handle unexpected errors
            from models.operation_result import ProfileOperationResult, OperationType
            error_result = ProfileOperationResult(
                operation_type=OperationType.SAVE_TO_FILE,
                success=False
            )
            error_result.add_error(str(e))
            self.app.after(0, self._handle_save_profile_completion, error_result)
        finally:
            if 'loop' in locals():
                loop.close()
    
    def _handle_save_profile_completion(self, result):
        """Handle the completion of saving profile from UI."""
        try:
            if result.success:
                # Show success message
                success_msg = "Profile saved successfully!"
                if hasattr(result, 'details') and result.details:
                    if 'file_path' in result.details:
                        success_msg += f"\nProfile saved to: {result.details['file_path']}"
                show_info(self.app, "Save Profile", success_msg)
                
                # Log success
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message("INFO: Profile saved from UI successfully\n")
            else:
                # Show error message
                error_msg = "Failed to save profile:\n\n"
                if hasattr(result, 'errors') and result.errors:
                    error_msg += "\n".join(result.errors)
                else:
                    error_msg += "Unknown error occurred"
                show_error(self.app, "Save Profile Failed", error_msg)
                
                # Log error
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    log_msg = "ERROR: Profile save from UI failed"
                    if result.errors:
                        log_msg += f": {result.errors[0]}"
                    self.app.log_frame.log_message(f"{log_msg}\n")
        
        except Exception as e:
            print(f"Error in completion callback: {e}")
    
    def _create_progress_dialog(self, title, initial_message):
        """Create a progress dialog for long-running operations."""
        try:
            import tkinter as tk
            from tkinter import ttk
            
            # Create progress window
            progress_window = tk.Toplevel(self.app)
            progress_window.title(title)
            progress_window.geometry("400x150")
            progress_window.resizable(False, False)
            progress_window.transient(self.app)
            progress_window.grab_set()
            
            # Center the window
            progress_window.update_idletasks()
            x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
            y = (progress_window.winfo_screenheight() // 2) - (150 // 2)
            progress_window.geometry(f"400x150+{x}+{y}")
            
            # Create progress elements
            frame = tk.Frame(progress_window, padx=20, pady=20)
            frame.pack(fill="both", expand=True)
            
            # Status label
            status_label = tk.Label(frame, text=initial_message, wraplength=360)
            status_label.pack(pady=(0, 10))
            
            # Progress bar
            progress_bar = ttk.Progressbar(frame, mode='determinate', length=360)
            progress_bar.pack(pady=(0, 10))
            
            # Percentage label
            percent_label = tk.Label(frame, text="0%")
            percent_label.pack()
            
            # Add methods to update progress
            def update_progress(percentage, status_text):
                try:
                    if progress_window.winfo_exists():
                        progress_bar['value'] = percentage
                        percent_label.config(text=f"{percentage:.1f}%")
                        status_label.config(text=status_text)
                        progress_window.update()
                except:
                    pass
            
            progress_window.update_progress = update_progress
            
            # Show the dialog
            progress_window.update()
            
            return progress_window
            
        except Exception as e:
            print(f"Error creating progress dialog: {e}")
            return None
    
    def _load_profile_to_device_worker(self, profile_path):
        """Worker method to load profile from file and deploy to device."""
        try:
            import asyncio
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Load profile from file
            load_result = loop.run_until_complete(self.app.profile_manager.load_from_file(profile_path))
            
            if not load_result.success:
                self.app.after(0, self._handle_profile_operation_completion, load_result)
                return
            
            # Deploy profile to device
            deploy_result = loop.run_until_complete(self.app.profile_manager.save_to_device())
            
            # Handle completion on the main thread
            self.app.after(0, self._handle_profile_operation_completion, deploy_result)
            
        except Exception as e:
            from models.operation_result import ProfileOperationResult, OperationType
            error_result = ProfileOperationResult(
                operation_type=OperationType.SAVE_TO_DEVICE,
                success=False
            )
            error_result.add_error(str(e))
            self.app.after(0, self._handle_profile_operation_completion, error_result)
        finally:
            if 'loop' in locals():
                loop.close()
    
    def _save_profile_from_ui(self):
        """Save current UI values to a profile file."""
        try:
            # Check if we have access to the parameters frame
            if not hasattr(self.app, 'params_frame'):
                show_error(
                    self.app,
                    "Save Profile Error",
                    "Parameters frame is not available. Cannot save profile."
                )
                return
            
            # Show file save dialog
            from tkinter import filedialog
            
            profile_path = filedialog.asksaveasfilename(
                title=self.i18n.get("save_profile", "Save Profile"),
                defaultextension=".json",
                filetypes=[
                    ("JSON Profile Files", "*.json"),
                    ("All Files", "*.*")
                ]
            )
            
            if not profile_path:
                return  # User canceled
            
            # Extract values from UI
            try:
                # Use the extract_validated_field_values method from ParametersFrame
                field_values, validation_result = self.app.params_frame.extract_validated_field_values()
                
                if not validation_result.is_valid:
                    # Show validation errors
                    error_msg = "Cannot save profile due to validation errors:\n\n"
                    error_msg += "\n".join(validation_result.errors)
                    show_error(self.app, "Validation Error", error_msg)
                    return
                
                # Create a profile from the UI values
                from models.universal_profile import UniversalProfile, ProfileMetadata, ParameterValue
                from datetime import datetime
                
                # Create metadata
                metadata = ProfileMetadata(
                    parameter_spec_version="1.0",
                    created_by="LT32 PRO Configurator",
                    device_model="LT32 PRO"
                )
                
                # Convert field values to ParameterValue objects
                parameter_values = {}
                for param_name, value in field_values.items():
                    parameter_values[param_name] = ParameterValue(
                        value=value,
                        source="user"
                    )
                
                now = datetime.now()
                profile = UniversalProfile(
                    name=f"UI_Profile_{now.strftime('%Y%m%d_%H%M%S')}",
                    version="1.0",
                    created_at=now,
                    modified_at=now,
                    metadata=metadata,
                    parameters=parameter_values
                )
                
                # Save the profile to file using the profile's to_dict method
                import json
                profile_data = profile.to_dict()
                
                with open(profile_path, 'w', encoding='utf-8') as f:
                    json.dump(profile_data, f, indent=2, ensure_ascii=False)
                
                # Show success message
                show_info(
                    self.app,
                    "Profile Saved",
                    f"Profile successfully saved to:\n{profile_path}"
                )
                
                # Log success
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message(f"Profile saved successfully to: {profile_path}\n")
                
            except Exception as extract_error:
                error_msg = f"Failed to extract UI values: {str(extract_error)}"
                show_error(self.app, "Save Profile Error", error_msg)
                
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
                
        except Exception as e:
            error_msg = f"Save profile failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            show_error(self.app, "Save Profile Error", error_msg)
    
    def _load_profile_to_ui(self):
        """Load profile from file and populate UI."""
        try:
            # Show file open dialog
            from tkinter import filedialog
            
            profile_path = filedialog.askopenfilename(
                title=self.i18n.get("load_profile", "Load Profile"),
                filetypes=[
                    ("JSON Profile Files", "*.json"),
                    ("All Files", "*.*")
                ]
            )
            
            if not profile_path:
                return  # User canceled
            
            # Load profile from file
            try:
                import json
                with open(profile_path, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                
                # Create UniversalProfile object
                from models.universal_profile import UniversalProfile
                from datetime import datetime
                
                # Use the from_dict method to properly reconstruct the profile
                profile = UniversalProfile.from_dict(profile_data)
                
                # Populate UI with profile values
                if hasattr(self.app, 'params_frame'):
                    populate_result = self.app.params_frame.populate_ui_from_profile(profile)
                    
                    if populate_result.is_valid:
                        show_info(
                            self.app,
                            "Profile Loaded",
                            f"Profile successfully loaded from:\n{profile_path}"
                        )
                        
                        if hasattr(self.app, 'log_frame') and self.app.log_frame:
                            self.app.log_frame.log_message(f"Profile loaded successfully from: {profile_path}\n")
                    else:
                        # Show warnings if there were issues
                        warning_msg = "Profile loaded with warnings:\n\n"
                        warning_msg += "\n".join(populate_result.errors)
                        show_warning(self.app, "Profile Load Warning", warning_msg)
                else:
                    show_error(
                        self.app,
                        "Load Profile Error",
                        "Parameters frame is not available. Cannot load profile."
                    )
                
            except Exception as load_error:
                error_msg = f"Failed to load profile file: {str(load_error)}"
                show_error(self.app, "Load Profile Error", error_msg)
                
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
                
        except Exception as e:
            error_msg = f"Load profile failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            show_error(self.app, "Load Profile Error", error_msg)
    
    def _handle_profile_operation_completion(self, result):
        """Handle the completion of profile operations."""
        try:
            if result.success:
                show_info(
                    self.app,
                    "Operation Successful",
                    "Profile operation completed successfully."
                )
                
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message("Profile operation completed successfully\n")
            else:
                error_msg = "Profile operation failed:\n\n"
                if hasattr(result, 'errors') and result.errors:
                    error_msg += "\n".join(result.errors)
                else:
                    error_msg += "Unknown error occurred"
                
                show_error(self.app, "Operation Failed", error_msg)
                
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message(f"ERROR: Profile operation failed\n")
        
        except Exception as e:
            print(f"Error in profile operation completion callback: {e}")

    def _update_ui_with_values(self, ui_field_values, populate_result):
        """Update UI with loaded values."""
        try:
            # Check if we have access to the parameters frame
            if not hasattr(self.app, 'parameters_frame') or not self.app.parameters_frame:
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message("WARNING: Parameters frame not available for UI update\n")
                return
            
            # Get the current profile from profile manager
            if hasattr(self.app, 'profile_manager') and self.app.profile_manager:
                current_profile = self.app.profile_manager.get_current_profile()
                if current_profile:
                    # Use the parameters frame's populate method
                    populate_result = self.app.parameters_frame.populate_ui_from_profile(current_profile)
                    
                    if populate_result.is_valid:
                        if hasattr(self.app, 'log_frame') and self.app.log_frame:
                            self.app.log_frame.log_message("INFO: UI updated successfully with loaded values\n")
                    else:
                        if hasattr(self.app, 'log_frame') and self.app.log_frame:
                            self.app.log_frame.log_message(f"WARNING: UI update completed with warnings: {populate_result.errors}\n")
                else:
                    if hasattr(self.app, 'log_frame') and self.app.log_frame:
                        self.app.log_frame.log_message("WARNING: No current profile available for UI update\n")
            else:
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message("WARNING: Profile manager not available for UI update\n")
                    
        except Exception as e:
            error_msg = f"Error updating UI with values: {e}"
            print(error_msg)
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")

    def _save_profile_from_ui(self):
        """Save current UI values to a profile file."""
        try:
            # Check if we have access to the parameters frame
            if not hasattr(self.app, 'params_frame'):
                show_error(
                    self.app,
                    "Save Profile Error",
                    "Parameters frame is not available. Cannot save profile."
                )
                return
            
            # Show file save dialog
            from tkinter import filedialog
            
            profile_path = filedialog.asksaveasfilename(
                title=self.i18n.get("save_profile", "Save Profile"),
                defaultextension=".json",
                filetypes=[
                    ("JSON Profile Files", "*.json"),
                    ("All Files", "*.*")
                ]
            )
            
            if not profile_path:
                return  # User canceled
            
            # Extract values from UI
            try:
                # Use the extract_validated_field_values method from ParametersFrame
                field_values, validation_result = self.app.params_frame.extract_validated_field_values()
                
                if not validation_result.is_valid:
                    # Show validation errors
                    error_msg = "Cannot save profile due to validation errors:\n\n"
                    error_msg += "\n".join(validation_result.errors)
                    show_error(self.app, "Validation Error", error_msg)
                    return
                
                # Create a profile from the UI values
                from models.universal_profile import UniversalProfile, ProfileMetadata, ParameterValue
                from datetime import datetime
                
                # Create metadata
                metadata = ProfileMetadata(
                    parameter_spec_version="1.0",
                    created_by="LT32 PRO Configurator",
                    device_model="LT32 PRO"
                )
                
                # Convert field values to ParameterValue objects
                parameter_values = {}
                for param_name, value in field_values.items():
                    parameter_values[param_name] = ParameterValue(
                        value=value,
                        source="user"
                    )
                
                now = datetime.now()
                profile = UniversalProfile(
                    name=f"UI_Profile_{now.strftime('%Y%m%d_%H%M%S')}",
                    version="1.0",
                    created_at=now,
                    modified_at=now,
                    metadata=metadata,
                    parameters=parameter_values
                )
                
                # Save the profile to file using the profile's to_dict method
                import json
                profile_data = profile.to_dict()
                
                with open(profile_path, 'w', encoding='utf-8') as f:
                    json.dump(profile_data, f, indent=2, ensure_ascii=False)
                
                # Show success message
                show_info(
                    self.app,
                    "Profile Saved",
                    f"Profile successfully saved to:\n{profile_path}"
                )
                
                # Log success
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message(f"Profile saved successfully to: {profile_path}\n")
                
            except Exception as extract_error:
                error_msg = f"Failed to extract UI values: {str(extract_error)}"
                show_error(self.app, "Save Profile Error", error_msg)
                
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
                
        except Exception as e:
            error_msg = f"Save profile failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            show_error(self.app, "Save Profile Error", error_msg)
    
    def _load_profile_to_ui(self):
        """Load profile from file and populate UI."""
        try:
            # Show file open dialog
            from tkinter import filedialog
            
            profile_path = filedialog.askopenfilename(
                title=self.i18n.get("load_profile", "Load Profile"),
                filetypes=[
                    ("JSON Profile Files", "*.json"),
                    ("All Files", "*.*")
                ]
            )
            
            if not profile_path:
                return  # User canceled
            
            # Load profile from file
            try:
                import json
                with open(profile_path, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                
                # Create UniversalProfile object
                from models.universal_profile import UniversalProfile
                from datetime import datetime
                
                # Use the from_dict method to properly reconstruct the profile
                profile = UniversalProfile.from_dict(profile_data)
                
                # Populate UI with profile values
                if hasattr(self.app, 'params_frame'):
                    populate_result = self.app.params_frame.populate_ui_from_profile(profile)
                    
                    if populate_result.is_valid:
                        show_info(
                            self.app,
                            "Profile Loaded",
                            f"Profile successfully loaded from:\n{profile_path}"
                        )
                        
                        if hasattr(self.app, 'log_frame') and self.app.log_frame:
                            self.app.log_frame.log_message(f"Profile loaded successfully from: {profile_path}\n")
                    else:
                        # Show warnings if there were issues
                        warning_msg = "Profile loaded with warnings:\n\n"
                        warning_msg += "\n".join(populate_result.errors)
                        show_warning(self.app, "Profile Load Warning", warning_msg)
                else:
                    show_error(
                        self.app,
                        "Load Profile Error",
                        "Parameters frame is not available. Cannot load profile."
                    )
                
            except Exception as load_error:
                error_msg = f"Failed to load profile file: {str(load_error)}"
                show_error(self.app, "Load Profile Error", error_msg)
                
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
                
        except Exception as e:
            error_msg = f"Load profile failed: {str(e)}"
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            show_error(self.app, "Load Profile Error", error_msg)

    def _update_ui_with_loaded_profile(self, profile):
        """Update UI with loaded profile values."""
        try:
            # Check if we have access to the parameters frame
            if not hasattr(self.app, 'parameters_frame') or not self.app.parameters_frame:
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message("WARNING: Parameters frame not available for UI update\n")
                return
            
            # Use the parameters frame's populate method directly
            if profile:
                populate_result = self.app.parameters_frame.populate_ui_from_profile(profile)
                
                if populate_result.is_valid:
                    if hasattr(self.app, 'log_frame') and self.app.log_frame:
                        self.app.log_frame.log_message("INFO: UI updated successfully with loaded values\n")
                else:
                    if hasattr(self.app, 'log_frame') and self.app.log_frame:
                        self.app.log_frame.log_message(f"WARNING: UI update completed with warnings: {populate_result.errors}\n")
            else:
                if hasattr(self.app, 'log_frame') and self.app.log_frame:
                    self.app.log_frame.log_message("WARNING: No profile available for UI update\n")
                    
        except Exception as e:
            error_msg = f"Error updating UI with loaded profile: {e}"
            print(error_msg)
            if hasattr(self.app, 'log_frame') and self.app.log_frame:
                self.app.log_frame.log_message(f"ERROR: {error_msg}\n")