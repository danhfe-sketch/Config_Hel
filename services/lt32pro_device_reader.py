"""
LT32Pro Device Reader

This module provides device reading functionality for LT32Pro devices via USB serial interface.
It handles proper command sequencing, response validation, and error handling for reading
device configuration parameters.
"""

import time
import threading
from typing import Dict, Optional, Callable, Any
from services.lt32pro_command_formatter import LT32ProCommandFormatter


class LT32ProDeviceReader:
    """
    Reads configuration from LT32Pro device using proper protocol support.
    
    This class handles the complete device reading process including:
    - Proper command sequencing with ATSMS prefix
    - Response validation and error handling
    - Timeout and retry logic for reliable communication
    - Progress tracking for UI integration
    """
    
    # Standard command sequence for reading device configuration
    READ_COMMAND_SEQUENCE = [
        'STATUS',    # Device status and connectivity
        'APN',       # APN configuration
        'SERVER',    # Server configuration
        'IMEI',      # Device IMEI
        'ICCID',     # SIM card ICCID
        'GT06SEL',   # Protocol selection
        'POSBYACK',  # TCP acknowledgment setting
        'VERSION',   # Firmware version
        'TIMER',     # Report intervals
        'HBT',       # Heartbeat intervals
        'ACCLINE',   # Ignition type
        'SPEED',     # Speed alert
        'SLPDISCONNECT',  # Sleep mode
        'SLEEPT',        # Sleep time
        'ANGLEVALUE',     # Angle report
        'BATALM',    # Backup battery alert
        'POWERALM',  # Main power alert
        'VIBL',  # Vibration sensitivity
        'JAMMER',    # Jammer detection
        'JAMRELAY',   # Jammer relay action
        'MILEAGE',   # Odometer
        'ACCONT'     # Hourmeter
    ]
    
    # Default timeouts and retry settings
    DEFAULT_COMMAND_TIMEOUT = 5  # seconds
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0  # seconds
    
    def __init__(self, serial_service, progress_callback: Optional[Callable] = None):
        """
        Initialize the LT32Pro device reader.
        
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
        
    def read_device_configuration(self, progress_callback: Optional[Callable] = None) -> Dict[str, str]:
        """
        Read all configuration parameters from the device.
        
        This method executes the complete command sequence to read all device
        parameters and returns them as a dictionary of raw responses.
        
        Args:
            progress_callback: Optional callback for progress updates.
                              Called with (current_step, total_steps, step_description, success)
        
        Returns:
            Dictionary mapping command names to device responses
            
        Raises:
            ConnectionError: If device is not connected
            TimeoutError: If device communication times out
            ValueError: If device returns invalid responses
        """
        if not self.serial_service.is_connected:
            raise ConnectionError("Device is not connected")
            
        # Use provided callback or instance callback
        callback = progress_callback or self.progress_callback
        
        # Initialize results dictionary
        device_responses = {}
        total_commands = len(self.READ_COMMAND_SEQUENCE)
        
        # Reset operation state
        self._operation_cancelled = False
        self._last_error = None
        
        try:
            # Execute each command in sequence
            for i, command in enumerate(self.READ_COMMAND_SEQUENCE):
                if self._operation_cancelled:
                    raise InterruptedError("Operation was cancelled")
                    
                # Update progress
                if callback:
                    callback(i, total_commands, f"Reading {command}", None)
                
                # Read single parameter with retry logic
                try:
                    response = self.read_single_parameter(
                        command, 
                        timeout=self.DEFAULT_COMMAND_TIMEOUT,
                        max_retries=self.DEFAULT_MAX_RETRIES
                    )
                    
                    if response:
                        device_responses[command] = response
                        
                        # Update progress with success
                        if callback:
                            callback(i + 1, total_commands, f"Read {command}: {response[:50]}...", True)
                    else:
                        # Handle empty response
                        error_msg = f"Empty response for command {command}"
                        self._last_error = error_msg
                        
                        # Update progress with failure
                        if callback:
                            callback(i + 1, total_commands, f"Failed to read {command}", False)
                            
                        # Continue with other commands but log the issue
                        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                            self.serial_service.app.log_frame.log_message(f"WARNING: {error_msg}\n")
                            
                except Exception as e:
                    error_msg = f"Error reading {command}: {str(e)}"
                    self._last_error = error_msg
                    
                    # Update progress with failure
                    if callback:
                        callback(i + 1, total_commands, f"Error reading {command}: {str(e)}", False)
                    
                    # Log error but continue with remaining commands
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(f"ERROR: {error_msg}\n")
                
                # Small delay between commands to avoid overwhelming the device (except after last command)
                if i < total_commands - 1:
                    time.sleep(0.2)
            
            # Final progress update
            if callback:
                success_count = len(device_responses)
                callback(total_commands, total_commands, 
                        f"Completed: {success_count}/{total_commands} parameters read", 
                        success_count > 0)
            
            return device_responses
            
        except Exception as e:
            # Update progress with final error
            if callback:
                callback(total_commands, total_commands, f"Operation failed: {str(e)}", False)
            raise
    
    def read_single_parameter(self, command: str, timeout: int = DEFAULT_COMMAND_TIMEOUT,
                            max_retries: int = DEFAULT_MAX_RETRIES) -> Optional[str]:
        """
        Read a single parameter from the device with timeout and retry logic.
        Includes fallback to alternative commands for better device compatibility.
        
        Args:
            command: The command to send (without ATSMS prefix)
            timeout: Timeout in seconds for each attempt
            max_retries: Maximum number of retry attempts
            
        Returns:
            Device response string, or None if failed
            
        Raises:
            ConnectionError: If device is not connected
            ValueError: If command is not supported
            TimeoutError: If all retry attempts timeout
        """
        if not self.serial_service.is_connected:
            raise ConnectionError("Device is not connected")
            
        if not self.command_formatter.is_read_command_supported(command):
            raise ValueError(f"Unsupported read command: {command}")
        
        # Try primary command first, then alternatives if available
        commands_to_try = [command]
        if self.command_formatter.has_alternative_commands(command):
            alternatives = self.command_formatter.get_alternative_read_commands(command)
            # Extract command names from full command strings
            for alt in alternatives:
                if alt.startswith('CXCS#') or alt.startswith('SZCS#'):
                    # Extract the parameter name after the prefix
                    alt_command = alt.replace('CXCS#', '').replace('SZCS#', '').split('=')[0]
                    if alt_command not in commands_to_try:
                        commands_to_try.append(alt_command)
                elif alt.endswith('#'):
                    # Simple command like STATUS#, PARAM#
                    alt_command = alt.replace('#', '')
                    if alt_command not in commands_to_try:
                        commands_to_try.append(alt_command)
        
        # DIAGNOSTIC LOGGING: Log command strategy
        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
            self.serial_service.app.log_frame.log_message(
                f"DEBUG: Will try commands in order: {commands_to_try}\n"
            )
        
        # Try each command in sequence
        for cmd_index, current_command in enumerate(commands_to_try):
            try:
                result = self._try_single_command(current_command, timeout, max_retries)
                if result:
                    # DIAGNOSTIC LOGGING: Log successful command
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        success_msg = f"SUCCESS: Command '{current_command}' worked"
                        if cmd_index > 0:
                            success_msg += f" (fallback from '{command}')"
                        self.serial_service.app.log_frame.log_message(f"DEBUG: {success_msg}\n")
                    return result
                else:
                    # DIAGNOSTIC LOGGING: Log failed command
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: Command '{current_command}' failed, trying next alternative\n"
                        )
            except Exception as e:
                # DIAGNOSTIC LOGGING: Log command exception
                if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                    self.serial_service.app.log_frame.log_message(
                        f"DEBUG: Command '{current_command}' threw exception: {str(e)}\n"
                    )
                continue
        
        # All commands failed
        raise TimeoutError(f"Failed to read parameter using any of these commands: {commands_to_try}")
    
    def _try_single_command(self, command: str, timeout: int, max_retries: int) -> Optional[str]:
        """
        Try a single command with retry logic.
        
        Args:
            command: The command to send (without ATSMS prefix)
            timeout: Timeout in seconds for each attempt
            max_retries: Maximum number of retry attempts
            
        Returns:
            Device response string, or None if failed
        """
        # Format the command with ATSMS prefix
        formatted_command = self.command_formatter.format_read_command(command)
        
        # DIAGNOSTIC LOGGING: Log the exact command being sent
        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
            self.serial_service.app.log_frame.log_message(
                f"DEBUG: Sending command '{command}' as '{formatted_command}'\n"
            )
        
        # Validate command syntax
        self.command_formatter.validate_command_syntax(formatted_command)
        
        last_exception = None
        
        # Retry loop
        for attempt in range(max_retries):
            try:
                if self._operation_cancelled:
                    raise InterruptedError("Operation was cancelled")
                
                # Log attempt
                if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                    attempt_msg = f"Attempt {attempt + 1}/{max_retries} for command {command}"
                    self.serial_service.app.log_frame.log_message(f"DEBUG: {attempt_msg}\n")
                
                # Setup response capture
                self._setup_response_capture()
                
                # Send the command
                success = self.serial_service.send_command(formatted_command, command)
                if not success:
                    raise RuntimeError(f"Failed to send command: {formatted_command}")
                
                # DIAGNOSTIC LOGGING: Log command send status
                if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                    self.serial_service.app.log_frame.log_message(
                        f"DEBUG: Command sent successfully: {formatted_command}\n"
                    )
                
                # Wait for response with timeout
                response = self._wait_for_response(timeout)
                
                # DIAGNOSTIC LOGGING: Log raw response
                if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                    if response:
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: Raw response for {command}: '{response}'\n"
                        )
                    else:
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: No response received for {command} within {timeout}s timeout\n"
                        )
                
                if response:
                    # Validate response format
                    if self._validate_response(command, response):
                        # DIAGNOSTIC LOGGING: Log successful validation
                        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                            self.serial_service.app.log_frame.log_message(
                                f"DEBUG: Response validation passed for {command}\n"
                            )
                        return response
                    else:
                        # Invalid response format, but we got something
                        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                            self.serial_service.app.log_frame.log_message(
                                f"WARNING: Invalid response format for {command}: {response}\n"
                            )
                        # Return the response anyway for further processing
                        return response
                else:
                    # No response received
                    error_msg = f"No response received for command {command} (attempt {attempt + 1})"
                    last_exception = TimeoutError(error_msg)
                    
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(f"WARNING: {error_msg}\n")
                
            except Exception as e:
                last_exception = e
                error_msg = f"Error in attempt {attempt + 1} for command {command}: {str(e)}"
                
                if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                    self.serial_service.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            
            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                retry_delay = self.DEFAULT_RETRY_DELAY * (2 ** attempt)
                time.sleep(retry_delay)
        
        # All retries failed for this command
        return None
    
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
    
    def _validate_response(self, command: str, response: str) -> bool:
        """
        Validate device response format for the given command.
        
        Args:
            command: The command that was sent
            response: The response received
            
        Returns:
            True if response format is valid
        """
        if not response or not response.strip():
            return False
        
        response = response.strip()
        
        # Basic validation patterns for different command types
        validation_patterns = {
            'STATUS': lambda r: 'Battery:' in r or 'GPRS:' in r or 'GSM' in r,
            'APN': lambda r: r.startswith('APN:'),
            'SERVER': lambda r: r.startswith('SERVER:'),
            'IMEI': lambda r: 'IMEI=' in r or 'READOK:' in r or (len(r.replace(' ', '').replace(':', '')) >= 15 and r.isdigit()),
            'ICCID': lambda r: 'ICCID=' in r or 'READOK:' in r or (len(r.replace(' ', '').replace(':', '')) >= 19 and r.isdigit()),
            'GT06SEL': lambda r: 'GT06SEL=' in r or 'READOK:' in r or (r.isdigit() and len(r) == 1),
            'POSBYACK': lambda r: 'POSBYACK=' in r or 'READOK:' in r or (r.isdigit() and len(r) == 1),
            'VERSION': lambda r: 'LT32Pro' in r or ('V' in r and '.' in r),
            'TIMER': lambda r: 'ACC ON:' in r and 'ACC OFF:' in r,
            'HBT': lambda r: 'ACC ON:' in r and 'ACC OFF:' in r,
            'ACCLINE': lambda r: 'ACCLINE=' in r or 'ACC_CFG=' in r or 'READOK:' in r,
            'SPEED': lambda r: r.startswith('SPEED:'),
            'SLPDISCONNECT': lambda r: 'SLPDISCONNECT=' in r or 'READOK:' in r,
            'SLEEPT': lambda r: 'SLEEPT=' in r or 'READOK:' in r,
            'ANGLEVALUE': lambda r: 'ANGLEVALUE=' in r or 'READOK:' in r,
            'BATALM': lambda r: r.startswith('BATALM:'),
            'POWERALM': lambda r: r.startswith('POWERALM:'),
            'VIBL': lambda r: 'VIBL=' in r or 'READOK:' in r,
            'JAMMER': lambda r: r.startswith('JAMMER:'),
            'JAMRELAY': lambda r: r.startswith('JAMRELAY:'),
            'MILEAGE': lambda r: 'Cur Mileage Value:' in r,
            'ACCONT': lambda r: 'Get ACC ON Time:' in r
        }
        
        # Get validation function for command
        validator = validation_patterns.get(command)
        if validator:
            try:
                return validator(response)
            except Exception:
                # If validation fails, assume response is invalid
                return False
        
        # If no specific validator, assume response is valid if not empty
        return True
    
    def cancel_operation(self):
        """Cancel the current reading operation."""
        self._operation_cancelled = True
        self._response_event.set()  # Unblock any waiting threads
    
    def get_last_error(self) -> Optional[str]:
        """Get the last error message from the operation."""
        return self._last_error
    
    def is_operation_cancelled(self) -> bool:
        """Check if the current operation was cancelled."""
        return self._operation_cancelled
    
    def get_supported_commands(self) -> list:
        """Get list of supported read commands."""
        return self.command_formatter.get_supported_read_commands()
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        # Restore original response processing method
        if hasattr(self, '_original_process_response') and hasattr(self.serial_service, 'process_device_response'):
            self.serial_service.process_device_response = self._original_process_response