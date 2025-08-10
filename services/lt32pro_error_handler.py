"""
LT32Pro Error Handler

Provides device-specific error handling with recovery strategies for LT32Pro communication.
Handles connection errors, communication timeouts, protocol errors, and validation issues.
"""

import time
import logging
from typing import Dict, Optional, Tuple, List
from enum import Enum


class ErrorCategory(Enum):
    """Categories of errors that can occur during LT32Pro operations."""
    CONNECTION = "connection"
    COMMUNICATION = "communication"
    PROTOCOL = "protocol"
    VALIDATION = "validation"
    FILE = "file"


class LT32ProError(Exception):
    """Base exception for LT32Pro specific errors."""
    
    def __init__(self, message: str, category: ErrorCategory, details: Optional[Dict] = None):
        super().__init__(message)
        self.category = category
        self.details = details or {}


class ConnectionError(LT32ProError):
    """Error related to device connection issues."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, ErrorCategory.CONNECTION, details)


class CommunicationError(LT32ProError):
    """Error related to device communication issues."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, ErrorCategory.COMMUNICATION, details)


class ProtocolError(LT32ProError):
    """Error related to protocol or command format issues."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, ErrorCategory.PROTOCOL, details)


class ValidationError(LT32ProError):
    """Error related to parameter validation issues."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, ErrorCategory.VALIDATION, details)


