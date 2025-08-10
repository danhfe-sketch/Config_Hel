"""
Unit tests for operation result data models.
"""

import unittest
from datetime import datetime
from models.operation_result import (
    OperationType,
    ParameterOperationResult,
    ProfileOperationResult
)
from models.universal_profile import UniversalProfile, ProfileMetadata


class TestOperationType(unittest.TestCase):
    """Test cases for OperationType enum."""
    
    def test_enum_values(self):
        """Test that all expected enum values exist."""
        self.assertEqual(OperationType.LOAD_FROM_DEVICE.value, "load_from_device")
        self.assertEqual(OperationType.SAVE_TO_DEVICE.value, "save_to_device")
        self.assertEqual(OperationType.LOAD_FROM_FILE.value, "load_from_file")
        self.assertEqual(OperationType.SAVE_TO_FILE.value, "save_to_file")
        self.assertEqual(OperationType.VALIDATE_PROFILE.value, "validate_profile")
        self.assertEqual(OperationType.MIGRATE_PROFILE.value, "migrate_profile")


class TestParameterOperationResult(unittest.TestCase):
    """Test cases for ParameterOperationResult class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.success_result = ParameterOperationResult(
            parameter_name="apn",
            success=True,
            value="internet.com",
            duration_seconds=0.5
        )
        
        self.failure_result = ParameterOperationResult(
            parameter_name="port",
            success=False,
            error_message="Connection timeout",
            retry_count=3,
            device_response="ERROR"
        )
    
    def test_creation_success(self):
        """Test creation of successful parameter result."""
        self.assertEqual(self.success_result.parameter_name, "apn")
        self.assertTrue(self.success_result.success)
        self.assertEqual(self.success_result.value, "internet.com")
        self.assertEqual(self.success_result.duration_seconds, 0.5)
        self.assertIsNone(self.success_result.error_message)
    
    def test_creation_failure(self):
        """Test creation of failed parameter result."""
        self.assertEqual(self.failure_result.parameter_name, "port")
        self.assertFalse(self.failure_result.success)
        self.assertEqual(self.failure_result.error_message, "Connection timeout")
        self.assertEqual(self.failure_result.retry_count, 3)
        self.assertEqual(self.failure_result.device_response, "ERROR")
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        data = self.success_result.to_dict()
        
        self.assertEqual(data["parameter_name"], "apn")
        self.assertTrue(data["success"])
        self.assertEqual(data["value"], "internet.com")
        self.assertEqual(data["duration_seconds"], 0.5)
        self.assertIsNone(data["error_message"])
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "parameter_name": "test_param",
            "success": False,
            "error_message": "Test error",
            "duration_seconds": 1.0,
            "retry_count": 2
        }
        
        result = ParameterOperationResult.from_dict(data)
        
        self.assertEqual(result.parameter_name, "test_param")
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Test error")
        self.assertEqual(result.duration_seconds, 1.0)
        self.assertEqual(result.retry_count, 2)


class TestProfileOperationResult(unittest.TestCase):
    """Test cases for ProfileOperationResult class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.metadata = ProfileMetadata(parameter_spec_version="1.0")
        self.profile = UniversalProfile(
            name="Test Profile",
            version="1.0",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            metadata=self.metadata
        )
        
        self.operation_result = ProfileOperationResult(
            operation_type=OperationType.LOAD_FROM_DEVICE,
            success=True,
            profile=self.profile,
            duration_seconds=5.0
        )
    
    def test_creation(self):
        """Test operation result creation."""
        self.assertEqual(self.operation_result.operation_type, OperationType.LOAD_FROM_DEVICE)
        self.assertTrue(self.operation_result.success)
        self.assertEqual(self.operation_result.profile, self.profile)
        self.assertEqual(self.operation_result.duration_seconds, 5.0)
        self.assertEqual(self.operation_result.parameters_processed, 0)
        self.assertEqual(self.operation_result.parameters_successful, 0)
        self.assertEqual(self.operation_result.parameters_failed, 0)
    
    def test_post_init_timestamps(self):
        """Test that timestamps are set automatically."""
        result = ProfileOperationResult(
            operation_type=OperationType.SAVE_TO_DEVICE,
            success=True
        )
        
        self.assertIsNotNone(result.started_at)
        self.assertIsNotNone(result.completed_at)
        self.assertIsInstance(result.started_at, datetime)
        self.assertIsInstance(result.completed_at, datetime)
    
    def test_add_error(self):
        """Test adding errors."""
        result = ProfileOperationResult(
            operation_type=OperationType.LOAD_FROM_DEVICE,
            success=True
        )
        
        result.add_error("Test error")
        
        self.assertFalse(result.success)
        self.assertIn("Test error", result.errors)
    
    def test_add_warning(self):
        """Test adding warnings."""
        result = ProfileOperationResult(
            operation_type=OperationType.LOAD_FROM_DEVICE,
            success=True
        )
        
        result.add_warning("Test warning")
        
        self.assertTrue(result.success)  # Warnings don't affect success
        self.assertIn("Test warning", result.warnings)
    
    def test_add_detail(self):
        """Test adding details."""
        self.operation_result.add_detail("key1", "value1")
        self.operation_result.add_detail("key2", 42)
        
        self.assertEqual(self.operation_result.details["key1"], "value1")
        self.assertEqual(self.operation_result.details["key2"], 42)
    
    def test_add_parameter_result_success(self):
        """Test adding successful parameter result."""
        param_result = ParameterOperationResult(
            parameter_name="apn",
            success=True,
            value="internet.com"
        )
        
        self.operation_result.add_parameter_result(param_result)
        
        self.assertEqual(self.operation_result.parameters_processed, 1)
        self.assertEqual(self.operation_result.parameters_successful, 1)
        self.assertEqual(self.operation_result.parameters_failed, 0)
        self.assertEqual(len(self.operation_result.parameter_results), 1)
    
    def test_add_parameter_result_failure(self):
        """Test adding failed parameter result."""
        param_result = ParameterOperationResult(
            parameter_name="port",
            success=False,
            error_message="Connection failed"
        )
        
        self.operation_result.add_parameter_result(param_result)
        
        self.assertEqual(self.operation_result.parameters_processed, 1)
        self.assertEqual(self.operation_result.parameters_successful, 0)
        self.assertEqual(self.operation_result.parameters_failed, 1)
        self.assertIn("Parameter port: Connection failed", self.operation_result.errors)
    
    def test_add_parameter_result_with_warning(self):
        """Test adding parameter result with warning."""
        param_result = ParameterOperationResult(
            parameter_name="test",
            success=True,
            warning_message="Test warning"
        )
        
        self.operation_result.add_parameter_result(param_result)
        
        self.assertIn("Parameter test: Test warning", self.operation_result.warnings)
    
    def test_get_failed_parameters(self):
        """Test getting failed parameters."""
        success_result = ParameterOperationResult("param1", True)
        failure_result = ParameterOperationResult("param2", False)
        
        self.operation_result.add_parameter_result(success_result)
        self.operation_result.add_parameter_result(failure_result)
        
        failed = self.operation_result.get_failed_parameters()
        
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0].parameter_name, "param2")
    
    def test_get_successful_parameters(self):
        """Test getting successful parameters."""
        success_result = ParameterOperationResult("param1", True)
        failure_result = ParameterOperationResult("param2", False)
        
        self.operation_result.add_parameter_result(success_result)
        self.operation_result.add_parameter_result(failure_result)
        
        successful = self.operation_result.get_successful_parameters()
        
        self.assertEqual(len(successful), 1)
        self.assertEqual(successful[0].parameter_name, "param1")
    
    def test_get_parameters_with_warnings(self):
        """Test getting parameters with warnings."""
        normal_result = ParameterOperationResult("param1", True)
        warning_result = ParameterOperationResult("param2", True, warning_message="Warning")
        
        self.operation_result.add_parameter_result(normal_result)
        self.operation_result.add_parameter_result(warning_result)
        
        with_warnings = self.operation_result.get_parameters_with_warnings()
        
        self.assertEqual(len(with_warnings), 1)
        self.assertEqual(with_warnings[0].parameter_name, "param2")
    
    def test_get_success_rate(self):
        """Test calculating success rate."""
        # No parameters processed
        self.assertEqual(self.operation_result.get_success_rate(), 0.0)
        
        # Add some results
        self.operation_result.add_parameter_result(ParameterOperationResult("param1", True))
        self.operation_result.add_parameter_result(ParameterOperationResult("param2", True))
        self.operation_result.add_parameter_result(ParameterOperationResult("param3", False))
        
        # 2 out of 3 successful = 66.67%
        self.assertAlmostEqual(self.operation_result.get_success_rate(), 66.67, places=1)
    
    def test_has_errors(self):
        """Test has_errors method."""
        self.assertFalse(self.operation_result.has_errors())
        
        self.operation_result.add_error("Test error")
        self.assertTrue(self.operation_result.has_errors())
    
    def test_has_warnings(self):
        """Test has_warnings method."""
        self.assertFalse(self.operation_result.has_warnings())
        
        self.operation_result.add_warning("Test warning")
        self.assertTrue(self.operation_result.has_warnings())
    
    def test_is_partial_success(self):
        """Test partial success detection."""
        self.assertFalse(self.operation_result.is_partial_success())
        
        # Add mixed results
        self.operation_result.add_parameter_result(ParameterOperationResult("param1", True))
        self.operation_result.add_parameter_result(ParameterOperationResult("param2", False))
        
        self.assertTrue(self.operation_result.is_partial_success())
    
    def test_get_summary_success(self):
        """Test summary for successful operation."""
        self.operation_result.add_parameter_result(ParameterOperationResult("param1", True))
        
        summary = self.operation_result.get_summary()
        self.assertIn("Load From Device completed successfully", summary)
        self.assertIn("(1/1 parameters)", summary)
    
    def test_get_summary_with_warnings(self):
        """Test summary for operation with warnings."""
        self.operation_result.add_parameter_result(ParameterOperationResult("param1", True))
        self.operation_result.add_warning("Test warning")
        
        summary = self.operation_result.get_summary()
        self.assertIn("completed with warnings", summary)
        self.assertIn("1 warnings", summary)
    
    def test_get_summary_partial_success(self):
        """Test summary for partial success."""
        self.operation_result.add_parameter_result(ParameterOperationResult("param1", True))
        self.operation_result.add_parameter_result(ParameterOperationResult("param2", False))
        
        summary = self.operation_result.get_summary()
        self.assertIn("partially completed", summary)
        self.assertIn("(1/2 parameters successful)", summary)
    
    def test_get_summary_failure(self):
        """Test summary for failed operation."""
        self.operation_result.success = False
        self.operation_result.add_parameter_result(ParameterOperationResult("param1", False))
        
        summary = self.operation_result.get_summary()
        self.assertIn("failed", summary)
        self.assertIn("(1/1 parameters failed)", summary)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        self.operation_result.add_parameter_result(ParameterOperationResult("param1", True))
        
        data = self.operation_result.to_dict()
        
        self.assertEqual(data["operation_type"], "load_from_device")
        self.assertTrue(data["success"])
        self.assertIsNotNone(data["profile"])
        self.assertEqual(data["parameters_processed"], 1)
        self.assertEqual(len(data["parameter_results"]), 1)
        self.assertIsNotNone(data["started_at"])
        self.assertIsNotNone(data["completed_at"])
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = self.operation_result.to_dict()
        
        new_result = ProfileOperationResult.from_dict(data)
        
        self.assertEqual(new_result.operation_type, self.operation_result.operation_type)
        self.assertEqual(new_result.success, self.operation_result.success)
        self.assertEqual(new_result.duration_seconds, self.operation_result.duration_seconds)
        self.assertIsNotNone(new_result.profile)
    
    def test_str_representation(self):
        """Test string representation."""
        self.operation_result.add_parameter_result(ParameterOperationResult("param1", True))
        self.operation_result.add_error("Test error")
        self.operation_result.add_warning("Test warning")
        
        result_str = str(self.operation_result)
        
        self.assertIn("Load From Device", result_str)
        self.assertIn("Duration:", result_str)
        self.assertIn("Test error", result_str)
        self.assertIn("Test warning", result_str)


if __name__ == '__main__':
    unittest.main()