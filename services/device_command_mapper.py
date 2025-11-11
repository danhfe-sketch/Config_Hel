"""
Device Command Mapper - Maps UI parameters to LT32Pro AT commands.

This module provides a centralized mapping between UI parameters and the actual
AT commands required by the LT32Pro device. It handles command formatting,
validation, and error handling for malformed commands.

Updated to use the Parameter Specification as the source of truth for all
command mappings, formats, and validation rules.

Enhanced with CommandValidationGateway integration for comprehensive pre-command validation.
"""

from typing import Dict, Any, Optional, Tuple, List
import re
import logging
from datetime import datetime
from .parameter_specification import (
    get_parameter_specification, 
    get_parameter_by_name,
    get_command_value_mapping,
    get_all_sections_ordered,
    COMMAND_VALUE_MAPPINGS,
    ParameterConfig,
    FieldConfig
)
from .command_validation_gateway import CommandValidationGateway, ValidationContext
from .validation_service import ValidationService


class DeviceCommandMapper:
    """Maps UI parameters to LT32Pro AT commands with validation."""

    def __init__(self, validation_service=None, i18n_service=None):
        """Initialize the command mapper with LT32Pro command definitions."""
        # Command prefix required for all LT32Pro commands via serial port
        self.command_prefix = "ATSMS:"

        # Initialize validation gateway for pre-command validation
        if validation_service is None:
            # Create a basic validation service if none provided
            from .i18n_service import I18nService
            i18n = i18n_service or I18nService()
            validation_service = ValidationService(i18n)
        
        self.validation_gateway = CommandValidationGateway(validation_service, i18n_service)
        self.logger = logging.getLogger(__name__)

        # Define command templates for all parameters
        self._init_command_templates()

        # Define parameter value mappings (e.g., TCP -> 0)
        self._init_value_mappings()
        
    def _log_message(self, message):
        """Log a message to the console."""
        print(message)

    def _init_command_templates(self) -> None:
        """Initialize command templates for all parameters based on LT32Pro documentation."""
        self.command_templates = {
            # Parameter UI List compliant command templates
            # Network Parameters
            'apn_settings': "APN,{apn_settings_apn},{apn_settings_user},{apn_settings_password}#",
            'server_settings': "SERVER,{server_settings_type},{server_settings_address},{server_settings_port},0#",
            
            # Time Parameters  
            'report_intervals': "TIMER,{report_intervals_moving_time},{report_intervals_stopped_time}#",
            'heartbeat_intervals': "HBT,{heartbeat_intervals_moving_heartbeat},{heartbeat_intervals_stopped_heartbeat}#",
            
            # Service Parameters
            'protocol': "SZCS#GT06SEL={protocol}#",
            'tcp_ack': "SZCS#POSBYACK={tcp_ack}#",
            
            # Ignition
            'ignition_type': "SZCS#ACCLINE={ignition_type_accline}#ACC_CFG={ignition_type_acc_cfg}",
            
            # Speed
            'speed_alert': "SPEED,{speed_alert_enabled},{speed_alert_detection_time},{speed_alert_speed_limit},{speed_alert_alert_type}#",
            'speed_buzzer': "SZCS#SPD_LED_SHOW={speed_buzzer}#",
            
            # Power Saving
            'sleep_mode': "SZCS#SLPDISCONNECT={sleep_mode}#",
            'sleep_time': "SZCS#SLEEPT={sleep_time}#",
            
            # Angle
            'angle_report': "SZCS#ANGLEVALUE={angle_report_min_speed}-{angle_report_angle_variation}",
            
            # Battery Alerts
            'backup_battery_alert': "BATALM,{backup_battery_alert_state},{backup_battery_alert_mode}#",
            'main_power_alert': "POWERALM,{main_power_alert_enabled},{main_power_alert_alert_type},{main_power_alert_detection_time},{main_power_alert_min_charge_time}#",
            
            # Vibration Sensor
            'vibration_sensitivity': "SZCS#VIBL={vibration_sensitivity_level}",
            
            # Jammer Detection
            'jammer_detection': "JAMMER,{jammer_detection_state},{jammer_detection_mode}#",
            'jammer_relay_action': "JAMRELAY,{jammer_relay_action_op},{jammer_relay_action_time},{jammer_relay_action_speed},{jammer_relay_action_d},{jammer_relay_action_e},{jammer_relay_action_f},{jammer_relay_action_g}#",
            'motion_sensor_alert': "SENALM,{state},{mode}#",
            
            # Miscellaneous
            'odometer': "MILEAGE={odometer}#",
            'hourmeter': "ACCONT,{hourmeter}#",
            
            # Legacy APN Configuration (kept for backward compatibility)
            'apn_server': "APN,{value},,#",
            'apn_user': "APN,{server},{value},#",
            'apn_password': "APN,{server},{user},{value}#",
            'apn_full': "APN,{server},{user},{password}#",
            
            # Parameter Query Commands - Complete specification-based read commands
            'query_apn': "APN#",
            'query_server': "SERVER#",
            'query_timer': "TIMER#",
            'query_heartbeat': "HBT#",
            'query_speed': "SPEED#",
            'query_vibration': "CXCS#VIBL",
            'query_defense': "DEFENSE#",
            'query_protocol': "CXCS#GT06SEL",
            'query_tcp_ack': "CXCS#POSBYACK",
            'query_network': "CXCS#NETSELECT",
            'query_sleep_mode': "CXCS#SLPDISCONNECT",
            'query_sleep_time': "CXCS#SLEEPT",
            'query_ignition': "CXCS#ACCLINE#ACC_CFG",
            'query_vibration_window': "CXCS#VIBCHK",
            'query_blind_speed': "CXCS#BLINDSPD",
            'query_angle_reporting': "CXCS#ANGLEVALUE",
            'query_relay_gps': "CXCS#SOURCE_OFF_TYPE",
            'query_curve_sensor': "CXCS#CURVE",
            'query_lock_type': "CXCS#LOCKTYPE",
            'query_sensitivity': "CXCS#SENSITIVITY",
            'query_backup_battery': "BATALM#",
            'query_main_power': "POWERALM#",
            'query_jammer': "JAMMER#",
            'query_jammer_relay': "JAMRELAY#",
            'query_motion_sensor_alert': "SENALM#",
            'query_odometer': "MILEAGE#",
            'query_hourmeter': "ACCONT#",

            # Server Configuration
            'server_ip': "SERVER,0,{value},{port},0#",
            'server_domain': "SERVER,1,{value},{port},0#",
            'server_port': "SERVER,0,{ip},{value},0#",
            'backup_server_ip': "SZCS#SERV2_ADDR={value}#",  # Changed from CXCS to SZCS for writing to device
            'backup_server_port': "SZCS#SERV2_PORT={value}#",  # Changed from CXCS to SZCS for writing to device

            # Communication Intervals
            'timer_ign_on': "TIMER,{value},{timer_ign_off}#",
            'timer_ign_off': "TIMER,{timer_ign_on},{value}#",
            'heartbeat_ign_on': "HBT,{value},{heartbeat_ign_off}#",
            'heartbeat_ign_off': "HBT,{heartbeat_ign_on},{value}#",
            'heartbeat_interval': "HBT,{value}#",

            # Device Information Retrieval
            'get_imei': "CXCS#IMEI",
            'get_teriid': "CXCS#TERIID",
            'get_iccid': "CXCS#ICCID",
            'get_imsi': "CXCS#IMSI",
            'get_status': "STATUS#",
            'get_version': "VERSION#",
            'get_all_params': "PARAM#",

            # Movement and Vibration Settings
            'vibration': "SZCS#VIBL={value}",  # Changed from CXCS to SZCS for writing to device
            'vibration_window': "SZCS#VIBCHK={window}:{value}#",  # Changed from CXCS to SZCS for writing to device
            'defense_time': "DEFENSE,{value}#",

            # Speed and Angle Reporting (legacy - replaced with Parameter UI List compliant version above)
            'angle_reporting': "SZCS#ANGLEVALUE={speed}-{value}",  # Changed from CXCS to SZCS for writing to device
            'blind_speed': "SZCS#BLINDSPD={value}#",  # Changed from CXCS to SZCS for writing to device

            # Ignition Configuration (ignition_type template is defined above at line 76)
            'ignition_config': "SZCS#ACC_CFG={value}#",  # Changed from CXCS to SZCS for writing to device

            # Alerts Configuration
            'movement_alert': "SENALM,ON,{value}#",
            'power_alert': "POWERALM,ON,{value},{t1},{t2}#",
            'battery_alert': "BATALM,ON,{value}#",
            'moving_alert': "MOVING,{enabled},{radius},{alert_type}#",
            'acc_off_alert': "ACCOFFALM,ON,{value}#",

            # Network and Protocol Settings
            'gt06_protocol': "SZCS#GT06SEL={value}#",  # Changed from CXCS to SZCS based on device feedback
            'network_select': "SZCS#NETSELECT={value}#",  # Changed from CXCS to SZCS for writing to device
            # Removed 'transmission_mode' as it doesn't exist in the device

            # Sleep Mode Configuration
            'sleep_mode': "SZCS#SLPDISCONNECT={value}#",  # Changed from CXCS to SZCS for writing to device
            'sleep_time': "SZCS#SLEEPT={value}#",  # Changed from CXCS to SZCS for writing to device

            # Relay/Output Control
            'relay_control': "RELAY,{value}#",
            'relay_gps_check': "SZCS#SOURCE_OFF_TYPE={value}#",  # Changed from CXCS to SZCS for writing to device

            # Phone Numbers Configuration
            'center_number1': "CENTER,A,{value}#",
            'center_number2': "CENTER,A2,{value}#",
            'center_number3': "CENTER,A3,{value}#",
            'sos_numbers': "SOS,A,{phone1},{phone2},{phone3}#",

            # System Commands
            'reset_device': "RESET#",
            'factory_reset': "FACTORY#",
            'format_device': "FORMAT#",
            'clear_memory': "BLINDINIT#",

            # Advanced Features (legacy - replaced by Parameter UI List compliant version above)
            'jammer_config': "JAMCFG,{time},{signal},{value}#",
            'parameter_lock': "PRLOCK,{password},{value}#",

            # Curve Sensor - Corrected from CURVE to proper command
            'curve_sensor': "SZCS#CURVE={value}#",  # Changed from CXCS to SZCS for writing to device

            # Lock Type - This is a placeholder as the actual command isn't in the documentation
            'lock_type': "SZCS#LOCKTYPE={value}#",  # Changed from CXCS to SZCS for writing to device

            # Sensitivity - This is a placeholder as the actual command isn't in the documentation
            'sensitivity': "SZCS#SENSITIVITY={value}#",  # Changed from CXCS to SZCS for writing to device

            # Missing command templates from Parameter UI List
            'jammer_relay_action': "JAMRELAY,{op},{time},{speed},{d},{e},{f},{g}#",
            'main_power_alert': "POWERALM,{enabled},{alert_type},{detection_time},{min_charge_time}#",
            'backup_battery_alert': "BATALM,{state},{mode}#",
            'vibration_sensitivity': "SZCS#VIBL={level}",
            'angle_report': "SZCS#ANGLEVALUE={min_speed}-{angle_variation}",
            'speed_buzzer': "SZCS#SPD_LED_SHOW={value}#",
            'sends_control': "SENDS,{value}#",
            'backup_battery_protection_voltage': "SZCS#BATSLPVALUE={value}#"
        }

    def _init_value_mappings(self) -> None:
        """Initialize value mappings for parameters that need translation based on LT32Pro documentation."""
        self.value_mappings = {
            # Network and Protocol Settings
            # Removed 'transmission_mode' mapping as it doesn't exist
            'gt06_protocol': {
                'GT06-0x60': '0',  # GT06 (0x60)
                'GT06-0x12': '2',  # GT06 (0x12)
                'CRX3': '1'        # CRX3 (0x22)
            },
            'network_select': {
                'AUTO': '0',  # Auto-select between 2G and 4G
                '4G': '1',    # 4G only
                '2G': '2'     # 2G only
            },

            # Sleep Mode Configuration
            'sleep_mode': {
                'Disabled': '0',    # Sleep mode disabled
                'Sleep': '1',       # Sleep mode (can receive SMS)
                'Deep Sleep': '2'   # Deep sleep mode (cannot receive SMS)
            },

            # Relay/Output Control
            'relay_control': {
                'OFF': '0',   # Disable output
                'ON': '1',     # Enable output
                'Desabilitada': '0',
                'Habilitada': '1'
            },
            'relay_gps_check': {
                'Check GPS': '0',   # Check GPS fix before activating output
                'Immediate': '1',    # Activate output immediately without checking GPS
                'Não verifica FIX de GPS': '1'
            },

            # Ignition Configuration
            'ignition_type': {
                'Digital': '0',   # Virtual ignition (based on movement)
                'Analog': '1'     # Physical ignition (based on voltage)
            },

            # Custom Parameters
            'lock_type': {
                'PIN': '0',     # PIN-based security
                'Card': '1'     # Card-based security
            },
            'curve_sensor': {
                'Disabled': '0',  # Curve sensor disabled
                'Enabled': '1',   # Curve sensor enabled
                'Auto': '2'       # Curve sensor in auto mode
            },

            # Jammer Relay Action Output Operation Mapping
            'jammer_output_operation': {
                'Sem Ação': '0',
                'Ativar e Manter': '1',
                'Ativar e Desativar com Jammer': '2'
            },

            'motion_sensor_alert': {
                'Desabilitado': 'DISABLED',
                'Alerta Enviado Apenas GPRS': 'GPRS_ONLY',
                'Alerta Enviado por SMS+GPRS': 'GPRS_SMS'
            },

            # Boolean ON/OFF mapping for various parameters
            'boolean_on_off': {
                True: 'ON',
                False: 'OFF'
            },

            # Alert type mapping for GPRS/SMS options
            'alert_type': {
                'Apenas GPRS': '0',
                'GPRS+SMS': '1'
            },

            # Speed alert enabled/disabled mapping
            'speed_alert_enabled': {
                True: 'ON',
                False: 'OFF'
            },

            # Battery alert state mapping
            'battery_alert_state': {
                True: 'ON',
                False: 'OFF'
            },

            # Battery alert mode mapping (for backup battery alert)
            'battery_alert_mode': {
                'GPRS': '0',
                'GPRS+SMS': '1'
            },

            # Main power alert enabled mapping
            'main_power_alert_enabled': {
                True: 'ON',
                False: 'OFF'
            },

            # Jammer detection state mapping
            'jammer_detection_state': {
                True: 'ON',
                False: 'OFF'
            },

            # Jammer detection mode mapping
            'jammer_detection_mode': {
                'GPRS': '0',
                'GPRS+SMS': '1'
            },

            # TCP ACK enabled/disabled mapping
            'tcp_ack_enabled': {
                True: '1',
                False: '0'
            },
            
            # TCP ACK value mapping for Parameter UI List compliance
            'tcp_ack': {
                'Enabled': '1',
                'Disabled': '0',
                True: '1',
                False: '0'
            },

            # Angle report enabled mapping
            'angle_report_enabled': {
                True: '1',
                False: '0'
            },

            # Speed buzzer enabled mapping
            'speed_buzzer_enabled': {
                True: '1',
                False: '0'
            },

            # Heartbeat Intervals (converted to seconds)
            'heartbeat_interval': {
                '30s': '30',
                '1min': '60',
                '5min': '300',
                '10min': '600',
                '30min': '1800',
                '1hr': '3600',
                '2hr': '7200',
                '6hr': '21600',
                '12hr': '43200',
                '24hr': '86400'
            },

            # Sleep mode mapping - Updated to match Parameter UI List exactly
            'sleep_mode': {
                'Desabilitado (Disabled)': 'Disabled',
                'Sleep (Habilitado)': 'Sleep',
                'Deep Sleep (Ultra-baixo)': 'Deep Sleep'
            },

            # Protocol mapping (GT06SEL values) - Updated to match Parameter UI List exactly
            'protocol': {
                'GT06 (0x60)': '0',
                'CRX3 (0x22)': '1',
                'CRX (0x12)': '2'
            },
            
            # GT06 protocol mapping for validation
            'gt06_protocol': {
                'GT06 (0x60)': 'GT06-0x60',
                'CRX3 (0x22)': 'CRX3',
                'CRX (0x12)': 'GT06-0x12'
            },

            # Ignition mode mapping
            'ignition_mode_value': {
                'Física (Physical)': '1',
                'Virtual por acelerômetro (Virtual by accelerometer)': '0',
                'Virtual por bateria (Virtual by battery)': '1'
            }
        }

    def get_command(self, param_name: str, value: Any, context: Dict[str, Any] = None,
                   confirm_destructive: bool = True, validate_command: bool = True) -> str:
        """
        Get the formatted AT command for a parameter with validation.

        Args:
            param_name: The parameter name
            value: The parameter value
            context: Optional context with additional parameter values needed for the command
            confirm_destructive: Whether to confirm destructive operations
            validate_command: Whether to validate the command before returning it

        Returns:
            The formatted AT command string

        Raises:
            ValueError: If command generation fails or validation fails
        """
        # Input validation
        if not param_name:
            raise ValueError("Parameter name cannot be empty")
        
        if not isinstance(param_name, str):
            raise ValueError(f"Parameter name must be a string, got {type(param_name).__name__}")
        
        self.logger.debug(f"Generating command for parameter: {param_name} with value: {value}")
        
        # Log context if provided
        if context:
            self.logger.debug(f"Command context: {context}")
        
        try:
            # Check if this is a destructive operation that requires confirmation
            if confirm_destructive and param_name in [
                'factory_reset', 'reset_device', 'format_device', 'clear_memory'
            ]:
                self.logger.warning(f"Destructive operation requested: {param_name}")
                
                # Map param_name to operation type
                operation_type_map = {
                    'factory_reset': 'OPERATION_FACTORY_RESET',
                    'reset_device': 'OPERATION_DEVICE_RESET',
                    'format_device': 'OPERATION_FORMAT_DEVICE',
                    'clear_memory': 'OPERATION_CLEAR_MEMORY'
                }

                # Get the app instance if available in context
                app = context.get('app') if context else None

                # If we have the app and operation confirmation service, confirm the operation
                if app and hasattr(app, 'operation_confirmation_service'):
                    operation_type = getattr(app.operation_confirmation_service, operation_type_map[param_name])
                    if not app.operation_confirmation_service.confirm_operation(operation_type):
                        self.logger.info(f"Destructive operation {param_name} was canceled by user")
                        raise ValueError(f"Operation {param_name} was canceled by user")
                    else:
                        self.logger.info(f"Destructive operation {param_name} confirmed by user")
                else:
                    self.logger.warning(f"No confirmation service available for destructive operation: {param_name}")

            # Check if this is a multi-field parameter that needs special handling
            multi_field_params = [
                'jammer_relay_action', 'main_power_alert', 'backup_battery_alert',
                'angle_report', 'speed_alert', 'moving_alert', 'vibration_window',
                'apn_settings', 'server_settings', 'report_intervals', 'heartbeat_intervals',
                'ignition_type', 'vibration_sensitivity', 'jammer_detection', 'motion_sensor_alert'
            ]
            
            command = None  # Initialize command variable
            
            if param_name in multi_field_params:
                self.logger.debug(f"Processing multi-field parameter: {param_name}")
                
                # Handle multi-field parameters using the specialized method
                if isinstance(value, dict):
                    # Value is already a dictionary of field values
                    field_values = value
                else:
                    # Convert single value to dictionary format for compatibility
                    self.logger.debug(f"Converting single value to dictionary format for {param_name}")
                    field_values = {'value': value}
                    if context:
                        field_values.update(context)
                
                # Use the multi-field parameter handler
                if param_name == 'moving_alert':
                    command_params = field_values.copy()
                    if 'enabled' in command_params:
                        command_params['enabled'] = 'ON' if command_params['enabled'] else 'OFF'
                    if 'alert_type' in command_params:
                        alert_type_map = self.value_mappings.get('alert_type', {})
                        if command_params['alert_type'] in alert_type_map:
                            command_params['alert_type'] = alert_type_map[command_params['alert_type']]
                elif param_name == 'vibration_window':
                    command_params = field_values.copy()
                    if 'threshold' in command_params:
                        command_params['value'] = command_params.pop('threshold')
                else:
                    command_params = self._handle_multi_field_parameter(param_name, field_values)
                
                # Get the command template
                template = self.command_templates.get(param_name)
                if not template:
                    available_templates = list(self.command_templates.keys())
                    raise ValueError(f"Unknown parameter: {param_name}. Available parameters: {available_templates}")
                
                self.logger.debug(f"Using template for {param_name}: {template}")
                
                # Special-case: when certain multi-field parameters are disabled, the
                # device expects a minimal command with only the state (e.g. "JAMMER,OFF#",
                # "SPEED,OFF#") instead of the full expanded template.
                try:
                    if param_name == 'jammer_detection' and command_params.get('state') == 'OFF':
                        # Generate minimal jammer command when disabled
                        command = f"JAMMER,{command_params.get('state')}#"
                        self.logger.debug(f"Using minimal command for disabled jammer_detection: {command}")
                    elif param_name == 'speed_alert' and command_params.get('enabled') == 'OFF':
                        # Generate minimal speed command when disabled
                        command = f"SPEED,OFF#"
                        self.logger.debug(f"Using minimal command for disabled speed_alert: {command}")
                    elif param_name == 'backup_battery_alert' and command_params.get('state') == 'OFF':
                        # Generate minimal backup battery command when disabled
                        command = "BATALM,OFF#"
                        self.logger.debug(f"Using minimal command for disabled backup_battery_alert: {command}")
                    elif param_name == 'backup_battery_alert':
                        # Enabled backup battery -> include mode (A)
                        mode = command_params.get('mode', '0')
                        # ensure numeric mode
                        try:
                            mode_int = int(mode)
                        except Exception:
                            mode_int = 0
                        if mode_int not in (0, 1):
                            mode_int = 0
                        command = f"BATALM,ON,{mode_int}#"
                        self.logger.debug(f"Using full command for backup_battery_alert: {command}")
                    elif param_name == 'motion_sensor_alert':
                        command = self._generate_motion_sensor_alert_command(field_values, validate_command)
                    else:
                        # Format the command using the mapped parameters
                        command = template.format(**command_params)
                        self.logger.debug(f"Formatted command for {param_name}: {command}")
                except KeyError as e:
                    missing_key = str(e).strip("'")
                    available_keys = list(command_params.keys())
                    raise ValueError(f"Missing required parameter: {missing_key} for {param_name}. Available parameters: {available_keys}")
                except Exception as e:
                    raise ValueError(f"Error formatting command template for {param_name}: {str(e)}")
            else:
                self.logger.debug(f"Processing single-field parameter: {param_name}")
                
                # Handle single-field parameters using the existing approach
                # Apply value mapping if needed
                try:
                    mapped_value = self._map_value(param_name, value)
                    self.logger.debug(f"Mapped value for {param_name}: {value} -> {mapped_value}")
                except Exception as e:
                    raise ValueError(f"Error mapping value for {param_name}: {str(e)}")

                # Get the command template
                template = self.command_templates.get(param_name)
                if not template:
                    available_templates = list(self.command_templates.keys())
                    raise ValueError(f"Unknown parameter: {param_name}. Available parameters: {available_templates}")

                self.logger.debug(f"Using template for {param_name}: {template}")

                # Prepare format arguments
                format_args = {'value': mapped_value}
                if context:
                    format_args.update(context)

                self.logger.debug(f"Format arguments for {param_name}: {format_args}")

                # Format the command
                try:
                    command = template.format(**format_args)
                    self.logger.debug(f"Formatted command for {param_name}: {command}")
                except KeyError as e:
                    missing_key = str(e).strip("'")
                    available_keys = list(format_args.keys())
                    raise ValueError(f"Missing required context parameter: {missing_key} for {param_name}. Available parameters: {available_keys}")
                except Exception as e:
                    raise ValueError(f"Error formatting command template for {param_name}: {str(e)}")
            
            # Add the command prefix for both single-field and multi-field parameters
            full_command = f"{self.command_prefix}{command}"
            self.logger.debug(f"Full command with prefix: {full_command}")
            
            # Validate the command using CommandValidationGateway if requested
            if validate_command and param_name not in ['vibration_window', 'network_select']:
                self.logger.debug(f"Validating command for {param_name}")
                
                validation_context = ValidationContext(
                    command_type=self._determine_command_type_from_param(param_name),
                    source='device_command_mapper',
                    timestamp=datetime.now()
                )
                
                validation_result = self.validation_gateway.validate_command_before_send(
                    full_command, validation_context
                )
                
                if not validation_result.is_valid:
                    error_msg = f"Command validation failed for {param_name}: {validation_result.error_message}"
                    if validation_result.suggestions:
                        error_msg += f". Suggestions: {'; '.join(validation_result.suggestions)}"
                    
                    self.logger.error(f"Command blocked by validation: {full_command}")
                    self.validation_gateway.log_blocked_command(validation_result, validation_context)
                    
                    raise ValueError(error_msg)
                
                self.logger.debug(f"Command validation passed for {param_name}: {full_command}")
            else:
                self.logger.debug(f"Command validation skipped for {param_name}")
            
            # Remove trailing '#' for SZCS commands during profile loading
            if full_command.startswith("ATSMS:SZCS#") and full_command.endswith('#'):
                # Check if this is a multi-part command like ACCLINE#ACC_CFG (these should keep their structure)
                command_body = full_command[6:]  # Remove "ATSMS:" prefix
                # Multi-part commands have multiple '=' signs or specific patterns like ACCLINE#ACC_CFG
                if 'ACCLINE=' in command_body and 'ACC_CFG=' in command_body:
                    # This is a multi-part ignition command, don't remove trailing '#'
                    self.logger.debug(f"Keeping multi-part SZCS command structure: {full_command}")
                else:
                    # This is a single SZCS command with trailing '#', remove it
                    full_command = full_command[:-1]
                    self.logger.debug(f"Removed trailing '#' for SZCS command: {full_command}")
            
            self.logger.info(f"Successfully generated command for {param_name}: {full_command}")
            return full_command
            
        except ValueError:
            # Re-raise ValueError exceptions as they contain user-friendly error messages
            raise
        except Exception as e:
            # Catch any other unexpected exceptions and provide detailed error information
            self.logger.error(f"Unexpected error generating command for {param_name}: {str(e)}")
            raise ValueError(f"Failed to generate command for parameter {param_name}: {str(e)}")

    def get_parameter_command_variations(self, section: str, param_name: str, values: Dict[str, Any]) -> List[str]:
        """
        Generate command variations for a parameter with multiple fields.
        
        This method handles both single-field and multi-field parameters and returns
        a list of commands for the given parameter.
        
        Args:
            section: The parameter section name
            param_name: The parameter name
            values: Dictionary of parameter field values
            
        Returns:
            List of commands for the parameter
            
        Raises:
            ValueError: If parameter is unknown or command generation fails
        """
        # Input validation
        if not section:
            raise ValueError("Section name cannot be empty")
        
        if not param_name:
            raise ValueError("Parameter name cannot be empty")
        
        if not isinstance(values, dict):
            raise ValueError(f"Values must be a dictionary, got {type(values).__name__}")
        
        self.logger.debug(f"Generating command variations for {section}.{param_name} with values: {values}")
        
        try:
            # Generate the command using the existing get_command method
            command = self.get_command(param_name, values, context={'section': section})
            
            self.logger.debug(f"Successfully generated command for {section}.{param_name}: {command}")
            return [command]
            
        except ValueError as e:
            # Provide detailed error message for unknown parameters
            if "Unknown parameter" in str(e):
                available_params = list(self.command_templates.keys())
                error_msg = f"Unknown parameter: {section}.{param_name}. Available parameters: {available_params}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                error_msg = f"Command generation failed for {section}.{param_name}: {str(e)}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
        except Exception as e:
            # Catch any other unexpected exceptions
            error_msg = f"Unexpected error generating command variations for {section}.{param_name}: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

    def _map_value(self, param_name: str, value: Any) -> str:
        """
        Map parameter values to their command equivalents if needed.
        
        Args:
            param_name: Name of the parameter
            value: Value to map
            
        Returns:
            Mapped value as string
            
        Raises:
            ValueError: If value mapping fails
        """
        try:
            if param_name == 'backup_battery_protection_voltage':
                try:
                    return str(int(float(value)))
                except (ValueError, TypeError):
                    self.logger.warning(f"Could not convert backup_battery_protection_voltage value '{value}' to int.")

            # Special handling for boolean values in specific parameters
            if param_name == 'speed_buzzer' and isinstance(value, bool):
                # Map boolean to 1/0 for speed buzzer
                mapped_value = '1' if value else '0'
                self.logger.debug(f"Mapped boolean value for {param_name}: {value} -> {mapped_value}")
                return mapped_value
            
            # Special handling for sleep mode values
            if param_name == 'sleep_mode':
                # Use the specification mapping for sleep mode
                from .parameter_specification import get_command_value_mapping
                sleep_mapping = get_command_value_mapping('sleep_mode')
                if sleep_mapping and value in sleep_mapping:
                    mapped_value = str(sleep_mapping[value])
                    self.logger.debug(f"Mapped sleep_mode value: {value} -> {mapped_value}")
                    return mapped_value
                # Fallback to internal mapping
                elif value in self.value_mappings.get('sleep_mode', {}):
                    mapped_value = str(self.value_mappings['sleep_mode'][value])
                    self.logger.debug(f"Mapped sleep_mode value (fallback): {value} -> {mapped_value}")
                    return mapped_value
            
            # Check if parameter has value mappings defined
            if param_name in self.value_mappings:
                mapping = self.value_mappings[param_name]
                
                if value in mapping:
                    mapped_value = mapping[value]
                    self.logger.debug(f"Mapped value for {param_name}: {value} -> {mapped_value}")
                    return str(mapped_value)
                else:
                    # Value not found in mapping - this might be an error
                    available_values = list(mapping.keys())
                    self.logger.warning(f"Value '{value}' not found in mapping for {param_name}. Available values: {available_values}")
                    
                    # For some parameters, unmapped values might be valid (e.g., numeric values)
                    # Log the issue but continue with the original value
                    if isinstance(value, (int, float, str)):
                        self.logger.debug(f"Using original value for {param_name}: {value}")
                        return str(value)
                    else:
                        raise ValueError(f"Invalid value '{value}' for parameter {param_name}. Valid values: {available_values}")
            else:
                # No mapping defined for this parameter - use value directly
                self.logger.debug(f"No value mapping defined for {param_name}, using original value: {value}")
                return str(value)
                
        except Exception as e:
            self.logger.error(f"Error mapping value for parameter {param_name}: {str(e)}")
            raise ValueError(f"Failed to map value '{value}' for parameter {param_name}: {str(e)}")

    def _determine_command_type_from_param(self, param_name: str) -> str:
        """
        Determine the command type based on the parameter name.
        
        Args:
            param_name: The parameter name
            
        Returns:
            String identifying the command type
        """
        if param_name.startswith('apn_'):
            return 'apn'
        elif param_name.startswith('server_'):
            return 'server'
        elif param_name.startswith('timer_'):
            return 'timer'
        elif param_name.startswith('heartbeat_'):
            return 'heartbeat'
        elif param_name in ['vibration', 'sensitivity', 'gt06_protocol', 'network_select', 
                           'sleep_mode', 'sleep_time', 'ignition_type',
                           'angle_reporting', 'blind_speed', 'curve_sensor', 'lock_type']:
            return 'szcs'
        else:
            return 'unknown'

    def validate_command(self, command: str) -> Tuple[bool, str]:
        """
        Validate a command string for proper format.

        Args:
            command: The command string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if command starts with prefix
        if not command.startswith(self.command_prefix):
            return False, f"Command must start with {self.command_prefix}"

        # Check for common format issues
        if not re.match(r'^ATSMS:[A-Z0-9#,_=:]+.*', command):
            return False, "Command format is invalid"

        # Check for specific command patterns
        command_body = command[len(self.command_prefix):]

        # Check APN command format
        if command_body.startswith("APN,"):
            parts = command_body.split(',')
            if len(parts) < 2 or not command_body.endswith('#'):
                return False, "Invalid APN command format. Should be APN,server,user,password#"

        # Check SERVER command format
        elif command_body.startswith("SERVER,"):
            parts = command_body.split(',')
            if len(parts) < 5 or not command_body.endswith('#'):
                return False, "Invalid SERVER command format. Should be SERVER,type,address,port,protocol#"

        # Check TIMER command format
        elif command_body.startswith("TIMER,"):
            parts = command_body.split(',')
            if len(parts) < 3 or not command_body.endswith('#'):
                return False, "Invalid TIMER command format. Should be TIMER,ign_on,ign_off#"

        # Check HBT command format
        elif command_body.startswith("HBT,"):
            parts = command_body.split(',')
            if len(parts) < 2 or not command_body.endswith('#'):
                return False, "Invalid HBT command format. Should be HBT,ign_on,ign_off#"

        # Check SZCS command format
        elif command_body.startswith("SZCS#"):
            if not re.match(r'^SZCS#[A-Z0-9_]+=.+#', command_body):
                return False, "Invalid SZCS command format. Should be SZCS#PARAM=value#"

        # All checks passed
        return True, ""

    def parse_device_response(self, response: str, command_type: str) -> Dict[str, Any]:
        """
        Parse device response based on the command type.

        Args:
            response: The device response string
            command_type: The type of command that was sent

        Returns:
            Dictionary with parsed information
        """
        result = {}

        # Handle different response types based on LT32Pro documentation
        if command_type == 'get_imei' or 'IMEI' in response:
            # Example responses:
            # "READOK: IMEI=868022038821794"
            # "IMEI: 868022038821794"
            # "IMEI:868022038821794"
            match = re.search(r'IMEI[=:]\s*(\d+)', response)
            if match:
                result['imei'] = match.group(1)

        elif command_type == 'get_teriid' or 'TERIID' in response:
            # Example responses:
            # "READOK: TERIID=864943044534994"
            # "TERIID: 864943044534994"
            # "TERIID:864943044534994"
            match = re.search(r'TERIID[=:]\s*(\d+)', response)
            if match:
                result['teriid'] = match.group(1)

        elif command_type == 'get_iccid' or 'ICCID' in response:
            # Example responses:
            # "READOK: ICCID=89860000192397786063"
            # "ICCID: 89860000192397786063"
            # "ICCID:89860000192397786063"
            match = re.search(r'ICCID[=:]\s*(\d+)', response)
            if match:
                result['iccid'] = match.group(1)

        elif command_type == 'get_imsi':
            # Example response: "READOK: IMSI=234588563274918"
            match = re.search(r'IMSI=(\d+)', response)
            if match:
                result['imsi'] = match.group(1)

        elif command_type == 'get_status':
            # Example response: "Battery:4.23V;GPRS:Offline;GSMSignalLevel:25;ACC:OFF;GPS:OFF;Defense:ON;"
            # Parse each section separated by semicolons
            for section in response.split(';'):
                if ':' in section:
                    key, value = section.split(':', 1)
                    result[key.strip()] = value.strip()

        elif command_type == 'get_version':
            # Example response: "W16A_10D6K_B44_V6.21 2024 11 15"
            result['version'] = response.strip()

        elif command_type == 'get_all_params':
            # Example response: "IMEI:357457040000821;TIMER:20,300;SEMDS:3;HBT:180Sec;Defense:3;"
            # Parse each section separated by semicolons
            for section in response.split(';'):
                if ':' in section:
                    key, value = section.split(':', 1)
                    result[key.strip()] = value.strip()

        # Handle bare device responses like "ACCOFFALM,OFF" (some firmwares reply without SETOK/READOK)
        elif re.search(r'^\s*ACCOFFALM\b', response, re.IGNORECASE):
            # Example device responses: "ACCOFFALM,OFF" or "ACCOFFALM OFF" or "ACCOFFALM:OFF"
            match = re.search(r'ACCOFFALM[,=:\s]*\s*(ON|OFF|\d+)', response, re.IGNORECASE)
            if match:
                param_value = match.group(1).upper()
                result['parameter'] = 'ACCOFFALM'
                result['value'] = param_value
                result['status'] = 'success'
                try:
                    self.logger.debug(f"Parsed bare ACCOFFALM response: raw={response!r} -> value={param_value}")
                except Exception:
                    print(f"DEBUG: Parsed bare ACCOFFALM response: raw={response!r} -> value={param_value}")
        # Handle command responses with SETOK prefix
        elif response.startswith('SETOK:'):
            # Example: "SETOK: VIBL=3"
            # Extract the parameter name and value
            match = re.search(r'SETOK:\s+([A-Z0-9_]+)=(.+)', response)
            if match:
                param_name = match.group(1)
                param_value = match.group(2)
                result['parameter'] = param_name
                result['value'] = param_value
                result['status'] = 'success'

        # Handle APN responses
        elif response.startswith('APN:'):
            # Example: "APN:cmnet,,"
            parts = response[4:].split(',')
            if len(parts) >= 1:
                result['apn_server'] = parts[0]
            if len(parts) >= 2:
                result['apn_user'] = parts[1]
            if len(parts) >= 3:
                result['apn_password'] = parts[2].rstrip('#')

        # Handle SERVER responses
        elif response.startswith('SERVER:'):
            # Example: "SERVER:0,58.61.154.247,7018,0"
            parts = response[7:].split(',')
            if len(parts) >= 4:
                result['server_type'] = parts[0]  # 0 for IP, 1 for domain
                result['server_address'] = parts[1]
                result['server_port'] = parts[2]
                result['server_protocol'] = parts[3]  # 0 for TCP

        # Handle TIMER responses
        elif response.startswith('TIMER ACC ON:'):
            # Example: "TIMER ACC ON:30s,ACC OFF:300s"
            match = re.search(r'TIMER ACC ON:(\d+)s,ACC OFF:(\d+)s', response)
            if match:
                result['timer_ign_on'] = match.group(1)
                result['timer_ign_off'] = match.group(2)

        # Handle HBT (Heartbeat) responses
        elif response.startswith('HBT ACC ON:'):
            # Example: "HBT ACC ON:180s,ACC OFF:180s"
            match = re.search(r'HBT ACC ON:(\d+)s,ACC OFF:(\d+)s', response)
            if match:
                result['heartbeat_ign_on'] = match.group(1)
                result['heartbeat_ign_off'] = match.group(2)

        elif response.startswith('JAMRELAY:'):
            # Example: "JAMRELAY:0,5,20,1,1,1,0"
            parts = response[len('JAMRELAY:'):].split(',')
            if len(parts) == 7:
                result['parameter'] = 'jammer_relay_action'
                result['value'] = {
                    'output_operation': parts[0],
                    'confirmation_time': parts[1],
                    'speed_limit': parts[2],
                    'd_parameter': parts[3],
                    'e_parameter': parts[4],
                    'f_parameter': parts[5],
                    'g_parameter': parts[6]
                }

        # Handle DEFENSE responses
        elif response.startswith('DEFENSE:'):
            # Example: "DEFENSE:3"
            match = re.search(r'DEFENSE:(\d+)', response)
            if match:
                result['defense_time'] = match.group(1)

        # Handle RELAY responses
        elif response.startswith('RELAY ') and response.endswith(' OK'):
            # Example: "RELAY 1 OK"
            match = re.search(r'RELAY (\d) OK', response)
            if match:
                result['relay_state'] = match.group(1)
                result['status'] = 'success'

        # Handle generic OK responses
        elif ' OK' in response:
            result['status'] = 'success'
            result['message'] = response

        return result

    def get_bulk_commands(self, parameters: Dict[str, Any], validate_commands: bool = True) -> List[str]:
        """
        Generate a list of commands for bulk sending based on LT32Pro documentation.
        This method processes all flattened parameters from the UI and generates appropriate commands.

        Args:
            parameters: Dictionary of flattened parameter names and values from UI
            validate_commands: Whether to validate commands before including them

        Returns:
            List of formatted commands in the correct sequence

        Raises:
            ValueError: If command validation fails for critical parameters
        """
        commands = []
        validation_errors = []
        validation_warnings = []
        processed_params = set()  # Track which parameters we've already processed

        self.logger.info(f"Starting bulk command generation for {len(parameters)} parameters")
        self.logger.info(f"Parameters keys: {list(parameters.keys())}")

        # Remove UI-only parameters that do not map to device commands
        params_to_ignore = []
        for p in params_to_ignore:
            if p in parameters:
                del parameters[p]

        # Pre-process to group flattened compound parameters
        compound_group_names = [
            'apn_settings', 'server_settings', 'report_intervals', 'heartbeat_intervals',
            'ignition_type', 'speed_alert', 'main_power_alert', 'angle_report',
            'vibration_sensitivity', 'jammer_relay_action', 'moving_alert', 'vibration_window'
        ]
        
        group_to_section = {
            'apn_settings': 'network_parameters', 'server_settings': 'network_parameters',
            'report_intervals': 'time_parameters', 'heartbeat_intervals': 'time_parameters',
            'ignition_type': 'ignition', 'speed_alert': 'speed',
            'main_power_alert': 'battery_alerts', 'angle_report': 'angle',
            'vibration_sensitivity': 'vibration_sensor', 'jammer_relay_action': 'jammer_detection',
            'moving_alert': 'alerts',
            'vibration_window': 'vibration_sensor'
        }

        new_params = {}
        keys_to_remove = []

        for key, value in parameters.items():
            if '.' in key:
                try:
                    group_name, field_name = key.split('.', 1)
                    if group_name in compound_group_names:
                        section = group_to_section[group_name]
                        new_key = f"{section}.{group_name}"
                        if new_key not in new_params:
                            new_params[new_key] = {}
                        new_params[new_key][field_name] = value
                        keys_to_remove.append(key)
                except ValueError:
                    # Handle cases where split doesn't produce 2 values, though '.' is present
                    pass

        for key in keys_to_remove:
            if key in parameters:
                del parameters[key]
        parameters.update(new_params)
        
        # Log all parameters for debugging
        self.logger.debug(f"All parameters received: {list(parameters.keys())}")
        for param_name, param_value in parameters.items():
            self.logger.debug(f"Parameter: {param_name} = {param_value} (type: {type(param_value).__name__})")

        # Group flattened parameters by their section and parameter name
        grouped_params = {}
        single_params = {}
        
        for param_name, param_value in parameters.items():
            if '.' in param_name:
                # This is a flattened parameter with section.parameter_name format
                section, param = param_name.split('.', 1)
                if section not in grouped_params:
                    grouped_params[section] = {}
                grouped_params[section][param] = param_value
            else:
                # This is a single parameter
                single_params[param_name] = param_value
        
        self.logger.debug(f"Grouped parameters: {grouped_params}")
        self.logger.debug(f"Single parameters: {single_params}")

        # Process compound commands from grouped parameters
        compound_groups = [
            # Network Configuration (Critical - send first)
            {
                'name': 'apn_settings',
                'section': 'network_parameters',
                'params': ['apn', 'user', 'password'],
                'required': ['apn'],  # At minimum we need the server
                'method': self._generate_apn_command
            },
            {
                'name': 'server_settings',
                'section': 'network_parameters',
                'params': ['address', 'port'],
                'required': ['address', 'port'],  # Both required
                'method': self._generate_server_command
            },
            
            # Timing Configuration
            {
                'name': 'report_intervals',
                'section': 'time_parameters',
                'params': ['moving_time', 'stopped_time'],
                'required': ['moving_time', 'stopped_time'],  # Both required
                'method': self._generate_timer_command
            },
            {
                'name': 'heartbeat_intervals',
                'section': 'time_parameters',
                'params': ['moving_heartbeat', 'stopped_heartbeat'],
                'required': ['moving_heartbeat', 'stopped_heartbeat'],  # Both required
                'method': self._generate_heartbeat_command
            },
            
            # Ignition Configuration
            {
                'name': 'ignition_type',
                'section': 'ignition',
                'params': ['ignition_mode', 'on_voltage', 'off_voltage'],
                'required': ['ignition_mode'],  # Mode is required, voltages are optional
                'method': self._generate_ignition_command
            },
            
            # Speed Alert Configuration
            {
                'name': 'speed_alert',
                'section': 'speed',
                'params': ['enabled', 'detection_time', 'speed_limit', 'alert_type'],
                'required': ['enabled'],  # At minimum we need enabled status
                'method': self._generate_speed_alert_command
            },
            
            # Power Alert Configuration
            {
                'name': 'main_power_alert',
                'section': 'battery_alerts',
                'params': ['enabled', 'alert_type', 'detection_time', 'min_charge_time'],
                'required': ['enabled'],
                'method': self._generate_main_power_alert_command
            },
            
            # Angle Report Configuration
            {
                'name': 'angle_report',
                'section': 'angle',
                'params': ['enabled', 'min_speed', 'angle_variation'],
                'required': ['enabled'],
                'method': self._generate_angle_report_command
            },
            
            # Vibration Configuration
            {
                'name': 'vibration_sensitivity',
                'section': 'vibration_sensor',
                'params': ['level'],
                'required': ['level'],
                'method': self._generate_vibration_command
            },
            
            # Jammer Relay Configuration
            {
                'name': 'jammer_relay_action',
                'section': 'jammer_detection',
                'params': ['output_operation', 'confirmation_time', 'speed_limit', 'param_d', 'param_e', 'param_f', 'param_g'],
                'required': ['output_operation'],
                'method': self._generate_jammer_relay_command
            }
        ]
        
        # Process compound commands first
        for group in compound_groups:
            self.logger.debug(f"Processing compound group: {group['name']}" )
            
            # Check if we have the section and required parameters for this group
            section = group.get('section')
            if section not in grouped_params:
                self.logger.debug(f"Section {section} not found in grouped parameters")
                continue
                
            section_params = grouped_params[section]
            param_name = group['name']
            
            if param_name not in section_params:
                self.logger.debug(f"Parameter {param_name} not found in section {section}")
                continue
                
            # Extract the parameter values
            param_values = section_params[param_name]
            if not isinstance(param_values, dict):
                self.logger.debug(f"Parameter {param_name} is not a dictionary: {type(param_values).__name__}")
                continue
            
            # Check if we have the required parameters for this group
            has_required = all(param in param_values and param_values[param] is not None and param_values[param] != '' 
                             for param in group['required'])
            
            self.logger.debug(f"Group {group['name']} has required params: {has_required}")
            
            if has_required:
                try:
                    # Collect all available parameters for this group
                    group_params = {}
                    for param in group['params']:
                        if param in param_values and param_values[param] is not None and param_values[param] != '':
                            group_params[param] = param_values[param]
                            self.logger.debug(f"Added param to group: {param} = {param_values[param]}")
                    
                    self.logger.debug(f"Group params collected: {group_params}")
                    
                    if group_params:  # Only process if we have some parameters
                        command = group['method'](group_params, validate_commands)
                        if command:
                            # Remove trailing '#' for SZCS commands during profile loading
                            if command.startswith("ATSMS:SZCS#") and command.endswith('#'):
                                command = command[:-1]
                                self.logger.debug(f"Removed trailing '#' for SZCS command in bulk operation: {command}")
                            commands.append(command)
                            self.logger.info(f"Added bulk command for {group['name']}: {command}")
                            # Mark these parameters as processed
                            processed_params.add(f"{section}.{param_name}")
                            self.logger.debug(f"Marked param as processed: {section}.{param_name}")
                        else:
                            self.logger.warning(f"No command generated for group: {group['name']}")
                    else:
                        self.logger.warning(f"No group params collected for: {group['name']}")
                            
                except ValueError as e:
                    if validate_commands and group['name'] in ['apn_settings', 'server_settings']:
                        error_msg = f"{group['name'].upper()} command validation failed: {str(e)}"
                        self.logger.error(error_msg)
                        validation_errors.append(f"{group['name']}: {error_msg}")
                    else:
                        warning_msg = f"Command validation failed for {group['name']}: {str(e)}"
                        validation_warnings.append(f"{group['name']}: {warning_msg}")
                        self.logger.warning(f"Non-critical parameter validation failed: {group['name']}")
                        
                except Exception as e:
                    self.logger.error(f"Unexpected error generating command for {group['name']}: {str(e)}")
                    if validate_commands and group['name'] in ['apn_settings', 'server_settings']:
                        validation_errors.append(f"{group['name']}: {str(e)}")
            else:
                # Log which required parameters are missing
                missing_params = [param for param in group['required'] 
                                 if param not in param_values or param_values[param] is None or param_values[param] == '']
                self.logger.debug(f"Group {group['name']} missing required params: {missing_params}")
        
        # Process single parameters that weren't part of compound commands
        individual_params = [
            'protocol', 'tcp_ack', 'speed_buzzer', 'sleep_mode', 'sleep_time',
            'backup_battery_alert', 'jammer_detection', 'odometer', 'hourmeter',
            'network_settings', 'defense_settings', 'source_off_type', 'relay_control', 'sends_control',
            'motion_sensor_alert', 'distance_movement_action', 'acc_on_alert', 'acc_off_alert', 'blind_area_speed'
        ]
        
        self.logger.info(f"Processing {len(individual_params)} individual parameters")
        self.logger.info(f"Individual parameters list: {individual_params}")
        self.logger.info(f"Single parameters keys: {list(single_params.keys())}")
        
        for param_name in individual_params:
            if param_name in single_params and param_name not in processed_params:
                param_value = single_params[param_name]
                
                self.logger.debug(f"Processing individual param: {param_name} = {param_value}")
                
                # Skip None values and empty strings
                if param_value is None or param_value == '':
                    self.logger.debug(f"Skipping individual param {param_name}: empty value")
                    continue
                    
                try:
                    command = self._generate_individual_command(param_name, param_value, validate_commands)
                    if command:
                        # Remove trailing '#' for SZCS commands during profile loading
                        if command.startswith("ATSMS:SZCS#") and command.endswith('#'):
                            command = command[:-1]
                            self.logger.debug(f"Removed trailing '#' for SZCS command in bulk operation: {command}")
                        commands.append(command)
                        self.logger.info(f"Added bulk command for {param_name}: {command}")
                        processed_params.add(param_name)
                    else:
                        self.logger.warning(f"No command generated for parameter: {param_name}")
                        
                except ValueError as e:
                    if validate_commands:
                        warning_msg = f"Command validation failed for {param_name}: {str(e)}"
                        validation_warnings.append(f"{param_name}: {warning_msg}")
                        self.logger.warning(f"Non-critical parameter validation failed: {param_name}")
                    else:
                        self.logger.warning(f"Command generation failed for {param_name}: {str(e)}")
                        
                except Exception as e:
                    self.logger.error(f"Unexpected error generating command for {param_name}: {str(e)}")
            else:
                if param_name in processed_params:
                    self.logger.debug(f"Skipping individual param {param_name}: already processed")
                elif param_name not in single_params:
                    self.logger.debug(f"Skipping individual param {param_name}: not in parameters")
        
        # Process any remaining parameters that weren't explicitly handled
        remaining_params = set(parameters.keys()) - processed_params
        if remaining_params:
            self.logger.info(f"Processing {len(remaining_params)} additional parameters: {remaining_params}")
            for param_name in remaining_params:
                param_value = parameters[param_name]
                
                self.logger.debug(f"Processing additional param: {param_name} = {param_value}")
                
                # Skip None values, empty strings, and metadata parameters
                if param_value is None or param_value == '' or param_name in ['profile_name', 'created_date', 'device_imei', 'version']:
                    self.logger.debug(f"Skipping additional param {param_name}: empty or metadata")
                    continue
                    
                try:
                    # Try to generate a command using the generic get_command method
                    short_param_name = param_name.split('.')[-1]
                    command = self.get_command(short_param_name, param_value, validate_command=validate_commands)
                    if command:
                        # Remove trailing '#' for SZCS commands during profile loading
                        if command.startswith("ATSMS:SZCS#") and command.endswith('#'):
                            command = command[:-1]
                            self.logger.debug(f"Removed trailing '#' for SZCS command in bulk operation: {command}")
                        commands.append(command)
                        self.logger.info(f"Added bulk command for additional parameter {param_name}: {command}")
                        processed_params.add(param_name)
                    else:
                        self.logger.debug(f"No command generated for additional parameter {param_name}")
                        
                except Exception as e:
                    self.logger.debug(f"Could not generate command for additional parameter {param_name}: {str(e)}")
        
        # Log which parameters were not processed
        unprocessed_params = set(parameters.keys()) - processed_params
        if unprocessed_params:
            self.logger.warning(f"Unprocessed parameters ({len(unprocessed_params)}): {unprocessed_params}")
            for param_name in unprocessed_params:
                param_value = parameters[param_name]
                self.logger.warning(f"Unprocessed param: {param_name} = {param_value} (type: {type(param_value).__name__})")
        
        # Check if we have critical validation errors that should block the operation
        if validation_errors:
            error_summary = f"Critical parameter validation failed: {'; '.join(validation_errors)}"
            self.logger.error(error_summary)
            raise ValueError(error_summary)
        
        # Log validation warnings for non-critical parameters
        if validation_warnings:
            warning_summary = f"Non-critical parameter validation warnings: {'; '.join(validation_warnings)}"
            self.logger.warning(warning_summary)

        self.logger.info(f"Generated {len(commands)} bulk commands from {len(parameters)} parameters")
        return commands
    
    # Format methods for bulk command generation
    def format_apn_command(self, apn: str, user: str = "", password: str = "") -> str:
        """Format APN configuration command."""
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                command = f"ATSMS:APN,{apn},{user},{password}#"
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
                return command
            except ValueError as e:
                raise ValueError(f"APN command validation failed: {str(e)}")
        return f"ATSMS:APN,{apn},{user},{password}#"
    
    def _determine_server_type(self, address: str) -> str:
        """Determine server type: 0 for IP address, 1 for domain name."""
        import re
        # Check if address is an IP address (IPv4)
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ip_pattern, address):
            return '0'  # IP address
        else:
            return '1'  # Domain name
    
    def format_server_command(self, address: str, port: str) -> str:
        """Format server configuration command."""
        # Determine server type (0 for IP, 1 for domain)
        server_type = self._determine_server_type(address)
        command = f"ATSMS:SERVER,{server_type},{address},{port},0#"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Server command validation failed: {str(e)}")
        return command
    
    def format_timer_command(self, moving_time: int, stopped_time: int) -> str:
        """Format timer configuration command."""
        command = f"ATSMS:TIMER,{moving_time},{stopped_time}#"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Timer command validation failed: {str(e)}")
        return command
    
    def format_hbt_command(self, moving_hbt: int, stopped_hbt: int) -> str:
        """Format heartbeat configuration command."""
        command = f"ATSMS:HBT,{moving_hbt},{stopped_hbt}#"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Heartbeat command validation failed: {str(e)}")
        return command
    
    def format_ignition_command(self, ignition_mode: str, on_voltage: float = None, off_voltage: float = None) -> str:
        """Format ignition configuration command."""
        if ignition_mode == 'Virtual por bateria (Virtual by battery)':
            if on_voltage is None or off_voltage is None:
                raise ValueError("On and off voltages are required for virtual battery ignition mode")
            
            # Convert voltages to integers
            on_voltage_int = int(float(on_voltage))
            off_voltage_int = int(float(off_voltage))
            
            command = f"ATSMS:SZCS#ACCLINE=1#ACC_CFG=1-{on_voltage_int}-{off_voltage_int}"
        elif ignition_mode == 'Física (Physical)':
            command = f"ATSMS:SZCS#ACCLINE=1#ACC_CFG=0-000-000"
        else: # 'Virtual por acelerômetro (Virtual by accelerometer)'
            command = f"ATSMS:SZCS#ACCLINE=0#ACC_CFG=0-000-000"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Ignition command validation failed: {str(e)}")
        return command
    
    def format_speed_alert_command(self, enabled: bool, detection_time: int, speed_limit: int, alert_type: str) -> str:
        """Format speed alert configuration command."""
        enabled_str = 'ON' if enabled else 'OFF'
        # When disabled, device expects a minimal SPEED,OFF# command (no extra numeric fields)
        if not enabled:
            command = f"ATSMS:SPEED,OFF#"
        else:
            alert_type_code = self._map_alert_type(alert_type)
            command = f"ATSMS:SPEED,{enabled_str},{detection_time},{speed_limit},{alert_type_code}#"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Speed alert command validation failed: {str(e)}")
        return command

    def _generate_jammer_detection_command(self, values: Dict[str, Any]) -> Optional[str]:
        """
        Generate JAMMER command from specification-based parameter values.

        Accepts both {'value': bool} and {'enabled': bool} formats and returns
        the fully formatted ATSMS: command string.
        """
        try:
            enabled = values.get('value') if 'value' in values else values.get('enabled', False)
            if not isinstance(enabled, bool):
                enabled = bool(enabled)

            # Delegate to existing formatter which already implements minimal form for OFF
            return self.format_jammer_detection_command(enabled)
        except Exception as e:
            self.logger.error(f"Error generating jammer detection command: {str(e)}")
            return None
    
    def format_main_power_alert_command(self, enabled: bool, alert_type: str, detection_time: int, min_charge_time: int) -> str:
        """Format main power alert configuration command."""
        enabled_str = 'ON' if enabled else 'OFF'
        alert_type_code = self._map_alert_type(alert_type)
        command = f"ATSMS:POWERALM,{enabled_str},{alert_type_code},{int(detection_time)},{int(min_charge_time)}#"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Main power alert command validation failed: {str(e)}")
        return command
    
    def format_angle_report_command(self, enabled: bool, min_speed: int, angle_variation: int) -> str:
        """Format angle report configuration command."""
        # Ensure formatting: min_speed -> 2 digits, angle_variation -> 3 digits
        if enabled:
            min_speed_str = f"{int(min_speed):02d}"
            angle_variation_str = f"{int(angle_variation):03d}"
            command = f"ATSMS:SZCS#ANGLEVALUE={min_speed_str}-{angle_variation_str}"
        else:
            command = f"ATSMS:SZCS#ANGLEVALUE=00-000"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Angle report command validation failed: {str(e)}")
        return command
    
    def format_vibration_sensitivity_command(self, level: int) -> str:
        """Format vibration sensitivity configuration command."""
        command = f"ATSMS:SZCS#VIBL={level}"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Vibration sensitivity command validation failed: {str(e)}")
        return command
    
    def format_jammer_relay_command(self, output_operation: str, confirmation_time: int, speed_limit: int, param_d: int, param_e: int, param_f: int, param_g: str) -> str:
        """Format jammer relay configuration command."""
        operation_code = self._map_jammer_operation(output_operation)
        param_g_code = self._map_param_g_value(param_g)
        command = f"ATSMS:JAMRELAY,{operation_code},{confirmation_time},{speed_limit},{param_d},{param_e},{param_f},{param_g_code}#"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Jammer relay command validation failed: {str(e)}")
        return command
    
    def _map_alert_type(self, alert_type: str) -> str:
        """Map alert type UI value to device command value."""
        alert_type_mapping = {
            'Apenas GPRS': '0',
            'GPRS+SMS': '1'
        }
        return alert_type_mapping.get(alert_type, '0')

    def _map_jammer_operation(self, output_operation: str) -> str:
        """Map jammer output operation UI value to device command value."""
        operation_mapping = {
            'Sem Ação': '0',
            'Ativar e Manter': '1',
            'Ativar e Desativar com Jammer': '2'
        }
        return operation_mapping.get(output_operation, '0')

    def _map_param_g_value(self, param_g: str) -> str:
        """Map param_g UI value to device command value."""
        param_g_mapping = {
            'Manter ativada': '0',
            'Manter desativada': '1'
        }
        return param_g_mapping.get(param_g, '0')

    def _map_protocol_value(self, protocol: str) -> str:
        """Map protocol UI value to device command value."""
        protocol_mapping = {
            'GT06 (0x60)': '0',
            'CRX3 (0x22)': '1', 
            'CRX (0x12)': '2'
        }
        return protocol_mapping.get(protocol, '0')  # Default to GT06
    
    def format_protocol_command(self, protocol: str) -> str:
        """Format protocol configuration command."""
        protocol_code = self._map_protocol_value(protocol)
        command = f"ATSMS:SZCS#GT06SEL={protocol_code}"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Protocol command validation failed: {str(e)}")
        return command
    
    def format_tcp_ack_command(self, tcp_ack: bool) -> str:
        """Format TCP ACK configuration command."""
        ack_value = '1' if tcp_ack else '0'
        command = f"ATSMS:SZCS#POSBYACK={ack_value}"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"TCP ACK command validation failed: {str(e)}")
        return command
    
    def format_speed_buzzer_command(self, enabled: bool) -> str:
        """Format speed buzzer configuration command."""
        buzzer_value = '1' if enabled else '0'
        command = f"ATSMS:SZCS#SPD_LED_SHOW={buzzer_value}"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Speed buzzer command validation failed: {str(e)}")
        return command
    
    def _map_sleep_mode_value(self, sleep_mode: str) -> str:
        """Map sleep mode UI value to device command value."""
        sleep_mode_mapping = {
            'Desabilitado (Disabled)': '0',
            'Sleep (Habilitado)': '1',
            'Deep Sleep (Ultra-baixo)': '2'
        }
        return sleep_mode_mapping.get(sleep_mode, '0')  # Default to disabled
    
    def format_sleep_mode_command(self, sleep_mode: str) -> str:
        """Format sleep mode configuration command."""
        mode_code = self._map_sleep_mode_value(sleep_mode)
        command = f"ATSMS:SZCS#SLPDISCONNECT={mode_code}"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Sleep mode command validation failed: {str(e)}")
        return command
    
    def format_sleep_time_command(self, sleep_time: int) -> str:
        """Format sleep time configuration command."""
        command = f"ATSMS:SZCS#SLEEPT={int(sleep_time)}"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Sleep time command validation failed: {str(e)}")
        return command
    
    def format_backup_battery_alert_command(self, enabled: bool) -> str:
        """Format backup battery alert configuration command."""
        state = 'ON' if enabled else 'OFF'
        command = f"ATSMS:BATALM,{state},0#"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Backup battery alert command validation failed: {str(e)}")
        return command
    
    def format_jammer_detection_command(self, enabled: bool) -> str:
        """Format jammer detection configuration command."""
        state = 'ON' if enabled else 'OFF'
        
        if not enabled:
            command = f"ATSMS:JAMMER,{state}#"
        else:
            command = f"ATSMS:JAMMER,{state},0#"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Jammer detection command validation failed: {str(e)}")
        return command
    
    def format_odometer_command(self, value: int) -> str:
        """Format odometer configuration command."""
        command = f"ATSMS:MILEAGE={value}#"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Odometer command validation failed: {str(e)}")
        return command
    
    def format_hourmeter_command(self, value: int) -> str:
        """Format hourmeter configuration command."""
        command = f"ATSMS:ACCONT,{value}#"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Hourmeter command validation failed: {str(e)}")
        return command

    def format_distance_movement_action_command(self, value: str) -> str:
        """Format distance movement action configuration command."""
        # Map distance movement action to command value
        distance_movement_action_mapping = {
            'Automaticamente ativado após entrar no modo DEFENSE (quando a ignição é desligada)': '0',
            'Envia um alerta - Apenas uma vez independente da IGN on ou off': '1',
            'Envia um alerta uma vez e bloqueia o veículo - Apenas uma vez independente da IGN on ou off': '2'
        }
        
        value_code = distance_movement_action_mapping.get(value, '0')
        command = f"ATSMS:SZCS#MOVEALMFUN={value_code}"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Distance movement action command validation failed: {str(e)}")
        return command

    def format_blind_area_speed_command(self, value: int) -> str:
        """Format blind area speed configuration command."""
        # Ensure value is within valid range (0-20)
        if value < 0 or value > 20:
            raise ValueError(f"Blind area speed value must be between 0 and 20, got {value}")
        
        command = f"ATSMS:SZCS#BLINDSPD={value}"
        
        if hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
            try:
                self.command_validation_gateway.validate_command(command, source="bulk_commands")
            except ValueError as e:
                raise ValueError(f"Blind area speed command validation failed: {str(e)}")
        return command

    def _generate_apn_command(self, apn_params: Dict[str, Any], validate_commands: bool) -> Optional[str]:
        """Generate APN command from flattened parameters.
        
        Accept multiple incoming key names for robustness: 'apn_server'|'apn'|'server' and
        'apn_user'|'user', 'apn_password'|'password'. Ensure values are stringified and
        return None if APN server is missing.
        """
        try:
            # Accept several possible keys coming from different parts of the codebase
            apn_server = apn_params.get('apn_server') or apn_params.get('apn') or apn_params.get('server') or ''
            apn_user = apn_params.get('apn_user') or apn_params.get('user') or ''
            apn_password = apn_params.get('apn_password') or apn_params.get('password') or ''
    
            # Normalize to strings and guard against None
            apn_server = '' if apn_server is None else str(apn_server)
            apn_user = '' if apn_user is None else str(apn_user)
            apn_password = '' if apn_password is None else str(apn_password)
    
            if not apn_server.strip():
                self.logger.warning("APN server is required for APN command")
                return None
    
            return self.format_apn_command(apn_server, apn_user, apn_password)
    
        except Exception as e:
            self.logger.error(f"Error generating APN command: {str(e)}")
            return None
    
    def _generate_server_command(self, server_params: Dict[str, Any], validate_commands: bool) -> Optional[str]:
        """Generate server command from flattened parameters.
        
        Be tolerant of different key names produced by various code paths:
        accept 'server_address'|'address'|'server_ip'|'server_domain' and
        'server_port'|'port'. Coerce port to integer and return None when required
        pieces are missing.
        """
        try:
            # Try multiple possible keys for address and port
            server_address = (server_params.get('server_address') or
                              server_params.get('address') or
                              server_params.get('server_ip') or
                              server_params.get('server_domain') or
                              '')
    
            server_port = (server_params.get('server_port') or
                           server_params.get('port') or
                           '')
    
            # Normalize and validate
            server_address = '' if server_address is None else str(server_address)
    
            if server_port is None or server_port == '':
                self.logger.warning("Both server address and port are required for server command")
                return None
    
            # Coerce port to integer where possible, fall back to 0
            try:
                server_port_int = int(float(server_port))
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid server port value '{server_port}', defaulting to 0")
                server_port_int = 0
    
            if not server_address.strip():
                self.logger.warning("Server address is required for server command")
                return None
    
            return self.format_server_command(str(server_address), str(server_port_int))
    
        except Exception as e:
            self.logger.error(f"Error generating server command: {str(e)}")
            return None
    
    def _generate_timer_command(self, timer_params: Dict[str, Any], validate_commands: bool) -> Optional[str]:
        """Generate timer command from flattened parameters."""
        try:
            moving_time = timer_params.get('moving_time')
            stopped_time = timer_params.get('stopped_time')
            
            if moving_time is None or stopped_time is None:
                self.logger.warning("Both moving and stopped times are required for timer command")
                return None
                
            return self.format_timer_command(int(float(moving_time)), int(float(stopped_time)))
            
        except Exception as e:
            self.logger.error(f"Error generating timer command: {str(e)}")
            return None
    
    def _generate_heartbeat_command(self, hbt_params: Dict[str, Any], validate_commands: bool) -> Optional[str]:
        """Generate heartbeat command from flattened parameters."""
        try:
            moving_hbt = hbt_params.get('moving_heartbeat')
            stopped_hbt = hbt_params.get('stopped_heartbeat')
            
            if moving_hbt is None or stopped_hbt is None:
                self.logger.warning("Both moving and stopped heartbeats are required for heartbeat command")
                return None
                
            return self.format_hbt_command(int(float(moving_hbt)), int(float(stopped_hbt)))
            
        except Exception as e:
            self.logger.error(f"Error generating heartbeat command: {str(e)}")
            return None
    
    def _generate_ignition_command(self, ignition_params: Dict[str, Any], validate_commands: bool) -> Optional[str]:
        """Generate ignition command from flattened parameters."""
        try:
            ignition_mode = ignition_params.get('ignition_mode')
            on_voltage = ignition_params.get('on_voltage')
            off_voltage = ignition_params.get('off_voltage')
            
            if not ignition_mode:
                self.logger.warning("Ignition mode is required for ignition command")
                return None
                
            return self.format_ignition_command(ignition_mode, on_voltage, off_voltage)
            
        except Exception as e:
            self.logger.error(f"Error generating ignition command: {str(e)}")
            return None
    
    def _generate_speed_alert_command(self, speed_params: Dict[str, Any], validate_commands: bool) -> Optional[str]:
        """Generate speed alert command from flattened parameters."""
        try:
            enabled = speed_params.get('speed_alert_enabled', False)
            detection_time = speed_params.get('speed_detection_time', 0)
            speed_limit = speed_params.get('speed_limit', 0)
            alert_type = speed_params.get('speed_alert_type', 'Apenas GPRS')
            
            return self.format_speed_alert_command(enabled, detection_time, speed_limit, alert_type)
            
        except Exception as e:
            self.logger.error(f"Error generating speed alert command: {str(e)}")
            return None
    
    def _generate_main_power_alert_command(self, power_params: Dict[str, Any], validate_commands: bool) -> Optional[str]:
        """Generate main power alert command from flattened parameters."""
        try:
            enabled = power_params.get('enabled', False)
            alert_type = power_params.get('alert_type', 'Apenas GPRS')
            detection_time = power_params.get('detection_time', 10)
            min_charge_time = power_params.get('min_charge_time', 10)
            
            return self.format_main_power_alert_command(enabled, alert_type, detection_time, min_charge_time)
            
        except Exception as e:
            self.logger.error(f"Error generating main power alert command: {str(e)}")
            return None
    
    def _generate_angle_report_command(self, angle_params: Dict[str, Any], validate_commands: bool) -> Optional[str]:
        """Generate angle report command from flattened parameters."""
        try:
            enabled = angle_params.get('enabled', False)
            
            # Use actual values from profile instead of defaults
            min_speed_raw = angle_params.get('min_speed', '08')
            angle_variation_raw = angle_params.get('angle_variation', '015')
            
            # Convert to int for the format_angle_report_command method but preserve original formatting
            try:
                min_speed = int(str(min_speed_raw))
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid min_speed value: {min_speed_raw}, using default 8")
                min_speed = 8
            
            try:
                angle_variation = int(str(angle_variation_raw))
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid angle_variation value: {angle_variation_raw}, using default 15")
                angle_variation = 15
            
            self.logger.debug(f"Using angle_report values from profile: min_speed={min_speed}, angle_variation={angle_variation}")
            
            return self.format_angle_report_command(enabled, min_speed, angle_variation)
            
        except Exception as e:
            self.logger.error(f"Error generating angle report command: {str(e)}")
            return None
    
    def _generate_vibration_command(self, vibration_params: Dict[str, Any], validate_commands: bool) -> Optional[str]:
        """Generate vibration command from flattened parameters."""
        try:
            level = vibration_params.get('vibration_level', 1)
            
            return self.format_vibration_sensitivity_command( level)
            
        except Exception as e:
            self.logger.error(f"Error generating vibration command: {str(e)}")
            return None
    
    def _generate_jammer_relay_command(self, jammer_params: Dict[str, Any], validate_commands: bool) -> Optional[str]:
        """Generate jammer relay command from flattened parameters."""
        try:
            output_operation = jammer_params.get('output_operation', 'Sem Ação')
            confirmation_time = jammer_params.get('confirmation_time', 80)
            speed_limit = jammer_params.get('speed_limit', 5)
            param_d = jammer_params.get('param_d', 0)
            param_e = jammer_params.get('param_e', 0)
            param_f = jammer_params.get('param_f', 0)
            param_g = jammer_params.get('param_g', 'Manter ativada')
            
            return self.format_jammer_relay_command(output_operation, confirmation_time, speed_limit, param_d, param_e, param_f, param_g)
            
        except Exception as e:
            self.logger.error(f"Error generating jammer relay command: {str(e)}")
            return None

    def _generate_motion_sensor_alert_command(self, params: Dict[str, Any], validate_commands: bool) -> Optional[str]:
        """Generate motion sensor alert command from flattened parameters."""
        try:
            value = params.get('value')
            if value == 'Desabilitado':
                command = "SENALM,OFF#"
            elif value == 'Alerta Enviado Apenas GPRS':
                command = "SENALM,ON,0#"
            elif value == 'Alerta Enviado por SMS+GPRS':
                command = "SENALM,ON,1#"
            else:
                return None
            
            if validate_commands and hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
                full_command = f"ATSMS:{command}"
                self.command_validation_gateway.validate_command(full_command, source="bulk_commands")

            return command
        except Exception as e:
            self.logger.error(f"Error generating motion sensor alert command: {str(e)}")
            return None

    def _generate_acc_on_alert_command(self, params: Dict[str, Any], validate_commands: bool) -> Optional[str]:
        """Generate ACC ON alert command from flattened parameters."""
        try:
            value = params.get('value')
            if value == 'Disabled':
                command = "ACCALM,OFF#"
            elif value == 'Enabled (GPRS)':
                command = "ACCALM,ON,0#"
            elif value == 'Enabled (SMS+GPRS)':
                command = "ACCALM,ON,1#"
            else:
                # For backward compatibility, check for simple 'Enabled'
                if value == 'Enabled':
                    command = "ACCALM,ON,0#" # Default to GPRS only
                else:
                    return None
            
            if validate_commands and hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
                full_command = f"ATSMS:{command}"
                self.command_validation_gateway.validate_command(full_command, source="bulk_commands")

            return command
        except Exception as e:
            self.logger.error(f"Error generating acc on alert command: {str(e)}")
            return None

    def _generate_acc_off_alert_command(self, params: Dict[str, Any], validate_commands: bool) -> Optional[str]:
        """Generate ACC OFF alert command from flattened parameters."""
        try:
            value = params.get('value')
            if value == 'Desabilitado':
                command = "ACCOFFALM,OFF#"
            elif value == 'Alerta Enviado Apenas GPRS':
                command = "ACCOFFALM,ON,0#"
            elif value == 'Alerta Enviado por SMS+GPRS':
                command = "ACCOFFALM,ON,1#"
            else:
                return None
            
            if validate_commands and hasattr(self, 'command_validation_gateway') and self.command_validation_gateway:
                full_command = f"ATSMS:{command}"
                self.command_validation_gateway.validate_command(full_command, source="bulk_commands")

            return command
        except Exception as e:
            self.logger.error(f"Error generating acc off alert command: {str(e)}")
            return None
    
    def _generate_individual_command(self, param_name: str, param_value: Any, validate_commands: bool) -> Optional[str]:
        """Generate command for individual parameters."""
        try:
            # Map individual parameters to their command methods
            individual_mapping = {
                'protocol': lambda v: self.format_protocol_command(v),
                'tcp_ack': lambda v: self.format_tcp_ack_command(v),
                'speed_buzzer': lambda v: self.format_speed_buzzer_command(v),
                'sleep_mode': lambda v: self.format_sleep_mode_command(v),
                'sleep_time': lambda v: self.format_sleep_time_command(int(float(v)) if v is not None else 0),
                'backup_battery_alert': lambda v: self.format_backup_battery_alert_command(v),
                'jammer_detection': lambda v: self.format_jammer_detection_command(v),
                'odometer': lambda v: self.format_odometer_command(v),
                'hourmeter': lambda v: self.format_hourmeter_command(v),
                'network_settings': lambda v: self.get_command('network_select', v),
                'defense_settings': lambda v: self.get_command('defense_time', v),
                'source_off_type': lambda v: self.get_command('relay_gps_check', v),
                'relay_control': lambda v: self.get_command('relay_control', v),
                'sends_control': lambda v: self.get_command('sends_control', v),
                'motion_sensor_alert': lambda v: self._generate_motion_sensor_alert_command({'value': v}, validate_commands),
                'acc_on_alert': lambda v: self._generate_acc_on_alert_command({'value': v}, validate_commands),
                'acc_off_alert': lambda v: self._generate_acc_off_alert_command({'value': v}, validate_commands),
                'distance_movement_action': lambda v: self.format_distance_movement_action_command(v),
                'blind_area_speed': lambda v: self.format_blind_area_speed_command(int(float(v)) if v is not None else 0)
            }
            
            if param_name in individual_mapping:
                return individual_mapping[param_name](param_value)
            else:
                self.logger.debug(f"No individual command mapping for parameter: {param_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating individual command for {param_name}: {str(e)}")
            return None

    def get_validation_statistics(self) -> Dict[str, Any]:
        """
        Get validation statistics from the command validation gateway.
        
        Returns:
            Dictionary with validation statistics
        """
        return self.validation_gateway.get_validation_statistics()
    
    def reset_validation_statistics(self):
        """Reset validation statistics."""
        self.validation_gateway.reset_statistics()
    
    def validate_parameters_before_bulk_send(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters before generating bulk commands.
        
        Args:
            parameters: Dictionary of parameter names and values
            
        Returns:
            Dictionary with validation results and recommendations
        """