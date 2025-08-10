"""
Ultra Simple Profile Manager

This is an extremely simplified profile manager that eliminates all potential sources
of multiple dialogs, callback loops, and hanging operations.

Key principles:
1. Single execution path - no complex callback chains
2. Single dialog per operation - no multiple dialogs
3. Simple state management - clear operation states
4. Immediate error handling - no delayed callbacks
5. Direct UI updates - no wrapper functions

Updated to use LT32Pro components:
- LT32ProDeviceReader for device reading
- LT32ProDeviceWriter for device writing
- EnhancedParameterExtractor for parameter extraction
- LT32ProErrorHandler for improved error handling
"""

import os
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

# Import only essential components
from services.simplified_profile_file_handler import SimplifiedProfileFileHandler
from services.core_profile_manager import CoreProfileManager

# Import new LT32Pro components
from services.lt32pro_device_reader import LT32ProDeviceReader
from services.lt32pro_device_writer import LT32ProDeviceWriter
from services.enhanced_parameter_extractor import EnhancedParameterExtractor
from services.lt32pro_error_handler import LT32ProErrorHandler


@dataclass
class SimpleOperationResult:
    """Simple result of a profile operation."""
    success: bool
    operation_type: str  # 'device_to_profile' or 'profile_to_device'
    profile_path: str
    parameters_processed: int
    failed_parameters: List[str]
    error_message: Optional[str]
    operation_duration: float
    timestamp: datetime


