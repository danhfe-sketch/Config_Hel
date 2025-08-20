"""
Non-Blocking Profile Manager - Executes profile operations in background threads.

This module provides the NonBlockingProfileManager class that executes profile operations
in background threads to maintain UI responsiveness. It includes thread-safe progress
callbacks, operation cancellation, and proper cleanup.

Key Features:
- Background thread execution for all profile operations
- Thread-safe progress updates using tkinter's after() method
- Operation cancellation with proper cleanup and thread termination
- Operation context management for maintaining state across threads
- Comprehensive error handling and recovery
"""

import threading
import time
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable, List
from enum import Enum


class OperationType(Enum):
    """Enumeration of supported profile operation types."""
    LOAD_FROM_DEVICE = "load_from_device"
    LOAD_TO_DEVICE = "load_to_device"
    LOAD_TO_UI = "load_to_ui"
    SAVE_FROM_UI = "save_from_ui"


@dataclass
class OperationContext:
    """Context information for profile operations."""
    operation_type: OperationType
    operation_id: str
    file_path: Optional[str] = None
    profile_name: Optional[str] = None
    parameters: Optional[Dict[str, str]] = None
    progress_callback: Optional[Callable] = None
    completion_callback: Optional[Callable] = None
    cancellation_token: Optional[threading.Event] = None
    start_time: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProgressInfo:
    """Progress information for profile operations."""
    operation_id: str
    operation_type: OperationType
    current_step: int
    total_steps: int
    current_parameter: str
    status_message: str
    can_cancel: bool
    is_complete: bool
    success: bool = False
    error_message: Optional[str] = None


