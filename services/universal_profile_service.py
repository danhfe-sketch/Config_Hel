"""
Universal Profile Service for the LT32 PRO Universal Profile System.

This module provides the core service for creating, validating, and managing
universal profiles using parameter specifications.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from models.universal_profile import UniversalProfile, ProfileMetadata, ParameterValue
from models.validation_result import ValidationResult
from services.parameter_specification_parser import ParameterSpecificationParser
from services.profile_ui_populator import ProfileUIPopulator


class UniversalProfileService:
    """
    Service for managing universal profiles with parameter specification validation.
    
    This service handles profile creation from UI values and device responses,
    profile validation, file I/O operations, and profile migration.
    """
    
    def __init__(self, spec_parser: ParameterSpecificationParser):
        """
        Initialize the service with a parameter specification parser.
        
        Args:
            spec_parser: Parameter specification parser instance
        """
        self.spec_parser = spec_parser
        self.profile_ui_populator = ProfileUIPopulator(spec_parser)
    
    def create_profile_from_ui(self, ui_values: Dict[str, Any], profile_name: str) -> UniversalProfile:
        """
        Create a universal profile from UI field values.
        
        Args:
            ui_values: Dictionary of UI field values keyed by parameter name
            profile_name: Name for the new profile
            
        Returns:
            UniversalProfile: Created profile with UI values
        """
        now = datetime.now()
        
        # Create metadata
        metadata = ProfileMetadata(
            parameter_spec_version="1.0",  # TODO: Get from spec parser
            created_by="LT32 PRO Configurator",
            device_model="LT32 PRO",
            profile_format_version="1.0"
        )
        
        # Create profile
        profile = UniversalProfile(
            name=profile_name,
            version="1.0",
            created_at=now,
            modified_at=now,
            metadata=metadata
        )
        
        # Process UI values and create parameter values
        for param_name, value in ui_values.items():
            # Get parameter specification for validation
            param_spec = self.spec_parser.get_parameter_spec(param_name)
            
            if param_spec:
                # Create parameter value with validation
                param_value = ParameterValue(
                    value=value,
                    source="user",
                    timestamp=now,
                    is_modified=True
                )
                
                # Validate the value
                validation_result = param_spec.validate_value(value)
                param_value.set_validation_result(validation_result)
                
                profile.parameters[param_name] = param_value
            else:
                # Parameter not found in specifications - still include but mark as unknown
                param_value = ParameterValue(
                    value=value,
                    source="user",
                    timestamp=now,
                    is_modified=True
                )
                
                # Create a warning validation result
                validation_result = ValidationResult(
                    is_valid=True,
                    warnings=[f"Parameter '{param_name}' not found in specifications"]
                )
                param_value.set_validation_result(validation_result)
                
                profile.parameters[param_name] = param_value
        
        return profile
    
    def create_profile_from_device(self, device_responses: Dict[str, str], profile_name: str) -> UniversalProfile:
        """
        Create a universal profile from device response data.
        
        Args:
            device_responses: Dictionary of device responses keyed by parameter name
            profile_name: Name for the new profile
            
        Returns:
            UniversalProfile: Created profile with device values
        """
        now = datetime.now()
        
        # Create metadata
        metadata = ProfileMetadata(
            parameter_spec_version="1.0",  # TODO: Get from spec parser
            created_by="LT32 PRO Configurator",
            device_model="LT32 PRO",
            profile_format_version="1.0",
            tags={"source": "device"}
        )
        
        # Create profile
        profile = UniversalProfile(
            name=profile_name,
            version="1.0",
            created_at=now,
            modified_at=now,
            metadata=metadata
        )
        
        # Process device responses and create parameter values
        for param_name, response in device_responses.items():
            # Get parameter specification
            param_spec = self.spec_parser.get_parameter_spec(param_name)
            
            if param_spec:
                # Parse the device response using the parameter specification
                parsed_value = self._parse_device_response(param_spec, response)
                
                # Create parameter value
                param_value = ParameterValue(
                    value=parsed_value,
                    source="device",
                    timestamp=now,
                    is_modified=False
                )
                
                # Validate the parsed value
                validation_result = param_spec.validate_value(parsed_value)
                param_value.set_validation_result(validation_result)
                
                profile.parameters[param_name] = param_value
            else:
                # Parameter not found in specifications - store raw response
                param_value = ParameterValue(
                    value=response,
                    source="device",
                    timestamp=now,
                    is_modified=False
                )
                
                # Create a warning validation result
                validation_result = ValidationResult(
                    is_valid=True,
                    warnings=[f"Parameter '{param_name}' not found in specifications"]
                )
                param_value.set_validation_result(validation_result)
                
                profile.parameters[param_name] = param_value
        
        return profile
    
    def _parse_device_response(self, param_spec, response: str) -> Any:
        """
        Parse a device response according to parameter specification.
        """
        if not response:
            return param_spec.get_default_value()

        raw_value = response.strip()

        # For complex parameters with fields, parse into a dictionary
        if param_spec.fields:
            # Special handling for server_settings
            if param_spec.name == 'server_settings':
                result = {}
                parts = raw_value.split(':')[-1].split(',')
                
                port_field = None
                for field in param_spec.fields:
                    if field.name == 'port':
                        port_field = field
                        break

                if len(parts) >= 3 and port_field:
                    result['address'] = parts[1]
                    result['port'] = self._convert_field_value(port_field, parts[2])
                else:
                    result['address'] = ''
                    if port_field:
                        result['port'] = port_field.get_default_value()
                    else:
                        result['port'] = 0 # fallback default
                return result

            # Special handling for ignition_type due to its unique response format
            if param_spec.name == 'ignition_type':
                result = {}
                # Default ignition mode mapping based on response
                ignition_mode_value = 'Física (Physical)'
                if 'ACCLINE=0' in raw_value:
                    ignition_mode_value = 'Virtual por acelerômetro (Virtual by accelerometer)'
                # Note: Only include voltage fields if battery mode is active
                result['ignition_mode'] = ignition_mode_value
                return result

            # Extract the value part of the response (e.g., from "APN:val1,val2")
            if ':' in raw_value:
                raw_value = raw_value.split(':', 1)[-1].strip()
            
            parts = raw_value.split(',')
            provisional = {}
            for i, field in enumerate(param_spec.fields):
                if i < len(parts):
                    # Convert each part to the correct field type
                    provisional[field.name] = self._convert_field_value(field, parts[i])
                else:
                    provisional[field.name] = field.get_default_value()

            # Filter out fields that should not be visible given the current context
            visible_field_names = {f.name for f in param_spec.get_visible_fields(provisional)}
            filtered: Dict[str, Any] = {}
            for field in param_spec.fields:
                if field.visibility_condition is None or field.name in visible_field_names:
                    filtered[field.name] = provisional[field.name]
            return filtered

        # For simple parameters, extract the single value
        last_delim = max(raw_value.rfind('='), raw_value.rfind(':'))
        if last_delim != -1:
            raw_value = raw_value[last_delim + 1:].strip()
            
        return self._convert_and_map_value(param_spec, raw_value)

    def _convert_field_value(self, field, raw_value: str) -> Any:
        """Convert a raw field value to the appropriate type and map to options."""
        # First, convert to a Python type
        typed_value = raw_value
        if field.ui_element.value == "number_input":
            try:
                typed_value = int(raw_value)
            except (ValueError, TypeError):
                try:
                    typed_value = float(raw_value)
                except (ValueError, TypeError):
                    # For validation errors like port:0, we keep the value for now
                    typed_value = raw_value
        elif field.ui_element.value == "toggle_switch":
            typed_value = raw_value.lower() in ("true", "1", "on", "yes", "enabled")

        # Then, map to UI option string if applicable
        if field.options:
            if field.ui_element.value == "dropdown":
                try:
                    index = int(str(typed_value).strip())
                    # Clamp out-of-range indices to nearest valid option
                    if index < 0:
                        index = 0
                    if index >= len(field.options):
                        index = len(field.options) - 1
                    return field.options[index]
                except (ValueError, TypeError):
                    if typed_value in field.options:
                        return typed_value
            elif field.ui_element.value == "toggle_switch":
                # This mapping is for UI display, the validator should handle the boolean
                if typed_value is True and len(field.options) > 0:
                    return field.options[0]
                elif typed_value is False and len(field.options) > 1:
                    return field.options[1]
        
        return typed_value

    def _convert_and_map_value(self, param_spec, raw_value: str) -> Any:
        """Convert a raw parameter value to the appropriate type and map to UI options if needed."""
        # First, convert to a Python type (int, bool, etc.)
        typed_value = self._convert_simple_value(param_spec, raw_value)

        # Then, map this typed value to the corresponding UI option string if applicable
        if param_spec.options:
            if param_spec.ui_element and param_spec.ui_element.value == "dropdown":
                try:
                    # Device value is an index for the options list
                    index = int(str(typed_value).strip())
                    # Clamp out-of-range indices to nearest valid option
                    if index < 0:
                        index = 0
                    if index >= len(param_spec.options):
                        index = len(param_spec.options) - 1
                    return param_spec.options[index]
                except (ValueError, TypeError):
                    # If it's not an index, it might be the value itself
                    if typed_value in param_spec.options:
                        return typed_value
            
            elif param_spec.ui_element and param_spec.ui_element.value == "toggle_switch":
                # Map boolean to "Enabled" / "Disabled" based on options
                if typed_value is True and "Enabled" in param_spec.options:
                    return "Enabled"
                elif typed_value is False and "Disabled" in param_spec.options:
                    return "Disabled"

        # For other cases, or if mapping fails, return the raw value or the typed value
        # Let's return the typed_value, as it's more likely to be what validation expects if no options are matched
        return typed_value

    def _convert_simple_value(self, param_spec, raw_value: str) -> Any:
        """Convert a raw parameter value to its basic Python type."""
        if param_spec.ui_element and param_spec.ui_element.value == "number_input":
            try:
                return int(raw_value)
            except (ValueError, TypeError):
                try:
                    return float(raw_value)
                except (ValueError, TypeError):
                    return param_spec.get_default_value()
        elif param_spec.ui_element and param_spec.ui_element.value == "toggle_switch":
            return raw_value.lower() in ("true", "1", "on", "yes", "enabled")
        
        return raw_value
    
    def save_profile_to_file(self, profile: UniversalProfile, file_path: str) -> bool:
        """
        Save a profile to a JSON file using the ProfileFileHandler.
        
        Args:
            profile: Profile to save
            file_path: Path where to save the profile
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from services.profile_file_handler import ProfileFileHandler
            file_handler = ProfileFileHandler()
            
            result = file_handler.save_profile_to_file(profile, file_path)
            return result.success
            
        except Exception as e:
            # Log error in a real implementation
            print(f"Error saving profile to {file_path}: {e}")
            return False
    
    def load_profile_from_file(self, file_path: str) -> UniversalProfile:
        """
        Load a profile from a JSON file using the ProfileFileHandler.
        
        Args:
            file_path: Path to the profile file
            
        Returns:
            UniversalProfile: Loaded profile
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid
        """
        try:
            from services.profile_file_handler import ProfileFileHandler
            file_handler = ProfileFileHandler()
            
            profile, result = file_handler.load_profile_from_file(file_path)
            
            if not result.success:
                if "not found" in result.error_message:
                    raise FileNotFoundError(result.error_message)
                else:
                    raise ValueError(result.error_message)
            
            # Migrate profile if needed
            migrated_profile = self.migrate_profile(profile)
            
            return migrated_profile
            
        except (FileNotFoundError, ValueError):
            raise
        except Exception as e:
            raise ValueError(f"Error loading profile from {file_path}: {e}")
    
    def validate_profile(self, profile: UniversalProfile) -> ValidationResult:
        """
        Validate a profile against current parameter specifications.
        
        Args:
            profile: Profile to validate
            
        Returns:
            ValidationResult: Comprehensive validation result
        """
        result = ValidationResult(is_valid=True)
        
        # Basic profile validation
        if not profile.name:
            result.add_error("Profile name is required")
        
        if not profile.version:
            result.add_error("Profile version is required")
        
        # Validate individual parameters
        for param_name, param_value in profile.parameters.items():
            param_spec = self.spec_parser.get_parameter_spec(param_name)
            
            if param_spec:
                value_to_validate = param_value.value

                # If parameter has conditional fields, validate only visible fields
                if param_spec.fields and isinstance(value_to_validate, dict):
                    context = value_to_validate.copy()
                    visible_fields = {f.name for f in param_spec.get_visible_fields(context)}
                    # Filter out non-visible fields prior to validation
                    filtered_value = {k: v for k, v in value_to_validate.items() if k in visible_fields}
                    # Preserve original non-visible fields for storage but validate filtered
                    param_validation = param_spec.validate_value(filtered_value)
                else:
                    param_validation = param_spec.validate_value(value_to_validate)

                if not param_validation.is_valid:
                    for error in param_validation.errors:
                        result.add_error(f"Parameter '{param_name}': {error}")
                
                for warning in param_validation.warnings:
                    result.add_warning(f"Parameter '{param_name}': {warning}")
                
                # Update parameter's validation status
                param_value.set_validation_result(param_validation)
            else:
                # Parameter not found in current specifications
                result.add_warning(f"Parameter '{param_name}' not found in current specifications")
        
        # Check for missing required parameters
        all_param_names = self.spec_parser.get_all_parameters()
        for param_name in all_param_names:
            if param_name not in profile.parameters:
                param_spec = self.spec_parser.get_parameter_spec(param_name)
                if param_spec:
                    # Add default value for missing parameter
                    default_value = param_spec.get_default_value()
                    profile.set_parameter_value(param_name, default_value, "default")
                    result.add_warning(f"Added default value for missing parameter '{param_name}'")
        
        # Validate parameter dependencies and visibility conditions
        self._validate_parameter_dependencies(profile, result)
        
        return result
    
    def _validate_parameter_dependencies(self, profile: UniversalProfile, result: ValidationResult) -> None:
        """
        Validate parameter dependencies and visibility conditions.
        
        Args:
            profile: Profile to validate
            result: Validation result to update
        """
        # Create context for visibility checks
        context = {}
        for param_name, param_value in profile.parameters.items():
            context[param_name] = param_value.value
        
        # Check visibility conditions for all parameters
        for param_name, param_value in profile.parameters.items():
            param_spec = self.spec_parser.get_parameter_spec(param_name)
            if param_spec and not param_spec.is_visible(context):
                result.add_warning(f"Parameter '{param_name}' should not be visible with current values")
        
        # Check field visibility for complex parameters
        for param_name, param_value in profile.parameters.items():
            param_spec = self.spec_parser.get_parameter_spec(param_name)
            if param_spec and param_spec.fields and isinstance(param_value.value, dict):
                visible_fields = param_spec.get_visible_fields(param_value.value)
                visible_field_names = {field.name for field in visible_fields}
                
                for field_name in param_value.value.keys():
                    if field_name not in visible_field_names:
                        result.add_warning(f"Field '{field_name}' in parameter '{param_name}' should not be visible")
    
    def migrate_profile(self, profile: UniversalProfile) -> UniversalProfile:
        """
        Migrate a profile to the current format and specifications.
        
        Args:
            profile: Profile to migrate
            
        Returns:
            UniversalProfile: Migrated profile
        """
        # For now, this is a simple migration that ensures all current parameters
        # have values (using defaults for missing ones)
        
        migrated_profile = profile.clone()
        
        # Add missing parameters with default values (do not mark as modified)
        all_param_names = self.spec_parser.get_all_parameters()
        for param_name in all_param_names:
            if param_name not in migrated_profile.parameters:
                param_spec = self.spec_parser.get_parameter_spec(param_name)
                if param_spec:
                    default_value = param_spec.get_default_value()
                    migrated_profile.parameters[param_name] = ParameterValue(
                        value=default_value,
                        source="default",
                        is_modified=False
                    )

        # Clean up field visibility: remove fields that should not be visible
        for param_name, param_value in list(migrated_profile.parameters.items()):
            param_spec = self.spec_parser.get_parameter_spec(param_name)
            if not param_spec or not param_spec.fields:
                continue
            value = param_value.value
            if not isinstance(value, dict):
                continue
            # Determine which fields are visible based on current values
            visible_fields = {f.name for f in param_spec.get_visible_fields(value)}
            cleaned: Dict[str, Any] = {}
            for field in param_spec.fields:
                if field.visibility_condition is None:
                    # Always include non-conditional fields
                    if field.name in value:
                        cleaned[field.name] = value[field.name]
                else:
                    if field.name in visible_fields and field.name in value:
                        cleaned[field.name] = value[field.name]
            # Replace with cleaned value if different (do not mark as modified)
            if cleaned != value:
                pv = migrated_profile.parameters.get(param_name)
                if pv:
                    pv.value = cleaned
                else:
                    migrated_profile.parameters[param_name] = ParameterValue(
                        value=cleaned,
                        source="device",
                        is_modified=False
                    )
        
        # Update metadata to reflect migration
        migrated_profile.metadata.parameter_spec_version = "1.0"  # Current version
        migrated_profile.modified_at = datetime.now()
        
        return migrated_profile
    
    def get_profile_summary(self, profile: UniversalProfile) -> Dict[str, Any]:
        """
        Get a summary of profile information.
        
        Args:
            profile: Profile to summarize
            
        Returns:
            Dict[str, Any]: Profile summary information
        """
        total_params = len(profile.parameters)
        modified_params = len(profile.get_modified_parameters())
        device_params = len(profile.get_parameters_by_source("device"))
        user_params = len(profile.get_parameters_by_source("user"))
        default_params = len(profile.get_parameters_by_source("default"))
        
        # Count validation issues
        validation_errors = 0
        validation_warnings = 0
        
        for param_value in profile.parameters.values():
            if param_value.validation_status:
                validation_errors += len(param_value.validation_status.errors)
                validation_warnings += len(param_value.validation_status.warnings)
        
        return {
            "name": profile.name,
            "version": profile.version,
            "created_at": profile.created_at.isoformat(),
            "modified_at": profile.modified_at.isoformat(),
            "total_parameters": total_params,
            "modified_parameters": modified_params,
            "device_parameters": device_params,
            "user_parameters": user_params,
            "default_parameters": default_params,
            "validation_errors": validation_errors,
            "validation_warnings": validation_warnings,
            "metadata": profile.metadata.to_dict()
        }
    
    def compare_profiles(self, profile1: UniversalProfile, profile2: UniversalProfile) -> Dict[str, Any]:
        """
        Compare two profiles and return differences.
        
        Args:
            profile1: First profile to compare
            profile2: Second profile to compare
            
        Returns:
            Dict[str, Any]: Comparison results
        """
        differences = {
            "added_parameters": [],
            "removed_parameters": [],
            "changed_parameters": [],
            "unchanged_parameters": []
        }
        
        params1 = set(profile1.parameters.keys())
        params2 = set(profile2.parameters.keys())
        
        # Find added and removed parameters
        differences["added_parameters"] = list(params2 - params1)
        differences["removed_parameters"] = list(params1 - params2)
        
        # Find changed and unchanged parameters
        common_params = params1 & params2
        
        for param_name in common_params:
            value1 = profile1.get_parameter_value(param_name)
            value2 = profile2.get_parameter_value(param_name)
            
            if value1 != value2:
                differences["changed_parameters"].append({
                    "parameter": param_name,
                    "old_value": value1,
                    "new_value": value2
                })
            else:
                differences["unchanged_parameters"].append(param_name)
        
        return differences
    
    def extract_validated_ui_values(self, ui_elements: Dict[str, Any]) -> Tuple[Dict[str, Any], ValidationResult]:
        """
        Extract validated values from UI elements using ProfileUIPopulator.
        
        Args:
            ui_elements: Dictionary mapping parameter names to UI elements
            
        Returns:
            Tuple[Dict[str, Any], ValidationResult]: Extracted values and validation result
        """
        return self.profile_ui_populator.extract_validated_field_values(ui_elements)
    
    def apply_visibility_conditions_to_profile(self, profile: UniversalProfile, context: Dict[str, Any]) -> None:
        """
        Apply visibility conditions to a profile based on context values.
        
        Args:
            profile: UniversalProfile to apply visibility conditions to
            context: Current parameter values for evaluating conditions
        """
        # Create a mapping of parameter names to UI elements if needed
        # For now, we'll just validate the profile data integrity
        self.profile_ui_populator.validate_profile_data_integrity(profile)
    
    def get_field_dependencies_for_parameter(self, param_name: str) -> List[str]:
        """
        Get field dependencies for a parameter based on visibility conditions.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            List[str]: List of parameter names this parameter depends on
        """
        return self.profile_ui_populator.get_field_dependencies(param_name)
    
    def populate_ui_from_profile_data(self, profile: UniversalProfile, ui_elements: Dict[str, Any]) -> ValidationResult:
        """
        Populate UI elements with values from a profile using ProfileUIPopulator.
        
        Args:
            profile: UniversalProfile containing parameter values
            ui_elements: Dictionary mapping parameter names to UI elements
            
        Returns:
            ValidationResult: Result of the population operation
        """
        return self.profile_ui_populator.populate_ui_from_profile(profile, ui_elements)
