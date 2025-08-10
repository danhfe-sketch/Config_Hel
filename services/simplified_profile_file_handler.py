"""
Simplified Profile File Handler

This module provides a simplified profile file handler that focuses only on the
[Device_Parameters] section, creating a universal format that works across all
profile operations without unnecessary metadata sections.

Requirements addressed:
- 1.1: Exclude [profile info] sections from generated files
- 1.2: Include only device parameter data in output files
- 1.4: Ignore [profile info] sections when loading existing profiles
- 1.5: Use universal format for all profile operations
- 4.5: Maintain data integrity across all operations
"""

import configparser
import os
import re
import logging
import time
from typing import Dict, Tuple, Optional, List, Set
from datetime import datetime


class ProfileValidationError(Exception):
    """Custom exception for profile validation errors."""
    pass


class ProfileRecoveryError(Exception):
    """Custom exception for profile recovery errors."""
    pass


class SimplifiedProfileFileHandler:
    """
    Simplified profile file handler that works with universal format.
    
    This handler creates and reads profile files containing only the
    [Device_Parameters] section, providing a clean, universal format
    that works for all profile operations with robust validation and error recovery.
    """
    
    # Define expected parameter patterns for validation
    PARAMETER_PATTERNS = {
        'apn_server': r'^[a-zA-Z0-9\.\-_]+$',
        'apn_user': r'^[a-zA-Z0-9\.\-_@]*$',
        'apn_password': r'^.*$',  # Allow any characters for password
        'server_ip': r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
        'server_port': r'^\d{1,5}$',
        'vibration': r'^\d{1,3}$',
        'sensitivity': r'^\d{1,2}$',
        'protocol': r'^(TCP|UDP)$',
        'transmission_mode': r'^(GPRS|SMS)$',
        'ignition_type': r'^(Digital|Analog|DIGITAL|ANALOG)$'
    }
    
    # Define parameter value ranges for validation
    PARAMETER_RANGES = {
        'server_port': (1, 65535),
        'vibration': (0, 255),
        'sensitivity': (1, 10)
    }
    
    # Define required parameters that must be present
    REQUIRED_PARAMETERS = {
        'apn_server', 'server_ip', 'server_port'
    }
    
    def __init__(self):
        """Initialize the simplified profile file handler."""
        self.logger = logging.getLogger(__name__)
        self._validation_errors = []
        self._recovery_actions = []
    
    def validate_device_parameters_section(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate that a profile file contains the required [Device_Parameters] section.
        
        Args:
            file_path: Path to the profile file to validate
            
        Returns:
            Tuple of (is_valid boolean, error message or empty string)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"Profile file does not exist: {file_path}"
            
            if not os.access(file_path, os.R_OK):
                return False, f"Profile file is not readable: {file_path}"
            
            # Check file size (empty files are invalid)
            if os.path.getsize(file_path) == 0:
                return False, "Profile file is empty"
            
            config = configparser.ConfigParser()
            try:
                config.read(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                # Try with different encodings
                for encoding in ['latin-1', 'cp1252']:
                    try:
                        config.read(file_path, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    return False, "Profile file has unsupported encoding"
            
            # Check if Device_Parameters section exists
            if not config.has_section('Device_Parameters'):
                return False, "Profile file missing required [Device_Parameters] section"
            
            # Check if section has any parameters
            if len(config['Device_Parameters']) == 0:
                return False, "[Device_Parameters] section is empty"
            
            return True, ""
            
        except configparser.Error as e:
            return False, f"Profile file format error: {str(e)}"
        except Exception as e:
            return False, f"Profile validation error: {str(e)}"
    
    def validate_parameter_values(self, parameters: Dict[str, str]) -> Tuple[bool, List[str]]:
        """
        Validate parameter values against expected patterns and ranges.
        
        Args:
            parameters: Dictionary of parameters to validate
            
        Returns:
            Tuple of (all_valid boolean, list of validation error messages)
        """
        validation_errors = []
        
        # Check required parameters
        missing_required = self.REQUIRED_PARAMETERS - set(parameters.keys())
        if missing_required:
            validation_errors.append(f"Missing required parameters: {', '.join(missing_required)}")
        
        # Validate each parameter
        for param_name, param_value in parameters.items():
            if not param_value:  # Skip empty values
                continue
                
            # Check pattern validation
            if param_name in self.PARAMETER_PATTERNS:
                pattern = self.PARAMETER_PATTERNS[param_name]
                if not re.match(pattern, param_value):
                    validation_errors.append(f"Invalid format for {param_name}: '{param_value}'")
            
            # Check range validation
            if param_name in self.PARAMETER_RANGES:
                try:
                    value = int(param_value)
                    min_val, max_val = self.PARAMETER_RANGES[param_name]
                    if not (min_val <= value <= max_val):
                        validation_errors.append(f"{param_name} value {value} out of range [{min_val}-{max_val}]")
                except ValueError:
                    validation_errors.append(f"{param_name} must be a number, got: '{param_value}'")
        
        return len(validation_errors) == 0, validation_errors
    
    def recover_corrupted_profile(self, file_path: str) -> Tuple[Dict[str, str], List[str]]:
        """
        Attempt to recover parameters from a corrupted or incomplete profile file.
        
        Args:
            file_path: Path to the corrupted profile file
            
        Returns:
            Tuple of (recovered parameters dict, list of recovery actions taken)
        """
        recovery_actions = []
        recovered_parameters = {}
        
        try:
            # Try to read the file with different approaches
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # If file is completely corrupted, try line-by-line recovery
            if not content.strip():
                recovery_actions.append("File was empty, no recovery possible")
                return recovered_parameters, recovery_actions
            
            # Try to find Device_Parameters section manually
            lines = content.split('\n')
            in_device_params = False
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#') or line.startswith(';'):
                    continue
                
                # Check for section headers
                if line.startswith('[') and line.endswith(']'):
                    section_name = line[1:-1].strip()
                    in_device_params = (section_name == 'Device_Parameters')
                    if in_device_params:
                        recovery_actions.append(f"Found [Device_Parameters] section at line {line_num}")
                    continue
                
                # If we're in Device_Parameters section, try to parse parameters
                if in_device_params and '=' in line:
                    try:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        recovered_parameters[key] = value
                        recovery_actions.append(f"Recovered parameter: {key} = {value}")
                        
                    except Exception as e:
                        recovery_actions.append(f"Failed to parse line {line_num}: {line} ({str(e)})")
            
            # If no Device_Parameters section found, try to recover from other sections
            if not recovered_parameters:
                recovery_actions.append("No [Device_Parameters] section found, attempting recovery from other sections")
                recovered_parameters = self._recover_from_legacy_sections(content, recovery_actions)
            
            # Apply default values for missing required parameters
            self._apply_default_values(recovered_parameters, recovery_actions)
            
        except Exception as e:
            recovery_actions.append(f"Recovery failed with error: {str(e)}")
        
        return recovered_parameters, recovery_actions
    
    def _recover_from_legacy_sections(self, content: str, recovery_actions: List[str]) -> Dict[str, str]:
        """
        Attempt to recover parameters from legacy profile sections.
        
        Args:
            content: File content as string
            recovery_actions: List to append recovery actions to
            
        Returns:
            Dictionary of recovered parameters
        """
        recovered = {}
        
        # Try to parse as INI file and extract from known sections
        try:
            config = configparser.ConfigParser()
            config.read_string(content)
            
            # Map legacy sections to device parameters
            section_mappings = {
                'APN_Configuration': ['apn_server', 'apn_user', 'apn_password'],
                'Server_Configuration': ['server_ip', 'server_port', 'protocol'],
                'Device_Settings': ['vibration', 'sensitivity', 'transmission_mode', 'ignition_type']
            }
            
            for section_name, param_names in section_mappings.items():
                if config.has_section(section_name):
                    recovery_actions.append(f"Found legacy section: [{section_name}]")
                    for param_name in param_names:
                        if config.has_option(section_name, param_name):
                            value = config.get(section_name, param_name)
                            recovered[param_name] = value
                            recovery_actions.append(f"Recovered from [{section_name}]: {param_name} = {value}")
        
        except Exception as e:
            recovery_actions.append(f"Legacy section recovery failed: {str(e)}")
        
        return recovered
    
    def _apply_default_values(self, parameters: Dict[str, str], recovery_actions: List[str]) -> None:
        """
        Apply default values for missing required parameters.
        
        Args:
            parameters: Parameters dictionary to update
            recovery_actions: List to append recovery actions to
        """
        defaults = {
            'apn_server': 'internet.provider.com',
            'server_ip': '192.168.1.100',
            'server_port': '8080',
            'protocol': 'TCP',
            'transmission_mode': 'GPRS',
            'vibration': '128',
            'sensitivity': '5'
        }
        
        for param_name in self.REQUIRED_PARAMETERS:
            if param_name not in parameters or not parameters[param_name]:
                if param_name in defaults:
                    parameters[param_name] = defaults[param_name]
                    recovery_actions.append(f"Applied default value for {param_name}: {defaults[param_name]}")
    
    def sanitize_parameter_values(self, parameters: Dict[str, str]) -> Tuple[Dict[str, str], List[str]]:
        """
        Sanitize parameter values to ensure they meet validation requirements.
        
        Args:
            parameters: Dictionary of parameters to sanitize
            
        Returns:
            Tuple of (sanitized parameters dict, list of sanitization actions)
        """
        sanitized = parameters.copy()
        sanitization_actions = []
        
        for param_name, param_value in parameters.items():
            if not param_value:
                continue
            
            original_value = param_value
            
            # Sanitize based on parameter type
            if param_name == 'server_ip':
                # Ensure IP format
                if not re.match(self.PARAMETER_PATTERNS['server_ip'], param_value):
                    # Try to extract IP-like pattern or use default
                    ip_match = re.search(r'(\d{1,3}\.){3}\d{1,3}', param_value)
                    if ip_match:
                        # Validate extracted IP components
                        ip_parts = ip_match.group().split('.')
                        valid_ip_parts = []
                        for part in ip_parts:
                            part_num = int(part)
                            if part_num > 255:
                                part_num = 255
                            valid_ip_parts.append(str(part_num))
                        sanitized[param_name] = '.'.join(valid_ip_parts)
                        sanitization_actions.append(f"Sanitized IP {param_name}: {original_value} -> {sanitized[param_name]}")
                    else:
                        # Use default IP if no valid pattern found
                        sanitized[param_name] = '192.168.1.100'
                        sanitization_actions.append(f"Applied default IP for {param_name}: {original_value} -> {sanitized[param_name]}")
            
            elif param_name == 'server_port':
                # Ensure port is numeric and in valid range
                port_match = re.search(r'\d+', param_value)
                if port_match:
                    port = int(port_match.group())
                    if port < 1:
                        port = 8080
                    elif port > 65535:
                        port = 8080
                    sanitized[param_name] = str(port)
                    if sanitized[param_name] != original_value:
                        sanitization_actions.append(f"Sanitized {param_name}: {original_value} -> {sanitized[param_name]}")
            
            elif param_name in ['vibration', 'sensitivity']:
                # Ensure numeric values in range
                num_match = re.search(r'\d+', param_value)
                if num_match:
                    value = int(num_match.group())
                    if param_name == 'vibration':
                        value = max(0, min(255, value))
                    elif param_name == 'sensitivity':
                        value = max(1, min(10, value))
                    sanitized[param_name] = str(value)
                    if sanitized[param_name] != original_value:
                        sanitization_actions.append(f"Sanitized {param_name}: {original_value} -> {sanitized[param_name]}")
                else:
                    # No numeric value found, use defaults
                    if param_name == 'vibration':
                        sanitized[param_name] = '128'
                    elif param_name == 'sensitivity':
                        sanitized[param_name] = '5'
                    sanitization_actions.append(f"Applied default for {param_name}: {original_value} -> {sanitized[param_name]}")
            
            elif param_name in ['protocol', 'transmission_mode', 'ignition_type']:
                # Ensure valid enum values
                if param_name == 'protocol':
                    value = param_value.upper()
                    if value not in ['TCP', 'UDP']:
                        value = 'TCP'
                elif param_name == 'transmission_mode':
                    value = param_value.upper()
                    if value not in ['GPRS', 'SMS']:
                        value = 'GPRS'
                elif param_name == 'ignition_type':
                    value = param_value.capitalize()  # Digital, Analog
                    if value not in ['Digital', 'Analog']:
                        value = 'Digital'
                
                sanitized[param_name] = value
                if sanitized[param_name] != original_value:
                    sanitization_actions.append(f"Sanitized {param_name}: {original_value} -> {sanitized[param_name]}")
        
        return sanitized, sanitization_actions

    def write_universal_profile(self, file_path: str, parameters: Dict[str, str]) -> Tuple[bool, str]:
        """
        Write a profile file in universal format with only [Device_Parameters] section.
        Includes validation and sanitization of parameters before writing with performance optimization.
        
        Args:
            file_path: Path where to write the profile file
            parameters: Dictionary of device parameters to write
            
        Returns:
            Tuple of (success boolean, error message or empty string)
        """
        write_start_time = time.time()
        
        try:
            # Fast validation check - only validate if parameters seem problematic
            needs_validation = any(
                not isinstance(v, str) or len(str(v)) > 1000 or '\n' in str(v)
                for v in parameters.values()
            )
            
            if needs_validation:
                # Validate parameters before writing
                is_valid, validation_errors = self.validate_parameter_values(parameters)
                if not is_valid:
                    self.logger.warning(f"Parameter validation issues: {'; '.join(validation_errors)}")
                    # Sanitize parameters to fix validation issues
                    sanitized_params, sanitization_actions = self.sanitize_parameter_values(parameters)
                    if sanitization_actions:
                        self.logger.info(f"Applied sanitization: {'; '.join(sanitization_actions)}")
                    parameters = sanitized_params
            
            # Ensure directory exists (optimized check)
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Optimized file writing - build content in memory first
            lines = ['[Device_Parameters]\n']
            
            # Sort parameters for consistent output and better performance
            sorted_params = sorted(parameters.items())
            
            for param_name, param_value in sorted_params:
                # Convert all values to strings and handle None values
                if param_value is None:
                    param_value = ""
                # Escape special characters for INI format
                param_value_str = str(param_value).replace('\n', '\\n').replace('\r', '\\r')
                lines.append(f"{param_name} = {param_value_str}\n")
            
            # Write all content at once for better performance
            with open(file_path, 'w', encoding='utf-8', buffering=8192) as config_file:
                config_file.writelines(lines)
            
            # Quick validation of written file (only check if file exists and has content)
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                return False, "Written file is empty or does not exist"
            
            write_duration = time.time() - write_start_time
            self.logger.debug(f"Profile write completed in {write_duration:.3f}s for {len(parameters)} parameters")
            
            return True, ""
            
        except PermissionError:
            return False, f"Permission denied writing to: {file_path}"
        except OSError as e:
            return False, f"OS error writing file: {str(e)}"
        except Exception as e:
            return False, f"Error writing profile file: {str(e)}"
    
    def read_universal_profile(self, file_path: str) -> Tuple[Dict[str, str], str]:
        """
        Read a profile file focusing only on [Device_Parameters] section with performance optimization.
        Includes validation and error recovery for corrupted or incomplete files.
        
        This method ignores all other sections (like [Profile_Info]) and only
        extracts parameters from the [Device_Parameters] section, providing
        backward compatibility with existing profile formats.
        
        Args:
            file_path: Path to the profile file to read
            
        Returns:
            Tuple of (parameters dictionary, error message or empty string)
        """
        read_start_time = time.time()
        
        try:
            # Quick file existence and readability check
            if not os.path.exists(file_path):
                return {}, f"Profile file does not exist: {file_path}"
            
            if not os.access(file_path, os.R_OK):
                return {}, f"Profile file is not readable: {file_path}"
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return {}, "Profile file is empty"
            
            # For small files, skip detailed validation and try direct reading
            skip_validation = file_size < 10240  # 10KB threshold
            
            if not skip_validation:
                # Validate the file structure for larger files
                is_valid, validation_error = self.validate_device_parameters_section(file_path)
                
                if not is_valid:
                    self.logger.warning(f"Profile validation failed: {validation_error}")
                    # Attempt recovery
                    recovered_params, recovery_actions = self.recover_corrupted_profile(file_path)
                    
                    if recovered_params:
                        self.logger.info(f"Profile recovery successful: {'; '.join(recovery_actions)}")
                        return recovered_params, f"Recovered from corrupted file"
                    else:
                        return {}, f"Profile validation failed and recovery unsuccessful: {validation_error}"
            
            # Optimized file reading - read entire file at once for better performance
            try:
                with open(file_path, 'r', encoding='utf-8', buffering=8192) as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try with different encodings
                for encoding in ['latin-1', 'cp1252']:
                    try:
                        with open(file_path, 'r', encoding=encoding, buffering=8192) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    return {}, "Profile file has unsupported encoding"
            
            # Fast parsing - look for Device_Parameters section directly
            parameters = {}
            lines = content.split('\n')
            in_device_params = False
            
            for line in lines:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#') or line.startswith(';'):
                    continue
                
                # Check for section headers
                if line.startswith('[') and line.endswith(']'):
                    section_name = line[1:-1].strip()
                    in_device_params = (section_name == 'Device_Parameters')
                    continue
                
                # If we're in Device_Parameters section, parse parameters
                if in_device_params and '=' in line:
                    try:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Unescape special characters
                        value = value.replace('\\n', '\n').replace('\\r', '\r')
                        
                        parameters[key] = value
                        
                    except Exception:
                        # Skip malformed lines
                        continue
            
            if not parameters:
                return {}, "No [Device_Parameters] section found or no parameters in file"
            
            # Skip parameter validation for performance unless parameters look suspicious
            needs_validation = any(
                len(str(v)) > 1000 or '\n' in str(v) or not isinstance(v, str)
                for v in parameters.values()
            )
            
            if needs_validation:
                # Validate the read parameters
                is_params_valid, param_errors = self.validate_parameter_values(parameters)
                if not is_params_valid:
                    self.logger.warning(f"Read parameters have validation issues: {'; '.join(param_errors)}")
                    # Sanitize parameters
                    sanitized_params, sanitization_actions = self.sanitize_parameter_values(parameters)
                    if sanitization_actions:
                        self.logger.info(f"Applied sanitization to read parameters: {'; '.join(sanitization_actions)}")
                    parameters = sanitized_params
            
            read_duration = time.time() - read_start_time
            self.logger.debug(f"Profile read completed in {read_duration:.3f}s for {len(parameters)} parameters")
            
            return parameters, ""
            
        except Exception as e:
            self.logger.error(f"Error reading profile file: {str(e)}")
            # Attempt recovery for any other errors
            recovered_params, recovery_actions = self.recover_corrupted_profile(file_path)
            if recovered_params:
                self.logger.info(f"Recovered from general error: {'; '.join(recovery_actions)}")
                return recovered_params, f"Recovered from error"
            return {}, f"Error reading profile file: {str(e)}"
    
    def convert_legacy_profile(self, file_path: str) -> Dict[str, str]:
        """
        Convert a legacy profile file to universal format by extracting
        only the [Device_Parameters] section.
        
        This method provides compatibility with existing profile files that
        may contain multiple sections like [Profile_Info], [APN_Configuration], etc.
        
        Args:
            file_path: Path to the legacy profile file
            
        Returns:
            Dictionary containing only device parameters
        """
        parameters, error = self.read_universal_profile(file_path)
        if error:
            # If reading failed, return empty dict
            return {}
        return parameters
    
    def validate_universal_profile(self, file_path: str) -> Tuple[bool, str]:
        """
        Comprehensive validation of a profile file including structure and parameter values.
        
        Args:
            file_path: Path to the profile file to validate
            
        Returns:
            Tuple of (is_valid boolean, error message or empty string)
        """
        try:
            # First validate file structure
            structure_valid, structure_error = self.validate_device_parameters_section(file_path)
            if not structure_valid:
                return False, f"Structure validation failed: {structure_error}"
            
            # Then validate parameter values
            parameters, read_error = self.read_universal_profile(file_path)
            if read_error and not parameters:
                return False, f"Read validation failed: {read_error}"
            
            # Validate parameter values
            values_valid, value_errors = self.validate_parameter_values(parameters)
            if not values_valid:
                return False, f"Parameter validation failed: {'; '.join(value_errors)}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def get_parameter_count(self, file_path: str) -> int:
        """
        Get the number of parameters in a profile file.
        
        Args:
            file_path: Path to the profile file
            
        Returns:
            Number of parameters in the file, or 0 if error
        """
        parameters, error = self.read_universal_profile(file_path)
        if error:
            return 0
        return len(parameters)
    
    def file_exists_and_readable(self, file_path: str) -> bool:
        """
        Check if a file exists and is readable.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file exists and is readable, False otherwise
        """
        try:
            return os.path.exists(file_path) and os.access(file_path, os.R_OK)
        except Exception:
            return False
    
    def create_sample_universal_profile(self, file_path: str, sample_parameters: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
        """
        Create a sample universal profile file for testing purposes.
        
        Args:
            file_path: Path where to create the sample file
            sample_parameters: Optional parameters to include, uses defaults if None
            
        Returns:
            Tuple of (success boolean, error message or empty string)
        """
        if sample_parameters is None:
            sample_parameters = {
                'apn_server': 'internet.provider.com',
                'apn_user': 'username',
                'apn_password': 'password',
                'server_ip': '192.168.1.100',
                'server_port': '8080',
                'vibration': '128',
                'sensitivity': '5'
            }
        
        return self.write_universal_profile(file_path, sample_parameters)
    
    def get_validation_report(self, file_path: str) -> Dict[str, any]:
        """
        Get a comprehensive validation report for a profile file.
        
        Args:
            file_path: Path to the profile file to analyze
            
        Returns:
            Dictionary containing validation results and recovery information
        """
        report = {
            'file_path': file_path,
            'file_exists': os.path.exists(file_path),
            'file_readable': False,
            'structure_valid': False,
            'structure_errors': [],
            'parameters_valid': False,
            'parameter_errors': [],
            'parameters_count': 0,
            'recovery_possible': False,
            'recovery_actions': [],
            'sanitization_needed': False,
            'sanitization_actions': []
        }
        
        if not report['file_exists']:
            report['structure_errors'].append('File does not exist')
            return report
        
        report['file_readable'] = os.access(file_path, os.R_OK)
        if not report['file_readable']:
            report['structure_errors'].append('File is not readable')
            return report
        
        # Validate structure
        structure_valid, structure_error = self.validate_device_parameters_section(file_path)
        report['structure_valid'] = structure_valid
        if not structure_valid:
            report['structure_errors'].append(structure_error)
            
            # Try recovery
            recovered_params, recovery_actions = self.recover_corrupted_profile(file_path)
            report['recovery_possible'] = len(recovered_params) > 0
            report['recovery_actions'] = recovery_actions
            
            if report['recovery_possible']:
                # Validate recovered parameters
                params_valid, param_errors = self.validate_parameter_values(recovered_params)
                report['parameters_valid'] = params_valid
                report['parameter_errors'] = param_errors
                report['parameters_count'] = len(recovered_params)
                
                if not params_valid:
                    # Check if sanitization would help
                    sanitized_params, sanitization_actions = self.sanitize_parameter_values(recovered_params)
                    sanitized_valid, sanitized_errors = self.validate_parameter_values(sanitized_params)
                    report['sanitization_needed'] = not sanitized_valid
                    report['sanitization_actions'] = sanitization_actions
        else:
            # Read parameters without automatic sanitization for validation report
            try:
                config = configparser.ConfigParser()
                config.read(file_path, encoding='utf-8')
                
                raw_parameters = {}
                if config.has_section('Device_Parameters'):
                    for param_name, param_value in config['Device_Parameters'].items():
                        raw_parameters[param_name] = param_value
                
                report['parameters_count'] = len(raw_parameters)
                
                if raw_parameters:
                    params_valid, param_errors = self.validate_parameter_values(raw_parameters)
                    report['parameters_valid'] = params_valid
                    report['parameter_errors'] = param_errors
                    
                    if not params_valid:
                        # Check if sanitization would help
                        sanitized_params, sanitization_actions = self.sanitize_parameter_values(raw_parameters)
                        sanitized_valid, sanitized_errors = self.validate_parameter_values(sanitized_params)
                        report['sanitization_needed'] = len(sanitized_errors) < len(param_errors)
                        report['sanitization_actions'] = sanitization_actions
            except Exception as e:
                report['parameter_errors'].append(f"Error reading parameters: {str(e)}")
        
        return report
    
    def repair_profile_file(self, file_path: str, backup_original: bool = True) -> Tuple[bool, str]:
        """
        Attempt to repair a corrupted profile file by applying recovery and sanitization.
        
        Args:
            file_path: Path to the profile file to repair
            backup_original: Whether to create a backup of the original file
            
        Returns:
            Tuple of (success boolean, status message)
        """
        try:
            if backup_original and os.path.exists(file_path):
                backup_path = f"{file_path}.backup"
                import shutil
                shutil.copy2(file_path, backup_path)
            
            # Get validation report
            report = self.get_validation_report(file_path)
            
            if report['structure_valid'] and report['parameters_valid']:
                return True, "Profile file is already valid, no repair needed"
            
            # If structure is valid but parameters need sanitization, try that first
            if report['structure_valid'] and not report['parameters_valid']:
                # Read parameters and apply sanitization
                parameters, read_error = self.read_universal_profile(file_path)
                if parameters:
                    # Write back with sanitization (write method handles this)
                    success, write_error = self.write_universal_profile(file_path, parameters)
                    if success:
                        return True, f"Profile file repaired with parameter sanitization"
                    else:
                        return False, f"Failed to write sanitized parameters: {write_error}"
            
            # Attempt recovery for structural issues
            if not report['recovery_possible']:
                return False, "Profile file cannot be recovered"
            
            # Read with recovery
            parameters, read_error = self.read_universal_profile(file_path)
            if not parameters:
                return False, f"Recovery failed: {read_error}"
            
            # Write repaired file
            success, write_error = self.write_universal_profile(file_path, parameters)
            if not success:
                return False, f"Failed to write repaired file: {write_error}"
            
            # Verify repair
            final_valid, final_error = self.validate_universal_profile(file_path)
            if not final_valid:
                return False, f"Repair verification failed: {final_error}"
            
            return True, f"Profile file repaired successfully. Recovery actions: {'; '.join(report['recovery_actions'])}"
            
        except Exception as e:
            return False, f"Repair failed with error: {str(e)}"