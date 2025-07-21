
import re
import time
import threading
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from services.i18n_service import I18nService


@dataclass
class ParameterReadResult:
    """Result of reading a single parameter from the device."""
    parameter_name: str
    success: bool
    value: Optional[str]
    error_message: Optional[str]
    raw_response: str


@dataclass
class ConfigurationReadResult:
    """Result of reading multiple parameters from the device."""
    success: bool
    parameters_read: List[ParameterReadResult]
    total_parameters: int
    failed_parameters: List[str]
    read_duration: float
    timestamp: datetime


@dataclass
class ParsedResponse:
    """Result of parsing a device response."""
    command: str
    success: bool
    parsed_values: Dict[str, Any]
    raw_response: str
    error_message: Optional[str]


class ConfigurationReaderService:
    """Service for reading device configurations via RS232 connection."""

    def __init__(self, app_instance, i18n_service: I18nService):
        """
        Initialize the configuration reader service.
        
        Args:
            app_instance: Main application instance
            i18n_service: Internationalization service for error messages
        """
        self.app = app_instance
        self.i18n = i18n_service
        self.is_reading = False
        self.read_thread = None
        self.progress_callback = None
        self.completion_callback = None
        self.cancel_requested = False
        
        # Response capture mechanism
        self.waiting_for_response = False
        self.captured_response = None
        self.response_timeout = False
        
        # Initialize parameter query commands
        self._init_parameter_query_commands()
        
        # Initialize response parsing patterns
        self._init_response_patterns()

    def _init_parameter_query_commands(self) -> None:
        """Initialize AT commands for querying device parameters."""
        self.parameter_query_commands = {
            # Basic device information
            'device_info': [
                ('ATSMS:CXCS#IMEI', 'get_imei'),
                ('ATSMS:CXCS#ICCID', 'get_iccid'),
                ('ATSMS:VERSION#', 'get_version'),
                ('ATSMS:STATUS#', 'get_status')
            ],
            
            # APN and server settings
            'apn_config': ('ATSMS:APN#', 'get_apn'),
            'server_config': ('ATSMS:SERVER#', 'get_server'),
            
            # Timer and heartbeat settings
            'timer_settings': ('ATSMS:TIMER#', 'get_timer'),
            'heartbeat_settings': ('ATSMS:HBT#', 'get_hbt'),
            
            # Vibration and sensitivity settings
            'vibration_settings': ('ATSMS:CXCS#VIBL', 'get_vibl'),
            'vibration_window': ('ATSMS:CXCS#VIBCHK', 'get_vibchk'),
            'defense_settings': ('ATSMS:DEFENSE#', 'get_defense'),
            
            # Network and protocol settings
            'protocol_settings': ('ATSMS:CXCS#GT06SEL', 'get_gt06sel'),
            'network_settings': ('ATSMS:CXCS#NETSELECT', 'get_netselect'),
            'volte_settings': ('ATSMS:CXCS#VOLTESWITCH', 'get_volteswitch'),
            
            # Sleep mode settings
            'sleep_mode_settings': ('ATSMS:CXCS#SLPDISCONNECT', 'get_slpdisconnect'),
            'sleep_time_settings': ('ATSMS:CXCS#SLEEPT', 'get_sleept'),
            
            # Ignition settings
            'ignition_settings': ('ATSMS:CXCS#ACCLINE#ACC_CFG', 'get_accline'),
            
            # Comprehensive parameter query
            'all_parameters': ('ATSMS:PARAM#', 'get_all_params')
        }

    def _init_response_patterns(self) -> None:
        """Initialize regex patterns for parsing device responses."""
        self.response_patterns = {
            # Device information patterns
            'get_imei': r'IMEI[=:]\s*(\d+)',
            'get_iccid': r'ICCID[=:]\s*(\d+)',
            'get_version': r'(.+)',  # Version can be any format
            'get_status': r'(.+)',   # Status contains multiple key:value pairs
            
            # APN configuration pattern
            'get_apn': r'APN:([^,]*),([^,]*),([^#]*)',
            
            # Server configuration pattern
            'get_server': r'SERVER:(\d+),([^,]*),(\d+),(\d+)',
            
            # Timer configuration pattern
            'get_timer': r'TIMER:(\d+),(\d+)|TIMER ACC ON:(\d+)s,ACC OFF:(\d+)s',
            
            # Heartbeat configuration pattern
            'get_hbt': r'HBT:(\d+),(\d+)|HBT ACC ON:(\d+)s,ACC OFF:(\d+)s',
            
            # Vibration settings pattern
            'get_vibl': r'VIBL=(\d+)',
            'get_vibchk': r'VIBCHK=(\d+):(\d+)',
            
            # Defense settings pattern
            'get_defense': r'DEFENSE:(\d+)',
            
            # Protocol settings pattern
            'get_gt06sel': r'GT06SEL=(\d+)',
            
            # Network settings pattern
            'get_netselect': r'NETSELECT=(\d+)',
            'get_volteswitch': r'VOLTESWITCH=(\d+)',
            
            # Sleep mode patterns
            'get_slpdisconnect': r'SLPDISCONNECT=(\d+)',
            'get_sleept': r'SLEEPT=(\d+)',
            
            # Ignition settings pattern
            'get_accline': r'ACCLINE=(\d+).*ACC_CFG=([^#]*)',
            
            # All parameters pattern (complex parsing needed)
            'get_all_params': r'(.+)'  # Will need special handling
        }

    def read_all_configurations(self, progress_callback: Optional[Callable] = None,
                              completion_callback: Optional[Callable] = None,
                              show_progress_dialog: bool = True) -> None:
        """
        Read all device configurations asynchronously.
        
        Args:
            progress_callback: Optional callback for progress updates (current, total, status)
            completion_callback: Optional callback when reading is complete (result)
            show_progress_dialog: Whether to show a progress dialog
        """
        if self.is_reading:
            error_msg = self.i18n.get('config_read_already_in_progress', 
                                    'Configuration reading is already in progress')
            if completion_callback:
                result = ConfigurationReadResult(
                    success=False,
                    parameters_read=[],
                    total_parameters=0,
                    failed_parameters=[],
                    read_duration=0.0,
                    timestamp=datetime.now()
                )
                completion_callback(result, error_msg)
            return

        # Check if device is connected
        if not hasattr(self.app, 'serial_service') or not self.app.serial_service.is_connected:
            error_msg = self.i18n.get('config_read_no_connection', 
                                    'Device connection is required for configuration reading')
            if completion_callback:
                result = ConfigurationReadResult(
                    success=False,
                    parameters_read=[],
                    total_parameters=0,
                    failed_parameters=[],
                    read_duration=0.0,
                    timestamp=datetime.now()
                )
                completion_callback(result, error_msg)
            return

        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.cancel_requested = False
        self.is_reading = True
        self.progress_dialog_id = None

        # Create progress dialog if requested and service is available
        if show_progress_dialog and hasattr(self.app, 'operation_confirmation_service'):
            try:
                self.progress_dialog_id = self.app.operation_confirmation_service.create_progress_dialog(
                    title=self.i18n.get('config_read_dialog_title', 'Reading Configuration'),
                    operation_name=self.i18n.get('config_read_operation_name', 'Device Configuration Reading'),
                    progress_type=self.app.operation_confirmation_service.PROGRESS_TYPE_DETERMINATE,
                    total_steps=100,
                    cancelable=True
                )
                
                # Set cancel callback
                self.app.operation_confirmation_service.set_cancel_callback(
                    self.progress_dialog_id,
                    self.cancel_reading
                )
            except Exception as e:
                self._log_message(f"WARNING: Failed to create progress dialog: {str(e)}")
                self.progress_dialog_id = None

        # Disable parameter modification during read operations
        self._disable_parameter_modification(True)

        # Start reading in a separate thread
        self.read_thread = threading.Thread(target=self._read_configurations_thread, daemon=True)
        self.read_thread.start()

    def _read_configurations_thread(self) -> None:
        """Thread function for reading configurations."""
        start_time = time.time()
        parameters_read = []
        failed_parameters = []
        success = False
        completion_message = None
        error_msg = None
        
        try:
            # Initialize error tracking
            self.last_read_attempt = datetime.now()
            self.total_read_attempts = getattr(self, 'total_read_attempts', 0) + 1
            
            # Get all parameter commands to execute
            all_commands = self._get_all_parameter_commands()
            total_commands = len(all_commands)
            
            self._log_message(f"INFO: Starting configuration read with {total_commands} commands (attempt #{self.total_read_attempts})")
            
            for i, (param_name, command, command_type) in enumerate(all_commands):
                if self.cancel_requested:
                    self._log_message("INFO: Configuration reading canceled by user")
                    break
                
                # Update progress
                status_text = self.i18n.get('config_read_progress', 
                                          'Reading {param_name}...').format(param_name=param_name)
                
                # Update progress dialog if available
                if self.progress_dialog_id and hasattr(self.app, 'operation_confirmation_service'):
                    try:
                        progress_step = int((i + 1) * 100 / total_commands)
                        self.app.after(0, self.app.operation_confirmation_service.update_progress,
                                      self.progress_dialog_id, progress_step, status_text)
                    except Exception as e:
                        self._log_message(f"WARNING: Failed to update progress dialog: {str(e)}")
                
                # Call custom progress callback if provided
                if self.progress_callback:
                    self.app.after(0, self.progress_callback, i + 1, total_commands, status_text)
                
                # Read the parameter with retry logic
                result = self.read_specific_parameter(param_name, command, command_type, max_retries=2)
                parameters_read.append(result)
                
                if not result.success:
                    failed_parameters.append(param_name)
                    error_msg = self._get_specific_error_message(param_name, result.error_message)
                    self._log_message(f"WARNING: Failed to read {param_name}: {error_msg}")
                else:
                    self._log_message(f"INFO: Successfully read {param_name}: {result.value}")
                
                # Add delay between commands to avoid overwhelming the device
                if i < total_commands - 1:  # Don't delay after the last command
                    time.sleep(0.8)
            
            # Calculate results
            read_duration = time.time() - start_time
            successful_reads = len(all_commands) - len(failed_parameters)
            success = successful_reads > 0  # Success if at least one parameter was read
            
            # Set completion message with detailed results
            if len(failed_parameters) == 0:
                completion_message = f"Configuration reading completed successfully - all {len(all_commands)} parameters read"
            elif successful_reads > 0:
                completion_message = f"Configuration reading partially completed - {successful_reads}/{len(all_commands)} parameters read"
            else:
                completion_message = "Configuration reading failed - no parameters could be read"
            
            result = ConfigurationReadResult(
                success=success,
                parameters_read=parameters_read,
                total_parameters=total_commands,
                failed_parameters=failed_parameters,
                read_duration=read_duration,
                timestamp=datetime.now()
            )
            
            # Update error statistics
            self.successful_reads = getattr(self, 'successful_reads', 0) + successful_reads
            self.failed_reads = getattr(self, 'failed_reads', 0) + len(failed_parameters)
            
            # Update UI with read parameters
            if success:
                self._update_ui_with_parameters(parameters_read)
            
            # Call completion callback
            if self.completion_callback:
                error_msg = None
                if failed_parameters:
                    error_msg = f"Failed to read {len(failed_parameters)} parameters"
                self.app.after(0, self.completion_callback, result, error_msg)
            
            self._log_message(f"INFO: Configuration reading completed in {read_duration:.2f} seconds")
            self._log_message(f"INFO: Session statistics - Total successful: {self.successful_reads}, Total failed: {self.failed_reads}")
            
        except Exception as e:
            # Handle unexpected errors
            success = False
            error_msg = self.i18n.get('config_read_unexpected_error',
                                    'Unexpected error during configuration reading: {error}').format(error=str(e))
            completion_message = f"Operation failed: {str(e)}"
            self._log_message(f"ERROR: {error_msg}")
            
            result = ConfigurationReadResult(
                success=False,
                parameters_read=parameters_read,
                total_parameters=0,
                failed_parameters=[],
                read_duration=time.time() - start_time,
                timestamp=datetime.now()
            )
            
            if self.completion_callback:
                self.app.after(0, self.completion_callback, result, error_msg)
        
        finally:
            self.is_reading = False
            
            # Re-enable parameter modification
            self._disable_parameter_modification(False)
            
            # Close progress dialog if it exists
            if self.progress_dialog_id and hasattr(self.app, 'operation_confirmation_service'):
                try:
                    self.app.after(0, self.app.operation_confirmation_service.complete_progress,
                                  self.progress_dialog_id, success, completion_message or error_msg)
                except Exception as e:
                    self._log_message(f"WARNING: Failed to close progress dialog: {str(e)}")
            
            self.progress_dialog_id = None

    def _update_ui_with_parameters(self, parameters_read):
        """
        Update UI with parameters read from the device.
        
        Args:
            parameters_read: List of parameter read results
        """
        try:
            self._log_message("DEBUG: Updating UI with parameters read from device")
            self._log_message(f"DEBUG: Number of parameters to process: {len(parameters_read)}")
            
            # Debug: List all parameters
            for result in parameters_read:
                self._log_message(f"DEBUG: Parameter {result.parameter_name}: success={result.success}, value={result.value}")
            
            # Check if we have access to the parameters frame
            if not hasattr(self.app, 'parameters_frame') or self.app.parameters_frame is None:
                self._log_message("DEBUG: Parameters frame not available yet, scheduling UI update for later")
                # Schedule the UI update for later when the parameters frame is available
                self.app.after(100, lambda: self._update_ui_with_parameters(parameters_read))
                return
            else:
                self._log_message("DEBUG: Parameters frame found, proceeding with UI updates")
            
            # Process APN configuration
            for result in parameters_read:
                if not result.success or result.value is None:
                    continue
                
                param_name = result.parameter_name
                value = result.value
                
                self._log_message(f"DEBUG: Processing parameter {param_name} with value {value}")
                
                # Handle APN configuration
                if param_name == 'apn_config':
                    # Parse APN components from raw response
                    apn_server = value  # This is the main value (server)
                    apn_user = ""
                    apn_password = ""
                    
                    # Try to extract user and password from raw response
                    if result.raw_response and 'APN:' in result.raw_response:
                        try:
                            # Extract the part after "APN:"
                            apn_part = result.raw_response.split('APN:', 1)[1].strip()
                            # Split by comma to get server, user, password
                            apn_components = apn_part.split(',')
                            if len(apn_components) >= 1:
                                apn_server = apn_components[0].strip()
                            if len(apn_components) >= 2:
                                apn_user = apn_components[1].strip()
                            if len(apn_components) >= 3:
                                apn_password = apn_components[2].strip()
                        except Exception as e:
                            self._log_message(f"WARNING: Failed to parse APN components: {str(e)}")
                    
                    # Update APN fields using the parameters frame method
                    if hasattr(self.app.parameters_frame, 'update_apn_fields'):
                        def update_apn():
                            try:
                                self.app.parameters_frame.update_apn_fields(
                                    server=apn_server, 
                                    user=apn_user, 
                                    password=apn_password
                                )
                                self._log_message(f"DEBUG: Updated APN fields - server: {apn_server}, user: {apn_user}, password: {apn_password}")
                            except Exception as e:
                                self._log_message(f"ERROR: Failed to update APN fields: {str(e)}")
                        
                        # Schedule the update on the main thread
                        self.app.after(0, update_apn)
                
                # Handle server configuration
                elif param_name == 'server_config':
                    # Try to update server IP widget
                    if hasattr(self.app.parameters_frame, 'parameter_widgets') and 'server_ip' in self.app.parameters_frame.parameter_widgets:
                        server_widget = self.app.parameters_frame.parameter_widgets['server_ip']
                        if hasattr(server_widget, 'set_value'):
                            def update_server():
                                try:
                                    server_widget.set_value(value)
                                    self._log_message(f"DEBUG: Updated server IP to {value}")
                                except Exception as e:
                                    self._log_message(f"ERROR: Failed to update server IP: {str(e)}")
                            
                            # Schedule the update on the main thread
                            self.app.after(0, update_server)
                
                # Handle protocol configuration
                elif param_name == 'protocol_settings':
                    # Try to update protocol widget
                    if hasattr(self.app.parameters_frame, 'parameter_widgets') and 'gt06_protocol' in self.app.parameters_frame.parameter_widgets:
                        protocol_widget = self.app.parameters_frame.parameter_widgets['gt06_protocol']
                        if hasattr(protocol_widget, 'set_value'):
                            def update_protocol():
                                try:
                                    protocol_widget.set_value(value)
                                    self._log_message(f"DEBUG: Updated protocol to {value}")
                                except Exception as e:
                                    self._log_message(f"ERROR: Failed to update protocol: {str(e)}")
                            
                            # Schedule the update on the main thread
                            self.app.after(0, update_protocol)
        except Exception as e:
            self._log_message(f"ERROR: Failed to update UI with parameters: {str(e)}")

    def read_specific_parameter(self, param_name: str, command: str = None, 
                              command_type: str = None, max_retries: int = 2) -> ParameterReadResult:
        """
        Read a specific parameter from the device with retry logic.
        
        Args:
            param_name: Name of the parameter to read
            command: AT command to send (optional, will be looked up if not provided)
            command_type: Type of command for response parsing
            max_retries: Maximum number of retry attempts for failed reads
            
        Returns:
            ParameterReadResult with the reading result
        """
        if command is None:
            # Look up the command for this parameter
            if param_name in self.parameter_query_commands:
                query_info = self.parameter_query_commands[param_name]
                if isinstance(query_info, tuple):
                    command, command_type = query_info
                else:
                    return ParameterReadResult(
                        parameter_name=param_name,
                        success=False,
                        value=None,
                        error_message=f"Invalid command configuration for {param_name}",
                        raw_response=""
                    )
            else:
                return ParameterReadResult(
                    parameter_name=param_name,
                    success=False,
                    value=None,
                    error_message=f"Unknown parameter: {param_name}",
                    raw_response=""
                )
        
        last_error = None
        last_response = ""
        
        # Attempt to read the parameter with retries
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # Log retry attempt
                    self._log_message(f"INFO: Retrying {param_name} read (attempt {attempt + 1}/{max_retries + 1})")
                    # Add a small delay between retries
                    time.sleep(0.5)
                
                # Send the command and wait for response
                response = self._send_command_and_wait(command, timeout=5.0)
                
                if response is None:
                    last_error = self.i18n.get('config_read_timeout', 'Command timeout')
                    continue
                
                last_response = response
                
                # Parse the response
                parsed_response = self.parse_device_response(command, response, command_type)
                
                if parsed_response.success and parsed_response.parsed_values:
                    # Extract the main value for this parameter
                    value = self._extract_parameter_value(param_name, parsed_response.parsed_values)
                    
                    # Log successful read after retries
                    if attempt > 0:
                        self._log_message(f"INFO: Successfully read {param_name} after {attempt + 1} attempts")
                    
                    return ParameterReadResult(
                        parameter_name=param_name,
                        success=True,
                        value=value,
                        error_message=None,
                        raw_response=response
                    )
                else:
                    last_error = parsed_response.error_message or "Failed to parse response"
                    
            except Exception as e:
                last_error = str(e)
                self._log_message(f"WARNING: Exception during {param_name} read attempt {attempt + 1}: {last_error}")
        
        # All attempts failed, return the final error
        final_error_msg = self._get_specific_error_message(param_name, last_error or "Unknown error")
        
        return ParameterReadResult(
            parameter_name=param_name,
            success=False,
            value=None,
            error_message=final_error_msg,
            raw_response=last_response
        )

    def parse_device_response(self, command: str, response: str, command_type: str) -> ParsedResponse:
        """
        Parse device response based on the command type.
        
        Args:
            command: The command that was sent
            response: The device response string
            command_type: The type of command for parsing
            
        Returns:
            ParsedResponse with parsed information
        """
        parsed_values = {}
        error_message = None
        success = False
        
        try:
            # Get the appropriate pattern for this command type
            pattern = self.response_patterns.get(command_type)
            
            if not pattern:
                error_message = f"No parsing pattern defined for command type: {command_type}"
                return ParsedResponse(command, False, {}, response, error_message)
            
            # Apply pattern matching
            match = re.search(pattern, response)
            
            if match:
                success = True
                
                # Parse based on command type
                if command_type == 'get_imei':
                    parsed_values['imei'] = match.group(1)
                    
                elif command_type == 'get_iccid':
                    parsed_values['iccid'] = match.group(1)
                    
                elif command_type == 'get_version':
                    parsed_values['version'] = match.group(1).strip()
                    
                elif command_type == 'get_status':
                    # Parse status response with multiple key:value pairs
                    status_text = match.group(1)
                    for section in status_text.split(';'):
                        if ':' in section:
                            key, value = section.split(':', 1)
                            parsed_values[key.strip().lower()] = value.strip()
                    
                elif command_type == 'get_apn':
                    parsed_values['apn_server'] = match.group(1)
                    parsed_values['apn_user'] = match.group(2)
                    parsed_values['apn_password'] = match.group(3).rstrip('#')
                    
                elif command_type == 'get_server':
                    parsed_values['server_type'] = match.group(1)
                    parsed_values['server_address'] = match.group(2)
                    parsed_values['server_port'] = match.group(3)
                    parsed_values['server_protocol'] = match.group(4)
                    
                elif command_type == 'get_timer':
                    # Handle both response formats
                    if match.group(1) and match.group(2):  # TIMER:x,y format
                        parsed_values['timer_ign_on'] = match.group(1)
                        parsed_values['timer_ign_off'] = match.group(2)
                    elif match.group(3) and match.group(4):  # TIMER ACC ON:xs,ACC OFF:ys format
                        parsed_values['timer_ign_on'] = match.group(3)
                        parsed_values['timer_ign_off'] = match.group(4)
                    
                elif command_type == 'get_hbt':
                    # Handle both response formats
                    if match.group(1) and match.group(2):  # HBT:x,y format
                        parsed_values['heartbeat_ign_on'] = match.group(1)
                        parsed_values['heartbeat_ign_off'] = match.group(2)
                    elif match.group(3) and match.group(4):  # HBT ACC ON:xs,ACC OFF:ys format
                        parsed_values['heartbeat_ign_on'] = match.group(3)
                        parsed_values['heartbeat_ign_off'] = match.group(4)
                    
                elif command_type == 'get_vibl':
                    parsed_values['vibration'] = match.group(1)
                    
                elif command_type == 'get_vibchk':
                    parsed_values['vibration_window'] = match.group(1)
                    parsed_values['vibration_threshold'] = match.group(2)
                    
                elif command_type == 'get_defense':
                    parsed_values['defense_time'] = match.group(1)
                    
                elif command_type == 'get_gt06sel':
                    # Map numeric values back to protocol names
                    protocol_map = {'0': 'GT06-0x60', '1': 'CRX3', '2': 'GT06-0x12'}
                    protocol_value = match.group(1)
                    parsed_values['gt06_protocol'] = protocol_map.get(protocol_value, protocol_value)
                    
                elif command_type == 'get_netselect':
                    # Map numeric values back to network names
                    network_map = {'0': 'AUTO', '1': '4G', '2': '2G'}
                    network_value = match.group(1)
                    parsed_values['network_select'] = network_map.get(network_value, network_value)
                    
                elif command_type == 'get_volteswitch':
                    # Map numeric values back to network names
                    volte_map = {'0': '2G', '1': '4G'}
                    volte_value = match.group(1)
                    parsed_values['volte_switch'] = volte_map.get(volte_value, volte_value)
                    
                elif command_type == 'get_slpdisconnect':
                    # Map numeric values back to sleep mode names
                    sleep_map = {'0': 'Disabled', '1': 'Sleep', '2': 'Deep Sleep'}
                    sleep_value = match.group(1)
                    parsed_values['sleep_mode'] = sleep_map.get(sleep_value, sleep_value)
                    
                elif command_type == 'get_sleept':
                    parsed_values['sleep_time'] = match.group(1)
                    
                elif command_type == 'get_accline':
                    # Map ignition type
                    ignition_map = {'0': 'Digital', '1': 'Analog'}
                    ignition_value = match.group(1)
                    parsed_values['ignition_type'] = ignition_map.get(ignition_value, ignition_value)
                    parsed_values['ignition_config'] = match.group(2)
                    
                elif command_type == 'get_all_params':
                    # Parse comprehensive parameter response
                    self._parse_all_parameters_response(response, parsed_values)
                    
            else:
                error_message = f"Response does not match expected pattern for {command_type}"
                
        except Exception as e:
            error_message = f"Error parsing response: {str(e)}"
            
        return ParsedResponse(command, success, parsed_values, response, error_message)

    def _parse_all_parameters_response(self, response: str, parsed_values: Dict[str, Any]) -> None:
        """Parse the comprehensive PARAM# response."""
        # Example: "IMEI:357457040000821;TIMER:20,300;SEMDS:3;HBT:180Sec;Defense:3;"
        for section in response.split(';'):
            if ':' in section:
                key, value = section.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'IMEI':
                    parsed_values['imei'] = value
                elif key == 'TIMER':
                    parts = value.split(',')
                    if len(parts) >= 2:
                        parsed_values['timer_ign_on'] = parts[0]
                        parsed_values['timer_ign_off'] = parts[1]
                elif key == 'HBT':
                    # Handle format like "180Sec"
                    hbt_value = re.sub(r'[^\d]', '', value)  # Extract only digits
                    parsed_values['heartbeat_interval'] = hbt_value
                elif key == 'Defense':
                    parsed_values['defense_time'] = value

    def _get_all_parameter_commands(self) -> List[tuple]:
        """Get all parameter commands to execute during configuration reading."""
        commands = []
        
        # Add device information commands
        for command, command_type in self.parameter_query_commands['device_info']:
            commands.append(('device_info', command, command_type))
        
        # Add APN configuration command
        apn_command, apn_command_type = self.parameter_query_commands['apn_config']
        commands.append(('apn_config', apn_command, apn_command_type))
        
        # Add server configuration command
        server_command, server_command_type = self.parameter_query_commands['server_config']
        commands.append(('server_config', server_command, server_command_type))
        
        # Add timer settings command
        timer_command, timer_command_type = self.parameter_query_commands['timer_settings']
        commands.append(('timer_settings', timer_command, timer_command_type))
        
        # Add heartbeat settings command
        hbt_command, hbt_command_type = self.parameter_query_commands['heartbeat_settings']
        commands.append(('heartbeat_settings', hbt_command, hbt_command_type))
        
        # Add vibration settings command
        vib_command, vib_command_type = self.parameter_query_commands['vibration_settings']
        commands.append(('vibration_settings', vib_command, vib_command_type))
        
        # Add vibration window command
        vibchk_command, vibchk_command_type = self.parameter_query_commands['vibration_window']
        commands.append(('vibration_window', vibchk_command, vibchk_command_type))
        
        # Add defense settings command
        defense_command, defense_command_type = self.parameter_query_commands['defense_settings']
        commands.append(('defense_settings', defense_command, defense_command_type))
        
        # Add protocol settings command
        protocol_command, protocol_command_type = self.parameter_query_commands['protocol_settings']
        commands.append(('protocol_settings', protocol_command, protocol_command_type))
        
        # Add network settings command
        network_command, network_command_type = self.parameter_query_commands['network_settings']
        commands.append(('network_settings', network_command, network_command_type))
        
        # Add volte settings command
        volte_command, volte_command_type = self.parameter_query_commands['volte_settings']
        commands.append(('volte_settings', volte_command, volte_command_type))
        
        # Add sleep mode settings command
        sleep_command, sleep_command_type = self.parameter_query_commands['sleep_mode_settings']
        commands.append(('sleep_mode_settings', sleep_command, sleep_command_type))
        
        # Add sleep time settings command
        sleept_command, sleept_command_type = self.parameter_query_commands['sleep_time_settings']
        commands.append(('sleep_time_settings', sleept_command, sleept_command_type))
        
        # Add ignition settings command
        ignition_command, ignition_command_type = self.parameter_query_commands['ignition_settings']
        commands.append(('ignition_settings', ignition_command, ignition_command_type))
        
        # Add all parameters command
        all_params_command, all_params_command_type = self.parameter_query_commands['all_parameters']
        commands.append(('all_parameters', all_params_command, all_params_command_type))
        
        return commands

    def _extract_parameter_value(self, param_name: str, parsed_values: Dict[str, Any]) -> str:
        """Extract the main value for a parameter from parsed values."""
        # Handle special cases
        if param_name == 'device_info':
            # Return IMEI as the main value for device_info
            return parsed_values.get('imei', '')
        elif param_name == 'apn_config':
            # Return APN server as the main value for apn_config
            return parsed_values.get('apn_server', '')
        elif param_name == 'server_config':
            # Return server address as the main value for server_config
            return parsed_values.get('server_address', '')
        elif param_name == 'timer_settings':
            # Return timer_ign_on as the main value for timer_settings
            return parsed_values.get('timer_ign_on', '')
        elif param_name == 'heartbeat_settings':
            # Return heartbeat_ign_on as the main value for heartbeat_settings
            return parsed_values.get('heartbeat_ign_on', '')
        elif param_name == 'vibration_settings':
            # Return vibration as the main value for vibration_settings
            return parsed_values.get('vibration', '')
        elif param_name == 'vibration_window':
            # Return vibration_window as the main value for vibration_window
            return parsed_values.get('vibration_window', '')
        elif param_name == 'defense_settings':
            # Return defense_time as the main value for defense_settings
            return parsed_values.get('defense_time', '')
        elif param_name == 'protocol_settings':
            # Return gt06_protocol as the main value for protocol_settings
            return parsed_values.get('gt06_protocol', '')
        elif param_name == 'network_settings':
            # Return network_select as the main value for network_settings
            return parsed_values.get('network_select', '')
        elif param_name == 'volte_settings':
            # Return volte_switch as the main value for volte_settings
            return parsed_values.get('volte_switch', '')
        elif param_name == 'sleep_mode_settings':
            # Return sleep_mode as the main value for sleep_mode_settings
            return parsed_values.get('sleep_mode', '')
        elif param_name == 'sleep_time_settings':
            # Return sleep_time as the main value for sleep_time_settings
            return parsed_values.get('sleep_time', '')
        elif param_name == 'ignition_settings':
            # Return ignition_type as the main value for ignition_settings
            return parsed_values.get('ignition_type', '')
        elif param_name == 'all_parameters':
            # Return IMEI as the main value for all_parameters
            return parsed_values.get('imei', '')
        else:
            # For other parameters, return the first value
            return next(iter(parsed_values.values()), '')

    def _send_command_and_wait(self, command: str, timeout: float = 5.0) -> Optional[str]:
        """
        Send a command and wait for a response.
        
        Args:
            command: The command to send
            timeout: Timeout in seconds
            
        Returns:
            The device response or None if timeout
        """
        # Check if we have access to the serial service
        if not hasattr(self.app, 'serial_service'):
            self._log_message("ERROR: Cannot send command - serial_service not found")
            return None
        
        # Set up response capture
        self.waiting_for_response = True
        self.captured_response = None
        self.response_timeout = False
        
        # Send the command
        self.app.serial_service.send_command(command)
        
        # Wait for a response
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.captured_response:
                response = self.captured_response
                self.waiting_for_response = False
                self.captured_response = None
                return response
            
            # Sleep for a short time
            time.sleep(0.1)
        
        # Timeout
        self.waiting_for_response = False
        self.response_timeout = True
        return None
    
    def capture_device_response(self, response: str) -> None:
        """
        Capture a device response for the configuration reader.
        
        Args:
            response: The device response string
        """
        if self.waiting_for_response and not self.captured_response:
            self.captured_response = response.strip()

    def _get_specific_error_message(self, param_name: str, error_message: str) -> str:
        """Get a specific error message for a parameter."""
        # Use the provided error message if available
        if error_message:
            return f"Failed to read {param_name}: {error_message}"
        
        # Default error message
        return f"Failed to read {param_name}"

    def _disable_parameter_modification(self, disable: bool) -> None:
        """
        Disable or enable parameter modification during read operations.
        
        Args:
            disable: Whether to disable parameter modification
        """
        # This is a placeholder method that would be implemented to disable UI elements
        pass

    def _log_message(self, message: str) -> None:
        """Log a message to the application log."""
        if hasattr(self.app, 'log_frame'):
            self.app.log_frame.log_message(message + "\n")
        else:
            print(message)

    def cancel_reading(self) -> None:
        """Cancel the current configuration reading operation."""
        self.cancel_requested = True
        self._log_message("INFO: Canceling configuration reading...")
