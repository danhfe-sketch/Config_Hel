"""
Profile Operation Manager for LT32Pro Devices

This module provides a high-level interface for orchestrating complete profile operations
including loading profiles from devices and sending profiles to devices with real-time
progress tracking and comprehensive error handling.
"""

import time
import threading
from typing import Dict, Optional, Callable, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from services.configuration_reader_service import ConfigurationReaderService
from services.unified_device_communicator import UnifiedDeviceCommunicator
from services.lt32pro_device_writer import LT32ProDeviceWriter
from services.enhanced_parameter_extractor import EnhancedParameterExtractor
from services.parameter_processor import ParameterProcessor
from services.parameter_error_feedback_service import ParameterErrorFeedbackService
from services.lt32pro_error_handler import LT32ProErrorHandler
from services.ui_responsiveness_service import UIResponsivenessService, UpdatePriority, BatchUpdateResult

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of profile operations."""
    LOAD_FROM_DEVICE = "load_from_device"
    SEND_TO_DEVICE = "send_to_device"


class OperationStatus(Enum):
    """Status of profile operations."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OperationResult:
    """Result of a profile operation."""
    operation_type: OperationType
    status: OperationStatus
    success_count: int
    failure_count: int
    total_count: int
    duration_seconds: float
    parameters: Optional[Dict[str, str]] = None
    write_results: Optional[Dict[str, bool]] = None
    error_message: Optional[str] = None
    warnings: Optional[List[str]] = None


@dataclass
class ProgressUpdate:
    """Progress update information."""
    current_step: int
    total_steps: int
    step_description: str
    success: Optional[bool] = None
    operation_type: Optional[OperationType] = None
    elapsed_time: float = 0.0


