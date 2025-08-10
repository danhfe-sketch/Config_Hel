"""
Demonstration of ProfileErrorHandler integration with the Universal Profile System.

This script shows how the ProfileErrorHandler would be integrated into
the existing services to provide comprehensive error handling and recovery.
"""

import asyncio
import time
import sys
import os
from typing import Optional, Callable, Dict, Any
from unittest.mock import Mock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the error handler and related classes
from services.profile_error_handler import (
    ProfileErrorHandler, DeviceConnectionError, DeviceCommunicationError,
    ParameterValidationError, ProfileFileError, ProfileErrorCategory
)
from models.operation_result import OperationType, ProfileOperationResult, ParameterOperationResult
from models.validation_result import ValidationResult


class EnhancedUniversalProfileManager:
    """
    Example of how UniversalProfileManager would be enhanced with ProfileErrorHandler.
    
    This demonstrates the integration patterns for comprehensive error handling.
    """
    
    def __init__(self, serial_service, parameter_ui_list_path: str):
        """Initialize with error handler integration."""
        self.serial_service = serial_service
        self.parameter_ui_list_path = parameter_ui_list_path
        
        # Initialize the error handler
        self.error_handler = ProfileErrorHandler(max_retries=3, base_delay=1.0, max_delay=30.0)
        
        # Mock other services for demonstration
        self.device_manager = Mock()
        self.profile_service = Mock()
        self.spec_parser = Mock()
    
    async def load_from_device_with_error_handling(self, 
                                                 progress_callback: Optional[Callable] = None) -> ProfileOperationResult:
        """
        Load profile from device with comprehensive error handling.
        
        This demonstrates how the error handler would be integrated into
        the actual profile loading operation.
        """
        print("🔄 Starting device profile load operation...")
        
        # Reset retry counts for new operation
        self.error_handler.reset_retry_counts()
        
        # Create operation result
        result = ProfileOperationResult(
            operation_type=OperationType.LOAD_FROM_DEVICE,
            success=True
        )
        
        # Simulate loading parameters with various error scenarios
        test_parameters = [
            ("server_ip", "192.168.1.100", None),  # Success
            ("server_port", None, "timeout"),      # Timeout error (retryable)
            ("apn_config", "invalid_format", "validation"),  # Validation error
            ("device_id", None, "busy"),           # Device busy (retryable)
            ("connection_timeout", "30", None),    # Success
            ("invalid_param", None, "not_supported")  # Not supported (non-retryable)
        ]
        
        for param_name, expected_value, error_type in test_parameters:
            print(f"\n📡 Processing parameter: {param_name}")
            
            param_result = await self._load_parameter_with_retry(
                param_name, expected_value, error_type, progress_callback
            )
            
            result.add_parameter_result(param_result)
            
            if progress_callback:
                progress = (result.parameters_processed / len(test_parameters)) * 100
                progress_callback(f"Loaded {result.parameters_processed}/{len(test_parameters)} parameters", progress)
        
        # Finalize result
        result.success = result.parameters_failed == 0
        
        print(f"\n✅ Operation completed: {result.get_summary()}")
        print(f"📊 Success rate: {result.get_success_rate():.1f}%")
        
        if result.has_errors():
            print("❌ Errors encountered:")
            for error in result.errors:
                print(f"   - {error}")
        
        if result.has_warnings():
            print("⚠️  Warnings:")
            for warning in result.warnings:
                print(f"   - {warning}")
        
        return result
    
    async def _load_parameter_with_retry(self, param_name: str, expected_value: Optional[str],
                                       error_type: Optional[str],
                                       progress_callback: Optional[Callable] = None) -> ParameterOperationResult:
        """Load a single parameter with retry logic."""
        max_attempts = self.error_handler.max_retries + 1
        
        for attempt in range(max_attempts):
            try:
                # Simulate parameter loading
                if error_type is None:
                    # Success case
                    print(f"   ✅ Successfully loaded {param_name} = {expected_value}")
                    return ParameterOperationResult(
                        parameter_name=param_name,
                        success=True,
                        value=expected_value,
                        duration_seconds=0.1
                    )
                else:
                    # Simulate different error types
                    if error_type == "timeout":
                        raise Exception(f"Device timeout while reading {param_name}")
                    elif error_type == "validation":
                        raise Exception(f"Invalid format for parameter {param_name}")
                    elif error_type == "busy":
                        raise Exception(f"Device is busy processing {param_name}")
                    elif error_type == "not_supported":
                        raise Exception(f"Parameter {param_name} not supported by device")
            
            except Exception as error:
                print(f"   ❌ Attempt {attempt + 1} failed: {error}")
                
                # Handle the error using the error handler
                if "timeout" in str(error).lower() or "busy" in str(error).lower():
                    # Use device communication error handler
                    error_result = self.error_handler.handle_device_communication_error(
                        error, f"READ_{param_name.upper()}", param_name, attempt
                    )
                else:
                    # Use general error handler
                    error_result = self.error_handler.handle_error(
                        error, "load_parameter", param_name, attempt
                    )
                
                print(f"   💡 {error_result.user_message}")
                
                if error_result.should_retry and attempt < max_attempts - 1:
                    print(f"   ⏳ Retrying in {error_result.retry_delay:.1f} seconds...")
                    await asyncio.sleep(error_result.retry_delay)
                    continue
                else:
                    # Create failed parameter result
                    print(f"   🚫 Giving up on {param_name}")
                    if error_result.suggestions:
                        print("   💡 Suggestions:")
                        for suggestion in error_result.suggestions[:3]:  # Show top 3
                            print(f"      - {suggestion}")
                    
                    return ParameterOperationResult(
                        parameter_name=param_name,
                        success=False,
                        error_message=error_result.user_message,
                        retry_count=attempt,
                        duration_seconds=0.1 * (attempt + 1)
                    )
        
        # Should not reach here
        return ParameterOperationResult(
            parameter_name=param_name,
            success=False,
            error_message="Unexpected error in retry logic"
        )
    
    async def save_to_device_with_error_handling(self, profile_data: Dict[str, Any],
                                               progress_callback: Optional[Callable] = None) -> ProfileOperationResult:
        """
        Save profile to device with comprehensive error handling.
        
        Demonstrates validation error handling and device communication errors.
        """
        print("🔄 Starting device profile save operation...")
        
        # Reset retry counts
        self.error_handler.reset_retry_counts()
        
        result = ProfileOperationResult(
            operation_type=OperationType.SAVE_TO_DEVICE,
            success=True
        )
        
        # First, validate all parameters
        print("\n🔍 Validating profile parameters...")
        validation_errors = []
        
        for param_name, value in profile_data.items():
            validation_result = self._validate_parameter(param_name, value)
            
            if not validation_result.is_valid:
                error_result = self.error_handler.handle_validation_error(
                    validation_result, param_name, value
                )
                
                print(f"   ❌ Validation failed for {param_name}: {error_result.user_message}")
                validation_errors.append(error_result)
                
                param_result = ParameterOperationResult(
                    parameter_name=param_name,
                    success=False,
                    error_message=error_result.user_message
                )
                result.add_parameter_result(param_result)
            else:
                print(f"   ✅ {param_name} validation passed")
        
        if validation_errors:
            print(f"\n⚠️  Found {len(validation_errors)} validation errors. Cannot proceed with save.")
            result.success = False
            return result
        
        # If validation passed, proceed with device save
        print("\n📤 Saving parameters to device...")
        
        for param_name, value in profile_data.items():
            param_result = await self._save_parameter_with_retry(param_name, value, progress_callback)
            result.add_parameter_result(param_result)
            
            if progress_callback:
                progress = (result.parameters_processed / len(profile_data)) * 100
                progress_callback(f"Saved {result.parameters_processed}/{len(profile_data)} parameters", progress)
        
        result.success = result.parameters_failed == 0
        
        print(f"\n✅ Save operation completed: {result.get_summary()}")
        return result
    
    def _validate_parameter(self, param_name: str, value: Any) -> ValidationResult:
        """Simulate parameter validation with various scenarios."""
        validation_result = ValidationResult(is_valid=True)
        
        # Simulate validation rules
        if param_name == "server_ip" and value:
            # Simple IP validation
            parts = str(value).split(".")
            if len(parts) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                validation_result.add_error("Invalid IP address format")
        
        elif param_name == "server_port" and value:
            # Port validation
            try:
                port = int(value)
                if not (1 <= port <= 65535):
                    validation_result.add_error("Port number must be between 1 and 65535")
            except ValueError:
                validation_result.add_error("Port must be a valid number")
        
        elif param_name == "apn_config" and value == "invalid_format":
            validation_result.add_error("APN configuration format is invalid")
            validation_result.add_error("Missing required APN server address")
        
        return validation_result
    
    async def _save_parameter_with_retry(self, param_name: str, value: Any,
                                       progress_callback: Optional[Callable] = None) -> ParameterOperationResult:
        """Save a single parameter with retry logic."""
        max_attempts = self.error_handler.max_retries + 1
        
        for attempt in range(max_attempts):
            try:
                # Simulate parameter saving with occasional errors
                if param_name == "connection_timeout" and attempt == 0:
                    # Simulate first attempt timeout
                    raise Exception("Device communication timeout")
                elif param_name == "device_id" and attempt < 2:
                    # Simulate device busy for first two attempts
                    raise Exception("Device is busy")
                else:
                    # Success
                    print(f"   ✅ Successfully saved {param_name} = {value}")
                    return ParameterOperationResult(
                        parameter_name=param_name,
                        success=True,
                        value=value,
                        retry_count=attempt,
                        duration_seconds=0.2 * (attempt + 1)
                    )
            
            except Exception as error:
                print(f"   ❌ Save attempt {attempt + 1} failed: {error}")
                
                error_result = self.error_handler.handle_device_communication_error(
                    error, f"WRITE_{param_name.upper()}", param_name, attempt
                )
                
                print(f"   💡 {error_result.user_message}")
                
                if error_result.should_retry and attempt < max_attempts - 1:
                    print(f"   ⏳ Retrying in {error_result.retry_delay:.1f} seconds...")
                    await asyncio.sleep(error_result.retry_delay)
                    continue
                else:
                    print(f"   🚫 Failed to save {param_name}")
                    return ParameterOperationResult(
                        parameter_name=param_name,
                        success=False,
                        error_message=error_result.user_message,
                        retry_count=attempt,
                        duration_seconds=0.2 * (attempt + 1)
                    )
        
        return ParameterOperationResult(
            parameter_name=param_name,
            success=False,
            error_message="Unexpected error in retry logic"
        )
    
    def handle_file_operation_error_demo(self, file_path: str, operation: str):
        """Demonstrate file operation error handling."""
        print(f"\n📁 Demonstrating file {operation} error handling...")
        
        # Simulate different file errors
        file_errors = [
            PermissionError("Access denied"),
            FileNotFoundError("File not found"),
            OSError("Disk full"),
            UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")
        ]
        
        for error in file_errors:
            print(f"\n❌ Simulating error: {error}")
            
            error_result = self.error_handler.handle_file_operation_error(
                error, file_path, operation
            )
            
            print(f"💡 User message: {error_result.user_message}")
            print(f"🔧 Category: {error_result.category.value}")
            print(f"⚠️  Severity: {error_result.severity.value}")
            print("💡 Suggestions:")
            for suggestion in error_result.suggestions[:3]:
                print(f"   - {suggestion}")


