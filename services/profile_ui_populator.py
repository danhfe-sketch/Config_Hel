"""
Profile UI Populator Service for the LT32 PRO Universal Profile System.

This module provides functionality to populate UI fields from profile data,
extract validated field values, and handle parameter visibility conditions
and field dependencies.
"""

from typing import Dict, Any, List, Optional, Tuple
from models.universal_profile import UniversalProfile, ParameterValue
from models.validation_result import ValidationResult
from services.parameter_specification_parser import ParameterSpecificationParser
from services.parameter_specification import get_parameter_specification, get_parameter_by_name
from ui.parameter_ui_element_factory import ParameterUIElementFactory, UIElementConfig
import re


class ProfileUIPopulator:
    """
    Service for populating UI fields from profile data with validation and 
    conditional visibility support.
    """
    
    def __init__(self, spec_parser: ParameterSpecificationParser):
        """
        Initialize the ProfileUIPopulator with a parameter specification parser.
        
        Args:
            spec_parser: Parameter specification parser instance
        """
        self.spec_parser = spec_parser
        self.ui_element_factory = ParameterUIElementFactory(None)  # No i18n needed for validation
        
    def populate_ui_from_profile(self, profile: UniversalProfile, ui_elements: Dict[str, Any]) -> ValidationResult:
        """
        Populate UI elements with values from a profile.
        
        Args:
            profile: UniversalProfile containing parameter values
            ui_elements: Dictionary mapping parameter names to UI elements
            
        Returns:
            ValidationResult: Result of the population operation
        """
        result = ValidationResult(is_valid=True)
        
        # Get all parameter specifications
        param_specs = self.spec_parser.parse_specifications()
        
        # For each parameter in the profile, populate the corresponding UI element
        for param_name, param_value in profile.parameters.items():
            if param_name in ui_elements:
                ui_element = ui_elements[param_name]
                spec = param_specs.get(param_name)
                
                if spec and ui_element:
                    # Set the value in the UI element
                    try:
                        ui_element.set_value(param_value.value)
                    except Exception as e:
                        result.add_error(f"Failed to set value for {param_name}: {str(e)}")
                        
                    # Validate the value
                    if not ui_element.validate():
                        error_msg = ui_element.get_validation_error()
                        if error_msg:
                            result.add_error(f"Validation failed for {param_name}: {error_msg}")
                            
        return result
    
    def extract_validated_field_values(self, ui_elements: Dict[str, Any]) -> Tuple[Dict[str, Any], ValidationResult]:
        """
        Extract validated values from UI elements.
        
        Args:
            ui_elements: Dictionary mapping parameter names to UI elements
            
        Returns:
            Tuple[Dict[str, Any], ValidationResult]: Extracted values and validation result
        """
        values = {}
        result = ValidationResult(is_valid=True)
        
        # Extract values from all UI elements
        for param_name, ui_element in ui_elements.items():
            try:
                # Get the value from the UI element
                value = ui_element.get_value()
                
                # Only include non-empty values in the profile
                if value is not None and str(value).strip() != '':
                    values[param_name] = value
                    
                    # Validate the value only if it's not empty
                    if not ui_element.validate():
                        error_msg = ui_element.get_validation_error()
                        if error_msg:
                            result.add_error(f"Validation failed for {param_name}: {error_msg}")
                else:
                    # For empty values, don't validate and don't include in profile
                    # This prevents validation errors for optional empty fields
                    pass
                        
            except Exception as e:
                result.add_error(f"Failed to extract value from {param_name}: {str(e)}")
                
        return values, result
    
    def apply_visibility_conditions(self, ui_elements: Dict[str, Any], context: Dict[str, Any]) -> None:
        """
        Apply visibility conditions to UI elements based on context values.
        
        Args:
            ui_elements: Dictionary mapping parameter names to UI elements
            context: Current parameter values for evaluating conditions
        """
        # Get all parameter specifications
        param_specs = self.spec_parser.parse_specifications()
        
        # Apply visibility conditions for each parameter
        for param_name, ui_element in ui_elements.items():
            spec = param_specs.get(param_name)
            if spec and spec.visibility_condition:
                # Check if the parameter should be visible
                is_visible = self._evaluate_visibility_condition(spec.visibility_condition, context)
                ui_element.set_visibility(is_visible)
    
    def _evaluate_visibility_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a visibility condition against context values.
        
        Args:
            condition: Visibility condition string (e.g., "field_name == 'value'")
            context: Current parameter values
            
        Returns:
            bool: True if condition is met, False otherwise
        """
        try:
            # Simple condition parsing: "field_name == 'value'" or "field_name == true"
            if "==" in condition:
                field_name, expected_value = condition.split("==")
                field_name = field_name.strip()
                expected_value = expected_value.strip().strip("'\"")
                
                # Convert expected value to appropriate type
                if expected_value.lower() == "true":
                    expected_value = True
                elif expected_value.lower() == "false":
                    expected_value = False
                elif expected_value.isdigit():
                    expected_value = int(expected_value)
                    
                # Get actual value from context
                actual_value = context.get(field_name)
                
                # Compare values
                return actual_value == expected_value
                
        except Exception:
            # If parsing fails, default to visible
            pass
            
        return True
    
    def get_field_dependencies(self, param_name: str) -> List[str]:
        """
        Get field dependencies for a parameter based on visibility conditions.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            List[str]: List of parameter names this parameter depends on
        """
        dependencies = []
        
        # Get parameter specification
        param_spec = self.spec_parser.get_parameter_spec(param_name)
        if not param_spec:
            return dependencies
            
        # Check main parameter visibility condition
        if param_spec.visibility_condition:
            dependency = self._extract_dependency_from_condition(param_spec.visibility_condition)
            if dependency:
                dependencies.append(dependency)
                
        # Check field-level visibility conditions for complex parameters
        if param_spec.fields:
            for field in param_spec.fields:
                if field.visibility_condition:
                    dependency = self._extract_dependency_from_condition(field.visibility_condition)
                    if dependency and dependency not in dependencies:
                        dependencies.append(dependency)
                        
        return dependencies
    
    def _extract_dependency_from_condition(self, condition: str) -> Optional[str]:
        """
        Extract dependency parameter name from a visibility condition.
        
        Args:
            condition: Visibility condition string
            
        Returns:
            Optional[str]: Dependency parameter name or None
        """
        try:
            # Extract field name from condition like "field_name == 'value'"
            if "==" in condition:
                field_name = condition.split("==")[0].strip()
                return field_name
        except Exception:
            pass
        return None
    
    def create_ui_element_configs_from_profile(self, profile: UniversalProfile) -> Dict[str, UIElementConfig]:
        """
        Create UI element configurations from profile data.
        
        Args:
            profile: UniversalProfile to create configurations from
            
        Returns:
            Dict[str, UIElementConfig]: UI element configurations
        """
        configs = {}
        param_specs = self.spec_parser.parse_specifications()
        
        # Create UI element configuration for each parameter in the profile
        for param_name, param_value in profile.parameters.items():
            spec = param_specs.get(param_name)
            if spec:
                # Create basic UI element configuration
                config = UIElementConfig(
                    element_type=spec.ui_element.value if spec.ui_element else "text_input",
                    label=spec.label,
                    default_value=param_value.value,
                    options=spec.options,
                    unit=spec.unit
                )
                configs[param_name] = config
                
        return configs
    
    def validate_profile_data_integrity(self, profile: UniversalProfile) -> ValidationResult:
        """
        Validate the integrity of profile data against parameter specifications.
        
        Args:
            profile: UniversalProfile to validate
            
        Returns:
            ValidationResult: Result of the validation
        """
        result = ValidationResult(is_valid=True)
        
        # Validate each parameter in the profile
        for param_name, param_value in profile.parameters.items():
            validation_result = self.spec_parser.validate_parameter_value(param_name, param_value.value)
            if not validation_result.is_valid:
                result.merge(validation_result)
                
        return result
    
    def map_profile_to_ui_structure(self, profile: UniversalProfile) -> Dict[str, Any]:
        """
        Map profile data to UI structure format.
        
        Args:
            profile: UniversalProfile to map
            
        Returns:
            Dict[str, Any]: UI structure mapping
        """
        ui_structure = {}
        
        # Map each parameter to UI structure
        for param_name, param_value in profile.parameters.items():
            # For complex parameters with fields, organize as nested structure
            if isinstance(param_value.value, dict):
                ui_structure[param_name] = param_value.value
            else:
                # For simple parameters, use direct value
                ui_structure[param_name] = param_value.value
                
        return ui_structure
    
    def update_ui_elements_from_profile(self, profile: UniversalProfile, section_widgets: Dict[str, Any]) -> ValidationResult:
        """
        Update UI elements in section widgets with values from a profile.
        
        Args:
            profile: UniversalProfile containing parameter values
            section_widgets: Section widgets containing parameter UI elements
            
        Returns:
            ValidationResult: Result of the update operation
        """
        result = ValidationResult(is_valid=True)
        updated_count = 0
        
        # Convert profile parameters to the format expected by UI
        # Group individual field parameters into complex parameter structures
        grouped_params = {}
        
        # Process each profile parameter
        for param_key, param_value in profile.parameters.items():
            # Parse string dictionary values back to actual dictionaries
            processed_value = self._parse_parameter_value(param_value.value)
            
            # Split the parameter key to identify section, parameter, and field
            parts = param_key.split('.')
            if len(parts) >= 3:  # section.parameter.field format
                section_name = parts[0]
                param_name = parts[1]
                field_name = parts[2]
                
                # Create the grouped parameter key
                grouped_key = f"{section_name}.{param_name}"
                
                # Initialize the grouped parameter if it doesn't exist
                if grouped_key not in grouped_params:
                    from models.universal_profile import ParameterValue
                    grouped_params[grouped_key] = ParameterValue(value={}, source=param_value.source)
                
                # Add the field value to the grouped parameter
                grouped_params[grouped_key].value[field_name] = processed_value
            else:
                # For simple parameters, if processed_value is a dict containing the field
                # matching the parameter name (common when a single-field dict was serialized),
                # extract the inner value so UI receives the raw value (e.g., '59') instead of {'odometer': '59'}.
                from models.universal_profile import ParameterValue
                # Determine the simple parameter name (last segment)
                simple_name = param_key.split('.')[-1] if param_key else None
                if isinstance(processed_value, dict) and simple_name and simple_name in processed_value and len(processed_value) == 1:
                    extracted_value = processed_value[simple_name]
                    grouped_params[param_key] = ParameterValue(value=extracted_value, source=param_value.source)
                else:
                    grouped_params[param_key] = ParameterValue(value=processed_value, source=param_value.source)
        
        # Update each section's parameters
        for section_name, section_widget in section_widgets.items():
            if hasattr(section_widget, 'parameters'):
                for param_name, param_widget in section_widget.parameters.items():
                    # Find corresponding parameter in grouped parameters
                    full_param_name = f"{section_name}.{param_name}"
                    profile_param = grouped_params.get(full_param_name) or grouped_params.get(param_name)
                    
                    if profile_param and param_widget:
                        try:
                            # Set value based on widget type
                            if param_widget.widget_type == 'simple':
                                if 'main' in param_widget.ui_elements:
                                    param_widget.ui_elements['main'].set_value(profile_param.value)
                                    updated_count += 1

                            elif param_widget.widget_type == 'complex' and isinstance(profile_param.value, dict):
                                # Set values for each field
                                for field_name, field_value in profile_param.value.items():
                                    if field_name in param_widget.ui_elements:
                                        param_widget.ui_elements[field_name].set_value(field_value)
                                        updated_count += 1

                        except Exception as e:
                            error_msg = f"Failed to update {full_param_name}: {str(e)}"
                            result.add_error(error_msg)
                            print(f"ERROR: {error_msg}")
        
        # Log successful update
        if updated_count > 0:
            print(f"INFO: Successfully updated {updated_count} UI parameters from profile")
            
        return result
    
    def _parse_parameter_value(self, value):
        """
        Parse parameter values that might be stored as string representations of dictionaries.
        
        Args:
            value: The parameter value to parse
            
        Returns:
            The parsed value (dict if it was a string representation, otherwise original value)
        """
        if isinstance(value, str):
            # Check if this looks like a string representation of a dictionary
            if value.startswith('{') and value.endswith('}'):
                try:
                    # Try to safely evaluate the string as a Python literal
                    import ast
                    parsed_value = ast.literal_eval(value)
                    return parsed_value
                except (ValueError, SyntaxError):
                    # If parsing fails, return the original string
                    return value
            else:
                # Regular string value
                return value
        else:
            # Non-string value, return as-is
            return value