class UltraSimpleProfileManager:
    """
    Ultra simple profile manager that eliminates all complexity.
    
    This version:
    - Uses NO progress dialogs (eliminates dialog issues)
    - Uses direct callbacks only (no wrapper functions)
    - Has simple state management (no complex state)
    - Provides immediate feedback (no delayed operations)
    """
    
    def __init__(self, app_instance):
        """Initialize the ultra simple profile manager."""
        self.app = app_instance
        self.i18n = getattr(app_instance, 'i18n_service', None) or getattr(app_instance, 'i18n', None)
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize only essential components
        self.file_handler = SimplifiedProfileFileHandler()
        self.core_manager = CoreProfileManager(app_instance)
        
        # Initialize new LT32Pro components
        self.device_reader = None  # Will be initialized when needed
        self.device_writer = None  # Will be initialized when needed
        self.parameter_extractor = EnhancedParameterExtractor()
        self.error_handler = LT32ProErrorHandler()
        
        # Simple state management
        self.is_busy = False
        
        self.logger.info("UltraSimpleProfileManager initialized with LT32Pro components")
    
    def _initialize_lt32pro_components(self):
        """Initialize LT32Pro components when needed."""
        try:
            if not self.device_reader and hasattr(self.app, 'serial_service'):
                self.device_reader = LT32ProDeviceReader(self.app.serial_service)
                self.logger.debug("LT32ProDeviceReader initialized")
            
            if not self.device_writer and hasattr(self.app, 'serial_service'):
                self.device_writer = LT32ProDeviceWriter(self.app.serial_service)
                self.logger.debug("LT32ProDeviceWriter initialized")
                
        except Exception as e:
            self.logger.error(f"Error initializing LT32Pro components: {e}")
            raise
    
    def _validate_connection(self):
        """Validate device connection - simple version."""
        try:
            if not hasattr(self.app, 'serial_service') or not self.app.serial_service:
                return False, "Serial service not available"
            
            if not getattr(self.app.serial_service, 'is_connected', False):
                return False, "Device not connected"
            
            if not hasattr(self.app, 'configuration_reader_service') or not self.app.configuration_reader_service:
                return False, "Configuration reader service not available"
            
            return True, ""
            
        except Exception as e:
            return False, f"Connection validation failed: {str(e)}"
    
    
    def _validate_connection_comprehensive(self):
        """Comprehensive connection validation with detailed error reporting."""
        try:
            # Check if app has serial service
            if not hasattr(self.app, 'serial_service') or not self.app.serial_service:
                return False, "Serial service not available. Please restart the application."
            
            serial_service = self.app.serial_service
            
            # Check if connected
            if not getattr(serial_service, 'is_connected', False):
                return False, "Device not connected. Please connect to the device first."
            
            # Check if configuration reader is available
            if not hasattr(self.app, 'configuration_reader_service') or not self.app.configuration_reader_service:
                return False, "Configuration reader service not available. Please restart the application."
            
            config_reader = self.app.configuration_reader_service
            
            # Try a simple communication test
            try:
                # Test if we can send a simple command (without timeout parameter)
                test_response = serial_service.send_command("ATSMS:STATUS#", bypass_validation=True)
                if test_response is None or test_response is False:
                    return False, "Device is not responding to commands. Please check: 1) Device is powered on, 2) Correct COM port selected, 3) Device is in configuration mode"
            except Exception as e:
                return False, f"Device communication test failed: {str(e)}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Connection validation failed: {str(e)}"


    
    def _read_device_configuration_sync(self, progress_callback: Optional[Callable] = None):
        """
        Read device configuration using LT32ProDeviceReader.
        
        This method uses the new LT32Pro components for improved device communication
        with proper command formatting and enhanced parameter extraction.
        """
        try:
            # Initialize LT32Pro components
            self._initialize_lt32pro_components()
            
            if not self.device_reader:
                raise Exception("Failed to initialize LT32Pro device reader")
            
            self.logger.info("Starting device configuration read with LT32Pro components...")
            
            # Create progress wrapper for LT32Pro reader
            def lt32pro_progress_callback(current_step, total_steps, step_description, success=True):
                """Progress callback for LT32Pro device reader."""
                if progress_callback:
                    try:
                        # Convert to the expected format
                        progress_callback(current_step, total_steps, step_description)
                    except Exception as e:
                        self.logger.debug(f"Progress callback failed (non-critical): {e}")
            
            # Read device configuration using LT32Pro reader
            device_responses = self.device_reader.read_device_configuration(
                progress_callback=lt32pro_progress_callback
            )
            
            if not device_responses:
                raise Exception("No responses received from device")
            
            self.logger.info(f"Received {len(device_responses)} responses from device")
            
            # Extract parameters using enhanced parameter extractor
            extracted_parameters = self.parameter_extractor.extract_parameters_from_responses(device_responses)
            
            if not extracted_parameters:
                raise Exception("No parameters extracted from device responses")
            
            self.logger.info(f"Extracted {len(extracted_parameters)} parameters from device responses")
            return extracted_parameters
            
        except Exception as e:
            # Use error handler for better error messages
            try:
                error_category = self.error_handler.categorize_error(e)
                suggestions = self.error_handler.get_recovery_suggestions(error_category, e)
                
                # Create user-friendly error message
                error_message = f"Device configuration read failed: {str(e)}"
                if suggestions:
                    error_message += f"\n\nTroubleshooting suggestions:\n" + "\n".join(f"• {s}" for s in suggestions[:3])
                
                self.logger.error(error_message)
                raise Exception(error_message)
            except Exception as handler_error:
                # Fallback to original error
                self.logger.error(f"Device configuration read failed: {e}")
                raise
    
    def load_from_device_to_profile(self, profile_path: str,
                                  progress_callback: Optional[Callable] = None,
                                  completion_callback: Optional[Callable] = None,
                                  show_progress_dialog: bool = False) -> None:
        """
        Load configuration from device and save to profile file - ultra simple version.
        
        Args:
            profile_path: Path where the profile file should be saved
            progress_callback: Optional callback for progress updates (step, total, message)
            completion_callback: Optional callback when operation is complete
            show_progress_dialog: Ignored - no progress dialogs in ultra simple version
        """
        if self.is_busy:
            self.logger.warning("Operation already running")
            if completion_callback:
                result = SimpleOperationResult(
                    success=False,
                    operation_type='device_to_profile',
                    profile_path=profile_path,
                    parameters_processed=0,
                    failed_parameters=[],
                    error_message="Another operation is already running",
                    operation_duration=0.0,
                    timestamp=datetime.now()
                )
                completion_callback(result)
            return
        
        # Start operation in background thread (validation will be done there)
        self.is_busy = True
        operation_thread = threading.Thread(
            target=self._execute_load_from_device,
            args=(profile_path, progress_callback, completion_callback),
            name="UltraSimpleLoadFromDevice",
            daemon=True
        )
        operation_thread.start()
    
    def _execute_load_from_device(self, profile_path: str, 
                                progress_callback: Optional[Callable],
                                completion_callback: Optional[Callable]):
        """Execute load from device operation - ultra simple version."""
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting load from device to: {profile_path}")
            
            # Simple progress update
            if progress_callback:
                progress_callback(1, 3, "Reading device configuration...")
            
            # Read device configuration using new LT32Pro components
            try:
                device_config = self._read_device_configuration_sync(progress_callback)
                
                if not device_config:
                    # Provide more specific error message
                    raise Exception("Failed to read device configuration. Please check: 1) Device is connected and powered on, 2) Correct COM port is selected, 3) Device is responding to commands, 4) No other applications are using the COM port")
                
                self.logger.info(f"Successfully read {len(device_config)} parameters from device")
                
            except Exception as device_error:
                # Use error handler for better error messages
                try:
                    error_category = self.error_handler.categorize_error(device_error)
                    suggestions = self.error_handler.get_recovery_suggestions(error_category, device_error)
                    
                    # Create user-friendly error message
                    error_message = f"Device communication failed: {str(device_error)}"
                    if suggestions:
                        error_message += f"\n\nTroubleshooting suggestions:\n" + "\n".join(f"• {s}" for s in suggestions[:3])
                    
                    raise Exception(error_message)
                except:
                    # Fallback to original error handling
                    self.logger.error(f"Device configuration read error: {str(device_error)}")
                    
                    # Provide user-friendly error message
                    if "timeout" in str(device_error).lower():
                        raise Exception("Device communication timeout. Please check device connection and try again.")
                    elif "permission" in str(device_error).lower():
                        raise Exception("COM port access denied. Please close other applications using the port and try again.")
                    elif "not found" in str(device_error).lower():
                        raise Exception("Device not found. Please check device connection and COM port settings.")
                    else:
                        raise Exception(f"Device communication failed: {str(device_error)}")
            
            # Simple progress update
            if progress_callback:
                progress_callback(2, 3, "Processing parameters...")
            
            # Save to profile file using simplified file handler
            success, error_msg = self.file_handler.write_universal_profile(profile_path, device_config)
            
            if not success:
                raise Exception(f"Failed to save profile file: {error_msg}")
            
            # Simple progress update
            if progress_callback:
                progress_callback(3, 3, "Operation completed")
            
            # Calculate results
            operation_duration = time.time() - start_time
            parameters_processed = len(device_config)
            
            self.logger.info(f"Load from device completed: {parameters_processed} parameters processed in {operation_duration:.2f}s")
            
            # Create success result
            result = SimpleOperationResult(
                success=True,
                operation_type='device_to_profile',
                profile_path=profile_path,
                parameters_processed=parameters_processed,
                failed_parameters=[],
                error_message=None,
                operation_duration=operation_duration,
                timestamp=datetime.now()
            )
            
            # Call completion callback
            if completion_callback:
                completion_callback(result)
                
        except Exception as e:
            operation_duration = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(f"Load from device failed: {error_msg}")
            
            # Create error result
            result = SimpleOperationResult(
                success=False,
                operation_type='device_to_profile',
                profile_path=profile_path,
                parameters_processed=0,
                failed_parameters=[],
                error_message=error_msg,
                operation_duration=operation_duration,
                timestamp=datetime.now()
            )
            
            # Call completion callback
            if completion_callback:
                completion_callback(result)
                
        finally:
            self.is_busy = False
    
    def load_from_profile_to_device(self, profile_path: str,
                                  progress_callback: Optional[Callable] = None,
                                  completion_callback: Optional[Callable] = None,
                                  show_progress_dialog: bool = False) -> None:
        """
        Load configuration from profile file and deploy to device - ultra simple version.
        
        Args:
            profile_path: Path to the profile file to load
            progress_callback: Optional callback for progress updates (step, total, message)
            completion_callback: Optional callback when operation is complete
            show_progress_dialog: Ignored - no progress dialogs in ultra simple version
        """
        if self.is_busy:
            self.logger.warning("Operation already running")
            if completion_callback:
                result = SimpleOperationResult(
                    success=False,
                    operation_type='profile_to_device',
                    profile_path=profile_path,
                    parameters_processed=0,
                    failed_parameters=[],
                    error_message="Another operation is already running",
                    operation_duration=0.0,
                    timestamp=datetime.now()
                )
                completion_callback(result)
            return
        
        # Validate connection
        is_connected, error_msg = self._validate_connection_comprehensive()
        if not is_connected:
            self.logger.error(f"Connection validation failed: {error_msg}")
            if completion_callback:
                result = SimpleOperationResult(
                    success=False,
                    operation_type='profile_to_device',
                    profile_path=profile_path,
                    parameters_processed=0,
                    failed_parameters=[],
                    error_message=error_msg,
                    operation_duration=0.0,
                    timestamp=datetime.now()
                )
                completion_callback(result)
            return
        
        # Validate profile file exists
        if not os.path.exists(profile_path):
            error_msg = f"Profile file does not exist: {profile_path}"
            self.logger.error(error_msg)
            if completion_callback:
                result = SimpleOperationResult(
                    success=False,
                    operation_type='profile_to_device',
                    profile_path=profile_path,
                    parameters_processed=0,
                    failed_parameters=[],
                    error_message=error_msg,
                    operation_duration=0.0,
                    timestamp=datetime.now()
                )
                completion_callback(result)
            return
        
        # Start operation in background thread
        self.is_busy = True
        operation_thread = threading.Thread(
            target=self._execute_load_to_device,
            args=(profile_path, progress_callback, completion_callback),
            name="UltraSimpleLoadToDevice",
            daemon=True
        )
        operation_thread.start()
    
    def _execute_load_to_device(self, profile_path: str,
                              progress_callback: Optional[Callable],
                              completion_callback: Optional[Callable]):
        """Execute load to device operation - ultra simple version."""
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting load to device from: {profile_path}")
            
            # Simple progress update
            if progress_callback:
                progress_callback(1, 4, "Reading profile file...")
            
            # Load profile parameters using simplified file handler
            profile_params, error_msg = self.file_handler.read_universal_profile(profile_path)
            
            # Ensure profile_params is a dictionary
            if not isinstance(profile_params, dict):
                raise Exception(f"Invalid profile data format: expected dictionary, got {type(profile_params)}")
            
            if not profile_params:
                raise Exception(f"Failed to load profile parameters: {error_msg}")
            
            # Simple progress update
            if progress_callback:
                progress_callback(2, 4, "Validating parameters...")
            
            # Simple validation
            if len(profile_params) == 0:
                raise Exception("Profile file contains no parameters")
            
            # Simple progress update
            if progress_callback:
                progress_callback(3, 4, "Writing to device...")
            
            # Write parameters to device using LT32ProDeviceWriter
            try:
                # Initialize LT32Pro components
                self._initialize_lt32pro_components()
                
                if not self.device_writer:
                    raise Exception("Failed to initialize LT32Pro device writer")
                
                # Create progress wrapper for LT32Pro writer
                def lt32pro_write_progress_callback(current_step, total_steps, step_description, success=True):
                    """Progress callback for LT32Pro device writer."""
                    if progress_callback:
                        try:
                            # Convert to the expected format
                            progress_callback(current_step + 2, 4, step_description)  # Offset by 2 for previous steps
                        except Exception as e:
                            self.logger.debug(f"Progress callback failed (non-critical): {e}")
                
                # Write parameters using LT32Pro writer
                write_results = self.device_writer.write_device_configuration(
                    profile_params, 
                    progress_callback=lt32pro_write_progress_callback
                )
                
                # Process results
                parameters_written = sum(1 for success in write_results.values() if success)
                failed_parameters = [param for param, success in write_results.items() if not success]
                
                self.logger.info(f"Device write completed: {parameters_written}/{len(profile_params)} parameters written")
                
            except Exception as write_error:
                # Use error handler for better error messages
                try:
                    error_category = self.error_handler.categorize_error(write_error)
                    suggestions = self.error_handler.get_recovery_suggestions(error_category, write_error)
                    
                    # Create user-friendly error message
                    error_message = f"Device write failed: {str(write_error)}"
                    if suggestions:
                        error_message += f"\n\nTroubleshooting suggestions:\n" + "\n".join(f"• {s}" for s in suggestions[:3])
                    
                    raise Exception(error_message)
                except:
                    # Fallback to original error
                    raise Exception(f"Device write failed: {str(write_error)}")
            
            # Initialize variables for backward compatibility
            parameters_written = parameters_written if 'parameters_written' in locals() else 0
            failed_parameters = failed_parameters if 'failed_parameters' in locals() else []
            
            # Simple progress update
            if progress_callback:
                progress_callback(4, 4, "Operation completed")
            
            # Calculate results
            operation_duration = time.time() - start_time
            
            if parameters_written == 0:
                raise Exception("No parameters were successfully written to device")
            
            self.logger.info(f"Load to device completed: {parameters_written}/{len(profile_params)} parameters written in {operation_duration:.2f}s")
            
            # Create success result
            result = SimpleOperationResult(
                success=True,
                operation_type='profile_to_device',
                profile_path=profile_path,
                parameters_processed=parameters_written,
                failed_parameters=failed_parameters,
                error_message=None,
                operation_duration=operation_duration,
                timestamp=datetime.now()
            )
            
            # Call completion callback with safety check
            if completion_callback:
                try:
                    # Ensure result is a proper SimpleOperationResult object
                    if not isinstance(result, SimpleOperationResult):
                        self.logger.error(f"Invalid result type: {type(result)}")
                        # Create a fallback result
                        result = SimpleOperationResult(
                            success=False,
                            operation_type='profile_to_device',
                            profile_path=profile_path,
                            parameters_processed=0,
                            failed_parameters=[],
                            error_message="Internal error: invalid result type",
                            operation_duration=time.time() - start_time,
                            timestamp=datetime.now()
                        )
                    completion_callback(result)
                except Exception as callback_error:
                    self.logger.error(f"Error in completion callback: {callback_error}")
                
        except Exception as e:
            operation_duration = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(f"Load to device failed: {error_msg}")
            
            # Create error result
            result = SimpleOperationResult(
                success=False,
                operation_type='profile_to_device',
                profile_path=profile_path,
                parameters_processed=0,
                failed_parameters=[],
                error_message=error_msg,
                operation_duration=operation_duration,
                timestamp=datetime.now()
            )
            
            # Call completion callback with safety check
            if completion_callback:
                try:
                    completion_callback(result)
                except Exception as callback_error:
                    self.logger.error(f"Error in completion callback: {callback_error}")
                
        finally:
            self.is_busy = False
    
    def validate_profile_file(self, profile_path: str) -> tuple:
        """
        Validate a profile file - simple version.
        
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        try:
            return self.file_handler.validate_universal_profile(profile_path)
        except Exception as e:
            return False, f"Profile validation error: {str(e)}"
    
    def load_profile_to_ui(self, profile_path: str) -> bool:
        """Load profile parameters to UI."""
        try:
            return self.core_manager.load_profile_to_ui(profile_path)
        except Exception as e:
            self.logger.error(f"Load profile to UI failed: {e}")
            return False
    
    def save_profile_from_ui(self, profile_path: str, profile_name: str = None) -> bool:
        """Save current UI parameters to profile file."""
        try:
            return self.core_manager.save_profile_from_ui(profile_path, profile_name)
        except Exception as e:
            self.logger.error(f"Save profile from UI failed: {e}")
            return False
    
    def get_profile_parameter_count(self, profile_path: str) -> int:
        """Get the number of parameters in a profile file."""
        try:
            return self.file_handler.get_parameter_count(profile_path)
        except Exception as e:
            self.logger.error(f"Error getting parameter count: {e}")
            return 0
    
    def is_profile_file_valid(self, profile_path: str) -> bool:
        """Check if a profile file is valid."""
        is_valid, _ = self.validate_profile_file(profile_path)
        return is_valid
    
    def show_user_confirmation_for_warnings(self, warnings: List, operation_context: Dict[str, Any]) -> bool:
        """
        Show user confirmation for warnings - ultra simple version.
        
        In ultra simple mode, we always continue (no complex dialogs).
        """
        if warnings:
            self.logger.info(f"Operation has {len(warnings)} warnings - continuing in simple mode")
        return True
    
    def create_recovery_summary(self, recovery_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a recovery summary - ultra simple version.
        
        Args:
            recovery_context: Dictionary containing recovery context information
            
        Returns:
            Dictionary with recovery summary information
        """
        # Extract recovery actions from context
        recovery_actions = recovery_context.get('recovery_actions', []) if isinstance(recovery_context, dict) else []
        
        # Create summary dictionary
        summary = {
            'recovery_actions': recovery_actions,
            'recovery_count': len(recovery_actions),
            'success_rate_percent': 100.0,  # Default success rate
            'has_recovery': len(recovery_actions) > 0,
            'summary_text': ""
        }
        
        if not recovery_actions:
            summary['summary_text'] = "No recovery actions were needed."
        else:
            summary_text = f"Recovery Summary ({len(recovery_actions)} actions):\\n"
            for i, action in enumerate(recovery_actions, 1):
                summary_text += f"{i}. {action}\\n"
            summary['summary_text'] = summary_text
        
        return summary
    
    def update_recovery_statistics(self, recovery_summary: Dict[str, Any]) -> None:
        """
        Update recovery statistics - ultra simple version.
        
        Args:
            recovery_summary: Recovery summary dictionary
        """
        try:
            # In ultra simple mode, just log the recovery statistics
            recovery_count = recovery_summary.get('recovery_count', 0)
            success_rate = recovery_summary.get('success_rate_percent', 100.0)
            
            if recovery_count > 0:
                self.logger.info(f"Recovery statistics updated: {recovery_count} actions, {success_rate:.1f}% success rate")
            else:
                self.logger.info("No recovery actions needed - operation completed successfully")
                
        except Exception as e:
            self.logger.error(f"Error updating recovery statistics: {e}")
    
    def cleanup(self):
        """Clean up resources - simple version."""
        try:
            self.is_busy = False
            self.logger.info("UltraSimpleProfileManager cleanup completed")
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")


# Create an alias for backward compatibility
ProfileManager = UltraSimpleProfileManager