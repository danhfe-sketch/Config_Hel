"""
Profile Data Models

This module defines standardized data models for profile operations in the LT32Pro Device Configurator.
These models ensure consistent data structures across all profile-related components.

Requirements addressed:
- 5.1: Standardized profile file format with consistent naming conventions
- 5.2: Consistent structure handling for save and load operations
- 3.1: Comprehensive validation with specific error reporting
- 7.1: Clear error messages with specific parameter locations
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class ValidationError:
    """
    Represents a validation error with location and suggestion information.
    
    Addresses requirement 7.1: Clear error messages with specific parameter locations
    """
    error_type: str  # 'missing_section', 'invalid_parameter', 'format_error', 'value_error'
    location: str    # section name, parameter name, or file location
    message: str     # Human-readable error description
    severity: str    # 'critical', 'error', 'warning'
    suggestion: Optional[str] = None  # Actionable suggestion for fixing the error
    parameter_name: Optional[str] = None  # Specific parameter that caused the error
    expected_value: Optional[str] = None  # Expected value or format
    actual_value: Optional[str] = None    # Actual value that caused the error


@dataclass
class ValidationWarning:
    """
    Represents a validation warning for non-critical issues.
    """
    warning_type: str
    location: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class CorrectionSuggestion:
    """
    Represents a suggested correction for validation issues.
    """
    parameter_name: str
    current_value: Any
    suggested_value: Any
    reason: str


@dataclass
class ValidationSummary:
    """
    Summary of validation results.
    """
    total_parameters: int
    valid_parameters: int
    invalid_parameters: int
    missing_sections: int
    warnings_count: int
    errors_count: int
    critical_errors_count: int


@dataclass
class ValidationResult:
    """
    Comprehensive validation result with error information.
    
    Addresses requirement 3.1: Comprehensive validation with specific error reporting
    """
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    suggestions: List[CorrectionSuggestion] = field(default_factory=list)
    validation_summary: Optional[ValidationSummary] = None
    
    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors that prevent operation."""
        return any(error.severity == 'critical' for error in self.errors)
    
    def get_errors_by_severity(self, severity: str) -> List[ValidationError]:
        """Get all errors of a specific severity level."""
        return [error for error in self.errors if error.severity == severity]
    
    def get_errors_by_type(self, error_type: str) -> List[ValidationError]:
        """Get all errors of a specific type."""
        return [error for error in self.errors if error.error_type == error_type]


@dataclass
class ProfileMetadata:
    """
    Profile metadata with all required fields.
    
    Addresses requirement 5.1: Standardized profile file format with consistent naming conventions
    """
    profile_name: str
    created_date: str
    app_version: str
    parameter_count: int
    device_imei: Optional[str] = None
    device_version: Optional[str] = None
    checksum: Optional[str] = None
    format_version: str = "1.0"
    last_modified: Optional[str] = None
    created_by: Optional[str] = None
    description: Optional[str] = None
    
    @classmethod
    def create_default(cls, profile_name: str, parameter_count: int = 0) -> 'ProfileMetadata':
        """Create metadata with default values."""
        return cls(
            profile_name=profile_name,
            created_date=datetime.now().isoformat(),
            app_version="1.0.0",  # Should be populated from app config
            parameter_count=parameter_count,
            last_modified=datetime.now().isoformat()
        )


@dataclass
class ValidationInfo:
    """
    Information about validation status and history.
    """
    last_validated: Optional[str] = None
    validation_version: Optional[str] = None
    is_validated: bool = False
    validation_errors_count: int = 0
    validation_warnings_count: int = 0


@dataclass
class ProfileData:
    """
    Complete profile data with metadata and parameters.
    
    Addresses requirements:
    - 5.1: Standardized profile file format with consistent naming conventions
    - 5.2: Consistent structure handling for save and load operations
    """
    metadata: ProfileMetadata
    device_parameters: Dict[str, Any]
    validation_info: ValidationInfo = field(default_factory=ValidationInfo)
    format_version: str = "1.0"
    raw_sections: Optional[Dict[str, Dict[str, Any]]] = None  # For preserving original structure
    
    def get_parameter(self, parameter_name: str, default: Any = None) -> Any:
        """Get a parameter value with optional default."""
        return self.device_parameters.get(parameter_name, default)
    
    def set_parameter(self, parameter_name: str, value: Any) -> None:
        """Set a parameter value and update metadata."""
        self.device_parameters[parameter_name] = value
        self.metadata.parameter_count = len(self.device_parameters)
        self.metadata.last_modified = datetime.now().isoformat()
    
    def remove_parameter(self, parameter_name: str) -> bool:
        """Remove a parameter and return True if it existed."""
        if parameter_name in self.device_parameters:
            del self.device_parameters[parameter_name]
            self.metadata.parameter_count = len(self.device_parameters)
            self.metadata.last_modified = datetime.now().isoformat()
            return True
        return False
    
    def get_parameter_names(self) -> List[str]:
        """Get list of all parameter names."""
        return list(self.device_parameters.keys())
    
    def is_empty(self) -> bool:
        """Check if profile has no parameters."""
        return len(self.device_parameters) == 0
    
    def update_validation_info(self, validation_result: ValidationResult) -> None:
        """Update validation information based on validation result."""
        self.validation_info.last_validated = datetime.now().isoformat()
        self.validation_info.is_validated = validation_result.is_valid
        self.validation_info.validation_errors_count = len(validation_result.errors)
        self.validation_info.validation_warnings_count = len(validation_result.warnings)


# Additional data models for specific operations

@dataclass
class ProfileFileResult:
    """Result of profile file reading operation."""
    success: bool
    profile_data: Optional[ProfileData] = None
    error_message: Optional[str] = None
    validation_result: Optional[ValidationResult] = None


@dataclass
class WriteResult:
    """Result of profile file writing operation."""
    success: bool
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    backup_created: bool = False
    backup_path: Optional[str] = None


@dataclass
class AccessValidationResult:
    """Result of file access validation."""
    can_read: bool
    can_write: bool
    exists: bool
    error_message: Optional[str] = None


@dataclass
class BackupResult:
    """Result of backup operation."""
    success: bool
    backup_path: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ProcessingResult:
    """Result of parameter processing operation."""
    successful_parameters: Dict[str, Any]
    failed_parameters: List[Dict[str, Any]]
    partial_success: bool
    total_processed: int = 0
    
    def __post_init__(self):
        self.total_processed = len(self.successful_parameters) + len(self.failed_parameters)


@dataclass
class CompatibilityResult:
    """Result of compatibility checking."""
    is_compatible: bool
    version_supported: bool
    migration_required: bool
    migration_available: bool
    compatibility_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# Utility functions for working with data models

def create_validation_error(error_type: str, location: str, message: str, 
                          severity: str = 'error', suggestion: Optional[str] = None,
                          parameter_name: Optional[str] = None) -> ValidationError:
    """Helper function to create validation errors consistently."""
    return ValidationError(
        error_type=error_type,
        location=location,
        message=message,
        severity=severity,
        suggestion=suggestion,
        parameter_name=parameter_name
    )


def create_profile_data(profile_name: str, parameters: Dict[str, Any], 
                       device_imei: Optional[str] = None) -> ProfileData:
    """Helper function to create ProfileData with proper metadata."""
    metadata = ProfileMetadata.create_default(profile_name, len(parameters))
    if device_imei:
        metadata.device_imei = device_imei
    
    return ProfileData(
        metadata=metadata,
        device_parameters=parameters,
        validation_info=ValidationInfo()
    )