@dataclass
class OperationResult:
    """Result of a profile operation."""
    operation_id: str
    operation_type: OperationType
    success: bool
    error_message: Optional[str] = None
    parameters_processed: int = 0
    failed_parameters: List[str] = None
    operation_duration: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class NonBlockingProfileManager:
    """
    Non-blocking profile manager that executes operations in background threads.
    
    This class provides thread-safe execution of profile operations while maintaining
    UI responsiveness through background thread execution and thread-safe callbacks.
    """
    
    def __init__(self, app_instance):
        """
        Initialize the non-blocking profile manager.
        
        Args:
            app_instance: Main application instance with UI and services
        """
        self.app = app_instance
        self.i18n = getattr(app_instance, 'i18n_service', None) or getattr(app_instance, 'i18n', None)
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Operation management
        self.active_operations: Dict[str, OperationContext] = {}
        self.operation_threads: Dict[str, threading.Thread] = {}
        self.operation_counter = 0
        self.operation_lock = threading.Lock()
        
        # Default callbacks
        self.default_progress_callback: Optional[Callable] = None
        self.default_completion_callback: Optional[Callable] = None
        
        # Operation timeout settings (in seconds)
        self.operation_timeouts = {
            OperationType.LOAD_FROM_DEVICE: 300,  # 5 minutes
            OperationType.LOAD_TO_DEVICE: 300,    # 5 minutes
            OperationType.LOAD_TO_UI: 30,         # 30 seconds
            OperationType.SAVE_FROM_UI: 30        # 30 seconds
        }
        
        # Optimized thread pool settings
        import os
        cpu_count = os.cpu_count() or 2
        self.max_concurrent_operations = min(4, max(2, cpu_count // 2))
        
        # Performance optimization settings
        self.progress_update_interval = 0.2  # 200ms between updates
        self.last_progress_update = {}  # Track last update time per operation
        self.memory_cleanup_threshold = 100  # MB
        self.parameter_batch_size = 10  # Process parameters in batches
        
        # Performance monitoring
        self.performance_monitor = None
        try:
            from .profile_performance_monitor import ProfilePerformanceMonitor
            self.performance_monitor = ProfilePerformanceMonitor()
            self.performance_monitor.start_monitoring()
        except ImportError:
            self.logger.warning("Performance monitor not available")
        
        self.logger.info(f"NonBlockingProfileManager initialized with {self.max_concurrent_operations} max concurrent operations")
    
    def execute_profile_operation(self, operation_type: OperationType, **kwargs) -> str:
        """
        Execute a profile operation in a background thread with performance monitoring.
        
        Args:
            operation_type: Type of operation to execute
            **kwargs: Operation-specific arguments
            
        Returns:
            str: Operation ID for tracking the operation
            
        Raises:
            RuntimeError: If too many operations are running concurrently
        """
        # Check concurrent operation limit
        with self.operation_lock:
            if len(self.active_operations) >= self.max_concurrent_operations:
                # Clean up completed operations first
                self.cleanup_completed_operations()
                
                # Check again after cleanup
                if len(self.active_operations) >= self.max_concurrent_operations:
                    raise RuntimeError(f"Maximum concurrent operations ({self.max_concurrent_operations}) exceeded")
            
            # Generate unique operation ID
            self.operation_counter += 1
            operation_id = f"{operation_type.value}_{self.operation_counter}_{int(time.time())}"
        
        # Create operation context
        context = OperationContext(
            operation_type=operation_type,
            operation_id=operation_id,
            file_path=kwargs.get('file_path'),
            profile_name=kwargs.get('profile_name'),
            parameters=kwargs.get('parameters'),
            progress_callback=kwargs.get('progress_callback', self.default_progress_callback),
            completion_callback=kwargs.get('completion_callback', self.default_completion_callback),
            cancellation_token=threading.Event(),
            start_time=datetime.now(),
            metadata=kwargs.get('metadata', {})
        )
        
        # Store operation context
        with self.operation_lock:
            self.active_operations[operation_id] = context
        
        # Start performance monitoring for this operation
        if self.performance_monitor:
            expected_params = kwargs.get('expected_parameters', 0)
            self.performance_monitor.start_operation_monitoring(
                operation_id, operation_type.value, expected_params
            )
        
        # Create and start operation thread
        operation_thread = threading.Thread(
            target=self._execute_operation_thread,
            args=(context,),
            name=f"ProfileOperation_{operation_id}",
            daemon=True
        )
        
        self.operation_threads[operation_id] = operation_thread
        operation_thread.start()
        
        self.logger.info(f"Started profile operation: {operation_id} ({operation_type.value})")
        return operation_id
    
    def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel a running profile operation.
        
        Args:
            operation_id: ID of the operation to cancel
            
        Returns:
            bool: True if cancellation was initiated, False if operation not found
        """
        with self.operation_lock:
            context = self.active_operations.get(operation_id)
            if not context:
                self.logger.warning(f"Cannot cancel operation {operation_id}: not found")
                return False
            
            # Signal cancellation
            if context.cancellation_token:
                context.cancellation_token.set()
                self.logger.info(f"Cancellation requested for operation: {operation_id}")
                return True
            
        return False
    
    def get_operation_status(self, operation_id: str) -> Optional[OperationContext]:
        """
        Get the status of a profile operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            OperationContext or None if operation not found
        """
        with self.operation_lock:
            return self.active_operations.get(operation_id)
    
    def get_active_operations(self) -> List[str]:
        """
        Get list of active operation IDs.
        
        Returns:
            List of active operation IDs
        """
        with self.operation_lock:
            return list(self.active_operations.keys())
    
    def set_progress_callback(self, callback: Callable[[ProgressInfo], None]) -> None:
        """
        Set the default progress callback for all operations.
        
        Args:
            callback: Function to call with progress updates
        """
        self.default_progress_callback = callback
        self.logger.debug("Default progress callback set")
    
    def set_completion_callback(self, callback: Callable[[OperationResult], None]) -> None:
        """
        Set the default completion callback for all operations.
        
        Args:
            callback: Function to call when operations complete
        """
        self.default_completion_callback = callback
        self.logger.debug("Default completion callback set")
    
    def cleanup_completed_operations(self) -> int:
        """
        Clean up completed operation threads and contexts.
        
        Returns:
            int: Number of operations cleaned up
        """
        cleaned_count = 0
        
        with self.operation_lock:
            completed_operations = []
            
            for operation_id, thread in self.operation_threads.items():
                if not thread.is_alive():
                    completed_operations.append(operation_id)
            
            for operation_id in completed_operations:
                # Remove from active operations
                if operation_id in self.active_operations:
                    del self.active_operations[operation_id]
                
                # Remove thread reference
                if operation_id in self.operation_threads:
                    del self.operation_threads[operation_id]
                
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.debug(f"Cleaned up {cleaned_count} completed operations")
        
        return cleaned_count
    
    def shutdown(self, timeout: float = 30.0) -> bool:
        """
        Shutdown the manager and wait for all operations to complete.
        
        Args:
            timeout: Maximum time to wait for operations to complete
            
        Returns:
            bool: True if all operations completed within timeout
        """
        self.logger.info("Shutting down NonBlockingProfileManager")
        
        # Cancel all active operations
        with self.operation_lock:
            operation_ids = list(self.active_operations.keys())
        
        for operation_id in operation_ids:
            self.cancel_operation(operation_id)
        
        # Wait for all threads to complete
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.operation_lock:
                if not self.operation_threads:
                    break
                
                # Check if any threads are still alive
                alive_threads = [t for t in self.operation_threads.values() if t.is_alive()]
                if not alive_threads:
                    break
            
            time.sleep(0.1)
        
        # Force cleanup
        self.cleanup_completed_operations()
        
        # Check if shutdown was successful
        with self.operation_lock:
            remaining_operations = len(self.active_operations)
            if remaining_operations > 0:
                self.logger.warning(f"Shutdown incomplete: {remaining_operations} operations still active")
                return False
        
        # Stop performance monitoring
        if self.performance_monitor:
            try:
                self.performance_monitor.stop_monitoring()
            except Exception as e:
                self.logger.error(f"Error stopping performance monitor: {e}")
        
        self.logger.info("NonBlockingProfileManager shutdown complete")
        return True
    
    def _execute_operation_thread(self, context: OperationContext) -> None:
        """
        Execute a profile operation in a background thread.
        
        Args:
            context: Operation context with all necessary information
        """
        operation_id = context.operation_id
        operation_type = context.operation_type
        
        try:
            self.logger.info(f"Executing operation {operation_id} ({operation_type.value})")
            
            # Execute the appropriate operation
            if operation_type == OperationType.LOAD_FROM_DEVICE:
                result = self._execute_load_from_device(context)
            elif operation_type == OperationType.LOAD_TO_DEVICE:
                result = self._execute_load_to_device(context)
            elif operation_type == OperationType.LOAD_TO_UI:
                result = self._execute_load_to_ui(context)
            elif operation_type == OperationType.SAVE_FROM_UI:
                result = self._execute_save_from_ui(context)
            else:
                raise ValueError(f"Unsupported operation type: {operation_type}")
            
            # Calculate operation duration
            if context.start_time:
                result.operation_duration = (datetime.now() - context.start_time).total_seconds()
            
            self.logger.info(f"Operation {operation_id} completed: success={result.success}")
            
        except Exception as e:
            self.logger.error(f"Operation {operation_id} failed with exception: {str(e)}")
            
            # Create error result
            result = OperationResult(
                operation_id=operation_id,
                operation_type=operation_type,
                success=False,
                error_message=str(e),
                operation_duration=(datetime.now() - context.start_time).total_seconds() if context.start_time else 0.0
            )
        
        finally:
            # Finish performance monitoring
            if self.performance_monitor:
                try:
                    performance_profile = self.performance_monitor.finish_operation_monitoring(
                        operation_id, result.success, result.error_message
                    )
                    
                    # Log performance summary
                    self.logger.info(f"Operation {operation_id} performance: "
                                   f"duration={performance_profile.total_duration:.2f}s, "
                                   f"params={performance_profile.parameters_processed}, "
                                   f"rate={performance_profile.parameters_per_second:.2f} params/sec, "
                                   f"peak_memory={performance_profile.peak_memory_usage:.1f}MB")
                    
                    # Log optimization recommendations
                    if performance_profile.optimization_recommendations:
                        self.logger.info(f"Optimization recommendations for {operation_id}: "
                                       f"{'; '.join(performance_profile.optimization_recommendations)}")
                        
                except Exception as perf_error:
                    self.logger.error(f"Performance monitoring error for {operation_id}: {perf_error}")
            
            # Clean up progress update tracking
            if operation_id in self.last_progress_update:
                del self.last_progress_update[operation_id]
            
            # Call completion callback on main thread if provided
            if context.completion_callback:
                self._schedule_completion_callback(context.completion_callback, result)
            
            # Note: Don't automatically clean up operation context here
            # Let cleanup_completed_operations() handle it to allow status checking
    
    def _execute_load_from_device(self, context: OperationContext) -> OperationResult:
        """
        Execute load from device operation.
        
        Args:
            context: Operation context
            
        Returns:
            OperationResult with operation results
        """
        operation_id = context.operation_id
        file_path = context.file_path
        
        if not file_path:
            raise ValueError("file_path is required for load_from_device operation")
        
        # Check if operation was cancelled before starting
        if context.cancellation_token and context.cancellation_token.is_set():
            return OperationResult(
                operation_id=operation_id,
                operation_type=OperationType.LOAD_FROM_DEVICE,
                success=False,
                error_message="Operation cancelled before execution"
            )
        
        # Send initial progress update
        self._send_progress_update(context, 0, 100, "", "Initializing device read...")
        
        try:
            # Check device connection
            if not self._is_device_connected():
                raise RuntimeError("Device not connected")
            
            self._send_progress_update(context, 5, 100, "", "Reading device parameters...")
            
            # Get all parameter commands
            if not hasattr(self.app, 'configuration_reader_service') or not self.app.configuration_reader_service:
                raise RuntimeError("Configuration reader service not available")
            
            config_reader = self.app.configuration_reader_service
            all_commands = config_reader._get_all_parameter_commands()
            
            if not all_commands:
                raise RuntimeError("No parameter commands available")
            
            # Read parameters with optimized batching and progress updates
            parameters = {}
            successful_reads = 0
            failed_parameters = []
            total_commands = len(all_commands)
            
            # Process parameters in optimized batches
            for batch_start in range(0, total_commands, self.parameter_batch_size):
                batch_end = min(batch_start + self.parameter_batch_size, total_commands)
                batch_commands = all_commands[batch_start:batch_end]
                
                # Check for cancellation before each batch
                if context.cancellation_token and context.cancellation_token.is_set():
                    return OperationResult(
                        operation_id=operation_id,
                        operation_type=OperationType.LOAD_FROM_DEVICE,
                        success=False,
                        error_message="Operation cancelled by user",
                        parameters_processed=successful_reads,
                        failed_parameters=failed_parameters
                    )
                
                # Process batch
                for i, (param_name, command, command_type) in enumerate(batch_commands):
                    param_index = batch_start + i
                    
                    # Update progress (optimized frequency)
                    progress = 10 + int((param_index / total_commands) * 80)  # 10-90% for parameter reading
                    self._send_progress_update(context, progress, 100, param_name, f"Reading parameter: {param_name}")
                    
                    # Record parameter processing start time
                    param_start_time = time.time()
                    
                    try:
                        result = config_reader.read_specific_parameter(param_name, command, command_type, max_retries=1)
                        
                        if result.success and result.value is not None:
                            parameters[param_name] = str(result.value)
                            successful_reads += 1
                        else:
                            failed_parameters.append(param_name)
                            parameters[param_name] = ""  # Store empty value for failed parameters
                            
                    except Exception as param_error:
                        self.logger.warning(f"Failed to read parameter {param_name}: {str(param_error)}")
                        failed_parameters.append(param_name)
                        parameters[param_name] = ""
                    
                    # Record parameter processing time for performance monitoring
                    param_processing_time = time.time() - param_start_time
                    if self.performance_monitor:
                        self.performance_monitor.record_parameter_processed(
                            operation_id, param_name, param_processing_time
                        )
                
                # Trigger memory cleanup if needed
                if self.performance_monitor and self.performance_monitor.should_trigger_memory_cleanup():
                    self.performance_monitor.trigger_memory_cleanup()
                
                # Small delay between batches to prevent overwhelming the device
                if batch_end < total_commands:
                    time.sleep(0.05)  # 50ms delay between batches
            
            # Save to profile file using SimplifiedProfileFileHandler
            self._send_progress_update(context, 90, 100, "", "Saving profile file...")
            
            # Use SimplifiedProfileFileHandler to write the parameters directly
            from services.simplified_profile_file_handler import SimplifiedProfileFileHandler
            file_handler = SimplifiedProfileFileHandler()
            
            success, error_message = file_handler.write_universal_profile(file_path, parameters)
            
            if not success:
                raise RuntimeError(f"Failed to save profile file: {error_message}")
            
            self.logger.info(f"Successfully saved profile file: {file_path} with {len(parameters)} parameters")
            
            # Final progress update
            self._send_progress_update(context, 100, 100, "", "Operation completed successfully")
            
            return OperationResult(
                operation_id=operation_id,
                operation_type=OperationType.LOAD_FROM_DEVICE,
                success=True,
                parameters_processed=successful_reads,
                failed_parameters=failed_parameters,
                metadata={'total_parameters': total_commands, 'file_path': file_path}
            )
            
        except Exception as e:
            self._send_progress_update(context, 0, 100, "", f"Error: {str(e)}")
            raise
    
    def _execute_load_to_device(self, context: OperationContext) -> OperationResult:
        """
        Execute load to device operation.
        
        Args:
            context: Operation context
            
        Returns:
            OperationResult with operation results
        """
        operation_id = context.operation_id
        file_path = context.file_path
        parameters = context.parameters
        
        if not file_path and not parameters:
            raise ValueError("Either file_path or parameters is required for load_to_device operation")
        
        # Check if operation was cancelled before starting
        if context.cancellation_token and context.cancellation_token.is_set():
            return OperationResult(
                operation_id=operation_id,
                operation_type=OperationType.LOAD_TO_DEVICE,
                success=False,
                error_message="Operation cancelled before execution"
            )
        
        # Send initial progress update
        self._send_progress_update(context, 0, 100, "", "Loading profile file...")
        
        try:
            # Check device connection
            if not self._is_device_connected():
                raise RuntimeError("Device not connected")
            
            # If parameters not provided, read from file
            if not parameters:
                self._send_progress_update(context, 10, 100, "", "Reading profile file...")
                
                # Use SimplifiedProfileFileHandler to read the profile
                from services.simplified_profile_file_handler import SimplifiedProfileFileHandler
                file_handler = SimplifiedProfileFileHandler()
                parameters, error = file_handler.read_universal_profile(file_path)
                
                if error:
                    raise RuntimeError(f"Failed to read profile file: {error}")
                
                if not parameters:
                    raise RuntimeError("No parameters found in profile file")
            
            self._send_progress_update(context, 20, 100, "", "Preparing device communication...")
            
            # Get device communication manager directly
            if not hasattr(self.app, 'device_communication_manager') or not self.app.device_communication_manager:
                raise RuntimeError("Device communication manager not available")
            
            device_manager = self.app.device_communication_manager
            
            # Create progress callback for device operations
            def device_progress_callback(current_step, total_steps, current_param, status_msg):
                # Map device progress to overall progress (20-95%)
                if total_steps > 0:
                    device_progress = (current_step / total_steps) * 75  # 75% of total progress
                    overall_progress = 20 + device_progress
                    self._send_progress_update(context, int(overall_progress), 100, current_param, status_msg)
            
            self._send_progress_update(context, 25, 100, "", "Writing parameters to device...")
            
            # Write parameters to device using DeviceCommunicationManager
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                write_results = loop.run_until_complete(
                    device_manager.write_all_parameters(parameters, device_progress_callback)
                )
                
                # Check for cancellation after device operation
                if context.cancellation_token and context.cancellation_token.is_set():
                    return OperationResult(
                        operation_id=operation_id,
                        operation_type=OperationType.LOAD_TO_DEVICE,
                        success=False,
                        error_message="Operation cancelled during device writing",
                        parameters_processed=len([r for r in write_results.values() if r])
                    )
                
                # Process results
                successful_writes = sum(1 for success in write_results.values() if success)
                failed_parameters = [param for param, success in write_results.items() if not success]
                
                self._send_progress_update(context, 95, 100, "", "Finalizing operation...")
                
                # Determine success based on write results
                if successful_writes > 0:
                    self._send_progress_update(context, 100, 100, "", f"Successfully wrote {successful_writes}/{len(parameters)} parameters")
                    
                    return OperationResult(
                        operation_id=operation_id,
                        operation_type=OperationType.LOAD_TO_DEVICE,
                        success=True,
                        parameters_processed=successful_writes,
                        failed_parameters=failed_parameters,
                        metadata={'file_path': file_path, 'total_parameters': len(parameters)}
                    )
                else:
                    raise RuntimeError(f"Failed to write any parameters to device. Failed parameters: {failed_parameters}")
                    
            finally:
                loop.close()
                
        except Exception as e:
            self._send_progress_update(context, 0, 100, "", f"Error: {str(e)}")
            raise
    
    def _execute_load_to_ui(self, context: OperationContext) -> OperationResult:
        """
        Execute load to UI operation.
        
        Args:
            context: Operation context
            
        Returns:
            OperationResult with operation results
        """
        operation_id = context.operation_id
        file_path = context.file_path
        
        if not file_path:
            raise ValueError("file_path is required for load_to_ui operation")
        
        # Check if operation was cancelled before starting
        if context.cancellation_token and context.cancellation_token.is_set():
            return OperationResult(
                operation_id=operation_id,
                operation_type=OperationType.LOAD_TO_UI,
                success=False,
                error_message="Operation cancelled before execution"
            )
        
        # Send initial progress update
        self._send_progress_update(context, 0, 100, "", "Loading profile file...")
        
        try:
            # Use core profile manager to load profile to UI
            if hasattr(self.app, 'core_profile_manager'):
                core_manager = self.app.core_profile_manager
                success = core_manager.load_profile_to_ui(file_path)
                
                if success:
                    self._send_progress_update(context, 100, 100, "", "Profile loaded to UI successfully")
                    return OperationResult(
                        operation_id=operation_id,
                        operation_type=OperationType.LOAD_TO_UI,
                        success=True,
                        metadata={'file_path': file_path}
                    )
                else:
                    raise RuntimeError("Failed to load profile to UI")
            else:
                raise RuntimeError("Core profile manager not available")
                
        except Exception as e:
            self._send_progress_update(context, 0, 100, "", f"Error: {str(e)}")
            raise
    
    def _execute_save_from_ui(self, context: OperationContext) -> OperationResult:
        """
        Execute save from UI operation.
        
        Args:
            context: Operation context
            
        Returns:
            OperationResult with operation results
        """
        operation_id = context.operation_id
        file_path = context.file_path
        profile_name = context.profile_name
        
        if not file_path:
            raise ValueError("file_path is required for save_from_ui operation")
        
        # Check if operation was cancelled before starting
        if context.cancellation_token and context.cancellation_token.is_set():
            return OperationResult(
                operation_id=operation_id,
                operation_type=OperationType.SAVE_FROM_UI,
                success=False,
                error_message="Operation cancelled before execution"
            )
        
        # Send initial progress update
        self._send_progress_update(context, 0, 100, "", "Saving UI configuration...")
        
        try:
            # Use core profile manager to save profile from UI
            if hasattr(self.app, 'core_profile_manager'):
                core_manager = self.app.core_profile_manager
                success = core_manager.save_profile_from_ui(file_path, profile_name)
                
                if success:
                    self._send_progress_update(context, 100, 100, "", "Profile saved successfully")
                    return OperationResult(
                        operation_id=operation_id,
                        operation_type=OperationType.SAVE_FROM_UI,
                        success=True,
                        metadata={'file_path': file_path, 'profile_name': profile_name}
                    )
                else:
                    raise RuntimeError("Failed to save profile from UI")
            else:
                raise RuntimeError("Core profile manager not available")
                
        except Exception as e:
            self._send_progress_update(context, 0, 100, "", f"Error: {str(e)}")
            raise
    
    def _is_device_connected(self) -> bool:
        """
        Check if device is connected.
        
        Returns:
            bool: True if device is connected, False otherwise
        """
        try:
            # Check if serial service exists and is connected
            if not hasattr(self.app, 'serial_service') or not self.app.serial_service:
                return False
                
            if not getattr(self.app.serial_service, 'is_connected', False):
                return False
            
            # Check if configuration reader service is available
            if not hasattr(self.app, 'configuration_reader_service') or not self.app.configuration_reader_service:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking device connection: {str(e)}")
            return False
    
    def _send_progress_update(self, context: OperationContext, current_step: int, total_steps: int, 
                            current_parameter: str, status_message: str) -> None:
        """
        Send progress update using thread-safe callback with optimized frequency.
        
        Args:
            context: Operation context
            current_step: Current step number
            total_steps: Total number of steps
            current_parameter: Name of current parameter being processed
            status_message: Status message to display
        """
        if not context.progress_callback:
            return
        
        # Optimize progress update frequency to prevent UI flooding
        current_time = time.time()
        operation_id = context.operation_id
        
        # Check if enough time has passed since last update
        if operation_id in self.last_progress_update:
            time_since_last = current_time - self.last_progress_update[operation_id]
            if time_since_last < self.progress_update_interval and current_step < total_steps:
                return  # Skip this update to prevent flooding
        
        self.last_progress_update[operation_id] = current_time
        
        # Record progress update for performance monitoring
        if self.performance_monitor:
            self.performance_monitor.record_progress_update(operation_id, current_parameter)
        
        # Create progress info
        progress_info = ProgressInfo(
            operation_id=context.operation_id,
            operation_type=context.operation_type,
            current_step=current_step,
            total_steps=total_steps,
            current_parameter=current_parameter,
            status_message=status_message,
            can_cancel=True,
            is_complete=(current_step >= total_steps),
            success=(current_step >= total_steps)
        )
        
        # Schedule callback on main thread
        self._schedule_progress_callback(context.progress_callback, progress_info)
    
    def _schedule_progress_callback(self, callback: Callable, progress_info: ProgressInfo) -> None:
        """
        Schedule progress callback on main thread using tkinter's after() method.
        
        Args:
            callback: Progress callback function
            progress_info: Progress information to send
        """
        try:
            if hasattr(self.app, 'root') and self.app.root and hasattr(self.app.root, 'after_idle'):
                self.app.root.after_idle(lambda: self._safe_callback_execution(callback, progress_info))
            else:
                # Fallback: call directly (not thread-safe but better than nothing)
                self._safe_callback_execution(callback, progress_info)
        except Exception as e:
            self.logger.error(f"Error scheduling progress callback: {str(e)}")
    
    def _schedule_completion_callback(self, callback: Callable, result: OperationResult) -> None:
        """
        Schedule completion callback on main thread using tkinter's after() method.
        
        Args:
            callback: Completion callback function
            result: Operation result to send
        """
        try:
            if hasattr(self.app, 'root') and self.app.root and hasattr(self.app.root, 'after_idle'):
                self.app.root.after_idle(lambda: self._safe_callback_execution(callback, result))
            else:
                # Fallback: call directly (not thread-safe but better than nothing)
                self._safe_callback_execution(callback, result)
        except Exception as e:
            self.logger.error(f"Error scheduling completion callback: {str(e)}")
    
    def _safe_callback_execution(self, callback: Callable, *args) -> None:
        """
        Execute callback with error handling.
        
        Args:
            callback: Callback function to execute
            *args: Arguments to pass to callback
        """
        try:
            callback(*args)
        except Exception as e:
            self.logger.error(f"Error in callback execution: {str(e)}")