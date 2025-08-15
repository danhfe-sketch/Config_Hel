
import re
import time
import threading
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from services.i18n_service import I18nService
from services.lt32pro_command_formatter import LT32ProCommandFormatter


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
        
        # Command formatter for proper LT32Pro USB communication
        self.command_formatter = LT32ProCommandFormatter()
        
        # Error handling
        self.parameter_error_handler = None
        self._init_error_handler()
        
        # Initialize parameter query commands
        self._init_parameter_query_commands()
        
        # Initialize response parsing patterns
        self._init_response_patterns()
    
    def _init_error_handler(self):
        """Initialize parameter error handler."""
        if hasattr(self.app, 'error_handler') and hasattr(self.app.error_handler, 'parameter_error_handler'):
            self.parameter_error_handler = self.app.error_handler.parameter_error_handler
        else:
            try:
                from services.parameter_error_handler import ParameterErrorHandler
                self.parameter_error_handler = ParameterErrorHandler(self.app)
            except ImportError:
                self.parameter_error_handler = None

    def _init_parameter_query_commands(self) -> None:
        """Initialize AT commands for querying device parameters based on specification."""
        # Expanded: Full parameter set for device configuration check
        self.parameter_query_commands = {
            # Basic device information
            'device_info': [
                ('IMEI', 'get_imei'),
                ('ICCID', 'get_iccid'),
                ('VERSION', 'get_version'),
                ('STATUS', 'get_status')
            ],
            # Network parameters
            'apn_settings': ('APN', 'get_apn'),
            'server_settings': ('SERVER', 'get_server'),
            'network_settings': ('NETSELECT', 'get_netselect'),
            # Service parameters
            'protocol': ('GT06SEL', 'get_protocol'),
            'tcp_ack': ('POSBYACK', 'get_tcp_ack'),
            # Time Parameters
            'report_intervals': ('TIMER', 'get_timer'),
            'heartbeat_intervals': ('HBT', 'get_hbt'),
            # Ignition Parameters
            'ignition_type': [
                ('ACCLINE', 'get_accline'),
                ('ACC_CFG', 'get_acc_cfg')
            ],
            # Speed Parameters
            'speed_alert': ('SPEED', 'get_speed_alert'),
            'speed_buzzer': ('SPD_LED_SHOW', 'get_speed_buzzer'),
            # Power Saving Parameters
            'sleep_mode': ('SLPDISCONNECT', 'get_sleep_mode'),
            'sleep_time': ('SLEEPT', 'get_sleep_time'),
            # Angle Parameters
            'angle_report': ('ANGLEVALUE', 'get_angle_report'),
            # Battery Alert Parameters
            'backup_battery_alert': ('BATALM', 'get_backup_battery_alert'),
            'main_power_alert': ('POWERALM', 'get_main_power_alert'),
            # Vibration Sensor Parameters
            'vibration_sensitivity': ('VIBL', 'get_vibration_sensitivity'),
            'vibration_settings': ('VIBL', 'get_vibl'),
            'vibration_window': ('VIBCHK', 'get_vibchk'),
            # Jammer Detection Parameters
            'jammer_detection': ('JAMMER', 'get_jammer_detection'),
            'jammer_relay_action': ('JAMRELAY', 'get_jammer_relay_action'),
            # Miscellaneous Parameters
            'odometer': ('MILEAGE', 'get_odometer'),
            'hourmeter': ('ACCONT', 'get_hourmeter'),
            'defense_settings': ('DEFENSE', 'get_defense'),
            'volte_settings': ('VOLTESWITCH', 'get_volteswitch'),
            # Comprehensive parameter query
            'all_parameters': ('PARAM', 'get_all_params')
        }

    def _init_response_patterns(self) -> None:
        """Initialize regex patterns for parsing device responses based on specification."""
        self.response_patterns = {
            # Device information patterns (LT32Pro serial format)
            'get_imei': r'READOK:\s*IMEI=(\d+)',
            'get_iccid': r'READOK:\s*ICCID=(\d+)',
            'get_version': r'(.+)',  # Version format: LT32Pro_10F8A_B53_V6.56 2025-06-26
            'get_status': r'(.+)',   # Status format: Battery:4.11V;GPRS:Online;GSM Signal Level:29;ACC:ON;GPS:Successful positioning
            
            # Network Parameters
            'get_apn': r'APN:([^,]*),([^,]*),([^#]*)',
            'get_server': r'SERVER:(\d+),([^,]*),(\d+),(\d+)',
            
            # Time Parameters
            'get_timer': r'TIMER:\s*(\d+)\s*,\s*(\d+)|TIMER\s+ACC\s+ON:\s*(\d+)s?\s*,\s*ACC\s+OFF:\s*(\d+)s?|TIMER:\s*(\d+)s?\s*,\s*ACC\s+OFF:\s*(\d+)s?',
            'get_hbt': r'HBT:(\d+),(\d+)|HBT ACC ON:(\d+)s,ACC OFF:(\d+)s|HBT:(\d+)s,ACC OFF:(\d+)s',
            
            # Service Parameters (LT32Pro format)
            'get_protocol': r'READOK:\s*GT06SEL=(\d+)',
            'get_tcp_ack': r'READOK:\s*POSBYACK=(\d+)',
            
            # Ignition Parameters (LT32Pro format)
            'get_accline': r'READOK:\s*ACCLINE=(\d+)',
            'get_acc_cfg': r'READOK:\s*ACC_CFG=(\d+)[,-](\d+)[,-](\d+)',
            
            # Speed Parameters (LT32Pro format)
            'get_speed_alert': r'SPEED:(OFF|ON,(\d+),(\d+),(\d+))',
            'get_speed_buzzer': r'READOK:\s*SPD_LED_SHOW=(\d+)',
            
            # Power Saving Parameters (LT32Pro format)
            'get_sleep_mode': r'READOK:\s*SLPDISCONNECT=(\d+)',
            'get_sleep_time': r'READOK:\s*SLEEPT=(\d+)',
            
            # Angle Parameters (LT32Pro format)
            'get_angle_report': r'READOK:\s*ANGLEVALUE=(\d+)-(\d+)',
            
            # Battery Alert Parameters
            'get_backup_battery_alert': r'BATALM:(ON|OFF|\d+),(\d+)',
            'get_main_power_alert': r'POWERALM:(ON|OFF|\d+),(\d+),(\d+),(\d+)',
            
            # Vibration Sensor Parameters (LT32Pro format)
            'get_vibration_sensitivity': r'READOK:\s*VIBL=(\d+)',
            
            # Jammer Detection Parameters
            'get_jammer_detection': r'JAMMER:(ON|OFF|\d+)(?:,(\d+))?',
            'get_jammer_relay_action': r'JAMRELAY:(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)',
            
            # Miscellaneous Parameters
            'get_odometer': r'(?:MILEAGE=([^,#\s]+)|Cur Mileage Value:([^K]+)KM)',
            'get_hourmeter': r'(?:ACCONT:([^,#\s]+)|Get ACC ON Time:([^M]+) Minute)',
            
            # Legacy patterns for backward compatibility (LT32Pro format)
            'get_vibl': r'READOK:\s*VIBL=(\d+)',
            'get_vibchk': r'READOK:\s*VIBCHK=(\d+):(\d+)',
            'get_defense': r'DEFENSE:(\d+)',
            'get_gt06sel': r'READOK:\s*GT06SEL=(\d+)',
            'get_netselect': r'READOK:\s*NETSELECT=(\d+)',
            'get_volteswitch': r'READOK:\s*VOLTESWITCH=(\d+)',
            'get_slpdisconnect': r'READOK:\s*SLPDISCONNECT=(\d+)',
            'get_sleept': r'READOK:\s*SLEEPT=(\d+)',
            
            # All parameters pattern (complex parsing needed)
            'get_all_params': r'(.+)'  # Will need special handling
        }

    def read_all_configurations(self, progress_callback: Optional[Callable] = None,
                              completion_callback: Optional[Callable] = None,
                              show_progress_dialog: bool = True) -> None:
        """
        Read all device configurations asynchronously with enhanced progress indication.
        
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

        # Enhanced connection validation before starting operations
        if self.parameter_error_handler:
            validation_result = self.parameter_error_handler.validate_connection_before_operation("configuration reading")
            if not validation_result.is_valid:
                error_msg = validation_result.error_message or 'Connection validation failed'
                self._log_message(f"ERROR: Connection validation failed: {error_msg}")
                
                # Log detailed validation information
                self._log_message(f"DEBUG: Connection quality: {validation_result.connection_quality}%")
                if validation_result.last_activity:
                    time_since = datetime.now() - validation_result.last_activity
                    self._log_message(f"DEBUG: Last activity: {int(time_since.total_seconds())}s ago")
                
                # Log suggested actions with priority
                if validation_result.suggested_actions:
                    self._log_message("INFO: Suggested solutions (in order of priority):")
                    for i, action in enumerate(validation_result.suggested_actions, 1):
                        priority = "HIGH" if i <= 2 else "MEDIUM" if i <= 4 else "LOW"
                        self._log_message(f"INFO: {i}. [{priority}] {action}")
                
                # Create detailed error result
                if completion_callback:
                    result = ConfigurationReadResult(
                        success=False,
                        parameters_read=[],
                        total_parameters=0,
                        failed_parameters=['connection_validation'],
                        read_duration=0.0,
                        timestamp=datetime.now()
                    )
                    completion_callback(result, error_msg)
                return
        else:
            # Fallback connection check
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
        
        # Initialize progress tracking variables
        self.current_parameter_index = 0
        self.total_parameters_count = 0
        self.successful_reads_count = 0
        self.failed_reads_count = 0
        self.current_parameter_name = ""

        # Create enhanced progress dialog if requested and service is available
        if show_progress_dialog and hasattr(self.app, 'operation_confirmation_service'):
            try:
                # Get total parameter count for accurate progress
                all_commands = self._get_all_parameter_commands()
                self.total_parameters_count = len(all_commands)
                
                self.progress_dialog_id = self.app.operation_confirmation_service.create_progress_dialog(
                    title=self.i18n.get('config_read_dialog_title', 'Reading Device Configuration'),
                    operation_name=self.i18n.get('config_read_operation_name', 'Parameter Reading Operation'),
                    progress_type=self.app.operation_confirmation_service.PROGRESS_TYPE_DETERMINATE,
                    total_steps=self.total_parameters_count,
                    cancelable=True
                )
                
                # Set cancel callback
                self.app.operation_confirmation_service.set_cancel_callback(
                    self.progress_dialog_id,
                    self.cancel_reading
                )
                
                # Initialize progress dialog with starting status
                self.app.operation_confirmation_service.update_progress(
                    self.progress_dialog_id,
                    step=0,
                    status_text=f"Preparing to read {self.total_parameters_count} parameters..."
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
                
                # Update current parameter tracking
                self.current_parameter_index = i + 1
                self.current_parameter_name = param_name
                
                # Create detailed status text with progress information
                status_text = self.i18n.get('config_read_progress', 
                                          'Reading {param_name}... ({current}/{total})').format(
                    param_name=param_name,
                    current=self.current_parameter_index,
                    total=total_commands
                )
                
                # Update progress dialog with enhanced information
                if self.progress_dialog_id and hasattr(self.app, 'operation_confirmation_service'):
                    try:
                        # Create detailed status with success/failure counts
                        detailed_status = (f"Reading: {param_name}\n"
                                         f"Progress: {self.current_parameter_index}/{total_commands} parameters\n"
                                         f"Success: {self.successful_reads_count} | Failed: {self.failed_reads_count}")
                        
                        self.app.after(0, self.app.operation_confirmation_service.update_progress,
                                      self.progress_dialog_id, self.current_parameter_index, detailed_status)
                    except Exception as e:
                        self._log_message(f"WARNING: Failed to update progress dialog: {str(e)}")
                
                # Call custom progress callback with enhanced information
                if self.progress_callback:
                    progress_info = {
                        'current_step': self.current_parameter_index,
                        'total_steps': total_commands,
                        'current_parameter': param_name,
                        'successful_count': self.successful_reads_count,
                        'failed_count': self.failed_reads_count,
                        'status_text': status_text,
                        'can_cancel': True
                    }
                    self.app.after(0, self.progress_callback, progress_info)
                
                # Log the command being sent for debugging
                self._log_message(f"DEBUG: Sending command for {param_name}: {command} (type: {command_type})")
                # Read the parameter with enhanced error handling
                result = self.read_specific_parameter_with_error_handling(param_name, command, command_type, max_retries=2)
                parameters_read.append(result)
                
                if not result.success:
                    failed_parameters.append(param_name)
                    self.failed_reads_count += 1
                    error_msg = self._get_specific_error_message(param_name, result.error_message)
                    self._log_message(f"WARNING: Failed to read {param_name}: {error_msg}")
                    
                    # Log additional error context if available
                    if hasattr(result, 'error_context') and result.error_context:
                        self._log_message(f"DEBUG: Error context: {result.error_context}")
                else:
                    self.successful_reads_count += 1
                    self._log_message(f"INFO: Successfully read {param_name}: {result.value}")
                    
                    # Update last successful operation timestamp
                    if self.parameter_error_handler:
                        self.parameter_error_handler.last_successful_operation = datetime.now()
                
                # Add delay between commands to avoid overwhelming the device
                if i < total_commands - 1:  # Don't delay after the last command
                    time.sleep(0.8)
            
            # Calculate results
            read_duration = time.time() - start_time
            successful_reads = self.successful_reads_count
            failed_reads = self.failed_reads_count
            success = successful_reads > 0  # Success if at least one parameter was read
            
            # Set completion message with detailed results and statistics
            if failed_reads == 0:
                completion_message = (f"✓ Configuration reading completed successfully!\n"
                                    f"All {successful_reads} parameters read successfully\n"
                                    f"Duration: {read_duration:.1f} seconds")
            elif successful_reads > 0:
                completion_message = (f"⚠ Configuration reading partially completed\n"
                                    f"Success: {successful_reads} | Failed: {failed_reads}\n"
                                    f"Total: {successful_reads + failed_reads} parameters\n"
                                    f"Duration: {read_duration:.1f} seconds")
            else:
                completion_message = (f"✗ Configuration reading failed\n"
                                    f"No parameters could be read ({failed_reads} failures)\n"
                                    f"Duration: {read_duration:.1f} seconds")
            
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
                # Also update the profile manager with the read parameters
                self._update_profile_manager_with_parameters(parameters_read)
            
            # Call completion callback
            if self.completion_callback:
                error_msg = None
                if failed_parameters:
                    error_msg = f"Failed to read {len(failed_parameters)} parameters"
                self.completion_callback(result, error_msg)
            
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
                self.completion_callback(result, error_msg)
        
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
        Update UI with parameters read from the device based on specification.
        
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
            
            # Group parameters by parsed data for efficient processing
            parsed_parameters = {}
            for result in parameters_read:
                if result.success and result.raw_response:
                    # Parse the response to get all field values
                    parsed_response = self.parse_device_response(
                        result.parameter_name, 
                        result.raw_response, 
                        self._get_command_type_for_parameter(result.parameter_name)
                    )
                    if parsed_response.success:
                        parsed_parameters[result.parameter_name] = parsed_response.parsed_values
            
            # Update UI fields based on parsed parameters
            self._update_ui_fields_from_parsed_data(parsed_parameters)
            
            # Handle conditional field updates
            self._handle_conditional_field_updates(parsed_parameters)
            
            # Log successful UI updates
            updated_count = len([r for r in parameters_read if r.success])
            self._log_message(f"INFO: Successfully updated UI with {updated_count} parameters")
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to update UI with parameters: {str(e)}")

    def _update_profile_manager_with_parameters(self, parameters_read):
        """
        Update the profile manager's current profile with parameters read from the device.
        
        Args:
            parameters_read: List of parameter read results
        """
        try:
            # Check if profile manager is available
            if not hasattr(self.app, 'profile_manager') or not self.app.profile_manager:
                self._log_message("DEBUG: Profile manager not available, skipping profile update")
                return
            
            # Create a profile from the read parameters
            from models.universal_profile import UniversalProfile, ProfileMetadata, ParameterValue
            from datetime import datetime
            
            # Create metadata
            metadata = ProfileMetadata(
                parameter_spec_version="1.0",
                created_by="LT32 PRO Configurator - Check Configuration",
                device_model="LT32 PRO"
            )
            
            # Convert read parameters to ParameterValue objects
            parameter_values = {}
            successful_reads = 0
            
            for result in parameters_read:
                if result.success and result.raw_response:
                    # Parse the response to get all field values
                    parsed_response = self.parse_device_response(
                        result.parameter_name, 
                        result.raw_response, 
                        self._get_command_type_for_parameter(result.parameter_name)
                    )
                    
                    if parsed_response.success:
                        # Get the section mapping for this parameter
                        parameter_mapping = self._get_parameter_section_mapping()
                        section_info = parameter_mapping.get(result.parameter_name)
                        
                        if section_info:
                            section_name = section_info['section']
                            param_name = section_info['parameter']
                            full_param_name = f"{section_name}.{param_name}"
                        else:
                            # Fallback to original parameter name
                            full_param_name = result.parameter_name
                        
                        # Create parameter value based on the parsed data
                        if isinstance(parsed_response.parsed_values, dict) and len(parsed_response.parsed_values) > 1:
                            # Complex parameter with multiple fields - create individual field parameters
                            for field_name, field_value in parsed_response.parsed_values.items():
                                field_param_name = f"{full_param_name}.{field_name}"
                                
                                # Clean time parameter values to show only numeric values
                                if result.parameter_name in ['report_intervals', 'heartbeat_intervals']:
                                    field_value = self._extract_numeric_value_from_time_string(field_value)
                                
                                parameter_values[field_param_name] = ParameterValue(
                                    value=field_value,
                                    source="device"
                                )
                        else:
                            # Simple parameter with single value
                            # For parameters like odometer and hourmeter, extract the actual value
                            if result.parameter_name in ['odometer', 'hourmeter'] and isinstance(parsed_response.parsed_values, dict):
                                # Extract the actual value from the dictionary
                                value = parsed_response.parsed_values.get(result.parameter_name, "")
                            else:
                                value = result.value or list(parsed_response.parsed_values.values())[0] if parsed_response.parsed_values else ""
                            
                            parameter_values[full_param_name] = ParameterValue(
                                value=value,
                                source="device"
                            )
                        successful_reads += 1
            
            if successful_reads > 0:
                # Create the profile
                now = datetime.now()
                profile = UniversalProfile(
                    name=f"Device Configuration {now.strftime('%Y-%m-%d %H:%M:%S')}",
                    version="1.0",
                    created_at=now,
                    modified_at=now,
                    metadata=metadata,
                    parameters=parameter_values
                )
                
                # Set as current profile in the profile manager
                self.app.profile_manager.set_current_profile(profile)
                self._log_message(f"INFO: Updated profile manager with {successful_reads} parameters from device")
            else:
                self._log_message("WARNING: No successful parameter reads to update profile manager")
                
        except Exception as e:
            self._log_message(f"ERROR: Failed to update profile manager with parameters: {str(e)}")

    def _extract_numeric_value_from_time_string(self, time_string: str) -> str:
        """
        Extract numeric value from time parameter strings.
        
        Examples:
        - "60s" -> "60"
        - "ACC OFF:120s" -> "120"
        - "180" -> "180"
        
        Args:
            time_string: Time string that may contain units and prefixes
            
        Returns:
            str: Numeric value only
        """
        if not time_string:
            return ""
        
        # Extract all digits from the string
        import re
        digits = re.findall(r'\d+', str(time_string))
        
        # Return the last number found (handles cases like "ACC OFF:120s")
        return digits[-1] if digits else ""

    def _update_ui_fields_from_parsed_data(self, parsed_parameters: Dict[str, Dict[str, Any]]):
        """
        Update UI fields from parsed parameter data.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            self._log_message(f"DEBUG: Starting UI field updates for {len(parsed_parameters)} parameters")
            
            # Debug: Log all parsed parameters and their structure
            for param_name, param_data in parsed_parameters.items():
                self._log_message(f"DEBUG: Parsed parameter '{param_name}': {param_data}")
            
            # Check if parameters frame has the specification-based update method
            if hasattr(self.app.parameters_frame, 'parameter_specification_factory'):
                self._log_message("DEBUG: Using specification-based update method")
                def update_fields():
                    try:
                        self._update_specification_based_fields(parsed_parameters)
                        self._log_message("DEBUG: Updated parameter fields using specification-based method")
                    except Exception as e:
                        self._log_message(f"ERROR: Failed to update specification-based fields: {str(e)}")
                        # Fallback to individual field updates
                        self._log_message("DEBUG: Falling back to individual field updates")
                        self._update_individual_fields(parsed_parameters)
                
                self.app.after(0, update_fields)
            else:
                # Fallback to individual field updates
                self._log_message("DEBUG: Using individual field updates (no specification factory)")
                self._update_individual_fields(parsed_parameters)
                
        except Exception as e:
            self._log_message(f"ERROR: Failed to update UI fields: {str(e)}")

    def _update_specification_based_fields(self, parsed_parameters: Dict[str, Dict[str, Any]]):
        """
        Update UI fields using the specification-based parameter factory.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            parameters_frame = self.app.parameters_frame
            section_widgets = parameters_frame.section_widgets
            factory = parameters_frame.parameter_specification_factory
            
            # Track updated parameters for logging and visual feedback
            updated_parameters = []
            update_timestamp = datetime.now()
            
            # Map parameter names to section/parameter structure
            parameter_mapping = self._get_parameter_section_mapping()
            
            for param_name, parsed_values in parsed_parameters.items():
                try:
                    # Get section and parameter name from mapping
                    section_info = parameter_mapping.get(param_name)
                    if not section_info:
                        self._log_message(f"WARNING: No section mapping found for parameter {param_name}")
                        continue
                    
                    section_name = section_info['section']
                    param_key = section_info['parameter']
                    
                    # Get current value to check if it changed
                    current_value = factory.get_parameter_value(section_name, param_key, section_widgets)
                    
                    # Determine the correct value to set based on parameter type
                    section_widget = section_widgets[section_name]
                    param_widget = section_widget.parameters[param_key]
                    
                    if param_widget.widget_type == 'simple':
                        # For simple parameters, extract the value from the parsed_values dict
                        # The parsed_values dict has the format: {'param_name': 'value'}
                        if param_key in parsed_values:
                            raw_value = parsed_values[param_key]
                        else:
                            # Fallback: if the key doesn't match, try to get the first value
                            raw_value = next(iter(parsed_values.values())) if parsed_values else None
                        
                        # Convert value based on UI element type
                        value_to_set = self._convert_value_for_ui_element(raw_value, param_widget)
                    else:
                        # For complex parameters, pass the entire parsed_values dict
                        value_to_set = parsed_values
                    
                    # Update the parameter value
                    if value_to_set is not None:
                        factory.set_parameter_value(section_name, param_key, value_to_set, section_widgets)
                    
                    # Check if value actually changed
                    new_value = factory.get_parameter_value(section_name, param_key, section_widgets)
                    value_changed = current_value != new_value
                    
                    # Add visual indicator for updated field
                    self._add_visual_update_indicator(section_name, param_key, value_changed)
                    
                    # Log the parameter update
                    self._log_parameter_update(param_name, current_value, new_value, value_changed, update_timestamp)
                    
                    updated_parameters.append({
                        'parameter': param_name,
                        'section': section_name,
                        'param_key': param_key,
                        'old_value': current_value,
                        'new_value': new_value,
                        'changed': value_changed
                    })
                    
                except Exception as e:
                    self._log_message(f"ERROR: Failed to update parameter {param_name}: {str(e)}")
            
            # Log summary of updates
            changed_count = sum(1 for p in updated_parameters if p['changed'])
            unchanged_count = len(updated_parameters) - changed_count
            
            self._log_message(f"INFO: UI field update summary - {changed_count} changed, {unchanged_count} unchanged, {len(updated_parameters)} total")
            
            # Store update information for potential export
            self._store_update_session_info(updated_parameters, update_timestamp)
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to update specification-based fields: {str(e)}")
            raise

    def _get_parameter_section_mapping(self) -> Dict[str, Dict[str, str]]:
        """
        Get mapping of parameter names to their section and parameter keys.
        
        Returns:
            Dictionary mapping parameter names to section info
        """
        return {
            # Network Parameters
            'apn_settings': {'section': 'network_parameters', 'parameter': 'apn_settings'},
            'server_settings': {'section': 'network_parameters', 'parameter': 'server_settings'},
            
            # Time Parameters
            'report_intervals': {'section': 'time_parameters', 'parameter': 'report_intervals'},
            'heartbeat_intervals': {'section': 'time_parameters', 'parameter': 'heartbeat_intervals'},
            
            # Service Parameters
            'protocol': {'section': 'service_parameters', 'parameter': 'protocol'},
            'tcp_ack': {'section': 'service_parameters', 'parameter': 'tcp_ack'},
            
            # Ignition Parameters
            'ignition_type': {'section': 'ignition', 'parameter': 'ignition_type'},
            
            # Speed Parameters
            'speed_alert': {'section': 'speed', 'parameter': 'speed_alert'},
            'speed_buzzer': {'section': 'speed', 'parameter': 'speed_buzzer'},
            
            # Power Saving Parameters
            'sleep_mode': {'section': 'power_saving', 'parameter': 'sleep_mode'},
            'sleep_time': {'section': 'power_saving', 'parameter': 'sleep_time'},
            
            # Angle Parameters
            'angle_report': {'section': 'angle', 'parameter': 'angle_report'},
            
            # Battery Alert Parameters
            'backup_battery_alert': {'section': 'battery_alerts', 'parameter': 'backup_battery_alert'},
            'main_power_alert': {'section': 'battery_alerts', 'parameter': 'main_power_alert'},
            
            # Vibration Sensor Parameters
            'vibration_sensitivity': {'section': 'vibration_sensor', 'parameter': 'vibration_sensitivity'},
            
            # Jammer Detection Parameters
            'jammer_detection': {'section': 'jammer_detection', 'parameter': 'jammer_detection'},
            'jammer_relay_action': {'section': 'jammer_detection', 'parameter': 'jammer_relay_action'},
            
            # Miscellaneous Parameters
            'odometer': {'section': 'miscellaneous', 'parameter': 'odometer'},
            'hourmeter': {'section': 'miscellaneous', 'parameter': 'hourmeter'}
        }

    def _is_time_parameter(self, param_widget) -> bool:
        """
        Check if a parameter widget represents a time parameter that needs cleaning.
        
        Args:
            param_widget: Parameter widget to check
            
        Returns:
            bool: True if this is a time parameter that needs numeric cleaning
        """
        try:
            # Get the parameter key/name from the widget
            param_key = getattr(param_widget, 'key', '')
            param_name = getattr(param_widget, 'name', '')
            
            self._log_message(f"DEBUG: Checking if parameter is time parameter - key: '{param_key}', name: '{param_name}'")
            
            # List of time parameter identifiers that need cleaning
            time_parameter_keys = [
                # Report interval parameters
                'moving_time', 'stopped_time', 
                'report_moving_time', 'report_stopped_time',
                
                # Heartbeat interval parameters
                'moving_heartbeat', 'stopped_heartbeat',
                'heartbeat_moving_time', 'heartbeat_stopped_time',
                
                # Sleep and power saving time parameters
                'sleep_time',
                
                # Speed detection time parameters
                'speed_detection_time', 'detection_time',
                
                # Power detection time parameters
                'power_detection_time',
                
                # Charge time parameters
                'min_charge_time',
                
                # Jammer confirmation time
                'jammer_confirmation_time'
            ]
            
            # Check if the parameter key or name matches any time parameter
            is_time_param = param_key in time_parameter_keys or param_name in time_parameter_keys
            self._log_message(f"DEBUG: Parameter '{param_key}'/'{param_name}' is time parameter: {is_time_param}")
            return is_time_param
            
        except Exception as e:
            self._log_message(f"WARNING: Error checking if parameter is time parameter: {str(e)}")
            return False

    def _convert_value_for_ui_element(self, raw_value: Any, param_widget) -> Any:
        """
        Convert raw parsed value to the format expected by the UI element.
        
        Args:
            raw_value: Raw value from parameter parsing
            param_widget: Parameter widget containing UI element information
            
        Returns:
            Converted value appropriate for the UI element type
        """
        if raw_value is None:
            return None
        
        # Apply time parameter cleaning for time-related parameters
        if self._is_time_parameter(param_widget):
            if isinstance(raw_value, str):
                cleaned_value = self._extract_numeric_value_from_time_string(raw_value)
                self._log_message(f"DEBUG: Time parameter cleaning applied - '{raw_value}' -> '{cleaned_value}'")
                raw_value = cleaned_value
            else:
                self._log_message(f"DEBUG: Time parameter detected but value is not string: {type(raw_value)} = {raw_value}")
        else:
            self._log_message(f"DEBUG: Not a time parameter, no cleaning applied for value: {raw_value}")
        
        # Get the UI element configuration
        ui_element = param_widget.ui_elements.get('main')
        if not ui_element:
            return raw_value
        
        element_type = ui_element.config.element_type
        
        # Convert based on UI element type
        if element_type == 'toggle_switch':
            # Convert string values to boolean for toggle switches
            if isinstance(raw_value, str):
                # Handle common string representations
                if raw_value.lower() in ['enabled', 'on', 'true', '1', 'yes']:
                    return True
                elif raw_value.lower() in ['disabled', 'off', 'false', '0', 'no']:
                    return False
                else:
                    # Fallback: try to convert to boolean
                    return bool(raw_value)
            else:
                # For non-string values, convert to boolean
                return bool(raw_value)
        
        elif element_type == 'number_input':
            # Convert to number for number inputs
            if isinstance(raw_value, str):
                try:
                    # Try integer first, then float
                    if '.' in raw_value:
                        return float(raw_value)
                    else:
                        return int(raw_value)
                except ValueError:
                    return raw_value
            else:
                return raw_value
        
        elif element_type == 'slider':
            # Convert to number for sliders
            if isinstance(raw_value, str):
                try:
                    return int(raw_value)
                except ValueError:
                    return raw_value
            else:
                return raw_value
        
        else:
            # For other element types (dropdown, text_input, password_input), return as-is
            return raw_value

    def _add_visual_update_indicator(self, section_name: str, param_key: str, value_changed: bool):
        """
        Add visual indicator to show which fields were updated from device.
        
        Args:
            section_name: Name of the parameter section
            param_key: Key of the parameter within the section
            value_changed: True if the value changed, False if it was the same
        """
        try:
            parameters_frame = self.app.parameters_frame
            
            # Use the existing highlight method if available
            if hasattr(parameters_frame, 'highlight_updated_parameter'):
                full_param_name = f"{section_name}.{param_key}"
                parameters_frame.highlight_updated_parameter(full_param_name, value_changed)
            else:
                # Fallback to direct widget highlighting
                self._highlight_parameter_widget(section_name, param_key, value_changed)
                
        except Exception as e:
            self._log_message(f"WARNING: Failed to add visual indicator for {section_name}.{param_key}: {str(e)}")

    def _highlight_parameter_widget(self, section_name: str, param_key: str, value_changed: bool):
        """
        Directly highlight a parameter widget.
        
        Args:
            section_name: Name of the parameter section
            param_key: Key of the parameter within the section
            value_changed: True if the value changed, False if it was the same
        """
        try:
            parameters_frame = self.app.parameters_frame
            
            if hasattr(parameters_frame, 'section_widgets'):
                section_widgets = parameters_frame.section_widgets
                
                if section_name in section_widgets:
                    section_widget = section_widgets[section_name]
                    
                    if param_key in section_widget.parameters:
                        param_widget = section_widget.parameters[param_key]
                        container_frame = param_widget.container_frame
                        
                        # Apply visual highlighting - safely check if configure method exists
                        if hasattr(container_frame, 'configure'):
                            if value_changed:
                                # Green border for changed values
                                container_frame.configure(border_color="#00ff00", border_width=2)
                                # Schedule removal after 3 seconds
                                self.app.after(3000, lambda: self._remove_widget_highlight(container_frame))
                            else:
                                # Blue border for unchanged values
                                container_frame.configure(border_color="#0066cc", border_width=1)
                                # Schedule removal after 2 seconds
                                self.app.after(2000, lambda: self._remove_widget_highlight(container_frame))
                        else:
                            # Log that highlighting is not supported for this widget type
                            widget_type = type(container_frame).__name__
                            self._log_message(f"DEBUG: Widget highlighting not supported for {widget_type} ({section_name}.{param_key})")
                            
        except Exception as e:
            self._log_message(f"WARNING: Failed to highlight parameter widget {section_name}.{param_key}: {str(e)}")

    def _remove_widget_highlight(self, widget):
        """Remove highlight from a widget."""
        try:
            if hasattr(widget, 'configure'):
                widget.configure(border_color="gray", border_width=0)
        except Exception as e:
            self._log_message(f"WARNING: Failed to remove widget highlight: {str(e)}")

    def _log_parameter_update(self, param_name: str, old_value: Any, new_value: Any, value_changed: bool, timestamp: datetime):
        """
        Log a parameter update with timestamps and values.
        
        Args:
            param_name: Name of the parameter
            old_value: Previous value
            new_value: New value from device
            value_changed: Whether the value actually changed
            timestamp: Timestamp of the update
        """
        try:
            status = "CHANGED" if value_changed else "UNCHANGED"
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            # Format values for logging
            old_str = self._format_value_for_logging(old_value)
            new_str = self._format_value_for_logging(new_value)
            
            log_message = f"PARAM_UPDATE [{timestamp_str}] {param_name}: {status} | Old: {old_str} | New: {new_str}"
            self._log_message(log_message)
            
            # Also log to a separate parameter update log if available
            if hasattr(self, 'parameter_update_log'):
                self.parameter_update_log.append({
                    'timestamp': timestamp,
                    'parameter': param_name,
                    'old_value': old_value,
                    'new_value': new_value,
                    'changed': value_changed
                })
            else:
                # Initialize parameter update log
                self.parameter_update_log = [{
                    'timestamp': timestamp,
                    'parameter': param_name,
                    'old_value': old_value,
                    'new_value': new_value,
                    'changed': value_changed
                }]
                
        except Exception as e:
            self._log_message(f"WARNING: Failed to log parameter update for {param_name}: {str(e)}")

    def _format_value_for_logging(self, value: Any) -> str:
        """
        Format a value for logging display.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted string representation
        """
        if value is None:
            return "None"
        elif isinstance(value, dict):
            # Format dictionary values compactly
            items = [f"{k}={v}" for k, v in value.items()]
            return "{" + ", ".join(items) + "}"
        elif isinstance(value, str):
            return f'"{value}"'
        else:
            return str(value)

    def _store_update_session_info(self, updated_parameters: List[Dict[str, Any]], timestamp: datetime):
        """
        Store information about the update session for potential export.
        
        Args:
            updated_parameters: List of parameter update information
            timestamp: Session timestamp
        """
        try:
            session_info = {
                'timestamp': timestamp,
                'total_parameters': len(updated_parameters),
                'changed_parameters': [p for p in updated_parameters if p['changed']],
                'unchanged_parameters': [p for p in updated_parameters if not p['changed']],
                'session_id': f"config_read_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            }
            
            # Store in instance for potential export
            if not hasattr(self, 'update_sessions'):
                self.update_sessions = []
            
            self.update_sessions.append(session_info)
            
            # Keep only the last 10 sessions to avoid memory issues
            if len(self.update_sessions) > 10:
                self.update_sessions = self.update_sessions[-10:]
                
        except Exception as e:
            self._log_message(f"WARNING: Failed to store update session info: {str(e)}")

    def _update_individual_fields(self, parsed_parameters: Dict[str, Dict[str, Any]]):
        """
        Update individual UI fields when bulk update is not available.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            self._log_message(f"DEBUG: Starting individual field updates for {len(parsed_parameters)} parameters")
            
            # Debug: Log all parameters being processed
            for param_name in parsed_parameters.keys():
                self._log_message(f"DEBUG: Processing individual field update for: {param_name}")
            # Network Parameters
            if 'apn_settings' in parsed_parameters:
                apn_data = parsed_parameters['apn_settings']
                if hasattr(self.app.parameters_frame, 'update_apn_fields'):
                    def update_apn():
                        try:
                            self.app.parameters_frame.update_apn_fields(
                                server=apn_data.get('apn', ''),
                                user=apn_data.get('user', ''),
                                password=apn_data.get('password', '')
                            )
                            self._log_message(f"DEBUG: Updated APN fields")
                        except Exception as e:
                            self._log_message(f"ERROR: Failed to update APN fields: {str(e)}")
                    
                    self.app.after(0, update_apn)
            
            # Server Settings
            if 'server_settings' in parsed_parameters:
                server_data = parsed_parameters['server_settings']
                self._update_widget_value('server_ip', server_data.get('address', ''))
                self._update_widget_value('server_port', server_data.get('port', ''))
            
            # Time Parameters
            if 'report_intervals' in parsed_parameters:
                timer_data = parsed_parameters['report_intervals']
                # Clean time parameter values to show only numeric values
                moving_time_raw = timer_data.get('moving_time', '')
                stopped_time_raw = timer_data.get('stopped_time', '')
                moving_time_clean = self._extract_numeric_value_from_time_string(moving_time_raw)
                stopped_time_clean = self._extract_numeric_value_from_time_string(stopped_time_raw)
                
                self._log_message(f"DEBUG: Time parameter transformation - moving_time: '{moving_time_raw}' -> '{moving_time_clean}'")
                self._log_message(f"DEBUG: Time parameter transformation - stopped_time: '{stopped_time_raw}' -> '{stopped_time_clean}'")
                
                self._update_widget_value('moving_time', moving_time_clean)
                self._update_widget_value('stopped_time', stopped_time_clean)
            
            if 'heartbeat_intervals' in parsed_parameters:
                hbt_data = parsed_parameters['heartbeat_intervals']
                # Clean time parameter values to show only numeric values
                moving_heartbeat_raw = hbt_data.get('moving_heartbeat', '')
                stopped_heartbeat_raw = hbt_data.get('stopped_heartbeat', '')
                moving_heartbeat_clean = self._extract_numeric_value_from_time_string(moving_heartbeat_raw)
                stopped_heartbeat_clean = self._extract_numeric_value_from_time_string(stopped_heartbeat_raw)
                
                self._log_message(f"DEBUG: Time parameter transformation - moving_heartbeat: '{moving_heartbeat_raw}' -> '{moving_heartbeat_clean}'")
                self._log_message(f"DEBUG: Time parameter transformation - stopped_heartbeat: '{stopped_heartbeat_raw}' -> '{stopped_heartbeat_clean}'")
                
                self._update_widget_value('moving_heartbeat', moving_heartbeat_clean)
                self._update_widget_value('stopped_heartbeat', stopped_heartbeat_clean)
            
            # Service Parameters
            if 'protocol' in parsed_parameters:
                protocol_data = parsed_parameters['protocol']
                self._update_widget_value('protocol', protocol_data.get('protocol', ''))
            
            if 'tcp_ack' in parsed_parameters:
                tcp_ack_data = parsed_parameters['tcp_ack']
                self._update_widget_value('tcp_ack', tcp_ack_data.get('tcp_ack', ''))
            
            # Vibration Sensor
            if 'vibration_sensitivity' in parsed_parameters:
                vib_data = parsed_parameters['vibration_sensitivity']
                self._update_widget_value('vibration_level', vib_data.get('level', ''))
                self._update_widget_value('vibration_enabled', vib_data.get('enabled', False))
            
            # Power Saving Parameters
            if 'sleep_time' in parsed_parameters:
                sleep_data = parsed_parameters['sleep_time']
                # Clean time parameter values to show only numeric values
                sleep_time_raw = sleep_data.get('sleep_time', '')
                sleep_time_clean = self._extract_numeric_value_from_time_string(sleep_time_raw)
                
                self._log_message(f"DEBUG: Time parameter transformation - sleep_time: '{sleep_time_raw}' -> '{sleep_time_clean}'")
                
                self._update_widget_value('sleep_time', sleep_time_clean)
            
            # Miscellaneous Parameters - Enhanced odometer handling
            if 'odometer' in parsed_parameters:
                odo_data = parsed_parameters['odometer']
                odometer_value = odo_data.get('odometer', '')
                self._log_message(f"DEBUG: Processing odometer parameter update - raw value: '{odometer_value}'")
                
                # Try specification-based update first
                if self._update_parameter_via_specification('miscellaneous', 'odometer', odometer_value):
                    self._log_message(f"DEBUG: Successfully updated odometer via specification method: {odometer_value}")
                else:
                    # Fallback to legacy widget update
                    self._log_message(f"DEBUG: Falling back to legacy widget update for odometer")
                    self._update_widget_value('odometer', odometer_value)
            
            # Enhanced hourmeter handling
            if 'hourmeter' in parsed_parameters:
                hour_data = parsed_parameters['hourmeter']
                hourmeter_value = hour_data.get('hourmeter', '')
                self._log_message(f"DEBUG: Processing hourmeter parameter update - raw value: '{hourmeter_value}'")
                
                # Try specification-based update first
                if self._update_parameter_via_specification('miscellaneous', 'hourmeter', hourmeter_value):
                    self._log_message(f"DEBUG: Successfully updated hourmeter via specification method: {hourmeter_value}")
                else:
                    # Fallback to legacy widget update
                    self._log_message(f"DEBUG: Falling back to legacy widget update for hourmeter")
                    self._update_widget_value('hourmeter', hourmeter_value)
            
            # Add more parameter updates as needed...
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to update individual fields: {str(e)}")

    def _update_parameter_via_specification(self, section_name: str, param_name: str, value: Any) -> bool:
        """
        Update a parameter using the specification-based method.
        
        Args:
            section_name: Name of the parameter section
            param_name: Name of the parameter
            value: Value to set
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Check if specification factory is available
            if not hasattr(self.app.parameters_frame, 'parameter_specification_factory'):
                self._log_message(f"DEBUG: No specification factory available for {section_name}.{param_name}")
                return False
            
            # Check if section widgets are available
            if not hasattr(self.app.parameters_frame, 'section_widgets'):
                self._log_message(f"DEBUG: No section widgets available for {section_name}.{param_name}")
                return False
            
            factory = self.app.parameters_frame.parameter_specification_factory
            section_widgets = self.app.parameters_frame.section_widgets
            
            # Check if the section exists
            if section_name not in section_widgets:
                self._log_message(f"DEBUG: Section '{section_name}' not found in section widgets")
                return False
            
            # Check if the parameter exists in the section
            section_widget = section_widgets[section_name]
            if param_name not in section_widget.parameters:
                self._log_message(f"DEBUG: Parameter '{param_name}' not found in section '{section_name}'")
                return False
            
            # Get current value for comparison
            current_value = factory.get_parameter_value(section_name, param_name, section_widgets)
            
            # Set the new value
            def update_parameter():
                try:
                    factory.set_parameter_value(section_name, param_name, value, section_widgets)
                    
                    # Verify the update
                    new_value = factory.get_parameter_value(section_name, param_name, section_widgets)
                    
                    # Log the update
                    self._log_message(f"DEBUG: Parameter {section_name}.{param_name} updated: '{current_value}' -> '{new_value}'")
                    
                    # Add visual indicator if available
                    self._add_visual_update_indicator(section_name, param_name, current_value != new_value)
                    
                except Exception as e:
                    self._log_message(f"ERROR: Failed to set parameter {section_name}.{param_name}: {str(e)}")
                    raise
            
            # Schedule the update on the main thread
            self.app.after(0, update_parameter)
            return True
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to update parameter {section_name}.{param_name} via specification: {str(e)}")
            return False

    def _update_widget_value(self, widget_name: str, value: Any):
        """
        Update a specific widget value using legacy method.
        
        Args:
            widget_name: Name of the widget to update
            value: Value to set
        """
        try:
            self._log_message(f"DEBUG: Attempting legacy widget update for {widget_name} = {value}")
            
            # Try parameter_widgets first (legacy approach)
            if hasattr(self.app.parameters_frame, 'parameter_widgets'):
                widgets = self.app.parameters_frame.parameter_widgets
                if widget_name in widgets:
                    widget = widgets[widget_name]
                    if hasattr(widget, 'set_value'):
                        def update_widget():
                            try:
                                widget.set_value(value)
                                self._log_message(f"DEBUG: Updated {widget_name} to {value} via parameter_widgets")
                            except Exception as e:
                                self._log_message(f"ERROR: Failed to update {widget_name} via parameter_widgets: {str(e)}")
                        
                        self.app.after(0, update_widget)
                        return
                    else:
                        self._log_message(f"DEBUG: Widget {widget_name} found but has no set_value method")
                else:
                    self._log_message(f"DEBUG: Widget {widget_name} not found in parameter_widgets")
            else:
                self._log_message(f"DEBUG: No parameter_widgets attribute found")
            
            # If legacy approach failed, log the issue
            self._log_message(f"WARNING: Could not update widget {widget_name} - widget not found or not accessible")
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to update widget {widget_name}: {str(e)}")

    def _handle_conditional_field_updates(self, parsed_parameters: Dict[str, Dict[str, Any]]):
        """
        Handle conditional field visibility updates based on parameter values.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            # Check if conditional field manager is available
            if hasattr(self.app.parameters_frame, 'parameter_specification_factory'):
                def update_conditional_fields():
                    try:
                        self._update_conditional_field_visibility(parsed_parameters)
                        self._log_message("DEBUG: Updated conditional field visibility")
                    except Exception as e:
                        self._log_message(f"ERROR: Failed to update conditional fields: {str(e)}")
                
                self.app.after(0, update_conditional_fields)
            else:
                # Fallback to legacy conditional field handling
                self._handle_legacy_conditional_fields(parsed_parameters)
                
        except Exception as e:
            self._log_message(f"ERROR: Failed to handle conditional field updates: {str(e)}")

    def _update_conditional_field_visibility(self, parsed_parameters: Dict[str, Dict[str, Any]]):
        """
        Update conditional field visibility using the specification-based system.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            parameters_frame = self.app.parameters_frame
            factory = parameters_frame.parameter_specification_factory
            conditional_manager = factory.conditional_field_manager
            
            # Track conditional field updates for logging
            conditional_updates = []
            
            # Process ignition type conditional fields
            if 'ignition_type' in parsed_parameters:
                ignition_data = parsed_parameters['ignition_type']
                ignition_mode = ignition_data.get('ignition_mode', '')
                
                self._log_message(f"DEBUG: Processing ignition conditional fields - mode: {ignition_mode}")
                
                # Determine if voltage fields should be visible
                show_voltage_fields = 'Virtual por bateria' in ignition_mode or 'Virtual by battery' in ignition_mode
                
                # Update field visibility
                voltage_fields = ['ignition_type.on_voltage', 'ignition_type.off_voltage']
                for field_name in voltage_fields:
                    try:
                        conditional_manager.update_field_visibility(field_name, show_voltage_fields)
                        conditional_updates.append({
                            'field': field_name,
                            'visible': show_voltage_fields,
                            'trigger': 'ignition_mode',
                            'trigger_value': ignition_mode
                        })
                        self._log_message(f"DEBUG: Set {field_name} visibility to {show_voltage_fields}")
                    except Exception as e:
                        self._log_message(f"WARNING: Failed to update visibility for {field_name}: {str(e)}")
            
            # Process speed alert conditional fields
            if 'speed_alert' in parsed_parameters:
                speed_data = parsed_parameters['speed_alert']
                speed_enabled = speed_data.get('enabled', False)
                
                self._log_message(f"DEBUG: Processing speed alert conditional fields - enabled: {speed_enabled}")
                
                # Update speed alert field visibility
                speed_fields = ['speed_alert.detection_time', 'speed_alert.speed_limit', 'speed_alert.alert_type']
                for field_name in speed_fields:
                    try:
                        conditional_manager.update_field_visibility(field_name, speed_enabled)
                        conditional_updates.append({
                            'field': field_name,
                            'visible': speed_enabled,
                            'trigger': 'speed_enabled',
                            'trigger_value': speed_enabled
                        })
                    except Exception as e:
                        self._log_message(f"WARNING: Failed to update visibility for {field_name}: {str(e)}")
            
            # Process angle report conditional fields
            if 'angle_report' in parsed_parameters:
                angle_data = parsed_parameters['angle_report']
                angle_enabled = angle_data.get('enabled', False)
                
                self._log_message(f"DEBUG: Processing angle report conditional fields - enabled: {angle_enabled}")
                
                # Update angle report field visibility
                angle_fields = ['angle_report.min_speed', 'angle_report.angle_variation']
                for field_name in angle_fields:
                    try:
                        conditional_manager.update_field_visibility(field_name, angle_enabled)
                        conditional_updates.append({
                            'field': field_name,
                            'visible': angle_enabled,
                            'trigger': 'angle_enabled',
                            'trigger_value': angle_enabled
                        })
                    except Exception as e:
                        self._log_message(f"WARNING: Failed to update visibility for {field_name}: {str(e)}")
            
            # Log conditional field update summary
            if conditional_updates:
                visible_count = sum(1 for u in conditional_updates if u['visible'])
                hidden_count = len(conditional_updates) - visible_count
                self._log_message(f"INFO: Conditional field updates - {visible_count} shown, {hidden_count} hidden")
                
                # Store conditional update information
                self._store_conditional_update_info(conditional_updates)
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to update conditional field visibility: {str(e)}")
            raise

    def _handle_legacy_conditional_fields(self, parsed_parameters: Dict[str, Dict[str, Any]]):
        """
        Handle conditional fields using legacy methods.
        
        Args:
            parsed_parameters: Dictionary of parameter names to parsed values
        """
        try:
            # Legacy ignition voltage field handling
            if 'ignition_type' in parsed_parameters:
                ignition_data = parsed_parameters['ignition_type']
                ignition_mode = ignition_data.get('ignition_mode', '')
                
                # Show/hide voltage fields based on ignition mode
                show_voltage = 'Virtual por bateria' in ignition_mode
                
                if hasattr(self.app.parameters_frame, 'conditional_field_manager'):
                    self.app.parameters_frame.conditional_field_manager.update_field_visibility(
                        'on_voltage', show_voltage
                    )
                    self.app.parameters_frame.conditional_field_manager.update_field_visibility(
                        'off_voltage', show_voltage
                    )
                
                # Update voltage values if available
                if show_voltage:
                    self._update_widget_value('on_voltage', ignition_data.get('on_voltage', ''))
                    self._update_widget_value('off_voltage', ignition_data.get('off_voltage', ''))
            
            self._log_message("DEBUG: Updated legacy conditional fields")
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to handle legacy conditional fields: {str(e)}")

    def _store_conditional_update_info(self, conditional_updates: List[Dict[str, Any]]):
        """
        Store information about conditional field updates.
        
        Args:
            conditional_updates: List of conditional field update information
        """
        try:
            if not hasattr(self, 'conditional_update_log'):
                self.conditional_update_log = []
            
            update_entry = {
                'timestamp': datetime.now(),
                'updates': conditional_updates,
                'session_id': f"conditional_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            self.conditional_update_log.append(update_entry)
            
            # Keep only the last 5 conditional update sessions
            if len(self.conditional_update_log) > 5:
                self.conditional_update_log = self.conditional_update_log[-5:]
                
        except Exception as e:
            self._log_message(f"WARNING: Failed to store conditional update info: {str(e)}")

    def _get_command_type_for_parameter(self, param_name: str) -> str:
        """
        Get the command type for a parameter name.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            Command type string for parsing
        """
        command_type_mapping = {
            'apn_settings': 'get_apn',
            'server_settings': 'get_server',
            'report_intervals': 'get_timer',
            'heartbeat_intervals': 'get_hbt',
            'protocol': 'get_protocol',
            'tcp_ack': 'get_tcp_ack',
            'ignition_type': 'get_accline',
            'speed_alert': 'get_speed_alert',
            'speed_buzzer': 'get_speed_buzzer',
            'sleep_mode': 'get_sleep_mode',
            'sleep_time': 'get_sleep_time',
            'angle_report': 'get_angle_report',
            'backup_battery_alert': 'get_backup_battery_alert',
            'main_power_alert': 'get_main_power_alert',
            'vibration_sensitivity': 'get_vibration_sensitivity',
            'jammer_detection': 'get_jammer_detection',
            'jammer_relay_action': 'get_jammer_relay_action',
            'odometer': 'get_odometer',
            'hourmeter': 'get_hourmeter',
            # Legacy mappings
            'apn_config': 'get_apn',
            'server_config': 'get_server',
            'timer_settings': 'get_timer',
            'heartbeat_settings': 'get_hbt',
            'protocol_settings': 'get_gt06sel',
            'vibration_settings': 'get_vibl',
            'vibration_window': 'get_vibchk',
            'defense_settings': 'get_defense',
            'network_settings': 'get_netselect',
            'volte_settings': 'get_volteswitch',
            'sleep_mode_settings': 'get_slpdisconnect',
            'sleep_time_settings': 'get_sleept',
            'ignition_settings': 'get_accline'
        }
        
        return command_type_mapping.get(param_name, 'get_default')

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
                # Use longer timeout for TIMER command as it may take more time to respond
                timeout = 8.0 if command == 'TIMER' else 5.0
                response = self._send_command_and_wait(command, timeout=timeout)
                
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
                
                # Network Parameters
                elif command_type == 'get_apn':
                    parsed_values['apn'] = match.group(1)
                    parsed_values['user'] = match.group(2)
                    parsed_values['password'] = match.group(3).rstrip('#')
                    
                elif command_type == 'get_server':
                    parsed_values['server_type'] = match.group(1)
                    parsed_values['address'] = match.group(2)
                    parsed_values['port'] = match.group(3)
                    parsed_values['protocol'] = match.group(4)
                
                # Time Parameters
                elif command_type == 'get_timer':
                    # Handle multiple response formats
                    if match.group(1) and match.group(2):  # TIMER:x,y format
                        parsed_values['moving_time'] = match.group(1)
                        parsed_values['stopped_time'] = match.group(2)
                    elif match.group(3) and match.group(4):  # TIMER ACC ON:xs,ACC OFF:ys format
                        parsed_values['moving_time'] = match.group(3)
                        parsed_values['stopped_time'] = match.group(4)
                    elif match.group(5) and match.group(6):  # TIMER:xs,ACC OFF:ys format
                        parsed_values['moving_time'] = match.group(5)
                        parsed_values['stopped_time'] = match.group(6)
                    
                elif command_type == 'get_hbt':
                    # Handle multiple response formats
                    if match.group(1) and match.group(2):  # HBT:x,y format
                        parsed_values['moving_heartbeat'] = match.group(1)
                        parsed_values['stopped_heartbeat'] = match.group(2)
                    elif match.group(3) and match.group(4):  # HBT ACC ON:xs,ACC OFF:ys format
                        parsed_values['moving_heartbeat'] = match.group(3)
                        parsed_values['stopped_heartbeat'] = match.group(4)
                    elif match.group(5) and match.group(6):  # HBT:xs,ACC OFF:ys format
                        parsed_values['moving_heartbeat'] = match.group(5)
                        parsed_values['stopped_heartbeat'] = match.group(6)
                
                # Service Parameters
                elif command_type == 'get_protocol':
                    # Map numeric values back to protocol names
                    protocol_map = {'0': 'GT06 (0x60)', '1': 'CRX3 (0x22)', '2': 'CRX (0x12)'}
                    protocol_value = match.group(1)
                    parsed_values['protocol'] = protocol_map.get(protocol_value, protocol_value)
                    
                elif command_type == 'get_tcp_ack':
                    # Map numeric values back to enabled/disabled
                    ack_map = {'0': 'Disabled', '1': 'Enabled'}
                    ack_value = match.group(1)
                    parsed_values['tcp_ack'] = ack_map.get(ack_value, ack_value)
                
                # Ignition Parameters
                elif command_type == 'get_accline':
                    # Map ignition line type
                    accline_map = {'0': 'Virtual por acelerômetro (Virtual by accelerometer)', 
                                  '1': 'Física (Physical)'}
                    accline_value = match.group(1)
                    parsed_values['ignition_mode'] = accline_map.get(accline_value, accline_value)
                    
                elif command_type == 'get_acc_cfg':
                    cfg_type = match.group(1)
                    on_voltage = match.group(2)
                    off_voltage = match.group(3)
                    
                    if cfg_type == '1':  # Battery mode
                        parsed_values['ignition_mode'] = 'Virtual por bateria (Virtual by battery)'
                        parsed_values['on_voltage'] = on_voltage
                        parsed_values['off_voltage'] = off_voltage
                    else:
                        parsed_values['cfg_type'] = cfg_type
                        parsed_values['on_voltage'] = on_voltage
                        parsed_values['off_voltage'] = off_voltage
                
                # Speed Parameters
                elif command_type == 'get_speed_alert':
                    # Handle OFF case
                    if match.group(1) == 'OFF':
                        parsed_values['enabled'] = False
                        parsed_values['detection_time'] = '0'
                        parsed_values['speed_limit'] = '0'
                        parsed_values['alert_type'] = 'Apenas GPRS'
                    else:
                        # Handle numeric case - groups are shifted due to alternation
                        parsed_values['enabled'] = match.group(2) == '1'
                        parsed_values['detection_time'] = match.group(3)
                        parsed_values['speed_limit'] = match.group(4)
                        alert_type_map = {'0': 'Apenas GPRS', '1': 'GPRS+SMS'}
                        parsed_values['alert_type'] = alert_type_map.get(match.group(5), match.group(5))
                    
                elif command_type == 'get_speed_buzzer':
                    parsed_values['speed_buzzer'] = match.group(1) == '1'
                
                # Power Saving Parameters
                elif command_type == 'get_sleep_mode':
                    # Map numeric values back to sleep mode names
                    sleep_map = {'0': 'Desabilitado (Disabled)', 
                               '1': 'Sleep (Habilitado)', 
                               '2': 'Deep Sleep (Ultra-baixo)'}
                    sleep_value = match.group(1)
                    parsed_values['sleep_mode'] = sleep_map.get(sleep_value, sleep_value)
                    
                elif command_type == 'get_sleep_time':
                    parsed_values['sleep_time'] = match.group(1)
                
                # Angle Parameters
                elif command_type == 'get_angle_report':
                    parsed_values['min_speed'] = match.group(1)
                    parsed_values['angle_variation'] = match.group(2)
                    parsed_values['enabled'] = True  # If we get a response, it's enabled
                
                # Battery Alert Parameters
                elif command_type == 'get_backup_battery_alert':
                    # Handle ON/OFF or numeric format
                    status = match.group(1)
                    if status == 'ON':
                        parsed_values['enabled'] = True
                    elif status == 'OFF':
                        parsed_values['enabled'] = False
                    else:
                        parsed_values['enabled'] = status == '1'
                    parsed_values['mode'] = match.group(2)
                    
                elif command_type == 'get_main_power_alert':
                    # Handle ON/OFF or numeric format
                    status = match.group(1)
                    if status == 'ON':
                        parsed_values['enabled'] = True
                    elif status == 'OFF':
                        parsed_values['enabled'] = False
                    else:
                        parsed_values['enabled'] = status == '1'
                    alert_type_map = {'0': 'Apenas GPRS', '1': 'GPRS+SMS'}
                    parsed_values['alert_type'] = alert_type_map.get(match.group(2), match.group(2))
                    parsed_values['detection_time'] = match.group(3)
                    parsed_values['min_charge_time'] = match.group(4)
                
                # Vibration Sensor Parameters
                elif command_type == 'get_vibration_sensitivity':
                    level = match.group(1)
                    parsed_values['level'] = level
                    parsed_values['enabled'] = level != '0'  # Enabled if level > 0
                
                # Jammer Detection Parameters
                elif command_type == 'get_jammer_detection':
                    # Handle ON/OFF or numeric format
                    status = match.group(1)
                    if status == 'ON':
                        parsed_values['enabled'] = True
                    elif status == 'OFF':
                        parsed_values['enabled'] = False
                    else:
                        parsed_values['enabled'] = status == '1'
                    # Handle optional mode parameter
                    mode = match.group(2) if match.lastindex >= 2 else None
                    parsed_values['mode'] = mode
                    
                elif command_type == 'get_jammer_relay_action':
                    parsed_values['enabled'] = match.group(1) == '1'
                    operation_map = {'0': 'Sem Ação', 
                                   '1': 'Ativar e Manter', 
                                   '2': 'Ativar e Desativar com Jammer'}
                    parsed_values['output_operation'] = operation_map.get(match.group(2), match.group(2))
                    parsed_values['confirmation_time'] = match.group(3)
                    parsed_values['speed_limit'] = match.group(4)
                    # Additional parameters D, E, F, G
                    parsed_values['param_d'] = match.group(5)
                    parsed_values['param_e'] = match.group(6)
                    parsed_values['param_f'] = match.group(7)
                
                # Miscellaneous Parameters
                elif command_type == 'get_odometer':
                    # Handle both MILEAGE=value and "Cur Mileage Value:valueKM" formats
                    odometer_value = None
                    if match.group(1):  # MILEAGE=value format
                        odometer_value = match.group(1)
                        self._log_message(f"DEBUG: Parsed odometer from MILEAGE format: '{odometer_value}'")
                    elif match.group(2):  # Cur Mileage Value:valueKM format
                        odometer_value = match.group(2)
                        self._log_message(f"DEBUG: Parsed odometer from 'Cur Mileage Value' format: '{odometer_value}'")
                    
                    if odometer_value is not None:
                        # Validate that the odometer value is numeric
                        try:
                            # Ensure the value is a valid number
                            int(odometer_value)
                            parsed_values['odometer'] = odometer_value
                            self._log_message(f"DEBUG: Successfully parsed odometer value: {odometer_value}")
                        except ValueError:
                            self._log_message(f"WARNING: Invalid odometer value (not numeric): '{odometer_value}'")
                            parsed_values['odometer'] = '0'  # Default to 0 for invalid values
                    else:
                        self._log_message(f"WARNING: No odometer value found in response: '{response}'")
                        parsed_values['odometer'] = '0'  # Default to 0 when no value found
                    
                elif command_type == 'get_hourmeter':
                    # Handle both ACCONT:value and "Get ACC ON Time:value Minute" formats
                    hourmeter_value = None
                    if match.group(1):  # ACCONT:value format
                        hourmeter_value = match.group(1)
                        self._log_message(f"DEBUG: Parsed hourmeter from ACCONT format: '{hourmeter_value}'")
                    elif match.group(2):  # Get ACC ON Time:value Minute format
                        hourmeter_value = match.group(2)
                        self._log_message(f"DEBUG: Parsed hourmeter from 'Get ACC ON Time' format: '{hourmeter_value}'")
                    
                    if hourmeter_value is not None:
                        # Validate that the hourmeter value is numeric
                        try:
                            # Ensure the value is a valid number
                            int(hourmeter_value)
                            parsed_values['hourmeter'] = hourmeter_value
                            self._log_message(f"DEBUG: Successfully parsed hourmeter value: {hourmeter_value}")
                        except ValueError:
                            self._log_message(f"WARNING: Invalid hourmeter value (not numeric): '{hourmeter_value}'")
                            parsed_values['hourmeter'] = '0'  # Default to 0 for invalid values
                    else:
                        self._log_message(f"WARNING: No hourmeter value found in response: '{response}'")
                        parsed_values['hourmeter'] = '0'  # Default to 0 when no value found
                
                # Legacy parameter parsing for backward compatibility
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
        """Get all parameter commands to execute during configuration reading based on specification."""
        commands = []
        
        # Exclude device information commands - only include actual parameter reading commands
        # This matches the behavior of the working "load profile from device" feature
        excluded_params = {'device_info'}  # Exclude IMEI, ICCID, VERSION, STATUS commands
        
        self._log_message("DEBUG: Building parameter command list for configuration reading")
        
        # Dynamically build commands based on what's actually configured
        for param_name, param_info in self.parameter_query_commands.items():
            # Skip device information commands that are not actual configuration parameters
            if param_name in excluded_params:
                self._log_message(f"DEBUG: Excluding device info parameter: {param_name}")
                continue
                
            if isinstance(param_info, list):
                # Multiple commands for this parameter - use only the first command to avoid duplicates
                # This prevents parameters like 'ignition_type' from being counted multiple times
                if param_info:  # Make sure the list is not empty
                    command, command_type = param_info[0]  # Use only the first command
                    commands.append((param_name, command, command_type))
                    self._log_message(f"DEBUG: Added parameter command (first of {len(param_info)}): {param_name} -> {command}")
            elif isinstance(param_info, tuple):
                # Single command for this parameter
                command, command_type = param_info
                commands.append((param_name, command, command_type))
                self._log_message(f"DEBUG: Added parameter command: {param_name} -> {command}")
        
        self._log_message(f"INFO: Configuration reading will use {len(commands)} parameter commands (device info commands excluded)")
        return commands

    def _extract_parameter_value(self, param_name: str, parsed_values: Dict[str, Any]) -> str:
        """Extract the main value for a parameter from parsed values."""
        # Handle special cases based on parameter specification
        if param_name == 'device_info':
            return parsed_values.get('imei', '')
        
        # Network Parameters
        elif param_name == 'apn_settings':
            return parsed_values.get('apn', '')
        elif param_name == 'server_settings':
            return parsed_values.get('address', '')
        
        # Time Parameters
        elif param_name == 'report_intervals':
            return parsed_values.get('moving_time', '')
        elif param_name == 'heartbeat_intervals':
            return parsed_values.get('moving_heartbeat', '')
        
        # Service Parameters
        elif param_name == 'protocol':
            return parsed_values.get('protocol', '')
        elif param_name == 'tcp_ack':
            return parsed_values.get('tcp_ack', '')
        
        # Ignition Parameters
        elif param_name == 'ignition_type':
            return parsed_values.get('ignition_mode', '')
        
        # Speed Parameters
        elif param_name == 'speed_alert':
            return str(parsed_values.get('enabled', False))
        elif param_name == 'speed_buzzer':
            return str(parsed_values.get('speed_buzzer', False))
        
        # Power Saving Parameters
        elif param_name == 'sleep_mode':
            return parsed_values.get('sleep_mode', '')
        elif param_name == 'sleep_time':
            return parsed_values.get('sleep_time', '')
        
        # Angle Parameters
        elif param_name == 'angle_report':
            return str(parsed_values.get('enabled', False))
        
        # Battery Alert Parameters
        elif param_name == 'backup_battery_alert':
            return str(parsed_values.get('enabled', False))
        elif param_name == 'main_power_alert':
            return str(parsed_values.get('enabled', False))
        
        # Vibration Sensor Parameters
        elif param_name == 'vibration_sensitivity':
            return parsed_values.get('level', '')
        
        # Jammer Detection Parameters
        elif param_name == 'jammer_detection':
            return str(parsed_values.get('enabled', False))
        elif param_name == 'jammer_relay_action':
            return str(parsed_values.get('enabled', False))
        
        # Miscellaneous Parameters
        elif param_name == 'odometer':
            return parsed_values.get('odometer', '')
        elif param_name == 'hourmeter':
            return parsed_values.get('hourmeter', '')
        
        # Legacy parameters for backward compatibility
        elif param_name == 'vibration_settings':
            return parsed_values.get('vibration', '')
        elif param_name == 'vibration_window':
            return parsed_values.get('vibration_window', '')
        elif param_name == 'defense_settings':
            return parsed_values.get('defense_time', '')
        elif param_name == 'network_settings':
            return parsed_values.get('network_select', '')
        elif param_name == 'volte_settings':
            return parsed_values.get('volte_switch', '')
        elif param_name == 'all_parameters':
            return parsed_values.get('imei', '')
        
        # Legacy mappings
        elif param_name == 'apn_config':
            return parsed_values.get('apn_server', '')
        elif param_name == 'server_config':
            return parsed_values.get('server_address', '')
        elif param_name == 'timer_settings':
            return parsed_values.get('timer_ign_on', '')
        elif param_name == 'heartbeat_settings':
            return parsed_values.get('heartbeat_ign_on', '')
        elif param_name == 'protocol_settings':
            return parsed_values.get('gt06_protocol', '')
        elif param_name == 'sleep_mode_settings':
            return parsed_values.get('sleep_mode', '')
        elif param_name == 'sleep_time_settings':
            return parsed_values.get('sleep_time', '')
        elif param_name == 'ignition_settings':
            return parsed_values.get('ignition_type', '')
        
        else:
            # For other parameters, return the first value
            return next(iter(parsed_values.values()), '') if parsed_values else ''

    def _send_command_and_wait(self, command: str, timeout: float = 5.0) -> Optional[str]:
        """
        Send a command and wait for a response.
        
        Args:
            command: The raw command to send (will be formatted with ATSMS prefix)
            timeout: Timeout in seconds
            
        Returns:
            The device response or None if timeout
        """
        # Check if we have access to the serial service
        if not hasattr(self.app, 'serial_service'):
            self._log_message("ERROR: Cannot send command - serial_service not found")
            return None
        
        try:
            # Format the command with ATSMS prefix for proper LT32Pro USB communication
            if self.command_formatter.is_read_command_supported(command):
                formatted_command = self.command_formatter.format_read_command(command)
                self._log_message(f"DEBUG: Formatted command '{command}' as '{formatted_command}'")
            else:
                # Fallback for unsupported commands - add ATSMS prefix manually
                formatted_command = f"ATSMS:{command}#"
                self._log_message(f"DEBUG: Using fallback formatting for '{command}' as '{formatted_command}'")
            
            # Validate command syntax
            self.command_formatter.validate_command_syntax(formatted_command)
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to format command '{command}': {str(e)}")
            return None
        
        # Set up response capture
        self.waiting_for_response = True
        self.captured_response = None
        self.response_timeout = False
        
        # Send the formatted command
        success = self.app.serial_service.send_command(formatted_command, command)
        if not success:
            self._log_message(f"ERROR: Failed to send formatted command: {formatted_command}")
            self.waiting_for_response = False
            return None
        
        self._log_message(f"DEBUG: Successfully sent formatted command: {formatted_command}")
        
        # Wait for a response
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.captured_response is not None:
                response = self.captured_response
                self.waiting_for_response = False
                self.captured_response = None
                self._log_message(f"DEBUG: Received response for '{command}': {response}")
                return response
            
            # Sleep for a short time
            time.sleep(0.1)
        
        # Timeout
        self.waiting_for_response = False
        self.response_timeout = True
        self._log_message(f"WARNING: Timeout waiting for response to '{command}' (formatted as '{formatted_command}')")
        return None
    
    def capture_device_response(self, response: str) -> None:
        """
        Capture a device response for the configuration reader.
        
        Args:
            response: The device response string
        """
        # Always log the response for debugging
        self._log_message(f"DEBUG: Received device response: '{response}'")
        
        # Capture response if we're waiting for one and haven't captured one yet
        if self.waiting_for_response and self.captured_response is None:
            self.captured_response = response.strip()
            self._log_message(f"DEBUG: Captured response for processing: '{self.captured_response}'")
        elif self.waiting_for_response:
            # Log if we're already have a captured response (might indicate timing issues)
            self._log_message(f"DEBUG: Already have captured response '{self.captured_response}', ignoring new response: '{response}'")
        else:
            # Log responses we're not expecting (helps with debugging)
            self._log_message(f"DEBUG: Ignoring unsolicited response: '{response}'")

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

    def read_specific_parameter_with_error_handling(self, param_name: str, command: str, 
                                                  command_type: str, max_retries: int = 2) -> ParameterReadResult:
        """
        Read a specific parameter with comprehensive error handling.
        
        Args:
            param_name: Name of the parameter to read
            command: Command to send to device
            command_type: Type of command for response parsing
            max_retries: Maximum number of retry attempts
            
        Returns:
            ParameterReadResult with enhanced error information
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                # Validate connection before each attempt
                if self.parameter_error_handler and retry_count > 0:
                    validation_result = self.parameter_error_handler.validate_connection_before_operation(f"reading {param_name}")
                    if not validation_result.is_valid:
                        return ParameterReadResult(
                            parameter_name=param_name,
                            success=False,
                            value=None,
                            error_message=f"Connection validation failed: {validation_result.error_message}",
                            raw_response=""
                        )
                
                # Format and send command with timeout handling
                start_time = time.time()
                
                try:
                    # Format the command with ATSMS prefix for proper LT32Pro USB communication
                    if self.command_formatter.is_read_command_supported(command):
                        formatted_command = self.command_formatter.format_read_command(command)
                        self._log_message(f"DEBUG: Formatted command '{command}' as '{formatted_command}' for {param_name}")
                    else:
                        # Fallback for unsupported commands - add ATSMS prefix manually
                        formatted_command = f"ATSMS:{command}#"
                        self._log_message(f"DEBUG: Using fallback formatting for '{command}' as '{formatted_command}' for {param_name}")
                    
                    # Validate command syntax
                    self.command_formatter.validate_command_syntax(formatted_command)
                    
                    # Send the formatted command
                    success = self.app.serial_service.send_command(formatted_command, command_type)
                    if not success:
                        raise RuntimeError(f"Failed to send formatted command: {formatted_command}")
                    
                    self._log_message(f"DEBUG: Successfully sent formatted command for {param_name}: {formatted_command}")
                    
                except Exception as e:
                    return ParameterReadResult(
                        parameter_name=param_name,
                        success=False,
                        value=None,
                        error_message=f"Command formatting error: {str(e)}",
                        raw_response=""
                    )
                
                # Wait for response with timeout
                response = self._wait_for_response_with_timeout(param_name, command, timeout=10.0)
                read_duration = time.time() - start_time
                
                if response is None:
                    # Handle timeout
                    if self.parameter_error_handler:
                        error = self.parameter_error_handler.handle_communication_timeout(
                            param_name, command, read_duration
                        )
                        last_error = error
                        
                        # Check if we should retry
                        if retry_count < max_retries and read_duration < 15.0:  # Only retry for shorter timeouts
                            retry_count += 1
                            self._log_message(f"INFO: Retrying {param_name} (attempt {retry_count + 1}/{max_retries + 1})")
                            time.sleep(1.0)  # Brief delay before retry
                            continue
                    
                    return ParameterReadResult(
                        parameter_name=param_name,
                        success=False,
                        value=None,
                        error_message=f"Communication timeout after {read_duration:.1f}s",
                        raw_response=""
                    )
                
                # Parse response
                parsed_response = self.parse_device_response(param_name, response, command_type)
                
                if parsed_response.success:
                    # Successful read
                    return ParameterReadResult(
                        parameter_name=param_name,
                        success=True,
                        value=str(parsed_response.parsed_values),
                        error_message=None,
                        raw_response=response
                    )
                else:
                    # Handle parsing error
                    if self.parameter_error_handler:
                        error = self.parameter_error_handler.handle_invalid_response(
                            param_name, command, response, 
                            expected_format=self._get_expected_format(command_type),
                            parsing_error=parsed_response.error_message or "Unknown parsing error"
                        )
                        last_error = error
                        
                        # Check if we should retry for parsing errors
                        if retry_count < max_retries and "format" not in parsed_response.error_message.lower():
                            retry_count += 1
                            self._log_message(f"INFO: Retrying {param_name} due to parsing error (attempt {retry_count + 1}/{max_retries + 1})")
                            time.sleep(0.5)  # Brief delay before retry
                            continue
                    
                    return ParameterReadResult(
                        parameter_name=param_name,
                        success=False,
                        value=None,
                        error_message=f"Invalid response: {parsed_response.error_message}",
                        raw_response=response
                    )
                    
            except Exception as e:
                # Handle unexpected errors
                if self.parameter_error_handler:
                    error_details = {
                        'exception': str(e),
                        'command_sent': command,
                        'retry_count': retry_count
                    }
                    error = self.parameter_error_handler.handle_parameter_operation_error(
                        'read', param_name, error_details
                    )
                    last_error = error
                
                if retry_count < max_retries:
                    retry_count += 1
                    self._log_message(f"WARNING: Exception reading {param_name}, retrying (attempt {retry_count + 1}/{max_retries + 1}): {str(e)}")
                    time.sleep(1.0)
                    continue
                else:
                    return ParameterReadResult(
                        parameter_name=param_name,
                        success=False,
                        value=None,
                        error_message=f"Unexpected error: {str(e)}",
                        raw_response=""
                    )
        
        # All retries exhausted
        error_msg = f"Failed after {max_retries + 1} attempts"
        if last_error:
            error_msg += f": {last_error.error_message}"
        
        return ParameterReadResult(
            parameter_name=param_name,
            success=False,
            value=None,
            error_message=error_msg,
            raw_response=""
        )
    
    def _wait_for_response_with_timeout(self, param_name: str, command: str, timeout: float = 10.0) -> Optional[str]:
        """
        Wait for device response with timeout and enhanced error handling.
        
        Args:
            param_name: Name of parameter being read
            command: Command that was sent
            timeout: Timeout in seconds
            
        Returns:
            Response string or None if timeout
        """
        start_time = time.time()
        self.waiting_for_response = True
        self.captured_response = None
        self.response_timeout = False
        
        # Wait for response with periodic connection checks
        while time.time() - start_time < timeout:
            if self.captured_response is not None:
                response = self.captured_response
                self.waiting_for_response = False
                self.captured_response = None
                return response
            
            # Check if connection is still valid every 2 seconds
            if time.time() - start_time > 2.0 and (time.time() - start_time) % 2.0 < 0.1:
                if not hasattr(self.app, 'serial_service') or not self.app.serial_service.is_connected:
                    self._log_message(f"WARNING: Connection lost while waiting for {param_name} response")
                    break
            
            time.sleep(0.1)
        
        # Timeout occurred
        self.waiting_for_response = False
        self.response_timeout = True
        return None
    
    def _get_expected_format(self, command_type: str) -> str:
        """
        Get the expected response format for a command type.
        
        Args:
            command_type: Type of command
            
        Returns:
            Expected format string
        """
        format_map = {
            'get_apn': 'APN:server,user,password',
            'get_server': 'SERVER:type,address,port,protocol',
            'get_timer': 'TIMER:moving_time,stopped_time',
            'get_hbt': 'HBT:moving_heartbeat,stopped_heartbeat',
            'get_protocol': 'GT06SEL=value',
            'get_tcp_ack': 'POSBYACK=value',
            'get_accline': 'ACCLINE=value',
            'get_acc_cfg': 'ACC_CFG=type-on_voltage-off_voltage'
        }
        return format_map.get(command_type, 'Unknown format')

    def _log_message(self, message: str) -> None:
        """Log a message to the application log."""
        if hasattr(self.app, 'log_frame'):
            self.app.log_frame.log_message(message + "\n")
        else:
            print(message)

    def read_parameter_section(self, section_name: str, progress_callback: Optional[Callable] = None,
                             completion_callback: Optional[Callable] = None) -> None:
        """
        Read all parameters from a specific section.
        
        Args:
            section_name: Name of the parameter section to read
            progress_callback: Optional callback for progress updates
            completion_callback: Optional callback when reading is complete
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

        # Get section parameters
        section_commands = self._get_section_parameter_commands(section_name)
        if not section_commands:
            error_msg = f"Unknown parameter section: {section_name}"
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

        # Start reading in a separate thread
        self.read_thread = threading.Thread(
            target=self._read_section_thread, 
            args=(section_name, section_commands), 
            daemon=True
        )
        self.read_thread.start()

    def _read_section_thread(self, section_name: str, section_commands: List[tuple]) -> None:
        """Thread function for reading a parameter section."""
        start_time = time.time()
        parameters_read = []
        failed_parameters = []
        
        try:
            self._log_message(f"INFO: Starting {section_name} section read with {len(section_commands)} commands")
            
            for i, (param_name, command, command_type) in enumerate(section_commands):
                if self.cancel_requested:
                    self._log_message(f"INFO: {section_name} section reading canceled by user")
                    break
                
                # Update progress
                status_text = f"Reading {param_name}..."
                if self.progress_callback:
                    self.app.after(0, self.progress_callback, i + 1, len(section_commands), status_text)
                
                # Read the parameter
                result = self.read_specific_parameter(param_name, command, command_type)
                parameters_read.append(result)
                
                if not result.success:
                    failed_parameters.append(param_name)
                    self._log_message(f"WARNING: Failed to read {param_name}: {result.error_message}")
                else:
                    self._log_message(f"INFO: Successfully read {param_name}: {result.value}")
                
                # Add delay between commands
                if i < len(section_commands) - 1:
                    time.sleep(0.5)
            
            # Calculate results
            read_duration = time.time() - start_time
            successful_reads = len(section_commands) - len(failed_parameters)
            success = successful_reads > 0
            
            result = ConfigurationReadResult(
                success=success,
                parameters_read=parameters_read,
                total_parameters=len(section_commands),
                failed_parameters=failed_parameters,
                read_duration=read_duration,
                timestamp=datetime.now()
            )
            
            # Update UI with read parameters
            if success:
                self._update_ui_with_parameters(parameters_read)
            
            # Call completion callback
            if self.completion_callback:
                error_msg = None
                if failed_parameters:
                    error_msg = f"Failed to read {len(failed_parameters)} parameters from {section_name}"
                self.completion_callback(result, error_msg)
            
            self._log_message(f"INFO: {section_name} section reading completed in {read_duration:.2f} seconds")
            
        except Exception as e:
            error_msg = f"Unexpected error during {section_name} section reading: {str(e)}"
            self._log_message(f"ERROR: {error_msg}")
            
            result = ConfigurationReadResult(
                success=False,
                parameters_read=parameters_read,
                total_parameters=len(section_commands),
                failed_parameters=failed_parameters,
                read_duration=time.time() - start_time,
                timestamp=datetime.now()
            )
            
            if self.completion_callback:
                self.completion_callback(result, error_msg)
        
        finally:
            self.is_reading = False

    def _get_section_parameter_commands(self, section_name: str) -> List[tuple]:
        """
        Get parameter commands for a specific section.
        
        Args:
            section_name: Name of the parameter section
            
        Returns:
            List of (param_name, command, command_type) tuples
        """
        section_mappings = {
            'network_parameters': [
                ('apn_settings', *self.parameter_query_commands['apn_settings']),
                ('server_settings', *self.parameter_query_commands['server_settings'])
            ],
            'time_parameters': [
                ('report_intervals', *self.parameter_query_commands['report_intervals']),
                ('heartbeat_intervals', *self.parameter_query_commands['heartbeat_intervals'])
            ],
            'service_parameters': [
                ('protocol', *self.parameter_query_commands['protocol']),
                ('tcp_ack', *self.parameter_query_commands['tcp_ack'])
            ],
            'ignition': [
                ('ignition_type', command, command_type) 
                for command, command_type in self.parameter_query_commands['ignition_type']
            ],
            'speed': [
                ('speed_alert', *self.parameter_query_commands['speed_alert']),
                ('speed_buzzer', *self.parameter_query_commands['speed_buzzer'])
            ],
            'power_saving': [
                ('sleep_mode', *self.parameter_query_commands['sleep_mode']),
                ('sleep_time', *self.parameter_query_commands['sleep_time'])
            ],
            'angle': [
                ('angle_report', *self.parameter_query_commands['angle_report'])
            ],
            'battery_alerts': [
                ('backup_battery_alert', *self.parameter_query_commands['backup_battery_alert']),
                ('main_power_alert', *self.parameter_query_commands['main_power_alert'])
            ],
            'vibration_sensor': [
                ('vibration_sensitivity', *self.parameter_query_commands['vibration_sensitivity'])
            ],
            'jammer_detection': [
                ('jammer_detection', *self.parameter_query_commands['jammer_detection']),
                ('jammer_relay_action', *self.parameter_query_commands['jammer_relay_action'])
            ],
            'miscellaneous': [
                ('odometer', *self.parameter_query_commands['odometer']),
                ('hourmeter', *self.parameter_query_commands['hourmeter'])
            ]
        }
        
        return section_mappings.get(section_name, [])

    def get_reading_progress(self) -> Dict[str, Any]:
        """
        Get current reading progress information.
        
        Returns:
            Dictionary with progress information
        """
        return {
            'is_reading': self.is_reading,
            'cancel_requested': self.cancel_requested,
            'successful_reads': getattr(self, 'successful_reads', 0),
            'failed_reads': getattr(self, 'failed_reads', 0),
            'total_read_attempts': getattr(self, 'total_read_attempts', 0),
            'last_read_attempt': getattr(self, 'last_read_attempt', None)
        }

    def get_specific_error_message(self, param_name: str, error_type: str) -> str:
        """
        Get a specific error message for a parameter and error type.
        
        Args:
            param_name: Name of the parameter
            error_type: Type of error (timeout, parse_error, connection_error, etc.)
            
        Returns:
            Localized error message
        """
        error_messages = {
            'timeout': self.i18n.get('param_read_timeout', 
                                   'Timeout reading {param}: Device did not respond within expected time'),
            'parse_error': self.i18n.get('param_parse_error', 
                                       'Parse error reading {param}: Device response format was unexpected'),
            'connection_error': self.i18n.get('param_connection_error', 
                                            'Connection error reading {param}: Device connection was lost'),
            'invalid_response': self.i18n.get('param_invalid_response', 
                                            'Invalid response reading {param}: Device returned an error or unexpected data'),
            'command_error': self.i18n.get('param_command_error', 
                                         'Command error reading {param}: Failed to send command to device')
        }
        
        message_template = error_messages.get(error_type, 
                                            self.i18n.get('param_unknown_error', 
                                                        'Unknown error reading {param}'))
        
        return message_template.format(param=param_name)

    def cancel_reading(self) -> None:
        """Cancel the current configuration reading operation with enhanced feedback."""
        if self.is_reading:
            self.cancel_requested = True
            self._log_message("INFO: Configuration reading cancellation requested by user")
            
            # Update progress dialog to show cancellation in progress
            if self.progress_dialog_id and hasattr(self.app, 'operation_confirmation_service'):
                try:
                    cancel_status = (f"Cancelling operation...\n"
                                   f"Current parameter: {getattr(self, 'current_parameter_name', 'Unknown')}\n"
                                   f"Completed: {getattr(self, 'successful_reads_count', 0)} successful, {getattr(self, 'failed_reads_count', 0)} failed")
                    
                    self.app.after(0, self.app.operation_confirmation_service.update_progress,
                                  self.progress_dialog_id, getattr(self, 'current_parameter_index', 0), cancel_status)
                except Exception as e:
                    self._log_message(f"WARNING: Failed to update progress dialog during cancellation: {str(e)}")
            
            # Wait for the thread to finish gracefully
            if hasattr(self, 'read_thread') and self.read_thread and self.read_thread.is_alive():
                self.read_thread.join(timeout=3.0)  # Wait up to 3 seconds for graceful shutdown
            
            self.is_reading = False
            successful_count = getattr(self, 'successful_reads_count', 0)
            self._log_message(f"INFO: Configuration reading cancelled - {successful_count} parameters read successfully before cancellation")
        else:
            self._log_message("INFO: No active configuration reading operation to cancel")

    def get_parameter_update_log(self) -> List[Dict[str, Any]]:
        """
        Get the parameter update log.
        
        Returns:
            List of parameter update entries
        """
        return getattr(self, 'parameter_update_log', [])

    def get_update_sessions(self) -> List[Dict[str, Any]]:
        """
        Get the update session information.
        
        Returns:
            List of update session entries
        """
        return getattr(self, 'update_sessions', [])

    def get_conditional_update_log(self) -> List[Dict[str, Any]]:
        """
        Get the conditional field update log.
        
        Returns:
            List of conditional update entries
        """
        return getattr(self, 'conditional_update_log', [])

    def export_parameter_update_log(self, file_path: str = None) -> str:
        """
        Export parameter update log to a file or return as string.
        
        Args:
            file_path: Optional file path to save the log
            
        Returns:
            Log content as string
        """
        try:
            log_entries = self.get_parameter_update_log()
            update_sessions = self.get_update_sessions()
            conditional_updates = self.get_conditional_update_log()
            
            # Build log content
            log_lines = []
            log_lines.append("# Parameter Update Log Export")
            log_lines.append(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            log_lines.append("")
            
            # Add session summary
            if update_sessions:
                log_lines.append("## Update Sessions Summary")
                for session in update_sessions:
                    log_lines.append(f"Session: {session['session_id']}")
                    log_lines.append(f"  Timestamp: {session['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                    log_lines.append(f"  Total Parameters: {session['total_parameters']}")
                    log_lines.append(f"  Changed: {len(session['changed_parameters'])}")
                    log_lines.append(f"  Unchanged: {len(session['unchanged_parameters'])}")
                    log_lines.append("")
            
            # Add detailed parameter updates
            if log_entries:
                log_lines.append("## Detailed Parameter Updates")
                for entry in log_entries:
                    timestamp_str = entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    status = "CHANGED" if entry['changed'] else "UNCHANGED"
                    old_str = self._format_value_for_logging(entry['old_value'])
                    new_str = self._format_value_for_logging(entry['new_value'])
                    
                    log_lines.append(f"[{timestamp_str}] {entry['parameter']}: {status}")
                    log_lines.append(f"  Old: {old_str}")
                    log_lines.append(f"  New: {new_str}")
                    log_lines.append("")
            
            # Add conditional field updates
            if conditional_updates:
                log_lines.append("## Conditional Field Updates")
                for session in conditional_updates:
                    log_lines.append(f"Session: {session['session_id']}")
                    log_lines.append(f"  Timestamp: {session['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                    for update in session['updates']:
                        visibility = "SHOWN" if update['visible'] else "HIDDEN"
                        log_lines.append(f"  {update['field']}: {visibility} (trigger: {update['trigger']}={update['trigger_value']})")
                    log_lines.append("")
            
            log_content = "\n".join(log_lines)
            
            # Save to file if path provided
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self._log_message(f"INFO: Parameter update log exported to {file_path}")
            
            return log_content
            
        except Exception as e:
            error_msg = f"ERROR: Failed to export parameter update log: {str(e)}"
            self._log_message(error_msg)
            return error_msg

    def clear_parameter_update_logs(self):
        """Clear all parameter update logs."""
        try:
            self.parameter_update_log = []
            self.update_sessions = []
            self.conditional_update_log = []
            self._log_message("INFO: Parameter update logs cleared")
        except Exception as e:
            self._log_message(f"ERROR: Failed to clear parameter update logs: {str(e)}")

    def get_update_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about parameter updates.
        
        Returns:
            Dictionary with update statistics
        """
        try:
            log_entries = self.get_parameter_update_log()
            update_sessions = self.get_update_sessions()
            
            if not log_entries:
                return {
                    'total_updates': 0,
                    'changed_updates': 0,
                    'unchanged_updates': 0,
                    'unique_parameters': 0,
                    'sessions': 0,
                    'last_update': None
                }
            
            changed_count = sum(1 for entry in log_entries if entry['changed'])
            unchanged_count = len(log_entries) - changed_count
            unique_parameters = len(set(entry['parameter'] for entry in log_entries))
            last_update = max(entry['timestamp'] for entry in log_entries) if log_entries else None
            
            return {
                'total_updates': len(log_entries),
                'changed_updates': changed_count,
                'unchanged_updates': unchanged_count,
                'unique_parameters': unique_parameters,
                'sessions': len(update_sessions),
                'last_update': last_update,
                'change_rate': (changed_count / len(log_entries) * 100) if log_entries else 0
            }
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to get update statistics: {str(e)}")
            return {'error': str(e)}
