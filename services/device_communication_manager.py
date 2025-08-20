"""
Device Communication Manager for the LT32 PRO Universal Profile System.

This module provides a unified interface for device communication that integrates
with existing device reader/writer services and uses parameter specifications
for command formatting and response parsing.
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime

from models.parameter_spec import ParameterSpec, ParameterCommands
from models.operation_result import ProfileOperationResult, ParameterOperationResult, OperationType
from services.parameter_specification_parser import ParameterSpecificationParser
from services.lt32pro_device_reader import LT32ProDeviceReader
from services.lt32pro_device_writer import LT32ProDeviceWriter


class DeviceCommunicationManager:
    """
    Manages device communication for reading and writing parameters using
    the Parameter UI List specifications.
    
    This class provides a unified interface that integrates with existing
    device services while using parameter specifications for proper command
    formatting and response parsing.
    """
    
    def __init__(self, serial_service, spec_parser: ParameterSpecificationParser):
        """
        Initialize the device communication manager.
        
        Args:
            serial_service: The serial communication service instance
            spec_parser: Parameter specification parser instance
        """
        self.serial_service = serial_service
        self.spec_parser = spec_parser
        
        # Initialize device reader and writer
        self.device_reader = LT32ProDeviceReader(serial_service)
        self.device_writer = LT32ProDeviceWriter(serial_service)
        
        # Operation state
        self._operation_cancelled = False
        self._current_operation: Optional[str] = None
    
    async def read_all_parameters(self, progress_callback: Optional[Callable] = None) -> Dict[str, str]:
        """
        Read all parameters from the device based on parameter specifications.
        
        Args:
            progress_callback: Optional callback for progress updates
                              Called with (current_step, total_steps, step_description, success)
        
        Returns:
            Dict[str, str]: Dictionary mapping parameter names to raw device responses
            
        Raises:
            ConnectionError: If device is not connected
            RuntimeError: If operation fails
        """
        if not self.serial_service.is_connected:
            raise ConnectionError("Device is not connected")
        
        self._operation_cancelled = False
        self._current_operation = "read_all_parameters"
        
        try:
            # Get all parameter specifications
            all_specs = self.spec_parser.parse_specifications()
            
            # Filter parameters that have read commands
            readable_params = []
            for param_name, spec in all_specs.items():
                if self._has_read_command(spec):
                    readable_params.append((param_name, spec))
            
            if not readable_params:
                return {}
            
            total_params = len(readable_params)
            device_responses = {}
            
            # Read each parameter
            for i, (param_name, spec) in enumerate(readable_params):
                if self._operation_cancelled:
                    break
                
                # Update progress
                if progress_callback:
                    progress_callback(i, total_params, f"Reading {param_name}", None)
                
                try:
                    # Get the read command for this parameter
                    read_command = self._get_read_command(spec)
                    if read_command:
                        # Execute the read command
                        response = await self._execute_read_command(read_command, param_name)
                        if response:
                            device_responses[param_name] = response
                            
                            # Update progress with success
                            if progress_callback:
                                progress_callback(i + 1, total_params, 
                                                f"Read {param_name}: {response[:50]}...", True)
                        else:
                            # Update progress with failure
                            if progress_callback:
                                progress_callback(i + 1, total_params, 
                                                f"Failed to read {param_name}", False)
                    
                except Exception as e:
                    # Log error but continue with other parameters
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"ERROR: Failed to read {param_name}: {str(e)}\n"
                        )
                    
                    # Update progress with failure
                    if progress_callback:
                        progress_callback(i + 1, total_params, 
                                        f"Error reading {param_name}: {str(e)}", False)
                
                # Small delay between commands
                if i < total_params - 1:
                    await asyncio.sleep(0.3)
            
            # Final progress update
            if progress_callback:
                success_count = len(device_responses)
                progress_callback(total_params, total_params, 
                                f"Completed: {success_count}/{total_params} parameters read", 
                                success_count > 0)
            
            return device_responses
            
        finally:
            self._current_operation = None
    
    async def write_all_parameters(self, parameters: Dict[str, Any], 
                                 progress_callback: Optional[Callable] = None) -> Dict[str, bool]:
        """
        Write all parameters to the device based on parameter specifications.
        
        Args:
            parameters: Dictionary mapping parameter names to values
            progress_callback: Optional callback for progress updates
                              Called with (current_step, total_steps, step_description, success)
        
        Returns:
            Dict[str, bool]: Dictionary mapping parameter names to success status
            
        Raises:
            ConnectionError: If device is not connected
            ValueError: If parameters contain invalid values
        """
        if not self.serial_service.is_connected:
            raise ConnectionError("Device is not connected")
        
        if not parameters:
            raise ValueError("No parameters provided for writing")
        
        self._operation_cancelled = False
        self._current_operation = "write_all_parameters"
        
        try:
            # Get parameter specifications for validation and command formatting
            all_specs = self.spec_parser.parse_specifications()
            
            # Filter parameters that have write commands and validate values
            # Be tolerant of parameter keys that include section prefixes (e.g. 'network_parameters.server_settings')
            writable_params = []
            for param_name, value in parameters.items():
                # Try exact lookup first
                spec = all_specs.get(param_name)
                used_param_key = param_name
                # Fallback: try short name (after last dot) or any spec that endswith the name
                if spec is None:
                    short_name = param_name.split('.')[-1]
                    spec = all_specs.get(short_name)
                    if spec:
                        used_param_key = short_name
                    else:
                        # As a last resort, try any key that endswith the short_name
                        for key, s in all_specs.items():
                            if key.endswith("." + short_name) or key.endswith(short_name):
                                spec = s
                                used_param_key = key
                                break
                if spec and self._has_write_command(spec):
                    # Validate parameter value
                    try:
                        validation_result = spec.validate_value(value)
                    except Exception:
                        # If spec validation raises, treat it as invalid and log
                        validation_result = None
                    if validation_result and validation_result.is_valid:
                        writable_params.append((param_name, value, spec))
                    elif validation_result is None:
                        # Log unexpected validation exception
                        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                            self.serial_service.app.log_frame.log_message(
                                f"ERROR: Exception while validating {param_name} against spec {spec.name}\n"
                            )
                    else:
                        # Log validation error
                        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                            error_msg = f"Validation failed for {param_name}: {', '.join(validation_result.errors)}"
                            self.serial_service.app.log_frame.log_message(f"ERROR: {error_msg}\n")
            
            if not writable_params:
                return {}
            
            total_params = len(writable_params)
            write_results = {}
            
            # Write each parameter
            for i, (param_name, value, spec) in enumerate(writable_params):
                if self._operation_cancelled:
                    break
                
                # Update progress
                if progress_callback:
                    progress_callback(i, total_params, f"Writing {param_name}", None)
                
                try:
                    # Debug: log parameter being written
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        try:
                            self.serial_service.app.log_frame.log_message(
                                f"DEBUG: Preparing to write parameter '{param_name}' with value: {repr(value)} and spec: {getattr(spec, 'name', 'unknown')}\n"
                            )
                        except Exception:
                            pass
                    else:
                        print(f"DEBUG: Preparing to write parameter '{param_name}' with value: {repr(value)} and spec: {getattr(spec, 'name', 'unknown')}")
    
                    # Format and execute the write command
                    success = await self._execute_write_command(spec, param_name, value)
                    write_results[param_name] = success
    
                    # Update progress with result
                    if progress_callback:
                        status_msg = "Success" if success else "Failed"
                        progress_callback(i + 1, total_params,
                                        f"{param_name}: {status_msg}", success)
    
                except Exception as e:
                    write_results[param_name] = False
    
                    # Log error
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"ERROR: Failed to write {param_name}: {str(e)}\n"
                        )
    
                    # Update progress with failure
                    if progress_callback:
                        progress_callback(i + 1, total_params,
                                        f"Error writing {param_name}: {str(e)}", False)
                
                # Small delay between commands
                if i < total_params - 1:
                    await asyncio.sleep(0.5)
            
            # Final progress update
            if progress_callback:
                success_count = sum(1 for success in write_results.values() if success)
                progress_callback(total_params, total_params, 
                                f"Completed: {success_count}/{total_params} parameters written", 
                                success_count > 0)
            
            return write_results
            
        finally:
            self._current_operation = None
    
    def parse_device_response(self, command: str, response: str, param_spec: ParameterSpec) -> Optional[Dict[str, Any]]:
        """
        Parse device response based on parameter specifications.
        
        Args:
            command: The command that was sent
            response: Raw device response string
            param_spec: Parameter specification for parsing context
            
        Returns:
            Optional[Dict[str, Any]]: Parsed parameter values or None if parsing fails
        """
        if not response or not response.strip():
            return None
        
        response = response.strip()
        
        try:
            # Use basic parsing directly since ParameterCommands.parse_read_response
            # is not properly implemented for our specific response formats
            return self._parse_response_basic(response, param_spec)
            
        except Exception as e:
            if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                self.serial_service.app.log_frame.log_message(
                    f"WARNING: Failed to parse response for {param_spec.name}: {str(e)}\n"
                )
            return None
    
    def format_parameter_for_device(self, param_spec: ParameterSpec, value: Any) -> Optional[str]:
        """
        Format parameter value for device command using DeviceCommandMapper.
        
        Args:
            param_spec: Parameter specification
            value: Parameter value to format
            
        Returns:
            Optional[str]: Formatted device command or None if formatting fails
        """
        try:
            # Use DeviceCommandMapper for proper value mapping and command generation
            from services.device_command_mapper import DeviceCommandMapper
            mapper = DeviceCommandMapper()
            
            # Prepare the value in the format expected by DeviceCommandMapper
            if param_spec.fields and isinstance(value, dict):
                # Complex parameter with multiple fields
                # Check if value has nested structure with 'value' key (from profile files)
                if 'value' in value and isinstance(value['value'], dict):
                    # Extract the actual field values from the nested structure
                    prepared_value = value['value']
                else:
                    # Value is already in the correct format
                    prepared_value = value
            else:
                # Simple parameter - extract value if it's nested
                if isinstance(value, dict) and 'value' in value:
                    prepared_value = value['value']
                else:
                    prepared_value = value
            
            # Generate command using DeviceCommandMapper
            # Keep the full command (including ATSMS: prefix) so the serial layer sends exactly what the mapper produced.
            full_command = mapper.get_command(param_spec.name, prepared_value, validate_command=False)
            if not full_command:
                return None
            # Debug/log the full generated command so we can trace what is actually sent
            try:
                if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                    self.serial_service.app.log_frame.log_message(
                        f"DEBUG: Formatted full command for {param_spec.name}: {full_command}\n"
                    )
                else:
                    print(f"DEBUG: Formatted full command for {param_spec.name}: {full_command}")
            except Exception:
                # Ignore logging errors
                pass
            return full_command
                    
        except Exception as e:
            if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                self.serial_service.app.log_frame.log_message(
                    f"ERROR: Failed to format parameter {param_spec.name}: {str(e)}\n"
                )
            return None
    
    def cancel_operation(self) -> None:
        """Cancel the current operation."""
        self._operation_cancelled = True
        
        # Cancel underlying operations
        if hasattr(self.device_reader, 'cancel_operation'):
            self.device_reader.cancel_operation()
        if hasattr(self.device_writer, 'cancel_operation'):
            self.device_writer.cancel_operation()
    
    def is_operation_cancelled(self) -> bool:
        """Check if the current operation was cancelled."""
        return self._operation_cancelled
    
    def get_current_operation(self) -> Optional[str]:
        """Get the name of the current operation."""
        return self._current_operation
    
    def get_supported_parameters(self) -> List[str]:
        """
        Get list of parameters supported by the device.
        
        Returns:
            List[str]: List of supported parameter names
        """
        try:
            all_specs = self.spec_parser.parse_specifications()
            supported = []
            
            for param_name, spec in all_specs.items():
                if self._has_read_command(spec) or self._has_write_command(spec):
                    supported.append(param_name)
            
            return supported
            
        except Exception:
            return []
    
    def _has_read_command(self, spec: ParameterSpec) -> bool:
        """Check if parameter specification has a read command."""
        return (spec.commands.read_command is not None or 
                spec.commands.read_level is not None)
    
    def _has_write_command(self, spec: ParameterSpec) -> bool:
        """Check if parameter specification has a write command."""
        return (spec.commands.set_command is not None or 
                spec.commands.set_physical is not None or
                spec.commands.set_accelerometer is not None or
                spec.commands.set_battery is not None or
                spec.commands.set_level is not None)
    
    def _get_read_command(self, spec: ParameterSpec) -> Optional[str]:
        """Get the appropriate read command for a parameter specification."""
        if spec.commands.read_command:
            return spec.commands.read_command
        elif spec.commands.read_level:
            return spec.commands.read_level
        return None
    
    async def _execute_read_command(self, command: str, param_name: str) -> Optional[str]:
        """
        Execute a read command and return the response.
        
        Args:
            command: Command to execute
            param_name: Parameter name for logging
            
        Returns:
            Optional[str]: Device response or None if failed
        """
        try:
            # HACK: Extract the base command from the formatted command string to maintain
            # compatibility with the LT32ProDeviceReader, which expects a base command.
            parts = command.split('#')
            if len(parts) > 1 and (parts[0] == 'CXCS' or parts[0] == 'SZCS'):
                # For commands like "CXCS#ACCLINE#ACC_CFG", the base command is "ACCLINE"
                base_command = parts[1]
            else:
                # For commands like "APN#", the base command is "APN"
                base_command = command.rstrip('#')

            # Use the existing device reader with the extracted base command
            response = self.device_reader.read_single_parameter(
                base_command,
                timeout=self.device_reader.DEFAULT_COMMAND_TIMEOUT,
                max_retries=2  # Reduce retries for faster operation
            )
            
            return response
            
        except Exception as e:
            if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                self.serial_service.app.log_frame.log_message(
                    f"ERROR: Failed to execute read command for {param_name}: {str(e)}\n"
                )
            return None
    
    async def _execute_write_command(self, spec: ParameterSpec, param_name: str, value: Any) -> bool:
        """
        Execute a write command for a parameter.
        
        Args:
            spec: Parameter specification
            param_name: Parameter name
            value: Value to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Format the command using parameter specification
            formatted_command = self.format_parameter_for_device(spec, value)
            if not formatted_command:
                return False
            
            # For now, use the serial service directly since the existing writer
            # has hardcoded parameter mappings that don't match our specifications
            success = self.serial_service.send_command(formatted_command, param_name)
            
            if success:
                # Wait a bit for the response and check if it indicates success
                await asyncio.sleep(3.0) # Increased timeout
                # For now, assume success if command was sent successfully
                # This could be enhanced with response validation
                return True
            
            return False
            
        except Exception as e:
            if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                self.serial_service.app.log_frame.log_message(
                    f"ERROR: Failed to execute write command for {param_name}: {str(e)}\n"
                )
            return False
    
    def _map_response_to_fields(self, parsed_data: Dict[str, Any], param_spec: ParameterSpec) -> Dict[str, Any]:
        """
        Map parsed response data to parameter fields.
        
        Args:
            parsed_data: Raw parsed data from response
            param_spec: Parameter specification for field mapping
            
        Returns:
            Dict[str, Any]: Mapped field values
        """
        if not param_spec.fields:
            # Simple parameter, return as-is
            return parsed_data
        
        # Map to field names
        mapped_data = {}
        
        # Try to map based on field order
        field_values = list(parsed_data.values())
        for i, field in enumerate(param_spec.fields):
            if i < len(field_values):
                mapped_data[field.name] = field_values[i]
        
        return mapped_data
    
    def _parse_response_basic(self, response: str, param_spec: ParameterSpec) -> Dict[str, Any]:
        """
        Basic response parsing fallback.
        
        Args:
            response: Raw device response
            param_spec: Parameter specification
            
        Returns:
            Dict[str, Any]: Parsed values
        """
        # Remove common prefixes and suffixes
        clean_response = response.strip().rstrip('#')
        
        # Handle different response formats based on parameter type
        if param_spec.name == "apn_settings":
            # APN format: "APN:server,user,password"
            if clean_response.startswith("APN:"):
                parts = clean_response[4:].split(',')
                return {
                    "apn": parts[0] if len(parts) > 0 else "",
                    "user": parts[1] if len(parts) > 1 else "",
                    "password": parts[2] if len(parts) > 2 else ""
                }
        elif param_spec.name == "server_settings":
            # SERVER format: "SERVER:type,address,port,protocol"
            if clean_response.startswith("SERVER:"):
                parts = clean_response[7:].split(',')
                return {
                    "address": parts[1] if len(parts) > 1 else "",
                    "port": parts[2] if len(parts) > 2 else ""
                }
        elif param_spec.name == "protocol":
            # Protocol format: "GT06SEL=X"
            if "GT06SEL=" in clean_response:
                value = clean_response.split("=")[1]
                return {"protocol": value}
        elif param_spec.name == "tcp_ack":
            # TCP ACK format: "POSBYACK=X"
            if "POSBYACK=" in clean_response:
                value = clean_response.split("=")[1]
                return {"tcp_ack": value}
        elif param_spec.name == "odometer":
            # Odometer formats:
            # - "MILEAGE=XXXXX" (direct format)
            # - "Cur Mileage Value:XXXXKM" (verbose format)
            if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                self.serial_service.app.log_frame.log_message(
                    f"DEBUG: Parsing odometer response: '{clean_response}'\n"
                )
            
            if clean_response.startswith("MILEAGE="):
                value = clean_response[8:]  # Remove "MILEAGE=" prefix
                # Validate that it's numeric
                try:
                    int(value)
                    result = {"odometer": value}
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: Parsed odometer from MILEAGE format: {result}\n"
                        )
                    return result
                except ValueError:
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: Invalid odometer value in MILEAGE format: '{value}'\n"
                        )
                    return {"odometer": "0"}  # Default to 0 for invalid values
            elif "Cur Mileage Value:" in clean_response:
                # Extract value from "Cur Mileage Value:XXXXKM"
                parts = clean_response.split(":")
                if len(parts) >= 2:
                    value_part = parts[1]
                    # Remove "KM" suffix if present
                    value = value_part.replace("KM", "").strip()
                    # Validate that it's numeric
                    try:
                        int(value)
                        result = {"odometer": value}
                        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                            self.serial_service.app.log_frame.log_message(
                                f"DEBUG: Parsed odometer from verbose format: {result}\n"
                            )
                        return result
                    except ValueError:
                        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                            self.serial_service.app.log_frame.log_message(
                                f"DEBUG: Invalid odometer value in verbose format: '{value}'\n"
                            )
                        return {"odometer": "0"}  # Default to 0 for invalid values
                else:
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: Malformed odometer response in verbose format: '{clean_response}'\n"
                        )
                    return {"odometer": "0"}  # Default to 0
            else:
                # Try to extract any numeric value
                import re
                numbers = re.findall(r'\d+', clean_response)
                if numbers:
                    result = {"odometer": numbers[-1]}  # Use last number found
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: Parsed odometer using fallback extraction: {result}\n"
                        )
                    return result
                else:
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: No numeric values found in odometer response: '{clean_response}'\n"
                        )
                    return {"odometer": "0"}  # Default to 0
        elif param_spec.name == "hourmeter":
            # Hourmeter formats:
            # - "ACCONT=XXXXX" (direct format)
            # - "Get ACC ON Time:XXXX Minute" (verbose format)
            if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                self.serial_service.app.log_frame.log_message(
                    f"DEBUG: Parsing hourmeter response: '{clean_response}'\n"
                )
            
            if clean_response.startswith("ACCONT="):
                value = clean_response[7:]  # Remove "ACCONT=" prefix
                # Validate that it's numeric
                try:
                    int(value)
                    result = {"hourmeter": value}
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: Parsed hourmeter from ACCONT format: {result}\n"
                        )
                    return result
                except ValueError:
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: Invalid hourmeter value in ACCONT format: '{value}'\n"
                        )
                    return {"hourmeter": "0"}  # Default to 0 for invalid values
            elif "Get ACC ON Time:" in clean_response:
                # Extract value from "Get ACC ON Time:XXXX Minute"
                parts = clean_response.split(":")
                if len(parts) >= 2:
                    value_part = parts[1]
                    # Remove "Minute" suffix if present
                    value = value_part.replace("Minute", "").strip()
                    # Validate that it's numeric
                    try:
                        int(value)
                        result = {"hourmeter": value}
                        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                            self.serial_service.app.log_frame.log_message(
                                f"DEBUG: Parsed hourmeter from verbose format: {result}\n"
                            )
                        return result
                    except ValueError:
                        if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                            self.serial_service.app.log_frame.log_message(
                                f"DEBUG: Invalid hourmeter value in verbose format: '{value}'\n"
                            )
                        return {"hourmeter": "0"}  # Default to 0 for invalid values
                else:
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: Malformed hourmeter response in verbose format: '{clean_response}'\n"
                        )
                    return {"hourmeter": "0"}  # Default to 0
            else:
                # Try to extract any numeric value
                import re
                numbers = re.findall(r'\d+', clean_response)
                if numbers:
                    result = {"hourmeter": numbers[-1]}  # Use last number found
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: Parsed hourmeter using fallback extraction: {result}\n"
                        )
                    return result
                else:
                    if hasattr(self.serial_service, 'app') and hasattr(self.serial_service.app, 'log_frame'):
                        self.serial_service.app.log_frame.log_message(
                            f"DEBUG: No numeric values found in hourmeter response: '{clean_response}'\n"
                        )
                    return {"hourmeter": "0"}  # Default to 0
        
        # Default: return the whole response as a single value
        return {"value": clean_response}