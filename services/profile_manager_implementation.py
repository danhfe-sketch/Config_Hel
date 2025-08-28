"""
Profile Manager - Manages bidirectional profile operations for LT32Pro device configurations.

This module provides functionality for:
1. Loading configuration from device and saving to profile file
2. Loading configuration from profile file and deploying to device
3. Validating profile file format and content
4. Error handling for profile operations
"""

import os
import re
import time
import threading
import configparser
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable, Tuple


@dataclass
class ValidationResult:
    """Result of validating a profile file."""
    is_valid: bool
    error_message: str
    error_code: str = None


@dataclass
class ProfileOperationResult:
    """Result of a profile operation (device-to-profile or profile-to-device)."""
    success: bool
    operation_type: str  # 'profile_to_device' or 'device_to_profile'
    profile_path: str
    parameters_processed: int
    failed_parameters: List[str]
    error_message: Optional[str]
    operation_duration: float
    timestamp: datetime


@dataclass
class DeploymentResult:
    """Result of deploying a profile to a device."""
    success: bool
    commands_sent: int
    successful_commands: int
    failed_commands: List[str]
    deployment_log: List[str]
    ui_updates_applied: bool
    error_details: Optional[Dict[str, str]] = None


class ProfileManager:
    """Manages bidirectional profile operations for LT32Pro device configurations."""

    def __init__(self, app_instance):
        """
        Initialize the profile manager.
        
        Args:
            app_instance: Main application instance
        """
        self.app = app_instance
        self.i18n = app_instance.i18n_service if hasattr(app_instance, 'i18n_service') else None
        self.profile_version = '1.0'  # Current profile format version
        self.is_operation_running = False
        self.operation_thread = None
        self.cancel_requested = False
        self.progress_callback = None
        self.completion_callback = None
        
        # Parameter to section mapping for organizing profile data
        self.parameter_to_section = {
            # APN Configuration
            'apn_server': 'APN_Configuration',
            'apn_user': 'APN_Configuration',
            'apn_password': 'APN_Configuration',
            'transmission_mode': 'APN_Configuration',
            
            # Server Configuration
            'server_ip': 'Server_Configuration',
            'server_port': 'Server_Configuration',
            'server_protocol': 'Server_Configuration',
            'backup_server_ip': 'Server_Configuration',
            'backup_server_port': 'Server_Configuration',
            'gt06_protocol': 'Server_Configuration',
            
            # Timer Settings
            'timer_ign_on': 'Timer_Settings',
            'timer_ign_off': 'Timer_Settings',
            'heartbeat_ign_on': 'Timer_Settings',
            'heartbeat_ign_off': 'Timer_Settings',
            'heartbeat_interval': 'Timer_Settings',
            
            # Device Parameters
            'vibration': 'Device_Parameters',
            'sensitivity': 'Device_Parameters',
            'lock_type': 'Device_Parameters',
            'ignition_type': 'Device_Parameters',
            'curve_sensor': 'Device_Parameters',
            
            # Alert Settings
            'movement_alert': 'Alert_Settings',
            'power_alert': 'Alert_Settings',
            'battery_alert': 'Alert_Settings',
            'speed_limit': 'Alert_Settings',
            'moving_alert': 'Alert_Settings',
            'acc_on_alert': 'Alert_Settings',
            'acc_off_alert': 'Alert_Settings',
            
            # Advanced Settings
            'sleep_mode': 'Advanced_Settings',
            'sleep_time': 'Advanced_Settings',
            'network_select': 'Advanced_Settings',
            'defense_time': 'Advanced_Settings',
            'vibration_window': 'Advanced_Settings',
            'blind_speed': 'Advanced_Settings',
            'angle_reporting': 'Advanced_Settings',
            'relay_gps_check': 'Advanced_Settings'
        }
        
        # Default values for parameters (used when creating new profiles)
        self.default_values = {
            'apn_server': '',
            'apn_user': '',
            'apn_password': '',
            'transmission_mode': 'TCP',
            'server_ip': '',
            'server_port': '8080',
            'server_protocol': 'TCP',
            'gt06_protocol': 'GT06-0x60',
            'timer_ign_on': '30',
            'timer_ign_off': '300',
            'heartbeat_ign_on': '60',
            'heartbeat_ign_off': '300',
            'vibration': '128',
            'sensitivity': '5',
            'lock_type': 'PIN',
            'ignition_type': 'Digital',
            'curve_sensor': 'Auto',
            'sleep_mode': 'Disabled',
            'network_select': 'AUTO'
        }

    def load_from_device_to_profile(self, profile_path: str,
                                  progress_callback: Optional[Callable] = None,
                                  completion_callback: Optional[Callable] = None) -> None:
        """
        Load configuration from device and save to profile file.
        
        Args:
            profile_path: Path where the profile file should be saved
            progress_callback: Optional callback for progress updates (current, total, status)
            completion_callback: Optional callback when operation is complete (result)
        """
        if self.is_operation_running:
            error_msg = self.i18n.get('profile_operation_already_running', 
                                    'Profile operation is already in progress')
            if completion_callback:
                result = ProfileOperationResult(
                    success=False,
                    operation_type='device_to_profile',
                    profile_path=profile_path,
                    parameters_processed=0,
                    failed_parameters=[],
                    error_message=error_msg,
                    operation_duration=0.0,
                    timestamp=datetime.now()
                )
                completion_callback(result)
            return
        
        # Validate connection
        connection_validation = self.validate_connection_required()
        if not connection_validation.is_valid:
            if completion_callback:
                result = ProfileOperationResult(
                    success=False,
                    operation_type='device_to_profile',
                    profile_path=profile_path,
                    parameters_processed=0,
                    failed_parameters=[],
                    error_message=connection_validation.error_message,
                    operation_duration=0.0,
                    timestamp=datetime.now()
                )
                completion_callback(result)
            return
        
        # Validate profile path for writing
        if profile_path:
            directory = os.path.dirname(profile_path)
            # Check if directory is writable
            if directory and not os.access(directory, os.W_OK):
                error_message = self.i18n.get('profile_directory_not_writable', 
                                           'Directory is not writable: {directory}').format(directory=directory)
                if completion_callback:
                    result = ProfileOperationResult(
                        success=False,
                        operation_type='device_to_profile',
                        profile_path=profile_path,
                        parameters_processed=0,
                        failed_parameters=[],
                        error_message=error_message,
                        operation_duration=0.0,
                        timestamp=datetime.now()
                    )
                    completion_callback(result)
                return
        
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.cancel_requested = False
        self.is_operation_running = True
        
        # Start operation in a separate thread
        self.operation_thread = threading.Thread(
            target=self._device_to_profile_worker,
            args=(profile_path,),
            daemon=True
        )
        self.operation_thread.start()

    def _device_to_profile_worker(self, profile_path: str) -> None:
        """
        Worker thread for device-to-profile operation.
        
        Args:
            profile_path: Path where the profile file should be saved
        """
        start_time = time.time()
        parameters_processed = 0
        failed_parameters = []
        success = False
        error_msg = None
        
        try:
            self._log_message(f"INFO: Starting device-to-profile operation: {profile_path}")
            
            # Check if ConfigurationReaderService is available
            if not hasattr(self.app, 'configuration_reader_service'):
                error_msg = self.i18n.get('profile_config_reader_not_available', 
                                        'Configuration reader service is not available')
                raise ValueError(error_msg)
            
            # Step 1: Read configuration from device
            if self.progress_callback:
                self.app.after(0, self.progress_callback, 1, 4, 
                             self.i18n.get('profile_reading_device', 'Reading device configuration...'))
            
            # Use ConfigurationReaderService to read all parameters
            config_reader = self.app.configuration_reader_service
            
            # Create a temporary completion callback to capture the read result
            read_result = [None]
            read_error = [None]
            read_completed = [False]
            
            def read_completion_callback(result, error=None):
                read_result[0] = result
                read_error[0] = error
                read_completed[0] = True
            
            # Start reading configuration
            config_reader.read_all_configurations(
                completion_callback=read_completion_callback,
                show_progress_dialog=False
            )
            
            # Wait for reading to complete
            max_wait_time = 60  # Maximum wait time in seconds
            wait_start = time.time()
            while not read_completed[0] and (time.time() - wait_start) < max_wait_time:
                time.sleep(0.1)
                
                # Check for cancellation
                if self.cancel_requested:
                    self._log_message("INFO: Device-to-profile operation canceled by user")
                    if hasattr(config_reader, 'cancel_reading'):
                        config_reader.cancel_reading()
                    break
            
            # Check if reading completed
            if not read_completed[0]:
                error_msg = self.i18n.get('profile_read_timeout', 
                                        'Timeout waiting for device configuration')
                raise TimeoutError(error_msg)
            
            # Check if reading was successful
            if not read_result[0] or not read_result[0].success:
                error_msg = read_error[0] or self.i18n.get('profile_read_failed', 
                                                         'Failed to read device configuration')
                raise ValueError(error_msg)
            
            # Step 2: Convert device configuration to profile data
            if self.progress_callback:
                self.app.after(0, self.progress_callback, 2, 4, 
                             self.i18n.get('profile_processing_data', 'Processing configuration data...'))
            
            # Extract device information
            device_info = {}
            
            # First, look for specific device info parameters
            for param_result in read_result[0].parameters_read:
                if param_result.parameter_name == 'device_info' and param_result.success:
                    # Parse raw response for IMEI and other device info
                    if 'IMEI' in param_result.raw_response:
                        match = re.search(r'IMEI[=:]\s*(\d+)', param_result.raw_response)
                        if match:
                            device_info['imei'] = match.group(1)
                    
                    if 'VERSION' in param_result.raw_response or 'version' in param_result.raw_response.lower():
                        device_info['version'] = param_result.raw_response.strip()
            
            # Also check for IMEI in get_imei parameter
            for param_result in read_result[0].parameters_read:
                if param_result.parameter_name == 'get_imei' and param_result.success:
                    if param_result.value:
                        device_info['imei'] = param_result.value
                    elif 'IMEI' in param_result.raw_response:
                        match = re.search(r'IMEI[=:]\s*(\d+)', param_result.raw_response)
                        if match:
                            device_info['imei'] = match.group(1)
            
            # Check for version in get_version parameter
            for param_result in read_result[0].parameters_read:
                if param_result.parameter_name == 'get_version' and param_result.success:
                    if param_result.value:
                        device_info['version'] = param_result.value
                    else:
                        device_info['version'] = param_result.raw_response.strip()
            
            # Check for ICCID in get_iccid parameter
            for param_result in read_result[0].parameters_read:
                if param_result.parameter_name == 'get_iccid' and param_result.success:
                    if param_result.value:
                        device_info['iccid'] = param_result.value
                    elif 'ICCID' in param_result.raw_response:
                        match = re.search(r'ICCID[=:]\s*(\d+)', param_result.raw_response)
                        if match:
                            device_info['iccid'] = match.group(1)
            
            # Convert read parameters to configuration data
            config_data = {}
            for param_result in read_result[0].parameters_read:
                if param_result.success and param_result.value is not None:
                    param_name = param_result.parameter_name
                    config_data[param_name] = param_result.value
                    parameters_processed += 1
                    self._log_message(f"DEBUG: Successfully read parameter {param_name}: {param_result.value}")
                elif not param_result.success:
                    failed_parameters.append(param_result.parameter_name)
                    self._log_message(f"WARNING: Failed to read parameter {param_result.parameter_name}: {param_result.error_message}")
            
            # Handle special case for APN parameters
            for param_result in read_result[0].parameters_read:
                if param_result.parameter_name == 'apn_config' and param_result.success:
                    # Parse APN components from raw response
                    if 'APN:' in param_result.raw_response:
                        try:
                            # Extract the part after "APN:"
                            apn_part = param_result.raw_response.split('APN:', 1)[1].strip()
                            # Split by comma to get server, user, password
                            apn_components = apn_part.split(',')
                            if len(apn_components) >= 1:
                                config_data['apn_server'] = apn_components[0].strip()
                            if len(apn_components) >= 2:
                                config_data['apn_user'] = apn_components[1].strip()
                            if len(apn_components) >= 3:
                                # Remove trailing # if present
                                password = apn_components[2].strip()
                                if password.endswith('#'):
                                    password = password[:-1]
                                config_data['apn_password'] = password
                            self._log_message(f"DEBUG: Parsed APN components - server: {config_data.get('apn_server', '')}, user: {config_data.get('apn_user', '')}, password: {config_data.get('apn_password', '')}")
                        except Exception as e:
                            self._log_message(f"WARNING: Failed to parse APN components: {str(e)}")
            
            # Handle special case for server parameters
            for param_result in read_result[0].parameters_read:
                if param_result.parameter_name == 'server_config' and param_result.success:
                    # Parse server components from raw response
                    if 'SERVER:' in param_result.raw_response:
                        try:
                            # Extract the part after "SERVER:"
                            server_part = param_result.raw_response.split('SERVER:', 1)[1].strip()
                            # Split by comma to get type, address, port, protocol
                            server_components = server_part.split(',')
                            if len(server_components) >= 4:
                                server_type = server_components[0].strip()
                                server_address = server_components[1].strip()
                                server_port = server_components[2].strip()
                                server_protocol = server_components[3].strip()
                                
                                # Store server parameters based on type (0=IP, 1=domain)
                                if server_type == '0':
                                    config_data['server_ip'] = server_address
                                else:
                                    config_data['server_domain'] = server_address
                                
                                config_data['server_port'] = server_port
                                
                                # Map protocol value to protocol name
                                protocol_map = {'0': 'TCP', '1': 'UDP'}
                                if server_protocol in protocol_map:
                                    config_data['transmission_mode'] = protocol_map[server_protocol]
                                
                                self._log_message(f"DEBUG: Parsed server components - address: {server_address}, port: {server_port}, protocol: {server_protocol}")
                        except Exception as e:
                            self._log_message(f"WARNING: Failed to parse server components: {str(e)}")
            
            # Handle special case for protocol settings
            for param_result in read_result[0].parameters_read:
                if param_result.parameter_name == 'protocol_settings' and param_result.success:
                    # Parse protocol value
                    if 'GT06SEL=' in param_result.raw_response:
                        try:
                            match = re.search(r'GT06SEL=(\d+)', param_result.raw_response)
                            if match:
                                protocol_value = match.group(1)
                                # Map protocol value to protocol name
                                protocol_map = {'0': 'GT06-0x60', '1': 'CRX3', '2': 'GT06-0x12'}
                                if protocol_value in protocol_map:
                                    config_data['gt06_protocol'] = protocol_map[protocol_value]
                                    self._log_message(f"DEBUG: Parsed protocol setting: {config_data['gt06_protocol']}")
                        except Exception as e:
                            self._log_message(f"WARNING: Failed to parse protocol setting: {str(e)}")
            
            # Step 3: Create profile file content
            if self.progress_callback:
                self.app.after(0, self.progress_callback, 3, 4, 
                             self.i18n.get('profile_creating_file', 'Creating profile file...'))
            
            # Generate profile text
            profile_text = self.create_profile_from_device_config(config_data, device_info)
            
            # Step 4: Write profile file
            if self.progress_callback:
                self.app.after(0, self.progress_callback, 4, 4, 
                             self.i18n.get('profile_saving_file', 'Saving profile file...'))
            
            # Write the profile file
            if self.write_profile_file(profile_path, profile_text):
                success = True
                self._log_message(f"INFO: Profile file created successfully: {profile_path}")
            else:
                error_msg = self.i18n.get('profile_write_failed', 
                                        'Failed to write profile file: {path}').format(path=profile_path)
                raise IOError(error_msg)
            
        except Exception as e:
            error_msg = str(e)
            self._log_message(f"ERROR: Device-to-profile operation failed: {error_msg}")
        
        finally:
            # Create result
            result = ProfileOperationResult(
                success=success,
                operation_type='device_to_profile',
                profile_path=profile_path,
                parameters_processed=parameters_processed,
                failed_parameters=failed_parameters,
                error_message=error_msg,
                operation_duration=time.time() - start_time,
                timestamp=datetime.now()
            )
            
            # Call completion callback
            if self.completion_callback:
                self.app.after(0, self.completion_callback, result)
            
            self.is_operation_running = False

    def create_profile_from_device_config(self, config_data: Dict[str, Any], 
                                        device_info: Dict[str, Any] = None) -> str:
        """
        Create INI-formatted profile text from device configuration data.
        
        Args:
            config_data: Dictionary containing device configuration data
            device_info: Optional dictionary containing device information (IMEI, etc.)
            
        Returns:
            INI-formatted profile text
        """
        # Create ConfigParser object
        config = configparser.ConfigParser()
        config.optionxform = str  # Preserve case in option names
        
        # Add profile information section
        config.add_section('Profile_Info')
        config.set('Profile_Info', 'version', self.profile_version)
        config.set('Profile_Info', 'created_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        config.set('Profile_Info', 'profile_name', f"LT32Pro_Config_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Add device information if available
        if device_info:
            if 'imei' in device_info:
                config.set('Profile_Info', 'device_imei', device_info['imei'])
            
            if 'version' in device_info:
                config.set('Profile_Info', 'firmware_version', device_info['version'])
                
            if 'iccid' in device_info:
                config.set('Profile_Info', 'device_iccid', device_info['iccid'])
        
        # Organize parameters into sections
        section_data = {}
        
        # Organize parameters by section
        for param_name, param_value in config_data.items():
            section_name = self.parameter_to_section.get(param_name, 'Device_Parameters')
            
            if section_name not in section_data:
                section_data[section_name] = {}
            
            section_data[section_name][param_name] = param_value
        
        # Add sections to config in a specific order for better organization
        section_order = [
            'APN_Configuration',
            'Server_Configuration',
            'Timer_Settings',
            'Device_Parameters',
            'Alert_Settings',
            'Advanced_Settings'
        ]
        
        # First add sections in the preferred order
        for section_name in section_order:
            if section_name in section_data:
                # Convert section name to proper INI section name
                ini_section_name = self._section_name_to_ini(section_name)
                config.add_section(ini_section_name)
                
                # Add parameters to section
                for param_name, param_value in section_data[section_name].items():
                    config.set(ini_section_name, param_name, str(param_value))
                
                # Remove processed section
                del section_data[section_name]
        
        # Add any remaining sections that weren't in the preferred order
        for section_name in section_data:
            # Convert section name to proper INI section name
            ini_section_name = self._section_name_to_ini(section_name)
            config.add_section(ini_section_name)
            
            # Add parameters to section
            for param_name, param_value in section_data[section_name].items():
                config.set(ini_section_name, param_name, str(param_value))
        
        # Convert to INI-formatted text with comments
        return self._config_to_string_with_comments(config, device_info)

    def _config_to_string_with_comments(self, config: configparser.ConfigParser, 
                                      device_info: Dict[str, Any] = None) -> str:
        """
        Convert ConfigParser to string with helpful comments.
        
        Args:
            config: ConfigParser object
            device_info: Optional dictionary containing device information
            
        Returns:
            INI-formatted text with comments
        """
        lines = []
        
        # Add header comment
        lines.append("# LT32Pro Configuration Profile")
        lines.append(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if device_info:
            if 'imei' in device_info:
                lines.append(f"# Device IMEI: {device_info['imei']}")
            if 'version' in device_info:
                lines.append(f"# Firmware Version: {device_info['version']}")
            if 'iccid' in device_info:
                lines.append(f"# Device ICCID: {device_info['iccid']}")
        
        lines.append("")
        lines.append("# This file contains device configuration parameters read directly from the LT32Pro device.")
        lines.append("# It can be edited manually or loaded back to the device using the 'Load Profile to Device' option.")
        lines.append("")
        
        # Parameter documentation dictionary
        param_docs = {
            # APN Configuration
            'apn_server': 'APN server name for cellular connectivity',
            'apn_user': 'APN username (leave empty if not required)',
            'apn_password': 'APN password (leave empty if not required)',
            'transmission_mode': 'Data transmission protocol (TCP or UDP)',
            
            # Server Configuration
            'server_ip': 'Main server IP address',
            'server_domain': 'Main server domain name',
            'server_port': 'Main server port number',
            'backup_server_ip': 'Backup server IP address',
            'backup_server_port': 'Backup server port number',
            'gt06_protocol': 'Protocol type (GT06-0x60, GT06-0x12, or CRX3)',
            
            # Timer Settings
            'timer_ign_on': 'Reporting interval in seconds when ignition is ON',
            'timer_ign_off': 'Reporting interval in seconds when ignition is OFF',
            'heartbeat_ign_on': 'Heartbeat interval in seconds when ignition is ON',
            'heartbeat_ign_off': 'Heartbeat interval in seconds when ignition is OFF',
            'heartbeat_interval': 'General heartbeat interval in seconds',
            
            # Device Parameters
            'vibration': 'Vibration sensitivity level (0-255)',
            'sensitivity': 'General sensitivity level (1-10)',
            'lock_type': 'Security lock type (PIN or Card)',
            'ignition_type': 'Ignition detection type (Digital or Analog)',
            'curve_sensor': 'Curve sensor mode (Enabled, Disabled, or Auto)',
            
            # Alert Settings
            'movement_alert': 'Movement alert configuration (ON or OFF)',
            'power_alert': 'Power disconnection alert configuration',
            'battery_alert': 'Low battery alert configuration',
            'speed_limit': 'Speed limit for alerts in km/h',
            
            # Advanced Settings
            'sleep_mode': 'Sleep mode configuration (Disabled, Sleep, or Deep Sleep)',
            'sleep_time': 'Time in minutes before entering sleep mode',
            'network_select': 'Network selection mode (AUTO, 4G, or 2G)',
            'defense_time': 'Movement sensor activation time in minutes',
            'vibration_window': 'Vibration detection window configuration',
            'blind_speed': 'Speed threshold for position logging in km/h',
            'angle_reporting': 'Angle reporting configuration',
            'relay_gps_check': 'GPS check requirement before relay activation'
        }
        
        # Write sections with comments
        for section_name in config.sections():
            # Add section-specific comments
            if section_name == 'Profile_Info':
                lines.append("# Profile metadata and device information")
            elif 'APN' in section_name:
                lines.append("# Access Point Name configuration for cellular connectivity")
                lines.append("# These settings are required for the device to connect to the cellular network")
            elif 'Server' in section_name:
                lines.append("# Server connection settings for data transmission")
                lines.append("# These settings determine where the device sends tracking data")
            elif 'Timer' in section_name:
                lines.append("# Reporting interval settings based on ignition status")
                lines.append("# These settings control how frequently the device reports its position")
            elif 'Device' in section_name:
                lines.append("# Device behavior and sensor configuration")
                lines.append("# These settings control how the device sensors operate")
            elif 'Alert' in section_name:
                lines.append("# Alert and notification settings")
                lines.append("# These settings control when and how alerts are triggered")
            elif 'Advanced' in section_name:
                lines.append("# Advanced device configuration options")
                lines.append("# These settings control advanced features of the device")
            
            # Write section header
            lines.append(f"[{section_name}]")
            
            # Write parameters with documentation comments
            for key, value in config[section_name].items():
                # Add parameter documentation if available
                if key in param_docs:
                    lines.append(f"# {param_docs[key]}")
                lines.append(f"{key}={value}")
                lines.append("")  # Empty line after each parameter for readability
            
            # Empty line between sections
            lines.append("")
        
        return "\n".join(lines)

    def _section_name_to_ini(self, section_name: str) -> str:
        """
        Convert internal section name to INI section name.
        
        Args:
            section_name: Internal section name
            
        Returns:
            INI-formatted section name
        """
        return section_name.replace('_', ' ').title().replace(' ', '_')

    def validate_connection_required(self) -> ValidationResult:
        """
        Validate that device connection is available.
        
        Returns:
            ValidationResult with validation status and error details
        """
        # Check if serial service is available
        serial_service = self.app.serial_service if hasattr(self.app, 'serial_service') else None
        
        if not serial_service:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('profile_no_serial_service', 
                                          'Serial service is not available'),
                error_code='NO_SERIAL_SERVICE'
            )
        
        # Check if device is connected
        if not serial_service.is_connected:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('profile_device_not_connected', 
                                          'Device is not connected'),
                error_code='DEVICE_NOT_CONNECTED'
            )
        
        return ValidationResult(is_valid=True, error_message="", error_code="")

    def write_profile_file(self, profile_path: str, profile_text: str) -> bool:
        """
        Write profile text to a file.
        
        Args:
            profile_path: Path where the profile file should be saved
            profile_text: INI-formatted profile text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(profile_path), exist_ok=True)
            
            # Write the file
            with open(profile_path, 'w', encoding='utf-8') as f:
                f.write(profile_text)
            
            return True
        except Exception as e:
            self._log_message(f"ERROR: Failed to write profile file {profile_path}: {str(e)}")
            return False

    def _log_message(self, message: str) -> int:
        """
        Log a message to the application log.
        
        Args:
            message: Message to log
            
        Returns:
            0 if successful
        """
        try:
            if hasattr(self.app, 'log_frame'):
                self.app.log_frame.log_message(message)
        except (ValueError, AttributeError):
            pass
        return 0