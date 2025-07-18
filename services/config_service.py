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
        
        # Create the base configuration structure with version
        config_data = {
            "version": self.CONFIG_VERSION,
            "created_at": datetime.datetime.now().isoformat(),
            "apn_config": {
                "server": params_frame.apn_server_entry.get(),
                "user": params_frame.apn_user_entry.get(),
                "password": params_frame.apn_password_entry.get(),
            },
            "communication": {
                "transmission_mode": params_frame.trans_mode_var.get(),
            },
            "device_parameters": {},
            "sensors": {},
            "timers": {},
            "security": {}
        }
        
        # Get all parameter values from factory-created widgets
        all_parameters = params_frame.get_all_parameter_values()
        
        # Map parameters to their respective categories based on parameter factory definitions
        for param_name, value in all_parameters.items():
            # Skip empty values
            if value is None or (isinstance(value, str) and not value.strip()):
                continue
                
            # Get parameter definition to determine its group
            param_def = params_frame.parameter_factory.get_parameter_definition(param_name)
            if param_def:
                group_name = param_def.group
                
                # Ensure the group exists in config_data
                if group_name not in config_data:
                    config_data[group_name] = {}
                
                # Add parameter to its group
                config_data[group_name][param_name] = value
        
        # Special handling for transmission_mode which might be in both places
        if "transmission_mode" in all_parameters:
            config_data["communication"]["transmission_mode"] = all_parameters["transmission_mode"]

        filepath = filedialog.asksaveasfilename(
            defaultextension=".lt32config",
            filetypes=[("LT32Pro Config Files", "*.lt32config"), ("All Files", "*.*")],
            title="Save Configuration Profile" # PRD 4.3.1
        )
        if not filepath:
            return

        with open(filepath, 'w') as f:
            json.dump(config_data, f, indent=4)
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
            
            # Show warning if there is one but file is still valid
            if error_message:
                if not messagebox.askyesno("Version Warning", error_message + " Do you want to continue?"):
                    return

            # Get a reference to the parameters frame for easier access
            params_frame = self.app.params_frame

            # Check if this is a new format config file with version
            is_new_format = "version" in config_data
            
            # --- Handle APN Configuration ---
            if is_new_format and "apn_config" in config_data:
                apn_config = config_data["apn_config"]
                params_frame.apn_server_entry.delete(0, "end")
                params_frame.apn_server_entry.insert(0, apn_config.get("server", ""))
                
                params_frame.apn_user_entry.delete(0, "end")
                params_frame.apn_user_entry.insert(0, apn_config.get("user", ""))
                
                params_frame.apn_password_entry.delete(0, "end")
                params_frame.apn_password_entry.insert(0, apn_config.get("password", ""))
            else:
                # Legacy format - direct keys
                params_frame.apn_server_entry.delete(0, "end")
                params_frame.apn_server_entry.insert(0, config_data.get("apn_server", ""))
                
                params_frame.apn_user_entry.delete(0, "end")
                params_frame.apn_user_entry.insert(0, config_data.get("apn_user", ""))
                
                params_frame.apn_password_entry.delete(0, "end")
                params_frame.apn_password_entry.insert(0, config_data.get("apn_password", ""))
            
            # --- Handle Transmission Mode ---
            if is_new_format and "communication" in config_data:
                comm_config = config_data["communication"]
                params_frame.trans_mode_var.set(comm_config.get("transmission_mode", "TCP"))
            else:
                # Legacy format - direct key
                params_frame.trans_mode_var.set(config_data.get("transmission_mode", "TCP"))
            
            # --- Handle all other parameters from factory-created widgets ---
            if is_new_format:
                # Collect all parameters from all categories
                all_params = {}
                invalid_params = []
                
                # Process each category in the config file
                for category, params in config_data.items():
                    # Skip non-dictionary categories and special categories
                    if not isinstance(params, dict) or category == "version" or category == "created_at":
                        continue
                    
                    # Process each parameter in this category
                    for param_name, param_value in params.items():
                        # Check if parameter exists in the UI
                        param_def = params_frame.parameter_factory.get_parameter_definition(param_name)
                        if param_def:
                            all_params[param_name] = param_value
                        else:
                            # Track unknown parameters for logging
                            invalid_params.append(f"{category}.{param_name}")
                
                # Log any invalid parameters found
                if invalid_params:
                    self.app.log_frame.log_message(f"WARNING: Skipped unknown parameters in profile: {', '.join(invalid_params)}\n")
                
                # Set values in the UI with validation
                try:
                    params_frame.set_all_parameter_values(all_params)
                    
                    # Log which parameters were successfully loaded
                    loaded_params = list(all_params.keys())
                    if loaded_params:
                        self.app.log_frame.log_message(f"INFO: Loaded {len(loaded_params)} parameters from profile\n")
                except Exception as e:
                    self.app.log_frame.log_message(f"ERROR: Error setting parameter values: {str(e)}\n")
                    messagebox.showerror("Parameter Error", f"Error setting some parameter values: {str(e)}")
            
            self.app.log_frame.log_message(f"Profile '{os.path.basename(filepath)}' loaded successfully.\n")

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
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
            with open(filepath, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Check if this is a new format config file with version
            is_new_format = "version" in config_data
            
            if is_new_format:
                # Check version compatibility
                file_version = config_data.get("version", "0.0")
                if self._compare_versions(file_version, self.CONFIG_VERSION) > 0:
                    warning_message = (
                        f"Warning: The profile was created with a newer version ({file_version}) "
                        f"than the current application version ({self.CONFIG_VERSION}). "
                        "Some settings may not be loaded correctly."
                    )
                    return (True, warning_message, config_data)  # Valid but with warning
                
                # Validate profile data structure using ValidationService if available
                params_frame = self.app.params_frame
                if hasattr(params_frame, 'validation_service'):
                    validation_result = params_frame.validation_service.validate_profile_data(config_data)
                    if not validation_result.is_valid:
                        return (False, validation_result.error_message, None)
            
            return (True, "", config_data)
            
        except json.JSONDecodeError:
            return (False, "Invalid JSON format in configuration file.", None)
        except FileNotFoundError:
            return (False, "Configuration file not found.", None)
        except Exception as e:
            return (False, f"Error validating configuration file: {str(e)}", None)