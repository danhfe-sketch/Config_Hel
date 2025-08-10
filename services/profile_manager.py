"""
Profile Manager - Manages bidirectional profile operations for LT32Pro device configurations.

This module provides functionality for:
1. Loading configuration from device and saving to profile file
2. Loading configuration from profile file and deploying to device
3. Validating profile file format and content
4. Error handling for profile operations
5. Progress indication with cancellation support
"""

import os
import re
import time
import threading
import configparser
import platform
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable, Tuple
import logging

# Import progress dialog components
try:
    from ui.profile_progress_dialog import ProfileProgressManager, ProfileProgressInfo
    from ui.simple_device_progress_dialog import (
        SimpleDeviceProgressDialog, SimpleProgressInfo,
        create_device_to_profile_progress, create_profile_to_device_progress
    )
    from ui.ultra_simple_progress_dialog import (
        UltraSimpleProgressDialog, UltraSimpleProgressInfo,
        create_ultra_simple_progress_info
    )
except ImportError:
    # Fallback if progress dialog is not available
    ProfileProgressManager = None
    ProfileProgressInfo = None
    SimpleDeviceProgressDialog = None
    SimpleProgressInfo = None
    UltraSimpleProgressDialog = None
    UltraSimpleProgressInfo = None

# Import simplified profile manager
from services.simple_profile_manager import SimpleProfileManager

# Import profile data models
from services.profile_data_models import ProfileData, ProfileMetadata, ValidationInfo, ValidationResult as ProfileValidationResult, WriteResult



# Import operation logger
from services.profile_operation_logger import get_profile_operation_logger

# Import file handler and related components
from services.profile_file_handler import ProfileFileHandler
from services.profile_validator import ProfileValidator
from services.profile_converter import ProfileConverter
from services.profile_error_handler import ProfileErrorHandler, ErrorReport


@dataclass
class ValidationResult:
    """Result of validating a profile file."""
    is_valid: bool
    error_message: str
    error_code: str = None


@dataclass
class ProfileOperationResult:
    """Result of a profile operation (device-to-profile or profile-to-device)."""
    success: bool
    operation_type: str  # 'profile_to_device' or 'device_to_profile'
    profile_path: str
    parameters_processed: int
    failed_parameters: List[str]
    error_message: Optional[str]
    operation_duration: float
    timestamp: datetime
    error_details: Optional[Dict[str, Any]] = None


@dataclass
class DeploymentResult:
    """Result of deploying a profile to a device."""
    success: bool
    commands_sent: int
    successful_commands: int
    failed_commands: List[str]
    deployment_log: List[str]
    ui_updates_applied: bool
    error_details: Optional[Dict[str, str]] = None


