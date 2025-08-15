"""
Parameter Processor for cleaning and standardizing device parameter values.

This module provides functionality to process raw device responses into clean,
UI-friendly parameter values. It handles time parameters, odometer values,
and hourmeter values according to the requirements.
"""

import re
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ParameterProcessingError(Exception):
    """Custom exception for parameter processing errors."""
    pass


class ErrorSeverity(Enum):
    """Severity levels for parameter processing errors."""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ProcessingResult:
    """Result of parameter processing operation."""
    success: bool
    original_value: str
    processed_value: str
    error_message: Optional[str] = None
    error_severity: Optional[ErrorSeverity] = None
    parameter_name: Optional[str] = None


@dataclass
class ProcessingSummary:
    """Summary of batch parameter processing operation."""
    total_parameters: int
    successful_parameters: int
    failed_parameters: int
    warnings: List[str]
    errors: List[str]
    processing_results: Dict[str, ProcessingResult]


class ParameterProcessor:
    """
    Processes raw device parameter values into clean, standardized formats for UI display.
    
    This class handles various parameter types including time parameters with units,
    odometer readings, and hourmeter values from device responses with comprehensive
    error handling and fallback mechanisms.
    """
    
    def __init__(self):
        """Initialize the ParameterProcessor."""
        self.processing_errors = []
        self.processing_warnings = []
        self.failed_parameters = []
        self.successful_parameters = []
    
    def safe_process_parameters(self, parameters: Dict[str, str], device_responses: Dict[str, str] = None) -> ProcessingSummary:
        """
        Safely process multiple parameters with comprehensive error handling.
        
        This method processes all parameters while ensuring that failures in individual
        parameters don't affect the processing of others. It provides detailed feedback
        about successes and failures.
        
        Args:
            parameters: Dictionary of parameter names to raw values
            device_responses: Optional raw device responses for context
            
        Returns:
            ProcessingSummary with detailed results and error information
            
        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
        """
        # Reset processing state
        self.processing_errors = []
        self.processing_warnings = []
        self.failed_parameters = []
        self.successful_parameters = []
        
        processing_results = {}
        warnings = []
        errors = []
        
        # Time parameter names that need cleaning
        time_parameter_names = {
            'heartbeat_interval', 'report_interval', 'upload_interval', 'sleep_time',
            'moving_time', 'stopped_time', 'moving_heartbeat', 'stopped_heartbeat',
            'timeout', 'interval', 'delay', 'duration'
        }
        
        for param_name, param_value in parameters.items():
            try:
                # Determine parameter type and process accordingly
                param_name_lower = param_name.lower()
                
                if any(time_param in param_name_lower for time_param in time_parameter_names):
                    result = self._safe_clean_time_parameter(param_name, param_value)
                elif 'odometer' in param_name_lower or 'mileage' in param_name_lower:
                    # Use device response if available for better processing
                    response = self._find_relevant_response(param_name, device_responses) if device_responses else param_value
                    result = self._safe_process_odometer_value(param_name, response or param_value)
                elif 'hourmeter' in param_name_lower or 'acc_on' in param_name_lower or 'accont' in param_name_lower:
                    # Use device response if available for better processing
                    response = self._find_relevant_response(param_name, device_responses) if device_responses else param_value
                    result = self._safe_process_hourmeter_value(param_name, response or param_value)
                else:
                    # For other parameters, just validate and clean basic formatting
                    result = self._safe_clean_generic_parameter(param_name, param_value)
                
                processing_results[param_name] = result
                
                if result.success:
                    self.successful_parameters.append(param_name)
                else:
                    self.failed_parameters.append(param_name)
                    if result.error_severity == ErrorSeverity.ERROR:
                        errors.append(f"{param_name}: {result.error_message}")
                    elif result.error_severity == ErrorSeverity.WARNING:
                        warnings.append(f"{param_name}: {result.error_message}")
                        
            except Exception as e:
                # Handle unexpected errors during parameter processing
                error_msg = f"Unexpected error processing parameter {param_name}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                self.failed_parameters.append(param_name)
                
                # Create a failed result for this parameter
                processing_results[param_name] = ProcessingResult(
                    success=False,
                    original_value=str(param_value) if param_value is not None else "",
                    processed_value="",
                    error_message=error_msg,
                    error_severity=ErrorSeverity.ERROR,
                    parameter_name=param_name
                )
        
        # Create summary
        summary = ProcessingSummary(
            total_parameters=len(parameters),
            successful_parameters=len(self.successful_parameters),
            failed_parameters=len(self.failed_parameters),
            warnings=warnings,
            errors=errors,
            processing_results=processing_results
        )
        
        # Log summary information
        if summary.failed_parameters > 0:
            logger.warning(f"Parameter processing completed with {summary.failed_parameters} failures out of {summary.total_parameters} parameters")
        else:
            logger.info(f"Successfully processed all {summary.total_parameters} parameters")
            
        return summary
    
    def _safe_clean_time_parameter(self, param_name: str, raw_value: str) -> ProcessingResult:
        """
        Safely clean a time parameter with error handling.
        
        Args:
            param_name: Name of the parameter being processed
            raw_value: Raw parameter value
            
        Returns:
            ProcessingResult with success status and processed value
        """
        try:
            if not raw_value or not isinstance(raw_value, str):
                return ProcessingResult(
                    success=True,
                    original_value=str(raw_value) if raw_value is not None else "",
                    processed_value="",
                    parameter_name=param_name
                )
            
            clean_value = self.extract_numeric_value(raw_value)
            
            # Log the cleaning operation for debugging
            if clean_value != raw_value:
                logger.debug(f"Cleaned time parameter {param_name}: '{raw_value}' -> '{clean_value}'")
            
            return ProcessingResult(
                success=True,
                original_value=raw_value,
                processed_value=clean_value,
                parameter_name=param_name
            )
            
        except Exception as e:
            error_msg = f"Failed to clean time parameter: {str(e)}"
            logger.warning(f"Parameter {param_name}: {error_msg}")
            
            return ProcessingResult(
                success=False,
                original_value=raw_value,
                processed_value=raw_value,  # Fallback to original value
                error_message=error_msg,
                error_severity=ErrorSeverity.WARNING,
                parameter_name=param_name
            )
    
    def _safe_process_odometer_value(self, param_name: str, raw_response: str) -> ProcessingResult:
        """
        Safely process an odometer value with error handling.
        
        Args:
            param_name: Name of the parameter being processed
            raw_response: Raw device response or parameter value
            
        Returns:
            ProcessingResult with success status and processed value
        """
        try:
            if not raw_response or not isinstance(raw_response, str):
                return ProcessingResult(
                    success=True,
                    original_value=str(raw_response) if raw_response is not None else "",
                    processed_value="",
                    parameter_name=param_name
                )
            
            processed_value = self._process_odometer_value_internal(raw_response)
            
            if processed_value:
                logger.debug(f"Processed odometer parameter {param_name}: '{raw_response}' -> '{processed_value}'")
                return ProcessingResult(
                    success=True,
                    original_value=raw_response,
                    processed_value=processed_value,
                    parameter_name=param_name
                )
            else:
                # No value extracted, but not necessarily an error
                warning_msg = "Could not extract odometer value, using original"
                return ProcessingResult(
                    success=True,
                    original_value=raw_response,
                    processed_value=raw_response,  # Fallback to original
                    error_message=warning_msg,
                    error_severity=ErrorSeverity.WARNING,
                    parameter_name=param_name
                )
                
        except Exception as e:
            error_msg = f"Failed to process odometer value: {str(e)}"
            logger.warning(f"Parameter {param_name}: {error_msg}")
            
            return ProcessingResult(
                success=False,
                original_value=raw_response,
                processed_value=raw_response,  # Fallback to original value
                error_message=error_msg,
                error_severity=ErrorSeverity.WARNING,
                parameter_name=param_name
            )
    
    def _safe_process_hourmeter_value(self, param_name: str, raw_response: str) -> ProcessingResult:
        """
        Safely process a hourmeter value with error handling.
        
        Args:
            param_name: Name of the parameter being processed
            raw_response: Raw device response or parameter value
            
        Returns:
            ProcessingResult with success status and processed value
        """
        try:
            if not raw_response or not isinstance(raw_response, str):
                return ProcessingResult(
                    success=True,
                    original_value=str(raw_response) if raw_response is not None else "",
                    processed_value="",
                    parameter_name=param_name
                )
            
            processed_value = self._process_hourmeter_value_internal(raw_response)
            
            if processed_value:
                logger.debug(f"Processed hourmeter parameter {param_name}: '{raw_response}' -> '{processed_value}'")
                return ProcessingResult(
                    success=True,
                    original_value=raw_response,
                    processed_value=processed_value,
                    parameter_name=param_name
                )
            else:
                # No value extracted, but not necessarily an error
                warning_msg = "Could not extract hourmeter value, using original"
                return ProcessingResult(
                    success=True,
                    original_value=raw_response,
                    processed_value=raw_response,  # Fallback to original
                    error_message=warning_msg,
                    error_severity=ErrorSeverity.WARNING,
                    parameter_name=param_name
                )
                
        except Exception as e:
            error_msg = f"Failed to process hourmeter value: {str(e)}"
            logger.warning(f"Parameter {param_name}: {error_msg}")
            
            return ProcessingResult(
                success=False,
                original_value=raw_response,
                processed_value=raw_response,  # Fallback to original value
                error_message=error_msg,
                error_severity=ErrorSeverity.WARNING,
                parameter_name=param_name
            )
    
    def _safe_clean_generic_parameter(self, param_name: str, raw_value: str) -> ProcessingResult:
        """
        Safely clean a generic parameter with basic validation.
        
        Args:
            param_name: Name of the parameter being processed
            raw_value: Raw parameter value
            
        Returns:
            ProcessingResult with success status and processed value
        """
        try:
            if raw_value is None:
                return ProcessingResult(
                    success=True,
                    original_value="",
                    processed_value="",
                    parameter_name=param_name
                )
            
            # Basic cleaning: strip whitespace and handle empty values
            cleaned_value = str(raw_value).strip()
            
            return ProcessingResult(
                success=True,
                original_value=str(raw_value),
                processed_value=cleaned_value,
                parameter_name=param_name
            )
            
        except Exception as e:
            error_msg = f"Failed to clean generic parameter: {str(e)}"
            logger.warning(f"Parameter {param_name}: {error_msg}")
            
            return ProcessingResult(
                success=False,
                original_value=str(raw_value) if raw_value is not None else "",
                processed_value=str(raw_value) if raw_value is not None else "",
                error_message=error_msg,
                error_severity=ErrorSeverity.WARNING,
                parameter_name=param_name
            )
    
    def _find_relevant_response(self, param_name: str, device_responses: Dict[str, str]) -> Optional[str]:
        """
        Find the most relevant device response for a given parameter.
        
        Args:
            param_name: Name of the parameter
            device_responses: Dictionary of device responses
            
        Returns:
            Most relevant response string or None
        """
        if not device_responses:
            return None
            
        param_lower = param_name.lower()
        
        # Map parameter types to likely response keys
        if 'odometer' in param_lower or 'mileage' in param_lower:
            for key in ['ODOMETER', 'MILEAGE', 'ATSMS:MILEAGE#', 'STATUS']:
                if key in device_responses:
                    return device_responses[key]
        elif 'hourmeter' in param_lower or 'acc_on' in param_lower or 'accont' in param_lower:
            for key in ['HOURMETER', 'ACCONT', 'ATSMS:ACCONT#', 'STATUS']:
                if key in device_responses:
                    return device_responses[key]
        
        return None
    
    def clean_time_parameter(self, raw_value: str) -> str:
        """
        Clean time parameter values by extracting only numeric portions.
        
        Handles various time parameter formats:
        - "60s" -> "60"
        - "ACC OFF:120s" -> "120"
        - "Moving Time: 30s" -> "30"
        - "180" -> "180" (already clean)
        
        Args:
            raw_value (str): Raw time parameter value from device
            
        Returns:
            str: Clean numeric value, or empty string if extraction fails
            
        Requirements: 1.1, 1.2, 1.3
        """
        result = self._safe_clean_time_parameter("time_parameter", raw_value)
        return result.processed_value
    
    def extract_numeric_value(self, raw_value: str) -> str:
        """
        Extract numeric value from formatted parameter strings.
        
        Handles various formats:
        - "60s" -> "60"
        - "ACC OFF:120s" -> "120"
        - "Moving Time: 30s" -> "30"
        - "Value=45" -> "45"
        - "180" -> "180"
        
        Args:
            raw_value (str): Raw parameter value
            
        Returns:
            str: Extracted numeric value, or original value if no extraction needed
            
        Requirements: 1.2, 1.3
        """
        if not raw_value or not isinstance(raw_value, str):
            return ""
        
        # Remove leading/trailing whitespace
        value = raw_value.strip()
        
        # If already numeric, return as-is
        if value.isdigit():
            return value
        
        # Pattern to extract numbers from various formats
        # This handles: "60s", "ACC OFF:120s", "Value=45", "Time: 30s", etc.
        numeric_pattern = r'(\d+)'
        
        # Find all numeric values in the string
        matches = re.findall(numeric_pattern, value)
        
        if matches:
            # Return the last numeric value found (handles cases like "ACC OFF:120s")
            return matches[-1]
        
        # If no numeric value found, return empty string
        return ""
    
    def process_odometer_value(self, raw_response: str) -> str:
        """
        Extract odometer value from device response.
        
        Handles various odometer response formats:
        - "MILEAGE=12345" -> "12345"
        - "Cur Mileage Value:12345KM" -> "12345"
        - "Odometer: 98765 km" -> "98765"
        
        Args:
            raw_response (str): Raw device response containing odometer data
            
        Returns:
            str: Extracted odometer value, or empty string if extraction fails
            
        Requirements: 3.2
        """
        result = self._safe_process_odometer_value("odometer", raw_response)
        return result.processed_value
    
    def _process_odometer_value_internal(self, raw_response: str) -> str:
        """
        Internal method to extract odometer value from device response.
        
        Args:
            raw_response (str): Raw device response containing odometer data
            
        Returns:
            str: Extracted odometer value, or empty string if extraction fails
        """
        if not raw_response or not isinstance(raw_response, str):
            return ""
        
        # Remove leading/trailing whitespace
        response = raw_response.strip()
        
        # Pattern to match various odometer formats
        # Handles: MILEAGE=12345, Cur Mileage Value:12345KM, Odometer: 98765 km
        odometer_patterns = [
            r'MILEAGE[=:](\d+)',
            r'Cur\s+Mileage\s+Value[=:](\d+)',
            r'Odometer[=:]?\s*(\d+)',
            r'Mileage[=:]?\s*(\d+)',
        ]
        
        for pattern in odometer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                value = match.group(1)
                logger.debug(f"Extracted odometer value: '{raw_response}' -> '{value}'")
                return value
        
        # If no specific pattern matches, try to extract any numeric value
        numeric_value = self.extract_numeric_value(response)
        if numeric_value:
            logger.debug(f"Extracted odometer value (fallback): '{raw_response}' -> '{numeric_value}'")
            return numeric_value
        
        logger.warning(f"Could not extract odometer value from: '{raw_response}'")
        return ""
    
    def process_hourmeter_value(self, raw_response: str) -> str:
        """
        Extract hourmeter value from device response.
        
        Handles various hourmeter response formats:
        - "ACCONT=5678" -> "5678"
        - "Get ACC ON Time:5678 Minute" -> "5678"
        - "Engine Hours: 1234 hours" -> "1234"
        
        Args:
            raw_response (str): Raw device response containing hourmeter data
            
        Returns:
            str: Extracted hourmeter value, or empty string if extraction fails
            
        Requirements: 4.2
        """
        result = self._safe_process_hourmeter_value("hourmeter", raw_response)
        return result.processed_value
    
    def _process_hourmeter_value_internal(self, raw_response: str) -> str:
        """
        Internal method to extract hourmeter value from device response.
        
        Args:
            raw_response (str): Raw device response containing hourmeter data
            
        Returns:
            str: Extracted hourmeter value, or empty string if extraction fails
        """
        if not raw_response or not isinstance(raw_response, str):
            return ""
        
        # Remove leading/trailing whitespace
        response = raw_response.strip()
        
        # Pattern to match various hourmeter formats
        # Handles: ACCONT=5678, Get ACC ON Time:5678 Minute, Engine Hours: 1234 hours
        hourmeter_patterns = [
            r'ACCONT[=:](\d+)',
            r'Get\s+ACC\s+ON\s+Time[=:](\d+)',
            r'Engine\s+Hours[=:]?\s*(\d+)',
            r'ACC\s+ON\s+Time[=:]?\s*(\d+)',
            r'Hourmeter[=:]?\s*(\d+)',
        ]
        
        for pattern in hourmeter_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                value = match.group(1)
                logger.debug(f"Extracted hourmeter value: '{raw_response}' -> '{value}'")
                return value
        
        # If no specific pattern matches, try to extract any numeric value
        numeric_value = self.extract_numeric_value(response)
        if numeric_value:
            logger.debug(f"Extracted hourmeter value (fallback): '{raw_response}' -> '{numeric_value}'")
            return numeric_value
        
        logger.warning(f"Could not extract hourmeter value from: '{raw_response}'")
        return ""
    
    def get_processing_summary(self) -> Dict[str, any]:
        """
        Get a summary of the last parameter processing operation.
        
        Returns:
            Dictionary containing processing statistics and error information
        """
        return {
            'successful_parameters': len(self.successful_parameters),
            'failed_parameters': len(self.failed_parameters),
            'total_parameters': len(self.successful_parameters) + len(self.failed_parameters),
            'processing_errors': self.processing_errors.copy(),
            'processing_warnings': self.processing_warnings.copy(),
            'failed_parameter_names': self.failed_parameters.copy(),
            'successful_parameter_names': self.successful_parameters.copy()
        }