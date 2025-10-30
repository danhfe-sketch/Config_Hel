"""
Profile Converter - Format standardization and compatibility for profile files.

This module provides format conversion and standardization for profile files including:
1. Converting raw profile data to standard ProfileData format
2. Legacy profile format migration utilities
3. Parameter name mapping and value format conversion
4. Integration with existing ProfileData structure
5. Backward compatibility with different profile versions
"""

import re
import logging
import configparser
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Tuple
from enum import Enum

# Import existing data models
from services.profile_data_models import ProfileData, ProfileMetadata, ValidationInfo


class ProfileFormatVersion(Enum):
    """Supported profile format versions."""
    LEGACY_V0_9 = "0.9"
    CURRENT_V1_0 = "1.0"
    CURRENT_V1_1 = "1.1"
    FUTURE_V1_2 = "1.2"


class ConversionErrorType(Enum):
    """Types of conversion errors."""
    UNSUPPORTED_VERSION = "unsupported_version"
    MISSING_REQUIRED_DATA = "missing_required_data"
    INVALID_PARAMETER_FORMAT = "invalid_parameter_format"
    PARAMETER_MAPPING_ERROR = "parameter_mapping_error"
    VALUE_CONVERSION_ERROR = "value_conversion_error"


@dataclass
class ConversionError:
    """Conversion error information."""
    error_type: ConversionErrorType
    parameter_name: Optional[str]
    original_value: Optional[str]
    error_message: str
    suggestion: Optional[str] = None


