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
from services.parameter_processor import ParameterProcessor


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
        self.parameter_processor = ParameterProcessor()
    
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
                    timestamp=now
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
                    timestamp=now
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
                
                # Apply parameter processing for clean display (Requirements 3.1, 3.2, 3.3, 3.5)
                processed_value = self._apply_parameter_processing(param_name, parsed_value, response)
                
                # Create parameter value with processed value
                param_value = ParameterValue(
                    value=processed_value,
                    source="device",
                    timestamp=now
                )
                
                # Validate the processed value
                validation_result = param_spec.validate_value(processed_value)
                param_value.set_validation_result(validation_result)
                
                profile.parameters[param_name] = param_value
            else:
                # Parameter not found in specifications - apply processing and store
                processed_value = self._apply_parameter_processing(param_name, response, response)
                
                param_value = ParameterValue(
                    value=processed_value,
                    source="device",
                    timestamp=now
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

    def _clean_time_parameter_field(self, field, raw_value: str) -> str:
        """
        Clean time parameter field values to show only numeric values.
        
        Args:
            field: Parameter field specification
            raw_value: Raw field value from device (e.g., '60s' or 'ACC OFF:120s')
            
        Returns:
            Cleaned value for time parameters, original value for others
        """
        if not isinstance(raw_value, str):
            return raw_value
        
        # Define time parameter field names that need cleaning
        time_field_names = [
            'moving_time', 'stopped_time',
            'moving_heartbeat', 'stopped_heartbeat',
            'sleep_time',
            'detection_time', 'speed_detection_time',
            'power_detection_time',
            'min_charge_time',
            'jammer_confirmation_time'
        ]
        
        # Check if this field needs time parameter cleaning
        if hasattr(field, 'name') and field.name in time_field_names:
            cleaned_value = self._extract_numeric_value_from_time_string(raw_value)
            print(f"DEBUG: Time parameter field cleaning - {field.name}: '{raw_value}' -> '{cleaned_value}'")
            return cleaned_value
        
        return raw_value
    
    def _extract_numeric_value_from_time_string(self, time_string: str) -> str:
        """
        Extract numeric value from time parameter strings.
        
        Examples:
        - "60s" -> "60"
        - "ACC OFF:120s" -> "120"
        - "180" -> "180"
        
        Args:
            time_string: Time string that may contain units and prefixes
            
        Returns:
            str: Numeric value only
        """
        if not time_string:
            return ""
        
        # Extract all digits from the string
        import re
        digits = re.findall(r'\d+', str(time_string))
        
        # Return the last number found (handles cases like "ACC OFF:120s")
        return digits[-1] if digits else ""

    def _convert_field_value(self, field, raw_value: str) -> Any:
        """Convert a raw field value to the appropriate type and map to options."""
        # Apply time parameter cleaning for time-related fields
        cleaned_value = self._clean_time_parameter_field(field, raw_value)
        
        # First, convert to a Python type
        typed_value = cleaned_value
        if field.ui_element.value == "number_input":
            try:
                typed_value = int(cleaned_value)
            except (ValueError, TypeError):
                try:
                    typed_value = float(cleaned_value)
                except (ValueError, TypeError):
                    # For validation errors like port:0, we keep the value for now
                    typed_value = cleaned_value
        elif field.ui_element.value == "toggle_switch":
            typed_value = cleaned_value.lower() in ("true", "1", "on", "yes", "enabled")

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
#            migrated_profile = self.migrate_profile(profile)
            
            return profile
            
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
            # Try exact lookup first; if not found, try the short parameter name after the last dot
            param_spec = self.spec_parser.get_parameter_spec(param_name)
            lookup_name = param_name
            if not param_spec:
                short_name = param_name.split('.')[-1]
                param_spec = self.spec_parser.get_parameter_spec(short_name)
                if param_spec:
                    lookup_name = short_name

            if param_spec:
                value_to_validate = param_value.value

                # If the profile stored a dict like {'tcp_ack': 'Disabled'} for a single-field parameter,
                # unwrap it to the inner value (common when loading device dump outputs).
                if not param_spec.fields and isinstance(value_to_validate, dict):
                    # If dict has a single key that matches the short parameter name, extract it
                    if len(value_to_validate) == 1:
                        sole_key = next(iter(value_to_validate))
                        if sole_key == lookup_name or sole_key.endswith(lookup_name):
                            value_to_validate = value_to_validate[sole_key]

                # If parameter has conditional fields and value is a dict, attempt coercion then validate visible fields
                if param_spec.fields and isinstance(value_to_validate, dict):
                    # Normalize fields container
                    fields_list = param_spec.fields
                    if isinstance(fields_list, dict):
                        fields_list = list(fields_list.values())
                    coerced = dict(value_to_validate)  # shallow copy to avoid mutating original

                    # Coerce common device dump formats to expected UI types
                    for field in fields_list:
                        field_name = getattr(field, "name", None) or (field.get("name") if isinstance(field, dict) else None)
                        if not field_name or field_name not in coerced:
                            continue
                        v = coerced[field_name]

                        ui_type = getattr(field, "ui_element", None) or (field.get("ui_element") if isinstance(field, dict) else None)
                        options = getattr(field, "options", None) or (field.get("options") if isinstance(field, dict) else None) or []

                        # Coerce numeric strings to ints/floats for number_input
                        if ui_type == "number_input" and isinstance(v, str):
                            s = v.strip()
                            try:
                                if s.isdigit():
                                    coerced[field_name] = int(s)
                                else:
                                    coerced[field_name] = float(s)
                            except Exception:
                                coerced[field_name] = v

                        # Map booleans/numeric flags to option labels for toggle_switch
                        if ui_type == "toggle_switch" and options:
                            opts = [opt.strip() for opt in options]
                            if isinstance(v, bool):
                                coerced[field_name] = opts[0] if v else (opts[1] if len(opts) > 1 else opts[0])
                            elif isinstance(v, (int, float)):
                                coerced[field_name] = opts[0] if int(v) == 1 else (opts[1] if len(opts) > 1 else opts[0])
                            elif isinstance(v, str) and v.strip().lower() in ("true", "false", "1", "0", "enabled", "disabled"):
                                s = v.strip().lower()
                                if s in ("true", "1", "enabled"):
                                    coerced[field_name] = opts[0]
                                else:
                                    coerced[field_name] = opts[1] if len(opts) > 1 else opts[0]

                    # If numeric fields coerced to 0 but validation expects min>0, replace with default instead of failing
                    try:
                        for field in fields_list:
                            field_name = getattr(field, "name", None) or (field.get("name") if isinstance(field, dict) else None)
                            if not field_name or field_name not in coerced:
                                continue
                            validation_rule = getattr(field, "validation", None) or (field.get("validation") if isinstance(field, dict) else None) or ""
                            val = coerced.get(field_name)
                            if isinstance(val, (int, float)) and int(val) == 0 and validation_rule and "-" in validation_rule:
                                parts = validation_rule.split("-", 1)
                                try:
                                    min_val = int(parts[0])
                                    if min_val > 0:
                                        # replace with the field's default if available
                                        default = getattr(field, "get_default_value", None)
                                        if callable(default):
                                            coerced[field_name] = default()
                                        else:
                                            # try attribute default or leave removed
                                            fld_def = getattr(field, "default", None) or None
                                            if fld_def is not None:
                                                coerced[field_name] = fld_def
                                            else:
                                                coerced.pop(field_name, None)
                                except Exception:
                                    pass
                    except Exception:
                        pass

                    # Evaluate visible fields based on coerced context
                    context = coerced.copy()
                    try:
                        visible_fields = {f.name for f in param_spec.get_visible_fields(context)}
                    except Exception:
                        visible_fields = set(coerced.keys())
                    filtered_value = {k: v for k, v in coerced.items() if k in visible_fields}

                    # Validate using the filtered/coerced structure
                    try:
                        param_validation = param_spec.validate_value(filtered_value)
                    except Exception as e:
                        pv = ValidationResult(is_valid=False)
                        pv.add_error(f"Validation exception: {e}")
                        param_validation = pv
                else:
                    # Handle single-value toggle switches stored as booleans by mapping them to option labels
                    ui_type = getattr(param_spec, "ui_element", None)
                    if ui_type == "toggle_switch" and isinstance(value_to_validate, bool):
                        options = getattr(param_spec, "options", []) or []
                        opts = [opt.strip() for opt in options]
                        if opts:
                            value_to_validate = opts[0] if value_to_validate else (opts[1] if len(opts) > 1 else opts[0])

                    # Normal validation (guard against exceptions)
                    try:
                        param_validation = param_spec.validate_value(value_to_validate)
                    except Exception as e:
                        pv = ValidationResult(is_valid=False)
                        pv.add_error(f"Validation exception: {e}")
                        param_validation = pv

                if not param_validation.is_valid:
                    for error in param_validation.errors:
                        result.add_error(f"Parameter '{lookup_name}': {error}")
                
                for warning in param_validation.warnings:
                    result.add_warning(f"Parameter '{lookup_name}': {warning}")
                
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
        # But avoid adding defaults if an equivalent parameter already exists with a section prefix
        all_param_names = self.spec_parser.get_all_parameters()
        existing_keys = set(migrated_profile.parameters.keys())
        for param_name in all_param_names:
            # Detect equivalent present keys (exact or with section prefixes, e.g. 'network_parameters.server_settings')
            def _has_equivalent(name: str) -> bool:
                if name in existing_keys:
                    return True
                for k in existing_keys:
                    if k == name or k.endswith("." + name):
                        return True
                return False

            if _has_equivalent(param_name):
                continue

            param_spec = self.spec_parser.get_parameter_spec(param_name)
            if param_spec:
                default_value = param_spec.get_default_value()
                migrated_profile.parameters[param_name] = ParameterValue(
                    value=default_value,
                    source="default"
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
                        source="device"
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
    
    def _apply_parameter_processing(self, param_name: str, parsed_value: Any, raw_response: str) -> Any:
        """
        Apply parameter processing for clean display according to requirements.
        
        This method processes parameters to ensure clean display in the UI:
        - Time parameters show only numeric values (Requirements 1.1, 1.2, 1.3)
        - Odometer values are properly parsed and displayed (Requirements 3.1, 3.2, 3.3, 3.5)
        - Hourmeter values are properly parsed and displayed (Requirements 4.1, 4.2, 4.3, 4.5)
        
        Args:
            param_name: Name of the parameter being processed
            parsed_value: Already parsed value from device response
            raw_response: Raw device response for additional processing
            
        Returns:
            Processed value for UI display
        """
        try:
            param_name_lower = param_name.lower()
            
            # Time parameter names that need cleaning (Requirements 1.1, 1.2, 1.3)
            time_parameter_names = {
                'heartbeat_interval', 'report_interval', 'upload_interval', 'sleep_time',
                'moving_time', 'stopped_time', 'moving_heartbeat', 'stopped_heartbeat',
                'timeout', 'interval', 'delay', 'duration'
            }
            
            # Process time parameters
            if any(time_param in param_name_lower for time_param in time_parameter_names):
                if isinstance(parsed_value, str):
                    clean_value = self.parameter_processor.clean_time_parameter(parsed_value)
                    return clean_value
                elif isinstance(parsed_value, dict):
                    # For complex parameters with time fields
                    processed_dict = {}
                    for field_name, field_value in parsed_value.items():
                        if any(time_param in field_name.lower() for time_param in time_parameter_names):
                            if isinstance(field_value, str):
                                processed_dict[field_name] = self.parameter_processor.clean_time_parameter(field_value)
                            else:
                                processed_dict[field_name] = field_value
                        else:
                            processed_dict[field_name] = field_value
                    return processed_dict
            
            # Process odometer parameters (Requirements 3.1, 3.2, 3.3, 3.5)
            elif 'odometer' in param_name_lower or 'mileage' in param_name_lower:
                if isinstance(parsed_value, str):
                    # Use the raw response for better parsing
                    clean_value = self.parameter_processor.process_odometer_value(raw_response)
                    if clean_value:
                        return clean_value
                    else:
                        # Fallback to parsed value if processing fails
                        return parsed_value
                elif isinstance(parsed_value, dict):
                    # For complex parameters with odometer fields
                    processed_dict = {}
                    for field_name, field_value in parsed_value.items():
                        if 'odometer' in field_name.lower() or 'mileage' in field_name.lower():
                            if isinstance(field_value, str):
                                clean_value = self.parameter_processor.process_odometer_value(raw_response)
                                processed_dict[field_name] = clean_value if clean_value else field_value
                            else:
                                processed_dict[field_name] = field_value
                        else:
                            processed_dict[field_name] = field_value
                    return processed_dict
            
            # Process hourmeter parameters (Requirements 4.1, 4.2, 4.3, 4.5)
            elif 'hourmeter' in param_name_lower or 'acc_on' in param_name_lower or 'accont' in param_name_lower:
                if isinstance(parsed_value, str):
                    # Use the raw response for better parsing
                    clean_value = self.parameter_processor.process_hourmeter_value(raw_response)
                    if clean_value:
                        return clean_value
                    else:
                        # Fallback to parsed value if processing fails
                        return parsed_value
                elif isinstance(parsed_value, dict):
                    # For complex parameters with hourmeter fields
                    processed_dict = {}
                    for field_name, field_value in parsed_value.items():
                        if 'hourmeter' in field_name.lower() or 'acc_on' in field_name.lower() or 'accont' in field_name.lower():
                            if isinstance(field_value, str):
                                clean_value = self.parameter_processor.process_hourmeter_value(raw_response)
                                processed_dict[field_name] = clean_value if clean_value else field_value
                            else:
                                processed_dict[field_name] = field_value
                        else:
                            processed_dict[field_name] = field_value
                    return processed_dict
            
            # For all other parameters, return the parsed value as-is
            return parsed_value
            
        except Exception as e:
            # Log the error and return the original parsed value
            print(f"WARNING: Parameter processing failed for {param_name}: {e}")
            return parsed_value