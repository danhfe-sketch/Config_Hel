"""
LT32Pro Profile Validator

This module provides comprehensive validation and compatibility checking for LT32Pro profile files.
Requirements addressed: 2.1, 3.4, 5.7
"""

import configparser
import ipaddress
import os
import shutil
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    severity: ValidationSeverity
    section: str
    parameter: str
    message: str
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None


class LT32ProProfileValidator:
    """Comprehensive validator for LT32Pro profile files."""
    
    # Required sections and their mandatory parameters
    REQUIRED_SECTIONS = {
        'Profile_Info': ['profile_name', 'profile_version', 'created_date'],
        'APN_Configuration': ['apn_server']
    }
    
    # Optional sections and their parameters
    OPTIONAL_SECTIONS = {
        'Server_Configuration': ['server_ip', 'server_port', 'server_protocol'],
        'Timer_Settings': ['timer_ign_on', 'timer_ign_off', 'heartbeat_interval'],
        'Device_Parameters': ['vibration', 'sensitivity', 'device_imei', 'device_iccid', 'GT06SEL', 'POSBYACK'],
        'Alert_Settings': ['movement_alert', 'power_alert', 'speed_limit']
    }
    
    # Validation rules for parameters
    VALIDATION_RULES = {
        'server_ip': {'type': 'ip_address'},
        'server_port': {'type': 'port', 'range': (1, 65535)},
        'apn_server': {'type': 'string', 'max_length': 100, 'required': True},
        'apn_user': {'type': 'string', 'max_length': 50},
        'apn_password': {'type': 'string', 'max_length': 50},
        'server_protocol': {'type': 'enum', 'values': ['TCP', 'UDP']},
        'gt06_protocol': {'type': 'string', 'pattern': r'^GT06-0x[0-9A-Fa-f]{2}$'},
        'timer_ign_on': {'type': 'integer', 'range': (1, 3600)},
        'timer_ign_off': {'type': 'integer', 'range': (1, 3600)},
        'heartbeat_interval': {'type': 'integer', 'range': (10, 3600)},
        'heartbeat_ign_on': {'type': 'integer', 'range': (10, 3600)},
        'heartbeat_ign_off': {'type': 'integer', 'range': (10, 3600)},
        'vibration': {'type': 'integer', 'range': (1, 255)},
        'sensitivity': {'type': 'integer', 'range': (1, 10)},
        'speed_limit': {'type': 'integer', 'range': (1, 300)},
        'movement_alert': {'type': 'boolean'},
        'power_alert': {'type': 'boolean'},
        'battery_alert': {'type': 'boolean'},
        'device_imei': {'type': 'imei'},
        'device_iccid': {'type': 'iccid'},
        'protocol': {'type': 'integer', 'range': (0, 10)},
        'tcp_ack': {'type': 'boolean'},
        'GT06SEL': {'type': 'integer', 'range': (0, 2)},  # LT32Pro protocol selection: 0=GT06, 1=CRX3, 2=CRX
        'POSBYACK': {'type': 'integer', 'range': (0, 1)},  # LT32Pro TCP ACK: 0=Disabled, 1=Enabled
        'profile_version': {'type': 'version'}
    }
    
    # Default values for optional parameters
    DEFAULT_VALUES = {
        'profile_version': '1.0',
        'apn_user': '',
        'apn_password': '',
        'server_port': '8080',
        'server_protocol': 'TCP',
        'heartbeat_interval': '60',
        'heartbeat_ign_on': '60',
        'heartbeat_ign_off': '300',
        'timer_ign_on': '30',
        'timer_ign_off': '300',
        'vibration': '128',
        'sensitivity': '5',
        'movement_alert': 'ON',
        'power_alert': 'ON',
        'battery_alert': 'ON',
        'speed_limit': '120',
        'protocol': '2',
        'tcp_ack': 'OFF',
        'GT06SEL': '2',  # Default to CRX protocol
        'POSBYACK': '0'  # Default to disabled TCP ACK
    }
    
    def __init__(self):
        self.validation_issues: List[ValidationIssue] = []

    def validate_profile_file(self, file_path: str) -> Tuple[bool, List[ValidationIssue]]:
        """
        Validate a complete profile file.
        
        Args:
            file_path: Path to the profile file to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        self.validation_issues.clear()
        
        if not os.path.exists(file_path):
            self.validation_issues.append(ValidationIssue(
                ValidationSeverity.ERROR, "File", "existence",
                f"Profile file does not exist: {file_path}"
            ))
            return False, self.validation_issues
        
        try:
            config = configparser.ConfigParser()
            config.read(file_path, encoding='utf-8')
            
            self._validate_file_format(config)
            self._validate_required_sections(config)
            self._validate_parameter_values(config)
            self._check_parameter_completeness(config)
            
        except Exception as e:
            self.validation_issues.append(ValidationIssue(
                ValidationSeverity.ERROR, "File", "parsing",
                f"Failed parsing profile file: {str(e)}"
            ))
            return False, self.validation_issues
        
        has_errors = any(issue.severity == ValidationSeverity.ERROR for issue in self.validation_issues)
        return not has_errors, self.validation_issues

    def _validate_file_format(self, config: configparser.ConfigParser) -> None:
        """Validate basic file format."""
        if not config.sections():
            self.validation_issues.append(ValidationIssue(
                ValidationSeverity.ERROR, "File", "format",
                "Profile file contains no sections"
            ))

    def _validate_required_sections(self, config: configparser.ConfigParser) -> None:
        """Validate required sections and parameters."""
        for section_name, required_params in self.REQUIRED_SECTIONS.items():
            if not config.has_section(section_name):
                self.validation_issues.append(ValidationIssue(
                    ValidationSeverity.ERROR, section_name, "section",
                    f"Required section missing: {section_name}"
                ))
                continue
            
            section = config[section_name]
            for param in required_params:
                if param not in section:
                    self.validation_issues.append(ValidationIssue(
                        ValidationSeverity.ERROR, section_name, param,
                        f"Required parameter missing: {param}"
                    ))

    def _validate_parameter_values(self, config: configparser.ConfigParser) -> None:
        """Validate parameter values."""
        # Create a case-insensitive mapping of validation rules
        validation_rules_lower = {k.lower(): k for k in self.VALIDATION_RULES.keys()}
        
        for section_name in config.sections():
            if section_name not in self.REQUIRED_SECTIONS and section_name not in self.OPTIONAL_SECTIONS:
                continue
                
            section = config[section_name]
            for param_name, value in section.items():
                # Check for case-insensitive match
                if param_name in validation_rules_lower:
                    # Use the original case name for validation
                    original_param_name = validation_rules_lower[param_name]
                    self._validate_single_parameter(section_name, original_param_name, value)

    def _validate_single_parameter(self, section: str, param: str, value: str) -> None:
        """Validate a single parameter value."""
        if not value.strip():
            if self.VALIDATION_RULES[param].get('required', False):
                self.validation_issues.append(ValidationIssue(
                    ValidationSeverity.ERROR, section, param,
                    f"Required parameter cannot be empty: {param}"
                ))
            return
        
        rules = self.VALIDATION_RULES[param]
        param_type = rules['type']
        
        try:
            if param_type == 'ip_address':
                ipaddress.ip_address(value)
            elif param_type == 'port':
                port = int(value)
                min_val, max_val = rules['range']
                if not (min_val <= port <= max_val):
                    raise ValueError(f"Port must be between {min_val} and {max_val}")
            elif param_type == 'integer':
                int_val = int(value)
                if 'range' in rules:
                    min_val, max_val = rules['range']
                    if not (min_val <= int_val <= max_val):
                        raise ValueError(f"Value must be between {min_val} and {max_val}")
            elif param_type == 'boolean':
                if value.upper() not in ['ON', 'OFF', 'TRUE', 'FALSE', 'ENABLED', 'DISABLED']:
                    raise ValueError("Boolean value must be ON/OFF, TRUE/FALSE, or ENABLED/DISABLED")
            elif param_type == 'enum':
                if value not in rules['values']:
                    raise ValueError(f"Value must be one of: {', '.join(rules['values'])}")
            elif param_type == 'string':
                if 'max_length' in rules and len(value) > rules['max_length']:
                    raise ValueError(f"String too long (max {rules['max_length']} characters)")
                if 'pattern' in rules and not re.match(rules['pattern'], value):
                    raise ValueError(f"String does not match required pattern")
            elif param_type == 'imei':
                if not self._validate_imei(value):
                    raise ValueError("Invalid IMEI format (must be 15 digits)")
            elif param_type == 'iccid':
                if not self._validate_iccid(value):
                    raise ValueError("Invalid ICCID format (must be 19-20 digits)")
            elif param_type == 'version':
                if not re.match(r'^\d+\.\d+(\.\d+)?$', value):
                    raise ValueError("Invalid version format (expected X.Y or X.Y.Z)")
                    
        except ValueError as e:
            self.validation_issues.append(ValidationIssue(
                ValidationSeverity.ERROR, section, param,
                f"Invalid value for {param}: {str(e)}", current_value=value
            ))

    def _validate_imei(self, imei: str) -> bool:
        """Validate IMEI format."""
        return re.match(r'^\d{15}$', imei) is not None

    def _validate_iccid(self, iccid: str) -> bool:
        """Validate ICCID format."""
        return re.match(r'^\d{19,20}$', iccid) is not None

    def _check_parameter_completeness(self, config: configparser.ConfigParser) -> None:
        """Check for missing optional parameters."""
        # Check optional sections
        for section_name, params in self.OPTIONAL_SECTIONS.items():
            if not config.has_section(section_name):
                self.validation_issues.append(ValidationIssue(
                    ValidationSeverity.INFO, section_name, "section",
                    f"Optional section missing: {section_name}"
                ))
                continue
            
            section = config[section_name]
            for param in params:
                if param not in section and param in self.DEFAULT_VALUES:
                    self.validation_issues.append(ValidationIssue(
                        ValidationSeverity.INFO, section_name, param,
                        f"Optional parameter missing: {param}",
                        suggested_value=self.DEFAULT_VALUES[param]
                    ))
        
        # Check required sections for optional parameters with default values
        for section_name, params in self.REQUIRED_SECTIONS.items():
            if config.has_section(section_name):
                section = config[section_name]
                # Get all parameters that could be in this section
                all_section_params = []
                if section_name == 'Profile_Info':
                    all_section_params = ['profile_version']  # Only profile_version has a default
                elif section_name == 'APN_Configuration':
                    all_section_params = ['apn_user', 'apn_password']
                
                for param in all_section_params:
                    if param not in section and param in self.DEFAULT_VALUES:
                        self.validation_issues.append(ValidationIssue(
                            ValidationSeverity.INFO, section_name, param,
                            f"Optional parameter missing: {param}",
                            suggested_value=self.DEFAULT_VALUES[param]
                        ))

    def get_validation_summary(self) -> Dict[str, int]:
        """Get validation summary."""
        summary = {
            'errors': 0,
            'warnings': 0,
            'info': 0,
            'total': len(self.validation_issues)
        }
        
        for issue in self.validation_issues:
            if issue.severity == ValidationSeverity.ERROR:
                summary['errors'] += 1
            elif issue.severity == ValidationSeverity.WARNING:
                summary['warnings'] += 1
            elif issue.severity == ValidationSeverity.INFO:
                summary['info'] += 1
        
        return summary
    
    def create_backup(self, file_path: str, backup_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Create a backup of a profile file.
        
        Args:
            file_path: Path to the profile file to backup
            backup_dir: Optional directory to store backup (defaults to same directory as file)
            
        Returns:
            Tuple of (success boolean, backup_path or error message)
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False, f"File does not exist: {file_path}"
            
            # Create backup file name
            if backup_dir:
                # Create backup directory if it doesn't exist
                os.makedirs(backup_dir, exist_ok=True)
                backup_path = os.path.join(backup_dir, f"{os.path.basename(file_path)}.backup.{int(datetime.now().timestamp())}")
            else:
                # Create backup in same directory as original file
                file_dir = os.path.dirname(file_path)
                backup_path = os.path.join(file_dir, f"{os.path.basename(file_path)}.backup.{int(datetime.now().timestamp())}")
            
            # Copy file to backup location
            shutil.copy2(file_path, backup_path)
            
            return True, backup_path
            
        except Exception as e:
            return False, f"Error creating backup: {str(e)}"
    
    def restore_from_backup(self, backup_path: str, target_path: str) -> Tuple[bool, str]:
        """
        Restore a profile file from a backup.
        
        Args:
            backup_path: Path to the backup file
            target_path: Path where to restore the file
            
        Returns:
            Tuple of (success boolean, message)
        """
        try:
            # Check if backup file exists
            if not os.path.exists(backup_path):
                return False, f"Backup file does not exist: {backup_path}"
            
            # Validate the backup file before restoring
            is_valid, issues = self.validate_profile_file(backup_path)
            if not is_valid:
                # Collect error messages
                error_messages = [issue.message for issue in issues if issue.severity == ValidationSeverity.ERROR]
                return False, f"Invalid backup file: {'; '.join(error_messages)}"
            
            # Copy backup to target location
            shutil.copy2(backup_path, target_path)
            
            return True, f"Profile restored successfully from {backup_path}"
            
        except Exception as e:
            return False, f"Error restoring from backup: {str(e)}"
    
    def add_missing_parameters(self, file_path: str, add_defaults: bool = True) -> Tuple[bool, str]:
        """
        Add missing optional parameters to a profile file.
        
        Args:
            file_path: Path to the profile file
            add_defaults: Whether to add default values for missing parameters
            
        Returns:
            Tuple of (success boolean, message)
        """
        try:
            # Read the existing config file
            config = configparser.ConfigParser()
            config.read(file_path, encoding='utf-8')
            
            added_count = 0
            
            # Add missing optional parameters with default values
            if add_defaults:
                for section_name, params in self.OPTIONAL_SECTIONS.items():
                    if not config.has_section(section_name):
                        config.add_section(section_name)
                    
                    section = config[section_name]
                    for param in params:
                        if param not in section and param in self.DEFAULT_VALUES:
                            section[param] = self.DEFAULT_VALUES[param]
                            added_count += 1
            
            # Write the updated config back to file
            with open(file_path, 'w', encoding='utf-8') as config_file:
                config.write(config_file)
            
            return True, f"Added {added_count} missing parameters"
            
        except Exception as e:
            return False, f"Error adding missing parameters: {str(e)}"
    
    def upgrade_legacy_profile(self, file_path: str, backup: bool = True) -> Tuple[bool, str]:
        """
        Upgrade a legacy profile format to the current format.
        
        Args:
            file_path: Path to the legacy profile file
            backup: Whether to create a backup before upgrading
            
        Returns:
            Tuple of (success boolean, message)
        """
        try:
            # Create backup if requested
            if backup:
                backup_success, backup_message = self.create_backup(file_path)
                if not backup_success:
                    return False, f"Failed to create backup: {backup_message}"
            
            # Read the existing config file
            config = configparser.ConfigParser()
            config.read(file_path, encoding='utf-8')
            
            # Check if profile is already in current format
            if (config.has_section('Profile_Info') and 
                config.has_section('APN_Configuration') and
                config.has_section('Server_Configuration')):
                return True, "Profile is already in current format"
            
            # Create new config with current format
            new_config = configparser.ConfigParser()
            
            # Add Profile_Info section
            new_config.add_section('Profile_Info')
            new_config['Profile_Info']['profile_name'] = 'Upgraded Profile'
            new_config['Profile_Info']['profile_version'] = '1.0'
            new_config['Profile_Info']['created_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Migrate sections from legacy format
            if config.has_section('APN_Settings'):
                new_config.add_section('APN_Configuration')
                apn_section = config['APN_Settings']
                if 'apn_server' in apn_section:
                    new_config['APN_Configuration']['apn_server'] = apn_section['apn_server']
                if 'apn_user' in apn_section:
                    new_config['APN_Configuration']['apn_user'] = apn_section['apn_user']
                if 'apn_password' in apn_section:
                    new_config['APN_Configuration']['apn_password'] = apn_section['apn_password']
                else:
                    new_config['APN_Configuration']['apn_password'] = ''
            
            if config.has_section('Server_Settings'):
                new_config.add_section('Server_Configuration')
                server_section = config['Server_Settings']
                if 'server_ip' in server_section:
                    new_config['Server_Configuration']['server_ip'] = server_section['server_ip']
                if 'server_port' in server_section:
                    new_config['Server_Configuration']['server_port'] = server_section['server_port']
            
            if config.has_section('Timers'):
                new_config.add_section('Timer_Settings')
                timer_section = config['Timers']
                if 'timer_ign_on' in timer_section:
                    new_config['Timer_Settings']['timer_ign_on'] = timer_section['timer_ign_on']
            
            # Write the updated config back to file
            with open(file_path, 'w', encoding='utf-8') as config_file:
                new_config.write(config_file)
            
            return True, "Profile upgraded successfully"
            
        except Exception as e:
            return False, f"Error upgrading profile: {str(e)}"
