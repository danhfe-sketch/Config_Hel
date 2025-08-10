"""
Parameter specification data models for the LT32 PRO Universal Profile System.

This module defines the data structures for representing parameter specifications
parsed from the Parameter UI List markdown file.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re
from enum import Enum


class UIElementType(Enum):
    """Enumeration of supported UI element types."""
    TEXT_INPUT = "text_input"
    NUMBER_INPUT = "number_input"
    DROPDOWN = "dropdown"
    TOGGLE_SWITCH = "toggle_switch"
    SLIDER = "slider"


@dataclass
class ParameterField:
    """Represents a single field within a parameter configuration."""
    name: str
    label: str
    ui_element: UIElementType
    validation: Optional[str] = None
    unit: Optional[str] = None
    options: Optional[List[str]] = None
    visibility_condition: Optional[str] = None
    
    def validate_value(self, value: Any) -> bool:
        """
        Validate a value against this field's validation rules.
        
        Args:
            value: The value to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Check dropdown options first
        if self.ui_element == UIElementType.DROPDOWN and self.options:
            # Allow either the display string or a numeric index from device
            # Accept ints or numeric strings as indices
            try:
                idx = int(str(value).strip())
                return 0 <= idx < len(self.options)
            except (ValueError, TypeError):
                return str(value) in self.options
            
        # Check validation rules for other types
        if self.validation is None:
            return True
            
        # Basic validation logic - can be extended
        if self.ui_element == UIElementType.NUMBER_INPUT and self.validation:
            try:
                validation_text = self.validation.strip()
                # Case 1: direct hyphenated range like "1-65535"
                hyphen_match = re.match(r"^\s*(-?\d+)\s*-\s*(-?\d+)\s*$", validation_text)
                if hyphen_match:
                    min_val, max_val = int(hyphen_match.group(1)), int(hyphen_match.group(2))
                    return min_val <= int(value) <= max_val

                # Case 2: prose containing two numbers, e.g. "Must be a number between 1 and 65535."
                numbers = re.findall(r"-?\d+", validation_text)
                if len(numbers) >= 2:
                    min_val, max_val = int(numbers[0]), int(numbers[1])
                    # ensure ordering in case they appear reversed
                    if min_val > max_val:
                        min_val, max_val = max_val, min_val
                    return min_val <= int(value) <= max_val

                # Case 3: single numeric equality (rare)
                if len(numbers) == 1:
                    return int(value) == int(numbers[0])

                # If no numbers found, consider it valid (no enforceable rule)
                return True
            except (ValueError, TypeError):
                return False
            
        return True
    
    def get_default_value(self) -> Any:
        """Get the default value for this field."""
        if self.ui_element == UIElementType.TOGGLE_SWITCH:
            return False
        elif self.ui_element == UIElementType.NUMBER_INPUT:
            return 0
        elif self.ui_element == UIElementType.DROPDOWN and self.options:
            return self.options[0]
        else:
            return ""
    
    def is_visible(self, context: Dict[str, Any]) -> bool:
        """
        Check if this field should be visible given the current context.
        
        Args:
            context: Dictionary of current field values
            
        Returns:
            bool: True if field should be visible
        """
        if not self.visibility_condition:
            return True
            
        # Simple visibility condition parsing
        # Format: "field_name == 'value'" or "field_name == true"
        try:
            if "==" in self.visibility_condition:
                field_name, expected_value = self.visibility_condition.split("==")
                field_name = field_name.strip()
                expected_value = expected_value.strip().strip("'\"")
                
                if expected_value.lower() == "true":
                    expected_value = True
                elif expected_value.lower() == "false":
                    expected_value = False
                    
                return context.get(field_name) == expected_value
        except Exception:
            # If parsing fails, default to visible
            pass
            
        return True