def progress_callback(message: str, percentage: float):
    """Simple progress callback for demonstration."""
    print(f"📊 Progress: {percentage:.1f}% - {message}")


async def main():
    """Main demonstration function."""
    print("🚀 ProfileErrorHandler Integration Demo")
    print("=" * 50)
    
    # Create enhanced profile manager with error handling
    mock_serial_service = Mock()
    manager = EnhancedUniversalProfileManager(mock_serial_service, "Parameter UI List.md")
    
    # Demo 1: Load from device with various errors
    print("\n🔸 Demo 1: Load from Device with Error Handling")
    print("-" * 45)
    
    load_result = await manager.load_from_device_with_error_handling(progress_callback)
    
    # Demo 2: Save to device with validation errors
    print("\n\n🔸 Demo 2: Save to Device with Validation Errors")
    print("-" * 48)
    
    # Profile data with some invalid values
    profile_data = {
        "server_ip": "192.168.1.100",      # Valid
        "server_port": "8080",             # Valid
        "connection_timeout": "30",        # Valid (will have retry scenario)
        "device_id": "LT32PRO_001",       # Valid (will have busy scenario)
        "invalid_ip": "999.999.999.999",   # Invalid IP
        "invalid_port": "99999",           # Invalid port (out of range)
        "apn_config": "invalid_format"     # Invalid format
    }
    
    save_result = await manager.save_to_device_with_error_handling(profile_data, progress_callback)
    
    # Demo 3: File operation error handling
    print("\n\n🔸 Demo 3: File Operation Error Handling")
    print("-" * 42)
    
    manager.handle_file_operation_error_demo("/path/to/profile.json", "write")
    
    # Demo 4: Error summary and reporting
    print("\n\n🔸 Demo 4: Error Summary and Reporting")
    print("-" * 40)
    
    # Collect errors from operations
    all_errors = []
    
    # Add errors from load operation
    for param_result in load_result.parameter_results:
        if not param_result.success and param_result.error_message:
            all_errors.append(Exception(param_result.error_message))
    
    # Add errors from save operation
    for param_result in save_result.parameter_results:
        if not param_result.success and param_result.error_message:
            all_errors.append(Exception(param_result.error_message))
    
    if all_errors:
        error_summary = manager.error_handler.create_error_summary(all_errors, "profile_operations")
        
        print(f"📊 Total errors encountered: {error_summary['total_errors']}")
        print("📋 Error categories:")
        
        for category, info in error_summary['categories'].items():
            print(f"   - {category}: {info['count']} errors (severity: {info['severity']})")
        
        print("\n💡 Top suggestions for resolution:")
        for i, suggestion in enumerate(error_summary['suggestions'][:5], 1):
            print(f"   {i}. {suggestion}")
    
    print("\n🎉 Demo completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())