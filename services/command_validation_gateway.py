"""
Command Validation Gateway - Pre-command validation service for LT32Pro device commands.

This service acts as a validation checkpoint that intercepts and validates all commands
before they are sent to the device. It specifically focuses on APN validation to prevent
malformed configurations from being transmitted.
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime

from services.validation_service import ValidationService, ValidationResult


@dataclass
class CommandValidationResult:
    """Result of command validation operation."""
    is_valid: bool
    command: str
    error_message: str = ""
    error_code: str = ""
    blocked_reason: str = ""
    extracted_parameters: Dict[str, str] = None
    validation_details: Dict[str, ValidationResult] = None
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.extracted_parameters is None:
            self.extracted_parameters = {}
        if self.validation_details is None:
            self.validation_details = {}
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class ValidationContext:
    """Context information for command validation."""
    command_type: str
    source: str  # 'ui', 'bulk', 'profile', 'manual'
    timestamp: datetime
    user_session_id: Optional[str] = None
    retry_count: int = 0


class CommandValidationGateway:
    """
    Gateway service that validates commands before transmission to the device.
    
    This service intercepts all commands and performs validation checks,
    particularly focusing on APN configuration commands that have been
    problematic in the past.
    """
    
    def __init__(self, validation_service: ValidationService, i18n_service=None):
        """
        Initialize the command validation gateway.
        
        Args:
            validation_service: ValidationService instance for parameter validation
            i18n_service: Optional I18nService for localized error messages
        """
        self.validation_service = validation_service
        self.i18n = i18n_service
        self.logger = logging.getLogger(__name__)
        
        # Initialize command patterns for parameter extraction
        self._init_command_patterns()
        
        # Statistics tracking
        self.validation_stats = {
            'total_commands': 0,
            'blocked_commands': 0,
            'apn_validations': 0,
            'apn_blocks': 0,
            'last_reset': datetime.now()
        }
    
    def _init_command_patterns(self):
        """Initialize regex patterns for extracting parameters from commands."""
        self.command_patterns = {
            # APN command patterns - matches ATSMS:APN,server,user,password#
            'apn': {
                'pattern': r'^ATSMS:APN,([^,]*),([^,]*),([^#]*)#?$',
                'groups': ['apn_server', 'apn_user', 'apn_password'],
                'required_params': ['apn_server']
            },
            
            # Server command patterns - matches ATSMS:SERVER,type,address,port,protocol#
            'server': {
                'pattern': r'^ATSMS:SERVER,(\d+),([^,]+),(\d+),(\d+)#?$',
                'groups': ['server_type', 'server_address', 'server_port', 'server_protocol'],
                'required_params': ['server_address', 'server_port']
            },
            
            # Timer command patterns - matches ATSMS:TIMER,ign_on,ign_off#
            'timer': {
                'pattern': r'^ATSMS:TIMER,(\d+),(\d+)#?$',
                'groups': ['timer_ign_on', 'timer_ign_off'],
                'required_params': ['timer_ign_on', 'timer_ign_off']
            },
            
            # Heartbeat command patterns - matches ATSMS:HBT,ign_on,ign_off#
            'heartbeat': {
                'pattern': r'^ATSMS:HBT,(\d+),(\d+)#?$',
                'groups': ['heartbeat_ign_on', 'heartbeat_ign_off'],
                'required_params': ['heartbeat_ign_on', 'heartbeat_ign_off']
            },
            
            # SZCS parameter commands - matches ATSMS:SZCS#PARAM=value#
            'szcs': {
                'pattern': r'^ATSMS:SZCS#([A-Z0-9_]+)=([^#]+)#?$',
                'groups': ['parameter_name', 'parameter_value'],
                'required_params': ['parameter_name', 'parameter_value']
            }
        }
    
    def validate_command_before_send(self, command: str, context: Optional[ValidationContext] = None) -> CommandValidationResult:
        """
        Validate a command before sending it to the device.
        
        This is the main entry point for command validation. It extracts parameters
        from the command and validates them according to the defined rules.
        
        Args:
            command: The command string to validate
            context: Optional validation context with additional information
            
        Returns:
            CommandValidationResult with validation status and details
        """
        if context is None:
            context = ValidationContext(
                command_type='unknown',
                source='manual',
                timestamp=datetime.now()
            )
        
        # Update statistics
        self.validation_stats['total_commands'] += 1
        
        # Log the validation attempt
        self.logger.info(f"Validating command: {command[:50]}... (source: {context.source})")
        
        try:
            # Extract parameters from the command
            extracted_params = self.extract_parameters_from_command(command)
            
            if not extracted_params:
                # Command doesn't match known patterns - allow it through with warning
                self.logger.warning(f"Unknown command format: {command}")
                return CommandValidationResult(
                    is_valid=True,
                    command=command,
                    extracted_parameters={},
                    error_message="Unknown command format - validation skipped"
                )
            
            # Determine command type from extracted parameters
            command_type = self._determine_command_type(extracted_params, command)
            context.command_type = command_type
            
            # Validate extracted parameters
            validation_result = self._validate_extracted_parameters(extracted_params, context)
            
            # Log validation result
            if validation_result.is_valid:
                self.logger.info(f"Command validation passed: {command_type}")
            else:
                self.logger.warning(f"Command validation failed: {command_type} - {validation_result.error_message}")
                self.validation_stats['blocked_commands'] += 1
                
                # Track APN-specific blocks
                if command_type == 'apn':
                    self.validation_stats['apn_blocks'] += 1
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error during command validation: {str(e)}")
            return CommandValidationResult(
                is_valid=False,
                command=command,
                error_message=f"Validation error: {str(e)}",
                error_code="VALIDATION_ERROR",
                blocked_reason="Internal validation error occurred"
            )
    
    def extract_parameters_from_command(self, command: str) -> Dict[str, str]:
        """
        Extract parameter values from a device command string.
        
        Args:
            command: The command string to parse
            
        Returns:
            Dictionary of parameter names and values extracted from the command
        """
        extracted = {}
        
        # Try each command pattern to find a match
        for cmd_type, pattern_info in self.command_patterns.items():
            pattern = pattern_info['pattern']
            groups = pattern_info['groups']
            
            match = re.match(pattern, command.strip())
            if match:
                # Extract parameter values based on regex groups
                for i, group_name in enumerate(groups):
                    if i < len(match.groups()):
                        value = match.group(i + 1)
                        # Clean up the value (remove extra whitespace, handle empty strings)
                        cleaned_value = value.strip() if value else ""
                        extracted[group_name] = cleaned_value
                
                # Add command type information
                extracted['_command_type'] = cmd_type
                break
        
        return extracted
    
    def validate_apn_command_parameters(self, parameters: Dict[str, str]) -> CommandValidationResult:
        """
        Validate APN command parameters specifically.
        
        This method provides focused validation for APN commands, which have been
        the source of configuration issues in the past.
        
        Args:
            parameters: Dictionary of APN parameters to validate
            
        Returns:
            CommandValidationResult with APN-specific validation details
        """
        self.validation_stats['apn_validations'] += 1
        
        validation_details = {}
        all_valid = True
        error_messages = []
        suggestions = []
        
        # Validate APN server (required)
        if 'apn_server' in parameters:
            apn_value = parameters['apn_server']
            apn_result = self.validation_service.validate_parameter('apn_server', apn_value)
            validation_details['apn_server'] = apn_result
            
            if not apn_result.is_valid:
                all_valid = False
                error_messages.append(f"APN Server: {apn_result.error_message}")
            
            # Add specific suggestions for common APN issues (regardless of validation result)
            if '..' in apn_value:
                suggestions.append("Remove consecutive dots from APN server name")
            if apn_value.startswith('.') or apn_value.endswith('.'):
                suggestions.append("Remove leading or trailing dots from APN server name")
            if not re.match(r'^[a-zA-Z0-9.-]+$', apn_value):
                suggestions.append("APN server should only contain letters, numbers, dots, and hyphens")
            
            # Check for malformed domain patterns like "allcom.br.t.t.t"
            if re.search(r'\.[a-zA-Z]\.[a-zA-Z]\.', apn_value):
                suggestions.append("APN server appears to have malformed domain structure")
            
            # Check for single character domain parts (like .t.t.t)
            parts = apn_value.split('.')
            single_char_parts = [part for part in parts if len(part) == 1]
            if len(single_char_parts) > 1:
                suggestions.append("APN server has too many single-character domain parts - check for typos")
        
        # Validate APN user (optional)
        if 'apn_user' in parameters and parameters['apn_user']:
            user_result = self.validation_service.validate_parameter('apn_user', parameters['apn_user'])
            validation_details['apn_user'] = user_result
            
            if not user_result.is_valid:
                all_valid = False
                error_messages.append(f"APN User: {user_result.error_message}")
        
        # Validate APN password (optional)
        if 'apn_password' in parameters and parameters['apn_password']:
            password_result = self.validation_service.validate_parameter('apn_password', parameters['apn_password'])
            validation_details['apn_password'] = password_result
            
            if not password_result.is_valid:
                all_valid = False
                error_messages.append(f"APN Password: {password_result.error_message}")
        
        # Create the result
        result = CommandValidationResult(
            is_valid=all_valid,
            command=f"APN,{parameters.get('apn_server', '')},{parameters.get('apn_user', '')},{parameters.get('apn_password', '')}#",
            extracted_parameters=parameters,
            validation_details=validation_details,
            suggestions=suggestions
        )
        
        if not all_valid:
            result.error_message = "; ".join(error_messages)
            result.error_code = "APN_VALIDATION_FAILED"
            result.blocked_reason = "APN parameters failed validation checks"
        
        return result
    
    def _determine_command_type(self, extracted_params: Dict[str, str], command: str) -> str:
        """
        Determine the type of command based on extracted parameters.
        
        Args:
            extracted_params: Parameters extracted from the command
            command: Original command string
            
        Returns:
            String identifying the command type
        """
        if '_command_type' in extracted_params:
            return extracted_params['_command_type']
        
        # Fallback: determine from command string
        if 'APN,' in command:
            return 'apn'
        elif 'SERVER,' in command:
            return 'server'
        elif 'TIMER,' in command:
            return 'timer'
        elif 'HBT,' in command:
            return 'heartbeat'
        elif 'SZCS#' in command:
            return 'szcs'
        else:
            return 'unknown'
    
    def _validate_extracted_parameters(self, parameters: Dict[str, str], context: ValidationContext) -> CommandValidationResult:
        """
        Validate the extracted parameters based on their types.
        
        Args:
            parameters: Dictionary of extracted parameters
            context: Validation context
            
        Returns:
            CommandValidationResult with validation details
        """
        command_type = parameters.get('_command_type', 'unknown')
        
        # Handle APN commands specifically
        if command_type == 'apn':
            return self.validate_apn_command_parameters(parameters)
        
        # Handle other command types
        elif command_type == 'server':
            return self._validate_server_parameters(parameters)
        
        elif command_type in ['timer', 'heartbeat']:
            return self._validate_timing_parameters(parameters, command_type)
        
        elif command_type == 'szcs':
            return self._validate_szcs_parameters(parameters)
        
        else:
            # Unknown command type - allow through with warning
            return CommandValidationResult(
                is_valid=True,
                command=self._reconstruct_command(parameters),
                extracted_parameters=parameters,
                error_message="Unknown command type - validation skipped"
            )
    
    def _validate_server_parameters(self, parameters: Dict[str, str]) -> CommandValidationResult:
        """Validate server command parameters."""
        validation_details = {}
        all_valid = True
        error_messages = []
        
        # Validate server address
        if 'server_address' in parameters:
            addr_result = self.validation_service.validate_parameter('server_address', parameters['server_address'])
            validation_details['server_address'] = addr_result
            
            if not addr_result.is_valid:
                all_valid = False
                error_messages.append(f"Server Address: {addr_result.error_message}")
        
        # Validate server port
        if 'server_port' in parameters:
            try:
                port_value = int(parameters['server_port'])
                port_result = self.validation_service.validate_parameter('server_port', port_value)
                validation_details['server_port'] = port_result
                
                if not port_result.is_valid:
                    all_valid = False
                    error_messages.append(f"Server Port: {port_result.error_message}")
            except ValueError:
                all_valid = False
                error_messages.append("Server Port: Must be a valid number")
        
        result = CommandValidationResult(
            is_valid=all_valid,
            command=self._reconstruct_command(parameters),
            extracted_parameters=parameters,
            validation_details=validation_details
        )
        
        if not all_valid:
            result.error_message = "; ".join(error_messages)
            result.error_code = "SERVER_VALIDATION_FAILED"
            result.blocked_reason = "Server parameters failed validation checks"
        
        return result
    
    def _validate_timing_parameters(self, parameters: Dict[str, str], command_type: str) -> CommandValidationResult:
        """Validate timing command parameters (timer, heartbeat)."""
        validation_details = {}
        all_valid = True
        error_messages = []
        
        # Get the parameter names based on command type
        if command_type == 'timer':
            param_names = ['timer_ign_on', 'timer_ign_off']
        else:  # heartbeat
            param_names = ['heartbeat_ign_on', 'heartbeat_ign_off']
        
        for param_name in param_names:
            if param_name in parameters:
                try:
                    value = int(parameters[param_name])
                    result = self.validation_service.validate_parameter(param_name, value)
                    validation_details[param_name] = result
                    
                    if not result.is_valid:
                        all_valid = False
                        error_messages.append(f"{param_name}: {result.error_message}")
                except ValueError:
                    all_valid = False
                    error_messages.append(f"{param_name}: Must be a valid number")
        
        result = CommandValidationResult(
            is_valid=all_valid,
            command=self._reconstruct_command(parameters),
            extracted_parameters=parameters,
            validation_details=validation_details
        )
        
        if not all_valid:
            result.error_message = "; ".join(error_messages)
            result.error_code = f"{command_type.upper()}_VALIDATION_FAILED"
            result.blocked_reason = f"{command_type.title()} parameters failed validation checks"
        
        return result
    
    def _validate_szcs_parameters(self, parameters: Dict[str, str]) -> CommandValidationResult:
        """Validate SZCS command parameters."""
        validation_details = {}
        all_valid = True
        error_messages = []
        
        param_name = parameters.get('parameter_name', '')
        param_value = parameters.get('parameter_value', '')
        
        # Map SZCS parameter names to validation parameter names
        szcs_param_mapping = {
            'VIBL': 'vibration',
            'VIBCHK': 'vibration_window',
            'SENSITIVITY': 'sensitivity',
            'GT06SEL': 'gt06_protocol',
            'NETSELECT': 'network_select',
            'VOLTESWITCH': 'volte_switch',
            'SLPDISCONNECT': 'sleep_mode',
            'SLEEPT': 'sleep_time',
            'ACCLINE': 'ignition_type',
            'ANGLEVALUE': 'angle_reporting',
            'BLINDSPD': 'blind_speed',
            'CURVE': 'curve_sensor',
            'LOCKTYPE': 'lock_type'
        }
        
        validation_param = szcs_param_mapping.get(param_name)
        if validation_param:
            # Convert value to appropriate type if needed
            if validation_param in ['vibration', 'vibration_window', 'sensitivity', 'sleep_time', 'blind_speed']:
                try:
                    param_value = int(param_value)
                except ValueError:
                    all_valid = False
                    error_messages.append(f"{param_name}: Must be a valid number")
                    param_value = None
            
            if param_value is not None:
                result = self.validation_service.validate_parameter(validation_param, param_value)
                validation_details[validation_param] = result
                
                if not result.is_valid:
                    all_valid = False
                    error_messages.append(f"{param_name}: {result.error_message}")
        
        result = CommandValidationResult(
            is_valid=all_valid,
            command=self._reconstruct_command(parameters),
            extracted_parameters=parameters,
            validation_details=validation_details
        )
        
        if not all_valid:
            result.error_message = "; ".join(error_messages)
            result.error_code = "SZCS_VALIDATION_FAILED"
            result.blocked_reason = "SZCS parameters failed validation checks"
        
        return result
    
    def _reconstruct_command(self, parameters: Dict[str, str]) -> str:
        """
        Reconstruct the original command from extracted parameters.
        
        Args:
            parameters: Dictionary of extracted parameters
            
        Returns:
            Reconstructed command string
        """
        command_type = parameters.get('_command_type', 'unknown')
        
        if command_type == 'apn':
            server = parameters.get('apn_server', '')
            user = parameters.get('apn_user', '')
            password = parameters.get('apn_password', '')
            return f"ATSMS:APN,{server},{user},{password}#"
        
        elif command_type == 'server':
            server_type = parameters.get('server_type', '0')
            address = parameters.get('server_address', '')
            port = parameters.get('server_port', '')
            protocol = parameters.get('server_protocol', '0')
            return f"ATSMS:SERVER,{server_type},{address},{port},{protocol}#"
        
        elif command_type == 'timer':
            ign_on = parameters.get('timer_ign_on', '')
            ign_off = parameters.get('timer_ign_off', '')
            return f"ATSMS:TIMER,{ign_on},{ign_off}#"
        
        elif command_type == 'heartbeat':
            ign_on = parameters.get('heartbeat_ign_on', '')
            ign_off = parameters.get('heartbeat_ign_off', '')
            return f"ATSMS:HBT,{ign_on},{ign_off}#"
        
        elif command_type == 'szcs':
            param_name = parameters.get('parameter_name', '')
            param_value = parameters.get('parameter_value', '')
            return f"ATSMS:SZCS#{param_name}={param_value}#"
        
        else:
            return "UNKNOWN_COMMAND"
    
    def log_blocked_command(self, result: CommandValidationResult, context: ValidationContext):
        """
        Log detailed information about a blocked command.
        
        Args:
            result: The validation result for the blocked command
            context: Validation context with additional information
        """
        log_entry = {
            'timestamp': context.timestamp.isoformat(),
            'command': result.command,
            'source': context.source,
            'command_type': context.command_type,
            'blocked_reason': result.blocked_reason,
            'error_code': result.error_code,
            'error_message': result.error_message,
            'extracted_parameters': result.extracted_parameters,
            'validation_details': {
                param: {
                    'is_valid': details.is_valid,
                    'error_message': details.error_message,
                    'error_code': details.error_code
                }
                for param, details in result.validation_details.items()
            },
            'suggestions': result.suggestions,
            'retry_count': context.retry_count,
            'user_session_id': context.user_session_id
        }
        
        self.logger.error(f"BLOCKED COMMAND: {log_entry}")
        
        # Also log a human-readable summary
        self.logger.error(
            f"Command blocked - Type: {context.command_type}, "
            f"Source: {context.source}, "
            f"Reason: {result.blocked_reason}, "
            f"Command: {result.command[:100]}..."
        )
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """
        Get validation statistics for monitoring and debugging.
        
        Returns:
            Dictionary with validation statistics
        """
        stats = self.validation_stats.copy()
        stats['block_rate'] = (stats['blocked_commands'] / max(stats['total_commands'], 1)) * 100
        stats['apn_block_rate'] = (stats['apn_blocks'] / max(stats['apn_validations'], 1)) * 100
        stats['uptime_hours'] = (datetime.now() - stats['last_reset']).total_seconds() / 3600
        
        return stats
    
    def reset_statistics(self):
        """Reset validation statistics."""
        self.validation_stats = {
            'total_commands': 0,
            'blocked_commands': 0,
            'apn_validations': 0,
            'apn_blocks': 0,
            'last_reset': datetime.now()
        }
        
        self.logger.info("Validation statistics reset")
    
    def is_command_safe_to_send(self, command: str, context: Optional[ValidationContext] = None) -> bool:
        """
        Quick check if a command is safe to send without full validation details.
        
        Args:
            command: Command string to check
            context: Optional validation context
            
        Returns:
            True if command is safe to send, False otherwise
        """
        result = self.validate_command_before_send(command, context)
        return result.is_valid
    
    def get_command_suggestions(self, command: str) -> List[str]:
        """
        Get suggestions for fixing a command that failed validation.
        
        Args:
            command: Command string that failed validation
            
        Returns:
            List of suggestions for fixing the command
        """
        result = self.validate_command_before_send(command)
        suggestions = []
        
        # Collect suggestions from the validation result
        if result.suggestions:
            suggestions.extend(result.suggestions)
        
        # Add suggestions from individual parameter validation details
        if result.validation_details:
            for param_name, validation_result in result.validation_details.items():
                if hasattr(validation_result, 'suggested_value') and validation_result.suggested_value:
                    suggestions.append(f"Try using '{validation_result.suggested_value}' for {param_name}")
        
        return suggestions