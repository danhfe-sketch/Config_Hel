"""
LT32ProDeviceReader - Minimal implementation that uses ConfigurationReaderService.

This is a wrapper around ConfigurationReaderService to provide the interface
expected by DeviceCommunicationManager while using the fixed odometer parsing logic.
"""

from services.configuration_reader_service import ConfigurationReaderService
from services.i18n_service import I18nService
from typing import Optional


class LT32ProDeviceReader:
    """Device reader that wraps ConfigurationReaderService for compatibility."""
    
    DEFAULT_COMMAND_TIMEOUT = 5.0
    
    def __init__(self, serial_service):
        """Initialize the device reader."""
        self.serial_service = serial_service
        
        # Use existing configuration reader from serial service if available
        if hasattr(serial_service, 'configuration_reader') and serial_service.configuration_reader is not None:
            self.config_reader = serial_service.configuration_reader
        else:
            # Fallback: Create ConfigurationReaderService instance
            if hasattr(serial_service, 'app'):
                app_instance = serial_service.app
                if hasattr(app_instance, 'i18n'):
                    i18n_service = app_instance.i18n
                else:
                    i18n_service = I18nService()
            else:
                # Create a minimal app-like object
                app_instance = type('MockApp', (), {
                    'serial_service': serial_service,
                    'parameters_frame': None
                })()
                i18n_service = I18nService()
            
            self.config_reader = ConfigurationReaderService(app_instance, i18n_service)
    
    def read_single_parameter(self, command: str, timeout: float = None, max_retries: int = 2) -> str:
        """
        Read a single parameter from the device.
        
        Args:
            command: Command to send (e.g., 'MILEAGE')
            timeout: Timeout for the operation (ignored, uses config reader defaults)
            max_retries: Maximum number of retries
            
        Returns:
            str: Raw device response or empty string if failed
        """
        try:
            # Use the ConfigurationReaderService approach which has the fixed
            # response capture mechanism and proper waiting flag handling
            if hasattr(self.config_reader, '_send_command_and_wait'):
                # Use the direct method with proper response capture
                response = self.config_reader._send_command_and_wait(command, timeout=timeout or 5.0)
                
                if response:
                    # Log successful read
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: LT32ProDeviceReader successfully read {command}: {response}\n"
                        )
                    
                    # Parse the response to extract just the numeric value for odometer/hourmeter
                    parsed_value = self._extract_numeric_value_from_response(command, response)
                    return parsed_value if parsed_value is not None else response
                else:
                    # Log the issue
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"WARNING: LT32ProDeviceReader failed to read {command} - no response\n"
                        )
                    return ""
            else:
                # Fallback approach: use the direct serial service method
                if hasattr(self.serial_service, 'send_command') and hasattr(self.serial_service, 'response_buffer'):
                    # Clear any existing responses
                    self.serial_service.response_buffer.clear()
                    
                    # Format the command like ConfigurationReaderService does
                    if hasattr(self.config_reader, 'command_formatter'):
                        if self.config_reader.command_formatter.is_read_command_supported(command):
                            formatted_command = self.config_reader.command_formatter.format_read_command(command)
                        else:
                            formatted_command = f"ATSMS:{command}#"
                    else:
                        formatted_command = f"ATSMS:{command}#"
                    
                    # Send the command
                    success = self.serial_service.send_command(formatted_command, command)
                    
                    if success:
                        # Wait a bit for the response
                        import time
                        time.sleep(1.0)  # Give device time to respond
                        
                        # Check if we got a response
                        if self.serial_service.response_buffer:
                            # Get the most recent response
                            response = self.serial_service.response_buffer[-1]
                            
                            # Log successful read
                            if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                                self.serial_service.app.log_frame.log_message(
                                    f"DEBUG: LT32ProDeviceReader successfully read {command}: {response}\n"
                                )
                            
                            # Parse the response to extract just the numeric value for odometer/hourmeter
                            parsed_value = self._extract_numeric_value_from_response(command, response)
                            return parsed_value if parsed_value is not None else response
                        else:
                            # No response in buffer
                            if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                                self.serial_service.app.log_frame.log_message(
                                    f"WARNING: LT32ProDeviceReader - no response in buffer for {command}\n"
                                )
                            return ""
                    else:
                        # Failed to send command
                        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                            self.serial_service.app.log_frame.log_message(
                                f"WARNING: LT32ProDeviceReader failed to send command {command}\n"
                            )
                        return ""
                else:
                    # Final fallback - return empty string
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"WARNING: LT32ProDeviceReader - no suitable method available for {command}\n"
                        )
                    return ""
                
        except Exception as e:
            # Log the error if possible
            if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                self.serial_service.app.log_frame.log_message(
                    f"ERROR: Exception in LT32ProDeviceReader.read_single_parameter({command}): {str(e)}\n"
                )
            return ""

    def _extract_numeric_value_from_response(self, command: str, response: str) -> Optional[str]:
        """
        Extract numeric value from device response for odometer and hourmeter parameters.
        
        Args:
            command: Command that was sent
            response: Raw device response
            
        Returns:
            str: Extracted numeric value or None if not applicable
        """
        try:
            # Handle odometer responses
            if command == 'MILEAGE':
                # Response formats:
                # - "Cur Mileage Value:28KM"
                # - "MILEAGE=28"
                clean_response = response.strip()
                
                if "Cur Mileage Value:" in clean_response:
                    # Extract value from "Cur Mileage Value:XXXXKM"
                    parts = clean_response.split(":")
                    if len(parts) >= 2:
                        value_part = parts[1]
                        # Remove "KM" suffix if present
                        value = value_part.replace("KM", "").strip()
                        # Validate that it's numeric
                        try:
                            int(value)
                            return value
                        except ValueError:
                            return None
                elif clean_response.startswith("MILEAGE="):
                    # Extract value from "MILEAGE=XXXX"
                    value = clean_response[8:]  # Remove "MILEAGE=" prefix
                    # Validate that it's numeric
                    try:
                        int(value)
                        return value
                    except ValueError:
                        return None
            
            # Handle hourmeter responses
            elif command == 'ACCONT':
                # Response formats:
                # - "Get ACC ON Time:367 Minute"
                # - "ACCONT=367"
                clean_response = response.strip()
                
                if "Get ACC ON Time:" in clean_response:
                    # Extract value from "Get ACC ON Time:XXXX Minute"
                    parts = clean_response.split(":")
                    if len(parts) >= 2:
                        value_part = parts[1]
                        # Remove "Minute" suffix if present
                        value = value_part.replace("Minute", "").strip()
                        # Validate that it's numeric
                        try:
                            int(value)
                            return value
                        except ValueError:
                            return None
                elif clean_response.startswith("ACCONT="):
                    # Extract value from "ACCONT=XXXX"
                    value = clean_response[7:]  # Remove "ACCONT=" prefix
                    # Validate that it's numeric
                    try:
                        int(value)
                        return value
                    except ValueError:
                        return None
            
            # For other parameters, return None to indicate no special handling needed
            return None
            
        except Exception as e:
            if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                self.serial_service.app.log_frame.log_message(
                    f"DEBUG: Failed to extract numeric value from {command} response '{response}': {str(e)}\n"
                )
            return None