"""
Simple Profile Manager - Simplified, reliable profile operations.

This is a streamlined version that focuses on core functionality:
1. Device to Profile: Read device config and save to file
2. Profile to Device: Load profile file and send to device
3. Simple progress tracking with parameter count
"""

import os
import configparser
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import threading
import time

from ui.ultra_simple_progress_dialog import UltraSimpleProgressDialog, create_ultra_simple_progress_info


class SimpleProfileManager:
    """Simplified profile manager with reliable operations."""
    
    def __init__(self, app):
        self.app = app
        self.i18n = app.i18n_service
        self.serial_service = app.serial_service
        self.config_reader = app.configuration_reader_service
        
        # Progress tracking
        self.progress_dialog = None
        self.is_operation_running = False
        self.cancel_requested = False
        
    def device_to_profile(self, profile_path: str, profile_name: str = None):
        """
        Read device configuration and save to profile file.
        
        Args:
            profile_path: Path where to save the profile
            profile_name: Name for the profile (optional)
        """
        if self.is_operation_running:
            return False
            
        self.is_operation_running = True
        self.cancel_requested = False
        
        # Create progress dialog
        self.progress_dialog = UltraSimpleProgressDialog(self.app, 'device_to_profile')
        self.progress_dialog.set_cancel_callback(self._cancel_operation)
        self.progress_dialog.show()
        
        # Start operation in background thread
        thread = threading.Thread(
            target=self._device_to_profile_worker,
            args=(profile_path, profile_name),
            daemon=True
        )
        thread.start()
        
        return True
        
    def profile_to_device(self, profile_path: str):
        """
        Load profile file and send configuration to device.
        
        Args:
            profile_path: Path to the profile file to load
        """
        if self.is_operation_running:
            return False
            
        if not os.path.exists(profile_path):
            self._show_error(f"Profile file not found: {profile_path}")
            return False
            
        self.is_operation_running = True
        self.cancel_requested = False
        
        # Create progress dialog
        self.progress_dialog = UltraSimpleProgressDialog(self.app, 'profile_to_device')
        self.progress_dialog.set_cancel_callback(self._cancel_operation)
        self.progress_dialog.show()
        
        # Start operation in background thread
        thread = threading.Thread(
            target=self._profile_to_device_worker,
            args=(profile_path,),
            daemon=True
        )
        thread.start()
        
        return True
        
    def _device_to_profile_worker(self, profile_path: str, profile_name: str = None):
        """Worker thread for device-to-profile operation."""
        try:
            # Step 1: Read device configuration
            self._update_progress(0, 0, "Connecting to device...")
            
            if self.cancel_requested:
                return
                
            # Read all parameters from device
            device_params = self.config_reader.read_all_parameters()
            
            if not device_params:
                self._show_error("Failed to read device configuration")
                return
                
            # Step 2: Process each parameter with progress updates
            total_params = len(device_params)
            processed_params = {}
            
            for i, (param_name, param_value) in enumerate(device_params.items(), 1):
                if self.cancel_requested:
                    return
                    
                # Update progress for each parameter
                self._update_progress(
                    i, total_params, 
                    f"Processing parameter: {param_name}"
                )
                
                # Process parameter (validate, convert, etc.)
                processed_params[param_name] = self._process_parameter(param_name, param_value)
                
                # Small delay to show progress
                time.sleep(0.05)
            
            # Step 3: Create profile file
            self._update_progress(total_params, total_params, "Creating profile file...")
            
            if self.cancel_requested:
                return
                
            success = self._save_profile_file(profile_path, processed_params, profile_name)
            
            if success:
                self._show_success("Profile saved successfully!")
            else:
                self._show_error("Failed to save profile file")
                
        except Exception as e:
            self._show_error(f"Operation failed: {str(e)}")
        finally:
            self.is_operation_running = False
            
    def _profile_to_device_worker(self, profile_path: str):
        """Worker thread for profile-to-device operation."""
        try:
            # Step 1: Load profile file
            self._update_progress(0, 0, "Loading profile file...")
            
            if self.cancel_requested:
                return
                
            profile_data = self._load_profile_file(profile_path)
            
            if not profile_data:
                self._show_error("Failed to load profile file")
                return
                
            # Step 2: Send each parameter to device with progress updates
            total_params = len(profile_data)
            
            for i, (param_name, param_value) in enumerate(profile_data.items(), 1):
                if self.cancel_requested:
                    return
                    
                # Update progress for each parameter
                self._update_progress(
                    i, total_params,
                    f"Sending parameter: {param_name}"
                )
                
                # Send parameter to device
                success = self._send_parameter_to_device(param_name, param_value)
                
                if not success:
                    print(f"Warning: Failed to send parameter {param_name}")
                
                # Small delay to show progress
                time.sleep(0.1)
            
            self._show_success("Profile loaded to device successfully!")
                
        except Exception as e:
            self._show_error(f"Operation failed: {str(e)}")
        finally:
            self.is_operation_running = False
            
    def _update_progress(self, current: int, total: int, message: str):
        """Update progress dialog."""
        if self.progress_dialog and not self.cancel_requested:
            progress_info = create_ultra_simple_progress_info(
                current_param=current,
                total_params=total,
                status_message=message
            )
            self.progress_dialog.update_progress(progress_info)
            
    def _show_success(self, message: str):
        """Show success message."""
        if self.progress_dialog:
            progress_info = create_ultra_simple_progress_info(
                current_param=1,
                total_params=1,
                status_message=message
            )
            progress_info.is_complete = True
            self.progress_dialog.update_progress(progress_info)
            
    def _show_error(self, message: str):
        """Show error message."""
        if self.progress_dialog:
            progress_info = create_ultra_simple_progress_info(
                current_param=0,
                total_params=1,
                status_message=message
            )
            progress_info.is_complete = True
            progress_info.has_error = True
            progress_info.error_message = message
            self.progress_dialog.update_progress(progress_info)
        else:
            # Fallback to console
            print(f"Error: {message}")
            
    def _cancel_operation(self):
        """Cancel the current operation."""
        self.cancel_requested = True
        self.is_operation_running = False
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
            
    def _process_parameter(self, param_name: str, param_value: Any) -> str:
        """Process a parameter value for profile storage."""
        if param_value is None:
            return ""
        return str(param_value)
        
    def _save_profile_file(self, profile_path: str, parameters: Dict[str, str], profile_name: str = None) -> bool:
        """Save parameters to profile file."""
        try:
            config = configparser.ConfigParser()
            
            # Add profile metadata
            config['Profile_Info'] = {
                'profile_name': profile_name or 'Device Configuration',
                'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'parameter_count': str(len(parameters)),
                'app_version': '1.0.0',
                'format_version': '1.0'
            }
            
            # Add device parameters
            config['Device_Parameters'] = parameters
            
            # Write to file
            with open(profile_path, 'w', encoding='utf-8') as f:
                config.write(f)
                
            return True
            
        except Exception as e:
            print(f"Error saving profile: {e}")
            return False
            
    def _load_profile_file(self, profile_path: str) -> Optional[Dict[str, str]]:
        """Load parameters from profile file."""
        try:
            config = configparser.ConfigParser()
            config.read(profile_path, encoding='utf-8')
            
            if 'Device_Parameters' not in config:
                print("Error: No Device_Parameters section in profile")
                return None
                
            # Convert to dictionary
            parameters = dict(config['Device_Parameters'])
            return parameters
            
        except Exception as e:
            print(f"Error loading profile: {e}")
            return None
            
    def _send_parameter_to_device(self, param_name: str, param_value: str) -> bool:
        """Send a parameter to the device."""
        try:
            if not self.serial_service.is_connected:
                print("Error: Device not connected")
                return False
                
            # Create AT command for parameter
            command = f"AT+{param_name.upper()}={param_value}"
            
            # Send command
            response = self.serial_service.send_command(command)
            
            # Check if command was successful
            return response and "OK" in response
            
        except Exception as e:
            print(f"Error sending parameter {param_name}: {e}")
            return False