class FileError(LT32ProError):
    """Error related to profile file operations."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, ErrorCategory.FILE, details)


class LT32ProErrorHandler:
    """
    Handles LT32Pro specific errors with recovery strategies.
    
    Provides error categorization, retry logic with exponential backoff,
    partial data recovery, and user-friendly error messages.
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        Initialize error handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.logger = logging.getLogger(__name__)
        
        # Device error codes and their meanings
        self.device_error_codes = {
            "ERROR": "General command error",
            "TIMEOUT": "Command timeout",
            "INVALID": "Invalid command format",
            "BUSY": "Device is busy processing another command",
            "NODATA": "No data available",
            "FAIL": "Command execution failed"
        }
    
    def handle_communication_timeout(self, command: str, attempt: int) -> bool:
        """
        Handle command timeout with exponential backoff retry.
        
        Args:
            command: The command that timed out
            attempt: Current attempt number (0-based)
            
        Returns:
            True if should retry, False if max retries exceeded
        """
        if attempt >= self.max_retries:
            self.logger.error(f"Command '{command}' failed after {self.max_retries} attempts")
            return False
        
        # Calculate exponential backoff delay
        delay = self.base_delay * (2 ** attempt)
        
        self.logger.warning(
            f"Command '{command}' timed out (attempt {attempt + 1}/{self.max_retries + 1}). "
            f"Retrying in {delay:.1f} seconds..."
        )
        
        time.sleep(delay)
        return True
    
    def handle_invalid_response(self, command: str, response: str) -> Tuple[str, Dict[str, str]]:
        """
        Handle invalid device responses with partial data recovery.
        
        Args:
            command: The command that generated the response
            response: The invalid response received
            
        Returns:
            Tuple of (cleaned_response, recovered_data)
        """
        self.logger.warning(f"Invalid response for command '{command}': {response}")
        
        recovered_data = {}
        cleaned_response = response.strip()
        
        # Try to extract partial data from malformed responses
        if ":" in cleaned_response:
            try:
                # Handle responses like "APN:server,user,pass" even if malformed
                if cleaned_response.startswith("APN:"):
                    parts = cleaned_response.split(":", 1)[1].split(",")
                    if len(parts) >= 1:
                        recovered_data["apn_server"] = parts[0].strip()
                    if len(parts) >= 2:
                        recovered_data["apn_user"] = parts[1].strip()
                    if len(parts) >= 3:
                        recovered_data["apn_password"] = parts[2].strip()
                
                # Handle SERVER responses
                elif cleaned_response.startswith("SERVER:"):
                    parts = cleaned_response.split(":", 1)[1].split(",")
                    if len(parts) >= 2:
                        recovered_data["server_ip"] = parts[1].strip()
                    if len(parts) >= 3:
                        recovered_data["server_port"] = parts[2].strip()
                
                # Handle READOK responses
                elif "READOK:" in cleaned_response and "=" in cleaned_response:
                    # Extract key=value pairs
                    value_part = cleaned_response.split("READOK:")[-1].strip()
                    if "=" in value_part:
                        key, value = value_part.split("=", 1)
                        recovered_data[key.strip().lower()] = value.strip()
                
            except Exception as e:
                self.logger.error(f"Failed to recover partial data from response: {e}")
        
        return cleaned_response, recovered_data
    
    def handle_device_error_response(self, command: str, error_response: str) -> Tuple[bool, str]:
        """
        Handle device error responses with user-friendly messages.
        
        Args:
            command: The command that generated the error
            error_response: The error response from device
            
        Returns:
            Tuple of (should_retry, user_friendly_message)
        """
        error_response = error_response.strip().upper()
        
        # Check for known error codes
        for error_code, description in self.device_error_codes.items():
            if error_code in error_response:
                user_message = f"Device error for command '{command}': {description}"
                
                # Determine if we should retry based on error type
                should_retry = error_code in ["TIMEOUT", "BUSY"]
                
                self.logger.error(f"Device error: {error_response} - {description}")
                return should_retry, user_message
        
        # Handle unknown error responses
        user_message = f"Unknown device error for command '{command}': {error_response}"
        self.logger.error(f"Unknown device error: {error_response}")
        
        # Default to not retrying for unknown errors
        return False, user_message
    
    def handle_connection_error(self, port: str, error: Exception) -> str:
        """
        Handle connection errors with specific troubleshooting guidance.
        
        Args:
            port: The COM port that failed to connect
            error: The connection error exception
            
        Returns:
            User-friendly troubleshooting message
        """
        error_str = str(error).lower()
        
        if "access is denied" in error_str or "permission denied" in error_str:
            return (
                f"Cannot access COM port {port}. "
                f"Troubleshooting steps:\n"
                f"1. Close any other applications using the port\n"
                f"2. Check if device is properly connected\n"
                f"3. Try unplugging and reconnecting the device\n"
                f"4. Restart the application with administrator privileges"
            )
        
        elif "file not found" in error_str or "no such file" in error_str:
            return (
                f"COM port {port} not found. "
                f"Troubleshooting steps:\n"
                f"1. Check Device Manager for available COM ports\n"
                f"2. Verify the LT32Pro device is connected via USB\n"
                f"3. Install or update the device drivers\n"
                f"4. Try a different USB cable or port"
            )
        
        elif "timeout" in error_str:
            return (
                f"Connection to {port} timed out. "
                f"Troubleshooting steps:\n"
                f"1. Check if the device is powered on\n"
                f"2. Verify the correct COM port is selected\n"
                f"3. Try reducing the baud rate\n"
                f"4. Check USB cable connection"
            )
        
        else:
            return (
                f"Failed to connect to {port}: {error}. "
                f"General troubleshooting steps:\n"
                f"1. Check device connection and power\n"
                f"2. Verify COM port settings\n"
                f"3. Close other applications using the port\n"
                f"4. Restart the device and try again"
            )
    
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Categorize an error based on its type and message.
        
        Args:
            error: The exception to categorize
            
        Returns:
            The error category
        """
        if isinstance(error, LT32ProError):
            return error.category
        
        error_str = str(error).lower()
        
        # Connection-related errors
        if any(keyword in error_str for keyword in [
            "connection", "port", "access denied", "permission denied", 
            "file not found", "no such file", "device not found"
        ]):
            return ErrorCategory.CONNECTION
        
        # Communication-related errors
        elif any(keyword in error_str for keyword in [
            "timeout", "read", "write", "serial", "communication"
        ]):
            return ErrorCategory.COMMUNICATION
        
        # Protocol-related errors
        elif any(keyword in error_str for keyword in [
            "protocol", "command", "format", "syntax", "invalid response"
        ]):
            return ErrorCategory.PROTOCOL
        
        # Validation-related errors
        elif any(keyword in error_str for keyword in [
            "validation", "invalid", "missing", "required", "format"
        ]):
            return ErrorCategory.VALIDATION
        
        # File-related errors
        elif any(keyword in error_str for keyword in [
            "file", "directory", "path"
        ]) and not any(keyword in error_str for keyword in [
            "access denied", "permission denied", "port", "connection"
        ]):
            return ErrorCategory.FILE
        
        # Default to communication error
        return ErrorCategory.COMMUNICATION
    
    def get_recovery_suggestions(self, category: ErrorCategory, error: Exception) -> List[str]:
        """
        Get recovery suggestions based on error category.
        
        Args:
            category: The error category
            error: The original exception
            
        Returns:
            List of recovery suggestions
        """
        suggestions = []
        
        if category == ErrorCategory.CONNECTION:
            suggestions.extend([
                "Check device connection and power",
                "Verify correct COM port selection",
                "Close other applications using the port",
                "Try unplugging and reconnecting the device",
                "Check Device Manager for port availability"
            ])
        
        elif category == ErrorCategory.COMMUNICATION:
            suggestions.extend([
                "Check device power and connection stability",
                "Verify baud rate and communication settings",
                "Try reducing communication speed",
                "Check for electromagnetic interference",
                "Restart the device and try again"
            ])
        
        elif category == ErrorCategory.PROTOCOL:
            suggestions.extend([
                "Verify device firmware version compatibility",
                "Check command format and syntax",
                "Ensure proper ATSMS prefix for USB communication",
                "Try basic commands first (STATUS, VERSION)",
                "Consult device manual for command reference"
            ])
        
        elif category == ErrorCategory.VALIDATION:
            suggestions.extend([
                "Check parameter values and formats",
                "Verify required parameters are present",
                "Validate IP addresses and port numbers",
                "Check profile file format and structure",
                "Use default values for optional parameters"
            ])
        
        elif category == ErrorCategory.FILE:
            suggestions.extend([
                "Check file permissions and access rights",
                "Verify file path exists and is accessible",
                "Ensure sufficient disk space",
                "Check file format and encoding",
                "Try saving to a different location"
            ])
        
        return suggestions
    
    def create_error_report(self, error: Exception, context: Dict[str, str] = None) -> Dict[str, any]:
        """
        Create a comprehensive error report.
        
        Args:
            error: The exception that occurred
            context: Additional context information
            
        Returns:
            Dictionary containing error report details
        """
        category = self.categorize_error(error)
        suggestions = self.get_recovery_suggestions(category, error)
        
        report = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "category": category.value,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "suggestions": suggestions,
            "context": context or {}
        }
        
        if isinstance(error, LT32ProError):
            report["details"] = error.details
        
        return report