@dataclass
class ConversionResult:
    """Result of profile conversion operation."""
    success: bool
    profile_data: Optional[ProfileData] = None
    errors: List[ConversionError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    conversion_summary: str = ""
    parameters_converted: int = 0
    parameters_failed: int = 0


@dataclass
class MigrationResult:
    """Result of legacy profile migration."""
    success: bool
    original_version: str
    target_version: str
    migrated_data: Optional[ProfileData] = None
    migration_log: List[str] = field(default_factory=list)
    errors: List[ConversionError] = field(default_factory=list)


class ProfileConverter:
    """
    Format standardization and compatibility for profile files.
    
    Features:
    - Converting raw profile data to standard ProfileData format
    - Legacy profile format migration utilities
    - Parameter name mapping and value format conversion
    - Integration with existing ProfileData structure
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the profile converter.
        
        Args:
            logger: Optional logger instance for detailed logging
        """
        self.logger = logger or logging.getLogger(__name__)
        self.current_version = ProfileFormatVersion.CURRENT_V1_0.value
        
        # Initialize parameter mappings
        self._init_parameter_mappings()
        
        # Initialize value converters
        self._init_value_converters()
        
        # Initialize legacy format handlers
        self._init_legacy_format_handlers()
        
        # Initialize section mappings
        self._init_section_mappings()
        
        self.logger.info("ProfileConverter initialized")

    def convert_to_standard_format(self, raw_data: Dict[str, Any]) -> ConversionResult:
        """
        Convert raw profile data to standard ProfileData format.
        
        Args:
            raw_data: Raw profile data dictionary (could be from ConfigParser or other sources)
            
        Returns:
            ConversionResult with standardized ProfileData or conversion errors
        """
        self.logger.info("Converting raw data to standard format")
        
        errors = []
        warnings = []
        parameters_converted = 0
        parameters_failed = 0
        
        try:
            # Detect format version
            format_version = self._detect_format_version(raw_data)
            self.logger.debug(f"Detected format version: {format_version}")
            
            # Extract metadata
            metadata_result = self._extract_and_convert_metadata(raw_data, format_version)
            if not metadata_result['success']:
                errors.extend(metadata_result['errors'])
                if not metadata_result['metadata']:
                    return ConversionResult(
                        success=False,
                        errors=errors,
                        conversion_summary="Failed to extract profile metadata"
                    )
            
            metadata = metadata_result['metadata']
            warnings.extend(metadata_result.get('warnings', []))
            
            # Extract and convert device parameters
            parameters_result = self._extract_and_convert_parameters(raw_data, format_version)
            device_parameters = parameters_result['parameters']
            errors.extend(parameters_result['errors'])
            warnings.extend(parameters_result.get('warnings', []))
            parameters_converted = parameters_result['converted_count']
            parameters_failed = parameters_result['failed_count']
            
            # Create validation info
            validation_info = ValidationInfo(
                is_validated=True,
                validation_date=datetime.now().isoformat(),
                validation_errors=[]
            )
            
            # Create standardized ProfileData
            profile_data = ProfileData(
                metadata=metadata,
                device_parameters=device_parameters,
                validation_info=validation_info,
                format_version=self.current_version
            )
            
            # Update parameter count in metadata
            profile_data.metadata.parameter_count = len(device_parameters)
            
            success = len([e for e in errors if e.error_type in [
                ConversionErrorType.UNSUPPORTED_VERSION,
                ConversionErrorType.MISSING_REQUIRED_DATA
            ]]) == 0
            
            conversion_summary = self._generate_conversion_summary(
                parameters_converted, parameters_failed, len(warnings), format_version
            )
            
            self.logger.info(f"Conversion completed: {conversion_summary}")
            
            return ConversionResult(
                success=success,
                profile_data=profile_data,
                errors=errors,
                warnings=warnings,
                conversion_summary=conversion_summary,
                parameters_converted=parameters_converted,
                parameters_failed=parameters_failed
            )
            
        except Exception as e:
            error_msg = f"Unexpected error during conversion: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return ConversionResult(
                success=False,
                errors=[ConversionError(
                    error_type=ConversionErrorType.INVALID_PARAMETER_FORMAT,
                    parameter_name=None,
                    original_value=None,
                    error_message=error_msg
                )],
                conversion_summary="Conversion failed due to unexpected error"
            )

    def migrate_legacy_format(self, legacy_data: Dict[str, Any], version: str) -> MigrationResult:
        """
        Migrate legacy profile format to current standard format.
        
        Args:
            legacy_data: Legacy profile data
            version: Version of the legacy format
            
        Returns:
            MigrationResult with migrated ProfileData or migration errors
        """
        self.logger.info(f"Migrating legacy format from version {version} to {self.current_version}")
        
        migration_log = []
        errors = []
        
        try:
            # Check if version is supported for migration
            if version not in self.legacy_format_handlers:
                error = ConversionError(
                    error_type=ConversionErrorType.UNSUPPORTED_VERSION,
                    parameter_name=None,
                    original_value=version,
                    error_message=f"Unsupported legacy version: {version}",
                    suggestion=f"Supported versions: {', '.join(self.legacy_format_handlers.keys())}"
                )
                return MigrationResult(
                    success=False,
                    original_version=version,
                    target_version=self.current_version,
                    errors=[error]
                )
            
            # Get migration handler for the version
            migration_handler = self.legacy_format_handlers[version]
            migration_log.append(f"Starting migration from version {version}")
            
            # Apply version-specific migrations
            migrated_data = migration_handler(legacy_data, migration_log)
            
            # Convert migrated data to standard format
            conversion_result = self.convert_to_standard_format(migrated_data)
            
            if not conversion_result.success:
                errors.extend(conversion_result.errors)
                migration_log.append("Migration failed during format conversion")
                return MigrationResult(
                    success=False,
                    original_version=version,
                    target_version=self.current_version,
                    migration_log=migration_log,
                    errors=errors
                )
            
            migration_log.append(f"Migration completed successfully: {conversion_result.parameters_converted} parameters converted")
            
            return MigrationResult(
                success=True,
                original_version=version,
                target_version=self.current_version,
                migrated_data=conversion_result.profile_data,
                migration_log=migration_log,
                errors=conversion_result.errors
            )
            
        except Exception as e:
            error_msg = f"Migration failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            migration_log.append(error_msg)
            
            return MigrationResult(
                success=False,
                original_version=version,
                target_version=self.current_version,
                migration_log=migration_log,
                errors=[ConversionError(
                    error_type=ConversionErrorType.INVALID_PARAMETER_FORMAT,
                    parameter_name=None,
                    original_value=None,
                    error_message=error_msg
                )]
            )

    def extract_device_parameters(self, profile_data: ProfileData) -> Dict[str, Any]:
        """
        Extract device parameters from ProfileData in a format suitable for device deployment.
        
        Args:
            profile_data: ProfileData object containing the parameters
            
        Returns:
            Dictionary of device parameters ready for deployment
        """
        self.logger.debug("Extracting device parameters for deployment")
        
        try:
            # Start with the device parameters from the profile
            device_params = profile_data.device_parameters.copy()
            
            # Apply reverse parameter mapping (standard names to device-specific names)
            mapped_params = {}
            for param_name, param_value in device_params.items():
                # Check if parameter needs reverse mapping
                device_param_name = self._get_device_parameter_name(param_name)
                
                # Apply value conversion for device deployment
                converted_value = self._convert_value_for_device(param_name, param_value)
                
                mapped_params[device_param_name] = converted_value
            
            self.logger.debug(f"Extracted {len(mapped_params)} device parameters")
            return mapped_params
            
        except Exception as e:
            self.logger.error(f"Error extracting device parameters: {str(e)}")
            return profile_data.device_parameters.copy()

    def create_profile_metadata(self, device_info: Dict[str, Any], 
                              parameters: Dict[str, Any]) -> ProfileMetadata:
        """
        Create ProfileMetadata from device information and parameters.
        
        Args:
            device_info: Dictionary containing device information (IMEI, version, etc.)
            parameters: Dictionary of device parameters
            
        Returns:
            ProfileMetadata object with generated metadata
        """
        self.logger.debug("Creating profile metadata from device info")
        
        try:
            # Generate profile name based on device info or timestamp
            profile_name = self._generate_profile_name(device_info)
            
            # Extract device information
            device_imei = device_info.get('imei') or device_info.get('device_imei')
            device_version = device_info.get('version') or device_info.get('device_version')
            
            # Create metadata
            metadata = ProfileMetadata(
                profile_name=profile_name,
                created_date=datetime.now().isoformat(),
                device_imei=device_imei,
                device_version=device_version,
                parameter_count=len(parameters),
                app_version=self.current_version,
                checksum=None  # Will be calculated later if needed
            )
            
            self.logger.debug(f"Created metadata for profile: {profile_name}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error creating profile metadata: {str(e)}")
            # Return minimal metadata
            return ProfileMetadata(
                profile_name=f"Profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                created_date=datetime.now().isoformat(),
                parameter_count=len(parameters),
                app_version=self.current_version
            )

    def convert_config_parser_to_profile_data(self, config: configparser.ConfigParser) -> ConversionResult:
        """
        Convert a ConfigParser object to ProfileData format.
        
        Args:
            config: ConfigParser object containing profile data
            
        Returns:
            ConversionResult with converted ProfileData
        """
        self.logger.debug("Converting ConfigParser to ProfileData")
        
        try:
            # Convert ConfigParser to dictionary format
            raw_data = {}
            
            for section_name in config.sections():
                raw_data[section_name] = dict(config[section_name])
            
            # Use standard conversion method
            return self.convert_to_standard_format(raw_data)
            
        except Exception as e:
            error_msg = f"Error converting ConfigParser: {str(e)}"
            self.logger.error(error_msg)
            
            return ConversionResult(
                success=False,
                errors=[ConversionError(
                    error_type=ConversionErrorType.INVALID_PARAMETER_FORMAT,
                    parameter_name=None,
                    original_value=None,
                    error_message=error_msg
                )],
                conversion_summary="Failed to convert ConfigParser to ProfileData"
            )

    def _init_parameter_mappings(self):
        """Initialize parameter name mappings between different formats."""
        # Standard parameter names to legacy parameter names
        self.parameter_mappings = {
            # Legacy v0.9 mappings
            'legacy_0.9': {
                # APN parameters
                'apn_server': 'apn',
                'apn_user': 'apn_username', 
                'apn_password': 'apn_pwd',
                'transmission_mode': 'protocol',
                
                # Server parameters
                'server_ip': 'server_address',
                'server_port': 'port',
                'server_protocol': 'server_type',
                
                # Timer parameters
                'timer_ign_on': 'ignition_on_timer',
                'timer_ign_off': 'ignition_off_timer',
                'heartbeat_ign_on': 'heartbeat_on',
                'heartbeat_ign_off': 'heartbeat_off',
                
                # Device parameters
                'vibration': 'vibration_level',
                'sensitivity': 'shock_sensitivity',
                'ignition_type': 'ignition_mode',
                
                # Alert parameters
                'movement_alert': 'motion_alert',
                'power_alert': 'power_cut_alert',
                'battery_alert': 'low_battery_alert'
            }
        }
        
        # Reverse mappings (legacy to standard)
        self.reverse_parameter_mappings = {}
        for version, mappings in self.parameter_mappings.items():
            self.reverse_parameter_mappings[version] = {v: k for k, v in mappings.items()}

    def _init_value_converters(self):
        """Initialize value conversion functions."""
        self.value_converters = {
            # Boolean conversions
            'boolean_to_on_off': lambda x: 'ON' if str(x).lower() in ['true', '1', 'on', 'yes'] else 'OFF',
            'on_off_to_boolean': lambda x: str(x).upper() == 'ON',
            
            # Numeric conversions
            'string_to_int': lambda x: int(x) if str(x).isdigit() else 0,
            'int_to_string': lambda x: str(x),
            
            # Protocol conversions
            'protocol_number_to_name': self._convert_protocol_number_to_name,
            'protocol_name_to_number': self._convert_protocol_name_to_number,
            
            # Transmission mode conversions
            'transmission_mode_to_protocol': lambda x: '0' if str(x).upper() == 'TCP' else '1',
            'protocol_to_transmission_mode': lambda x: 'TCP' if str(x) == '0' else 'UDP'
        }

    def _init_legacy_format_handlers(self):
        """Initialize handlers for different legacy format versions."""
        self.legacy_format_handlers = {
            '0.9': self._migrate_from_v0_9,
            '1.0': self._migrate_from_v1_0  # For future compatibility
        }

    def _init_section_mappings(self):
        """Initialize section name mappings between formats."""
        self.section_mappings = {
            # Standard section organization
            'standard': {
                'Profile_Info': 'Profile_Info',
                'APN_Configuration': 'APN_Configuration', 
                'Server_Configuration': 'Server_Configuration',
                'Timer_Settings': 'Timer_Settings',
                'Device_Parameters': 'Device_Parameters',
                'Alert_Settings': 'Alert_Settings',
                'Advanced_Settings': 'Advanced_Settings'
            },
            
            # Legacy v0.9 section mappings
            'legacy_0.9': {
                'ProfileInfo': 'Profile_Info',
                'APNConfig': 'APN_Configuration',
                'ServerConfig': 'Server_Configuration',
                'TimerConfig': 'Timer_Settings',
                'DeviceConfig': 'Device_Parameters',
                'AlertConfig': 'Alert_Settings'
            }
        }

    def _detect_format_version(self, raw_data: Dict[str, Any]) -> str:
        """
        Detect the format version of the profile data.
        
        Args:
            raw_data: Raw profile data
            
        Returns:
            Detected version string
        """
        # Validate that raw_data is a dictionary
        if not isinstance(raw_data, dict):
            raise ValueError(f"Invalid data type: expected dict, got {type(raw_data)}")
        
        # Check for explicit version in Profile_Info
        if 'Profile_Info' in raw_data:
            profile_info = raw_data['Profile_Info']
            if isinstance(profile_info, dict):
                if 'profile_version' in profile_info:
                    return profile_info['profile_version']
                if 'format_version' in profile_info:
                    return profile_info['format_version']
        
        # Check for legacy section names
        if 'ProfileInfo' in raw_data or 'APNConfig' in raw_data:
            return '0.9'
        
        # Check for current format indicators
        if 'APN_Configuration' in raw_data or 'Server_Configuration' in raw_data:
            return '1.0'
        
        # Default to current version
        return self.current_version

    def _extract_and_convert_metadata(self, raw_data: Dict[str, Any], 
                                    format_version: str) -> Dict[str, Any]:
        """Extract and convert metadata from raw data."""
        result = {
            'success': True,
            'metadata': None,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Find metadata section
            metadata_section = None
            if 'Profile_Info' in raw_data:
                metadata_section = raw_data['Profile_Info']
            elif 'ProfileInfo' in raw_data:  # Legacy format
                metadata_section = raw_data['ProfileInfo']
                result['warnings'].append("Using legacy ProfileInfo section name")
            
            if not metadata_section:
                # Create minimal metadata
                result['warnings'].append("No metadata section found, creating minimal metadata")
                metadata = ProfileMetadata(
                    profile_name=f"Converted_Profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    created_date=datetime.now().isoformat(),
                    parameter_count=0,
                    app_version=self.current_version
                )
            else:
                # Extract metadata fields
                profile_name = metadata_section.get('profile_name', 
                    f"Converted_Profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                created_date = metadata_section.get('created_date', datetime.now().isoformat())
                device_imei = metadata_section.get('device_imei')
                device_version = metadata_section.get('device_version')
                app_version = metadata_section.get('app_version', self.current_version)
                
                # Handle parameter count
                parameter_count = 0
                if 'parameter_count' in metadata_section:
                    try:
                        parameter_count = int(metadata_section['parameter_count'])
                    except (ValueError, TypeError):
                        result['warnings'].append("Invalid parameter_count value, will be recalculated")
                
                metadata = ProfileMetadata(
                    profile_name=profile_name,
                    created_date=created_date,
                    device_imei=device_imei,
                    device_version=device_version,
                    parameter_count=parameter_count,
                    app_version=app_version,
                    checksum=metadata_section.get('checksum')
                )
            
            result['metadata'] = metadata
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(ConversionError(
                error_type=ConversionErrorType.MISSING_REQUIRED_DATA,
                parameter_name='metadata',
                original_value=None,
                error_message=f"Failed to extract metadata: {str(e)}"
            ))
        
        return result

    def _extract_and_convert_parameters(self, raw_data: Dict[str, Any], 
                                      format_version: str) -> Dict[str, Any]:
        """Extract and convert device parameters from raw data."""
        result = {
            'parameters': {},
            'errors': [],
            'warnings': [],
            'converted_count': 0,
            'failed_count': 0
        }
        
        try:
            # Collect parameters from all sections except Profile_Info
            all_parameters = {}
            
            for section_name, section_data in raw_data.items():
                if section_name in ['Profile_Info', 'ProfileInfo']:
                    continue
                
                if isinstance(section_data, dict):
                    all_parameters.update(section_data)
            
            # Convert parameters based on format version
            for param_name, param_value in all_parameters.items():
                try:
                    # Apply parameter name mapping if needed
                    standard_param_name = self._map_parameter_name(param_name, format_version)
                    
                    # Apply value conversion if needed
                    converted_value = self._convert_parameter_value(
                        standard_param_name, param_value, format_version
                    )
                    
                    result['parameters'][standard_param_name] = converted_value
                    result['converted_count'] += 1
                    
                except Exception as e:
                    result['failed_count'] += 1
                    result['errors'].append(ConversionError(
                        error_type=ConversionErrorType.PARAMETER_MAPPING_ERROR,
                        parameter_name=param_name,
                        original_value=str(param_value),
                        error_message=f"Failed to convert parameter: {str(e)}",
                        suggestion=f"Check parameter format for {param_name}"
                    ))
            
        except Exception as e:
            result['errors'].append(ConversionError(
                error_type=ConversionErrorType.INVALID_PARAMETER_FORMAT,
                parameter_name=None,
                original_value=None,
                error_message=f"Failed to extract parameters: {str(e)}"
            ))
        
        return result

    def _map_parameter_name(self, param_name: str, format_version: str) -> str:
        """Map parameter name from legacy format to standard format."""
        if format_version in self.reverse_parameter_mappings:
            return self.reverse_parameter_mappings[format_version].get(param_name, param_name)
        return param_name

    def _convert_parameter_value(self, param_name: str, param_value: Any, 
                                format_version: str) -> Any:
        """Convert parameter value based on parameter type and format version."""
        # Convert to string first for consistent processing
        str_value = str(param_value) if param_value is not None else ""
        
        # Apply parameter-specific conversions
        if param_name in ['movement_alert', 'power_alert', 'battery_alert']:
            # Convert boolean-like values to ON/OFF
            return self.value_converters['boolean_to_on_off'](str_value)
        
        elif param_name == 'transmission_mode':
            # Ensure transmission mode is properly formatted
            if str_value.upper() in ['TCP', 'UDP']:
                return str_value.upper()
            elif str_value in ['0', '1']:
                return self.value_converters['protocol_to_transmission_mode'](str_value)
        
        elif param_name == 'gt06_protocol':
            # Convert protocol numbers to names if needed
            return self._convert_protocol_number_to_name(str_value)
        
        elif param_name in ['vibration', 'sensitivity', 'timer_ign_on', 'timer_ign_off', 
                           'heartbeat_ign_on', 'heartbeat_ign_off', 'server_port']:
            # Ensure numeric parameters are properly formatted
            try:
                return str(int(str_value)) if str_value.isdigit() else str_value
            except ValueError:
                return str_value
        
        # Return original value if no specific conversion needed
        return str_value

    def _convert_protocol_number_to_name(self, protocol_value: str) -> str:
        """Convert protocol number to protocol name."""
        protocol_map = {
            '0': 'GT06-0x60',
            '1': 'CRX3', 
            '2': 'GT06-0x12'
        }
        return protocol_map.get(str(protocol_value), protocol_value)

    def _convert_protocol_name_to_number(self, protocol_name: str) -> str:
        """Convert protocol name to protocol number."""
        name_to_number = {
            'GT06-0x60': '0',
            'CRX3': '1',
            'GT06-0x12': '2'
        }
        return name_to_number.get(protocol_name, '0')

    def _get_device_parameter_name(self, standard_name: str) -> str:
        """Get device-specific parameter name from standard name."""
        # For now, return the standard name as device names match
        # This can be extended if device-specific naming is needed
        return standard_name

    def _convert_value_for_device(self, param_name: str, param_value: Any) -> Any:
        """Convert parameter value for device deployment."""
        str_value = str(param_value) if param_value is not None else ""
        
        # Apply device-specific value conversions
        if param_name == 'transmission_mode':
            # Convert to protocol number for device
            return self.value_converters['transmission_mode_to_protocol'](str_value)
        
        elif param_name == 'gt06_protocol':
            # Convert protocol name to number for device
            return self._convert_protocol_name_to_number(str_value)
        
        elif param_name in ['movement_alert', 'power_alert', 'battery_alert']:
            # Convert ON/OFF to boolean for device
            return self.value_converters['on_off_to_boolean'](str_value)
        
        # Return original value for other parameters
        return param_value

    def _generate_profile_name(self, device_info: Dict[str, Any]) -> str:
        """Generate a profile name based on device information."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if device_info.get('imei'):
            return f"Profile_IMEI_{device_info['imei'][-6:]}_{timestamp}"
        elif device_info.get('device_version'):
            version_clean = re.sub(r'[^\w\d]', '_', device_info['device_version'])
            return f"Profile_{version_clean}_{timestamp}"
        else:
            return f"Profile_{timestamp}"

    def _migrate_from_v0_9(self, legacy_data: Dict[str, Any], 
                          migration_log: List[str]) -> Dict[str, Any]:
        """Migrate profile data from version 0.9 to current format."""
        migration_log.append("Applying v0.9 to v1.0 migration")
        
        migrated_data = {}
        
        # Migrate section names
        for old_section, new_section in self.section_mappings['legacy_0.9'].items():
            if old_section in legacy_data:
                migrated_data[new_section] = legacy_data[old_section].copy()
                migration_log.append(f"Migrated section: {old_section} -> {new_section}")
        
        # Migrate parameter names within sections
        for section_name, section_data in migrated_data.items():
            if section_name == 'Profile_Info':
                continue
                
            if isinstance(section_data, dict):
                migrated_params = {}
                for param_name, param_value in section_data.items():
                    # Map parameter name
                    standard_name = self._map_parameter_name(param_name, 'legacy_0.9')
                    migrated_params[standard_name] = param_value
                    
                    if standard_name != param_name:
                        migration_log.append(f"Migrated parameter: {param_name} -> {standard_name}")
                
                migrated_data[section_name] = migrated_params
        
        # Ensure Profile_Info section exists with updated version
        if 'Profile_Info' not in migrated_data:
            migrated_data['Profile_Info'] = {}
        
        migrated_data['Profile_Info']['profile_version'] = self.current_version
        migrated_data['Profile_Info']['migration_date'] = datetime.now().isoformat()
        migrated_data['Profile_Info']['migrated_from'] = '0.9'
        
        migration_log.append("v0.9 migration completed")
        return migrated_data

    def _migrate_from_v1_0(self, data: Dict[str, Any], 
                          migration_log: List[str]) -> Dict[str, Any]:
        """Handle v1.0 format (current format, minimal changes needed)."""
        migration_log.append("Processing v1.0 format (current version)")
        
        # For v1.0, just ensure all required fields are present
        migrated_data = data.copy()
        
        if 'Profile_Info' not in migrated_data:
            migrated_data['Profile_Info'] = {}
        
        # Ensure version is set correctly
        migrated_data['Profile_Info']['profile_version'] = self.current_version
        
        migration_log.append("v1.0 processing completed")
        return migrated_data

    def _generate_conversion_summary(self, converted: int, failed: int, 
                                   warnings: int, version: str) -> str:
        """Generate a summary of the conversion operation."""
        summary_parts = []
        
        if converted > 0:
            summary_parts.append(f"{converted} parameters converted")
        
        if failed > 0:
            summary_parts.append(f"{failed} parameters failed")
        
        if warnings > 0:
            summary_parts.append(f"{warnings} warnings")
        
        summary = f"Conversion from v{version}: " + ", ".join(summary_parts)
        
        if not summary_parts:
            summary = f"Conversion from v{version}: No parameters processed"
        
        return summary