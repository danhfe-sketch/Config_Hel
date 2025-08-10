import json
import os
import datetime
from tkinter import filedialog
from tkinter import messagebox

class ConfigService:
    """Handles saving and loading of configuration profiles."""
    
    # Default values for parameters
    DEFAULT_VALUES = {
        'apn_server': '',
        'apn_user': '',
        'apn_password': '',
        'transmission_mode': 'TCP',
        'timer_ign_on': '30',
        'timer_ign_off': '300',
        'heartbeat_interval': '1min',
        'vibration': '3',
        'sensitivity': '5',
        'curve_sensor': 'Auto',
        'ignition_type': 'Digital',
        'lock_type': 'PIN',
        'protocol': 'GT06',
        'network_select': 'AUTO',
        'sleep_mode': 'Disabled',
        'sleep_time': '10'
    }

    # Current configuration file format version
    CONFIG_VERSION = "1.0"

    def __init__(self, app_instance):
        self.app = app_instance

    def save_profile(self):
        """Gathers configuration from UI and saves it to a .lt32config file."""
        # Get a reference to the parameters frame for easier access
        params_frame = self.app.params_frame
        
        import configparser
        from datetime import datetime
        # Get all parameter values from factory-created widgets
        all_parameters = params_frame.get_all_parameter_values()

        config = configparser.ConfigParser()
        config.optionxform = str  # Preserve case

        # Add profile info section
        config.add_section('Profile_Info')
        config.set('Profile_Info', 'version', self.CONFIG_VERSION)
        config.set('Profile_Info', 'created_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        config.set('Profile_Info', 'profile_name', f"LT32Pro_Config_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        # Organize parameters into sections and flatten all values
        # APN section
        apn_values = params_frame._get_apn_values_from_section()
        config.add_section('APN_Configuration')
        config.set('APN_Configuration', 'apn', apn_values.get('apn', ''))
        config.set('APN_Configuration', 'user', apn_values.get('user', ''))
        config.set('APN_Configuration', 'password', apn_values.get('password', ''))

        # Transmission mode section
        config.add_section('Server_Configuration')
        config.set('Server_Configuration', 'transmission_mode', all_parameters.get('transmission_mode', 'TCP'))

        # Device parameters section (device format: dict strings for complex values)
        import json
        config.add_section('Device_Parameters')
        for param_name, value in all_parameters.items():
            if param_name not in ['apn', 'user', 'password', 'transmission_mode']:
                if isinstance(value, dict):
                    # Store as dict string (use json for safe serialization)
                    config.set('Device_Parameters', param_name, json.dumps(value, ensure_ascii=False))
                else:
                    config.set('Device_Parameters', param_name, str(value))

        filepath = filedialog.asksaveasfilename(
            defaultextension=".lt32config",
            filetypes=[("LT32Pro Config Files", "*.lt32config"), ("All Files", "*.*")],
            title="Save Configuration Profile" # PRD 4.3.1
        )
        if not filepath:
            return

        with open(filepath, 'w') as f:
            config.write(f)
        self.app.log_frame.log_message(f"Profile '{os.path.basename(filepath)}' saved.\n")

    def load_profile(self):
        """Loads a .lt32config file and populates the UI."""
        filepath = filedialog.askopenfilename(
            filetypes=[("LT32Pro Config Files", "*.lt32config"), ("All Files", "*.*")],
            title="Load Configuration Profile" # PRD 4.3.1
        )
        if not filepath:
            return # User cancelled the dialog
            
        # Show success notification when profile is loaded
        if hasattr(self.app, 'operation_confirmation_service'):
            self.app.operation_confirmation_service.show_success_notification(f"Loading profile '{os.path.basename(filepath)}'...")

        try:
            # Validate the configuration file before loading
            is_valid, error_message, config_data = self.validate_config_file(filepath)
            if not is_valid:
                messagebox.showerror("Profile Validation Error", error_message)
                self.app.log_frame.log_message(f"Profile validation error: {error_message}\n")
                return
            if error_message:
                if not messagebox.askyesno("Version Warning", error_message + " Do you want to continue?"):
                    return
            params_frame = self.app.params_frame
            # --- Handle APN Configuration ---
            apn_config = config_data.get('APN_Configuration', {})
            params_frame.apn_server_entry.delete(0, "end")
            params_frame.apn_server_entry.insert(0, apn_config.get("apn", ""))
            params_frame.apn_user_entry.delete(0, "end")
            params_frame.apn_user_entry.insert(0, apn_config.get("user", ""))
            params_frame.apn_password_entry.delete(0, "end")
            params_frame.apn_password_entry.insert(0, apn_config.get("password", ""))
            # --- Handle Transmission Mode ---
            server_config = config_data.get('Server_Configuration', {})
            params_frame.trans_mode_var.set(server_config.get("transmission_mode", "TCP"))
            # --- Handle all other parameters from factory-created widgets ---
            all_params = {}
            for section, params in config_data.items():
                if section in ['APN_Configuration', 'Server_Configuration', 'Profile_Info']:
                    continue
                for param_name, param_value in params.items():
                    # Attempt to deserialize JSON strings for complex parameters
                    if isinstance(param_value, str):
                        try:
                            # Only parse if it looks like a JSON object or array
                            if param_value.strip().startswith('{') or param_value.strip().startswith('['):
                                all_params[param_name] = json.loads(param_value)
                            else:
                                all_params[param_name] = param_value
                        except Exception:
                            all_params[param_name] = param_value
                    else:
                        all_params[param_name] = param_value
            try:
                params_frame.set_all_parameter_values(all_params)
                loaded_params = list(all_params.keys())
                if loaded_params:
                    self.app.log_frame.log_message(f"INFO: Loaded {len(loaded_params)} parameters from profile\n")
            except Exception as e:
                self.app.log_frame.log_message(f"ERROR: Error setting parameter values: {str(e)}\n")
                messagebox.showerror("Parameter Error", f"Error setting some parameter values: {str(e)}")
            self.app.log_frame.log_message(f"Profile '{os.path.basename(filepath)}' loaded successfully.\n")
        except Exception as e:
            error_message = f"Error loading profile: {e}\n"
            self.app.log_frame.log_message(error_message)
            messagebox.showerror("Load Profile Error", f"Failed to load or parse the profile file.\n\n{e}")
    
    def _compare_versions(self, version1, version2):
        """
        Compare two version strings.
        
        Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
        """
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        # Pad with zeros if needed
        while len(v1_parts) < len(v2_parts):
            v1_parts.append(0)
        while len(v2_parts) < len(v1_parts):
            v2_parts.append(0)
        
        # Compare each part
        for i in range(len(v1_parts)):
            if v1_parts[i] < v2_parts[i]:
                return -1
            elif v1_parts[i] > v2_parts[i]:
                return 1
        
        # If we get here, versions are equal
        return 0
        
    def restore_defaults(self):
        """
        Restore all UI fields to application default values.
        Requires confirmation before proceeding.
        """
        # Check if we have the operation confirmation service
        if hasattr(self.app, 'operation_confirmation_service'):
            # Ask for confirmation before restoring defaults
            if not self.app.operation_confirmation_service.confirm_operation(
                self.app.operation_confirmation_service.OPERATION_RESTORE_DEFAULTS
            ):
                self.app.log_frame.log_message("INFO: Restore defaults operation canceled by user\n")
                return
        else:
            # Fallback to standard confirmation dialog
            if not messagebox.askyesno(
                "Confirm Restore Defaults",
                "This will restore all application settings to default values.\n\n"
                "Current UI values will be reset. This will not affect the device settings.\n\n"
                "Do you want to continue?"
            ):
                self.app.log_frame.log_message("INFO: Restore defaults operation canceled by user\n")
                return
        
        # Get a reference to the parameters frame for easier access
        params_frame = self.app.params_frame
        
        try:
            # Create a progress dialog if we have the operation confirmation service
            progress_dialog_id = None
            if hasattr(self.app, 'operation_confirmation_service'):
                progress_dialog_id = self.app.operation_confirmation_service.create_progress_dialog(
                    "Restoring Defaults",
                    "Restore Default Values",
                    self.app.operation_confirmation_service.PROGRESS_TYPE_INDETERMINATE,
                    cancelable=False
                )
            
            # Reset APN parameters
            params_frame.apn_server_entry.delete(0, "end")
            params_frame.apn_server_entry.insert(0, self.DEFAULT_VALUES.get('apn_server', ''))
            
            params_frame.apn_user_entry.delete(0, "end")
            params_frame.apn_user_entry.insert(0, self.DEFAULT_VALUES.get('apn_user', ''))
            
            params_frame.apn_password_entry.delete(0, "end")
            params_frame.apn_password_entry.insert(0, self.DEFAULT_VALUES.get('apn_password', ''))
            
            # Reset transmission mode
            params_frame.trans_mode_var.set(self.DEFAULT_VALUES.get('transmission_mode', 'TCP'))
            
            # Reset all other parameters from factory-created widgets
            if hasattr(params_frame, 'set_all_parameter_values'):
                params_frame.set_all_parameter_values(self.DEFAULT_VALUES)
            
            # Complete the progress dialog if it exists
            if progress_dialog_id:
                self.app.operation_confirmation_service.complete_progress(
                    progress_dialog_id,
                    True,
                    "Default values restored successfully"
                )
            
            # Show success notification
            if hasattr(self.app, 'operation_confirmation_service'):
                self.app.operation_confirmation_service.show_success_notification("Default values restored successfully")
            else:
                self.app.log_frame.log_message("INFO: Default values restored successfully\n")
                
        except Exception as e:
            self.app.log_frame.log_message(f"ERROR: Failed to restore defaults: {str(e)}\n")
            
            # Close progress dialog with error if it exists
            if progress_dialog_id:
                self.app.operation_confirmation_service.complete_progress(
                    progress_dialog_id,
                    False,
                    f"Error: {str(e)}"
                )
            
            # Show error dialog
            messagebox.showerror("Restore Defaults Error", f"Failed to restore default values.\n\n{e}")
    
    def validate_config_file(self, filepath):
        """
        Validate a configuration file before loading it.
        
        Args:
            filepath: Path to the configuration file
            
        Returns:
            Tuple of (is_valid, error_message, config_data)
        """
        try:
            import configparser
            config = configparser.ConfigParser()
            config.optionxform = str
            config.read(filepath, encoding='utf-8')
            config_data = {}
            for section in config.sections():
                config_data[section] = dict(config.items(section))
            # Check for required Profile_Info section and version key
            if 'Profile_Info' not in config_data or 'version' not in config_data['Profile_Info']:
                return (False, "Profile is missing required section or key: Profile_Info/version", None)
            file_version = config_data['Profile_Info']['version']
            if self._compare_versions(file_version, self.CONFIG_VERSION) > 0:
                warning_message = (
                    f"Warning: The profile was created with a newer version ({file_version}) "
                    f"than the current application version ({self.CONFIG_VERSION}). "
                    "Some settings may not be loaded correctly."
                )
                return (True, warning_message, config_data)
            # Validate profile data structure using ValidationService if available
            params_frame = self.app.params_frame
            if hasattr(params_frame, 'validation_service'):
                validation_result = params_frame.validation_service.validate_profile_data(config_data)
                if not validation_result.is_valid:
                    return (False, validation_result.error_message, None)
            return (True, "", config_data)
        except Exception as e:
            return (False, f"Error validating configuration file: {str(e)}", None)