class ProfileOperationManager:
    """
    Orchestrates complete profile operations with progress tracking.
    
    This class provides high-level methods for loading profiles from devices
    and sending profiles to devices, with real-time progress tracking,
    comprehensive error handling, and detailed operation reporting.
    """
    
    def __init__(self, serial_service, progress_callback: Optional[Callable[[ProgressUpdate], None]] = None):
        """
        Initialize the profile operation manager.
        
        Args:
            serial_service: The serial communication service instance
            progress_callback: Optional callback for progress updates
        """
        self.serial_service = serial_service
        self.progress_callback = progress_callback
        
        # Initialize components - using ConfigurationReaderService instead of LT32ProDeviceReader
        self.config_reader = ConfigurationReaderService(serial_service.app, serial_service.app.i18n)
        self.device_communicator = UnifiedDeviceCommunicator(self.config_reader)
        self.device_writer = LT32ProDeviceWriter(serial_service)
        self.parameter_extractor = EnhancedParameterExtractor()
        self.parameter_processor = ParameterProcessor()
        self.feedback_service = ParameterErrorFeedbackService()
        self.error_handler = LT32ProErrorHandler()
        
        # UI responsiveness service for batch updates and visual feedback
        self.ui_responsiveness = UIResponsivenessService()
        
        # Operation state
        self._current_operation = None
        self._operation_cancelled = False
        self._operation_start_time = None
        self._operation_lock = threading.Lock()
        
        # Results tracking
        self._last_result = None
        self._operation_warnings = []
        
    def load_profile_from_device(self, progress_callback: Optional[Callable[[ProgressUpdate], None]] = None) -> OperationResult:
        """
        Load a profile from the connected LT32Pro device.
        
        This method orchestrates the complete process of reading device configuration,
        extracting individual parameters, and creating a profile dictionary.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            OperationResult with extracted parameters and operation details
            
        Raises:
            ConnectionError: If device is not connected
            RuntimeError: If another operation is in progress
        """
        with self._operation_lock:
            if self._current_operation is not None:
                raise RuntimeError(f"Another operation is in progress: {self._current_operation}")
            
            self._current_operation = OperationType.LOAD_FROM_DEVICE
            
        # Use provided callback or instance callback
        callback = progress_callback or self.progress_callback
        
        # Initialize operation state
        self._operation_cancelled = False
        self._operation_start_time = time.time()
        self._operation_warnings = []
        
        # Total steps: device reading + parameter extraction + parameter processing + validation
        total_steps = len(self.device_communicator.READ_COMMAND_SEQUENCE) + 3
        current_step = 0
        
        try:
            # Update progress - starting operation
            if callback:
                progress = ProgressUpdate(
                    current_step=0,
                    total_steps=total_steps,
                    step_description="Starting profile load operation",
                    operation_type=OperationType.LOAD_FROM_DEVICE,
                    elapsed_time=0.0
                )
                callback(progress)
            
            # Step 1: Read device configuration using ConfigurationReaderService
            device_responses = {}
            
            def device_read_progress(progress_info):
                nonlocal current_step
                if callback:
                    # Extract progress information from ConfigurationReaderService format
                    current_step = progress_info.get('current_step', 0)
                    description = progress_info.get('status_text', 'Reading device configuration...')
                    success = progress_info.get('successful_count', 0) > 0
                    
                    progress = ProgressUpdate(
                        current_step=current_step,
                        total_steps=total_steps,
                        step_description=f"Device reading: {description}",
                        success=success,
                        operation_type=OperationType.LOAD_FROM_DEVICE,
                        elapsed_time=time.time() - self._operation_start_time
                    )
                    callback(progress)
            
            try:
                device_responses = self.device_communicator.read_device_configuration(device_read_progress)
                
                if not device_responses:
                    raise RuntimeError("No device responses received")
                    
            except Exception as e:
                error_msg = f"Failed to read device configuration: {str(e)}"
                self._operation_warnings.append(error_msg)
                
                # Try to handle the error and continue if possible
                try:
                    # Use the available error handling methods
                    if "timeout" in str(e).lower():
                        can_continue = self.error_handler.handle_communication_timeout("READ_CONFIG", 1)
                    else:
                        can_continue = False
                    
                    if not can_continue:
                        raise RuntimeError(error_msg)
                except Exception:
                    # If error handling fails, raise the original error
                    raise RuntimeError(error_msg)
            
            # Step 2: Extract parameters from responses
            current_step += 1
            if callback:
                progress = ProgressUpdate(
                    current_step=current_step,
                    total_steps=total_steps,
                    step_description="Extracting parameters from device responses",
                    operation_type=OperationType.LOAD_FROM_DEVICE,
                    elapsed_time=time.time() - self._operation_start_time
                )
                callback(progress)
            
            try:
                extracted_parameters = self.parameter_extractor.extract_parameters_from_responses(device_responses)
                
                if not extracted_parameters:
                    self._operation_warnings.append("No parameters could be extracted from device responses")
                    
            except Exception as e:
                error_msg = f"Failed to extract parameters: {str(e)}"
                self._operation_warnings.append(error_msg)
                extracted_parameters = {}
            
            # Step 3: Process parameters for clean display
            current_step += 1
            if callback:
                progress = ProgressUpdate(
                    current_step=current_step,
                    total_steps=total_steps,
                    step_description="Processing parameters for clean display",
                    operation_type=OperationType.LOAD_FROM_DEVICE,
                    elapsed_time=time.time() - self._operation_start_time
                )
                callback(progress)
            
            try:
                processed_parameters = self._process_parameters_for_display(extracted_parameters, device_responses)
                
                # Count processing results
                original_count = len(extracted_parameters)
                processed_count = len(processed_parameters)
                
                if processed_count != original_count:
                    warning_msg = f"Parameter processing changed {abs(original_count - processed_count)} parameters"
                    self._operation_warnings.append(warning_msg)
                    
            except Exception as e:
                error_msg = f"Parameter processing failed: {str(e)}"
                self._operation_warnings.append(error_msg)
                processed_parameters = extracted_parameters  # Use unprocessed parameters
            
            # Step 4: Validate processed parameters
            current_step += 1
            if callback:
                progress = ProgressUpdate(
                    current_step=current_step,
                    total_steps=total_steps,
                    step_description="Validating processed parameters",
                    operation_type=OperationType.LOAD_FROM_DEVICE,
                    elapsed_time=time.time() - self._operation_start_time
                )
                callback(progress)
            
            try:
                validated_parameters = self.parameter_extractor.validate_extracted_parameters(processed_parameters)
                
                # Count validation results
                original_count = len(processed_parameters)
                validated_count = len(validated_parameters)
                
                if validated_count < original_count:
                    warning_msg = f"Parameter validation removed {original_count - validated_count} invalid parameters"
                    self._operation_warnings.append(warning_msg)
                    
            except Exception as e:
                error_msg = f"Parameter validation failed: {str(e)}"
                self._operation_warnings.append(error_msg)
                validated_parameters = processed_parameters  # Use unvalidated parameters
            
            # Calculate operation results
            duration = time.time() - self._operation_start_time
            success_count = len(device_responses)
            total_count = len(self.device_communicator.READ_COMMAND_SEQUENCE)
            failure_count = total_count - success_count
            
            # Determine overall status
            if success_count == 0:
                status = OperationStatus.FAILED
            elif failure_count > 0:
                status = OperationStatus.COMPLETED  # Partial success
            else:
                status = OperationStatus.COMPLETED
            
            # Create result
            result = OperationResult(
                operation_type=OperationType.LOAD_FROM_DEVICE,
                status=status,
                success_count=success_count,
                failure_count=failure_count,
                total_count=total_count,
                duration_seconds=duration,
                parameters=validated_parameters,
                warnings=self._operation_warnings.copy() if self._operation_warnings else None
            )
            
            # Final progress update
            if callback:
                progress = ProgressUpdate(
                    current_step=total_steps,
                    total_steps=total_steps,
                    step_description=f"Load completed: {success_count}/{total_count} parameters extracted",
                    success=status == OperationStatus.COMPLETED,
                    operation_type=OperationType.LOAD_FROM_DEVICE,
                    elapsed_time=duration
                )
                callback(progress)
            
            self._last_result = result
            return result
            
        except Exception as e:
            # Handle operation failure
            duration = time.time() - self._operation_start_time
            error_msg = str(e)
            
            result = OperationResult(
                operation_type=OperationType.LOAD_FROM_DEVICE,
                status=OperationStatus.FAILED,
                success_count=0,
                failure_count=1,
                total_count=1,
                duration_seconds=duration,
                error_message=error_msg,
                warnings=self._operation_warnings.copy() if self._operation_warnings else None
            )
            
            # Final progress update with error
            if callback:
                progress = ProgressUpdate(
                    current_step=total_steps,
                    total_steps=total_steps,
                    step_description=f"Load failed: {error_msg}",
                    success=False,
                    operation_type=OperationType.LOAD_FROM_DEVICE,
                    elapsed_time=duration
                )
                callback(progress)
            
            self._last_result = result
            raise
            
        finally:
            with self._operation_lock:
                self._current_operation = None
    
    def send_profile_to_device(self, parameters: Dict[str, str], 
                             progress_callback: Optional[Callable[[ProgressUpdate], None]] = None) -> OperationResult:
        """
        Send a profile to the connected LT32Pro device.
        
        This method orchestrates the complete process of validating profile parameters,
        sending configuration commands to the device, and tracking the results.
        
        Args:
            parameters: Dictionary of parameters to send to device
            progress_callback: Optional callback for progress updates
            
        Returns:
            OperationResult with write results and operation details
            
        Raises:
            ConnectionError: If device is not connected
            ValueError: If parameters are invalid
            RuntimeError: If another operation is in progress
        """
        with self._operation_lock:
            if self._current_operation is not None:
                raise RuntimeError(f"Another operation is in progress: {self._current_operation}")
            
            self._current_operation = OperationType.SEND_TO_DEVICE
            
        # Use provided callback or instance callback
        callback = progress_callback or self.progress_callback
        
        # Initialize operation state
        self._operation_cancelled = False
        self._operation_start_time = time.time()
        self._operation_warnings = []
        
        if not parameters:
            raise ValueError("No parameters provided for sending to device")
        
        # Group parameters by command for progress calculation
        command_groups = self.device_writer._group_parameters_by_command(parameters)
        total_steps = len(command_groups) + 2  # +2 for validation and completion
        current_step = 0
        
        try:
            # Update progress - starting operation
            if callback:
                progress = ProgressUpdate(
                    current_step=0,
                    total_steps=total_steps,
                    step_description="Starting profile send operation",
                    operation_type=OperationType.SEND_TO_DEVICE,
                    elapsed_time=0.0
                )
                callback(progress)
            
            # Step 1: Validate parameters
            current_step += 1
            if callback:
                progress = ProgressUpdate(
                    current_step=current_step,
                    total_steps=total_steps,
                    step_description=f"Validating {len(parameters)} parameters",
                    operation_type=OperationType.SEND_TO_DEVICE,
                    elapsed_time=time.time() - self._operation_start_time
                )
                callback(progress)
            
            # Validate parameters before sending
            validated_parameters = self._validate_parameters_for_writing(parameters)
            
            if not validated_parameters:
                raise ValueError("No valid parameters found for device configuration")
            
            validation_warnings = len(parameters) - len(validated_parameters)
            if validation_warnings > 0:
                warning_msg = f"Parameter validation removed {validation_warnings} invalid parameters"
                self._operation_warnings.append(warning_msg)
            
            # Step 2: Send parameters to device
            write_results = {}
            
            def device_write_progress(step, total, description, success):
                nonlocal current_step
                if callback:
                    progress = ProgressUpdate(
                        current_step=current_step + step,
                        total_steps=total_steps,
                        step_description=f"Device writing: {description}",
                        success=success,
                        operation_type=OperationType.SEND_TO_DEVICE,
                        elapsed_time=time.time() - self._operation_start_time
                    )
                    callback(progress)
            
            try:
                write_results = self.device_writer.write_device_configuration(
                    validated_parameters, 
                    device_write_progress
                )
                
                if not write_results:
                    raise RuntimeError("No write results received from device")
                    
            except Exception as e:
                error_msg = f"Failed to write device configuration: {str(e)}"
                self._operation_warnings.append(error_msg)
                
                # Try to handle the error and continue if possible
                try:
                    # Use the available error handling methods
                    if "timeout" in str(e).lower():
                        can_continue = self.error_handler.handle_communication_timeout("WRITE_CONFIG", 1)
                    else:
                        can_continue = False
                    
                    if not can_continue:
                        raise RuntimeError(error_msg)
                except Exception:
                    # If error handling fails, raise the original error
                    raise RuntimeError(error_msg)
                
                # Use partial results if available
                write_results = self.device_writer.get_write_results()
            
            # Step 3: Final validation and completion
            current_step = total_steps - 1
            if callback:
                progress = ProgressUpdate(
                    current_step=current_step,
                    total_steps=total_steps,
                    step_description="Finalizing operation results",
                    operation_type=OperationType.SEND_TO_DEVICE,
                    elapsed_time=time.time() - self._operation_start_time
                )
                callback(progress)
            
            # Calculate operation results
            duration = time.time() - self._operation_start_time
            success_count = sum(1 for success in write_results.values() if success)
            total_count = len(write_results)
            failure_count = total_count - success_count
            
            # Determine overall status
            if success_count == 0:
                status = OperationStatus.FAILED
            elif failure_count > 0:
                status = OperationStatus.COMPLETED  # Partial success
            else:
                status = OperationStatus.COMPLETED
            
            # Create result
            result = OperationResult(
                operation_type=OperationType.SEND_TO_DEVICE,
                status=status,
                success_count=success_count,
                failure_count=failure_count,
                total_count=total_count,
                duration_seconds=duration,
                write_results=write_results,
                warnings=self._operation_warnings.copy() if self._operation_warnings else None
            )
            
            # Final progress update
            if callback:
                progress = ProgressUpdate(
                    current_step=total_steps,
                    total_steps=total_steps,
                    step_description=f"Send completed: {success_count}/{total_count} parameters written",
                    success=status == OperationStatus.COMPLETED,
                    operation_type=OperationType.SEND_TO_DEVICE,
                    elapsed_time=duration
                )
                callback(progress)
            
            self._last_result = result
            return result
            
        except Exception as e:
            # Handle operation failure
            duration = time.time() - self._operation_start_time
            error_msg = str(e)
            
            result = OperationResult(
                operation_type=OperationType.SEND_TO_DEVICE,
                status=OperationStatus.FAILED,
                success_count=0,
                failure_count=1,
                total_count=1,
                duration_seconds=duration,
                error_message=error_msg,
                warnings=self._operation_warnings.copy() if self._operation_warnings else None
            )
            
            # Final progress update with error
            if callback:
                progress = ProgressUpdate(
                    current_step=total_steps,
                    total_steps=total_steps,
                    step_description=f"Send failed: {error_msg}",
                    success=False,
                    operation_type=OperationType.SEND_TO_DEVICE,
                    elapsed_time=duration
                )
                callback(progress)
            
            self._last_result = result
            raise
            
        finally:
            with self._operation_lock:
                self._current_operation = None
    
    def _process_parameters_for_display(self, extracted_parameters: Dict[str, str], device_responses: Dict[str, str]) -> Dict[str, str]:
        """
        Process extracted parameters for clean UI display with comprehensive error handling.
        
        This method applies parameter processing to clean up time parameters,
        odometer values, and hourmeter values according to the requirements.
        Uses safe parameter processing with fallbacks for malformed data.
        
        Args:
            extracted_parameters: Parameters extracted from device responses
            device_responses: Raw device responses for additional processing
            
        Returns:
            Dictionary of processed parameters with clean values for UI display
            
        Requirements: 1.4, 1.5, 2.1, 2.2, 5.1, 5.2, 5.3, 5.4, 5.5
        """
        try:
            # Use the safe parameter processing method
            processing_summary = self.parameter_processor.safe_process_parameters(
                extracted_parameters, 
                device_responses
            )
            
            # Generate user feedback for processing results
            feedback_messages = self.feedback_service.generate_processing_feedback(processing_summary)
            
            # Add feedback messages to operation warnings for user visibility
            for feedback in feedback_messages:
                if feedback.level.value in ['warning', 'error']:
                    self._operation_warnings.append(f"{feedback.title}: {feedback.message}")
            
            # Extract processed parameters from results
            processed_parameters = {}
            for param_name, result in processing_summary.processing_results.items():
                processed_parameters[param_name] = result.processed_value
            
            # Use batch UI updates for processed parameters (Requirements 7.1, 7.2)
            if processed_parameters:
                try:
                    batch_result = self.ui_responsiveness.process_large_parameter_set(
                        processed_parameters,
                        progress_callback=lambda current, total: logger.debug(f"UI update progress: {current}/{total}")
                    )
                    
                    if batch_result.update_duration_ms > 100:  # Requirement 7.1
                        warning_msg = f"UI updates took {batch_result.update_duration_ms:.1f}ms, exceeding 100ms target"
                        self._operation_warnings.append(warning_msg)
                        logger.warning(warning_msg)
                    else:
                        logger.debug(f"UI updates completed in {batch_result.update_duration_ms:.1f}ms")
                        
                except Exception as e:
                    warning_msg = f"UI batch update failed: {str(e)}"
                    self._operation_warnings.append(warning_msg)
                    logger.warning(warning_msg)
            
            # Log comprehensive processing summary
            logger.info(f"Parameter processing completed: {processing_summary.successful_parameters}/{processing_summary.total_parameters} parameters processed successfully")
            
            if processing_summary.failed_parameters > 0:
                logger.warning(f"Parameter processing had {processing_summary.failed_parameters} failures: {processing_summary.errors[:3]}")
            
            if processing_summary.warnings:
                logger.info(f"Parameter processing had {len(processing_summary.warnings)} warnings")
            
            return processed_parameters
            
        except Exception as e:
            # Handle catastrophic failure in parameter processing
            error_msg = f"Critical error in parameter processing: {str(e)}"
            logger.error(error_msg)
            self._operation_warnings.append(error_msg)
            
            # Generate error feedback for user
            try:
                error_feedback = self.feedback_service.generate_malformed_data_feedback(
                    "parameter_processing", 
                    str(extracted_parameters)[:200], 
                    error_msg
                )
                self._operation_warnings.append(f"{error_feedback.title}: {error_feedback.message}")
            except Exception:
                # If even feedback generation fails, just log it
                logger.error("Failed to generate error feedback for parameter processing failure")
            
            # Return original parameters as fallback (Requirement 5.5)
            logger.info("Falling back to original extracted parameters due to processing failure")
            return extracted_parameters
    
    def _find_specific_odometer_response(self, param_name: str, device_responses: Dict[str, str]) -> Optional[str]:
        """
        Find the most appropriate raw device response for a specific odometer parameter.
        
        Args:
            param_name: Name of the parameter being processed
            device_responses: Raw device responses
            
        Returns:
            Raw response most appropriate for this parameter, or None if not found
        """
        param_name_lower = param_name.lower()
        
        # Priority order for finding responses based on parameter name
        if 'current' in param_name_lower or 'cur' in param_name_lower:
            # For current_mileage, prefer status response with "Cur Mileage Value"
            for command, response in device_responses.items():
                if response and 'Cur Mileage Value' in response:
                    return response
        
        # For general odometer/mileage parameters, prefer direct odometer command
        for command, response in device_responses.items():
            if not response:
                continue
                
            command_lower = command.lower()
            response_upper = response.upper()
            
            # Prefer direct odometer/mileage commands
            if 'odometer' in command_lower or 'mileage' in command_lower:
                if 'MILEAGE=' in response_upper:
                    return response
        
        # Fallback to any response containing odometer data
        return self._find_odometer_response(device_responses)
    
    def _find_specific_hourmeter_response(self, param_name: str, device_responses: Dict[str, str]) -> Optional[str]:
        """
        Find the most appropriate raw device response for a specific hourmeter parameter.
        
        Args:
            param_name: Name of the parameter being processed
            device_responses: Raw device responses
            
        Returns:
            Raw response most appropriate for this parameter, or None if not found
        """
        param_name_lower = param_name.lower()
        
        # First, try to find direct command match for the parameter
        for command, response in device_responses.items():
            if not response:
                continue
                
            command_lower = command.lower()
            response_upper = response.upper()
            
            # Direct command match - prefer exact parameter name matches
            if param_name_lower in command_lower:
                if 'ACCONT=' in response_upper:
                    return response
        
        # Priority order for finding responses based on parameter name
        if 'acc_on' in param_name_lower and 'accont' != param_name_lower:
            # For acc_on_time parameters (but not 'accont' itself), prefer status response with "Get ACC ON Time"
            for command, response in device_responses.items():
                if response and 'Get ACC ON Time' in response:
                    return response
        
        # For general hourmeter parameters, prefer direct hourmeter/accont commands
        for command, response in device_responses.items():
            if not response:
                continue
                
            command_lower = command.lower()
            response_upper = response.upper()
            
            # Prefer direct hourmeter/accont commands
            if 'hourmeter' in command_lower or 'accont' in command_lower:
                if 'ACCONT=' in response_upper:
                    return response
        
        # Fallback to any response containing hourmeter data
        return self._find_hourmeter_response(device_responses)
    
    def _find_odometer_response(self, device_responses: Dict[str, str]) -> Optional[str]:
        """
        Find the raw device response containing odometer data.
        
        Args:
            device_responses: Raw device responses
            
        Returns:
            Raw response containing odometer data, or None if not found
        """
        # Look for responses that might contain odometer data
        odometer_commands = ['odometer', 'mileage', 'status']
        
        for command, response in device_responses.items():
            if not response:
                continue
                
            command_lower = command.lower()
            response_upper = response.upper()
            
            # Check if this command might contain odometer data
            if any(cmd in command_lower for cmd in odometer_commands):
                # Check if response contains odometer-related keywords
                if any(keyword in response_upper for keyword in ['MILEAGE', 'ODOMETER', 'KM']):
                    return response
        
        return None
    
    def _find_hourmeter_response(self, device_responses: Dict[str, str]) -> Optional[str]:
        """
        Find the raw device response containing hourmeter data.
        
        Args:
            device_responses: Raw device responses
            
        Returns:
            Raw response containing hourmeter data, or None if not found
        """
        # Look for responses that might contain hourmeter data
        hourmeter_commands = ['hourmeter', 'accont', 'acc_on', 'status']
        
        for command, response in device_responses.items():
            if not response:
                continue
                
            command_lower = command.lower()
            response_upper = response.upper()
            
            # Check if this command might contain hourmeter data
            if any(cmd in command_lower for cmd in hourmeter_commands):
                # Check if response contains hourmeter-related keywords
                if any(keyword in response_upper for keyword in ['ACCONT', 'ACC ON', 'HOURMETER', 'MINUTE', 'HOUR']):
                    return response
        
        return None

    def _validate_parameters_for_writing(self, parameters: Dict[str, str]) -> Dict[str, str]:
        """
        Validate parameters before writing to device.
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            Dictionary of validated parameters
        """
        validated = {}
        supported_params = self.device_writer.get_supported_parameters()
        
        for param_name, value in parameters.items():
            # Check if parameter is supported
            if param_name.lower() not in [p.lower() for p in supported_params]:
                warning_msg = f"Unsupported parameter ignored: {param_name}"
                self._operation_warnings.append(warning_msg)
                continue
            
            # Check if value is valid
            if not value or not str(value).strip():
                warning_msg = f"Empty parameter ignored: {param_name}"
                self._operation_warnings.append(warning_msg)
                continue
            
            # Basic validation for specific parameter types
            if self._validate_parameter_value(param_name, value):
                validated[param_name] = str(value).strip()
            else:
                warning_msg = f"Invalid parameter value ignored: {param_name}={value}"
                self._operation_warnings.append(warning_msg)
        
        return validated
    
    def _validate_parameter_value(self, param_name: str, value: str) -> bool:
        """
        Validate individual parameter values.
        
        Args:
            param_name: Name of the parameter
            value: Value to validate
            
        Returns:
            True if value is valid for the parameter
        """
        param_lower = param_name.lower()
        value_str = str(value).strip()
        
        # Server IP validation
        if 'server_ip' in param_lower or param_lower == 'server':
            # Basic IP address or domain name validation
            if not value_str or len(value_str) < 3:
                return False
            # Allow IP addresses and domain names
            return True
        
        # Port validation
        if 'port' in param_lower:
            try:
                port = int(value_str)
                return 1 <= port <= 65535
            except ValueError:
                return False
        
        # Protocol validation
        if param_lower in ['protocol', 'gt06sel']:
            return value_str in ['0', '1', '2', '3', '4']
        
        # TCP ACK validation
        if param_lower in ['tcp_ack', 'tcp_acknowledgment', 'posbyack']:
            return value_str in ['0', '1']
        
        # APN validation
        if 'apn' in param_lower:
            # APN values can be empty for user/password but not for server
            if param_lower == 'apn_server' or param_lower == 'apn':
                return len(value_str) > 0
            return True  # User and password can be empty
        
        # Default: accept non-empty values
        return len(value_str) > 0
    
    def cancel_operation(self):
        """Cancel the current operation."""
        self._operation_cancelled = True
        
        # Cancel underlying operations
        if hasattr(self.device_communicator, 'cancel_operation'):
            self.device_communicator.cancel_operation()
        if hasattr(self.device_writer, 'cancel_operation'):
            self.device_writer.cancel_operation()
    
    def is_operation_in_progress(self) -> bool:
        """Check if an operation is currently in progress."""
        with self._operation_lock:
            return self._current_operation is not None
    
    def get_current_operation_type(self) -> Optional[OperationType]:
        """Get the type of the current operation."""
        with self._operation_lock:
            return self._current_operation
    
    def get_last_operation_result(self) -> Optional[OperationResult]:
        """Get the result of the last completed operation."""
        return self._last_result
    
    def get_operation_summary(self, result: OperationResult) -> str:
        """
        Generate a human-readable summary of an operation result.
        
        Args:
            result: The operation result to summarize
            
        Returns:
            Formatted summary string
        """
        operation_name = "Load Profile" if result.operation_type == OperationType.LOAD_FROM_DEVICE else "Send Profile"
        status_name = result.status.value.replace('_', ' ').title()
        
        summary_lines = [
            f"{operation_name} Operation - {status_name}",
            f"Duration: {result.duration_seconds:.2f} seconds",
            f"Success: {result.success_count}/{result.total_count} items"
        ]
        
        if result.failure_count > 0:
            summary_lines.append(f"Failures: {result.failure_count}")
        
        if result.error_message:
            summary_lines.append(f"Error: {result.error_message}")
        
        if result.warnings:
            summary_lines.append(f"Warnings: {len(result.warnings)}")
            for warning in result.warnings[:3]:  # Show first 3 warnings
                summary_lines.append(f"  - {warning}")
            if len(result.warnings) > 3:
                summary_lines.append(f"  ... and {len(result.warnings) - 3} more")
        
        return "\n".join(summary_lines)
    
    def get_supported_operations(self) -> List[OperationType]:
        """Get list of supported operation types."""
        return [OperationType.LOAD_FROM_DEVICE, OperationType.SEND_TO_DEVICE]
    
    def get_component_status(self) -> Dict[str, bool]:
        """
        Get status of all components.
        
        Returns:
            Dictionary mapping component names to their availability status
        """
        return {
            'config_reader': self.config_reader is not None,
            'device_communicator': self.device_communicator is not None,
            'device_writer': self.device_writer is not None,
            'parameter_extractor': self.parameter_extractor is not None,
            'parameter_processor': self.parameter_processor is not None,
            'error_handler': self.error_handler is not None,
            'ui_responsiveness': self.ui_responsiveness is not None,
            'serial_service': self.serial_service is not None and hasattr(self.serial_service, 'is_connected')
        }
    
    def set_parameters_frame(self, parameters_frame) -> None:
        """
        Set the parameters frame reference for UI responsiveness service.
        
        Args:
            parameters_frame: Reference to the parameters frame for UI updates
            
        Requirements: 7.1, 7.2, 7.3
        """
        self.ui_responsiveness.set_parameters_frame(parameters_frame)
        logger.debug("Parameters frame reference set for UI responsiveness")
    
    def update_parameters_with_batch_processing(self, parameters: Dict[str, Any], 
                                              progress_callback: Optional[Callable[[int, int], None]] = None) -> BatchUpdateResult:
        """
        Update UI parameters using batch processing for optimal responsiveness.
        
        Args:
            parameters: Dictionary of parameter names to values
            progress_callback: Optional callback for progress updates
            
        Returns:
            BatchUpdateResult: Results of the batch update operation
            
        Requirements: 7.1, 7.2, 7.4, 7.5
        """
        if not parameters:
            from services.ui_responsiveness_service import BatchUpdateResult
            return BatchUpdateResult(0, 0, 0, 0.0, [], [])
        
        logger.info(f"Starting batch parameter update for {len(parameters)} parameters")
        
        # Use UI responsiveness service for large parameter sets
        result = self.ui_responsiveness.process_large_parameter_set(parameters, progress_callback)
        
        # Log performance metrics
        performance = self.ui_responsiveness.get_performance_summary()
        logger.info(f"Batch update completed: {result.successful_updates}/{result.total_updates} successful, "
                   f"avg duration: {performance['avg_duration_ms']:.1f}ms")
        
        if result.update_duration_ms > 100:  # Requirement 7.1
            logger.warning(f"Batch update exceeded 100ms target: {result.update_duration_ms:.1f}ms")
        
        return result