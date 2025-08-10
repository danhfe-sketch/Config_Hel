"""
Device Communicator - Bridge to existing device communication methods.

This module provides a simple wrapper around the existing device communication
infrastructure to support profile operations. It focuses on parameter-by-parameter
transmission with proper error handling and connection checking.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
import time
import threading
from datetime import datetime


class DeviceCommunicator:
    """Bridge to existing device communication methods for profile operations."""
    
    def __init__(self, app_instance):
        """
        Initialize the device communicator.
        
        Args:
            app_instance: Main application instance with serial service and device mapper
        """
        self.app = app_instance
        self.logger = logging.getLogger(__name__)
        
        # Get references to existing services
        self.serial_service = getattr(app_instance, 'serial_service', None)
        self.device_command_mapper = getattr(app_instance, 'device_command_mapper', None)
        
        # Connection timeout settings
        self.connection_timeout = 5.0  # seconds
        self.parameter_send_delay = 0.5  # delay between parameter sends
        
    def is_device_connected(self) -> bool:
        """
        Check if device is connected and responsive.
        
        Returns:
            bool: True if device is connected, False otherwise
        """
        try:
            if not self.serial_service:
                self.logger.error("Serial service not available")
                return False
                
            # Check basic connection status
            if not self.serial_service.is_connected:
                self.logger.debug("Serial service reports not connected")
                return False
                
            # Check if serial port is available
            if not hasattr(self.serial_service, 'serial_port') or not self.serial_service.serial_port:
                self.logger.debug("Serial port not available")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking device connection: {str(e)}")
            return False
    
    def send_parameter_to_device(self, param_name: str, param_value: str, 
                               additional_params: Optional[Dict[str, str]] = None) -> bool:
        """
        Send a single parameter to the device.
        
        Args:
            param_name: Name of the parameter to send
            param_value: Value of the parameter
            additional_params: Additional parameters needed for command generation
            
        Returns:
            bool: True if parameter was sent successfully, False otherwise
        """
        try:
            # Check device connection first
            if not self.is_device_connected():
                self.logger.error(f"Device not connected - cannot send parameter {param_name}")
                return False
                
            # Check if device command mapper is available
            if not self.device_command_mapper:
                self.logger.error("Device command mapper not available")
                return False
                
            # Prepare parameter values for command generation
            param_values = {param_name: param_value}
            if additional_params:
                param_values.update(additional_params)
                
            # Generate command using device command mapper
            try:
                command = self.device_command_mapper.get_command(param_name, param_values)
                if not command:
                    self.logger.error(f"Could not generate command for parameter: {param_name}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error generating command for {param_name}: {str(e)}")
                return False
            
            # Send command to device
            try:
                success = self.serial_service.send_command(command, param_name)
                if success:
                    self.logger.debug(f"Successfully sent parameter {param_name} = {param_value}")
                    # Add small delay between parameter sends
                    time.sleep(self.parameter_send_delay)
                    return True
                else:
                    self.logger.error(f"Failed to send command for parameter {param_name}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error sending command for {param_name}: {str(e)}")
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error sending parameter {param_name}: {str(e)}")
            return False
    
    def get_parameter_from_device(self, param_name: str) -> Optional[str]:
        """
        Get a parameter value from the device.
        
        Args:
            param_name: Name of the parameter to retrieve
            
        Returns:
            str: Parameter value if successful, None otherwise
        """
        try:
            # Check device connection first
            if not self.is_device_connected():
                self.logger.error(f"Device not connected - cannot get parameter {param_name}")
                return None
                
            # Check if device command mapper is available
            if not self.device_command_mapper:
                self.logger.error("Device command mapper not available")
                return None
                
            # Generate query command
            try:
                query_command = self.device_command_mapper.get_query_command(param_name)
                if not query_command:
                    self.logger.error(f"Could not generate query command for parameter: {param_name}")
                    return None
                    
            except Exception as e:
                self.logger.error(f"Error generating query command for {param_name}: {str(e)}")
                return None
            
            # Send query command and wait for response
            # Note: This is a simplified implementation
            # In a real implementation, you would need to handle response parsing
            try:
                success = self.serial_service.send_command(query_command, f"query_{param_name}")
                if success:
                    # For now, return a placeholder - actual response parsing would be needed
                    self.logger.debug(f"Query sent for parameter {param_name}")
                    return "query_sent"  # Placeholder
                else:
                    self.logger.error(f"Failed to send query for parameter {param_name}")
                    return None
                    
            except Exception as e:
                self.logger.error(f"Error querying parameter {param_name}: {str(e)}")
                return None
                
        except Exception as e:
            self.logger.error(f"Unexpected error getting parameter {param_name}: {str(e)}")
            return None
    
    def send_multiple_parameters(self, parameters: Dict[str, str], 
                               progress_callback: Optional[callable] = None) -> Tuple[bool, List[str]]:
        """
        Send multiple parameters to the device with progress tracking.
        
        Args:
            parameters: Dictionary of parameter names and values
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Tuple[bool, List[str]]: (success, list of failed parameters)
        """
        failed_parameters = []
        total_params = len(parameters)
        processed_params = 0
        
        try:
            # Check device connection first
            if not self.is_device_connected():
                self.logger.error("Device not connected - cannot send parameters")
                return False, list(parameters.keys())
            
            # Send parameters one by one
            for param_name, param_value in parameters.items():
                try:
                    # Update progress if callback provided
                    if progress_callback:
                        progress_callback(processed_params, total_params, param_name)
                    
                    # Send parameter
                    success = self.send_parameter_to_device(param_name, param_value)
                    
                    if not success:
                        failed_parameters.append(param_name)
                        self.logger.warning(f"Failed to send parameter: {param_name}")
                    
                    processed_params += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing parameter {param_name}: {str(e)}")
                    failed_parameters.append(param_name)
                    processed_params += 1
            
            # Final progress update
            if progress_callback:
                progress_callback(processed_params, total_params, "Complete")
            
            # Determine overall success
            success = len(failed_parameters) == 0
            
            if success:
                self.logger.info(f"Successfully sent all {total_params} parameters to device")
            else:
                self.logger.warning(f"Sent {total_params - len(failed_parameters)}/{total_params} parameters successfully")
            
            return success, failed_parameters
            
        except Exception as e:
            self.logger.error(f"Unexpected error sending multiple parameters: {str(e)}")
            return False, list(parameters.keys())
    
    def get_multiple_parameters(self, param_names: List[str], 
                              progress_callback: Optional[callable] = None) -> Tuple[Dict[str, str], List[str]]:
        """
        Get multiple parameter values from the device.
        
        Args:
            param_names: List of parameter names to retrieve
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Tuple[Dict[str, str], List[str]]: (retrieved parameters, failed parameter names)
        """
        retrieved_parameters = {}
        failed_parameters = []
        total_params = len(param_names)
        processed_params = 0
        
        try:
            # Check device connection first
            if not self.is_device_connected():
                self.logger.error("Device not connected - cannot get parameters")
                return {}, param_names
            
            # Get parameters one by one
            for param_name in param_names:
                try:
                    # Update progress if callback provided
                    if progress_callback:
                        progress_callback(processed_params, total_params, param_name)
                    
                    # Get parameter
                    param_value = self.get_parameter_from_device(param_name)
                    
                    if param_value is not None:
                        retrieved_parameters[param_name] = param_value
                    else:
                        failed_parameters.append(param_name)
                        self.logger.warning(f"Failed to get parameter: {param_name}")
                    
                    processed_params += 1
                    
                except Exception as e:
                    self.logger.error(f"Error getting parameter {param_name}: {str(e)}")
                    failed_parameters.append(param_name)
                    processed_params += 1
            
            # Final progress update
            if progress_callback:
                progress_callback(processed_params, total_params, "Complete")
            
            self.logger.info(f"Retrieved {len(retrieved_parameters)}/{total_params} parameters from device")
            
            return retrieved_parameters, failed_parameters
            
        except Exception as e:
            self.logger.error(f"Unexpected error getting multiple parameters: {str(e)}")
            return {}, param_names
    
    def test_device_communication(self) -> Tuple[bool, str]:
        """
        Test device communication by sending a simple command.
        
        Returns:
            Tuple[bool, str]: (success, status message)
        """
        try:
            # Check basic connection
            if not self.is_device_connected():
                return False, "Device not connected"
            
            # Try to send a simple status command
            if not self.serial_service or not self.device_command_mapper:
                return False, "Required services not available"
            
            try:
                # Send a simple status query
                status_command = self.device_command_mapper.get_command('get_status', {})
                if status_command:
                    success = self.serial_service.send_command(status_command, 'get_status')
                    if success:
                        return True, "Device communication test successful"
                    else:
                        return False, "Failed to send test command"
                else:
                    return False, "Could not generate test command"
                    
            except Exception as e:
                return False, f"Communication test failed: {str(e)}"
                
        except Exception as e:
            self.logger.error(f"Error testing device communication: {str(e)}")
            return False, f"Test error: {str(e)}"
    
    def get_device_info(self) -> Dict[str, str]:
        """
        Get basic device information (IMEI, version, etc.).
        
        Returns:
            Dict[str, str]: Device information
        """
        device_info = {}
        
        try:
            if not self.is_device_connected():
                return device_info
            
            # Get device info from serial service if available
            if hasattr(self.serial_service, 'device_info'):
                device_info.update(self.serial_service.device_info)
            
            return device_info
            
        except Exception as e:
            self.logger.error(f"Error getting device info: {str(e)}")
            return device_info