class ProfileManager:
    def _validate_device_connection(self):
        """Check if the serial service is available and connected."""
        if not hasattr(self.app, 'serial_service'):
            return False, self.i18n.get('no_serial_service', 'Serial service not available')
        if not self.app.serial_service.is_connected:
            return False, self.i18n.get('device_not_connected', 'Device not connected')
        return True, ""

    def _validate_file_access(self, file_path, mode='read'):
        """Validate that a file can be accessed for reading or writing."""
        try:
            if mode == 'read':
                if not os.path.exists(file_path):
                    return False, self.i18n.get('file_not_found', 'File not found')
                if not os.access(file_path, os.R_OK):
                    return False, self.i18n.get('file_not_readable', 'File not readable')
            elif mode == 'write':
                # Check if directory exists and is writable
                dir_name = os.path.dirname(file_path)
                if not os.path.exists(dir_name):
                    return False, self.i18n.get('directory_not_found', 'Directory not found')
                if not os.access(dir_name, os.W_OK):
                    return False, self.i18n.get('directory_not_writable', 'Directory not writable')
            return True, ""
        except Exception as e:
            return False, str(e)

    def validate_connection_required(self):
        """
        Validate that device connection is available.
        Always returns a result object with is_valid and error_message properties.
        """
        class Result:
            def __init__(self, is_valid, error_message='', error_code=None):
                self.is_valid = is_valid
                self.error_message = error_message
                self.error_code = error_code

        # Use enhanced validation method
        is_connected, error_message = self._validate_device_connection()
        
        if is_connected:
            return Result(True)
        else:
            # Determine error code based on error message
            error_code = 'DEVICE_NOT_CONNECTED'
            if 'serial service' in error_message.lower():
                error_code = 'NO_SERIAL_SERVICE'
            
            return Result(False, error_message, error_code)

    def _write_profile_file_with_validation(self, profile_path, profile_info, device_parameters):
        """
        Write the profile file using the enhanced standardized format with validation.
        """
        try:
            # Use the enhanced save_profile_with_validation method
            device_info = {
                'imei': profile_info.get('device_imei'),
                'version': profile_info.get('device_version'),
                'iccid': profile_info.get('device_iccid')
            }
            
            # Remove None values from device_info
            device_info = {k: v for k, v in device_info.items() if v is not None}
            
            write_result = self.save_profile_with_validation(profile_path, device_info, device_parameters)
            
            if not write_result.success:
                raise Exception(f"Failed to write profile file: {write_result.error_message}")
            
            self.logger.info(f"Successfully wrote standardized profile file: {profile_path} ({write_result.bytes_written} bytes)")
            
        except Exception as e:
            self.logger.error(f"Error writing profile file with standardized format: {str(e)}")
            # Fallback to legacy method for compatibility
            self._write_profile_file_legacy_fallback(profile_path, profile_info, device_parameters)

    def _write_profile_file_legacy_fallback(self, profile_path, profile_info, device_parameters):
        """
        Legacy fallback method for writing profile files.
        """
        self.logger.warning("Using legacy profile writing method as fallback")
        
        try:
            import configparser
            config = configparser.ConfigParser()
            config.optionxform = str  # Preserve case in option names
            
            # Add Profile_Info section with standardized keys
            config.add_section('Profile_Info')
            config.set('Profile_Info', 'profile_name', 
                      profile_info.get('profile_name', f"LT32Pro_Config_{datetime.now().strftime('%Y%m%d_%H%M%S')}"))
            config.set('Profile_Info', 'created_date', 
                      profile_info.get('created_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            config.set('Profile_Info', 'format_version', self.profile_version)
            config.set('Profile_Info', 'app_version', 
                      profile_info.get('app_version', self.profile_version))
            config.set('Profile_Info', 'parameter_count', str(len(device_parameters)))
            
            # Add device information if available
            if profile_info.get('device_imei'):
                config.set('Profile_Info', 'device_imei', profile_info['device_imei'])
            if profile_info.get('device_version'):
                config.set('Profile_Info', 'device_version', profile_info['device_version'])
            if profile_info.get('device_iccid'):
                config.set('Profile_Info', 'device_iccid', profile_info['device_iccid'])
            
            # Add Device_Parameters section
            config.add_section('Device_Parameters')
            for key, value in device_parameters.items():
                config.set('Device_Parameters', key, str(value))
            
            # Write to file with UTF-8 encoding
            with open(profile_path, 'w', encoding='utf-8') as f:
                config.write(f)
                
            self.logger.info(f"Successfully wrote legacy format profile file: {profile_path}")
            
        except Exception as fallback_error:
            self.logger.error(f"Legacy fallback also failed: {str(fallback_error)}")
            raise Exception(f"Both standardized and legacy profile writing failed: {str(fallback_error)}")

    def __init__(self, app_instance):
        """
        Initialize the profile manager.
        
        Args:
            app_instance: Main application instance
        """
        self.app = app_instance
        self.i18n = app_instance.i18n_service if hasattr(app_instance, 'i18n_service') else None
        self.profile_version = '1.0'  # Current profile format version
        self.is_operation_running = False
        self.operation_thread = None
        self.cancel_requested = False
        self.progress_callback = None
        self.completion_callback = None
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize enhanced operation logger
        self.operation_logger = get_profile_operation_logger()
        
        # Initialize new profile components
        self.file_handler = ProfileFileHandler()
        self.validator = ProfileValidator()
        self.converter = ProfileConverter()
        self.error_handler = ProfileErrorHandler()
        
        # Initialize progress dialog manager
        self.progress_manager = None
        if ProfileProgressManager:
            self.progress_manager = ProfileProgressManager(app_instance)
        
        # Current progress dialog ID
        self.current_progress_dialog = None
        
        # Enhanced error recovery configuration
        self.error_recovery_config = {
            'max_parameter_failures': 15,  # Maximum failed parameters before aborting
            'continue_on_warnings': True,   # Continue operation with warnings
            'auto_sanitize_values': True,   # Automatically sanitize invalid values
            'create_recovery_log': True,    # Create detailed recovery logs
            'prompt_user_on_warnings': True, # Ask user confirmation for warnings
            'graceful_degradation': True,   # Enable graceful degradation for partial failures
            'parameter_level_continuation': True,  # Continue processing even with parameter failures
            'detailed_context_logging': True,     # Enable detailed context logging
            'recovery_summary_dialog': True,      # Show recovery summary to user
            'max_recovery_attempts': 3,           # Maximum recovery attempts per parameter
            'backup_on_partial_failure': True,    # Create backup when partial failure occurs
            'user_confirmation_threshold': 5,     # Show confirmation if warnings exceed this number
            'enable_partial_success_recovery': True,  # Allow partial success operations
            'min_success_rate_threshold': 0.3,    # Minimum success rate to consider operation viable
            'create_recovery_backups': True,      # Create backups during recovery operations
            'log_recovery_metrics': True,         # Log detailed recovery metrics
            'show_recovery_progress': True,       # Show recovery progress to user
            'enable_smart_defaults': True,        # Use intelligent default values during recovery
            'recovery_retry_delays': [1, 2, 5],   # Retry delays in seconds for recovery attempts
            'enable_context_preservation': True   # Preserve operation context across recovery attempts
        }
        
        # Parameter to section mapping for organizing profile data
        self.parameter_to_section = {
            # APN Configuration
            'apn_server': 'APN_Configuration',
            'apn_user': 'APN_Configuration',
            'apn_password': 'APN_Configuration',
            'transmission_mode': 'APN_Configuration',
            
            # Server Configuration
            'server_ip': 'Server_Configuration',
            'server_port': 'Server_Configuration',
            'server_protocol': 'Server_Configuration',
            'backup_server_ip': 'Server_Configuration',
            'backup_server_port': 'Server_Configuration',
            'gt06_protocol': 'Server_Configuration',
            
            # Timer Settings
            'timer_ign_on': 'Timer_Settings',
            'timer_ign_off': 'Timer_Settings',
            'heartbeat_ign_on': 'Timer_Settings',
            'heartbeat_ign_off': 'Timer_Settings',
            'heartbeat_interval': 'Timer_Settings',
            
            # Device Parameters
            'vibration': 'Device_Parameters',
            'sensitivity': 'Device_Parameters',
            'lock_type': 'Device_Parameters',
            'ignition_type': 'Device_Parameters',
            'curve_sensor': 'Device_Parameters',
            
            # Alert Settings
            'movement_alert': 'Alert_Settings',
            'power_alert': 'Alert_Settings',
            'battery_alert': 'Alert_Settings',
            'speed_limit': 'Alert_Settings',
            'moving_alert': 'Alert_Settings',
            'acc_on_alert': 'Alert_Settings',
            'acc_off_alert': 'Alert_Settings',
            
            # Advanced Settings
            'sleep_mode': 'Advanced_Settings',
            'sleep_time': 'Advanced_Settings',
            'network_select': 'Advanced_Settings',
            'volte_switch': 'Advanced_Settings',
            'defense_time': 'Advanced_Settings',
            'vibration_window': 'Advanced_Settings',
            'blind_speed': 'Advanced_Settings',
            'angle_reporting': 'Advanced_Settings',
            'relay_gps_check': 'Advanced_Settings',
            # Miscellaneous
            'odometer': 'Miscellaneous',
            'hourmeter': 'Miscellaneous'
        }
        
        # Default values for parameters (used when creating new profiles)
        self.default_values = {
            'apn_server': '',
            'apn_user': '',
            'apn_password': '',
            'transmission_mode': 'TCP',
            'server_ip': '',
            'server_port': '8080',
            'server_protocol': 'TCP',
            'gt06_protocol': 'GT06-0x60',
            'timer_ign_on': '30',
            'timer_ign_off': '300',
            'heartbeat_ign_on': '60',
            'heartbeat_ign_off': '300',
            'vibration': '128',
            'sensitivity': '5',
            'lock_type': 'PIN',
            'ignition_type': 'Digital',
            'curve_sensor': 'Auto',
            'sleep_mode': 'Disabled',
            'network_select': 'AUTO'
        }
        
        # Recovery statistics tracking
        self.recovery_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'partial_success_operations': 0,
            'failed_operations': 0,
            'parameters_recovered': 0,
            'parameters_failed': 0,
            'recovery_actions_taken': 0
        }
        
        # Session-level warning ignore list for user convenience
        self.ignored_warning_types = set()

    def _create_progress_dialog(self, operation_type, title):
        """Create and show a progress dialog for the given operation."""
        if not self.progress_manager:
            return

        # Create progress info based on operation type
        if operation_type == 'device_to_profile':
            progress_info = create_device_to_profile_progress(1, 4, self.i18n)
        elif operation_type == 'profile_to_device':
            progress_info = create_profile_to_device_progress()
        else:
            progress_info = create_ultra_simple_progress_info(title, "Initializing...")

        # Create and show the dialog
        self.current_progress_dialog = self.progress_manager.create_dialog(title, progress_info)
        self.progress_manager.show_dialog(self.current_progress_dialog)

    def _should_continue_after_parameter_error(self, recovery_context: Dict[str, Any]) -> bool:
        """
        Determine if operation should continue after parameter error based on recovery context.
        
        Args:
            recovery_context: Context information about the recovery operation
            
        Returns:
            bool: True if operation should continue, False if it should abort
        """
        if not self.error_recovery_config.get('graceful_degradation', True):
            return False
        
        total_params = len(recovery_context.get('successful_parameters', [])) + len(recovery_context.get('failed_parameters', []))
        failed_count = len(recovery_context.get('failed_parameters', []))
        
        if total_params == 0:
            return True  # No parameters processed yet
        
        # Check maximum failure threshold
        max_failures = self.error_recovery_config.get('max_parameter_failures', 15)
        if failed_count >= max_failures:
            self._log_message(f"ERROR: Aborting operation - failed parameter count ({failed_count}) exceeds maximum threshold ({max_failures})")
            return False
        
        # Check minimum success rate threshold
        success_rate = (total_params - failed_count) / total_params if total_params > 0 else 0
        min_success_rate = self.error_recovery_config.get('min_success_rate_threshold', 0.3)
        
        if success_rate < min_success_rate:
            self._log_message(f"ERROR: Aborting operation - success rate ({success_rate:.2%}) below minimum threshold ({min_success_rate:.2%})")
            return False
        
        self._log_message(f"INFO: Continuing operation - success rate ({success_rate:.2%}) acceptable, {failed_count} failures within limits")
        return True

    def _handle_parameter_error_with_continuation(self, param_name: str, param_value: Any, 
                                                error: Exception, recovery_context: Dict[str, Any]) -> Any:
        """
        Handle parameter error with continuation logic and recovery strategies.
        
        Args:
            param_name: Name of the parameter that failed
            param_value: Original parameter value that caused the error
            error: Exception that occurred
            recovery_context: Context information for recovery
            
        Returns:
            Recovered parameter value or None if recovery failed
        """
        # Record the error detection
        recovery_action = {
            'action': 'parameter_error_detected',
            'parameter': param_name,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'original_value': param_value,
            'timestamp': datetime.now().isoformat()
        }
        recovery_context.setdefault('recovery_actions', []).append(recovery_action)
        
        # Log detailed error context
        self._log_detailed_error_context(error, recovery_context, 'parameter_processing')
        
        # Attempt recovery using multiple strategies
        recovered_value = self._attempt_parameter_recovery_with_strategies(
            param_name, param_value, error, recovery_context
        )
        
        if recovered_value is not None:
            # Record successful recovery
            recovery_action = {
                'action': 'parameter_recovered',
                'parameter': param_name,
                'original_value': param_value,
                'recovered_value': recovered_value,
                'timestamp': datetime.now().isoformat()
            }
            recovery_context['recovery_actions'].append(recovery_action)
            
            # Add to successful parameters
            recovery_context.setdefault('successful_parameters', []).append({
                'name': param_name,
                'value': recovered_value,
                'original_value': param_value,
                'recovered': True
            })
            
            self._log_message(f"INFO: Successfully recovered parameter '{param_name}': '{param_value}' -> '{recovered_value}'")
            return recovered_value
        else:
            # Record failed recovery
            recovery_context.setdefault('failed_parameters', []).append({
                'name': param_name,
                'value': param_value,
                'error': str(error),
                'error_type': type(error).__name__,
                'timestamp': datetime.now().isoformat()
            })
            
            self._log_message(f"WARNING: Failed to recover parameter '{param_name}': {str(error)}")
            return None

    def _attempt_parameter_recovery_with_strategies(self, param_name: str, param_value: Any,
                                                  error: Exception, recovery_context: Dict[str, Any]) -> Any:
        """
        Attempt parameter recovery using multiple strategies.
        
        Args:
            param_name: Name of the parameter
            param_value: Original parameter value
            error: Exception that occurred
            recovery_context: Recovery context information
            
        Returns:
            Recovered value or None if all strategies failed
        """
        recovery_strategies = [
            self._attempt_basic_sanitization,
            self._attempt_context_aware_recovery,
            self._attempt_default_value_recovery,
            self._attempt_smart_default_recovery
        ]
        
        for i, strategy in enumerate(recovery_strategies):
            try:
                if strategy == self._attempt_context_aware_recovery:
                    recovered_value = strategy(param_name, param_value, error, recovery_context)
                else:
                    recovered_value = strategy(param_name, param_value, error)
                
                if recovered_value is not None:
                    strategy_name = strategy.__name__.replace('_attempt_', '').replace('_recovery', '').replace('_', ' ')
                    self._log_message(f"INFO: Parameter '{param_name}' recovered using {strategy_name} strategy")
                    return recovered_value
                    
            except Exception as strategy_error:
                self._log_message(f"WARNING: Recovery strategy {i+1} failed for '{param_name}': {str(strategy_error)}")
                continue
        
        return None

    def _attempt_basic_sanitization(self, param_name: str, param_value: Any, error: Exception) -> Any:
        """
        Attempt basic sanitization of parameter value.
        
        Args:
            param_name: Parameter name
            param_value: Original value
            error: Original error
            
        Returns:
            Sanitized value or None if sanitization failed
        """
        if param_value is None:
            return None
        
        try:
            # Convert to string and sanitize
            str_value = str(param_value).strip()
            
            # Remove common problematic characters
            sanitized = str_value.replace('\n', '').replace('\r', '').replace('\t', ' ')
            
            # Remove extra whitespace
            sanitized = ' '.join(sanitized.split())
            
            # If it's a numeric parameter, try to extract numbers
            if param_name in ['server_port', 'timer_ign_on', 'timer_ign_off', 'heartbeat_ign_on', 
                             'heartbeat_ign_off', 'vibration', 'sensitivity', 'speed_limit']:
                import re
                numbers = re.findall(r'\d+', sanitized)
                if numbers:
                    sanitized = numbers[0]
            
            # Return sanitized value if it's different and non-empty
            if sanitized and sanitized != str(param_value):
                return sanitized
                
        except Exception:
            pass
        
        return None

    def _attempt_context_aware_recovery(self, param_name: str, param_value: Any, 
                                      error: Exception, recovery_context: Dict[str, Any]) -> Any:
        """
        Attempt context-aware recovery using information from other parameters.
        
        Args:
            param_name: Parameter name
            param_value: Original value
            error: Original error
            recovery_context: Recovery context with other parameter values
            
        Returns:
            Context-derived value or None if recovery failed
        """
        successful_params = recovery_context.get('successful_parameters', [])
        
        # Create lookup dictionary for successful parameters
        param_values = {}
        for param in successful_params:
            param_values[param['name']] = param['value']
        
        # Context-aware recovery strategies
        if param_name == 'server_ip' and 'backup_server_ip' in param_values:
            return param_values['backup_server_ip']
        
        if param_name == 'backup_server_ip' and 'server_ip' in param_values:
            return param_values['server_ip']
        
        if param_name == 'server_port' and 'backup_server_port' in param_values:
            return param_values['backup_server_port']
        
        if param_name.endswith('_port') and 'server_port' in param_values:
            return param_values['server_port']
        
        # Timer value context recovery
        if param_name == 'heartbeat_ign_on' and 'timer_ign_on' in param_values:
            try:
                timer_value = int(param_values['timer_ign_on'])
                return str(timer_value * 2)  # Heartbeat typically 2x timer
            except (ValueError, TypeError):
                pass
        
        if param_name == 'heartbeat_ign_off' and 'timer_ign_off' in param_values:
            try:
                timer_value = int(param_values['timer_ign_off'])
                return str(timer_value)  # Same as timer off
            except (ValueError, TypeError):
                pass
        
        return None

    def _attempt_default_value_recovery(self, param_name: str, param_value: Any, error: Exception) -> Any:
        """
        Attempt recovery using default values.
        
        Args:
            param_name: Parameter name
            param_value: Original value
            error: Original error
            
        Returns:
            Default value or None if no default available
        """
        return self.default_values.get(param_name)

    def _attempt_smart_default_recovery(self, param_name: str, param_value: Any, error: Exception) -> Any:
        """
        Attempt recovery using smart default value generation.
        
        Args:
            param_name: Parameter name
            param_value: Original value
            error: Original error
            
        Returns:
            Smart default value or None if generation failed
        """
        return self._get_smart_default_value(param_name, param_value, error, {})

    def _get_smart_default_value(self, param_name: str, param_value: Any, 
                                error: Exception, recovery_context: Dict[str, Any]) -> Any:
        """
        Generate smart default values based on parameter type and context.
        
        Args:
            param_name: Parameter name
            param_value: Original value
            error: Original error
            recovery_context: Recovery context
            
        Returns:
            Smart default value or None
        """
        # Smart defaults based on parameter patterns
        if param_name == 'apn_server':
            return 'internet.provider.com'
        
        if param_name in ['server_ip', 'backup_server_ip']:
            return '0.0.0.0'  # Will need to be configured by user
        
        if param_name in ['server_port', 'backup_server_port']:
            return '8080'
        
        if param_name.startswith('timer_'):
            if 'ign_on' in param_name:
                return '30'
            elif 'ign_off' in param_name:
                return '300'
            else:
                return '60'
        
        if param_name.startswith('heartbeat_'):
            if 'ign_on' in param_name:
                return '60'
            elif 'ign_off' in param_name:
                return '300'
            else:
                return '120'
        
        if param_name == 'vibration':
            return '128'
        
        if param_name == 'sensitivity':
            return '5'
        
        if param_name == 'transmission_mode':
            return 'TCP'
        
        if param_name == 'server_protocol':
            return 'TCP'
        
        return None

    def _cancel_operation(self):
        """Cancel the current profile operation with enhanced cleanup."""
        self.cancel_requested = True
        self._log_message("INFO: Profile operation cancellation requested by user")
        
        # Try to interrupt the operation thread if it's running
        if self.operation_thread and self.operation_thread.is_alive():
            self._log_message("INFO: Attempting to interrupt operation thread")
            
            # Set a timeout for cancellation
            cancellation_timeout = 10.0  # 10 seconds
            cancellation_start = time.time()
            
            # Wait for thread to finish or timeout
            while (self.operation_thread.is_alive() and 
                   (time.time() - cancellation_start) < cancellation_timeout):
                time.sleep(0.1)
            
            if self.operation_thread.is_alive():
                self._log_message("WARNING: Operation thread did not respond to cancellation within timeout")
                # Force mark operation as not running
                self.is_operation_running = False
                
                # Show cancellation completed in dialog
                if self.current_progress_dialog and self.progress_manager:
                    # Create cancellation progress info
                    if ProfileProgressInfo:
                        cancel_info = ProfileProgressInfo(
                            operation_type=getattr(self, 'current_operation_type', 'unknown'),
                            current_step=0,
                            total_steps=4,
                            current_parameter="",
                            status_message="Operation cancelled due to timeout",
                            is_cancelled=True
                        )
                        self.progress_manager.update_progress(self.current_progress_dialog, cancel_info)
            else:
                self._log_message("INFO: Operation thread cancelled successfully")

    def load_from_device_to_profile(self, profile_path: str,
                                  progress_callback: Optional[Callable] = None,
                                  completion_callback: Optional[Callable] = None,
                                  show_progress_dialog: bool = True) -> None:
        """
        Load configuration from device and save to profile file.
        
        Args:
            profile_path: Path where the profile file should be saved
            progress_callback: Optional callback for progress updates (current, total, status)
            completion_callback: Optional callback when operation is complete (result)
            show_progress_dialog: Whether to show progress dialog (default: True)
        """
        if self.is_operation_running:
            error_msg = self.i18n.get('profile_operation_already_running', 
                                    'Profile operation is already in progress')
            if completion_callback:
                result = ProfileOperationResult(
                    success=False,
                    operation_type='device_to_profile',
                    profile_path=profile_path,
                    parameters_processed=0,
                    failed_parameters=[],
                    error_message=error_msg,
                    operation_duration=0.0,
                    timestamp=datetime.now()
                )
                completion_callback(result)
            return
        
        # Validate connection
        connection_validation = self.validate_connection_required()
        if not connection_validation.is_valid:
            if completion_callback:
                result = ProfileOperationResult(
                    success=False,
                    operation_type='device_to_profile',
                    profile_path=profile_path,
                    parameters_processed=0,
                    failed_parameters=[],
                    error_message=connection_validation.error_message,
                    operation_duration=0.0,
                    timestamp=datetime.now()
                )
                completion_callback(result)
            return
        
        # Validate profile path for writing using enhanced validation
        if profile_path:
            is_valid, error_message = self._validate_file_access(profile_path, 'write')
            if not is_valid:
                if completion_callback:
                    result = ProfileOperationResult(
                        success=False,
                        operation_type='device_to_profile',
                        profile_path=profile_path,
                        parameters_processed=0,
                        failed_parameters=[],
                        error_message=error_message,
                        operation_duration=0.0,
                        timestamp=datetime.now()
                    )
                    completion_callback(result)
                return
        
        # Only use progress_callback if not showing progress dialog to avoid duplicate dialogs
        self.progress_callback = progress_callback if not show_progress_dialog else None
        self.completion_callback = completion_callback
        self.cancel_requested = False
        self.is_operation_running = True
        
        # Create progress dialog if requested and available
        if show_progress_dialog and self.progress_manager:
            self._create_progress_dialog('device_to_profile', 'Load Configuration from Device')
        
        # Start operation in a separate thread
        self.operation_thread = threading.Thread(
            target=self._device_to_profile_worker,
            args=(profile_path,),
            daemon=True
        )
        self.operation_thread.start()

    def _device_to_profile_worker(self, profile_path: str) -> None:
        """
        Worker thread for device-to-profile operation with comprehensive error recovery.
        
        Args:
            profile_path: Path where the profile file should be saved
        """
        # Start enhanced operation logging
        operation_id = self.operation_logger.start_operation('save_device_to_profile', {
            'profile_path': profile_path,
            'thread_id': threading.current_thread().ident
        })
        
        start_time = time.time()
        parameters_processed = 0
        failed_parameters = []
        success = False
        error_msg = None
        partial_success = False
        recovery_context = {
            'operation': 'device_to_profile',
            'operation_id': operation_id,
            'start_time': start_time,
            'profile_path': profile_path,
            'total_parameters': 0,
            'successful_parameters': [],
            'failed_parameters': [],
            'warnings': [],
            'recovery_actions': []
        }
        
        try:
            # Log operation start with detailed information
            self._log_profile_operation_start('device_to_profile', profile_path)
            self.operation_logger.log_operation_step(operation_id, "operation_started", {
                'profile_path': profile_path,
                'recovery_config': self.error_recovery_config
            })
            
            # Update progress dialog
            self._update_progress_dialog(1, 4, "Initializing", "Preparing to read device configuration", 'device_to_profile')
            self._log_profile_operation_progress('device_to_profile', 1, 4, "Initializing device configuration read")
            
            # Check if ConfigurationReaderService is available
            if not hasattr(self.app, 'configuration_reader_service'):
                error_msg = self._get_localized_error_message('config_reader_not_available',
                    'Configuration reader service is not available. Please ensure the device communication module is properly initialized.')
                raise ValueError(error_msg)
            
            # Step 1: Read configuration from device
            self._update_progress_dialog(1, 4, "Reading Device", "Connecting to device and reading current configuration", 'device_to_profile')
            self._log_profile_operation_progress('device_to_profile', 1, 4, "Reading device configuration")
            
            if self.progress_callback:
                self.app.after(0, self.progress_callback, 1, 4, 
                             self.i18n.get('profile_reading_device', 'Reading device configuration...'))
            
            # Use ConfigurationReaderService to read all parameters
            config_reader = self.app.configuration_reader_service
            
            # Create a temporary completion callback to capture the read result
            read_result = [None]
            read_error = [None]
            read_completed_event = threading.Event()

            def read_completion_callback(result, error=None):
                read_result[0] = result
                read_error[0] = error
                read_completed_event.set()
                self._log_message("INFO: read_completed_event set.")

            # Start reading configuration
            self._log_message("INFO: Calling config_reader.read_all_configurations...")
            config_reader.read_all_configurations(
                completion_callback=read_completion_callback,
                show_progress_dialog=False
            )
            self._log_message("INFO: config_reader.read_all_configurations called.")

            # Wait for reading to complete
            max_wait_time = 120  # Increased timeout to 120 seconds
            wait_start = time.time()
            read_completed = False
            self._log_message(f"INFO: Waiting for read_completed_event with a timeout of {max_wait_time} seconds...")
            
            while (time.time() - wait_start) < max_wait_time:
                if self.cancel_requested:
                    self._log_message("INFO: Device-to-profile operation canceled by user")
                    if hasattr(config_reader, 'cancel_reading'):
                        config_reader.cancel_reading()
                    break
                
                if read_completed_event.wait(timeout=0.1):  # Poll for completion
                    read_completed = True
                    self._log_message("INFO: read_completed_event received successfully.")
                    break

            self._log_message(f"INFO: Finished waiting for read_completed_event. Event was set: {read_completed}")
            
            # Check if reading completed
            if not read_completed:
                self._log_message(f"ERROR: Device read did not complete within the {max_wait_time}-second timeout.")
                error_msg = self._get_localized_error_message('device_read_timeout',
                    'Timeout waiting for device configuration. The device may not be responding or the connection may be unstable. Please check the connection and try again.')
                
                # Show timeout error in progress dialog
                if self.current_progress_dialog and self.progress_manager:
                    self.progress_manager.show_error(self.current_progress_dialog, error_msg, "timeout")
                
                raise TimeoutError(error_msg)
            
            # Check if reading was successful or partially successful
            if not read_result[0]:
                error_msg = self._get_localized_error_message('device_read_no_result',
                    'No response received from device. Please verify the device is connected and powered on.')
                raise ValueError(error_msg)
            
            # Handle partial success - some parameters read successfully, others failed
            if not read_result[0].success:
                if read_result[0].parameters_read and any(p.success for p in read_result[0].parameters_read):
                    # Partial success - some parameters were read successfully
                    partial_success = True
                    self._log_message(f"WARNING: Partial device configuration read - {len([p for p in read_result[0].parameters_read if p.success])} parameters successful, {len([p for p in read_result[0].parameters_read if not p.success])} failed")
                else:
                    # Complete failure
                    error_msg = self._get_localized_error_message('device_read_complete_failure',
                        f'Failed to read device configuration. Error: {read_error[0] if read_error[0] else "Unknown communication error"}')
                    raise ValueError(error_msg)
            
            # Step 2: Convert device configuration to profile data
            # Don't update progress here - let the parameter loop handle it
            self._log_profile_operation_progress('device_to_profile', 2, 4, "Processing configuration data")
            
            if self.progress_callback:
                self.app.after(0, self.progress_callback, 2, 4, 
                             self.i18n.get('profile_processing_data', 'Processing configuration data...'))
            
            # Extract device information
            device_info = {}
            
            # First, look for specific device info parameters
            for param_result in read_result[0].parameters_read:
                if param_result.parameter_name == 'device_info' and param_result.success:
                    # Parse raw response for IMEI and other device info
                    if 'IMEI' in param_result.raw_response:
                        match = re.search(r'IMEI[=:]\s*(\d+)', param_result.raw_response)
                        if match:
                            device_info['imei'] = match.group(1)
                    
                    if 'VERSION' in param_result.raw_response or 'version' in param_result.raw_response.lower():
                        device_info['version'] = param_result.raw_response.strip()
            
            # Also check for IMEI in get_imei parameter
            for param_result in read_result[0].parameters_read:
                if param_result.parameter_name == 'get_imei' and param_result.success:
                    if param_result.value:
                        device_info['imei'] = param_result.value
                    elif 'IMEI' in param_result.raw_response:
                        match = re.search(r'IMEI[=:]\s*(\d+)', param_result.raw_response)
                        if match:
                            device_info['imei'] = match.group(1)
            
            # Check for version in get_version parameter
            for param_result in read_result[0].parameters_read:
                if param_result.parameter_name == 'get_version' and param_result.success:
                    if param_result.value:
                        device_info['version'] = param_result.value
                    else:
                        device_info['version'] = param_result.raw_response.strip()
            
            # Check for ICCID in get_iccid parameter
            for param_result in read_result[0].parameters_read:
                if param_result.parameter_name == 'get_iccid' and param_result.success:
                    if param_result.value:
                        device_info['iccid'] = param_result.value
                    elif 'ICCID' in param_result.raw_response:
                        match = re.search(r'ICCID[=:]\s*(\d+)', param_result.raw_response)
                        if match:
                            device_info['iccid'] = match.group(1)
            
            # Convert read parameters to configuration data with comprehensive error recovery
            config_data = {}
            communication_errors = []
            total_read_parameters = len(read_result[0].parameters_read)
            processed_count = 0
            recovery_context['total_parameters'] = total_read_parameters

            # Track odometer and hourmeter values if found
            odometer_value = None
            hourmeter_value = None

            # Parameter-level error handling with continuation
            for param_result in read_result[0].parameters_read:
                processed_count += 1

                # Update progress dialog with parameter-level tracking
                self._update_progress_dialog(
                    2.0, 4,
                    param_result.parameter_name,
                    f"Converting device parameter to profile format",
                    'device_to_profile',
                    parameter_index=processed_count,
                    total_parameters=total_read_parameters,
                    current_operation='processing'
                )

                # Attempt to process parameter with error recovery
                if param_result.success and param_result.value is not None:
                    try:
                        param_name = param_result.parameter_name

                        # Special handling for odometer and hourmeter
                        if param_name == 'odometer':
                            odometer_value = param_result.value
                        if param_name == 'hourmeter':
                            hourmeter_value = param_result.value

                        # Validate parameter value before adding to config
                        validated_value = self._validate_and_sanitize_parameter(
                            param_name, param_result.value, recovery_context
                        )

                        config_data[param_name] = validated_value
                        parameters_processed += 1
                        recovery_context['successful_parameters'].append({
                            'name': param_name,
                            'value': validated_value,
                            'original_value': param_result.value
                        })

                    except Exception as param_error:
                        # Parameter-level error handling with continuation
                        self._handle_parameter_error_with_continuation(
                            param_name, param_result.value, param_error, recovery_context
                        )
                        failed_parameters.append(param_name)
                        recovery_context['failed_parameters'].append({
                            'name': param_name,
                            'value': param_result.value,
                            'error': str(param_error),
                            'error_type': type(param_error).__name__
                        })

                        # Check if we should continue or abort based on error recovery config
                        if not self._should_continue_after_parameter_error(recovery_context):
                            break

                else:
                    # Parameter read failed - handle with continuation
                    param_name = param_result.parameter_name
                    error_msg = f"Failed to read parameter: {param_result.error_message or 'Unknown error'}"

                    self._handle_parameter_error_with_continuation(
                        param_name, None, Exception(error_msg), recovery_context
                    )
                    failed_parameters.append(param_name)
                    recovery_context['failed_parameters'].append({
                        'name': param_name,
                        'value': None,
                        'error': error_msg,
                        'error_type': 'ReadError'
                    })

                    # Check if we should continue or abort
                    if not self._should_continue_after_parameter_error(recovery_context):
                        break

            # Ensure odometer and hourmeter are present in config_data if found
            if odometer_value is not None:
                config_data['odometer'] = odometer_value
            if hourmeter_value is not None:
                config_data['hourmeter'] = hourmeter_value
            
            # Graceful degradation for partial profile loading failures
            if len(recovery_context['successful_parameters']) > 0:
                # We have some successful parameters - continue with partial success
                partial_success = True
                self._log_message(f"INFO: Partial success - {len(recovery_context['successful_parameters'])} parameters successful, {len(recovery_context['failed_parameters'])} failed")
                
                # Create recovery summary for partial success
                recovery_summary = self._create_recovery_summary_from_context(recovery_context)
                
                # Log detailed recovery context
                self._log_detailed_recovery_context(recovery_context, 'device_to_profile')
            else:
                # No successful parameters - complete failure
                error_msg = self._get_localized_error_message('device_read_no_successful_params',
                    f'Failed to read any device parameters successfully. Total failures: {len(recovery_context["failed_parameters"])}')
                raise ValueError(error_msg)
            
            # Step 3: Create profile metadata with device information
            total_params = recovery_context.get('total_parameters', 0)
            self._update_progress_dialog(3, 4, "Creating Profile", "Generating profile metadata and structure", 'device_to_profile',
                                       parameter_index=total_params, total_parameters=total_params)
            self._log_profile_operation_progress('device_to_profile', 3, 4, "Creating profile metadata")
            
            if self.progress_callback:
                self.app.after(0, self.progress_callback, 3, 4, 
                             self.i18n.get('profile_creating_metadata', 'Creating profile metadata...'))
            
            # Create profile metadata with recovery information
            profile_metadata = ProfileMetadata(
                profile_name=f"LT32Pro_Config_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                created_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                device_imei=device_info.get('imei'),
                device_version=device_info.get('version'),
                parameter_count=len(config_data),
                app_version=self.profile_version,
                checksum=None  # Will be calculated by file handler
            )
            
            # Create profile data with recovery context
            profile_data = ProfileData(
                metadata=profile_metadata,
                device_parameters=config_data,
                validation_info=ValidationInfo(
                    is_validated=True,
                    last_validated=datetime.now().isoformat(),
                    validation_version=self.profile_version,
                    validation_errors_count=0,
                    validation_warnings_count=0
                ),
                format_version=self.profile_version
            )
            
            # Add recovery context to profile data for later reference
            if hasattr(profile_data, 'recovery_context'):
                profile_data.recovery_context = recovery_context
            
            # Step 4: Save profile file with comprehensive error handling
            total_params = recovery_context.get('total_parameters', 0)
            self._update_progress_dialog(4, 4, "Saving Profile", "Writing profile data to file", 'device_to_profile',
                                       parameter_index=total_params, total_parameters=total_params)
            self._log_profile_operation_progress('device_to_profile', 4, 4, "Saving profile file")
            
            if self.progress_callback:
                self.app.after(0, self.progress_callback, 4, 4, 
                             self.i18n.get('profile_saving_file', 'Saving profile file...'))
            
            # Use ProfileFileHandler for robust file writing
            # Convert ProfileData to ConfigParser format
            config = configparser.ConfigParser()
            config.optionxform = str
            
            # Add Profile_Info section
            config.add_section('Profile_Info')
            config.set('Profile_Info', 'profile_name', profile_data.metadata.profile_name)
            config.set('Profile_Info', 'created_date', profile_data.metadata.created_date)
            config.set('Profile_Info', 'parameter_count', str(profile_data.metadata.parameter_count))
            if profile_data.metadata.device_imei:
                config.set('Profile_Info', 'device_imei', profile_data.metadata.device_imei)
            if profile_data.metadata.device_version:
                config.set('Profile_Info', 'device_version', profile_data.metadata.device_version)
            if profile_data.metadata.app_version:
                config.set('Profile_Info', 'app_version', profile_data.metadata.app_version)
            
            # Add Device_Parameters section
            config.add_section('Device_Parameters')
            for key, value in profile_data.device_parameters.items():
                config.set('Device_Parameters', key, str(value))
            
            # Write using the available method
            success, error_msg = self.file_handler.write_ini_file(profile_path, config)
            
            # Create write_result-like object for compatibility
            class WriteResult:
                def __init__(self, success, error_message=None):
                    self.success = success
                    self.error_message = error_message
            
            write_result = WriteResult(success, error_msg)
            
            if not write_result.success:
                error_msg = self._get_localized_error_message('profile_write_failed',
                    f'Failed to save profile file: {write_result.error_message}')
                raise IOError(error_msg)
            
            # Calculate operation duration
            operation_duration = time.time() - start_time
            
            # Create operation result with recovery information
            result = ProfileOperationResult(
                success=True,
                operation_type='device_to_profile',
                profile_path=profile_path,
                parameters_processed=parameters_processed,
                failed_parameters=failed_parameters,
                error_message=None,
                operation_duration=operation_duration,
                timestamp=datetime.now(),
                error_details=None
            )
            
            # Add recovery context to result
            result.recovery_context = recovery_context
            result.partial_success = partial_success
            
            # Update recovery statistics
            self._update_recovery_statistics_from_context(recovery_context, True, partial_success)
            
            success = True
            self._log_message(f"INFO: Device-to-profile operation completed successfully in {operation_duration:.2f} seconds")
            
        except Exception as e:
            # Comprehensive error handling with recovery context
            operation_duration = time.time() - start_time
            error_msg = str(e)
            
            # Log detailed error context
            self._log_detailed_error_context(e, recovery_context, 'device_to_profile')
            
            # Create error result with recovery information
            result = ProfileOperationResult(
                success=False,
                operation_type='device_to_profile',
                profile_path=profile_path,
                parameters_processed=parameters_processed,
                failed_parameters=failed_parameters,
                error_message=error_msg,
                operation_duration=operation_duration,
                timestamp=datetime.now(),
                error_details={'exception_type': type(e).__name__, 'traceback': str(e)}
            )
            
            # Add recovery context to result
            result.recovery_context = recovery_context
            
            # Update recovery statistics for failure
            self._update_recovery_statistics_from_context(recovery_context, False, False)
            
            self._log_message(f"ERROR: Device-to-profile operation failed after {operation_duration:.2f} seconds: {error_msg}")
            
        finally:
            # End enhanced operation logging
            additional_metrics = {
                'parameters_processed': parameters_processed,
                'file_size_bytes': os.path.getsize(profile_path) if os.path.exists(profile_path) else 0
            }
            self.operation_logger.end_operation(
                operation_id, 
                success=success, 
                error_message=error_msg,
                additional_metrics=additional_metrics
            )
            
            # Clean up operation state
            self.is_operation_running = False
            self.cancel_requested = False
            
            # Close progress dialog
            if hasattr(self, 'ultra_simple_dialog') and self.ultra_simple_dialog:
                self.ultra_simple_dialog.close()
                self.ultra_simple_dialog = None
            elif hasattr(self, 'simple_progress_dialog') and self.simple_progress_dialog:
                self.simple_progress_dialog.close()
                self.simple_progress_dialog = None
            elif self.current_progress_dialog and self.progress_manager:
                self.progress_manager.close_dialog(self.current_progress_dialog)
                self.current_progress_dialog = None
            
            # Show recovery summary dialog if enabled and there were recovery actions
            if (
                self.error_recovery_config.get('recovery_summary_dialog', True) and 
                hasattr(result, 'recovery_context') and result.recovery_context.get('recovery_actions')):
                self._show_recovery_summary_dialog(result.recovery_context, result)
            
            # Call completion callback with result
            self._log_message("INFO: Worker thread completing. Calling completion callback.")
            if self.completion_callback:
                try:
                    def safe_completion_callback():
                        try:
                            self.completion_callback(result)
                        except Exception as callback_error:
                            self._log_message(f"ERROR: Completion callback failed: {str(callback_error)}")
                    
                    self.app.after(0, safe_completion_callback)
                except Exception as callback_error:
                    self._log_message(f"ERROR: Failed to schedule completion callback: {str(callback_error)}")

    def show_user_confirmation_for_warnings(self, warnings: List, operation_context: Dict[str, Any]) -> bool:
        """
        Show comprehensive user confirmation dialog for operations with validation warnings.
        
        Args:
            warnings: List of validation warnings
            operation_context: Context information about the operation
            
        Returns:
            bool: True if user wants to continue, False to cancel
        """
        try:
            # Check if warnings should be ignored based on user preferences
            if self._should_ignore_warnings(warnings):
                self._log_message("INFO: Warnings ignored based on user preferences")
                return True
            
            # Check warning threshold for automatic continuation
            warning_count = len(warnings)
            threshold = self.error_recovery_config.get('user_confirmation_threshold', 5)
            
            if warning_count < threshold:
                # Below threshold - continue automatically but log warnings
                self._log_message(f"INFO: {warning_count} warnings found (below threshold of {threshold}), continuing automatically")
                self._log_warning_summary(warnings, 'auto_continue')
                return True
            
            # Analyze warnings for better user presentation
            warning_analysis = self._analyze_warnings_for_user_dialog(warnings)
            
            # Convert warnings to enhanced dialog format
            warning_dicts = []
            for warning in warnings:
                warning_dict = {
                    'parameter': getattr(warning, 'location', 'Unknown'),
                    'message': getattr(warning, 'message', 'No message'),
                    'suggestion': getattr(warning, 'suggestion', ''),
                    'category': self._categorize_warning(warning),
                    'severity': getattr(warning, 'severity', 'WARNING'),
                    'auto_fixable': self._is_warning_auto_fixable(warning),
                    'impact_level': self._assess_warning_impact(warning),
                    'recommended_action': self._get_recommended_action_for_warning(warning)
                }
                warning_dicts.append(warning_dict)
            
            # Create comprehensive operation context for dialog
            enhanced_context = {
                **operation_context,
                'warning_analysis': warning_analysis,
                'total_warnings': warning_count,
                'critical_warnings': warning_analysis['critical_count'],
                'auto_fixable_warnings': warning_analysis['auto_fixable_count'],
                'estimated_success_rate': self._estimate_success_rate_with_warnings(warnings),
                'recovery_options_available': self._check_recovery_options_available(warnings)
            }
            
            # Show enhanced warning confirmation dialog
            try:
                from ui.profile_warning_confirmation_dialog import show_enhanced_warning_confirmation_dialog
                dialog_function = show_enhanced_warning_confirmation_dialog
            except ImportError:
                # Fallback to basic dialog
                from ui.profile_warning_confirmation_dialog import show_warning_confirmation_dialog
                dialog_function = show_warning_confirmation_dialog
            
            operation_type = operation_context.get('operation_type', 'operation')
            title = f"Continue {operation_type.replace('_', ' ').title()} with {warning_count} Warnings?"
            
            # Create detailed message based on warning analysis
            if warning_analysis['critical_count'] > 0:
                message = f"The operation has {warning_count} warnings, including {warning_analysis['critical_count']} critical warnings that may affect operation success."
            else:
                message = f"The operation has {warning_count} warnings. Most can be automatically handled, but your confirmation is required."
            
            result = dialog_function(
                self.app, title, message, warning_dicts, enhanced_context
            )
            
            # Handle user choice with comprehensive logging
            if result.user_choice == 'continue':
                if hasattr(result, 'ignore_similar_warnings') and result.ignore_similar_warnings:
                    # Add warning types to ignore list for this session
                    ignored_types = set()
                    for warning in warnings:
                        warning_type = self._get_warning_type(warning)
                        self.ignored_warning_types.add(warning_type)
                        ignored_types.add(warning_type)
                    
                    self._log_message(f"INFO: User chose to ignore warning types: {', '.join(ignored_types)}")
                
                self._log_message(f"INFO: User chose to continue with {warning_count} warnings")
                self._log_warning_summary(warnings, 'user_continue')
                
                # Log user decision context
                self._log_user_decision_context('continue_with_warnings', enhanced_context)
                return True
                
            elif result.user_choice == 'fix_and_retry':
                # Attempt to auto-fix warnings if possible
                self._log_message(f"INFO: User requested auto-fix for {warning_count} warnings")
                fixed_count = self._attempt_comprehensive_auto_fix_warnings(warnings, enhanced_context)
                
                if fixed_count > 0:
                    self._log_message(f"INFO: Successfully auto-fixed {fixed_count} warnings, operation should be retried")
                    self._log_user_decision_context('fix_and_retry', enhanced_context, {'fixed_count': fixed_count})
                else:
                    self._log_message(f"WARNING: No warnings could be auto-fixed, user should manually address issues")
                
                return False
                
            elif result.user_choice == 'show_details':
                # User wants to see detailed warning information
                self._show_detailed_warning_information(warnings, enhanced_context)
                # Recursively show dialog again after showing details
                return self.show_user_confirmation_for_warnings(warnings, operation_context)
                
            else:  # cancel or any other choice
                self._log_message(f"INFO: User cancelled operation due to {warning_count} warnings")
                self._log_warning_summary(warnings, 'user_cancel')
                self._log_user_decision_context('cancel_due_to_warnings', enhanced_context)
                return False
                
        except Exception as e:
            self._log_message(f"ERROR: Failed to show warning confirmation dialog: {str(e)}")
            # Create error context for logging
            error_context = {
                'error': str(e),
                'warning_count': len(warnings) if warnings else 0,
                'operation_context': operation_context
            }
            self._log_user_decision_context('dialog_error', error_context)
            
            # Default behavior based on configuration
            if self.error_recovery_config.get('continue_on_warnings', True):
                self._log_message("INFO: Defaulting to continue due to dialog error and continue_on_warnings=True")
                return True
            else:
                self._log_message("INFO: Defaulting to cancel due to dialog error and continue_on_warnings=False")
                return False

    def create_recovery_summary(self, recovery_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create recovery summary from recovery context.
        
        Args:
            recovery_context: Recovery context information
            
        Returns:
            Dict with recovery summary information
        """
        return self._create_recovery_summary_from_context(recovery_context)

    def update_recovery_statistics(self, recovery_summary: Dict[str, Any]) -> None:
        """
        Update recovery statistics from recovery summary.
        
        Args:
            recovery_summary: Recovery summary information
        """
        try:
            # Update operation counts
            self.recovery_stats['total_operations'] += 1
            
            if recovery_summary.get('complete_success', False):
                self.recovery_stats['successful_operations'] += 1
            elif recovery_summary.get('partial_success', False):
                self.recovery_stats['partial_success_operations'] += 1
            else:
                self.recovery_stats['failed_operations'] += 1
            
            # Update parameter counts
            self.recovery_stats['parameters_recovered'] += recovery_summary.get('successful_parameters', 0)
            self.recovery_stats['parameters_failed'] += recovery_summary.get('failed_parameters', 0)
            self.recovery_stats['recovery_actions_taken'] += recovery_summary.get('recovery_actions', 0)
            
            # Log statistics update
            self._log_message(f"INFO: Recovery statistics updated - Total operations: {self.recovery_stats['total_operations']}")
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to update recovery statistics: {str(e)}")

    def _handle_parameter_error_with_continuation(self, param_name: str, param_value: Any, 
                                                error: Exception, recovery_context: Dict[str, Any]) -> Any:
        """
        Handle parameter-level errors with continuation logic and comprehensive recovery.
        
        Args:
            param_name: Name of the parameter that failed
            param_value: Value that caused the error
            error: The exception that occurred
            recovery_context: Recovery context for tracking
            
        Returns:
            Recovered parameter value if successful, None otherwise
        """
        try:
            # Log detailed parameter error with context
            error_context = {
                'parameter': param_name,
                'original_value': param_value,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'timestamp': datetime.now().isoformat()
            }
            
            self._log_message(f"WARNING: Parameter '{param_name}' failed with {type(error).__name__}: {str(error)}")
            
            # Add to recovery context with detailed information
            recovery_context['recovery_actions'].append({
                'action': 'parameter_error_detected',
                'parameter': param_name,
                'error': str(error),
                'error_type': type(error).__name__,
                'original_value': param_value,
                'timestamp': datetime.now().isoformat()
            })
            
            # Attempt multiple recovery strategies with retry logic
            max_attempts = self.error_recovery_config.get('max_recovery_attempts', 3)
            retry_delays = self.error_recovery_config.get('recovery_retry_delays', [1, 2, 5])
            
            for attempt in range(max_attempts):
                try:
                    # Strategy 1: Attempt parameter-level recovery with sanitization
                    if self.error_recovery_config.get('auto_sanitize_values', True):
                        recovered_value = self._attempt_parameter_recovery_with_strategies(
                            param_name, param_value, error, attempt, recovery_context
                        )
                        
                        if recovered_value is not None:
                            self._log_message(f"INFO: Parameter '{param_name}' recovered on attempt {attempt + 1} with value: {recovered_value}")
                            recovery_context['recovery_actions'].append({
                                'action': 'parameter_recovered',
                                'parameter': param_name,
                                'original_value': param_value,
                                'recovered_value': recovered_value,
                                'attempt': attempt + 1,
                                'timestamp': datetime.now().isoformat()
                            })
                            return recovered_value
                    
                    # Strategy 2: Use intelligent defaults based on parameter context
                    if self.error_recovery_config.get('enable_smart_defaults', True):
                        smart_default = self._get_smart_default_value(param_name, param_value, error, recovery_context)
                        if smart_default is not None:
                            self._log_message(f"INFO: Using smart default for '{param_name}': {smart_default}")
                            recovery_context['recovery_actions'].append({
                                'action': 'smart_default_applied',
                                'parameter': param_name,
                                'original_value': param_value,
                                'smart_default': smart_default,
                                'attempt': attempt + 1,
                                'timestamp': datetime.now().isoformat()
                            })
                            return smart_default
                    
                    # If we reach here, this attempt failed
                    if attempt < max_attempts - 1:
                        # Wait before next attempt
                        delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                        self._log_message(f"INFO: Recovery attempt {attempt + 1} failed for '{param_name}', retrying in {delay}s")
                        time.sleep(delay)
                    
                except Exception as recovery_attempt_error:
                    self._log_message(f"WARNING: Recovery attempt {attempt + 1} failed for '{param_name}': {str(recovery_attempt_error)}")
                    recovery_context['recovery_actions'].append({
                        'action': 'recovery_attempt_failed',
                        'parameter': param_name,
                        'attempt': attempt + 1,
                        'error': str(recovery_attempt_error),
                        'timestamp': datetime.now().isoformat()
                    })
            
            # All recovery attempts failed - log comprehensive failure information
            self._log_message(f"ERROR: All {max_attempts} recovery attempts failed for parameter '{param_name}'")
            recovery_context['recovery_actions'].append({
                'action': 'parameter_recovery_exhausted',
                'parameter': param_name,
                'total_attempts': max_attempts,
                'final_error': str(error),
                'timestamp': datetime.now().isoformat()
            })
            
            # Check if graceful degradation allows continuation
            if self.error_recovery_config.get('graceful_degradation', True):
                self._log_message(f"INFO: Continuing operation with graceful degradation despite '{param_name}' failure")
                recovery_context['recovery_actions'].append({
                    'action': 'graceful_degradation_applied',
                    'parameter': param_name,
                    'timestamp': datetime.now().isoformat()
                })
                return None  # Continue without this parameter
            else:
                # Re-raise the original error if graceful degradation is disabled
                raise error
            
        except Exception as recovery_error:
            self._log_message(f"ERROR: Critical failure in parameter error handling for '{param_name}': {str(recovery_error)}")
            recovery_context['recovery_actions'].append({
                'action': 'critical_recovery_failure',
                'parameter': param_name,
                'error': str(recovery_error),
                'timestamp': datetime.now().isoformat()
            })
            return None

    def _should_continue_after_parameter_error(self, recovery_context: Dict[str, Any]) -> bool:
        """
        Determine if operation should continue after a parameter error.
        
        Args:
            recovery_context: Current recovery context
            
        Returns:
            bool: True if operation should continue, False to abort
        """
        try:
            # Check if parameter-level continuation is enabled
            if not self.error_recovery_config.get('parameter_level_continuation', True):
                return False
            
            # Check maximum failure threshold
            max_failures = self.error_recovery_config.get('max_parameter_failures', 15)
            current_failures = len(recovery_context.get('failed_parameters', []))
            
            if current_failures >= max_failures:
                self._log_message(f"WARNING: Maximum parameter failures ({max_failures}) reached, aborting operation")
                return False
            
            # Check success rate threshold
            total_processed = len(recovery_context.get('successful_parameters', [])) + current_failures
            if total_processed > 0:
                success_rate = len(recovery_context.get('successful_parameters', [])) / total_processed
                min_success_rate = 0.3  # Minimum 30% success rate to continue
                
                if success_rate < min_success_rate and total_processed > 10:
                    self._log_message(f"WARNING: Success rate ({success_rate:.1%}) below threshold, aborting operation")
                    return False
            
            return True
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to determine continuation: {str(e)}")
            return False

    def _create_recovery_summary_from_context(self, recovery_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create recovery summary from recovery context.
        
        Args:
            recovery_context: Recovery context information
            
        Returns:
            Dict with recovery summary
        """
        try:
            successful_params = len(recovery_context.get('successful_parameters', []))
            failed_params = len(recovery_context.get('failed_parameters', []))
            total_params = successful_params + failed_params
            warnings = len(recovery_context.get('warnings', []))
            recovery_actions = len(recovery_context.get('recovery_actions', []))
            
            # Calculate success rate
            success_rate = (successful_params / total_params * 100) if total_params > 0 else 0
            
            # Determine operation result
            complete_success = failed_params == 0 and warnings == 0
            partial_success = successful_params > 0 and (failed_params > 0 or warnings > 0)
            
            # Calculate duration
            start_time = recovery_context.get('start_time', time.time())
            duration = time.time() - start_time
            
            # Categorize failures
            failure_categories = {}
            for failed_param in recovery_context.get('failed_parameters', []):
                error_type = failed_param.get('error_type', 'Unknown')
                failure_categories[error_type] = failure_categories.get(error_type, 0) + 1
            
            # Categorize recovery actions
            recovery_categories = {}
            for action in recovery_context.get('recovery_actions', []):
                action_type = action.get('action', 'unknown')
                recovery_categories[action_type] = recovery_categories.get(action_type, 0) + 1
            
            return {
                'operation_type': recovery_context.get('operation', 'unknown'),
                'total_parameters': total_params,
                'successful_parameters': successful_params,
                'failed_parameters': failed_params,
                'warnings': warnings,
                'recovery_actions': recovery_actions,
                'success_rate_percent': success_rate,
                'complete_success': complete_success,
                'partial_success': partial_success,
                'duration_seconds': duration,
                'failure_categories': failure_categories,
                'recovery_categories': recovery_categories,
                'profile_path': recovery_context.get('profile_path', ''),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to create recovery summary: {str(e)}")
            return {
                'operation_type': 'unknown',
                'total_parameters': 0,
                'successful_parameters': 0,
                'failed_parameters': 0,
                'complete_success': False,
                'partial_success': False,
                'error': str(e)
            }

    def _update_recovery_statistics_from_context(self, recovery_context: Dict[str, Any], 
                                               success: bool, partial_success: bool) -> None:
        """
        Update recovery statistics from recovery context.
        
        Args:
            recovery_context: Recovery context information
            success: Whether operation was successful
            partial_success: Whether operation had partial success
        """
        try:
            self.recovery_stats['total_operations'] += 1
            
            if success and not partial_success:
                self.recovery_stats['successful_operations'] += 1
            elif partial_success:
                self.recovery_stats['partial_success_operations'] += 1
            else:
                self.recovery_stats['failed_operations'] += 1
            
            # Update parameter counts
            successful_params = len(recovery_context.get('successful_parameters', []))
            failed_params = len(recovery_context.get('failed_parameters', []))
            recovery_actions = len(recovery_context.get('recovery_actions', []))
            
            self.recovery_stats['parameters_recovered'] += successful_params
            self.recovery_stats['parameters_failed'] += failed_params
            self.recovery_stats['recovery_actions_taken'] += recovery_actions
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to update recovery statistics from context: {str(e)}")

    def _log_detailed_recovery_context(self, recovery_context: Dict[str, Any], operation_type: str) -> None:
        """
        Log detailed recovery context information.
        
        Args:
            recovery_context: Recovery context to log
            operation_type: Type of operation being performed
        """
        try:
            if not self.error_recovery_config.get('detailed_context_logging', True):
                return
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            log_lines = [
                f"[{timestamp}] DETAILED_RECOVERY_CONTEXT - {operation_type}",
                "=" * 60,
                f"Operation: {recovery_context.get('operation', 'unknown')}",
                f"Profile Path: {recovery_context.get('profile_path', 'N/A')}",
                f"Total Parameters: {recovery_context.get('total_parameters', 0)}",
                f"Successful Parameters: {len(recovery_context.get('successful_parameters', []))}",
                f"Failed Parameters: {len(recovery_context.get('failed_parameters', []))}",
                f"Warnings: {len(recovery_context.get('warnings', []))}",
                f"Recovery Actions: {len(recovery_context.get('recovery_actions', []))}"
            ]
            
            # Add successful parameters details
            if recovery_context.get('successful_parameters'):
                log_lines.append("\nSUCCESSFUL PARAMETERS:")
                for param in recovery_context['successful_parameters'][:10]:  # First 10
                    log_lines.append(f"  {param.get('name', 'unknown')}: {param.get('value', 'N/A')}")
                if len(recovery_context['successful_parameters']) > 10:
                    log_lines.append(f"  ... and {len(recovery_context['successful_parameters']) - 10} more")
            
            # Add failed parameters details
            if recovery_context.get('failed_parameters'):
                log_lines.append("\nFAILED PARAMETERS:")
                for param in recovery_context['failed_parameters'][:10]:  # First 10
                    log_lines.append(f"  {param.get('name', 'unknown')}: {param.get('error', 'Unknown error')}")
                if len(recovery_context['failed_parameters']) > 10:
                    log_lines.append(f"  ... and {len(recovery_context['failed_parameters']) - 10} more")
            
            # Add recovery actions details
            if recovery_context.get('recovery_actions'):
                log_lines.append("\nRECOVERY ACTIONS:")
                for action in recovery_context['recovery_actions'][-5:]:
                    action_type = action.get('action', 'unknown')
                    timestamp = action.get('timestamp', 'N/A')
                    log_lines.append(f"  {timestamp}: {action_type}")
            
            log_lines.append("=" * 60)
            
            # Log the complete context
            full_log = "\n".join(log_lines)
            self._log_message(full_log)
            
        except Exception as e:
            self._log_message(f"ERROR: Failed to log detailed recovery context: {str(e)}")

    def _log_detailed_error_context(self, error: Exception, recovery_context: Dict[str, Any], 
                                  operation_type: str) -> None:
        """
        Log detailed error context information with comprehensive recovery tracking.
        
        Args:
            error: The exception that occurred
            recovery_context: Recovery context information
            operation_type: Type of operation that failed
        """
        try:
            if not self.error_recovery_config.get('detailed_context_logging', True):
                return
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            # Calculate operation metrics
            successful_params = len(recovery_context.get('successful_parameters', []))
            failed_params = len(recovery_context.get('failed_parameters', []))
            total_params = successful_params + failed_params
            success_rate = (successful_params / total_params * 100) if total_params > 0 else 0
            
            # Calculate operation duration
            start_time = recovery_context.get('start_time', time.time())
            duration = time.time() - start_time
            
            log_lines = [
                f"[{timestamp}] COMPREHENSIVE_ERROR_CONTEXT - {operation_type}",
                "=" * 80,
                "ERROR INFORMATION:",
                f"  Error Type: {type(error).__name__}",
                f"  Error Message: {str(error)}",
                f"  Error Module: {getattr(error, '__module__', 'unknown')}",
                "",
                "OPERATION CONTEXT:",
                f"  Operation: {recovery_context.get('operation', 'unknown')}",
                f"  Profile Path: {recovery_context.get('profile_path', 'N/A')}",
                f"  Operation Duration: {duration:.2f} seconds",
                f"  Start Time: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "PARAMETER PROCESSING METRICS:",
                f"  Total Parameters: {total_params}",
                f"  Successfully Processed: {successful_params}",
                f"  Failed Parameters: {failed_params}",
                f"  Success Rate: {success_rate:.1f}%",
                f"  Recovery Actions Attempted: {len(recovery_context.get('recovery_actions', []))}",
                ""
            ]
            
            # Add detailed failure analysis
            if recovery_context.get('failed_parameters'):
                log_lines.append("FAILED PARAMETERS ANALYSIS:")
                failure_categories = {}
                for failed_param in recovery_context['failed_parameters']:
                    error_type = failed_param.get('error_type', 'Unknown')
                    failure_categories[error_type] = failure_categories.get(error_type, 0) + 1
                
                for error_type, count in failure_categories.items():
                    log_lines.append(f"  {error_type}: {count} parameters")
                
                log_lines.append("\nFAILED PARAMETERS DETAILS:")
                for i, failed_param in enumerate(recovery_context['failed_parameters'][:10], 1):
                    param_name = failed_param.get('name', 'unknown')
                    param_error = failed_param.get('error', 'No error message')
                    log_lines.append(f"  {i}. {param_name}: {param_error}")
                
                if len(recovery_context['failed_parameters']) > 10:
                    remaining = len(recovery_context['failed_parameters']) - 10
                    log_lines.append(f"  ... and {remaining} more failed parameters")
                log_lines.append("")
            
            # Add recovery actions analysis
            if recovery_context.get('recovery_actions'):
                log_lines.append("RECOVERY ACTIONS ANALYSIS:")
                action_categories = {}
                for action in recovery_context['recovery_actions']:
                    action_type = action.get('action', 'unknown')
                    action_categories[action_type] = action_categories.get(action_type, 0) + 1
                
                for action_type, count in action_categories.items():
                    log_lines.append(f"  {action_type.replace('_', ' ').title()}: {count} actions")
                
                log_lines.append("\nRECENT RECOVERY ACTIONS:")
                for action in recovery_context['recovery_actions'][-5:]:
                    action_type = action.get('action', 'unknown')
                    action_timestamp = action.get('timestamp', 'N/A')
                    action_param = action.get('parameter', 'N/A')
                    log_lines.append(f"  {action_timestamp}: {action_type} for {action_param}")
                log_lines.append("")
            
            # Add system context information
            log_lines.extend([
                "SYSTEM CONTEXT:",
                f"  Python Version: {platform.python_version()}",
                f"  Platform: {platform.system()} {platform.release()}",
                f"  Process ID: {os.getpid()}",
                f"  Memory Usage: {self._get_memory_usage_mb():.1f} MB",
                f"  Thread Count: {threading.active_count()}",
                ""
            ])
            
            # Add recovery configuration context
            log_lines.extend([
                "RECOVERY CONFIGURATION:",
                f"  Graceful Degradation: {self.error_recovery_config.get('graceful_degradation', False)}",
                f"  Parameter Continuation: {self.error_recovery_config.get('parameter_level_continuation', False)}",
                f"  Auto Sanitize Values: {self.error_recovery_config.get('auto_sanitize_values', False)}",
                f"  Max Parameter Failures: {self.error_recovery_config.get('max_parameter_failures', 0)}",
                f"  Max Recovery Attempts: {self.error_recovery_config.get('max_recovery_attempts', 0)}",
                ""
            ])
            
            # Add stack trace if available
            import traceback
            if hasattr(error, '__traceback__'):
                log_lines.extend([
                    "STACK TRACE:",
                    traceback.format_exc(),
                    ""
                ])
            
            log_lines.append("=" * 80)
            
            # Log the complete context
            full_log = "\n".join(log_lines)
            self._log_message(full_log)
            
            # Also log to error handler for centralized error tracking
            if hasattr(self, 'error_handler'):
                self.error_handler.log_detailed_error_context(
                    error, recovery_context, include_system_info=True
                )
            
        except Exception as log_error:
            self._log_message(f"ERROR: Failed to log detailed error context: {str(log_error)}")

    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
        except Exception:
            return 0.0

    def _should_ignore_warnings(self, warnings: List) -> bool:
        """Check if warnings should be ignored based on user preferences."""
        try:
            for warning in warnings:
                warning_type = self._get_warning_type(warning)
                if warning_type not in self.ignored_warning_types:
                    return False
            return True
        except:
            return False

    def _categorize_warning(self, warning) -> str:
        """Categorize a warning for display purposes."""
        try:
            error_type = getattr(warning, 'error_type', None)
            if error_type:
                return error_type.value if hasattr(error_type, 'value') else str(error_type)
            return 'General'
        except:
            return 'General'

    def _is_warning_auto_fixable(self, warning) -> bool:
        """Check if a warning can be automatically fixed."""
        try:
            # Check if warning has a suggestion that can be auto-applied
            suggestion = getattr(warning, 'suggestion', '')
            if not suggestion:
                return False
            
            # Simple heuristics for auto-fixable warnings
            auto_fix_keywords = ['use default', 'set to', 'change to', 'remove invalid']
            return any(keyword in suggestion.lower() for keyword in auto_fix_keywords)
        except:
            return False

    def _get_warning_type(self, warning) -> str:
        """Get warning type for ignore tracking."""
        try:
            error_type = getattr(warning, 'error_type', None)
            if error_type:
                return error_type.value if hasattr(error_type, 'value') else str(error_type)
            return 'general_warning'
        except:
            return 'general_warning'

    def _attempt_auto_fix_warnings(self, warnings: List) -> int:
        """Attempt to automatically fix warnings that can be auto-fixed."""
        fixed_count = 0
        try:
            for warning in warnings:
                if self._is_warning_auto_fixable(warning):
                    # Implement auto-fix logic here
                    # This would depend on the specific warning type
                    fixed_count += 1
        except Exception as e:
            self._log_message(f"ERROR: Failed to auto-fix warnings: {str(e)}")
        return fixed_count

    def _attempt_parameter_recovery(self, param_name: str, param_value: Any, error: Exception) -> Any:
        """Attempt to recover a failed parameter with a default or sanitized value."""
        try:
            # Strategy 1: Use default value if available
            if param_name in self.default_values:
                default_value = self.default_values[param_name]
                recovery_msg = self._get_localized_error_message(
                    'recovery_using_default',
                    f"Using default value for '{param_name}': {default_value}"
                )
                self._log_message(f"INFO: {recovery_msg}")
                return default_value
            
            # Strategy 2: Sanitize the value based on error type
            if isinstance(error, ValueError) and param_value:
                sanitized = str(param_value).strip()
                if sanitized and sanitized != str(param_value):
                    recovery_msg = self._get_localized_error_message(
                        'recovery_parameter_fixed',
                        f"Parameter '{param_name}' was automatically corrected"
                    )
                    self._log_message(f"INFO: {recovery_msg}: '{param_value}' -> '{sanitized}'")
                    return sanitized
            
            # Strategy 3: Return None to indicate recovery failed
        except Exception as recovery_error:
            recovery_msg = self._get_localized_error_message(
                'recovery_attempt_failed',
                f"Recovery attempt failed for '{param_name}': {str(recovery_error)}"
            )
            self._log_message(f"ERROR: {recovery_msg}")
            return None

    def _attempt_parameter_recovery_with_strategies(self, param_name: str, param_value: Any, 
                                                  error: Exception, attempt: int, 
                                                  recovery_context: Dict[str, Any]) -> Any:
        """
        Attempt parameter recovery using multiple strategies based on attempt number.
        
        Args:
            param_name: Name of the parameter
            param_value: Original parameter value
            error: The error that occurred
            attempt: Current attempt number (0-based)
            recovery_context: Recovery context for tracking
        """
        # ... (rest of the file content)
    def save_profile_from_ui(self):
        """
        Save the current UI state to a profile file with comprehensive validation.
        """
        try:
            # Show file save dialog
            from tkinter import filedialog
            profile_path = filedialog.asksaveasfilename(
                title=self.i18n.get("save_profile_title", "Save Configuration Profile"),
                defaultextension=".lt32config",
                filetypes=[
                    ("LT32Pro Config Files", "*.lt32config"),
                    ("All Files", "*.*")
                ]
            )

            if not profile_path:
                return False  # User canceled

            # Step 1: Get all parameters from the UI
            if not hasattr(self.app, 'parameters_frame'):
                self._log_and_show_error("Parameters frame not found.", "UI Error")
                return False

            ui_parameters = self.app.parameters_frame.get_all_parameters()

            # Step 2: Get device information (if available)
            device_info = self._get_device_info_for_profile()

            # Step 3: Save the profile using the new centralized method
            write_result = self.save_profile_with_validation(
                profile_path,
                device_info,
                ui_parameters
            )

            # Step 4: Show user feedback
            if write_result.success:
                success_msg = self.i18n.get(
                    "profile_saved_successfully",
                    "Profile saved successfully to:\n{path}"
                ).format(path=profile_path)
                self._show_info_dialog("Profile Saved", success_msg)
                self._log_message(f"INFO: Profile saved from UI to {profile_path}")
                return True
            else:
                self._log_and_show_error(
                    f"Failed to save profile: {write_result.error_message}",
                    "Save Profile Failed"
                )
                return False

        except Exception as e:
            self._log_and_show_error(f"An unexpected error occurred while saving the profile: {str(e)}", "Save Profile Error")
            return False
