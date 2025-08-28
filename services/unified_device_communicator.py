"""
UnifiedDeviceCommunicator - Wrapper around ConfigurationReaderService for unified device communication.

This class provides a consistent interface for device communication by wrapping
ConfigurationReaderService, ensuring both "Check Configuration" and "Load Profile from Device"
operations use the same reliable communication method.
"""

import logging
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

from services.configuration_reader_service import ConfigurationReaderService, ConfigurationReadResult
from services.i18n_service import I18nService


class UnifiedDeviceCommunicator:
    """
    Unified device communication wrapper that uses ConfigurationReaderService
    for consistent and reliable device communication.
    """
    
    # Command sequence for reading device configuration
    READ_COMMAND_SEQUENCE = [
        'device_info',
        'apn_settings', 
        'server_settings',
        'network_settings',
        'protocol',
        'tcp_ack',
        'report_intervals',
        'heartbeat_intervals',
        'ignition_type',
        'speed_alert',
        'speed_buzzer',
        'sleep_mode',
        'sleep_time',
        'angle_report',
        'backup_battery_alert',
        'main_power_alert',
        'vibration_sensitivity',
        'vibration_settings',
        'vibration_window',
        'jammer_detection',
        'jammer_relay_action',
        'odometer',
        'hourmeter',
        'defense_settings'
    ]
    
    def __init__(self, configuration_reader_service: ConfigurationReaderService):
        """
        Initialize the unified device communicator.
        
        Args:
            configuration_reader_service: ConfigurationReaderService instance to wrap
        """
        self.config_reader = configuration_reader_service
        self.logger = logging.getLogger(__name__)
        
        # Track operation state
        self.is_reading = False
        self.last_operation_result = None
        self.last_error_message = None
        
    def read_device_configuration(self, progress_callback: Optional[Callable] = None) -> Dict[str, str]:
        """
        Read all device parameters using ConfigurationReaderService.
        
        This method provides a synchronous interface that wraps the asynchronous
        ConfigurationReaderService.read_all_configurations method.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict[str, str]: Dictionary mapping parameter names to their values
            
        Raises:
            RuntimeError: If device communication fails or times out
            ConnectionError: If device connection is not available
            ValueError: If invalid parameters are provided
        """
        if self.is_reading:
            error_msg = "Device configuration reading is already in progress"
            self._log_message(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg)
            
        # Validate that we have a valid configuration reader
        if not self.config_reader:
            error_msg = "ConfigurationReaderService is not available"
            self._log_message(f"ERROR: {error_msg}")
            raise ConnectionError(error_msg)
            
        # Check if device connection is available
        if (hasattr(self.config_reader, 'app') and 
            hasattr(self.config_reader.app, 'serial_service') and
            not self.config_reader.app.serial_service.is_connected):
            error_msg = "Device connection is not available"
            self._log_message(f"ERROR: {error_msg}")
            raise ConnectionError(error_msg)
            
        self.is_reading = True
        self.last_operation_result = None
        self.last_error_message = None
        
        # Result storage for the async operation
        operation_complete = False
        operation_result = None
        operation_error = None
        
        def completion_callback(result: ConfigurationReadResult, error_msg: Optional[str] = None):
            """Handle completion of the async read operation."""
            nonlocal operation_complete, operation_result, operation_error
            operation_result = result
            operation_error = error_msg
            operation_complete = True
            
        def wrapped_progress_callback(progress_info: Dict[str, Any]):
            """Wrap the progress callback to match expected format."""
            if progress_callback:
                try:
                    progress_callback(progress_info)
                except Exception as e:
                    self.logger.warning(f"Progress callback error: {e}")
        
        try:
            # Log the start of the operation
            self._log_message("INFO: Starting unified device configuration read")
            self._log_message(f"DEBUG: Using ConfigurationReaderService for device communication")
            
            # Start the async read operation with comprehensive error handling
            try:
                self.config_reader.read_all_configurations(
                    progress_callback=wrapped_progress_callback,
                    completion_callback=completion_callback,
                    show_progress_dialog=False  # Let the caller handle progress display
                )
            except Exception as e:
                error_msg = f"Failed to start configuration reading: {e}"
                self._log_message(f"ERROR: {error_msg}")
                self.last_error_message = error_msg
                raise RuntimeError(error_msg) from e
            
            # Wait for completion with timeout
            timeout_seconds = 60  # 1 minute timeout
            start_time = time.time()
            
            self._log_message(f"DEBUG: Waiting for operation completion (timeout: {timeout_seconds}s)")
            
            while not operation_complete:
                elapsed_time = time.time() - start_time
                
                if elapsed_time > timeout_seconds:
                    error_msg = f"Device communication timeout after {timeout_seconds} seconds"
                    self._log_message(f"ERROR: {error_msg}")
                    self.last_error_message = error_msg
                    
                    # Try to cancel the operation
                    try:
                        self.cancel_operation()
                    except Exception as cancel_error:
                        self._log_message(f"WARNING: Failed to cancel operation: {cancel_error}")
                        
                    raise RuntimeError(error_msg)
                    
                # Log progress every 10 seconds
                if int(elapsed_time) % 10 == 0 and int(elapsed_time) > 0:
                    self._log_message(f"DEBUG: Operation in progress... ({elapsed_time:.0f}s elapsed)")
                    
                time.sleep(0.1)  # Small delay to prevent busy waiting
                
            # Process the result with comprehensive error handling
            self._log_message("DEBUG: Processing operation result")
            
            if operation_result:
                self.last_operation_result = operation_result
                
                # Log operation statistics
                total_params = operation_result.total_parameters
                successful_params = len([p for p in operation_result.parameters_read if p.success])
                failed_params = len(operation_result.failed_parameters)
                duration = operation_result.read_duration
                
                self._log_message(f"INFO: Operation completed - Total: {total_params}, "
                                f"Success: {successful_params}, Failed: {failed_params}, "
                                f"Duration: {duration:.2f}s")
                
                if operation_result.success:
                    # Convert parameter read results to dictionary format
                    device_responses = {}
                    
                    for param_result in operation_result.parameters_read:
                        if param_result.success and param_result.value is not None:
                            device_responses[param_result.parameter_name] = param_result.value
                            self._log_message(f"DEBUG: Parameter {param_result.parameter_name}: {param_result.value}")
                        elif not param_result.success:
                            self._log_message(f"WARNING: Failed to read {param_result.parameter_name}: "
                                            f"{param_result.error_message or 'Unknown error'}")
                    
                    if device_responses:
                        self._log_message(f"INFO: Successfully read {len(device_responses)} parameters from device")
                        return device_responses
                    else:
                        error_msg = "No parameters were successfully read from device"
                        self._log_message(f"ERROR: {error_msg}")
                        self.last_error_message = error_msg
                        raise RuntimeError(error_msg)
                else:
                    # Operation completed but was not successful
                    error_msg = operation_error or "Device communication completed with errors"
                    self.last_error_message = error_msg
                    self._log_message(f"ERROR: {error_msg}")
                    
                    if operation_result.failed_parameters:
                        failed_list = ', '.join(operation_result.failed_parameters)
                        self._log_message(f"ERROR: Failed parameters: {failed_list}")
                        
                    raise RuntimeError(f"Device communication failed: {error_msg}")
            else:
                # No result received
                error_msg = operation_error or "No result received from device communication"
                self.last_error_message = error_msg
                self._log_message(f"ERROR: {error_msg}")
                raise RuntimeError(error_msg)
                
        except ConnectionError as e:
            self.last_error_message = str(e)
            self._log_message(f"ERROR: Connection error during device configuration read: {e}")
            raise
        except RuntimeError as e:
            self.last_error_message = str(e)
            self._log_message(f"ERROR: Runtime error during device configuration read: {e}")
            raise
        except Exception as e:
            self.last_error_message = str(e)
            self._log_message(f"ERROR: Unexpected exception during device configuration read: {e}")
            # Log the full traceback for debugging
            import traceback
            self._log_message(f"DEBUG: Exception traceback: {traceback.format_exc()}")
            raise RuntimeError(f"Unexpected error during device communication: {e}") from e
            
        finally:
            self.is_reading = False
            self._log_message("DEBUG: Device configuration read operation completed")
            
    def get_current_profile(self) -> Dict[str, Any]:
        """
        Get current device configuration as profile data.
        
        This method reads the device configuration and formats it as profile data
        that can be used by the profile management system.
        
        Returns:
            Dict[str, Any]: Profile data dictionary
            
        Raises:
            RuntimeError: If device communication fails
        """
        try:
            self._log_message("INFO: Reading current device profile")
            
            # Read device configuration
            device_responses = self.read_device_configuration()
            
            # Convert to profile format
            profile_data = {
                'metadata': {
                    'source': 'device',
                    'timestamp': datetime.now().isoformat(),
                    'parameter_count': len(device_responses)
                },
                'parameters': device_responses
            }
            
            self._log_message(f"INFO: Successfully retrieved current profile with {len(device_responses)} parameters")
            return profile_data
            
        except Exception as e:
            error_msg = f"Failed to get current device profile: {e}"
            self._log_message(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg) from e
    
    def cancel_operation(self):
        """Cancel any ongoing device communication operation."""
        try:
            if hasattr(self.config_reader, 'cancel_reading'):
                self.config_reader.cancel_reading()
                self._log_message("INFO: Device communication operation cancelled")
            else:
                self._log_message("WARNING: Cancel operation not supported by ConfigurationReaderService")
        except Exception as e:
            self._log_message(f"WARNING: Failed to cancel operation: {e}")
            
    def get_last_operation_result(self) -> Optional[ConfigurationReadResult]:
        """
        Get the result of the last operation.
        
        Returns:
            ConfigurationReadResult: Last operation result or None if no operation completed
        """
        return self.last_operation_result
        
    def get_last_error_message(self) -> Optional[str]:
        """
        Get the error message from the last failed operation.
        
        Returns:
            str: Last error message or None if no error occurred
        """
        return self.last_error_message
        
    def is_operation_in_progress(self) -> bool:
        """
        Check if a device communication operation is currently in progress.
        
        Returns:
            bool: True if operation is in progress, False otherwise
        """
        return self.is_reading
        
    def _log_message(self, message: str):
        """
        Log a message using the application's logging system.
        
        Args:
            message: Message to log
        """
        try:
            # Try to use the app's log frame if available
            if (hasattr(self.config_reader, 'app') and 
                hasattr(self.config_reader.app, 'log_frame') and 
                self.config_reader.app.log_frame):
                self.config_reader.app.log_frame.log_message(f"{message}\n")
            else:
                # Fallback to standard logging
                if message.startswith("ERROR:"):
                    self.logger.error(message[6:].strip())
                elif message.startswith("WARNING:"):
                    self.logger.warning(message[8:].strip())
                elif message.startswith("INFO:"):
                    self.logger.info(message[5:].strip())
                elif message.startswith("DEBUG:"):
                    self.logger.debug(message[6:].strip())
                else:
                    self.logger.info(message)
                    
        except Exception as e:
            # If logging fails, use standard logging as final fallback
            self.logger.error(f"Failed to log message '{message}': {e}")