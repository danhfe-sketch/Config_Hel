"""
LT32Pro Device Writer

This module provides device writing functionality for LT32Pro devices via USB serial interface.
It handles proper command formatting, response validation, and error handling for writing
device configuration parameters.
"""

import time
import threading
from typing import Dict, Optional, Callable, Any, List
from services.lt32pro_command_formatter import LT32ProCommandFormatter


class LT32ProDeviceWriter:
    """
    Writes configuration to LT32Pro device using proper protocol support.
    
    This class handles the complete device writing process including:
    - Parameter-to-command mapping for device configuration
    - Proper command formatting with ATSMS prefix
    - Response validation and success confirmation
    - Timeout and retry logic for reliable communication
    - Progress tracking for UI integration
    """
    
    # Parameter to command mapping for device configuration
    PARAMETER_COMMAND_MAPPING = {
        # Network configuration
        'apn_server': 'APN',
        'apn_user': 'APN', 
        'apn_password': 'APN',
        'server_ip': 'SERVER',
        'server_port': 'SERVER',
        'server_type': 'SERVER',
        
        # Protocol settings
        'protocol': 'GT06SEL',
        'tcp_ack': 'POSBYACK',
        'tcp_acknowledgment': 'POSBYACK',
        
        # Alternative parameter names
        'apn': 'APN',
        'server': 'SERVER',
        'gt06sel': 'GT06SEL',
        'posbyack': 'POSBYACK'
    }
    
    # Success response patterns for command validation
    SUCCESS_RESPONSE_PATTERNS = {
        'APN': ['SETOK', 'OK', 'APN:'],
        'SERVER': ['SETOK', 'OK', 'SERVER:'],
        'GT06SEL': ['SETOK', 'OK', 'READOK:', 'GT06SEL='],
        'POSBYACK': ['SETOK', 'OK', 'READOK:', 'POSBYACK=']
    }
    
    # Default timeouts and retry settings
    DEFAULT_COMMAND_TIMEOUT = 10  # seconds (longer for write operations)
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0  # seconds
    
    def __init__(self, serial_service, progress_callback: Optional[Callable] = None):
        """
        Initialize the LT32Pro device writer.
        
        Args:
            serial_service: The serial communication service instance
            progress_callback: Optional callback for progress updates
        """
        self.serial_service = serial_service
        self.command_formatter = LT32ProCommandFormatter()
        self.progress_callback = progress_callback
        
        # Response handling
        self._current_response = None
        self._waiting_for_response = False
        self._response_event = threading.Event()
        self._response_timeout = False
        
        # Operation state
        self._operation_cancelled = False
        self._last_error = None
        self._write_results = {}
        
    def write_device_configuration(self, parameters: Dict[str, str], 
                                 progress_callback: Optional[Callable] = None) -> Dict[str, bool]:
        """
        Write configuration parameters to the device.
        
        This method processes the parameters dictionary and sends the appropriate
        commands to configure the device. It handles parameter grouping and
        command sequencing for optimal device communication.
        
        Args:
            parameters: Dictionary of parameter names to values
            progress_callback: Optional callback for progress updates.
                              Called with (current_step, total_steps, step_description, success)
        
        Returns:
            Dictionary mapping parameter names to success status (True/False)
            
        Raises:
            ConnectionError: If device is not connected
            ValueError: If parameters contain invalid values
        """
        if not self.serial_service.is_connected:
            raise ConnectionError("Device is not connected")
            
        if not parameters:
            raise ValueError("No parameters provided for writing")
            
        # Use provided callback or instance callback
        callback = progress_callback or self.progress_callback
        
        # Reset operation state
        self._operation_cancelled = False
        self._last_error = None
        self._write_results = {}
        
        # Group parameters by command type for efficient processing
        command_groups = self._group_parameters_by_command(parameters)
        
        total_commands = len(command_groups)
        current_step = 0
        
        try:
            # Process each command group
            for command_type, param_group in command_groups.items():
                if self._operation_cancelled:
                    raise InterruptedError("Operation was cancelled")
                    
                # Update progress
                if callback:
                    param_names = list(param_group.keys())
                    callback(current_step, total_commands, 
                            f"Writing {command_type} ({', '.join(param_names)})", None)
                
                # Write the command group
                try:
                    success = self._write_command_group(command_type, param_group)
                    
                    # Update results for all parameters in this group
                    for param_name in param_group.keys():
                        self._write_results[param_name] = success
                    
                    # Update progress with result
                    if callback:
                        status_msg = "Success" if success else "Failed"
                        callback(current_step + 1, total_commands, 
                                f"{command_type}: {status_msg}", success)
                        
                except Exception as e:
                    error_msg = f"Error writing {command_type}: {str(e)}"
                    self._last_error = error_msg
                    
                    # Mark all parameters in this group as failed
                    for param_name in param_group.keys():
                        self._write_results[param_name] = False
                    
                    # Update progress with failure
                    if callback:
                        callback(current_step + 1, total_commands, 
                                f"Error writing {command_type}: {str(e)}", False)
                    
                    # Log error but continue with remaining commands
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(f"ERROR: {error_msg}\n")
                
                current_step += 1
                
                # Small delay between command groups to avoid overwhelming the device
                if current_step < total_commands:
                    time.sleep(0.5)
            
            # Final progress update
            if callback:
                success_count = sum(1 for success in self._write_results.values() if success)
                total_params = len(self._write_results)
                callback(total_commands, total_commands, 
                        f"Completed: {success_count}/{total_params} parameters written", 
                        success_count > 0)
            
            return self._write_results.copy()
            
        except Exception as e:
            # Update progress with final error
            if callback:
                callback(total_commands, total_commands, f"Operation failed: {str(e)}", False)
            raise
    
    def write_single_parameter(self, parameter_name: str, value: str, 
                             timeout: int = DEFAULT_COMMAND_TIMEOUT,
                             max_retries: int = DEFAULT_MAX_RETRIES) -> bool:
        """
        Write a single parameter to the device with response validation.
        
        Args:
            parameter_name: Name of the parameter to write
            value: Value to set for the parameter
            timeout: Timeout in seconds for each attempt
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if parameter was written successfully, False otherwise
            
        Raises:
            ConnectionError: If device is not connected
            ValueError: If parameter is not supported or value is invalid
        """
        if not self.serial_service.is_connected:
            raise ConnectionError("Device is not connected")
            
        # Map parameter to command
        command_type = self._get_command_for_parameter(parameter_name)
        if not command_type:
            raise ValueError(f"Unsupported parameter: {parameter_name}")
        
        # Create parameter group for this single parameter
        param_group = {parameter_name: value}
        
        # Write the parameter using command group logic
        return self._write_command_group(command_type, param_group, timeout, max_retries)   
 
    def _group_parameters_by_command(self, parameters: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """
        Group parameters by their corresponding command type.
        
        Args:
            parameters: Dictionary of parameter names to values
            
        Returns:
            Dictionary mapping command types to parameter groups
        """
        command_groups = {}
        
        for param_name, value in parameters.items():
            command_type = self._get_command_for_parameter(param_name)
            
            if command_type:
                if command_type not in command_groups:
                    command_groups[command_type] = {}
                command_groups[command_type][param_name] = value
            else:
                # Log unsupported parameter but continue
                if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                    self.serial_service.app.log_frame.log_message(
                        f"WARNING: Unsupported parameter ignored: {param_name}\n"
                    )
        
        return command_groups
    
    def _get_command_for_parameter(self, parameter_name: str) -> Optional[str]:
        """
        Get the command type for a given parameter name.
        
        Args:
            parameter_name: Name of the parameter
            
        Returns:
            Command type string or None if not supported
        """
        return self.PARAMETER_COMMAND_MAPPING.get(parameter_name.lower())
    
    def _write_command_group(self, command_type: str, param_group: Dict[str, str],
                           timeout: int = DEFAULT_COMMAND_TIMEOUT,
                           max_retries: int = DEFAULT_MAX_RETRIES) -> bool:
        """
        Write a group of parameters that map to the same command type.
        
        Args:
            command_type: The command type to execute
            param_group: Dictionary of parameters for this command
            timeout: Timeout in seconds for each attempt
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if command was executed successfully, False otherwise
        """
        # Build command value based on command type
        command_value = self._build_command_value(command_type, param_group)
        if not command_value:
            return False
        
        # Format the command with ATSMS prefix
        try:
            formatted_command = self.command_formatter.format_write_command(command_type, command_value)
        except ValueError as e:
            if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                self.serial_service.app.log_frame.log_message(
                    f"ERROR: Invalid command format for {command_type}: {str(e)}\n"
                )
            return False
        
        # Validate command syntax
        try:
            self.command_formatter.validate_command_syntax(formatted_command)
        except ValueError as e:
            if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                self.serial_service.app.log_frame.log_message(
                    f"ERROR: Invalid command syntax for {command_type}: {str(e)}\n"
                )
            return False
        
        last_exception = None
        
        # Retry loop
        for attempt in range(max_retries):
            try:
                if self._operation_cancelled:
                    raise InterruptedError("Operation was cancelled")
                
                # Log attempt
                if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                    attempt_msg = f"Attempt {attempt + 1}/{max_retries} for command {command_type}"
                    self.serial_service.app.log_frame.log_message(f"DEBUG: {attempt_msg}\n")
                
                # Setup response capture
                self._setup_response_capture()
                
                # Send the command
                success = self.serial_service.send_command(formatted_command, command_type)
                if not success:
                    raise RuntimeError(f"Failed to send command: {formatted_command}")
                
                # Wait for response with timeout
                response = self._wait_for_response(timeout)
                
                if response:
                    # Validate response for success
                    if self._validate_write_response(command_type, response):
                        return True
                    else:
                        # Invalid or error response
                        error_msg = f"Device returned error for {command_type}: {response}"
                        last_exception = RuntimeError(error_msg)
                        
                        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                            self.serial_service.app.log_frame.log_message(f"WARNING: {error_msg}\n")
                else:
                    # No response received
                    error_msg = f"No response received for command {command_type} (attempt {attempt + 1})"
                    last_exception = TimeoutError(error_msg)
                    
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(f"WARNING: {error_msg}\n")
                
            except Exception as e:
                last_exception = e
                error_msg = f"Error in attempt {attempt + 1} for command {command_type}: {str(e)}"
                
                if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                    self.serial_service.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            
            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                retry_delay = self.DEFAULT_RETRY_DELAY * (2 ** attempt)
                time.sleep(retry_delay)
        
        # All retries failed
        if last_exception:
            if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                self.serial_service.app.log_frame.log_message(
                    f"ERROR: Failed to write {command_type} after {max_retries} attempts: {str(last_exception)}\n"
                )
        
        return False
    
    def _build_command_value(self, command_type: str, param_group: Dict[str, str]) -> Optional[str]:
        """
        Build the command value string based on command type and parameters.
        
        Args:
            command_type: The command type (APN, SERVER, GT06SEL, POSBYACK)
            param_group: Dictionary of parameters for this command
            
        Returns:
            Formatted command value string or None if invalid
        """
        if command_type == 'APN':
            # APN format: server,user,password
            apn_server = param_group.get('apn_server', param_group.get('apn', ''))
            apn_user = param_group.get('apn_user', '')
            apn_password = param_group.get('apn_password', '')
            
            if not apn_server:
                if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                    self.serial_service.app.log_frame.log_message(
                        "ERROR: APN server is required for APN configuration\n"
                    )
                return None
            
            return f"{apn_server},{apn_user},{apn_password}"
            
        elif command_type == 'SERVER':
            # SERVER format: type,ip,port,protocol
            server_ip = param_group.get('server_ip', param_group.get('server', ''))
            server_port = param_group.get('server_port', '8080')  # Default port
            server_type = param_group.get('server_type', '0')     # Default to IP type
            
            if not server_ip:
                if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                    self.serial_service.app.log_frame.log_message(
                        "ERROR: Server IP is required for SERVER configuration\n"
                    )
                return None
            
            return f"{server_type},{server_ip},{server_port},0"  # Protocol always 0 (TCP)
            
        elif command_type == 'GT06SEL':
            # GT06SEL format: protocol value (0, 1, or 2)
            protocol = param_group.get('protocol', param_group.get('gt06sel', ''))
            
            if not protocol:
                if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                    self.serial_service.app.log_frame.log_message(
                        "ERROR: Protocol value is required for GT06SEL configuration\n"
                    )
                return None
            
            return protocol
            
        elif command_type == 'POSBYACK':
            # POSBYACK format: TCP ACK value (0 or 1)
            tcp_ack = param_group.get('tcp_ack', param_group.get('tcp_acknowledgment', param_group.get('posbyack', '')))
            
            if not tcp_ack:
                if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                    self.serial_service.app.log_frame.log_message(
                        "ERROR: TCP ACK value is required for POSBYACK configuration\n"
                    )
                return None
            
            return tcp_ack
        
        return None
    
    def _validate_write_response(self, command_type: str, response: str) -> bool:
        """
        Validate device response for write command success.
        
        Args:
            command_type: The command type that was sent
            response: The response received from the device
            
        Returns:
            True if response indicates success, False otherwise
        """
        if not response or not response.strip():
            return False
        
        response = response.strip().upper()
        
        # Get success patterns for this command type
        success_patterns = self.SUCCESS_RESPONSE_PATTERNS.get(command_type, [])
        
        # Check if response matches any success pattern
        for pattern in success_patterns:
            if pattern.upper() in response:
                return True
        
        # Check for common error patterns
        error_patterns = ['ERROR', 'FAIL', 'INVALID', 'TIMEOUT']
        for error_pattern in error_patterns:
            if error_pattern in response:
                return False
        
        # If no explicit success or error pattern, log for analysis
        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
            self.serial_service.app.log_frame.log_message(
                f"DEBUG: Ambiguous response for {command_type}: {response}\n"
            )
        
        # Default to success if no error patterns found
        return True
    
    def _setup_response_capture(self):
        """Setup response capture mechanism."""
        self._current_response = None
        self._waiting_for_response = True
        self._response_event.clear()
        self._response_timeout = False
        
        # Hook into the serial service's response processing
        if hasattr(self.serial_service, 'process_device_response'):
            # Store original method
            if not hasattr(self, '_original_process_response'):
                self._original_process_response = self.serial_service.process_device_response
            
            # Replace with our wrapper
            self.serial_service.process_device_response = self._capture_response_wrapper
    
    def _capture_response_wrapper(self, response: str):
        """Wrapper for capturing device responses."""
        # Call original processing first
        if hasattr(self, '_original_process_response'):
            self._original_process_response(response)
        
        # Capture response if we're waiting for one
        if self._waiting_for_response:
            self._current_response = response
            self._response_event.set()
    
    def _wait_for_response(self, timeout: int) -> Optional[str]:
        """
        Wait for device response with timeout.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Response string or None if timeout
        """
        # Wait for response event
        if self._response_event.wait(timeout):
            self._waiting_for_response = False
            return self._current_response
        else:
            self._response_timeout = True
            self._waiting_for_response = False
            return None
    
    def cancel_operation(self):
        """Cancel the current writing operation."""
        self._operation_cancelled = True
        self._response_event.set()  # Unblock any waiting threads
    
    def get_last_error(self) -> Optional[str]:
        """Get the last error message from the operation."""
        return self._last_error
    
    def is_operation_cancelled(self) -> bool:
        """Check if the current operation was cancelled."""
        return self._operation_cancelled
    
    def get_write_results(self) -> Dict[str, bool]:
        """Get the results of the last write operation."""
        return self._write_results.copy()
    
    def get_supported_parameters(self) -> List[str]:
        """Get list of supported parameter names."""
        return list(self.PARAMETER_COMMAND_MAPPING.keys())
    
    def get_parameter_command_mapping(self) -> Dict[str, str]:
        """Get the parameter to command mapping."""
        return self.PARAMETER_COMMAND_MAPPING.copy()
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        # Restore original response processing method
        if hasattr(self, '_original_process_response') and hasattr(self.serial_service, 'process_device_response'):
            self.serial_service.process_device_response = self._original_process_response