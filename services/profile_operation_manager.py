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

from services.lt32pro_device_reader import LT32ProDeviceReader
from services.lt32pro_device_writer import LT32ProDeviceWriter
from services.enhanced_parameter_extractor import EnhancedParameterExtractor
from services.lt32pro_error_handler import LT32ProErrorHandler

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
        
        # Initialize components
        self.device_reader = LT32ProDeviceReader(serial_service)
        self.device_writer = LT32ProDeviceWriter(serial_service)
        self.parameter_extractor = EnhancedParameterExtractor()
        self.error_handler = LT32ProErrorHandler()
        
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
        
        # Total steps: device reading + parameter extraction + validation
        total_steps = len(self.device_reader.READ_COMMAND_SEQUENCE) + 2
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
            
            # Step 1: Read device configuration
            device_responses = {}
            
            def device_read_progress(step, total, description, success):
                nonlocal current_step
                if callback:
                    progress = ProgressUpdate(
                        current_step=step,
                        total_steps=total_steps,
                        step_description=f"Device reading: {description}",
                        success=success,
                        operation_type=OperationType.LOAD_FROM_DEVICE,
                        elapsed_time=time.time() - self._operation_start_time
                    )
                    callback(progress)
                
                # Update current step for overall progress
                current_step = step
            
            try:
                device_responses = self.device_reader.read_device_configuration(device_read_progress)
                
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
            
            # Step 3: Validate extracted parameters
            current_step += 1
            if callback:
                progress = ProgressUpdate(
                    current_step=current_step,
                    total_steps=total_steps,
                    step_description="Validating extracted parameters",
                    operation_type=OperationType.LOAD_FROM_DEVICE,
                    elapsed_time=time.time() - self._operation_start_time
                )
                callback(progress)
            
            try:
                validated_parameters = self.parameter_extractor.validate_extracted_parameters(extracted_parameters)
                
                # Count validation results
                original_count = len(extracted_parameters)
                validated_count = len(validated_parameters)
                
                if validated_count < original_count:
                    warning_msg = f"Parameter validation removed {original_count - validated_count} invalid parameters"
                    self._operation_warnings.append(warning_msg)
                    
            except Exception as e:
                error_msg = f"Parameter validation failed: {str(e)}"
                self._operation_warnings.append(error_msg)
                validated_parameters = extracted_parameters  # Use unvalidated parameters
            
            # Calculate operation results
            duration = time.time() - self._operation_start_time
            success_count = len(device_responses)
            total_count = len(self.device_reader.READ_COMMAND_SEQUENCE)
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
        if hasattr(self.device_reader, 'cancel_operation'):
            self.device_reader.cancel_operation()
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
            'device_reader': self.device_reader is not None,
            'device_writer': self.device_writer is not None,
            'parameter_extractor': self.parameter_extractor is not None,
            'error_handler': self.error_handler is not None,
            'serial_service': self.serial_service is not None and hasattr(self.serial_service, 'is_connected')
        }