"""
Parameter Response Parser for LT32 PRO Configurator

This module provides comprehensive response parsing for all parameter types
as defined in the Parameter UI List specification. It handles different response
formats, extracts multiple values from complex responses, and provides detailed
error handling for invalid or unexpected response formats.
"""

import re
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from services.parameter_specification import (
    get_parameter_specification, 
    get_command_value_mapping,
    PARAMETER_SPECIFICATION
)


@dataclass
class ParsedResponse:
    """Result of parsing a device response."""
    parameter_name: str
    command: str
    success: bool
    parsed_values: Dict[str, Any]
    raw_response: str
    error_message: Optional[str]
    timestamp: datetime


@dataclass
class ParseError:
    """Details of a parsing error."""
    parameter_name: str
    raw_response: str
    expected_pattern: str
    error_type: str
    error_message: str
    timestamp: datetime


class ParameterResponseParser:
    """
    Parser for device responses to parameter read commands.
    
    This class handles parsing of all parameter response formats according to
    the Parameter UI List specification, including complex multi-value responses
    and conditional parameter parsing.
    """

    def __init__(self):
        """Initialize the parameter response parser."""
        self.logger = logging.getLogger(__name__)
        self._init_response_patterns()
        self._init_value_mappings()

    def _init_response_patterns(self) -> None:
        """Initialize regex patterns for parsing device responses based on specification."""
        self.response_patterns = {
            # Network Parameters
            'apn_settings': {
                'pattern': r'APN:([^,]*),([^,]*),([^#]*)',
                'fields': ['apn', 'user', 'password'],
                'description': 'APN configuration response'
            },
            'server_settings': {
                'pattern': r'SERVER:(\d+),([^,]*),(\d+),(\d+)',
                'fields': ['type', 'address', 'port', 'protocol'],
                'description': 'Server configuration response',
                'post_process': self._process_server_response
            },
            
            # Time Parameters
            'report_intervals': {
                'pattern': r'TIMER:\s*(\d+)\s*,\s*(\d+)|TIMER\s+ACC\s+ON:\s*(\d+)s?\s*,\s*ACC\s+OFF:\s*(\d+)s?',
                'fields': ['moving_time', 'stopped_time'],
                'description': 'Report interval configuration response',
                'post_process': self._process_timer_response
            },
            'heartbeat_intervals': {
                'pattern': r'HBT:(\d+),(\d+)|HBT ACC ON:(\d+)s,ACC OFF:(\d+)s',
                'fields': ['moving_heartbeat', 'stopped_heartbeat'],
                'description': 'Heartbeat interval configuration response',
                'post_process': self._process_hbt_response
            },
            
            # Service Parameters
            'protocol': {
                'pattern': r'GT06SEL=(\d+)',
                'fields': ['protocol_value'],
                'description': 'Protocol selection response',
                'post_process': self._process_protocol_response
            },
            'tcp_ack': {
                'pattern': r'POSBYACK=(\d+)',
                'fields': ['ack_value'],
                'description': 'TCP ACK configuration response',
                'post_process': self._process_tcp_ack_response
            },
            
            # Ignition Parameters (complex multi-command response)
            'ignition_type': {
                'patterns': {
                    'accline': r'ACCLINE=(\d+)',
                    'acc_cfg': r'ACC_CFG=(\d+)[,-](\d+)[,-](\d+)'
                },
                'fields': {
                    'accline': ['accline_value'],
                    'acc_cfg': ['cfg_type', 'on_voltage', 'off_voltage']
                },
                'description': 'Ignition type configuration response',
                'post_process': self._process_ignition_response
            },
            
            # Speed Parameters
            'speed_alert': {
                'pattern': r'SPEED:(OFF|(\d+),(\d+),(\d+),(\d+))',
                'fields': ['full_match', 'enabled', 'detection_time', 'speed_limit', 'alert_type'],
                'description': 'Speed alert configuration response',
                'post_process': self._process_speed_alert_response
            },
            'speed_buzzer': {
                'pattern': r'SPD_LED_SHOW=(\d+)',
                'fields': ['enabled'],
                'description': 'Speed buzzer configuration response',
                'post_process': self._process_boolean_response
            },
            
            # Power Saving Parameters
            'sleep_mode': {
                'pattern': r'SLPDISCONNECT=(\d+)',
                'fields': ['mode_value'],
                'description': 'Sleep mode configuration response',
                'post_process': self._process_sleep_mode_response
            },
            'sleep_time': {
                'pattern': r'SLEEPT=(\d+)',
                'fields': ['time_minutes'],
                'description': 'Sleep time configuration response'
            },
            
            # Angle Parameters
            'angle_report': {
                'pattern': r'ANGLEVALUE=(\d+)-(\d+)',
                'fields': ['min_speed', 'angle_variation'],
                'description': 'Angle report configuration response',
                'post_process': self._process_angle_response
            },
            
            # Battery Alert Parameters
            'backup_battery_alert': {
                'pattern': r'BATALM:(OFF|(\d+),(\d+))',
                'fields': ['full_match', 'enabled', 'mode'],
                'description': 'Backup battery alert configuration response',
                'post_process': self._process_backup_battery_alert_response
            },
            'main_power_alert': {
                'pattern': r'POWERALM:(\d+),(\d+),(\d+),(\d+)',
                'fields': ['enabled', 'alert_type', 'detection_time', 'min_charge_time'],
                'description': 'Main power alert configuration response',
                'post_process': self._process_power_alert_response
            },
            
            # Vibration Sensor Parameters
            'vibration_sensitivity': {
                'pattern': r'VIBL=(\d+)',
                'fields': ['level'],
                'description': 'Vibration sensitivity configuration response'
            },
            
            # Jammer Detection Parameters
            'jammer_detection': {
                'pattern': r'JAMMER:(ON|OFF|\d+)(?:,(\d+))?',
                'fields': ['enabled', 'mode'],
                'description': 'Jammer detection configuration response',
                'post_process': self._process_jammer_detection_response
            },
            'jammer_relay_action': {
                'pattern': r'JAMRELAY:(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)',
                'fields': ['enabled', 'output_operation', 'confirmation_time', 'speed_limit', 'param_d', 'param_e', 'param_f'],
                'description': 'Jammer relay action configuration response',
                'post_process': self._process_jammer_relay_response
            },
            
            # Miscellaneous Parameters
            'odometer': {
                'pattern': r'MILEAGE=(\d+)',
                'fields': ['value_meters'],
                'description': 'Odometer configuration response'
            },
            'hourmeter': {
                'pattern': r'ACCONT:(\d+)',
                'fields': ['value_minutes'],
                'description': 'Hourmeter configuration response'
            },
            
            # Movement Alert Parameters
            'moving': {
                'pattern': r'MOVING:(OFF|ON,(\d+),(\d+))',
                'fields': ['full_match', 'radius', 'notification_mode'],
                'description': 'Movement alert configuration response',
                'post_process': self._process_moving_alert_response
            },
            'moving_alert': {
                'pattern': r'MOVING:(OFF|ON,(\d+),(\d+))',
                'fields': ['full_match', 'radius', 'notification_mode'],
                'description': 'Movement alert configuration response',
                'post_process': self._process_moving_alert_response
            },
            
            # Device Information Patterns
            'device_imei': {
                'pattern': r'IMEI[=:]\s*(\d+)',
                'fields': ['imei'],
                'description': 'Device IMEI response'
            },
            'device_iccid': {
                'pattern': r'ICCID[=:]\s*(\d+)',
                'fields': ['iccid'],
                'description': 'Device ICCID response'
            },
            'device_version': {
                'pattern': r'(.+)',
                'fields': ['version'],
                'description': 'Device version response'
            },
            'device_status': {
                'pattern': r'(.+)',
                'fields': ['status'],
                'description': 'Device status response',
                'post_process': self._process_status_response
            }
        }

    def _init_value_mappings(self) -> None:
        """Initialize value mappings for converting numeric responses to human-readable values."""
        self.value_mappings = {
            'protocol': {
                0: 'GT06 (0x60)',
                1: 'CRX3 (0x22)',
                2: 'CRX (0x12)'
            },
            'tcp_ack': {
                0: 'Disabled',
                1: 'Enabled'
            },
            'sleep_mode': {
                0: 'Desabilitado (Disabled)',
                1: 'Sleep (Habilitado)',
                2: 'Deep Sleep (Ultra-baixo)'
            },
            'alert_type': {
                0: 'Apenas GPRS',
                1: 'GPRS+SMS'
            },
            'jammer_output_operation': {
                0: 'Sem Ação',
                1: 'Ativar e Manter',
                2: 'Ativar e Desativar com Jammer'
            },
            'ignition_mode': {
                ('1', '0'): 'Física (Physical)',
                ('0', '0'): 'Virtual por acelerômetro (Virtual by accelerometer)',
                ('1', '1'): 'Virtual por bateria (Virtual by battery)'
            },
            'boolean': {
                0: False,
                1: True
            }
        }

    def parse_response(self, parameter_name: str, raw_response: str, command: str = '') -> ParsedResponse:
        """
        Parse a device response for a specific parameter.
        
        Args:
            parameter_name: Name of the parameter being parsed
            raw_response: Raw response string from the device
            command: Original command that generated this response
            
        Returns:
            ParsedResponse object with parsing results
        """
        try:
            # Clean the response
            cleaned_response = self._clean_response(raw_response)
            
            # Get the response pattern for this parameter
            pattern_config = self.response_patterns.get(parameter_name)
            if not pattern_config:
                return self._create_error_response(
                    parameter_name, raw_response, command,
                    f"No parsing pattern defined for parameter '{parameter_name}'"
                )
            
            # Parse the response
            parsed_values = self._parse_with_pattern(parameter_name, cleaned_response, pattern_config)
            
            if parsed_values is None:
                return self._create_error_response(
                    parameter_name, raw_response, command,
                    f"Response does not match expected pattern for '{parameter_name}'"
                )
            
            return ParsedResponse(
                parameter_name=parameter_name,
                command=command,
                success=True,
                parsed_values=parsed_values,
                raw_response=raw_response,
                error_message=None,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing response for {parameter_name}: {str(e)}")
            return self._create_error_response(
                parameter_name, raw_response, command,
                f"Parsing error: {str(e)}"
            )

    def _clean_response(self, raw_response: str) -> str:
        """
        Clean the raw response by removing common prefixes and suffixes.
        
        Args:
            raw_response: Raw response from device
            
        Returns:
            Cleaned response string
        """
        if not raw_response:
            return ""
        
        # Remove common prefixes and suffixes
        cleaned = raw_response.strip()
        
        # Remove ATSMS: prefix if present
        if cleaned.startswith('ATSMS:'):
            cleaned = cleaned[6:]
        
        # Remove OK suffix if present
        if cleaned.endswith(' OK'):
            cleaned = cleaned[:-3]
        
        # Remove trailing # if present
        if cleaned.endswith('#'):
            cleaned = cleaned[:-1]
        
        return cleaned.strip()

    def _parse_with_pattern(self, parameter_name: str, response: str, pattern_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse response using the specified pattern configuration.
        
        Args:
            parameter_name: Name of the parameter
            response: Cleaned response string
            pattern_config: Pattern configuration dictionary
            
        Returns:
            Dictionary of parsed values or None if parsing failed
        """
        # Handle complex multi-pattern parameters (like ignition_type)
        if 'patterns' in pattern_config:
            return self._parse_multi_pattern_response(parameter_name, response, pattern_config)
        
        # Handle single pattern parameters
        pattern = pattern_config['pattern']
        fields = pattern_config['fields']
        
        match = re.search(pattern, response, re.IGNORECASE)
        if not match:
            return None
        
        # Extract values from regex groups
        groups = match.groups()
        parsed_values = {}
        
        # Standard pattern matching - map all groups to fields
        for i, field in enumerate(fields):
            if i < len(groups):
                parsed_values[field] = groups[i]
        
        # Apply post-processing if defined
        if 'post_process' in pattern_config:
            parsed_values = pattern_config['post_process'](parsed_values, response)
        
        return parsed_values

    def _parse_multi_pattern_response(self, parameter_name: str, response: str, pattern_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse response that requires multiple patterns (like ignition configuration).
        
        Args:
            parameter_name: Name of the parameter
            response: Response string (may contain multiple lines)
            pattern_config: Pattern configuration with multiple patterns
            
        Returns:
            Dictionary of parsed values or None if parsing failed
        """
        patterns = pattern_config['patterns']
        fields = pattern_config['fields']
        parsed_values = {}
        
        # Split response into lines for multi-line responses
        response_lines = response.split('\n')
        response_text = ' '.join(response_lines)
        
        # Try to match each pattern
        for pattern_name, pattern in patterns.items():
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                pattern_fields = fields.get(pattern_name, [])
                
                for i, field in enumerate(pattern_fields):
                    if i < len(groups):
                        parsed_values[f"{pattern_name}_{field}"] = groups[i]
        
        # Apply post-processing if defined
        if 'post_process' in pattern_config:
            parsed_values = pattern_config['post_process'](parsed_values, response)
        
        return parsed_values if parsed_values else None

    def _create_error_response(self, parameter_name: str, raw_response: str, command: str, error_message: str) -> ParsedResponse:
        """
        Create an error response object.
        
        Args:
            parameter_name: Name of the parameter
            raw_response: Raw response from device
            command: Original command
            error_message: Error description
            
        Returns:
            ParsedResponse object indicating failure
        """
        return ParsedResponse(
            parameter_name=parameter_name,
            command=command,
            success=False,
            parsed_values={},
            raw_response=raw_response,
            error_message=error_message,
            timestamp=datetime.now()
        )

    # Post-processing methods for specific parameter types
    
    def _process_server_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process server configuration response."""
        if 'type' in values:
            # Convert type to human-readable format
            server_type = int(values['type'])
            values['address_type'] = 'IP Address' if server_type == 0 else 'Domain'
        
        if 'port' in values:
            values['port'] = int(values['port'])
        
        return values

    def _process_timer_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process timer configuration response."""
        # Convert string values to integers
        for key in ['moving_time', 'stopped_time']:
            if key in values and values[key]:
                values[key] = int(values[key])
        
        return values

    def _process_hbt_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process heartbeat configuration response."""
        # Convert string values to integers
        for key in ['moving_heartbeat', 'stopped_heartbeat']:
            if key in values and values[key]:
                values[key] = int(values[key])
        
        return values

    def _process_protocol_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process protocol selection response."""
        if 'protocol_value' in values:
            protocol_num = int(values['protocol_value'])
            values['protocol'] = self.value_mappings['protocol'].get(protocol_num, f'Unknown ({protocol_num})')
            values['protocol_value'] = protocol_num
        
        return values

    def _process_tcp_ack_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process TCP ACK configuration response."""
        if 'ack_value' in values:
            ack_num = int(values['ack_value'])
            values['tcp_ack'] = self.value_mappings['tcp_ack'].get(ack_num, f'Unknown ({ack_num})')
            values['ack_value'] = ack_num
        
        return values

    def _process_ignition_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process ignition configuration response."""
        # Extract ACCLINE and ACC_CFG values
        accline = values.get('accline_accline_value', '0')
        cfg_type = values.get('acc_cfg_cfg_type', '0')
        
        # Determine ignition mode
        mode_key = (accline, cfg_type)
        values['ignition_mode'] = self.value_mappings['ignition_mode'].get(mode_key, 'Unknown')
        
        # Process voltage values if present
        if 'acc_cfg_on_voltage' in values:
            values['on_voltage'] = int(values['acc_cfg_on_voltage'])
        if 'acc_cfg_off_voltage' in values:
            values['off_voltage'] = int(values['acc_cfg_off_voltage'])
        
        return values

    def _process_speed_alert_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process speed alert configuration response."""
        # Handle OFF case
        if 'full_match' in values and values['full_match'] == 'OFF':
            values['enabled'] = False
            values['detection_time'] = 0
            values['speed_limit'] = 0
            values['alert_type'] = 0
            values['alert_type_text'] = 'Apenas GPRS'
            # Remove the full_match field as it's not needed
            del values['full_match']
            return values
        
        # Handle numeric format case
        # Convert numeric values (skip None values from regex groups)
        for key in ['enabled', 'detection_time', 'speed_limit', 'alert_type']:
            if key in values and values[key] is not None:
                values[key] = int(values[key])
        
        # Convert enabled to boolean
        if 'enabled' in values:
            values['enabled'] = bool(values['enabled'])
        
        # Convert alert type to human-readable
        if 'alert_type' in values and values['alert_type'] is not None:
            alert_num = values['alert_type']
            values['alert_type_text'] = self.value_mappings['alert_type'].get(alert_num, f'Unknown ({alert_num})')
        
        # Remove the full_match field as it's not needed
        if 'full_match' in values:
            del values['full_match']
        
        return values

    def _process_backup_battery_alert_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process backup battery alert configuration response."""
        # Handle OFF case
        if 'full_match' in values and values['full_match'] == 'OFF':
            values['enabled'] = False
            values['mode'] = 0
            del values['full_match']
            return values
        
        # Handle numeric format case
        if 'enabled' in values and values['enabled'] is not None:
            values['enabled'] = bool(int(values['enabled']))
        
        if 'mode' in values and values['mode'] is not None:
            values['mode'] = int(values['mode'])
        
        if 'full_match' in values:
            del values['full_match']
            
        return values

    def _process_boolean_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process boolean configuration responses."""
        for key, value in values.items():
            if key == 'enabled' or key.endswith('_enabled'):
                values[key] = bool(int(value))
        
        return values

    def _process_sleep_mode_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process sleep mode configuration response."""
        if 'mode_value' in values:
            mode_num = int(values['mode_value'])
            values['sleep_mode'] = self.value_mappings['sleep_mode'].get(mode_num, f'Unknown ({mode_num})')
            values['mode_value'] = mode_num
        
        return values

    def _process_angle_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process angle report configuration response."""
        # Convert to integers
        for key in ['min_speed', 'angle_variation']:
            if key in values:
                values[key] = int(values[key])
        
        # Determine if angle reporting is enabled (non-zero values indicate enabled)
        min_speed = values.get('min_speed', 0)
        angle_var = values.get('angle_variation', 0)
        values['enabled'] = min_speed > 0 and angle_var > 0
        
        return values

    def _process_power_alert_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process power alert configuration response."""
        # Convert numeric values
        for key in ['enabled', 'alert_type', 'detection_time', 'min_charge_time']:
            if key in values:
                values[key] = int(values[key])
        
        # Convert alert type to human-readable
        if 'alert_type' in values:
            alert_num = values['alert_type']
            values['alert_type_text'] = self.value_mappings['alert_type'].get(alert_num, f'Unknown ({alert_num})')
        
        # Convert enabled to boolean
        if 'enabled' in values:
            values['enabled'] = bool(values['enabled'])
        
        return values

    def _process_jammer_detection_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process jammer detection configuration response."""
        # Handle ON/OFF or numeric format for enabled status
        if 'enabled' in values:
            status = values['enabled']
            if status == 'ON':
                values['enabled'] = True
            elif status == 'OFF':
                values['enabled'] = False
            else:
                # Numeric value - 1 means enabled, 0 means disabled
                values['enabled'] = bool(int(status))
        
        # Handle optional mode parameter
        if 'mode' in values:
            mode = values['mode']
            if mode is not None:
                values['mode'] = int(mode)
        
        return values

    def _process_jammer_relay_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process jammer relay action configuration response."""
        # Convert numeric values
        for key in ['enabled', 'output_operation', 'confirmation_time', 'speed_limit']:
            if key in values:
                values[key] = int(values[key])
        
        # Convert output operation to human-readable
        if 'output_operation' in values:
            op_num = values['output_operation']
            values['output_operation_text'] = self.value_mappings['jammer_output_operation'].get(op_num, f'Unknown ({op_num})')
        
        # Convert enabled to boolean
        if 'enabled' in values:
            values['enabled'] = bool(values['enabled'])
        
        return values

    def _process_moving_alert_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process movement alert configuration response."""
        # Debug log the incoming values
        self.logger.debug(f"Processing moving alert response - raw values: {values}")
        
        # Handle OFF case
        if 'full_match' in values and values['full_match'] == 'OFF':
            result = {
                'enabled': False,
                'radius': 1000,  # Default to 1000m when disabled
                'notification_mode': 0,
                'alert_type': 'Apenas GPRS'  # Match the UI field name
            }
            self.logger.debug(f"Processed OFF case - result: {result}")
            return result
        
        # Handle numeric format case
        try:
            # Convert radius to integer
            radius = None
            if 'radius' in values and values['radius'] is not None:
                radius = int(values['radius'])
            
            # Convert notification mode to integer
            notification_mode = 0
            if 'notification_mode' in values and values['notification_mode'] is not None:
                notification_mode = int(values['notification_mode'])
            
            # Build result with UI-matching field names
            result = {
                'enabled': True,
                'radius': radius if radius is not None else 1000,  # Default to 1000m
                'notification_mode': notification_mode,
                'alert_type': 'SMS+GPRS' if notification_mode == 1 else 'Apenas GPRS'  # Match the UI field name
            }
            self.logger.debug(f"Processed ON case - result: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process moving alert response: {e}")
            # Return safe defaults on error
            return {
                'enabled': False,
                'radius': 1000,
                'notification_mode': 0,
                'alert_type': 'Apenas GPRS'
            }

    def _process_status_response(self, values: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Process device status response (complex multi-line format)."""
        if 'status' in values:
            status_text = values['status']
            # Parse key:value pairs from status response
            status_dict = {}
            
            # Split by common delimiters and extract key:value pairs
            lines = status_text.replace(',', '\n').replace(';', '\n').split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    status_dict[key.strip()] = value.strip()
            
            values['status_details'] = status_dict
        
        return values

    def validate_response_format(self, parameter_name: str, response: str) -> bool:
        """
        Validate that a response matches the expected format for a parameter.
        
        Args:
            parameter_name: Name of the parameter
            response: Response string to validate
            
        Returns:
            True if response format is valid, False otherwise
        """
        pattern_config = self.response_patterns.get(parameter_name)
        if not pattern_config:
            return False
        
        cleaned_response = self._clean_response(response)
        
        if 'patterns' in pattern_config:
            # Multi-pattern validation
            patterns = pattern_config['patterns']
            return any(re.search(pattern, cleaned_response, re.IGNORECASE) for pattern in patterns.values())
        else:
            # Single pattern validation
            pattern = pattern_config['pattern']
            return bool(re.search(pattern, cleaned_response, re.IGNORECASE))

    def get_response_pattern(self, parameter_name: str) -> Optional[str]:
        """
        Get the response pattern for a parameter.
        
        Args:
            parameter_name: Name of the parameter
            
        Returns:
            Response pattern string or None if not found
        """
        pattern_config = self.response_patterns.get(parameter_name)
        if not pattern_config:
            return None
        
        if 'patterns' in pattern_config:
            # Return all patterns for multi-pattern parameters
            return str(pattern_config['patterns'])
        else:
            return pattern_config['pattern']

    def get_supported_parameters(self) -> List[str]:
        """
        Get list of all supported parameter names.
        
        Returns:
            List of parameter names that can be parsed
        """
        return list(self.response_patterns.keys())

    def create_parse_error(self, parameter_name: str, response: str, error_message: str) -> ParseError:
        """
        Create a detailed parse error object.
        
        Args:
            parameter_name: Name of the parameter
            response: Raw response that failed to parse
            error_message: Description of the error
            
        Returns:
            ParseError object with error details
        """
        expected_pattern = self.get_response_pattern(parameter_name) or "Unknown"
        
        return ParseError(
            parameter_name=parameter_name,
            raw_response=response,
            expected_pattern=expected_pattern,
            error_type="PARSE_ERROR",
            error_message=error_message,
            timestamp=datetime.now()
        )

    def batch_parse_responses(self, responses: Dict[str, str]) -> Dict[str, ParsedResponse]:
        """
        Parse multiple parameter responses in batch.
        
        Args:
            responses: Dictionary mapping parameter names to response strings
            
        Returns:
            Dictionary mapping parameter names to ParsedResponse objects
        """
        results = {}
        
        for parameter_name, response in responses.items():
            results[parameter_name] = self.parse_response(parameter_name, response)
        
        return results

    def get_parsing_statistics(self, parsed_responses: List[ParsedResponse]) -> Dict[str, Any]:
        """
        Generate statistics from a list of parsed responses.
        
        Args:
            parsed_responses: List of ParsedResponse objects
            
        Returns:
            Dictionary with parsing statistics
        """
        total_responses = len(parsed_responses)
        successful_parses = sum(1 for r in parsed_responses if r.success)
        failed_parses = total_responses - successful_parses
        
        # Group failures by error type
        error_types = {}
        for response in parsed_responses:
            if not response.success and response.error_message:
                error_type = response.error_message.split(':')[0]
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            'total_responses': total_responses,
            'successful_parses': successful_parses,
            'failed_parses': failed_parses,
            'success_rate': (successful_parses / total_responses * 100) if total_responses > 0 else 0,
            'error_types': error_types,
            'parameters_parsed': [r.parameter_name for r in parsed_responses if r.success],
            'parameters_failed': [r.parameter_name for r in parsed_responses if not r.success]
        }