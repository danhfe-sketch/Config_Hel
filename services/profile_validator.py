"""
Profile Validator - Comprehensive validation for profile files and data.

This module provides comprehensive validation for profile files including:
1. Structure validation for required sections and parameters
2. Parameter value validation with range and format checking
3. Compatibility validation for different profile versions
4. Integration with existing validation service patterns
"""

import re
import logging
import configparser
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Set
from enum import Enum
from services.profile_data_models import ProfileData, ProfileMetadata


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationErrorType(Enum):
    """Types of validation errors."""
    MISSING_SECTION = "missing_section"
    INVALID_PARAMETER = "invalid_parameter"
    FORMAT_ERROR = "format_error"
    RANGE_ERROR = "range_error"
    COMPATIBILITY_ERROR = "compatibility_error"
    STRUCTURE_ERROR = "structure_error"


@dataclass
class ValidationError:
    """Detailed validation error information."""
    error_type: ValidationErrorType
    location: str  # section name or parameter name
    message: str
    severity: ValidationSeverity
    suggestion: Optional[str] = None
    parameter_name: Optional[str] = None
    section_name: Optional[str] = None
    current_value: Optional[str] = None
    expected_format: Optional[str] = None


@dataclass
class ValidationWarning:
    """Validation warning information."""
    location: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class CorrectionSuggestion:
    """Suggested correction for validation issues."""
    parameter_name: str
    current_value: str
    suggested_value: str
    reason: str


@dataclass
class ValidationSummary:
    """Summary of validation results."""
    total_parameters: int = 0
    valid_parameters: int = 0
    invalid_parameters: int = 0
    missing_required_sections: int = 0
    compatibility_issues: int = 0
    format_version: str = "unknown"


@dataclass
class ValidationResult:
    """Comprehensive validation result."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    suggestions: List[CorrectionSuggestion] = field(default_factory=list)
    validation_summary: ValidationSummary = field(default_factory=ValidationSummary)
    validation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ParameterValidationResult:
    """Result of parameter value validation."""
    is_valid: bool
    parameter_name: str
    current_value: Any
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    suggested_value: Optional[str] = None


@dataclass
class MetadataValidationResult:
    """Result of metadata validation."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)


@dataclass
class CompatibilityResult:
    """Result of compatibility validation."""
    is_compatible: bool
    profile_version: str
    current_app_version: str
    compatibility_level: str  # 'full', 'partial', 'incompatible'
    migration_required: bool = False
    migration_suggestions: List[str] = field(default_factory=list)
    unsupported_features: List[str] = field(default_factory=list)


