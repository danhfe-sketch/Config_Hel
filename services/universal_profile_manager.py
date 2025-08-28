"""
Universal Profile Manager for the LT32 PRO Universal Profile System.

This module provides the main orchestrator class that coordinates all profile
operations including loading from device, saving to device, and file operations.
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Callable, List

from models.universal_profile import UniversalProfile
from models.operation_result import ProfileOperationResult, ParameterOperationResult, OperationType
from models.validation_result import ValidationResult
from services.parameter_specification_parser import ParameterSpecificationParser
from services.universal_profile_service import UniversalProfileService
from services.device_communication_manager import DeviceCommunicationManager


class UniversalProfileManager:
    """
    Main orchestrator for all profile operations in the LT32 PRO Universal Profile System.
    
    This class provides a unified interface for loading and saving profiles between
    the UI, device, and file system. It coordinates the various services to provide
    comprehensive profile management with progress tracking and error handling.
    """
    
    def __init__(self, serial_service, parameter_ui_list_path: str):
        """
        Initialize the Universal Profile Manager.
        
        Args:
            serial_service: The serial communication service instance
            parameter_ui_list_path: Path to the Parameter UI List markdown file
        """
        self.serial_service = serial_service
        self.parameter_ui_list_path = parameter_ui_list_path
        
        # Initialize core services
        self.spec_parser = ParameterSpecificationParser(parameter_ui_list_path)
        self.profile_service = UniversalProfileService(self.spec_parser)
        self.device_manager = DeviceCommunicationManager(serial_service, self.spec_parser)
        
        # Current profile state
        self._current_profile: Optional[UniversalProfile] = None
        self._operation_cancelled = False
        self._current_operation: Optional[str] = None
    
    async def load_from_device(self, progress_callback: Optional[Callable] = None) -> ProfileOperationResult:
        """
        Load the current configuration from the LT32 PRO device into a profile.
        
        This method reads all supported parameters from the device and creates
        a universal profile with the current device configuration.
        
        Args:
            progress_callback: Optional callback for progress updates
                              Called with (current_step, total_steps, step_description, success)
        
        Returns:
            ProfileOperationResult: Result of the load operation including the profile
            
        Raises:
            ConnectionError: If device is not connected
        """
        start_time = time.time()
        self._operation_cancelled = False
        self._current_operation = "load_from_device"
        
        result = ProfileOperationResult(
            operation_type=OperationType.LOAD_FROM_DEVICE,
            success=False,
            started_at=datetime.now()
        )
        
        try:
            # Check device connection
            if not self.serial_service.is_connected:
                result.add_error("Device is not connected")
                return result
            
            # Update progress
            if progress_callback:
                progress_callback(0, 100, "Starting device read operation", None)
            
            # Read all parameters from device
            try:
                device_responses = await self.device_manager.read_all_parameters(
                    progress_callback=self._create_device_progress_callback(progress_callback, 10, 90)
                )
                
                if self._operation_cancelled:
                    result.add_error("Operation was cancelled")
                    return result
                
                if not device_responses:
                    result.add_error("No parameters could be read from device")
                    return result
                
                # Update progress
                if progress_callback:
                    progress_callback(90, 100, "Creating profile from device data", None)
                
                # Create profile from device responses
                profile_name = f"Device Profile {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                profile = self.profile_service.create_profile_from_device(device_responses, profile_name)
                
                # Validate the created profile
                validation_result = self.profile_service.validate_profile(profile)
                
                # Add validation warnings to result
                for warning in validation_result.warnings:
                    result.add_warning(warning)
                
                if not validation_result.is_valid:
                    for error in validation_result.errors:
                        result.add_error(f"Profile validation: {error}")
                
                # Set the current profile
                self._current_profile = profile
                result.profile = profile
                result.success = True
                
                # Add parameter results
                for param_name, response in device_responses.items():
                    param_result = ParameterOperationResult(
                        parameter_name=param_name,
                        success=True,
                        value=profile.get_parameter_value(param_name),
                        device_response=response
                    )
                    result.add_parameter_result(param_result)
                
                # Final progress update
                if progress_callback:
                    progress_callback(100, 100, f"Successfully loaded {len(device_responses)} parameters", True)
                
                result.add_detail("device_responses_count", len(device_responses))
                result.add_detail("profile_name", profile_name)
                
            except Exception as e:
                result.add_error(f"Failed to read from device: {str(e)}")
                
        except Exception as e:
            result.add_error(f"Unexpected error during load from device: {str(e)}")
            
        finally:
            result.duration_seconds = time.time() - start_time
            result.completed_at = datetime.now()
            self._current_operation = None
        
        return result
    
    async def save_to_device(self, progress_callback: Optional[Callable] = None) -> ProfileOperationResult:
        """
        Save the current profile configuration to the LT32 PRO device.
        
        This method validates the current profile and writes all parameters
        to the device using the appropriate commands.
        
        Args:
            progress_callback: Optional callback for progress updates
                              Called with (current_step, total_steps, step_description, success)
        
        Returns:
            ProfileOperationResult: Result of the save operation
            
        Raises:
            ConnectionError: If device is not connected
            ValueError: If no profile is loaded or profile is invalid
        """
        start_time = time.time()
        self._operation_cancelled = False
        self._current_operation = "save_to_device"
        
        result = ProfileOperationResult(
            operation_type=OperationType.SAVE_TO_DEVICE,
            success=False,
            started_at=datetime.now()
        )
        
        try:
            # Check device connection
            if not self.serial_service.is_connected:
                result.add_error("Device is not connected")
                return result
            
            # Check if we have a current profile
            if not self._current_profile:
                result.add_error("No profile loaded to save to device")
                return result
            
            # Update progress
            if progress_callback:
                progress_callback(0, 100, "Validating profile before save", None)
            
            # Validate profile before saving
#            validation_result = self.profile_service.validate_profile(self._current_profile)
            
            # Add validation warnings to result
            # for warning in validation_result.warnings:
            #     result.add_warning(warning)
            
            # if not validation_result.is_valid:
            #     for error in validation_result.errors:
            #         result.add_error(f"Profile validation failed: {error}")
            #     return result
            
            # Update progress
            if progress_callback:
                progress_callback(10, 100, "Preparing parameters for device", None)
            
            # Prepare parameters for device writing
            parameters_to_write = {}
            complex_param_values = {}
            all_specs = self.spec_parser.parse_specifications()

            for param_name, param_value_obj in self._current_profile.parameters.items():
                if param_name == 'miscellaneous.odometer':
                    param_name = 'odometer'
                elif param_name == 'miscellaneous.hourmeter':
                    param_name = 'hourmeter'
                spec = all_specs.get(param_name)
                spec_key = param_name


                if not spec:
                    param_parts = param_name.split('.')
                    best_match_spec = None
                    best_match_key = None
                    for key, s in all_specs.items():
                        if key in param_parts:
                            if best_match_key is None or len(key) > len(best_match_key):
                                best_match_spec = s
                                best_match_key = key
                    if best_match_spec:
                        spec = best_match_spec
                        spec_key = best_match_key
                
                if spec:
                    if spec.fields:
                        field_name = param_name.split('.')[-1]
                        if spec_key not in complex_param_values:
                            complex_param_values[spec_key] = {}
                        complex_param_values[spec_key][field_name] = param_value_obj.value
                    else:
                        parameters_to_write[spec_key] = param_value_obj.value
            
            parameters_to_write.update(complex_param_values)

            # Debugging: Check odometer and hourmeter values before sending
            if 'odometer' in parameters_to_write:
                print(f"DEBUG: Odometer in parameters_to_write: {parameters_to_write['odometer']}")
            if 'hourmeter' in parameters_to_write:
                print(f"DEBUG: Hourmeter in parameters_to_write: {parameters_to_write['hourmeter']}")

            if not parameters_to_write:
                result.add_warning("No parameters to write to device")
                result.success = True
                return result
            
            # Write parameters to device
            try:
                write_results = await self.device_manager.write_all_parameters(
                    parameters_to_write,
                    progress_callback=self._create_device_progress_callback(progress_callback, 20, 90)
                )
                
                if self._operation_cancelled:
                    result.add_error("Operation was cancelled")
                    return result
                
                # Process write results
                successful_writes = 0
                failed_writes = 0
                
                for param_name, success in write_results.items():
                    param_result = ParameterOperationResult(
                        parameter_name=param_name,
                        success=success,
                        value=parameters_to_write.get(param_name)
                    )
                    
                    if not success:
                        param_result.error_message = "Failed to write to device"
                        failed_writes += 1
                    else:
                        successful_writes += 1
                    
                    result.add_parameter_result(param_result)
                
                # Update progress
                if progress_callback:
                    progress_callback(90, 100, "Finalizing save operation", None)
                
                # Determine overall success
                if successful_writes > 0:
                    result.success = True
                    if failed_writes > 0:
                        result.add_warning(f"Partial success: {successful_writes} parameters written, {failed_writes} failed")
                else:
                    result.add_error("No parameters could be written to device")
                
                # Final progress update
                if progress_callback:
                    status_msg = f"Saved {successful_writes}/{len(parameters_to_write)} parameters"
                    progress_callback(100, 100, status_msg, successful_writes > 0)
                
                result.add_detail("parameters_to_write", len(parameters_to_write))
                result.add_detail("successful_writes", successful_writes)
                result.add_detail("failed_writes", failed_writes)
                
            except Exception as e:
                result.add_error(f"Failed to write to device: {str(e)}")
                
        except Exception as e:
            result.add_error(f"Unexpected error during save to device: {str(e)}")
            
        finally:
            result.duration_seconds = time.time() - start_time
            result.completed_at = datetime.now()
            self._current_operation = None
        
        return result
    
    async def load_from_file(self, file_path: str) -> ProfileOperationResult:
        """Load a profile from a JSON file."""
        start_time = time.time()
        self._current_operation = "load_from_file"
        
        result = ProfileOperationResult(
            operation_type=OperationType.LOAD_FROM_FILE,
            success=False,
            started_at=datetime.now()
        )
        
        try:
            # Check if file exists
            if not Path(file_path).exists():
                result.add_error(f"Profile file not found: {file_path}")
                return result
            
            # Load profile using the profile service
            try:
                profile = self.profile_service.load_profile_from_file(file_path)
                
                # Mark all parameters as user source after loading
                for param_name in profile.parameters:
                    profile.parameters[param_name].source = "user"
                
                # Validate the loaded profile
#                validation_result = self.profile_service.validate_profile(profile)
                
                # Add validation warnings to result
                # for warning in validation_result.warnings:
                #     result.add_warning(warning)
                
                # if not validation_result.is_valid:
                #     for error in validation_result.errors:
                #         result.add_error(f"Profile validation: {error}")
                
                # Set the current profile
                self._current_profile = profile
                result.profile = profile
                result.success = True
                
                # Debugging: Check odometer and hourmeter values after loading
                if self._current_profile.parameters.get('miscellaneous.odometer'):
                    print(f"DEBUG: Odometer after load: {self._current_profile.parameters['miscellaneous.odometer'].value}")
                if self._current_profile.parameters.get('miscellaneous.hourmeter'):
                    print(f"DEBUG: Hourmeter after load: {self._current_profile.parameters['miscellaneous.hourmeter'].value}")
                
                # Add parameter results
                for param_name, param_value in profile.parameters.items():
                    param_result = ParameterOperationResult(
                        parameter_name=param_name,
                        success=True,
                        value=param_value.value
                    )
                    result.add_parameter_result(param_result)
                
                result.add_detail("file_path", file_path)
                result.add_detail("profile_name", profile.name)
                result.add_detail("parameters_loaded", len(profile.parameters))
                
            except FileNotFoundError:
                result.add_error(f"Profile file not found: {file_path}")
            except ValueError as e:
                result.add_error(f"Invalid profile file format: {str(e)}")
            except Exception as e:
                result.add_error(f"Failed to load profile file: {str(e)}")
                
        except Exception as e:
            result.add_error(f"Unexpected error during load from file: {str(e)}")
            
        finally:
            result.duration_seconds = time.time() - start_time
            result.completed_at = datetime.now()
            self._current_operation = None
        
        return result
    
    async def save_to_file(self, file_path: str, profile_name: Optional[str] = None) -> ProfileOperationResult:
        """
        Save the current profile to a JSON file.
        
        Args:
            file_path: Path where to save the profile file
            profile_name: Optional new name for the profile
        
        Returns:
            ProfileOperationResult: Result of the save operation
        """
        start_time = time.time()
        self._current_operation = "save_to_file"
        
        result = ProfileOperationResult(
            operation_type=OperationType.SAVE_TO_FILE,
            success=False,
            started_at=datetime.now()
        )
        
        try:
            # Check if we have a current profile
            if not self._current_profile:
                result.add_error("No profile loaded to save to file")
                return result
            
            # Create a copy of the profile for saving
            profile_to_save = self._current_profile.clone()
            
            # Update profile name if provided
            if profile_name:
                profile_to_save.name = profile_name
            
            # Update modification timestamp
            profile_to_save.modified_at = datetime.now()
            
            # Validate profile before saving
            validation_result = self.profile_service.validate_profile(profile_to_save)
            
            # Add validation warnings to result
            for warning in validation_result.warnings:
                result.add_warning(warning)
            
            if not validation_result.is_valid:
                for error in validation_result.errors:
                    result.add_error(f"Profile validation failed: {error}")
                return result
            
            # Save profile using the profile service
            try:
                success = self.profile_service.save_profile_to_file(profile_to_save, file_path)
                
                if success:
                    result.success = True
                    result.profile = profile_to_save
                    
                    # Add parameter results
                    for param_name, param_value in profile_to_save.parameters.items():
                        param_result = ParameterOperationResult(
                            parameter_name=param_name,
                            success=True,
                            value=param_value.value
                        )
                        result.add_parameter_result(param_result)
                    
                    result.add_detail("file_path", file_path)
                    result.add_detail("profile_name", profile_to_save.name)
                    result.add_detail("parameters_saved", len(profile_to_save.parameters))
                else:
                    result.add_error("Failed to save profile to file")
                    
            except Exception as e:
                result.add_error(f"Failed to save profile file: {str(e)}")
                
        except Exception as e:
            result.add_error(f"Unexpected error during save to file: {str(e)}")
            
        finally:
            result.duration_seconds = time.time() - start_time
            result.completed_at = datetime.now()
            self._current_operation = None
        
        return result 
   
    def get_current_profile(self) -> Optional[UniversalProfile]:
        """
        Get the currently loaded profile.
        
        Returns:
            Optional[UniversalProfile]: Current profile or None if no profile is loaded
        """
        return self._current_profile
    
    def set_current_profile(self, profile: UniversalProfile) -> None:
        """
        Set the current profile.
        
        Args:
            profile: Profile to set as current
        """
        self._current_profile = profile
    
    def populate_ui_fields(self, ui_field_values: Dict[str, Any]) -> ValidationResult:
        """
        Populate UI fields from the current profile with enhanced visibility and dependency handling.
        
        Args:
            ui_field_values: Dictionary to populate with UI field values
        
        Returns:
            ValidationResult: Result of the population operation
        """
        result = ValidationResult(is_valid=True)
        
        if not self._current_profile:
            result.add_error("No profile loaded to populate UI fields")
            return result
        
        try:
            # Clear existing UI values
            ui_field_values.clear()
            
            # Create context for visibility evaluation
            context = {name: pv.value for name, pv in self._current_profile.parameters.items()}
            
            # Track parameters that were skipped due to visibility
            skipped_parameters = []
            populated_parameters = []
            
            # Populate UI fields from profile parameters
            for param_name, param_value in self._current_profile.parameters.items():
                try:
                    # Get parameter specification for UI mapping
                    param_spec = self.spec_parser.get_parameter_spec(param_name)
                    
                    if param_spec:
                        # Check if parameter should be visible
                        if self._evaluate_visibility_condition(param_spec.visibility_condition, context):
                            # Handle complex parameters with multiple fields
                            if param_spec.fields:
                                # Complex parameter - populate individual fields
                                for field in param_spec.fields:
                                    field_name = f"{param_name}.{field.name}"
                                    if hasattr(param_value.value, field.name):
                                        field_value = getattr(param_value.value, field.name)
                                        ui_field_values[field_name] = field_value
                                        populated_parameters.append(field_name)
                                    elif isinstance(param_value.value, dict) and field.name in param_value.value:
                                        ui_field_values[field_name] = param_value.value[field.name]
                                        populated_parameters.append(field_name)
                            else:
                                # Simple parameter
                                ui_field_values[param_name] = param_value.value
                                populated_parameters.append(param_name)
                        else:
                            skipped_parameters.append(param_name)
                            result.add_warning(f"Parameter '{param_name}' is not visible with current values")
                    else:
                        # Parameter not found in specifications - include it anyway
                        ui_field_values[param_name] = param_value.value
                        populated_parameters.append(param_name)
                        result.add_warning(f"No specification found for parameter '{param_name}'")
                        
                except Exception as e:
                    result.add_warning(f"Failed to populate parameter '{param_name}': {str(e)}")
            
            # Validate field dependencies after population
            dependency_result = self._validate_field_dependencies(ui_field_values)
            if not dependency_result.is_valid:
                result.warnings.extend(dependency_result.warnings)
                result.errors.extend(dependency_result.errors)
            
            result.add_detail("parameters_populated", len(populated_parameters))
            result.add_detail("parameters_skipped", len(skipped_parameters))
            result.add_detail("populated_parameters", populated_parameters)
            result.add_detail("skipped_parameters", skipped_parameters)
            
        except Exception as e:
            result.is_valid = False
            result.add_error(f"Failed to populate UI fields: {str(e)}")
        
        return result
    
    def extract_ui_field_values(self, ui_field_values: Dict[str, Any]) -> ValidationResult:
        """
        Extract UI field values and update the current profile with enhanced validation and dependency handling.
        
        Args:
            ui_field_values: Dictionary of UI field values
        
        Returns:
            ValidationResult: Result of the extraction operation
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Validate field dependencies first
            dependency_result = self._validate_field_dependencies(ui_field_values)
            if not dependency_result.is_valid:
                result.warnings.extend(dependency_result.warnings)
                result.errors.extend(dependency_result.errors)
            
            # Track processing results
            processed_parameters = []
            failed_parameters = []
            updated_dependencies = []
            
            # Create a new profile if none exists
            if not self._current_profile:
                profile_name = f"UI Profile {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                self._current_profile = self.profile_service.create_profile_from_ui(ui_field_values, profile_name)
                processed_parameters = list(ui_field_values.keys())
            else:
                # Update existing profile with UI values
                for param_name, value in ui_field_values.items():
                    try:
                        # Get parameter specification for validation
                        param_spec = self.spec_parser.get_parameter_spec(param_name)
                        
                        # Check if this is a complex parameter field first
                        if '.' in param_name:
                            # Handle complex parameter field
                            base_param, field_name = param_name.split('.', 1)
                            self._set_complex_parameter_field(base_param, field_name, value)
                            processed_parameters.append(param_name)
                        elif param_spec:
                            # Validate individual parameter value
                            param_validation = param_spec.validate_value(value)
                            
                            if param_validation.is_valid:
                                # Simple parameter
                                old_value = self._current_profile.get_parameter_value(param_name)
                                self._current_profile.set_parameter_value(param_name, value, "user")
                                
                                # Check if this parameter affects other parameters
                                if old_value != value:
                                    dependencies = self._update_dependent_fields(param_name, value, ui_field_values)
                                    updated_dependencies.extend(dependencies)
                                
                                processed_parameters.append(param_name)
                            else:
                                # Use default value for invalid parameters
                                default_value = param_spec.get_default_value()
                                if default_value is not None:
                                    self._current_profile.set_parameter_value(param_name, default_value, "default")
                                    result.add_warning(f"Invalid value for '{param_name}': {param_validation.errors[0]}. Using default: {default_value}")
                                    processed_parameters.append(param_name)
                                else:
                                    failed_parameters.append(param_name)
                                    result.add_error(f"Invalid value for '{param_name}': {param_validation.errors[0]}")
                        else:
                            # Parameter not in specifications - set it anyway with warning
                            self._current_profile.set_parameter_value(param_name, value, "user")
                            processed_parameters.append(param_name)
                            result.add_warning(f"No specification found for parameter '{param_name}'")
                            
                    except Exception as e:
                        failed_parameters.append(param_name)
                        result.add_error(f"Failed to process parameter '{param_name}': {str(e)}")
            
            # Validate the updated profile
            validation_result = self.profile_service.validate_profile(self._current_profile)
            
            # Merge validation results
            result.warnings.extend(validation_result.warnings)
            if not validation_result.is_valid:
                result.errors.extend(validation_result.errors)
                result.is_valid = False
            
            result.add_detail("parameters_extracted", len(processed_parameters))
            result.add_detail("parameters_failed", len(failed_parameters))
            result.add_detail("dependencies_updated", len(updated_dependencies))
            result.add_detail("processed_parameters", processed_parameters)
            result.add_detail("failed_parameters", failed_parameters)
            result.add_detail("updated_dependencies", updated_dependencies)
            result.add_detail("profile_name", self._current_profile.name)
            
        except Exception as e:
            result.add_error(f"Failed to extract UI field values: {str(e)}")
        
        return result
    
    def cancel_operation(self) -> None:
        """Cancel the current operation."""
        self._operation_cancelled = True
        
        # Cancel device manager operations
        if self.device_manager:
            self.device_manager.cancel_operation()
    
    def is_operation_cancelled(self) -> bool:
        """Check if the current operation was cancelled."""
        return self._operation_cancelled
    
    def get_current_operation(self) -> Optional[str]:
        """Get the name of the current operation."""
        return self._current_operation
    
    def get_supported_parameters(self) -> List[str]:
        """
        Get list of parameters supported by the system.
        
        Returns:
            List[str]: List of supported parameter names
        """
        try:
            return self.spec_parser.get_all_parameters()
        except Exception:
            return []
    
    def get_profile_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get a summary of the current profile.
        
        Returns:
            Optional[Dict[str, Any]]: Profile summary or None if no profile loaded
        """
        if not self._current_profile:
            return None
        
        return self.profile_service.get_profile_summary(self._current_profile)
    
    def validate_current_profile(self) -> ValidationResult:
        """
        Validate the current profile.
        
        Returns:
            ValidationResult: Validation result
        """
        if not self._current_profile:
            result = ValidationResult(is_valid=False)
            result.add_error("No profile loaded to validate")
            return result
        
        return self.profile_service.validate_profile(self._current_profile)
    
    def get_visible_parameters(self, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Get list of parameters that should be visible given the current context.
        
        Args:
            context: Optional context dictionary. If None, uses current profile values.
        
        Returns:
            List[str]: List of visible parameter names
        """
        if context is None and self._current_profile:
            context = {name: pv.value for name, pv in self._current_profile.parameters.items()}
        elif context is None:
            context = {}
        
        visible_params = []
        
        try:
            all_params = self.spec_parser.get_all_parameters()
            
            for param_name in all_params:
                param_spec = self.spec_parser.get_parameter_spec(param_name)
                if param_spec:
                    if self._evaluate_visibility_condition(param_spec.visibility_condition, context):
                        visible_params.append(param_name)
                else:
                    # Include parameters without specifications
                    visible_params.append(param_name)
        
        except Exception:
            # If visibility evaluation fails, return all parameters
            visible_params = self.get_supported_parameters()
        
        return visible_params
    
    def get_parameter_dependencies(self, parameter_name: str) -> Dict[str, List[str]]:
        """
        Get dependency information for a parameter.
        
        Args:
            parameter_name: Name of the parameter to check
        
        Returns:
            Dict containing 'depends_on' and 'affects' lists
        """
        result = {
            'depends_on': [],
            'affects': []
        }
        
        try:
            # Get what this parameter depends on
            result['depends_on'] = self._get_field_dependencies(parameter_name)
            
            # Get what parameters this one affects
            all_params = self.spec_parser.get_all_parameters()
            for param_name in all_params:
                dependencies = self._get_field_dependencies(param_name)
                if parameter_name in dependencies:
                    result['affects'].append(param_name)
        except Exception:
            pass
        
        return result
    
    def validate_ui_field_values(self, ui_field_values: Dict[str, Any]) -> ValidationResult:
        """
        Validate UI field values without updating the profile.
        
        Args:
            ui_field_values: Dictionary of UI field values to validate
        
        Returns:
            ValidationResult: Validation result with detailed feedback
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Validate field dependencies
            dependency_result = self._validate_field_dependencies(ui_field_values)
            result.warnings.extend(dependency_result.warnings)
            result.errors.extend(dependency_result.errors)
            
            # Validate individual field values
            valid_fields = []
            invalid_fields = []
            
            for field_name, field_value in ui_field_values.items():
                param_spec = self.spec_parser.get_parameter_spec(field_name)
                
                if param_spec:
                    field_validation = param_spec.validate_value(field_value)
                    
                    if field_validation.is_valid:
                        valid_fields.append(field_name)
                    else:
                        invalid_fields.append(field_name)
                        result.add_error(f"Invalid value for '{field_name}': {field_validation.errors[0]}")
                else:
                    # No specification - assume valid but warn
                    valid_fields.append(field_name)
                    result.add_warning(f"No specification found for field '{field_name}'")
            
            if invalid_fields:
                result.is_valid = False
            
            result.add_detail("valid_fields", valid_fields)
            result.add_detail("invalid_fields", invalid_fields)
            result.add_detail("total_fields", len(ui_field_values))
            
        except Exception as e:
            result.add_error(f"Failed to validate UI field values: {str(e)}")
            result.is_valid = False
        
        return result
    
    def get_field_default_values(self, field_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get default values for specified fields or all supported fields.
        
        Args:
            field_names: Optional list of field names. If None, returns defaults for all fields.
        
        Returns:
            Dict[str, Any]: Dictionary of field names to default values
        """
        defaults = {}
        
        try:
            if field_names is None:
                field_names = self.get_supported_parameters()
            
            for field_name in field_names:
                param_spec = self.spec_parser.get_parameter_spec(field_name)
                if param_spec:
                    default_value = param_spec.get_default_value()
                    if default_value is not None:
                        defaults[field_name] = default_value
        
        except Exception:
            pass
        
        return defaults
    
    def compare_with_device(self, progress_callback: Optional[Callable] = None) -> ProfileOperationResult:
        """
        Compare the current profile with device configuration.
        
        This method reads the current device configuration and compares it
        with the loaded profile to identify differences.
        
        Args:
            progress_callback: Optional callback for progress updates
        
        Returns:
            ProfileOperationResult: Result containing comparison details
        """
        # This would be implemented as a future enhancement
        # For now, return a not implemented result
        result = ProfileOperationResult(
            operation_type=OperationType.VALIDATE_PROFILE,
            success=False,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        result.add_error("Profile comparison with device not yet implemented")
        return result
    
    def _evaluate_visibility_condition(self, condition: Optional[str], context: Dict[str, Any]) -> bool:
        """
        Evaluate a visibility condition against the current parameter context.
        
        Args:
            condition: Visibility condition string (e.g., "ignition_mode == 'Virtual por bateria'")
            context: Dictionary of parameter values for evaluation
        
        Returns:
            bool: True if the condition is met or no condition exists
        """
        if not condition:
            return True
        
        try:
            # Simple condition parsing - supports basic equality and boolean checks
            condition = condition.strip()
            
            # Handle boolean conditions
            if condition in context:
                return bool(context[condition])
            
            # Handle equality conditions
            if '==' in condition:
                left, right = condition.split('==', 1)
                left = left.strip()
                right = right.strip().strip("'\"")
                
                if left in context:
                    return str(context[left]) == right
            
            # Handle boolean true/false conditions
            if '== true' in condition:
                param_name = condition.replace('== true', '').strip()
                if param_name in context:
                    return bool(context[param_name])
            
            if '== false' in condition:
                param_name = condition.replace('== false', '').strip()
                if param_name in context:
                    return not bool(context[param_name])
            
            # Default to visible if condition cannot be evaluated
            return True
            
        except Exception:
            # If condition evaluation fails, default to visible
            return True
    
    def _update_dependent_fields(self, changed_field: str, new_value: Any, ui_field_values: Dict[str, Any]) -> List[str]:
        """
        Update fields that depend on the changed field.
        
        Args:
            changed_field: Name of the field that changed
            new_value: New value of the changed field
            ui_field_values: Dictionary of all UI field values
        
        Returns:
            List[str]: List of field names that were updated
        """
        updated_fields = []
        
        try:
            # Get all parameter specifications to check for dependencies
            all_params = self.spec_parser.get_all_parameters()
            
            for param_name in all_params:
                param_spec = self.spec_parser.get_parameter_spec(param_name)
                if param_spec and param_spec.visibility_condition:
                    # Check if this parameter's visibility depends on the changed field
                    if changed_field in param_spec.visibility_condition:
                        # Update the context and re-evaluate visibility
                        context = dict(ui_field_values)
                        context[changed_field] = new_value
                        
                        is_visible = self._evaluate_visibility_condition(param_spec.visibility_condition, context)
                        
                        # If parameter becomes invisible, remove it from UI values
                        if not is_visible and param_name in ui_field_values:
                            del ui_field_values[param_name]
                            updated_fields.append(param_name)
                        # If parameter becomes visible and has a default, add it
                        elif is_visible and param_name not in ui_field_values:
                            default_value = param_spec.get_default_value()
                            if default_value is not None:
                                ui_field_values[param_name] = default_value
                                updated_fields.append(param_name)
            
        except Exception:
            # If dependency update fails, continue without updates
            pass
        
        return updated_fields
    
    def _get_field_dependencies(self, field_name: str) -> List[str]:
        """
        Get the list of fields that the given field depends on.
        
        Args:
            field_name: Name of the field to check dependencies for
        
        Returns:
            List[str]: List of field names that this field depends on
        """
        dependencies = []
        
        try:
            param_spec = self.spec_parser.get_parameter_spec(field_name)
            if param_spec and param_spec.visibility_condition:
                # Simple dependency extraction from visibility condition
                condition = param_spec.visibility_condition
                
                # Extract parameter names from condition
                import re
                # Find parameter names (alphanumeric with underscores)
                param_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', condition)
                
                # Filter out keywords and operators
                keywords = {'true', 'false', 'and', 'or', 'not', 'in', 'is'}
                dependencies = [match for match in param_matches if match not in keywords]
        
        except Exception:
            pass
        
        return dependencies
    
    def _validate_field_dependencies(self, ui_field_values: Dict[str, Any]) -> ValidationResult:
        """
        Validate that all field dependencies are satisfied.
        
        Args:
            ui_field_values: Dictionary of UI field values
        
        Returns:
            ValidationResult: Result of dependency validation
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Check each field's dependencies
            for field_name, field_value in ui_field_values.items():
                dependencies = self._get_field_dependencies(field_name)
                
                for dependency in dependencies:
                    if dependency not in ui_field_values:
                        result.add_warning(f"Field '{field_name}' depends on '{dependency}' which is not present")
                    else:
                        # Check if the dependency relationship is valid
                        param_spec = self.spec_parser.get_parameter_spec(field_name)
                        if param_spec and param_spec.visibility_condition:
                            is_visible = self._evaluate_visibility_condition(
                                param_spec.visibility_condition, ui_field_values
                            )
                            
                            if not is_visible:
                                result.add_error(f"Field '{field_name}' should not be visible with current dependency values. "
                                               f"Condition: {param_spec.visibility_condition}")
        
        except Exception as e:
            result.add_warning(f"Failed to validate field dependencies: {str(e)}")
        
        return result
    
    def _set_complex_parameter_field(self, base_param: str, field_name: str, value: Any) -> None:
        """
        Set a field value in a complex parameter.
        
        Args:
            base_param: Name of the base parameter
            field_name: Name of the field within the parameter
            value: Value to set
        """
        try:
            current_value = self._current_profile.get_parameter_value(base_param)
            
            if current_value is None:
                # Create new complex parameter value
                current_value = {}
            elif not isinstance(current_value, dict):
                # Convert to dict if needed
                current_value = {"value": current_value}
            
            # Set the field value
            current_value[field_name] = value
            
            # Update the parameter
            self._current_profile.set_parameter_value(base_param, current_value, "user")
            
        except Exception:
            # If complex parameter handling fails, set as simple parameter
            self._current_profile.set_parameter_value(f"{base_param}.{field_name}", value, "user")
    
    def _create_device_progress_callback(self, user_callback: Optional[Callable], 
                                       start_percent: int, end_percent: int) -> Optional[Callable]:
        """
        Create a progress callback that maps device operation progress to user callback.
        
        Args:
            user_callback: User's progress callback
            start_percent: Starting percentage for this operation
            end_percent: Ending percentage for this operation
        
        Returns:
            Optional[Callable]: Mapped progress callback
        """
        if not user_callback:
            return None
        
        def device_progress_callback(current: int, total: int, description: str, success: Optional[bool]):
            if total > 0:
                # Map device progress to user progress range
                device_percent = (current / total) * 100
                mapped_percent = start_percent + (device_percent * (end_percent - start_percent) / 100)
                user_callback(int(mapped_percent), 100, description, success)
            else:
                user_callback(start_percent, 100, description, success)
        
        return device_progress_callback
    
    def __str__(self) -> str:
        """String representation of the profile manager."""
        profile_info = "No profile loaded"
        if self._current_profile:
            profile_info = f"Profile: {self._current_profile.name} ({len(self._current_profile.parameters)} parameters)"
        
        operation_info = "Idle"
        if self._current_operation:
            operation_info = f"Operation: {self._current_operation}"
        
        return f"UniversalProfileManager({profile_info}, {operation_info})"

    def create_recovery_summary(self, recovery_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a recovery summary from the given context.
        
        Args:
            recovery_context: Dictionary with recovery information
        
        Returns:
            Dictionary with a summary of the recovery actions
        """
        if not recovery_context:
            return {}

        summary = {
            'total_parameters': recovery_context.get('total_parameters', 0),
            'successful_parameters': recovery_context.get('successful_parameters', 0),
            'failed_parameters': recovery_context.get('failed_parameters', 0),
            'recovery_actions': recovery_context.get('recovery_actions', 0),
            'success_rate_percent': 0
        }
        
        if summary['total_parameters'] > 0:
            summary['success_rate_percent'] = (summary['successful_parameters'] / summary['total_parameters']) * 100
            
        return summary

    def update_recovery_statistics(self, stats: Dict[str, Any]) -> None:
        """
        Update recovery statistics.

        (Placeholder implementation)

        Args:
            stats: Dictionary with recovery statistics.
        """
        # TODO: Implement recovery statistics handling
        pass