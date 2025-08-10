"""
Core Profile Manager - Simple, reliable profile operations with new components.

This module provides the core ProfileManager class with four main methods:
1. save_profile_from_ui - Save UI configuration to profile file
2. save_profile_from_device - Save device configuration to profile file  
3. load_profile_to_ui - Load profile file to UI
4. load_profile_to_device - Load profile file to device

Updated to use:
- SimplifiedProfileFileHandler for universal format
- NonBlockingProfileManager for UI responsiveness
- UnifiedProgressDialog for consistent progress indication
- ProfileMessageManager for simplified messaging
"""

import os
import configparser
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import logging

from services.simplified_profile_file_handler import SimplifiedProfileFileHandler
from services.non_blocking_profile_manager import NonBlockingProfileManager, OperationType
from ui.unified_progress_dialog import UnifiedProgressDialog
from services.profile_message_manager import ProfileMessageManager


class CoreProfileManager:
    """Core profile manager with four main operations using new components."""
    
    def __init__(self, app_instance):
        """
        Initialize the core profile manager.
        
        Args:
            app_instance: Main application instance with UI and services
        """
        self.app = app_instance
        self.i18n = getattr(app_instance, 'i18n_service', None) or getattr(app_instance, 'i18n', None)
        
        # Initialize new components
        self.file_handler = SimplifiedProfileFileHandler()
        self.non_blocking_manager = NonBlockingProfileManager(app_instance)
        self.message_manager = ProfileMessageManager(
            parent_widget=getattr(app_instance, 'root', None),
            i18n_service=self.i18n
        )
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Profile format version
        self.profile_version = "1.0"
        
    def save_profile_from_ui(self, file_path: str, profile_name: str = None) -> bool:
        """
        Save current UI configuration to a profile file using universal format.
        
        Args:
            file_path: Path where to save the profile file
            profile_name: Optional name for the profile
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get all parameter values from UI
            if not hasattr(self.app, 'parameters_frame') or not self.app.parameters_frame:
                error_msg = self._get_localized_message("parameters_frame_not_available", "Parameters frame not available")
                self.logger.error("Parameters frame not available")
                self.message_manager.show_operation_result(
                    operation_id="save_from_ui",
                    success=False,
                    operation_type="save_from_ui",
                    details=error_msg
                )
                return False
                
            ui_parameters = self.app.parameters_frame.get_all_parameter_values()
            
            if not ui_parameters:
                self.logger.warning("No parameters found in UI")
                ui_parameters = {}
            
            # Use SimplifiedProfileFileHandler to write universal format
            success, error = self.file_handler.write_universal_profile(file_path, ui_parameters)
            
            if success:
                self.logger.info(f"Successfully saved UI profile to: {file_path}")
                
                # Show success message using ProfileMessageManager
                success_msg = self._get_localized_message(
                    "profile_save_success_message", 
                    "UI configuration has been saved successfully to:\n\n{file_path}\n\nParameters saved: {param_count}"
                ).format(file_path=file_path, param_count=len(ui_parameters))
                
                self.message_manager.show_operation_result(
                    operation_id="save_from_ui",
                    success=True,
                    operation_type="save_from_ui",
                    details=success_msg
                )
                return True
            else:
                self.logger.error(f"Failed to save UI profile: {error}")
                
                # Show error message using ProfileMessageManager
                error_msg = self._get_localized_message(
                    "profile_save_error_message",
                    "Failed to save profile file:\n\n{error}\n\nPlease check file permissions and try again."
                ).format(error=error)
                
                self.message_manager.show_operation_result(
                    operation_id="save_from_ui",
                    success=False,
                    operation_type="save_from_ui",
                    details=error_msg
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Error saving profile from UI: {str(e)}")
            
            # Show generic error message using ProfileMessageManager
            error_msg = self._get_localized_message(
                "profile_save_unexpected_error",
                "An unexpected error occurred while saving the profile:\n\n{error}\n\nPlease try again or contact support."
            ).format(error=str(e))
            
            self.message_manager.show_operation_result(
                operation_id="save_from_ui",
                success=False,
                operation_type="save_from_ui",
                details=error_msg
            )
            return False
    
    def save_profile_from_device(self, file_path: str, profile_name: str = None) -> bool:
        """
        Save current device configuration to a profile file using non-blocking operations.
        
        Args:
            file_path: Path where to save the profile file
            profile_name: Optional name for the profile
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check device connection with comprehensive validation
            if not self._is_device_connected():
                self.logger.error("Device not connected")
                
                error_msg = self._get_localized_message(
                    "device_not_connected_save_message",
                    "Cannot save profile from device because no device is connected.\n\nPlease:\n1. Connect your device\n2. Ensure it's powered on\n3. Check the connection cable\n4. Try again"
                )
                self.message_manager.show_operation_result(
                    operation_id="save_from_device",
                    success=False,
                    operation_type="save_from_device",
                    details=error_msg
                )
                return False
            
            # Create unified progress dialog first
            progress_dialog = UnifiedProgressDialog(
                parent=getattr(self.app, 'root', None),
                operation_type="save_from_device",
                i18n_service=self.i18n
            )
            progress_dialog.show()
            
            # Use non-blocking manager to execute the operation
            def progress_callback(progress_info):
                """Handle progress updates from non-blocking operation."""
                # Convert non-blocking progress info to unified progress info
                from ui.unified_progress_dialog import UnifiedProgressInfo
                unified_info = UnifiedProgressInfo(
                    operation_type="save_from_device",
                    current_step=progress_info.current_step,
                    total_steps=progress_info.total_steps,
                    progress_percentage=progress_info.current_step / max(progress_info.total_steps, 1),
                    status_message=progress_info.status_message,
                    current_parameter=progress_info.current_parameter,
                    parameter_count=progress_info.current_step,
                    total_parameters=progress_info.total_steps,
                    can_cancel=progress_info.can_cancel,
                    is_complete=progress_info.is_complete
                )
                progress_dialog.update_progress(unified_info)
            
            def completion_callback(result):
                """Handle completion of non-blocking operation."""
                # Update progress dialog with completion status
                from ui.unified_progress_dialog import UnifiedProgressInfo
                completion_info = UnifiedProgressInfo(
                    operation_type="save_from_device",
                    current_step=100,
                    total_steps=100,
                    progress_percentage=1.0,
                    status_message="Operation completed" if result.success else f"Operation failed: {result.error_message}",
                    is_complete=True,
                    has_error=not result.success,
                    error_message=result.error_message if not result.success else ""
                )
                progress_dialog.update_progress(completion_info)
                
                if result.success:
                    success_msg = self._get_localized_message(
                        "device_profile_save_success_message",
                        "Device configuration has been saved successfully to:\n\n{file_path}\n\nParameters saved: {param_count}"
                    ).format(
                        file_path=file_path, 
                        param_count=result.parameters_processed
                    )
                    
                    self.message_manager.show_operation_result(
                        operation_id="save_from_device",
                        success=True,
                        operation_type="save_from_device",
                        details=success_msg
                    )
                else:
                    error_msg = self._get_localized_message(
                        "device_profile_save_error_message",
                        "Failed to save device profile:\n\n{error}\n\nPlease check device connection and try again."
                    ).format(error=result.error_message or "Unknown error")
                    
                    self.message_manager.show_operation_result(
                        operation_id="save_from_device",
                        success=False,
                        operation_type="save_from_device",
                        details=error_msg
                    )
            
            # Set up cancellation callback for progress dialog
            def cancel_callback():
                """Handle cancellation from progress dialog."""
                self.non_blocking_manager.cancel_operation(operation_id)
            
            progress_dialog.set_cancel_callback(cancel_callback)
            # DO NOT set completion callback - this causes callback loops
            # The completion will be handled by the non-blocking manager's completion callback
            
            # Execute operation using non-blocking manager
            operation_id = self.non_blocking_manager.execute_profile_operation(
                operation_type=OperationType.LOAD_FROM_DEVICE,
                file_path=file_path,
                profile_name=profile_name,
                progress_callback=progress_callback,
                completion_callback=completion_callback
            )
            
            # The operation will complete asynchronously
            return True
                
        except Exception as e:
            self.logger.error(f"Error saving profile from device: {str(e)}")
            
            error_msg = self._get_localized_message(
                "profile_save_unexpected_error",
                "An unexpected error occurred while saving the device profile:\n\n{error}\n\nPlease try again or contact support."
            ).format(error=str(e))
            
            self.message_manager.show_operation_result(
                operation_id="save_from_device",
                success=False,
                operation_type="save_from_device",
                details=error_msg
            )
            return False
    
    def load_profile_to_ui(self, file_path: str) -> bool:
        """
        Load profile file and populate UI with the values using universal format reading.
        
        Args:
            file_path: Path to the profile file to load
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Show unified progress dialog
            progress_dialog = UnifiedProgressDialog(
                parent=getattr(self.app, 'root', None),
                operation_type="load_to_ui",
                i18n_service=self.i18n
            )
            progress_dialog.show()
            
            # Update progress - reading file
            from ui.unified_progress_dialog import UnifiedProgressInfo
            progress_info = UnifiedProgressInfo(
                operation_type="load_to_ui",
                current_step=1,
                total_steps=3,
                progress_percentage=0.33,
                status_message=self._get_localized_message("reading_profile_file", "Reading profile file...")
            )
            progress_dialog.update_progress(progress_info)
            
            # Use SimplifiedProfileFileHandler to read universal format
            parameters, error = self.file_handler.read_universal_profile(file_path)
            
            if error:
                self.logger.error(f"Failed to read profile file: {error}")
                progress_dialog.close_dialog()
                
                error_msg = self._get_localized_message(
                    "profile_read_error_message",
                    "Failed to read profile file:\n\n{error}\n\nPlease check the file format and try again."
                ).format(error=error)
                
                self.message_manager.show_operation_result(
                    operation_id="load_to_ui",
                    success=False,
                    operation_type="load_to_ui",
                    details=error_msg
                )
                return False
            
            if not parameters:
                self.logger.warning("No parameters found in profile file")
                progress_dialog.close_dialog()
                
                warning_msg = self._get_localized_message(
                    "profile_empty_warning_message",
                    "The profile file contains no parameters to load."
                )
                
                self.message_manager.show_operation_result(
                    operation_id="load_to_ui",
                    success=False,
                    operation_type="load_to_ui",
                    details=warning_msg
                )
                return False
            
            # Update progress - validating UI
            progress_info = UnifiedProgressInfo(
                operation_type="load_to_ui",
                current_step=2,
                total_steps=3,
                progress_percentage=0.66,
                status_message=self._get_localized_message("validating_ui", "Validating UI components...")
            )
            progress_dialog.update_progress(progress_info)
            
            # Set parameters in UI
            if not hasattr(self.app, 'parameters_frame') or not self.app.parameters_frame:
                self.logger.error("Parameters frame not available")
                progress_dialog.close_dialog()
                
                error_msg = self._get_localized_message("parameters_frame_not_available", "Parameters frame not available")
                self.message_manager.show_operation_result(
                    operation_id="load_to_ui",
                    success=False,
                    operation_type="load_to_ui",
                    details=error_msg
                )
                return False
            
            # Update progress - populating UI
            progress_info = UnifiedProgressInfo(
                operation_type="load_to_ui",
                current_step=3,
                total_steps=3,
                progress_percentage=1.0,
                status_message=self._get_localized_message("populating_ui", "Populating UI fields...")
            )
            progress_dialog.update_progress(progress_info)
            
            self.app.parameters_frame.set_all_parameter_values(parameters)
            
            # Show completion
            completion_info = UnifiedProgressInfo(
                operation_type="load_to_ui",
                current_step=3,
                total_steps=3,
                progress_percentage=1.0,
                status_message=self._get_localized_message("profile_loaded_successfully", "Profile loaded successfully"),
                is_complete=True
            )
            progress_dialog.update_progress(completion_info)
            progress_dialog.close_dialog()
            
            self.logger.info(f"Successfully loaded profile to UI from: {file_path}")
            
            # Show success message
            success_msg = self._get_localized_message(
                "profile_to_ui_success_message",
                "Profile has been loaded successfully to UI.\n\nParameters loaded: {param_count}"
            ).format(param_count=len(parameters))
            
            self.message_manager.show_operation_result(
                operation_id="load_to_ui",
                success=True,
                operation_type="load_to_ui",
                details=success_msg
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading profile to UI: {str(e)}")
            
            if 'progress_dialog' in locals():
                progress_dialog.close_dialog()
            
            error_msg = self._get_localized_message(
                "profile_load_unexpected_error",
                "An unexpected error occurred while loading the profile:\n\n{error}\n\nPlease try again or contact support."
            ).format(error=str(e))
            
            self.message_manager.show_operation_result(
                operation_id="load_to_ui",
                success=False,
                operation_type="load_to_ui",
                details=error_msg
            )
            return False
    
    def load_profile_to_device(self, file_path: str) -> bool:
        """
        Load profile file and send configuration to device using non-blocking operations.
        
        Args:
            file_path: Path to the profile file to load
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check device connection
            if not self._is_device_connected():
                self.logger.error("Device not connected")
                
                error_msg = self._get_localized_message(
                    "device_not_connected_load_message",
                    "Cannot load profile to device because no device is connected.\n\nPlease:\n1. Connect your device\n2. Ensure it's powered on\n3. Check the connection cable\n4. Try again"
                )
                self.message_manager.show_operation_result(
                    operation_id="load_to_device",
                    success=False,
                    operation_type="load_to_device",
                    details=error_msg
                )
                return False
            
            # Read profile file using universal format
            parameters, error = self.file_handler.read_universal_profile(file_path)
            
            if error:
                self.logger.error(f"Failed to read profile file: {error}")
                
                error_msg = self._get_localized_message(
                    "profile_read_failed_message",
                    "Failed to read profile data from file:\n\n{error}\n\nPlease check the file format and try again."
                ).format(error=error)
                
                self.message_manager.show_operation_result(
                    operation_id="load_to_device",
                    success=False,
                    operation_type="load_to_device",
                    details=error_msg
                )
                return False
            
            if not parameters:
                self.logger.warning("No parameters found in profile data.")
                
                warning_msg = self._get_localized_message(
                    "profile_empty_message",
                    "The selected profile contains no parameters to load to the device."
                )
                
                self.message_manager.show_operation_result(
                    operation_id="load_to_device",
                    success=False,
                    operation_type="load_to_device",
                    details=warning_msg
                )
                return False
            
            # Create unified progress dialog first
            progress_dialog = UnifiedProgressDialog(
                parent=getattr(self.app, 'root', None),
                operation_type="load_to_device",
                i18n_service=self.i18n
            )
            progress_dialog.show()
            
            # Use non-blocking manager to execute the operation
            def progress_callback(progress_info):
                """Handle progress updates from non-blocking operation."""
                # Convert non-blocking progress info to unified progress info
                from ui.unified_progress_dialog import UnifiedProgressInfo
                unified_info = UnifiedProgressInfo(
                    operation_type="load_to_device",
                    current_step=progress_info.current_step,
                    total_steps=progress_info.total_steps,
                    progress_percentage=progress_info.current_step / max(progress_info.total_steps, 1),
                    status_message=progress_info.status_message,
                    current_parameter=progress_info.current_parameter,
                    parameter_count=progress_info.current_step,
                    total_parameters=progress_info.total_steps,
                    can_cancel=progress_info.can_cancel,
                    is_complete=progress_info.is_complete
                )
                progress_dialog.update_progress(unified_info)
            
            def completion_callback(result):
                """Handle completion of non-blocking operation."""
                # Update progress dialog with completion status
                from ui.unified_progress_dialog import UnifiedProgressInfo
                completion_info = UnifiedProgressInfo(
                    operation_type="load_to_device",
                    current_step=100,
                    total_steps=100,
                    progress_percentage=1.0,
                    status_message="Operation completed" if result.success else f"Operation failed: {result.error_message}",
                    is_complete=True,
                    has_error=not result.success,
                    error_message=result.error_message if not result.success else ""
                )
                progress_dialog.update_progress(completion_info)
                
                if result.success:
                    # Consider successful if at least 80% of parameters were sent
                    success_rate = result.parameters_processed / len(parameters) if parameters else 0
                    
                    if success_rate >= 0.8:
                        success_msg = self._get_localized_message(
                            "profile_to_device_success_message",
                            "Profile successfully loaded to device.\n\nParameters deployed: {deployed}/{total}"
                        ).format(
                            deployed=result.parameters_processed,
                            total=len(parameters)
                        )
                        
                        self.message_manager.show_operation_result(
                            operation_id="load_to_device",
                            success=True,
                            operation_type="load_to_device",
                            details=success_msg
                        )
                    else:
                        error_msg = self._get_localized_message(
                            "profile_to_device_partial_failure_message",
                            "Failed to load profile to device.\n\nOnly {deployed}/{total} parameters were successfully deployed.\n\nPlease check device connection and logs for details."
                        ).format(
                            deployed=result.parameters_processed,
                            total=len(parameters)
                        )
                        
                        self.message_manager.show_operation_result(
                            operation_id="load_to_device",
                            success=False,
                            operation_type="load_to_device",
                            details=error_msg
                        )
                else:
                    error_msg = self._get_localized_message(
                        "profile_to_device_error_message",
                        "Failed to load profile to device:\n\n{error}\n\nPlease check device connection and try again."
                    ).format(error=result.error_message or "Unknown error")
                    
                    self.message_manager.show_operation_result(
                        operation_id="load_to_device",
                        success=False,
                        operation_type="load_to_device",
                        details=error_msg
                    )
            
            # Set up cancellation callback for progress dialog
            def cancel_callback():
                """Handle cancellation from progress dialog."""
                self.non_blocking_manager.cancel_operation(operation_id)
            
            progress_dialog.set_cancel_callback(cancel_callback)
            # DO NOT set completion callback - this causes callback loops
            # The completion will be handled by the non-blocking manager's completion callback
            
            # Execute operation using non-blocking manager
            operation_id = self.non_blocking_manager.execute_profile_operation(
                operation_type=OperationType.LOAD_TO_DEVICE,
                file_path=file_path,
                parameters=parameters,
                progress_callback=progress_callback,
                completion_callback=completion_callback
            )
            
            # The operation will complete asynchronously
            return True
                
        except Exception as e:
            self.logger.error(f"Error loading profile to device: {str(e)}")
            
            error_msg = self._get_localized_message(
                "profile_load_unexpected_error",
                "An unexpected error occurred while loading the profile:\n\n{error}\n\nPlease try again or contact support."
            ).format(error=str(e))
            
            self.message_manager.show_operation_result(
                operation_id="load_to_device",
                success=False,
                operation_type="load_to_device",
                details=error_msg
            )
            return False
    

    
    def _is_device_connected(self) -> bool:
        """
        Check if device is connected with comprehensive validation.
        
        Returns:
            bool: True if device is connected, False otherwise
        """
        try:
            # Check if serial service exists and is connected
            if not hasattr(self.app, 'serial_service') or not self.app.serial_service:
                self.logger.debug("Serial service not available")
                return False
                
            if not getattr(self.app.serial_service, 'is_connected', False):
                self.logger.debug("Serial service reports not connected")
                return False
            
            # Additional validation - check if serial port is available
            if hasattr(self.app.serial_service, 'serial_port') and not self.app.serial_service.serial_port:
                self.logger.debug("Serial port not available")
                return False
            
            # Check if configuration reader service is available (needed for parameter reading)
            if not hasattr(self.app, 'configuration_reader_service') or not self.app.configuration_reader_service:
                self.logger.debug("Configuration reader service not available")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking device connection: {str(e)}")
            return False
    
    def _get_device_info(self) -> Dict[str, str]:
        """
        Get device information for profile metadata.
        
        Returns:
            Dictionary with device information
        """
        device_info = {}
        
        try:
            # Try to get device info from serial service
            if hasattr(self.app, 'serial_service') and self.app.serial_service:
                if hasattr(self.app.serial_service, 'device_info'):
                    device_info.update(self.app.serial_service.device_info)
                
                # Try to get port information
                if hasattr(self.app.serial_service, 'port'):
                    device_info['port'] = str(self.app.serial_service.port)
                
                # Try to get baudrate
                if hasattr(self.app.serial_service, 'baudrate'):
                    device_info['baudrate'] = str(self.app.serial_service.baudrate)
            
            # Try to get additional info from configuration reader
            if hasattr(self.app, 'configuration_reader_service') and self.app.configuration_reader_service:
                config_reader = self.app.configuration_reader_service
                
                # Try to read device identification parameters
                try:
                    # Common device identification parameters
                    id_params = ['imei', 'serial_number', 'device_id', 'firmware_version', 'hardware_version']
                    
                    for param in id_params:
                        try:
                            result = config_reader.read_specific_parameter(param, f"AT+{param.upper()}", "query", max_retries=1)
                            if result.success and result.value:
                                device_info[param] = str(result.value)
                        except Exception:
                            continue  # Skip failed parameter reads
                            
                except Exception as e:
                    self.logger.debug(f"Could not read device identification parameters: {e}")
            
            # Add timestamp
            device_info['read_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return device_info
            
        except Exception as e:
            self.logger.error(f"Error getting device info: {str(e)}")
            return {'error': str(e), 'read_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    def _read_all_device_parameters(self) -> Optional[Dict[str, str]]:
        """
        Read all parameters from the connected device.
        
        Returns:
            Dictionary of parameter name/value pairs, or None if failed
        """
        return self._read_all_device_parameters_with_progress(None)
    
    def _read_all_device_parameters_with_progress(self, progress_dialog=None) -> Optional[Dict[str, str]]:
        """
        Read all parameters from the connected device with optional progress tracking.
        
        Args:
            progress_dialog: Optional progress dialog for user feedback
            
        Returns:
            Dictionary of parameter name/value pairs, or None if failed
        """
        try:
            if not hasattr(self.app, 'configuration_reader_service') or not self.app.configuration_reader_service:
                self.logger.error("Configuration reader service not available")
                return None
            
            config_reader = self.app.configuration_reader_service
            
            # Get all parameter commands from the configuration reader
            all_commands = config_reader._get_all_parameter_commands()
            
            if not all_commands:
                self.logger.error("No parameter commands available")
                return None
            
            parameters = {}
            successful_reads = 0
            total_commands = len(all_commands)
            
            self.logger.info(f"Reading {total_commands} parameters from device...")
            
            # Update progress dialog with actual parameter count
            if progress_dialog:
                progress_dialog.total_steps = total_commands + 10  # Extra steps for setup/cleanup
                init_msg = self._get_localized_message("initializing_device_read", "Initializing device read...")
                progress_dialog.update_progress(5, init_msg)
            
            # Read each parameter individually with progress updates
            for i, (param_name, command, command_type) in enumerate(all_commands):
                try:
                    # Update progress
                    if progress_dialog:
                        read_msg = self._get_localized_message(
                            "reading_parameter", 
                            "Reading parameter: {param_name}"
                        ).format(param_name=param_name)
                        progress_dialog.update_progress(10 + i, read_msg)
                    
                    # Use the existing parameter reading method
                    result = config_reader.read_specific_parameter(param_name, command, command_type, max_retries=1)
                    
                    if result.success and result.value is not None:
                        parameters[param_name] = str(result.value)
                        successful_reads += 1
                        self.logger.debug(f"Successfully read {param_name}: {result.value}")
                    else:
                        self.logger.warning(f"Failed to read parameter {param_name}: {result.error_message}")
                        # Store empty value for failed parameters to maintain structure
                        parameters[param_name] = ""
                        
                except Exception as param_error:
                    self.logger.warning(f"Exception reading parameter {param_name}: {str(param_error)}")
                    parameters[param_name] = ""
            
            # Final progress update
            if progress_dialog:
                complete_msg = self._get_localized_message(
                    "device_read_complete", 
                    "Device read complete: {successful}/{total} parameters"
                ).format(successful=successful_reads, total=total_commands)
                progress_dialog.update_progress(total_commands + 5, complete_msg)
            
            # Consider successful if we read at least some parameters
            if successful_reads > 0:
                self.logger.info(f"Successfully read {successful_reads}/{total_commands} parameters from device")
                return parameters
            else:
                self.logger.error("Failed to read any parameters from device")
                return None
            
        except Exception as e:
            self.logger.error(f"Error reading device parameters: {str(e)}")
            return None
    
    def _send_parameter_to_device(self, param_name: str, param_value: str) -> bool:
        """
        Send a single parameter to the device.
        
        Args:
            param_name: Name of the parameter
            param_value: Value to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not hasattr(self.app, 'serial_service') or not self.app.serial_service:
                self.logger.error("Serial service not available")
                return False
            
            if not hasattr(self.app, 'device_command_mapper') or not self.app.device_command_mapper:
                self.logger.error("Device command mapper not available")
                return False
            
            # Use the device command mapper to generate the proper command
            try:
                command = self.app.device_command_mapper.get_command(
                    param_name, 
                    param_value, 
                    context={}, 
                    confirm_destructive=False, 
                    validate_command=True
                )
                
                if not command:
                    self.logger.warning(f"No command generated for parameter {param_name}")
                    return False
                
            except Exception as cmd_error:
                self.logger.warning(f"Failed to generate command for {param_name}: {str(cmd_error)}")
                # Fallback to simple command format
                command = f"ATSMS:{param_name.upper()},{param_value}#"
            
            # Send command to device
            response = self.app.serial_service.send_command(command)
            
            # Check if command was successful
            # LT32Pro typically responds with "OK" or the command echo for successful commands
            if response and ("OK" in response or "SUCCESS" in response or command.replace("ATSMS:", "") in response):
                self.logger.debug(f"Successfully sent {param_name}: {param_value}")
                return True
            else:
                self.logger.warning(f"Device response for {param_name}: {response}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending parameter {param_name} to device: {str(e)}")
            return False
    
    def _get_localized_message(self, key: str, default: str) -> str:
        """
        Get localized message using i18n service.
        
        Args:
            key: Translation key
            default: Default message if translation not found
            
        Returns:
            Localized message string
        """
        try:
            if self.i18n:
                return self.i18n.get(key, default)
            return default
        except Exception:
            return default
    