@dataclass
class ParameterCommands:
    """Represents the device commands associated with a parameter."""
    set_command: Optional[str] = None
    read_command: Optional[str] = None
    set_physical: Optional[str] = None
    set_accelerometer: Optional[str] = None
    set_battery: Optional[str] = None
    set_level: Optional[str] = None
    read_level: Optional[str] = None
    
    def format_set_command(self, values: Dict[str, Any]) -> Optional[str]:
        """
        Format the set command with the provided values.
        
        Args:
            values: Dictionary of field values to substitute
            
        Returns:
            Optional[str]: Formatted command or None if no set command
        """
        if not self.set_command:
            return None
            
        command = self.set_command
        
        # Replace placeholders with actual values
        for key, value in values.items():
            placeholder = f"<{key}>"
            if placeholder in command:
                command = command.replace(placeholder, str(value))
                
        return command
    
    def parse_read_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse a device response for read commands.
        
        Args:
            response: Raw device response string
            
        Returns:
            Optional[Dict[str, Any]]: Parsed values or None if parsing fails
        """
        # Basic response parsing - can be extended based on actual device responses
        if not response:
            return None
            
        # Remove common prefixes/suffixes
        response = response.strip().rstrip('#')
        
        # Split by comma for multi-value responses
        parts = response.split(',')
        
        # Return as dictionary with indexed keys for now
        # This would need to be customized based on actual response formats
        result = {}
        for i, part in enumerate(parts):
            result[f"value_{i}"] = part.strip()
            
        return result


@dataclass
class ParameterSpec:
    """
    Represents a complete parameter specification from the Parameter UI List.
    """
    name: str
    label: str
    section: str
    description: Optional[str] = None
    ui_element: Optional[UIElementType] = None
    validation: Optional[str] = None
    unit: Optional[str] = None
    options: Optional[List[str]] = None
    visibility_condition: Optional[str] = None
    commands: ParameterCommands = field(default_factory=ParameterCommands)
    fields: Optional[List[ParameterField]] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Convert string ui_element to enum if needed
        if isinstance(self.ui_element, str):
            try:
                self.ui_element = UIElementType(self.ui_element)
            except ValueError:
                self.ui_element = None
    
    def validate_value(self, value: Any) -> 'ValidationResult':
        """
        Validate a value against this parameter's validation rules.
        
        Args:
            value: The value to validate
            
        Returns:
            ValidationResult: Result of validation
        """
        from .validation_result import ValidationResult
        
        errors = []
        warnings = []
        
        # If this is a complex parameter with fields, validate each field
        if self.fields:
            if not isinstance(value, dict):
                errors.append(f"Parameter {self.name} expects a dictionary value")
                return ValidationResult(False, errors, warnings)

            # If there is an 'enabled' field and it is false, skip validating other fields
            enabled_val = value.get('enabled')
            enabled_bool = None
            if isinstance(enabled_val, str):
                enabled_bool = enabled_val.strip().lower() in ("true", "1", "on", "yes", "enabled")
            elif isinstance(enabled_val, (int, bool)):
                enabled_bool = bool(enabled_val)

            for field in self.fields:
                # Always validate the 'enabled' field itself if present
                if field.name != 'enabled' and enabled_bool is False:
                    continue
                field_value = value.get(field.name)
                if field_value is not None and not field.validate_value(field_value):
                    errors.append(f"Invalid value for field {field.name}: {field_value}")
        else:
            # Simple parameter validation
            if self.validation:
                if self.ui_element == UIElementType.NUMBER_INPUT:
                    try:
                        if "-" in self.validation:
                            min_val, max_val = map(int, self.validation.split("-"))
                            if not (min_val <= int(value) <= max_val):
                                errors.append(f"Value {value} not in range {min_val}-{max_val}")
                    except (ValueError, TypeError):
                        errors.append(f"Invalid numeric value: {value}")
                        
            if self.options and str(value) not in self.options:
                errors.append(f"Value {value} not in allowed options: {self.options}")
        
        return ValidationResult(len(errors) == 0, errors, warnings)
    
    def get_default_value(self) -> Any:
        """Get the default value for this parameter."""
        if self.fields:
            # For complex parameters, return default values for all fields
            defaults = {}
            for field in self.fields:
                defaults[field.name] = field.get_default_value()
            return defaults
        else:
            # For simple parameters
            if self.ui_element == UIElementType.TOGGLE_SWITCH:
                return False
            elif self.ui_element == UIElementType.NUMBER_INPUT:
                return 0
            elif self.ui_element == UIElementType.DROPDOWN and self.options:
                return self.options[0]
            else:
                return ""
    
    def is_visible(self, context: Dict[str, Any]) -> bool:
        """
        Check if this parameter should be visible given the current context.
        
        Args:
            context: Dictionary of current parameter values
            
        Returns:
            bool: True if parameter should be visible
        """
        if not self.visibility_condition:
            return True
            
        # Simple visibility condition parsing
        try:
            if "==" in self.visibility_condition:
                field_name, expected_value = self.visibility_condition.split("==")
                field_name = field_name.strip()
                expected_value = expected_value.strip().strip("'\"")
                
                if expected_value.lower() == "true":
                    expected_value = True
                elif expected_value.lower() == "false":
                    expected_value = False
                    
                return context.get(field_name) == expected_value
        except Exception:
            # If parsing fails, default to visible
            pass
            
        return True
    
    def get_visible_fields(self, context: Dict[str, Any]) -> List[ParameterField]:
        """
        Get the list of fields that should be visible given the current context.
        
        Args:
            context: Dictionary of current field values
            
        Returns:
            List[ParameterField]: List of visible fields
        """
        if not self.fields:
            return []
            
        visible_fields = []
        for field in self.fields:
            if field.is_visible(context):
                visible_fields.append(field)
                
        return visible_fields