"""
ValidationService - Comprehensive parameter validation with localized error messages.

This service provides centralized validation for all LT32Pro device parameters,
including range checking for numeric inputs, format validation for text inputs,
and connection state validation.
"""

import re
from dataclasses import dataclass
from typing import Optional, Any, Dict, List
from services.i18n_service import I18nService


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    error_message: str = ""
    error_code: str = ""
    suggested_value: Optional[str] = None


class ValidationService:
    """Handles comprehensive parameter validation with localized error messages."""
    
    def __init__(self, i18n_service: I18nService):
        self.i18n = i18n_service
        self._init_validation_rules()
    
    def _init_validation_rules(self):
        """Initialize validation rules for all parameter types."""
        self.validation_rules = {
            # Numeric parameters with ranges
            'vibration': {
                'type': 'numeric',
                'min': 0,
                'max': 255,
                'integer': True
            },
            'sensitivity': {
                'type': 'numeric',
                'min': 1,
                'max': 10,
                'integer': True
            },
            'timer_ign_on': {
                'type': 'numeric',
                'min': 1,
                'max': 65500,
                'integer': True
            },
            'timer_ign_off': {
                'type': 'numeric',
                'min': 1,
                'max': 65500,
                'integer': True
            },
            'heartbeat_ign_on': {
                'type': 'numeric',
                'min': 60,
                'max': 300,
                'integer': True
            },
            'heartbeat_ign_off': {
                'type': 'numeric',
                'min': 60,
                'max': 300,
                'integer': True
            },
            'speed_limit': {
                'type': 'numeric',
                'min': 1,
                'max': 255,
                'integer': True
            },
            'speed_time': {
                'type': 'numeric',
                'min': 5,
                'max': 600,
                'integer': True
            },
            'angle_speed': {
                'type': 'numeric',
                'min': 1,
                'max': 20,
                'integer': True
            },
            'angle_value': {
                'type': 'numeric',
                'min': 5,
                'max': 90,
                'integer': True
            },
            'blind_speed': {
                'type': 'numeric',
                'min': 0,
                'max': 20,
                'integer': True
            },
            'defense_time': {
                'type': 'numeric',
                'min': 1,
                'max': 60,
                'integer': True
            },
            'moving_radius': {
                'type': 'numeric',
                'min': 100,
                'max': 1000,
                'integer': True
            },
            'sleep_time': {
                'type': 'numeric',
                'min': 1,
                'max': 1440,
                'integer': True
            },
            'jammer_time': {
                'type': 'numeric',
                'min': 1,
                'max': 60,
                'integer': True
            },
            'jammer_signal': {
                'type': 'numeric',
                'min': 1,
                'max': 100,
                'integer': True
            },
            'jammer_freq': {
                'type': 'numeric',
                'min': 1,
                'max': 10,
                'integer': True
            },
            'acc_on_voltage': {
                'type': 'numeric',
                'min': 6,
                'max': 60,
                'integer': True
            },
            'acc_off_voltage': {
                'type': 'numeric',
                'min': 6,
                'max': 60,
                'integer': True
            },
            'timezone_hours': {
                'type': 'numeric',
                'min': 0,
                'max': 12,
                'integer': True
            },
            'timezone_minutes': {
                'type': 'numeric',
                'min': 0,
                'max': 59,
                'integer': True
            },
            
            # Text parameters with format validation
            'apn_server': {
                'type': 'text',
                'max_length': 50,
                'required': True,
                'pattern': r'^((?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))$'
            },
            'apn_user': {
                'type': 'text',
                'max_length': 30,
                'required': False
            },
            'apn_password': {
                'type': 'text',
                'max_length': 30,
                'required': False
            },
            'server_ip': {
                'type': 'ip_address',
                'required': True
            },
            'server_domain': {
                'type': 'domain',
                'max_length': 50,
                'required': True
            },
            'server_port': {
                'type': 'numeric',
                'min': 1,
                'max': 65535,
                'integer': True
            },
            'phone_number': {
                'type': 'phone',
                'max_length': 15,
                'required': True
            },
            
            # Dropdown parameters with allowed values
            'heartbeat_interval': {
                'type': 'dropdown',
                'allowed_values': ['30s', '1min', '5min', '10min', '30min', '1hr', '2hr', '6hr', '12hr', '24hr']
            },
            'curve_sensor': {
                'type': 'dropdown',
                'allowed_values': ['Enabled', 'Disabled', 'Auto']
            },
            'protocol_type': {
                'type': 'dropdown',
                'allowed_values': ['TCP', 'UDP']
            },
            'network_type': {
                'type': 'dropdown',
                'allowed_values': ['AUTO', '4G', '2G']
            },
            'sleep_mode': {
                'type': 'dropdown',
                'allowed_values': ['Disabled', 'Sleep', 'Deep Sleep']
            },
            'alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'gt06_protocol': {
                'type': 'dropdown',
                'allowed_values': ['GT06', 'CRX3', 'CRX']
            },
            'volte_switch': {
                'type': 'dropdown',
                'allowed_values': ['2G', '4G']
            },
            'relay_state': {
                'type': 'dropdown',
                'allowed_values': ['OFF', 'ON']
            },
            
            # Radio button parameters
            'lock_type': {
                'type': 'radio',
                'allowed_values': ['PIN', 'Card']
            },
            'ignition_type': {
                'type': 'radio',
                'allowed_values': ['Digital', 'Analog']
            },
            'transmission_mode': {
                'type': 'radio',
                'allowed_values': ['TCP', 'UDP']
            },
            'timezone_direction': {
                'type': 'radio',
                'allowed_values': ['E', 'W']
            },
            
            # Additional numeric parameters for comprehensive coverage
            'vibration_window': {
                'type': 'numeric',
                'min': 1,
                'max': 60,
                'integer': True
            },
            'vibration_threshold': {
                'type': 'numeric',
                'min': 1,
                'max': 100,
                'integer': True
            },
            'power_alert_t1': {
                'type': 'numeric',
                'min': 1,
                'max': 60,
                'integer': True
            },
            'power_alert_t2': {
                'type': 'numeric',
                'min': 1,
                'max': 60,
                'integer': True
            },
            'sos_phone1': {
                'type': 'phone',
                'max_length': 15,
                'required': False
            },
            'sos_phone2': {
                'type': 'phone',
                'max_length': 15,
                'required': False
            },
            'sos_phone3': {
                'type': 'phone',
                'max_length': 15,
                'required': False
            },
            'center_phone1': {
                'type': 'phone',
                'max_length': 15,
                'required': False
            },
            'center_phone2': {
                'type': 'phone',
                'max_length': 15,
                'required': False
            },
            'center_phone3': {
                'type': 'phone',
                'max_length': 15,
                'required': False
            },
            'password': {
                'type': 'text',
                'min_length': 4,
                'max_length': 20,
                'required': False
            },
            
            # Additional dropdown parameters
            'power_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'battery_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'movement_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'acc_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'acc_off_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'jammer_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'speed_alert_type': {
                'type': 'dropdown',
                'allowed_values': ['GPRS', 'SMS+GPRS']
            },
            'gps_source_type': {
                'type': 'dropdown',
                'allowed_values': ['Disabled', 'Enabled']
            },
            'parameter_lock_state': {
                'type': 'dropdown',
                'allowed_values': ['Unlock', 'Lock']
            },
            
            # Additional parameters from design document
            'firmware_version': {
                'type': 'text',
                'max_length': 20,
                'required': False
            },
            'signal_strength': {
                'type': 'numeric',
                'min': 0,
                'max': 100,
                'integer': True
            },
            'device_status': {
                'type': 'text',
                'max_length': 50,
                'required': False
            },
            'imei': {
                'type': 'text',
                'min_length': 15,
                'max_length': 15,
                'required': False,
                'pattern': r'^\d{15}$'
            },
            'iccid': {
                'type': 'text',
                'min_length': 19,
                'max_length': 20,
                'required': False,
                'pattern': r'^\d{19,20}$'
            },
            'imsi': {
                'type': 'text',
                'min_length': 15,
                'max_length': 15,
                'required': False,
                'pattern': r'^\d{15}$'
            }
        }
    
    def validate_parameter(self, param_name: str, value: Any) -> ValidationResult:
        """
        Validate a parameter value according to its defined rules.
        
        Args:
            param_name: Name of the parameter to validate
            value: Value to validate
            
        Returns:
            ValidationResult with validation status and error details
        """
        if param_name not in self.validation_rules:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_unknown_parameter', 'Unknown parameter: {param_name}').format(param_name=param_name),
                error_code='UNKNOWN_PARAMETER'
            )
        
        rules = self.validation_rules[param_name]
        param_type = rules['type']
        
        # Handle empty values
        if value is None or (isinstance(value, str) and value.strip() == ''):
            if rules.get('required', False):
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_required_field', '{param_name} is required and cannot be empty').format(param_name=param_name),
                    error_code='REQUIRED_FIELD'
                )
            else:
                return ValidationResult(is_valid=True)
        
        # Type-specific validation
        if param_type == 'numeric':
            return self._validate_numeric(param_name, value, rules)
        elif param_type == 'text':
            return self._validate_text(param_name, value, rules)
        elif param_type == 'ip_address':
            return self._validate_ip_address(param_name, value)
        elif param_type == 'domain':
            return self._validate_domain(param_name, value, rules)
        elif param_type == 'phone':
            return self._validate_phone(param_name, value, rules)
        elif param_type == 'dropdown':
            return self._validate_dropdown(param_name, value, rules)
        elif param_type == 'radio':
            return self._validate_radio(param_name, value, rules)
        
        return ValidationResult(is_valid=True)
    
    def _validate_numeric(self, param_name: str, value: Any, rules: Dict) -> ValidationResult:
        """Validate numeric parameters with range checking."""
        try:
            if isinstance(value, str):
                if rules.get('integer', False):
                    num_value = int(value)
                else:
                    num_value = float(value)
            else:
                num_value = value
                
            # Check if integer is required
            if rules.get('integer', False) and not isinstance(num_value, int):
                if isinstance(num_value, float) and not num_value.is_integer():
                    return ValidationResult(
                        is_valid=False,
                        error_message=self.i18n.get('validation_integer_required', '{param_name} must be an integer value').format(param_name=param_name),
                        error_code='INTEGER_REQUIRED'
                    )
                num_value = int(num_value)
            
            # Check range
            min_val = rules.get('min')
            max_val = rules.get('max')
            
            if min_val is not None and num_value < min_val:
                # Use more specific range error message if both min and max are specified
                if max_val is not None:
                    return ValidationResult(
                        is_valid=False,
                        error_message=self.i18n.get('validation_range_error', '{param_name} must be between {min_val} and {max_val}').format(
                            param_name=param_name, min_val=min_val, max_val=max_val
                        ),
                        error_code='RANGE_ERROR',
                        suggested_value=str(min_val)
                    )
                else:
                    return ValidationResult(
                        is_valid=False,
                        error_message=self.i18n.get('validation_min_value', '{param_name} must be at least {min_val}').format(
                            param_name=param_name, min_val=min_val
                        ),
                        error_code='MIN_VALUE',
                        suggested_value=str(min_val)
                    )
            
            if max_val is not None and num_value > max_val:
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_max_value', '{param_name} must be at most {max_val}').format(
                        param_name=param_name, max_val=max_val
                    ),
                    error_code='MAX_VALUE',
                    suggested_value=str(max_val)
                )
            
            # Check allowed values (for specific numeric constraints)
            allowed_values = rules.get('allowed_values')
            if allowed_values and num_value not in allowed_values:
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_not_in_allowed_values', '{param_name} must be one of: {allowed_values}').format(
                        param_name=param_name, 
                        allowed_values=", ".join(map(str, allowed_values))
                    ),
                    error_code='NOT_IN_ALLOWED_VALUES'
                )
            
            return ValidationResult(is_valid=True)
            
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_numeric_required', '{param_name} must be a numeric value').format(param_name=param_name),
                error_code='NUMERIC_REQUIRED'
            )
    
    def _validate_text(self, param_name: str, value: Any, rules: Dict) -> ValidationResult:
        """Validate text parameters with length and pattern checking."""
        if not isinstance(value, str):
            value = str(value)
        
        # Check minimum length
        min_length = rules.get('min_length')
        if min_length and len(value) < min_length:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_min_length', '{param_name} must be at least {min_length} characters').format(
                    param_name=param_name, 
                    min_length=min_length
                ),
                error_code='MIN_LENGTH'
            )
        
        # Check maximum length
        max_length = rules.get('max_length')
        if max_length and len(value) > max_length:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_max_length', '{param_name} must be at most {max_length} characters').format(
                    param_name=param_name, 
                    max_length=max_length
                ),
                error_code='MAX_LENGTH'
            )
        
        # Check pattern
        pattern = rules.get('pattern')
        if pattern and not re.match(pattern, value):
            # Use specific error messages for known patterns
            if param_name == 'imei':
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_invalid_imei', '{param_name} must be exactly 15 digits').format(param_name=param_name),
                    error_code='INVALID_IMEI'
                )
            elif param_name == 'iccid':
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_invalid_iccid', '{param_name} must be 19-20 digits').format(param_name=param_name),
                    error_code='INVALID_ICCID'
                )
            elif param_name == 'imsi':
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_invalid_imsi', '{param_name} must be exactly 15 digits').format(param_name=param_name),
                    error_code='INVALID_IMSI'
                )
            elif param_name == 'apn_server':
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_invalid_apn', '{param_name} must be a valid hostname or IP address').format(param_name=param_name),
                    error_code='INVALID_APN'
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_invalid_format', '{param_name} has an invalid format').format(param_name=param_name),
                    error_code='INVALID_FORMAT'
                )
        
        return ValidationResult(is_valid=True)
    
    def _validate_ip_address(self, param_name: str, value: str) -> ValidationResult:
        """Validate IP address format."""
        ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        
        if not re.match(ip_pattern, value):
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_invalid_ip', '{param_name} must be a valid IP address (e.g. 192.168.1.1)').format(param_name=param_name),
                error_code='INVALID_IP'
            )
        
        return ValidationResult(is_valid=True)
    
    def _validate_domain(self, param_name: str, value: str, rules: Dict) -> ValidationResult:
        """Validate domain name format."""
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        
        if not re.match(domain_pattern, value):
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_invalid_domain', '{param_name} must be a valid domain name (e.g. example.com)').format(param_name=param_name),
                error_code='INVALID_DOMAIN'
            )
        
        max_length = rules.get('max_length', 253)
        if len(value) > max_length:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_max_length', '{param_name} must be at most {max_length} characters').format(
                    param_name=param_name, 
                    max_length=max_length
                ),
                error_code='MAX_LENGTH'
            )
        
        return ValidationResult(is_valid=True)
    
    def _validate_phone(self, param_name: str, value: str, rules: Dict) -> ValidationResult:
        """Validate phone number format."""
        # Remove common phone number separators
        clean_phone = re.sub(r'[\s\-\(\)\+]', '', value)
        
        # Check if it contains only digits
        if not clean_phone.isdigit():
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_invalid_phone', '{param_name} must contain only digits').format(param_name=param_name),
                error_code='INVALID_PHONE'
            )
        
        # Check length
        max_length = rules.get('max_length', 15)
        if len(clean_phone) > max_length:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_phone_too_long', '{param_name} must be at most {max_length} digits').format(
                    param_name=param_name,
                    max_length=max_length
                ),
                error_code='PHONE_TOO_LONG'
            )
        
        if len(clean_phone) < 7:  # Minimum reasonable phone number length
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_phone_too_short', '{param_name} must be at least 7 digits').format(param_name=param_name),
                error_code='PHONE_TOO_SHORT'
            )
        
        return ValidationResult(is_valid=True)
    
    def _validate_dropdown(self, param_name: str, value: str, rules: Dict) -> ValidationResult:
        """Validate dropdown selection."""
        allowed_values = rules.get('allowed_values', [])
        
        if value not in allowed_values:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_invalid_selection', '{param_name} must be one of: {allowed_values}').format(
                    param_name=param_name,
                    allowed_values=", ".join(allowed_values)
                ),
                error_code='INVALID_SELECTION'
            )
        
        return ValidationResult(is_valid=True)
    
    def _validate_radio(self, param_name: str, value: str, rules: Dict) -> ValidationResult:
        """Validate radio button selection."""
        return self._validate_dropdown(param_name, value, rules)
    
    def validate_connection_required(self, serial_service) -> ValidationResult:
        """
        Validate that device connection is available for operations that require it.
        
        Args:
            serial_service: SerialService instance to check connection status
            
        Returns:
            ValidationResult indicating if connection is available
        """
        if not hasattr(serial_service, 'is_connected') or not serial_service.is_connected:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_connection_required', 'Device connection is required for this operation'),
                error_code='CONNECTION_REQUIRED'
            )
        
        return ValidationResult(is_valid=True)
    
    def validate_profile_data(self, profile_data: Dict) -> ValidationResult:
        """
        Validate configuration profile data structure.
        
        Args:
            profile_data: Dictionary containing profile configuration
            
        Returns:
            ValidationResult indicating if profile data is valid
        """
        if not isinstance(profile_data, dict):
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_invalid_profile_format', 'Profile data must be a valid configuration object'),
                error_code='INVALID_PROFILE_FORMAT'
            )
        
        # Validate required sections
        required_sections = ['version']
        for section in required_sections:
            if section not in profile_data:
                return ValidationResult(
                    is_valid=False,
                    error_message=self.i18n.get('validation_missing_profile_section', 'Profile is missing required section: {section}').format(section=section),
                    error_code='MISSING_PROFILE_SECTION'
                )
        
        # Validate individual parameters in profile
        errors = []
        for section_name, section_data in profile_data.items():
            if section_name == 'version':
                continue
                
            if isinstance(section_data, dict):
                for param_name, param_value in section_data.items():
                    result = self.validate_parameter(param_name, param_value)
                    if not result.is_valid:
                        errors.append(f"{section_name}.{param_name}: {result.error_message}")
        
        if errors:
            return ValidationResult(
                is_valid=False,
                error_message=self.i18n.get('validation_profile_errors', 'Profile validation errors: {errors}').format(errors="; ".join(errors)),
                error_code='PROFILE_VALIDATION_ERRORS'
            )
        
        return ValidationResult(is_valid=True)
    
    def get_parameter_info(self, param_name: str) -> Optional[Dict]:
        """
        Get validation rules and information for a parameter.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            Dictionary with parameter validation rules or None if not found
        """
        return self.validation_rules.get(param_name)
    
    def get_all_parameters(self) -> List[str]:
        """
        Get list of all supported parameter names.
        
        Returns:
            List of parameter names
        """
        return list(self.validation_rules.keys())