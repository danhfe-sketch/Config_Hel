"""
Validation result data models for the LT32 PRO Universal Profile System.

This module defines the data structures for representing validation results
throughout the system.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class ValidationResult:
    """
    Represents the result of a validation operation.
    """
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, error: str) -> None:
        """Add an error message to the result."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message to the result."""
        self.warnings.append(warning)
    
    def add_detail(self, key: str, value: Any) -> None:
        """Add a detail to the result."""
        self.details[key] = value
    
    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """
        Merge another validation result into this one.
        
        Args:
            other: Another ValidationResult to merge
            
        Returns:
            ValidationResult: New merged result
        """
        merged = ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            details={**self.details, **other.details}
        )
        return merged
    
    def has_errors(self) -> bool:
        """Check if this result has any errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if this result has any warnings."""
        return len(self.warnings) > 0
    
    def get_summary(self) -> str:
        """Get a summary string of the validation result."""
        if self.is_valid and not self.has_warnings():
            return "Validation passed"
        elif self.is_valid and self.has_warnings():
            return f"Validation passed with {len(self.warnings)} warning(s)"
        else:
            return f"Validation failed with {len(self.errors)} error(s)"
    
    def __str__(self) -> str:
        """String representation of the validation result."""
        lines = [self.get_summary()]
        
        if self.errors:
            lines.append("Errors:")
            for error in self.errors:
                lines.append(f"  - {error}")
        
        if self.warnings:
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
        
        return "\n".join(lines)