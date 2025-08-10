"""
Operation result data models for the LT32 PRO Universal Profile System.

This module defines the data structures for representing the results of
profile operations like loading from device, saving to device, etc.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from .universal_profile import UniversalProfile


class OperationType(Enum):
    """Enumeration of profile operation types."""
    LOAD_FROM_DEVICE = "load_from_device"
    SAVE_TO_DEVICE = "save_to_device"
    LOAD_FROM_FILE = "load_from_file"
    SAVE_TO_FILE = "save_to_file"
    VALIDATE_PROFILE = "validate_profile"
    MIGRATE_PROFILE = "migrate_profile"


@dataclass
class ParameterOperationResult:
    """
    Represents the result of an operation on a single parameter.
    """
    parameter_name: str
    success: bool
    value: Optional[Any] = None
    error_message: Optional[str] = None
    warning_message: Optional[str] = None
    duration_seconds: float = 0.0
    retry_count: int = 0
    device_response: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "parameter_name": self.parameter_name,
            "success": self.success,
            "value": self.value,
            "error_message": self.error_message,
            "warning_message": self.warning_message,
            "duration_seconds": self.duration_seconds,
            "retry_count": self.retry_count,
            "device_response": self.device_response
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParameterOperationResult':
        """Create from dictionary representation."""
        return cls(
            parameter_name=data["parameter_name"],
            success=data["success"],
            value=data.get("value"),
            error_message=data.get("error_message"),
            warning_message=data.get("warning_message"),
            duration_seconds=data.get("duration_seconds", 0.0),
            retry_count=data.get("retry_count", 0),
            device_response=data.get("device_response")
        )


@dataclass
class ProfileOperationResult:
    """
    Represents the result of a complete profile operation.
    """
    operation_type: OperationType
    success: bool
    profile: Optional[UniversalProfile] = None
    parameters_processed: int = 0
    parameters_successful: int = 0
    parameters_failed: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    parameter_results: List[ParameterOperationResult] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.started_at is None:
            self.started_at = datetime.now()
        if self.completed_at is None:
            self.completed_at = datetime.now()
    
    def add_error(self, error: str) -> None:
        """Add an error message to the result."""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message to the result."""
        self.warnings.append(warning)
    
    def add_detail(self, key: str, value: Any) -> None:
        """Add a detail to the result."""
        self.details[key] = value
    
    def add_parameter_result(self, param_result: ParameterOperationResult) -> None:
        """Add a parameter operation result."""
        self.parameter_results.append(param_result)
        self.parameters_processed += 1
        
        if param_result.success:
            self.parameters_successful += 1
        else:
            self.parameters_failed += 1
            if param_result.error_message:
                self.add_error(f"Parameter {param_result.parameter_name}: {param_result.error_message}")
        
        if param_result.warning_message:
            self.add_warning(f"Parameter {param_result.parameter_name}: {param_result.warning_message}")
    
    def get_failed_parameters(self) -> List[ParameterOperationResult]:
        """Get list of failed parameter operations."""
        return [result for result in self.parameter_results if not result.success]
    
    def get_successful_parameters(self) -> List[ParameterOperationResult]:
        """Get list of successful parameter operations."""
        return [result for result in self.parameter_results if result.success]
    
    def get_parameters_with_warnings(self) -> List[ParameterOperationResult]:
        """Get list of parameter operations with warnings."""
        return [result for result in self.parameter_results if result.warning_message]
    
    def get_success_rate(self) -> float:
        """Get the success rate as a percentage."""
        if self.parameters_processed == 0:
            return 0.0
        return (self.parameters_successful / self.parameters_processed) * 100.0
    
    def has_errors(self) -> bool:
        """Check if this result has any errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if this result has any warnings."""
        return len(self.warnings) > 0
    
    def is_partial_success(self) -> bool:
        """Check if this is a partial success (some parameters succeeded, some failed)."""
        return self.parameters_successful > 0 and self.parameters_failed > 0
    
    def get_summary(self) -> str:
        """Get a summary string of the operation result."""
        operation_name = self.operation_type.value.replace("_", " ").title()
        
        if self.is_partial_success():
            return f"{operation_name} partially completed ({self.parameters_successful}/{self.parameters_processed} parameters successful)"
        elif self.success and not self.has_warnings():
            return f"{operation_name} completed successfully ({self.parameters_successful}/{self.parameters_processed} parameters)"
        elif self.success and self.has_warnings():
            return f"{operation_name} completed with warnings ({self.parameters_successful}/{self.parameters_processed} parameters, {len(self.warnings)} warnings)"
        else:
            return f"{operation_name} failed ({self.parameters_failed}/{self.parameters_processed} parameters failed)"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "operation_type": self.operation_type.value,
            "success": self.success,
            "profile": self.profile.to_dict() if self.profile else None,
            "parameters_processed": self.parameters_processed,
            "parameters_successful": self.parameters_successful,
            "parameters_failed": self.parameters_failed,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details,
            "parameter_results": [result.to_dict() for result in self.parameter_results],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProfileOperationResult':
        """Create from dictionary representation."""
        # Parse timestamps
        started_at = None
        completed_at = None
        
        if data.get("started_at"):
            try:
                started_at = datetime.fromisoformat(data["started_at"])
            except ValueError:
                pass
        
        if data.get("completed_at"):
            try:
                completed_at = datetime.fromisoformat(data["completed_at"])
            except ValueError:
                pass
        
        # Parse profile
        profile = None
        if data.get("profile"):
            profile = UniversalProfile.from_dict(data["profile"])
        
        # Parse parameter results
        parameter_results = []
        for result_data in data.get("parameter_results", []):
            parameter_results.append(ParameterOperationResult.from_dict(result_data))
        
        return cls(
            operation_type=OperationType(data["operation_type"]),
            success=data["success"],
            profile=profile,
            parameters_processed=data.get("parameters_processed", 0),
            parameters_successful=data.get("parameters_successful", 0),
            parameters_failed=data.get("parameters_failed", 0),
            duration_seconds=data.get("duration_seconds", 0.0),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            details=data.get("details", {}),
            parameter_results=parameter_results,
            started_at=started_at,
            completed_at=completed_at
        )
    
    def __str__(self) -> str:
        """String representation of the operation result."""
        lines = [self.get_summary()]
        
        if self.duration_seconds > 0:
            lines.append(f"Duration: {self.duration_seconds:.2f} seconds")
        
        if self.errors:
            lines.append("Errors:")
            for error in self.errors:
                lines.append(f"  - {error}")
        
        if self.warnings:
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
        
        return "\n".join(lines)