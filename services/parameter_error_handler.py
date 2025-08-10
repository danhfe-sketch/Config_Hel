"""
Parameter Error Handler for LT32 PRO Configurator

This module provides comprehensive error handling specifically for parameter operations,
including communication timeouts, invalid device responses, connection validation,
and user-friendly error messages with corrective actions.
"""

import time
import threading
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
import re


class ParameterErrorType(Enum):
    """Types of parameter operation errors."""
    COMMUNICATION_TIMEOUT = "communication_timeout"
    INVALID_RESPONSE = "invalid_response"
    CONNECTION_LOST = "connection_lost"
    DEVICE_NOT_RESPONDING = "device_not_responding"
    COMMAND_REJECTED = "command_rejected"
    PARSING_ERROR = "parsing_error"
    VALIDATION_ERROR = "validation_error"
    DEVICE_BUSY = "device_busy"
    PARAMETER_NOT_SUPPORTED = "parameter_not_supported"
    SEQUENCE_ERROR = "sequence_error"
    BUFFER_OVERFLOW = "buffer_overflow"
    CHECKSUM_ERROR = "checksum_error"


class ParameterErrorSeverity(Enum):
    """Severity levels for parameter errors."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ParameterError:
    """Detailed parameter operation error information."""
    error_type: ParameterErrorType
    severity: ParameterErrorSeverity
    parameter_name: str
    command_sent: str
    response_received: str
    error_message: str
    suggested_actions: List[str]
    timestamp: datetime
    retry_count: int = 0
    context: Dict[str, Any] = None


@dataclass
class ConnectionValidationResult:
    """Result of connection validation before parameter operations."""
    is_valid: bool
    error_message: Optional[str]
    connection_quality: int  # 0-100
    last_activity: Optional[datetime]
    suggested_actions: List[str]


class ParameterErrorHandler:
    """
    Comprehensive error handling service for parameter operations.
    
    This service provides specific error handling for parameter reading/writing operations,
    including timeout detection, response validation, connection monitoring, and
    user-friendly error reporting with corrective actions.
    """

    def __init__(self, app_instance):
        """
        Initialize the parameter error handler.
        
        Args:
            app_instance: Reference to the main application instance
        """
        self.app = app_instance
        self.error_history = []
        self.connection_validation_enabled = True
        self.timeout_threshold = 10.0  # seconds
        self.max_retry_attempts = 3
        self.retry_delay = 2.0  # seconds
        
        # Error pattern recognition
        self._init_error_patterns()
        
        # Error message templates
        self._init_error_messages()
        
        # Corrective action suggestions
        self._init_corrective_actions()
        
        # Connection monitoring
        self.last_successful_operation = None
        self.consecutive_failures = 0
        self.connection_quality_history = []

    def _init_error_patterns(self) -> None:
        """Initialize patterns for recognizing different types of errors."""
        self.error_patterns = {
            ParameterErrorType.COMMUNICATION_TIMEOUT: [
                r'timeout',
                r'no response',
                r'communication timeout',
                r'device not responding'
            ],
            ParameterErrorType.INVALID_RESPONSE: [
                r'invalid response',
                r'unexpected response',
                r'malformed response',
                r'response format error',
                r'parsing failed'
            ],
            ParameterErrorType.CONNECTION_LOST: [
                r'connection lost',
                r'device disconnected',
                r'serial port error',
                r'communication error'
            ],
            ParameterErrorType.DEVICE_NOT_RESPONDING: [
                r'device not responding',
                r'no acknowledgment',
                r'silent device',
                r'unresponsive'
            ],
            ParameterErrorType.COMMAND_REJECTED: [
                r'command rejected',
                r'invalid command',
                r'command not recognized',
                r'error response'
            ],
            ParameterErrorType.DEVICE_BUSY: [
                r'device busy',
                r'resource busy',
                r'operation in progress',
                r'try again later'
            ],
            ParameterErrorType.PARAMETER_NOT_SUPPORTED: [
                r'parameter not supported',
                r'unknown parameter',
                r'command not available',
                r'feature not supported'
            ]
        }

    def _init_error_messages(self) -> None:
        """Initialize user-friendly error messages."""
        self.error_messages = {
            ParameterErrorType.COMMUNICATION_TIMEOUT: {
                'title': 'Communication Timeout',
                'message': 'The device did not respond to the parameter command within the expected time ({timeout}s). Parameter: {parameter_name}',
                'details': 'Command sent: {command_sent}\nTimeout after: {timeout} seconds'
            },
            ParameterErrorType.INVALID_RESPONSE: {
                'title': 'Invalid Device Response',
                'message': 'The device returned an invalid or unexpected response for parameter {parameter_name}.',
                'details': 'Command sent: {command_sent}\nResponse received: {response_received}\nExpected format: {expected_format}'
            },
            ParameterErrorType.CONNECTION_LOST: {
                'title': 'Connection Lost',
                'message': 'The connection to the device was lost during parameter operation for {parameter_name}.',
                'details': 'Last command: {command_sent}\nConnection status: Disconnected'
            },
            ParameterErrorType.DEVICE_NOT_RESPONDING: {
                'title': 'Device Not Responding',
                'message': 'The device is connected but not responding to parameter commands. Parameter: {parameter_name}',
                'details': 'Command sent: {command_sent}\nNo response received after {timeout} seconds'
            },
            ParameterErrorType.COMMAND_REJECTED: {
                'title': 'Command Rejected',
                'message': 'The device rejected the parameter command for {parameter_name}.',
                'details': 'Command sent: {command_sent}\nDevice response: {response_received}'
            },
            ParameterErrorType.PARSING_ERROR: {
                'title': 'Response Parsing Error',
                'message': 'Failed to parse the device response for parameter {parameter_name}.',
                'details': 'Command sent: {command_sent}\nResponse received: {response_received}\nParsing error: {parsing_error}'
            },
            ParameterErrorType.VALIDATION_ERROR: {
                'title': 'Parameter Validation Error',
                'message': 'The parameter value for {parameter_name} failed validation before sending to the device.',
                'details': 'Parameter value: {parameter_value}\nValidation error: {validation_error}'
            },
            ParameterErrorType.DEVICE_BUSY: {
                'title': 'Device Busy',
                'message': 'The device is currently busy and cannot process the parameter command for {parameter_name}.',
                'details': 'Command sent: {command_sent}\nDevice status: Busy'
            },
            ParameterErrorType.PARAMETER_NOT_SUPPORTED: {
                'title': 'Parameter Not Supported',
                'message': 'The parameter {parameter_name} is not supported by this device or firmware version.',
                'details': 'Command sent: {command_sent}\nDevice response: {response_received}'
            }
        }

    def _init_corrective_actions(self) -> None:
        """Initialize corrective action suggestions for each error type."""
        self.corrective_actions = {
            ParameterErrorType.COMMUNICATION_TIMEOUT: [
                "Check the physical connection between the device and computer",
                "Verify the device is powered on and in configuration mode",
                "Try increasing the communication timeout in settings",
                "Restart the device and try again",
                "Check for interference on the communication line"
            ],
            ParameterErrorType.INVALID_RESPONSE: [
                "Verify the device firmware version is compatible",
                "Check if the parameter command format has changed",
                "Try reading the parameter again to see if it was a temporary issue",
                "Contact technical support if the problem persists",
                "Check device documentation for correct response format"
            ],
            ParameterErrorType.CONNECTION_LOST: [
                "Check the USB cable connection",
                "Verify the device has stable power supply",
                "Try a different USB port or cable",
                "Restart both the device and the application",
                "Check Windows Device Manager for COM port issues"
            ],
            ParameterErrorType.DEVICE_NOT_RESPONDING: [
                "Power cycle the device (turn off and on)",
                "Check if the device is in the correct mode for configuration",
                "Verify the correct COM port is selected",
                "Try disconnecting and reconnecting to the device",
                "Check if another application is using the device"
            ],
            ParameterErrorType.COMMAND_REJECTED: [
                "Verify the parameter command syntax is correct",
                "Check if the parameter is supported by your device model",
                "Ensure the device is in configuration mode",
                "Try sending the command with different formatting",
                "Check device documentation for supported commands"
            ],
            ParameterErrorType.PARSING_ERROR: [
                "The device response format may have changed - check for firmware updates",
                "Try reading the parameter again to see if it was a temporary issue",
                "Check if the response contains error messages from the device",
                "Contact technical support with the exact response received",
                "Verify the parameter specification is up to date"
            ],
            ParameterErrorType.VALIDATION_ERROR: [
                "Check the parameter value is within the allowed range",
                "Verify the parameter format matches the specification",
                "Review the parameter documentation for correct values",
                "Try using a different valid value for testing",
                "Check for any conditional requirements for this parameter"
            ],
            ParameterErrorType.DEVICE_BUSY: [
                "Wait a few seconds and try the operation again",
                "Check if another parameter operation is in progress",
                "Ensure no other applications are communicating with the device",
                "Try sending commands with longer delays between them",
                "Restart the device if it remains busy for extended periods"
            ],
            ParameterErrorType.PARAMETER_NOT_SUPPORTED: [
                "Check the device model and firmware version",
                "Verify the parameter is available on your specific device",
                "Update the device firmware if a newer version is available",
                "Check the parameter specification for device compatibility",
                "Contact technical support for parameter availability information"
            ]
        }

    def validate_connection_before_operation(self, operation_name: str = "parameter operation") -> ConnectionValidationResult:
        """
        Validate the connection before performing parameter operations.
        
        Args:
            operation_name: Name of the operation being performed
            
        Returns:
            ConnectionValidationResult with validation details
        """
        if not self.connection_validation_enabled:
            return ConnectionValidationResult(
                is_valid=True,
                error_message=None,
                connection_quality=100,
                last_activity=datetime.now(),
                suggested_actions=[]
            )

        # Enhanced connection validation with comprehensive checks
        validation_issues = []
        suggested_actions = []
        connection_quality = 100
        
        # Check basic connection
        if not hasattr(self.app, 'serial_service') or not self.app.serial_service.is_connected:
            validation_issues.append("Device is not connected")
            connection_quality = 0
            suggested_actions.extend([
                "Connect to the device using the Connection tab",
                "Verify the device is powered on and in configuration mode",
                "Check the USB cable connection is secure",
                "Select the correct COM port from the dropdown",
                "Try a different USB port if connection fails"
            ])
        else:
            # Check serial port status
            try:
                if hasattr(self.app.serial_service, 'serial_port') and self.app.serial_service.serial_port:
                    if not self.app.serial_service.serial_port.is_open:
                        validation_issues.append("Serial port is not open")
                        connection_quality = 0
                        suggested_actions.extend([
                            "Reconnect to the device",
                            "Check if another application is using the COM port",
                            "Restart the application if the port appears stuck"
                        ])
            except Exception as e:
                validation_issues.append(f"Serial port error: {str(e)}")
                connection_quality = 0
                suggested_actions.append("Check the device connection and try reconnecting")

        # Check connection quality
        if connection_quality > 0:
            connection_quality = self._assess_connection_quality()
        
        # Check last activity with more detailed analysis
        last_activity = getattr(self.app.serial_service, 'last_activity_time', None)
        if last_activity and isinstance(last_activity, datetime):
            try:
                time_since_activity = datetime.now() - last_activity
                
                if time_since_activity > timedelta(minutes=10):
                    validation_issues.append(f"No communication for {int(time_since_activity.total_seconds() / 60)} minutes")
                    connection_quality = max(0, connection_quality - 40)
                    suggested_actions.extend([
                        "Send a test command to verify device responsiveness",
                        "Check if the device has entered sleep mode",
                        "Try power cycling the device",
                        "Verify the device is still physically connected"
                    ])
                elif time_since_activity > timedelta(minutes=5):
                    validation_issues.append(f"Limited recent communication ({int(time_since_activity.total_seconds() / 60)} minutes ago)")
                    connection_quality = max(0, connection_quality - 20)
                    suggested_actions.extend([
                        "Test the connection by sending a simple command",
                        "Check if the device is still responsive"
                    ])
            except (TypeError, AttributeError):
                # Handle cases where last_activity is not a datetime object
                pass

        # Check for recent failures with detailed analysis
        try:
            consecutive_failures = int(self.consecutive_failures) if self.consecutive_failures is not None else 0
            
            if consecutive_failures >= 5:
                validation_issues.append(f"High failure rate detected ({consecutive_failures} consecutive failures)")
                connection_quality = max(0, connection_quality - 50)
                suggested_actions.extend([
                    "Check the device connection stability",
                    "Try restarting the device completely",
                    "Verify there's no electromagnetic interference",
                    "Consider using a different USB port or cable",
                    "Check if the device firmware needs updating"
                ])
            elif consecutive_failures >= 3:
                validation_issues.append(f"Multiple recent failures ({consecutive_failures} consecutive)")
                connection_quality = max(0, connection_quality - 30)
                suggested_actions.extend([
                    "Check the device connection stability",
                    "Try restarting the device",
                    "Verify there's no interference"
                ])
        except (TypeError, ValueError):
            # Handle cases where consecutive_failures is not a number
            pass

        # Check device responsiveness if we have a way to test it
        if connection_quality > 0 and hasattr(self.app, 'serial_service'):
            responsiveness_check = self._check_device_responsiveness()
            if not responsiveness_check['responsive']:
                validation_issues.append("Device not responding to test commands")
                connection_quality = max(0, connection_quality - 30)
                suggested_actions.extend(responsiveness_check['suggested_actions'])

        # Determine overall validation result
        is_valid = len(validation_issues) == 0 or connection_quality >= 50
        
        # Create comprehensive error message
        error_message = None
        if validation_issues:
            error_message = f"Connection validation failed for {operation_name}: " + "; ".join(validation_issues)
        
        # Log validation results
        self._log_connection_validation_results(operation_name, is_valid, connection_quality, validation_issues)
        
        return ConnectionValidationResult(
            is_valid=is_valid,
            error_message=error_message,
            connection_quality=connection_quality,
            last_activity=last_activity,
            suggested_actions=suggested_actions
        )
    
    def _check_device_responsiveness(self) -> Dict[str, Any]:
        """
        Check if the device is responsive by analyzing recent communication patterns.
        
        Returns:
            Dictionary with responsiveness status and suggested actions
        """
        try:
            # Check if we have recent successful operations
            recent_successes = []
            recent_timeouts = []
            
            try:
                recent_successes = [e for e in self.error_history if 
                                  hasattr(e, 'timestamp') and isinstance(e.timestamp, datetime) and
                                  (datetime.now() - e.timestamp).total_seconds() < 60 and
                                  hasattr(e, 'error_type') and
                                  e.error_type not in [ParameterErrorType.COMMUNICATION_TIMEOUT, 
                                                     ParameterErrorType.DEVICE_NOT_RESPONDING]]
                
                # Check if we have recent timeouts
                recent_timeouts = [e for e in self.error_history if 
                                 hasattr(e, 'timestamp') and isinstance(e.timestamp, datetime) and
                                 (datetime.now() - e.timestamp).total_seconds() < 300 and
                                 hasattr(e, 'error_type') and
                                 e.error_type == ParameterErrorType.COMMUNICATION_TIMEOUT]
            except (TypeError, AttributeError):
                pass
            
            if len(recent_timeouts) > 2:
                return {
                    'responsive': False,
                    'suggested_actions': [
                        "Device appears unresponsive - try power cycling",
                        "Check if device is in sleep mode or low power state",
                        "Verify device is in configuration mode",
                        "Try increasing communication timeout settings"
                    ]
                }
            elif len(recent_successes) > 0:
                return {
                    'responsive': True,
                    'suggested_actions': []
                }
            else:
                return {
                    'responsive': True,  # Assume responsive if no recent data
                    'suggested_actions': []
                }
                
        except Exception as e:
            return {
                'responsive': True,  # Default to responsive on error
                'suggested_actions': []
            }
    
    def _log_connection_validation_results(self, operation_name: str, is_valid: bool, 
                                         connection_quality: int, validation_issues: List[str]):
        """
        Log detailed connection validation results.
        
        Args:
            operation_name: Name of the operation being validated
            is_valid: Whether validation passed
            connection_quality: Connection quality score
            validation_issues: List of validation issues found
        """
        status = "PASSED" if is_valid else "FAILED"
        self.app.log_frame.log_message(f"DEBUG: Connection validation for {operation_name}: {status}\n")
        self.app.log_frame.log_message(f"DEBUG: - Connection quality: {connection_quality}%\n")
        
        if validation_issues:
            self.app.log_frame.log_message("DEBUG: - Issues found:\n")
            for issue in validation_issues:
                self.app.log_frame.log_message(f"DEBUG:   * {issue}\n")
        else:
            self.app.log_frame.log_message("DEBUG: - No issues found\n")
        
        # Log additional diagnostic information
        if hasattr(self.app, 'serial_service') and self.app.serial_service.is_connected:
            try:
                port_name = getattr(self.app.serial_service.serial_port, 'port', 'Unknown')
                self.app.log_frame.log_message(f"DEBUG: - Connected to port: {port_name}\n")
            except:
                pass
        
        self.app.log_frame.log_message(f"DEBUG: - Consecutive failures: {self.consecutive_failures}\n")

    def handle_parameter_error(self, error_type: ParameterErrorType, parameter_name: str,
                             command_sent: str, response_received: str = "",
                             context: Dict[str, Any] = None) -> ParameterError:
        """
        Handle a parameter operation error with comprehensive logging and user feedback.
        
        Args:
            error_type: Type of error that occurred
            parameter_name: Name of the parameter being processed
            command_sent: Command that was sent to the device
            response_received: Response received from device (if any)
            context: Additional context information
            
        Returns:
            ParameterError object with error details
        """
        if context is None:
            context = {}

        # Determine error severity
        severity = self._determine_error_severity(error_type, context)
        
        # Create error object
        error = ParameterError(
            error_type=error_type,
            severity=severity,
            parameter_name=parameter_name,
            command_sent=command_sent,
            response_received=response_received,
            error_message=self._format_error_message(error_type, parameter_name, command_sent, response_received, context),
            suggested_actions=self.corrective_actions.get(error_type, []),
            timestamp=datetime.now(),
            context=context
        )

        # Add to error history
        self.error_history.append(error)
        
        # Update failure tracking
        self._update_failure_tracking(error_type)
        
        # Log the error with appropriate detail level
        self._log_parameter_error(error)
        
        # Show user notification based on severity
        self._show_error_notification(error)
        
        # Trigger automatic recovery if appropriate
        self._attempt_automatic_recovery(error)
        
        return error

    def handle_communication_timeout(self, parameter_name: str, command_sent: str, 
                                   timeout_duration: float) -> ParameterError:
        """
        Handle communication timeout errors with specific timeout information.
        
        Args:
            parameter_name: Name of the parameter
            command_sent: Command that timed out
            timeout_duration: How long we waited before timing out
            
        Returns:
            ParameterError object
        """
        context = {
            'timeout_duration': timeout_duration,
            'timeout_threshold': self.timeout_threshold,
            'retry_suggested': timeout_duration < self.timeout_threshold * 2,
            'connection_check_needed': timeout_duration >= self.timeout_threshold
        }
        
        # Enhanced timeout handling with specific corrective actions
        error = self.handle_parameter_error(
            ParameterErrorType.COMMUNICATION_TIMEOUT,
            parameter_name,
            command_sent,
            "",
            context
        )
        
        # Add timeout-specific corrective actions
        timeout_actions = [
            f"Wait {int(self.timeout_threshold)}s and retry the parameter operation",
            "Check if the device is responding to other commands",
            "Verify the device is not in sleep mode or low power state",
            "Try increasing the communication timeout in settings",
            "Check for interference on the communication line"
        ]
        
        # Replace generic actions with timeout-specific ones
        error.suggested_actions = timeout_actions
        
        # Log detailed timeout information
        self._log_timeout_details(parameter_name, command_sent, timeout_duration)
        
        return error
    
    def _log_timeout_details(self, parameter_name: str, command_sent: str, timeout_duration: float):
        """
        Log detailed timeout information for troubleshooting.
        
        Args:
            parameter_name: Name of the parameter that timed out
            command_sent: Command that was sent
            timeout_duration: How long we waited
        """
        self.app.log_frame.log_message(f"DEBUG: Timeout details for {parameter_name}:\n")
        self.app.log_frame.log_message(f"DEBUG: - Command sent: {command_sent}\n")
        self.app.log_frame.log_message(f"DEBUG: - Timeout duration: {timeout_duration:.2f}s\n")
        self.app.log_frame.log_message(f"DEBUG: - Timeout threshold: {self.timeout_threshold:.2f}s\n")
        self.app.log_frame.log_message(f"DEBUG: - Consecutive failures: {self.consecutive_failures}\n")
        
        # Check connection quality if available
        if hasattr(self.app, 'error_handler') and hasattr(self.app.error_handler, 'connection_quality'):
            quality = self.app.error_handler.connection_quality
            self.app.log_frame.log_message(f"DEBUG: - Connection quality: {quality}%\n")
            
            if quality < 50:
                self.app.log_frame.log_message("WARNING: Poor connection quality may be causing timeouts\n")

    def handle_invalid_response(self, parameter_name: str, command_sent: str,
                              response_received: str, expected_format: str = "",
                              parsing_error: str = "") -> ParameterError:
        """
        Handle invalid device response errors with detailed response information.
        
        Args:
            parameter_name: Name of the parameter
            command_sent: Command that was sent
            response_received: Invalid response received
            expected_format: Expected response format
            parsing_error: Specific parsing error message
            
        Returns:
            ParameterError object
        """
        context = {
            'expected_format': expected_format,
            'parsing_error': parsing_error,
            'response_length': len(response_received),
            'response_type': self._analyze_response_type(response_received),
            'possible_causes': self._analyze_response_issues(response_received, expected_format)
        }
        
        # Enhanced invalid response handling
        error = self.handle_parameter_error(
            ParameterErrorType.INVALID_RESPONSE,
            parameter_name,
            command_sent,
            response_received,
            context
        )
        
        # Add response-specific corrective actions
        response_actions = self._get_response_specific_actions(response_received, expected_format, parsing_error)
        error.suggested_actions = response_actions
        
        # Log detailed response analysis
        self._log_response_analysis(parameter_name, command_sent, response_received, expected_format, parsing_error)
        
        return error
    
    def _analyze_response_type(self, response: str) -> str:
        """
        Analyze the type of response received to provide better error context.
        
        Args:
            response: Response received from device
            
        Returns:
            String describing the response type
        """
        if not response:
            return "empty_response"
        elif response.startswith("ERROR"):
            return "error_response"
        elif response.startswith("OK"):
            return "ok_response"
        elif ":" in response:
            return "formatted_response"
        elif response.isdigit():
            return "numeric_response"
        elif len(response) < 5:
            return "short_response"
        else:
            return "unknown_response"
    
    def _analyze_response_issues(self, response: str, expected_format: str) -> List[str]:
        """
        Analyze potential issues with the response.
        
        Args:
            response: Response received
            expected_format: Expected format
            
        Returns:
            List of possible causes for the invalid response
        """
        issues = []
        
        if not response:
            issues.append("Device sent empty response")
        elif response.startswith("ERROR"):
            issues.append("Device returned error response")
        elif expected_format and ":" in expected_format and ":" not in response:
            issues.append("Response missing expected delimiter ':'")
        elif expected_format and "=" in expected_format and "=" not in response:
            issues.append("Response missing expected delimiter '='")
        elif len(response) < 3:
            issues.append("Response too short to be valid")
        elif response.count(",") != expected_format.count(",") if expected_format else False:
            issues.append("Response has wrong number of comma-separated values")
        
        return issues
    
    def _get_response_specific_actions(self, response: str, expected_format: str, parsing_error: str) -> List[str]:
        """
        Get corrective actions specific to the type of invalid response.
        
        Args:
            response: Response received
            expected_format: Expected format
            parsing_error: Parsing error message
            
        Returns:
            List of suggested corrective actions
        """
        actions = []
        
        if not response:
            actions.extend([
                "Check if the device is powered on and responding",
                "Verify the command syntax is correct for your device model",
                "Try sending a simple test command to verify communication",
                "Check if the device requires a different command format"
            ])
        elif response.startswith("ERROR"):
            actions.extend([
                "Check if the parameter is supported by your device firmware",
                "Verify the parameter command syntax matches your device model",
                "Try reading device information to confirm compatibility",
                "Check device documentation for supported parameter commands"
            ])
        elif "timeout" in parsing_error.lower():
            actions.extend([
                "Increase the response timeout setting",
                "Check for communication interference",
                "Verify the device is not in sleep mode",
                "Try sending the command again after a short delay"
            ])
        else:
            actions.extend([
                "Verify the device firmware version is compatible",
                "Check if the response format has changed in newer firmware",
                "Try reading the parameter again to see if it was a temporary issue",
                "Contact technical support with the exact response received"
            ])
        
        return actions
    
    def _log_response_analysis(self, parameter_name: str, command_sent: str, response_received: str, 
                              expected_format: str, parsing_error: str):
        """
        Log detailed response analysis for troubleshooting.
        
        Args:
            parameter_name: Name of the parameter
            command_sent: Command that was sent
            response_received: Response received
            expected_format: Expected format
            parsing_error: Parsing error message
        """
        self.app.log_frame.log_message(f"DEBUG: Response analysis for {parameter_name}:\n")
        self.app.log_frame.log_message(f"DEBUG: - Command sent: {command_sent}\n")
        self.app.log_frame.log_message(f"DEBUG: - Response received: '{response_received}'\n")
        self.app.log_frame.log_message(f"DEBUG: - Response length: {len(response_received)} characters\n")
        self.app.log_frame.log_message(f"DEBUG: - Expected format: {expected_format}\n")
        
        if parsing_error:
            self.app.log_frame.log_message(f"DEBUG: - Parsing error: {parsing_error}\n")
        
        # Analyze response characteristics
        response_type = self._analyze_response_type(response_received)
        self.app.log_frame.log_message(f"DEBUG: - Response type: {response_type}\n")
        
        issues = self._analyze_response_issues(response_received, expected_format)
        if issues:
            self.app.log_frame.log_message("DEBUG: - Identified issues:\n")
            for issue in issues:
                self.app.log_frame.log_message(f"DEBUG:   * {issue}\n")

    def handle_connection_validation_failure(self, validation_result: ConnectionValidationResult,
                                           operation_name: str) -> ParameterError:
        """
        Handle connection validation failures before parameter operations.
        
        Args:
            validation_result: Result of connection validation
            operation_name: Name of the operation that was prevented
            
        Returns:
            ParameterError object
        """
        context = {
            'connection_quality': validation_result.connection_quality,
            'last_activity': validation_result.last_activity,
            'operation_name': operation_name
        }
        
        return self.handle_parameter_error(
            ParameterErrorType.CONNECTION_LOST,
            operation_name,
            "Connection validation",
            validation_result.error_message or "Connection validation failed",
            context
        )

    def _assess_connection_quality(self) -> int:
        """
        Assess the current connection quality based on recent activity and errors.
        
        Returns:
            Connection quality score (0-100)
        """
        base_quality = 100
        
        # Reduce quality based on recent errors
        try:
            recent_errors = [e for e in self.error_history if 
                            hasattr(e, 'timestamp') and isinstance(e.timestamp, datetime) and
                            (datetime.now() - e.timestamp).total_seconds() < 300]  # Last 5 minutes
            
            quality_reduction = min(len(recent_errors) * 10, 50)
            base_quality -= quality_reduction
        except (TypeError, AttributeError):
            pass
        
        # Reduce quality based on consecutive failures
        try:
            consecutive_failures = int(self.consecutive_failures) if self.consecutive_failures is not None else 0
            consecutive_penalty = min(consecutive_failures * 15, 60)
            base_quality -= consecutive_penalty
        except (TypeError, ValueError):
            pass
        
        # Check if we have error handler with connection quality
        if hasattr(self.app, 'error_handler') and hasattr(self.app.error_handler, 'connection_quality'):
            try:
                # Use the main error handler's quality assessment
                main_quality = self.app.error_handler.connection_quality
                if isinstance(main_quality, (int, float)):
                    base_quality = min(base_quality, main_quality)
            except (TypeError, AttributeError):
                # Handle cases where connection_quality is not a number
                pass
        
        return max(0, base_quality)

    def _determine_error_severity(self, error_type: ParameterErrorType, context: Dict[str, Any]) -> ParameterErrorSeverity:
        """
        Determine the severity of an error based on type and context.
        
        Args:
            error_type: Type of error
            context: Error context
            
        Returns:
            Error severity level
        """
        # Critical errors that prevent all operations
        if error_type in [ParameterErrorType.CONNECTION_LOST]:
            return ParameterErrorSeverity.CRITICAL
        
        # Errors that affect multiple operations
        if error_type in [ParameterErrorType.DEVICE_NOT_RESPONDING, ParameterErrorType.DEVICE_BUSY]:
            return ParameterErrorSeverity.ERROR
        
        # Errors that affect single operations but may be recoverable
        if error_type in [ParameterErrorType.COMMUNICATION_TIMEOUT, ParameterErrorType.INVALID_RESPONSE]:
            # Check retry count to escalate severity
            try:
                retry_count = int(context.get('retry_count', 0))
                max_retries = int(self.max_retry_attempts)
                if retry_count >= max_retries:
                    return ParameterErrorSeverity.ERROR
                else:
                    return ParameterErrorSeverity.WARNING
            except (TypeError, ValueError):
                return ParameterErrorSeverity.WARNING
        
        # Validation and parsing errors are typically warnings
        if error_type in [ParameterErrorType.VALIDATION_ERROR, ParameterErrorType.PARSING_ERROR]:
            return ParameterErrorSeverity.WARNING
        
        # Default to warning
        return ParameterErrorSeverity.WARNING

    def _format_error_message(self, error_type: ParameterErrorType, parameter_name: str,
                            command_sent: str, response_received: str, context: Dict[str, Any]) -> str:
        """
        Format a user-friendly error message.
        
        Args:
            error_type: Type of error
            parameter_name: Parameter name
            command_sent: Command sent
            response_received: Response received
            context: Additional context
            
        Returns:
            Formatted error message
        """
        message_template = self.error_messages.get(error_type, {})
        base_message = message_template.get('message', f'Parameter error: {error_type.value}')
        
        # Format the message with available context
        format_dict = {
            'parameter_name': parameter_name,
            'command_sent': command_sent,
            'response_received': response_received,
            'timeout': context.get('timeout_duration', self.timeout_threshold),
            'expected_format': context.get('expected_format', 'Unknown'),
            'parsing_error': context.get('parsing_error', 'Unknown'),
            'parameter_value': context.get('parameter_value', 'Unknown'),
            'validation_error': context.get('validation_error', 'Unknown')
        }
        
        try:
            return base_message.format(**format_dict)
        except KeyError:
            # Fallback if formatting fails
            return f"{base_message} (Parameter: {parameter_name})"

    def _update_failure_tracking(self, error_type: ParameterErrorType) -> None:
        """
        Update failure tracking statistics.
        
        Args:
            error_type: Type of error that occurred
        """
        try:
            if error_type in [ParameterErrorType.COMMUNICATION_TIMEOUT, 
                             ParameterErrorType.DEVICE_NOT_RESPONDING,
                             ParameterErrorType.CONNECTION_LOST]:
                self.consecutive_failures = int(self.consecutive_failures or 0) + 1
            else:
                # Reset consecutive failures for non-critical errors
                current_failures = int(self.consecutive_failures or 0)
                self.consecutive_failures = max(0, current_failures - 1)
        except (TypeError, ValueError):
            # Handle cases where consecutive_failures is not a number
            self.consecutive_failures = 1 if error_type in [ParameterErrorType.COMMUNICATION_TIMEOUT, 
                                                           ParameterErrorType.DEVICE_NOT_RESPONDING,
                                                           ParameterErrorType.CONNECTION_LOST] else 0

    def _log_parameter_error(self, error: ParameterError) -> None:
        """
        Log parameter error with appropriate detail level.
        
        Args:
            error: Parameter error to log
        """
        # Format log message based on severity
        if error.severity == ParameterErrorSeverity.CRITICAL:
            log_prefix = "CRITICAL"
        elif error.severity == ParameterErrorSeverity.ERROR:
            log_prefix = "ERROR"
        elif error.severity == ParameterErrorSeverity.WARNING:
            log_prefix = "WARNING"
        else:
            log_prefix = "INFO"
        
        # Log the main error message
        self.app.log_frame.log_message(f"{log_prefix}: {error.error_message}\n")
        
        # Log additional details for errors and critical issues
        if error.severity in [ParameterErrorSeverity.ERROR, ParameterErrorSeverity.CRITICAL]:
            if error.command_sent:
                self.app.log_frame.log_message(f"DEBUG: Command sent: {error.command_sent}\n")
            if error.response_received:
                self.app.log_frame.log_message(f"DEBUG: Response received: {error.response_received}\n")
        
        # Log suggested actions for critical and error level issues
        if error.severity in [ParameterErrorSeverity.ERROR, ParameterErrorSeverity.CRITICAL] and error.suggested_actions:
            self.app.log_frame.log_message(f"INFO: Suggested solutions:\n")
            for i, action in enumerate(error.suggested_actions[:3], 1):  # Limit to top 3 actions
                self.app.log_frame.log_message(f"INFO: {i}. {action}\n")

    def _show_error_notification(self, error: ParameterError) -> None:
        """
        Show user notification based on error severity.
        
        Args:
            error: Parameter error to show
        """
        # Only show dialog for critical errors
        if error.severity == ParameterErrorSeverity.CRITICAL:
            try:
                from tkinter import messagebox
                message_template = self.error_messages.get(error.error_type, {})
                title = message_template.get('title', 'Parameter Error')
                
                # Show error dialog with primary suggested action
                message = error.error_message
                if error.suggested_actions:
                    message += f"\n\nSuggested action: {error.suggested_actions[0]}"
                
                self.app.after(0, lambda: messagebox.showerror(title, message))
            except Exception as e:
                self.app.log_frame.log_message(f"WARNING: Failed to show error dialog: {str(e)}\n")

    def _attempt_automatic_recovery(self, error: ParameterError) -> None:
        """
        Attempt automatic recovery for certain types of errors.
        
        Args:
            error: Parameter error to attempt recovery for
        """
        # Only attempt recovery for specific error types
        if error.error_type not in [ParameterErrorType.COMMUNICATION_TIMEOUT, 
                                   ParameterErrorType.DEVICE_BUSY]:
            return
        
        # Don't attempt recovery if we've already tried too many times
        if error.retry_count >= self.max_retry_attempts:
            return
        
        # Schedule a retry after a delay
        def retry_operation():
            self.app.log_frame.log_message(f"INFO: Attempting automatic recovery for {error.parameter_name}\n")
            # The actual retry would be handled by the calling service
            
        self.app.after(int(self.retry_delay * 1000), retry_operation)

    def create_user_friendly_error_message(self, error: ParameterError) -> str:
        """
        Create a comprehensive, user-friendly error message with corrective actions.
        
        Args:
            error: ParameterError object
            
        Returns:
            Formatted user-friendly error message
        """
        message_parts = []
        
        # Main error description
        message_parts.append(f"Parameter Operation Failed: {error.parameter_name}")
        message_parts.append(f"Error: {error.error_message}")
        
        # Add context information if available
        if error.context:
            if 'timeout_duration' in error.context:
                message_parts.append(f"Timeout: {error.context['timeout_duration']:.1f}s")
            if 'response_length' in error.context:
                message_parts.append(f"Response length: {error.context['response_length']} characters")
            if 'connection_quality' in error.context:
                quality = error.context['connection_quality']
                quality_desc = "Excellent" if quality >= 90 else "Good" if quality >= 70 else "Fair" if quality >= 40 else "Poor"
                message_parts.append(f"Connection quality: {quality}% ({quality_desc})")
        
        # Add suggested actions
        if error.suggested_actions:
            message_parts.append("\nSuggested solutions:")
            for i, action in enumerate(error.suggested_actions[:5], 1):  # Limit to top 5 actions
                message_parts.append(f"{i}. {action}")
        
        # Add retry information if applicable
        if error.retry_count > 0:
            message_parts.append(f"\nRetry attempt: {error.retry_count}/{self.max_retry_attempts}")
        
        return "\n".join(message_parts)
    
    def handle_parameter_operation_error(self, operation_type: str, parameter_name: str, 
                                       error_details: Dict[str, Any]) -> ParameterError:
        """
        Handle parameter operation errors with comprehensive error analysis and user feedback.
        
        Args:
            operation_type: Type of operation (read, write, validate)
            parameter_name: Name of the parameter
            error_details: Dictionary with error details
            
        Returns:
            ParameterError object with comprehensive error information
        """
        # Determine error type based on error details
        error_type = self._determine_error_type_from_details(error_details)
        
        # Extract relevant information
        command_sent = error_details.get('command_sent', '')
        response_received = error_details.get('response_received', '')
        
        # Create enhanced context
        context = {
            'operation_type': operation_type,
            'error_details': error_details,
            'timestamp': datetime.now(),
            'session_info': self._get_session_info()
        }
        
        # Handle the error with enhanced context
        error = self.handle_parameter_error(
            error_type,
            parameter_name,
            command_sent,
            response_received,
            context
        )
        
        # Add operation-specific corrective actions
        operation_actions = self._get_operation_specific_actions(operation_type, error_type, error_details)
        if operation_actions:
            error.suggested_actions = operation_actions + error.suggested_actions
        
        return error
    
    def _determine_error_type_from_details(self, error_details: Dict[str, Any]) -> ParameterErrorType:
        """
        Determine the error type based on error details.
        
        Args:
            error_details: Dictionary with error details
            
        Returns:
            ParameterErrorType enum value
        """
        if 'timeout' in str(error_details).lower():
            return ParameterErrorType.COMMUNICATION_TIMEOUT
        elif 'invalid_response' in error_details or 'parsing_error' in error_details:
            return ParameterErrorType.INVALID_RESPONSE
        elif 'connection' in str(error_details).lower():
            return ParameterErrorType.CONNECTION_LOST
        elif 'validation' in str(error_details).lower():
            return ParameterErrorType.VALIDATION_ERROR
        elif 'busy' in str(error_details).lower():
            return ParameterErrorType.DEVICE_BUSY
        elif 'not_supported' in error_details:
            return ParameterErrorType.PARAMETER_NOT_SUPPORTED
        else:
            return ParameterErrorType.DEVICE_NOT_RESPONDING
    
    def _get_operation_specific_actions(self, operation_type: str, error_type: ParameterErrorType, 
                                      error_details: Dict[str, Any]) -> List[str]:
        """
        Get corrective actions specific to the operation type.
        
        Args:
            operation_type: Type of operation (read, write, validate)
            error_type: Type of error that occurred
            error_details: Error details dictionary
            
        Returns:
            List of operation-specific corrective actions
        """
        actions = []
        
        if operation_type == 'read':
            if error_type == ParameterErrorType.COMMUNICATION_TIMEOUT:
                actions.extend([
                    "Try reading a single parameter instead of bulk reading",
                    "Increase the read timeout for this specific parameter",
                    "Check if the parameter exists on your device model"
                ])
            elif error_type == ParameterErrorType.INVALID_RESPONSE:
                actions.extend([
                    "Verify the parameter read command is correct for your device",
                    "Check if the parameter name has changed in newer firmware",
                    "Try reading device information first to verify compatibility"
                ])
        elif operation_type == 'write':
            if error_type == ParameterErrorType.COMMUNICATION_TIMEOUT:
                actions.extend([
                    "Verify the parameter value is within acceptable range",
                    "Check if the device is in configuration mode",
                    "Try sending the parameter command manually"
                ])
            elif error_type == ParameterErrorType.COMMAND_REJECTED:
                actions.extend([
                    "Verify the parameter value format is correct",
                    "Check if the parameter is read-only on your device",
                    "Ensure the device is not locked or in protected mode"
                ])
        elif operation_type == 'validate':
            actions.extend([
                "Check the parameter value against the specification",
                "Verify the parameter format matches the expected type",
                "Review the parameter documentation for valid ranges"
            ])
        
        return actions
    
    def _get_session_info(self) -> Dict[str, Any]:
        """
        Get current session information for error context.
        
        Returns:
            Dictionary with session information
        """
        return {
            'total_errors': len(self.error_history),
            'consecutive_failures': self.consecutive_failures,
            'connection_quality': self._assess_connection_quality(),
            'last_successful_operation': self.last_successful_operation,
            'session_start': getattr(self, 'session_start', datetime.now())
        }
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about parameter errors.
        
        Returns:
            Dictionary with error statistics
        """
        if not self.error_history:
            return {
                'total_errors': 0,
                'error_types': {},
                'severity_distribution': {},
                'recent_errors': 0,
                'consecutive_failures': self.consecutive_failures
            }
        
        # Count errors by type
        error_types = {}
        severity_distribution = {}
        
        for error in self.error_history:
            error_type_name = error.error_type.value
            error_types[error_type_name] = error_types.get(error_type_name, 0) + 1
            
            severity_name = error.severity.value
            severity_distribution[severity_name] = severity_distribution.get(severity_name, 0) + 1
        
        # Count recent errors (last hour)
        recent_errors = len([e for e in self.error_history if 
                           (datetime.now() - e.timestamp).total_seconds() < 3600])
        
        return {
            'total_errors': len(self.error_history),
            'error_types': error_types,
            'severity_distribution': severity_distribution,
            'recent_errors': recent_errors,
            'consecutive_failures': self.consecutive_failures,
            'connection_quality': self._assess_connection_quality()
        }

    def clear_error_history(self) -> None:
        """Clear the error history and reset failure tracking."""
        self.error_history.clear()
        self.consecutive_failures = 0
        self.app.log_frame.log_message("INFO: Parameter error history cleared\n")

    def set_timeout_threshold(self, timeout_seconds: float) -> None:
        """
        Set the timeout threshold for parameter operations.
        
        Args:
            timeout_seconds: Timeout threshold in seconds
        """
        self.timeout_threshold = max(1.0, timeout_seconds)
        self.app.log_frame.log_message(f"INFO: Parameter timeout threshold set to {self.timeout_threshold}s\n")

    def enable_connection_validation(self, enabled: bool) -> None:
        """
        Enable or disable connection validation before operations.
        
        Args:
            enabled: Whether to enable connection validation
        """
        self.connection_validation_enabled = enabled
        status = "enabled" if enabled else "disabled"
        self.app.log_frame.log_message(f"INFO: Connection validation {status}\n")

    def get_recent_errors(self, hours: int = 1) -> List[ParameterError]:
        """
        Get recent parameter errors within the specified time window.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of recent parameter errors
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [error for error in self.error_history if error.timestamp >= cutoff_time]

    def export_error_log(self, filename: str = None) -> str:
        """
        Export error history to a log file.
        
        Args:
            filename: Optional filename for the log file
            
        Returns:
            Path to the exported log file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"parameter_errors_{timestamp}.log"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Parameter Error Log - Generated: {datetime.now()}\n")
                f.write("=" * 60 + "\n\n")
                
                for error in self.error_history:
                    f.write(f"Timestamp: {error.timestamp}\n")
                    f.write(f"Error Type: {error.error_type.value}\n")
                    f.write(f"Severity: {error.severity.value}\n")
                    f.write(f"Parameter: {error.parameter_name}\n")
                    f.write(f"Command: {error.command_sent}\n")
                    f.write(f"Response: {error.response_received}\n")
                    f.write(f"Message: {error.error_message}\n")
                    f.write(f"Retry Count: {error.retry_count}\n")
                    
                    if error.suggested_actions:
                        f.write("Suggested Actions:\n")
                        for i, action in enumerate(error.suggested_actions, 1):
                            f.write(f"  {i}. {action}\n")
                    
                    f.write("-" * 40 + "\n\n")
                
                # Add statistics
                stats = self.get_error_statistics()
                f.write("Error Statistics:\n")
                f.write(f"Total Errors: {stats['total_errors']}\n")
                f.write(f"Recent Errors (1h): {stats['recent_errors']}\n")
                f.write(f"Consecutive Failures: {stats['consecutive_failures']}\n")
                f.write(f"Connection Quality: {stats['connection_quality']}%\n")
            
            self.app.log_frame.log_message(f"INFO: Error log exported to {filename}\n")
            return filename
            
        except Exception as e:
            self.app.log_frame.log_message(f"ERROR: Failed to export error log: {str(e)}\n")
            return ""