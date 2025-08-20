"""
Universal profile data models for the LT32 PRO Universal Profile System.

This module defines the main data structures for representing device profiles
and their associated metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
import json
from .validation_result import ValidationResult


@dataclass
class ProfileMetadata:
    """
    Metadata associated with a universal profile.
    """
    parameter_spec_version: str
    created_by: str = "LT32 PRO Configurator"
    device_model: str = "LT32 PRO"
    profile_format_version: str = "1.0"
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "parameter_spec_version": self.parameter_spec_version,
            "created_by": self.created_by,
            "device_model": self.device_model,
            "profile_format_version": self.profile_format_version,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProfileMetadata':
        """Create metadata from dictionary."""
        return cls(
            parameter_spec_version=data.get("parameter_spec_version", "unknown"),
            created_by=data.get("created_by", "LT32 PRO Configurator"),
            device_model=data.get("device_model", "LT32 PRO"),
            profile_format_version=data.get("profile_format_version", "1.0"),
            tags=data.get("tags", {})
        )


@dataclass
class ParameterValue:
    """
    Represents a parameter value with its metadata.
    """
    value: Any
    source: str = "user"  # "user", "device", "default"
    timestamp: Optional[datetime] = None
    validation_status: Optional[ValidationResult] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameter value to dictionary."""
        result = {
            "value": self.value,
            # "source": self.source,
            # "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
        
        if self.validation_status:
            result["validation_status"] = {
                "is_valid": self.validation_status.is_valid,
                "errors": self.validation_status.errors,
                "warnings": self.validation_status.warnings
            }
        
        return result
    
    def to_dict_for_save(self) -> Dict[str, Any]:
        """Convert parameter value to dictionary for saving to file (without runtime metadata)."""
        result = {
            "value": self.value
        }
        
        # Only include validation_status if it exists
        if self.validation_status:
            result["validation_status"] = {
                "is_valid": self.validation_status.is_valid,
                "errors": self.validation_status.errors,
                "warnings": self.validation_status.warnings
            }
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParameterValue':
        """Create parameter value from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except ValueError:
                timestamp = datetime.now()
        
        validation_status = None
        if "validation_status" in data:
            vs_data = data["validation_status"]
            validation_status = ValidationResult(
                is_valid=vs_data.get("is_valid", True),
                errors=vs_data.get("errors", []),
                warnings=vs_data.get("warnings", [])
            )
        
        return cls(
            value=data.get("value"),
            # source=data.get("source", "user"),
            # timestamp=timestamp,
            validation_status=validation_status
        )
    
    def set_validation_result(self, result: ValidationResult) -> None:
        """Set the validation result for this parameter value."""
        self.validation_status = result


@dataclass
class UniversalProfile:
    """
    Main data structure representing a complete device configuration profile.
    """
    name: str
    version: str
    created_at: datetime
    modified_at: datetime
    metadata: ProfileMetadata
    parameters: Dict[str, ParameterValue] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure timestamps are datetime objects
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.modified_at, str):
            self.modified_at = datetime.fromisoformat(self.modified_at)
    
    def to_dict(self, for_save: bool = False) -> Dict[str, Any]:
        """
        Convert profile to dictionary for serialization.
        
        Args:
            for_save: If True, omits runtime metadata fields from parameters
        """
        parameters_dict = {}
        for param_name, param_value in self.parameters.items():
            if for_save:
                parameters_dict[param_name] = param_value.to_dict_for_save()
            else:
                parameters_dict[param_name] = param_value.to_dict()
        
        return {
            "name": self.name,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "metadata": self.metadata.to_dict(),
            "parameters": parameters_dict
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UniversalProfile':
        """Create profile from dictionary."""
        # Parse timestamps
        created_at = datetime.now()
        modified_at = datetime.now()
        
        if "created_at" in data:
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except ValueError:
                pass
        
        if "modified_at" in data:
            try:
                modified_at = datetime.fromisoformat(data["modified_at"])
            except ValueError:
                pass
        
        # Parse metadata
        metadata = ProfileMetadata.from_dict(data.get("metadata", {}))
        
        # Parse parameters
        parameters = {}
        for param_name, param_data in data.get("parameters", {}).items():
            parameters[param_name] = ParameterValue.from_dict(param_data)
        
        return cls(
            name=data.get("name", "Unnamed Profile"),
            version=data.get("version", "1.0"),
            created_at=created_at,
            modified_at=modified_at,
            metadata=metadata,
            parameters=parameters
        )
    
    def get_parameter_value(self, param_name: str) -> Optional[Any]:
        """
        Get the value of a parameter.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            Optional[Any]: Parameter value or None if not found
        """
        param_value = self.parameters.get(param_name)
        return param_value.value if param_value else None
    
    def set_parameter_value(self, param_name: str, value: Any, source: str = "user") -> None:
        """
        Set the value of a parameter.
        
        Args:
            param_name: Name of the parameter
            value: Value to set
            source: Source of the value ("user", "device", "default")
        """
        if param_name in self.parameters:
            self.parameters[param_name].value = value
            self.parameters[param_name].source = source
            self.parameters[param_name].timestamp = datetime.now()
        else:
            self.parameters[param_name] = ParameterValue(
                value=value,
                source=source
            )
        
        self.modified_at = datetime.now()
    
    def get_parameter_info(self, param_name: str) -> Optional[ParameterValue]:
        """
        Get the complete parameter information.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            Optional[ParameterValue]: Parameter info or None if not found
        """
        return self.parameters.get(param_name)
    
    def validate(self, spec_parser=None) -> ValidationResult:
        """
        Validate the profile against parameter specifications.
        
        Args:
            spec_parser: Parameter specification parser (optional)
            
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(is_valid=True)
        
        if not self.name:
            result.add_error("Profile name is required")
        
        if not self.version:
            result.add_error("Profile version is required")
        
        # Validate individual parameters if spec_parser is provided
        if spec_parser:
            for param_name, param_value in self.parameters.items():
                param_spec = spec_parser.get_parameter_spec(param_name)
                if param_spec:
                    param_validation = param_spec.validate_value(param_value.value)
                    if not param_validation.is_valid:
                        for error in param_validation.errors:
                            result.add_error(f"Parameter {param_name}: {error}")
                    for warning in param_validation.warnings:
                        result.add_warning(f"Parameter {param_name}: {warning}")
                    
                    # Store validation result in parameter
                    param_value.set_validation_result(param_validation)
                else:
                    result.add_warning(f"No specification found for parameter: {param_name}")
        
        return result
    
    def get_parameters_by_source(self, source: str) -> Dict[str, ParameterValue]:
        """
        Get all parameters from a specific source.
        
        Args:
            source: Source to filter by ("user", "device", "default")
            
        Returns:
            Dict[str, ParameterValue]: Dictionary of parameters from the source
        """
        return {
            name: param_value
            for name, param_value in self.parameters.items()
            if param_value.source == source
        }
    
    def to_json(self, indent: int = 2) -> str:
        """
        Convert profile to JSON string.
        
        Args:
            indent: JSON indentation level
            
        Returns:
            str: JSON representation of the profile
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'UniversalProfile':
        """
        Create profile from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            UniversalProfile: Profile instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def clone(self, new_name: Optional[str] = None) -> 'UniversalProfile':
        """
        Create a copy of this profile.
        
        Args:
            new_name: Optional new name for the cloned profile
            
        Returns:
            UniversalProfile: Cloned profile
        """
        import time
        # Add a small delay to ensure different timestamps
        time.sleep(0.001)
        
        profile_dict = self.to_dict()
        
        if new_name:
            profile_dict["name"] = new_name
        
        # Reset timestamps for the clone
        now = datetime.now()
        profile_dict["created_at"] = now.isoformat()
        profile_dict["modified_at"] = now.isoformat()
        
        return self.from_dict(profile_dict)