class ProfileValidator:
    """
    Comprehensive validation for profile files and data.
    
    Features:
    - Structure validation for required sections and parameters
    - Parameter value validation with range and format checking
    - Compatibility validation for different profile versions
    - Integration with existing validation service patterns
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the profile validator.
        
        Args:
            logger: Optional logger instance for detailed logging
        """
        self.logger = logger or logging.getLogger(__name__)
        self.current_app_version = "1.2"
        
        # Define required sections for profile files
        self.required_sections = {
            'Profile_Info': {
                'required': True,
                'description': 'Profile metadata and information'
            },
            'Device_Parameters': {
                'required': True,
                'description': 'Device configuration parameters'
            }
        }
        
        # Define optional sections that are commonly used
        self.optional_sections = {
            'APN_Configuration': {
                'description': 'APN and network configuration'
            },
            'Server_Configuration': {
                'description': 'Server connection settings'
            },
            'Timer_Settings': {
                'description': 'Timer and heartbeat configuration'
            },
            'Alert_Settings': {
                'description': 'Alert and notification settings'
            },
            'Advanced_Settings': {
                'description': 'Advanced device settings'
            }
        }
        
        # Define required metadata fields
        self.required_metadata_fields = {
            'profile_name': {
                'type': str,
                'required': True,
                'description': 'Name of the profile'
            },
            'created_date': {
                'type': str,
                'required': True,
                'description': 'Profile creation date'
            }
        }
        
        # Define optional metadata fields
        self.optional_metadata_fields = {
            'profile_version': {
                'type': str,
                'default': '1.2',
                'description': 'Profile format version'
            },
            'device_imei': {
                'type': str,
                'description': 'Device IMEI number'
            },
            'device_version': {
                'type': str,
                'description': 'Device firmware version'
            },
            'parameter_count': {
                'type': int,
                'description': 'Number of parameters in profile'
            },
            'app_version': {
                'type': str,
                'default': '1.2',
                'description': 'Application version that created the profile'
            },
            'checksum': {
                'type': str,
                'description': 'Profile data checksum'
            }
        }
        
        # Initialize parameter validation rules
        self._init_parameter_validation_rules()
        
        # Initialize compatibility rules
        self._init_compatibility_rules()
        
        self.logger.info("ProfileValidator initialized")

    def validate_profile_structure(self, profile_data: ProfileData) -> ValidationResult:
        """
        Validate the overall structure of a profile.
        
        Args:
            profile_data: ProfileData object to validate
            
        Returns:
            ValidationResult with comprehensive validation information
        """
        self.logger.info("Validating profile structure")
        
        errors = []
        warnings = []
        suggestions = []
        
        # Validate metadata
        metadata_result = self.validate_profile_metadata(profile_data.metadata)
        errors.extend(metadata_result.errors)
        warnings.extend(metadata_result.warnings)
        
        # Validate device parameters structure
        if not profile_data.device_parameters:
            errors.append(ValidationError(
                error_type=ValidationErrorType.MISSING_SECTION,
                location="Device_Parameters",
                message="Device parameters section is empty or missing",
                severity=ValidationSeverity.CRITICAL,
                suggestion="Add device parameters to the profile",
                section_name="Device_Parameters"
            ))
        
        # Validate parameter values
        parameter_results = self.validate_parameter_values(profile_data.device_parameters)
        for param_result in parameter_results:
            errors.extend(param_result.errors)
            warnings.extend(param_result.warnings)
            if param_result.suggested_value:
                suggestions.append(CorrectionSuggestion(
                    parameter_name=param_result.parameter_name,
                    current_value=str(param_result.current_value),
                    suggested_value=param_result.suggested_value,
                    reason=f"Parameter validation failed for {param_result.parameter_name}"
                ))
        
        # Create validation summary
        summary = ValidationSummary(
            total_parameters=len(profile_data.device_parameters),
            valid_parameters=len([r for r in parameter_results if r.is_valid]),
            invalid_parameters=len([r for r in parameter_results if not r.is_valid]),
            missing_required_sections=len([e for e in errors if e.error_type == ValidationErrorType.MISSING_SECTION]),
            compatibility_issues=0,  # Will be updated by compatibility validation
            format_version=profile_data.format_version
        )
        
        is_valid = len([e for e in errors if e.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]]) == 0
        
        result = ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            validation_summary=summary
        )
        
        self.logger.info(f"Profile structure validation completed: {'VALID' if is_valid else 'INVALID'}")
        return result

    def validate_parameter_values(self, parameters: Dict[str, Any]) -> List[ParameterValidationResult]:
        """
        Validate parameter values according to their defined rules.
        
        Args:
            parameters: Dictionary of parameter names and values
            
        Returns:
            List of ParameterValidationResult objects
        """
        self.logger.debug(f"Validating {len(parameters)} parameters")
        
        results = []
        
        for param_name, param_value in parameters.items():
            result = self._validate_single_parameter(param_name, param_value)
            results.append(result)
        
        return results

    def validate_profile_metadata(self, metadata: ProfileMetadata) -> MetadataValidationResult:
        """
        Validate profile metadata information.
        
        Args:
            metadata: ProfileMetadata object to validate
            
        Returns:
            MetadataValidationResult with validation details
        """
        self.logger.debug("Validating profile metadata")
        
        errors = []
        warnings = []
        
        # Validate required fields
        for field_name, field_config in self.required_metadata_fields.items():
            field_value = getattr(metadata, field_name, None)
            
            if field_value is None or (isinstance(field_value, str) and not field_value.strip()):
                errors.append(ValidationError(
                    error_type=ValidationErrorType.MISSING_SECTION,
                    location=f"Profile_Info.{field_name}",
                    message=f"Required metadata field '{field_name}' is missing or empty",
                    severity=ValidationSeverity.ERROR,
                    suggestion=f"Add {field_config['description'].lower()}",
                    parameter_name=field_name,
                    section_name="Profile_Info"
                ))
        
        # Validate profile name format
        if metadata.profile_name:
            if len(metadata.profile_name) > 100:
                errors.append(ValidationError(
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    location="Profile_Info.profile_name",
                    message="Profile name is too long (maximum 100 characters)",
                    severity=ValidationSeverity.ERROR,
                    suggestion="Shorten the profile name",
                    parameter_name="profile_name",
                    current_value=metadata.profile_name
                ))
            
            # Check for invalid characters
            invalid_chars = re.findall(r'[<>:"/\\|?*]', metadata.profile_name)
            if invalid_chars:
                errors.append(ValidationError(
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    location="Profile_Info.profile_name",
                    message=f"Profile name contains invalid characters: {', '.join(set(invalid_chars))}",
                    severity=ValidationSeverity.ERROR,
                    suggestion="Remove invalid characters from profile name",
                    parameter_name="profile_name",
                    current_value=metadata.profile_name
                ))
        
        # Validate created_date format
        if metadata.created_date:
            try:
                # Try to parse the date
                datetime.fromisoformat(metadata.created_date.replace('Z', '+00:00'))
            except ValueError:
                errors.append(ValidationError(
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    location="Profile_Info.created_date",
                    message="Invalid date format for created_date",
                    severity=ValidationSeverity.WARNING,
                    suggestion="Use ISO format (YYYY-MM-DD HH:MM:SS)",
                    parameter_name="created_date",
                    current_value=metadata.created_date,
                    expected_format="YYYY-MM-DD HH:MM:SS"
                ))
        
        # Validate IMEI format if present
        if metadata.device_imei:
            if not re.match(r'^\d{15}$', metadata.device_imei):
                errors.append(ValidationError(
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    location="Profile_Info.device_imei",
                    message="Invalid IMEI format (must be 15 digits)",
                    severity=ValidationSeverity.WARNING,
                    suggestion="Ensure IMEI is exactly 15 digits",
                    parameter_name="device_imei",
                    current_value=metadata.device_imei,
                    expected_format="15 digits"
                ))
        
        # Validate parameter count consistency
        if metadata.parameter_count is not None and metadata.parameter_count < 0:
            errors.append(ValidationError(
                error_type=ValidationErrorType.RANGE_ERROR,
                location="Profile_Info.parameter_count",
                message="Parameter count cannot be negative",
                severity=ValidationSeverity.ERROR,
                suggestion="Set parameter count to actual number of parameters",
                parameter_name="parameter_count",
                current_value=str(metadata.parameter_count)
            ))
        
        is_valid = len([e for e in errors if e.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]]) == 0
        
        return MetadataValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )

    def check_compatibility(self, profile_version: str) -> CompatibilityResult:
        """
        Check compatibility of a profile version with the current application.
        
        Args:
            profile_version: Version string from the profile
            
        Returns:
            CompatibilityResult with compatibility information
        """
        self.logger.debug(f"Checking compatibility for profile version: {profile_version}")
        
        # Parse version strings
        try:
            profile_ver = self._parse_version(profile_version)
            current_ver = self._parse_version(self.current_app_version)
        except ValueError as e:
            return CompatibilityResult(
                is_compatible=False,
                profile_version=profile_version,
                current_app_version=self.current_app_version,
                compatibility_level='incompatible',
                migration_required=False,
                migration_suggestions=[f"Invalid version format: {str(e)}"]
            )
        
        # Determine compatibility level
        compatibility_level = 'full'
        migration_required = False
        migration_suggestions = []
        unsupported_features = []
        
        # Major version compatibility
        if profile_ver['major'] > current_ver['major']:
            compatibility_level = 'incompatible'
            migration_suggestions.append(
                f"Profile was created with a newer version ({profile_version}). "
                f"Update application to version {profile_version} or higher."
            )
        elif profile_ver['major'] < current_ver['major']:
            compatibility_level = 'partial'
            migration_required = True
            migration_suggestions.append(
                f"Profile format is outdated (v{profile_version}). "
                f"Automatic migration to v{self.current_app_version} is recommended."
            )
        
        # Minor version compatibility
        elif profile_ver['minor'] > current_ver['minor']:
            compatibility_level = 'partial'
            migration_suggestions.append(
                f"Profile uses newer features from v{profile_version}. "
                f"Some features may not be available."
            )
        elif profile_ver['minor'] < current_ver['minor']:
            migration_suggestions.append(
                f"Profile can be upgraded to use new features from v{self.current_app_version}."
            )
        
        # Check for known compatibility issues
        compatibility_issues = self._check_version_specific_issues(profile_version)
        if compatibility_issues:
            unsupported_features.extend(compatibility_issues)
            if compatibility_level == 'full':
                compatibility_level = 'partial'
        
        is_compatible = compatibility_level != 'incompatible'
        
        return CompatibilityResult(
            is_compatible=is_compatible,
            profile_version=profile_version,
            current_app_version=self.current_app_version,
            compatibility_level=compatibility_level,
            migration_required=migration_required,
            migration_suggestions=migration_suggestions,
            unsupported_features=unsupported_features
        )

    def validate_config_parser_structure(self, config: configparser.ConfigParser) -> ValidationResult:
        """
        Validate the structure of a ConfigParser object representing a profile.
        
        Args:
            config: ConfigParser object to validate
            
        Returns:
            ValidationResult with structure validation details
        """
        self.logger.debug("Validating ConfigParser structure")
        
        errors = []
        warnings = []
        suggestions = []
        
        # Check for required sections
        for section_name, section_config in self.required_sections.items():
            if not config.has_section(section_name):
                errors.append(ValidationError(
                    error_type=ValidationErrorType.MISSING_SECTION,
                    location=section_name,
                    message=f"Required section '{section_name}' is missing",
                    severity=ValidationSeverity.CRITICAL,
                    suggestion=f"Add [{section_name}] section with {section_config['description'].lower()}",
                    section_name=section_name
                ))
        
        # Check for unknown sections (warnings only)
        known_sections = set(self.required_sections.keys()) | set(self.optional_sections.keys())
        for section_name in config.sections():
            if section_name not in known_sections:
                warnings.append(ValidationWarning(
                    location=section_name,
                    message=f"Unknown section '{section_name}' found",
                    suggestion=f"Verify that section '{section_name}' is needed"
                ))
        
        # Validate Profile_Info section structure
        if config.has_section('Profile_Info'):
            self._validate_profile_info_section(config['Profile_Info'], errors, warnings)
        
        # Count parameters in Device_Parameters section
        parameter_count = 0
        if config.has_section('Device_Parameters'):
            parameter_count = len(config['Device_Parameters'])
            if parameter_count == 0:
                warnings.append(ValidationWarning(
                    location="Device_Parameters",
                    message="Device_Parameters section is empty",
                    suggestion="Add device configuration parameters"
                ))
        
        # Create validation summary
        summary = ValidationSummary(
            total_parameters=parameter_count,
            valid_parameters=0,  # Will be updated by parameter validation
            invalid_parameters=0,  # Will be updated by parameter validation
            missing_required_sections=len([e for e in errors if e.error_type == ValidationErrorType.MISSING_SECTION]),
            compatibility_issues=0,
            format_version="unknown"
        )
        
        is_valid = len([e for e in errors if e.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]]) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            validation_summary=summary
        )

    def _validate_single_parameter(self, param_name: str, param_value: Any) -> ParameterValidationResult:
        """
        Validate a single parameter value.
        
        Args:
            param_name: Name of the parameter
            param_value: Value to validate
            
        Returns:
            ParameterValidationResult with validation details
        """
        errors = []
        warnings = []
        suggested_value = None
        
        # Get validation rules for this parameter
        if param_name not in self.parameter_validation_rules:
            # Unknown parameter - create warning
            warnings.append(ValidationWarning(
                location=f"Device_Parameters.{param_name}",
                message=f"Unknown parameter '{param_name}'",
                suggestion="Verify parameter name is correct"
            ))
            return ParameterValidationResult(
                is_valid=True,  # Unknown parameters don't fail validation
                parameter_name=param_name,
                current_value=param_value,
                warnings=warnings
            )
        
        rules = self.parameter_validation_rules[param_name]
        param_type = rules['type']
        
        # Convert value to string for validation
        str_value = str(param_value) if param_value is not None else ""
        
        # Check if required parameter is empty
        if rules.get('required', False) and not str_value.strip():
            errors.append(ValidationError(
                error_type=ValidationErrorType.INVALID_PARAMETER,
                location=f"Device_Parameters.{param_name}",
                message=f"Required parameter '{param_name}' is empty",
                severity=ValidationSeverity.ERROR,
                suggestion="Provide a value for this required parameter",
                parameter_name=param_name,
                current_value=str_value
            ))
            return ParameterValidationResult(
                is_valid=False,
                parameter_name=param_name,
                current_value=param_value,
                errors=errors
            )
        
        # Skip validation for empty optional parameters
        if not str_value.strip() and not rules.get('required', False):
            return ParameterValidationResult(
                is_valid=True,
                parameter_name=param_name,
                current_value=param_value
            )
        
        # Type-specific validation
        if param_type == 'numeric':
            self._validate_numeric_parameter(param_name, str_value, rules, errors, warnings)
            if errors and 'min' in rules and 'max' in rules:
                suggested_value = str(max(rules['min'], min(rules['max'], rules.get('default', rules['min']))))
        
        elif param_type == 'text':
            self._validate_text_parameter(param_name, str_value, rules, errors, warnings)
        
        elif param_type == 'dropdown':
            self._validate_dropdown_parameter(param_name, str_value, rules, errors, warnings)
            if errors and 'allowed_values' in rules:
                suggested_value = rules['allowed_values'][0]
        
        elif param_type == 'radio':
            self._validate_radio_parameter(param_name, str_value, rules, errors, warnings)
            if errors and 'allowed_values' in rules:
                suggested_value = rules['allowed_values'][0]
        
        elif param_type in ['apn', 'apn_credential']:
            self._validate_apn_parameter(param_name, str_value, rules, errors, warnings)
        
        elif param_type == 'phone':
            self._validate_phone_parameter(param_name, str_value, rules, errors, warnings)
        
        elif param_type == 'domain':
            self._validate_domain_parameter(param_name, str_value, rules, errors, warnings)
        
        is_valid = len([e for e in errors if e.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]]) == 0
        
        return ParameterValidationResult(
            is_valid=is_valid,
            parameter_name=param_name,
            current_value=param_value,
            errors=errors,
            warnings=warnings,
            suggested_value=suggested_value
        )

    def _validate_numeric_parameter(self, param_name: str, value: str, rules: Dict[str, Any], 
                                  errors: List[ValidationError], warnings: List[ValidationWarning]):
        """Validate numeric parameter values."""
        try:
            if rules.get('integer', False):
                num_value = int(value)
            else:
                num_value = float(value)
        except ValueError:
            errors.append(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                location=f"Device_Parameters.{param_name}",
                message=f"Parameter '{param_name}' must be a number",
                severity=ValidationSeverity.ERROR,
                suggestion="Enter a valid number",
                parameter_name=param_name,
                current_value=value,
                expected_format="number"
            ))
            return
        
        # Range validation
        if 'min' in rules and num_value < rules['min']:
            errors.append(ValidationError(
                error_type=ValidationErrorType.RANGE_ERROR,
                location=f"Device_Parameters.{param_name}",
                message=f"Parameter '{param_name}' value {num_value} is below minimum {rules['min']}",
                severity=ValidationSeverity.ERROR,
                suggestion=f"Use a value >= {rules['min']}",
                parameter_name=param_name,
                current_value=value
            ))
        
        if 'max' in rules and num_value > rules['max']:
            errors.append(ValidationError(
                error_type=ValidationErrorType.RANGE_ERROR,
                location=f"Device_Parameters.{param_name}",
                message=f"Parameter '{param_name}' value {num_value} is above maximum {rules['max']}",
                severity=ValidationSeverity.ERROR,
                suggestion=f"Use a value <= {rules['max']}",
                parameter_name=param_name,
                current_value=value
            ))

    def _validate_text_parameter(self, param_name: str, value: str, rules: Dict[str, Any],
                               errors: List[ValidationError], warnings: List[ValidationWarning]):
        """Validate text parameter values."""
        # Length validation
        if 'max_length' in rules and len(value) > rules['max_length']:
            errors.append(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                location=f"Device_Parameters.{param_name}",
                message=f"Parameter '{param_name}' exceeds maximum length of {rules['max_length']}",
                severity=ValidationSeverity.ERROR,
                suggestion=f"Shorten to {rules['max_length']} characters or less",
                parameter_name=param_name,
                current_value=value
            ))
        
        if 'min_length' in rules and len(value) < rules['min_length']:
            errors.append(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                location=f"Device_Parameters.{param_name}",
                message=f"Parameter '{param_name}' is shorter than minimum length of {rules['min_length']}",
                severity=ValidationSeverity.ERROR,
                suggestion=f"Extend to at least {rules['min_length']} characters",
                parameter_name=param_name,
                current_value=value
            ))
        
        # Pattern validation
        if 'pattern' in rules:
            try:
                if not re.match(rules['pattern'], value):
                    errors.append(ValidationError(
                        error_type=ValidationErrorType.FORMAT_ERROR,
                        location=f"Device_Parameters.{param_name}",
                        message=f"Parameter '{param_name}' format is invalid",
                        severity=ValidationSeverity.ERROR,
                        suggestion="Check the format requirements",
                        parameter_name=param_name,
                        current_value=value,
                        expected_format=rules.get('format_description', 'Valid format required')
                    ))
            except re.error:
                # If pattern is invalid, skip pattern validation and log warning
                warnings.append(ValidationWarning(
                    location=f"Device_Parameters.{param_name}",
                    message=f"Invalid regex pattern for parameter '{param_name}'",
                    suggestion="Check parameter validation rules"
                ))

    def _validate_dropdown_parameter(self, param_name: str, value: str, rules: Dict[str, Any],
                                   errors: List[ValidationError], warnings: List[ValidationWarning]):
        """Validate dropdown parameter values."""
        allowed_values = rules.get('allowed_values', [])
        if value not in allowed_values:
            errors.append(ValidationError(
                error_type=ValidationErrorType.INVALID_PARAMETER,
                location=f"Device_Parameters.{param_name}",
                message=f"Parameter '{param_name}' has invalid value '{value}'",
                severity=ValidationSeverity.ERROR,
                suggestion=f"Use one of: {', '.join(allowed_values)}",
                parameter_name=param_name,
                current_value=value
            ))

    def _validate_radio_parameter(self, param_name: str, value: str, rules: Dict[str, Any],
                                errors: List[ValidationError], warnings: List[ValidationWarning]):
        """Validate radio button parameter values."""
        # Radio parameters use the same validation as dropdown
        self._validate_dropdown_parameter(param_name, value, rules, errors, warnings)

    def _validate_apn_parameter(self, param_name: str, value: str, rules: Dict[str, Any],
                              errors: List[ValidationError], warnings: List[ValidationWarning]):
        """Validate APN-related parameter values."""
        if param_name == 'apn':
            # APN validation - domain, IP, URL, or simple name
            patterns = [
                r'^(?!.*\.\.+)(?!^\.)(?!.*\.$)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$',  # Domain
                r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',  # IP
                r'^https?://(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?:/.*)?$',  # URL
                r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$'  # Simple name (allows underscores, single char)
            ]
            
            if not any(re.match(pattern, value) for pattern in patterns):
                errors.append(ValidationError(
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    location=f"Device_Parameters.{param_name}",
                    message=f"APN '{value}' has invalid format",
                    severity=ValidationSeverity.ERROR,
                    suggestion="Use a valid domain name, IP address, URL, or simple APN name",
                    parameter_name=param_name,
                    current_value=value,
                    expected_format="domain.com, 192.168.1.1, http://example.com, or simple_name"
                ))
        else:
            # APN credentials validation
            if 'max_length' in rules and len(value) > rules['max_length']:
                errors.append(ValidationError(
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    location=f"Device_Parameters.{param_name}",
                    message=f"APN credential exceeds maximum length of {rules['max_length']}",
                    severity=ValidationSeverity.ERROR,
                    suggestion=f"Shorten to {rules['max_length']} characters or less",
                    parameter_name=param_name,
                    current_value=value
                ))

    def _validate_phone_parameter(self, param_name: str, value: str, rules: Dict[str, Any],
                                errors: List[ValidationError], warnings: List[ValidationWarning]):
        """Validate phone number parameter values."""
        # Basic phone number validation
        phone_pattern = r'^\+?[\d\s\-\(\)]{7,15}$'
        if not re.match(phone_pattern, value):
            errors.append(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                location=f"Device_Parameters.{param_name}",
                message=f"Phone number '{value}' has invalid format",
                severity=ValidationSeverity.ERROR,
                suggestion="Use format: +1234567890 or (123) 456-7890",
                parameter_name=param_name,
                current_value=value,
                expected_format="Valid phone number format"
            ))

    def _validate_domain_parameter(self, param_name: str, value: str, rules: Dict[str, Any],
                                 errors: List[ValidationError], warnings: List[ValidationWarning]):
        """Validate domain name parameter values."""
        domain_pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        if not re.match(domain_pattern, value):
            errors.append(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                location=f"Device_Parameters.{param_name}",
                message=f"Domain '{value}' has invalid format",
                severity=ValidationSeverity.ERROR,
                suggestion="Use format: example.com",
                parameter_name=param_name,
                current_value=value,
                expected_format="Valid domain name"
            ))

    def _validate_profile_info_section(self, profile_info: configparser.SectionProxy,
                                     errors: List[ValidationError], warnings: List[ValidationWarning]):
        """Validate the Profile_Info section structure."""
        # Check for required fields
        for field_name, field_config in self.required_metadata_fields.items():
            if field_name not in profile_info:
                errors.append(ValidationError(
                    error_type=ValidationErrorType.MISSING_SECTION,
                    location=f"Profile_Info.{field_name}",
                    message=f"Required field '{field_name}' is missing from Profile_Info",
                    severity=ValidationSeverity.ERROR,
                    suggestion=f"Add {field_name} = <value> to Profile_Info section",
                    parameter_name=field_name,
                    section_name="Profile_Info"
                ))

    def _parse_version(self, version_str: str) -> Dict[str, int]:
        """Parse a version string into components."""
        if not version_str:
            raise ValueError("Version string is empty")
        
        # Remove 'v' prefix if present
        version_str = version_str.lstrip('v')
        
        # Split by dots
        parts = version_str.split('.')
        if len(parts) < 2:
            raise ValueError(f"Invalid version format: {version_str}")
        
        try:
            return {
                'major': int(parts[0]),
                'minor': int(parts[1]),
                'patch': int(parts[2]) if len(parts) > 2 else 0
            }
        except ValueError:
            raise ValueError(f"Invalid version format: {version_str}")

    def _check_version_specific_issues(self, profile_version: str) -> List[str]:
        """Check for known compatibility issues with specific versions."""
        issues = []
        
        # Add version-specific compatibility checks here
        # This can be expanded as new versions are released
        
        return issues

    def _init_parameter_validation_rules(self):
        """Initialize parameter validation rules based on existing validation service."""
        # This is a subset of the most common parameters for profile validation
        # The full validation service has more comprehensive rules
        self.parameter_validation_rules = {
            # Network Parameters
            'apn': {
                'type': 'apn',
                'max_length': 50,
                'required': True
            },
            'apn_user': {
                'type': 'apn_credential',
                'max_length': 30,
                'required': False
            },
            'apn_password': {
                'type': 'apn_credential',
                'max_length': 30,
                'required': False
            },
            'server_address': {
                'type': 'text',
                'max_length': 100,
                'required': True
            },
            'server_port': {
                'type': 'numeric',
                'min': 1,
                'max': 65535,
                'integer': True
            },
            
            # Timer Parameters
            'moving_time': {
                'type': 'numeric',
                'min': 1,
                'max': 65535,
                'integer': True
            },
            'stopped_time': {
                'type': 'numeric',
                'min': 1,
                'max': 65535,
                'integer': True
            },
            'moving_heartbeat': {
                'type': 'numeric',
                'min': 30,
                'max': 86400,
                'integer': True
            },
            'stopped_heartbeat': {
                'type': 'numeric',
                'min': 30,
                'max': 86400,
                'integer': True
            },
            
            # Service Parameters
            'protocol': {
                'type': 'dropdown',
                'allowed_values': ['GT06 (0x60)', 'CRX3 (0x22)', 'CRX (0x12)']
            },
            'tcp_ack': {
                'type': 'dropdown',
                'allowed_values': ['Enabled', 'Disabled']
            },
            
            # Ignition Parameters
            'ignition_mode': {
                'type': 'dropdown',
                'allowed_values': ['Física (Physical)', 'Virtual por acelerômetro (Virtual by accelerometer)', 'Virtual por bateria (Virtual by battery)']
            },
            'on_voltage': {
                'type': 'numeric',
                'min': 6,
                'max': 60,
                'integer': True
            },
            'off_voltage': {
                'type': 'numeric',
                'min': 6,
                'max': 60,
                'integer': True
            },
            
            # Speed Parameters
            'speed_detection_time': {
                'type': 'numeric',
                'min': 5,
                'max': 600,
                'integer': True
            },
            'speed_limit': {
                'type': 'numeric',
                'min': 1,
                'max': 255,
                'integer': True
            },
            
            # Vibration Parameters
            'vibration_level': {
                'type': 'numeric',
                'min': 1,
                'max': 6,
                'integer': True
            },
            
            # Legacy parameters for backward compatibility
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
            
            # Phone parameters
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
            
            # Device identification
            'imei': {
                'type': 'text',
                'min_length': 15,
                'max_length': 15,
                'required': False,
                'pattern': r'^\d{15}$'
            }
        }

    def _init_compatibility_rules(self):
        """Initialize compatibility rules for different profile versions."""
        self.compatibility_rules = {
            '1.0': {
                'supported_features': ['basic_parameters', 'apn_config', 'timer_settings'],
                'deprecated_features': [],
                'migration_path': None
            },
            '1.1': {
                'supported_features': ['basic_parameters', 'apn_config', 'timer_settings', 'advanced_alerts'],
                'deprecated_features': [],
                'migration_path': '1.0'
            },
            '1.2': {
                'supported_features': ['basic_parameters', 'apn_config', 'timer_settings', 'advanced_alerts', 'security_features'],
                'deprecated_features': ['legacy_timer_format'],
                'migration_path': '1.1'
            }
        }