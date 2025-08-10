"""
Unit tests for universal profile data models.
"""

import unittest
import json
from datetime import datetime
from models.universal_profile import (
    ProfileMetadata,
    ParameterValue,
    UniversalProfile
)
from models.validation_result import ValidationResult


class TestProfileMetadata(unittest.TestCase):
    """Test cases for ProfileMetadata class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.metadata = ProfileMetadata(
            parameter_spec_version="1.0",
            created_by="Test User",
            device_model="LT32 PRO",
            tags={"environment": "test", "version": "1.0"}
        )
    
    def test_creation(self):
        """Test metadata creation."""
        self.assertEqual(self.metadata.parameter_spec_version, "1.0")
        self.assertEqual(self.metadata.created_by, "Test User")
        self.assertEqual(self.metadata.device_model, "LT32 PRO")
        self.assertEqual(self.metadata.profile_format_version, "1.0")
        self.assertEqual(self.metadata.tags["environment"], "test")
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        data = self.metadata.to_dict()
        
        self.assertEqual(data["parameter_spec_version"], "1.0")
        self.assertEqual(data["created_by"], "Test User")
        self.assertEqual(data["device_model"], "LT32 PRO")
        self.assertEqual(data["profile_format_version"], "1.0")
        self.assertIn("tags", data)
        self.assertEqual(data["tags"]["environment"], "test")
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "parameter_spec_version": "2.0",
            "created_by": "Another User",
            "device_model": "LT32 PRO",
            "profile_format_version": "1.1",
            "tags": {"test": "value"}
        }
        
        metadata = ProfileMetadata.from_dict(data)
        
        self.assertEqual(metadata.parameter_spec_version, "2.0")
        self.assertEqual(metadata.created_by, "Another User")
        self.assertEqual(metadata.profile_format_version, "1.1")
        self.assertEqual(metadata.tags["test"], "value")
    
    def test_from_dict_defaults(self):
        """Test creation from dictionary with missing values."""
        data = {"parameter_spec_version": "1.0"}
        
        metadata = ProfileMetadata.from_dict(data)
        
        self.assertEqual(metadata.parameter_spec_version, "1.0")
        self.assertEqual(metadata.created_by, "LT32 PRO Configurator")
        self.assertEqual(metadata.device_model, "LT32 PRO")
        self.assertEqual(metadata.profile_format_version, "1.0")
        self.assertEqual(len(metadata.tags), 0)


class TestParameterValue(unittest.TestCase):
    """Test cases for ParameterValue class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.param_value = ParameterValue(
            value="test_value",
            source="user",
            is_modified=True
        )
    
    def test_creation(self):
        """Test parameter value creation."""
        self.assertEqual(self.param_value.value, "test_value")
        self.assertEqual(self.param_value.source, "user")
        self.assertTrue(self.param_value.is_modified)
        self.assertIsNotNone(self.param_value.timestamp)
    
    def test_post_init_timestamp(self):
        """Test that timestamp is set automatically."""
        param = ParameterValue(value="test")
        self.assertIsNotNone(param.timestamp)
        self.assertIsInstance(param.timestamp, datetime)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        data = self.param_value.to_dict()
        
        self.assertEqual(data["value"], "test_value")
        self.assertEqual(data["source"], "user")
        self.assertTrue(data["is_modified"])
        self.assertIsNotNone(data["timestamp"])
    
    def test_to_dict_with_validation(self):
        """Test conversion to dictionary with validation status."""
        validation = ValidationResult(is_valid=False, errors=["Test error"])
        self.param_value.validation_status = validation
        
        data = self.param_value.to_dict()
        
        self.assertIn("validation_status", data)
        self.assertFalse(data["validation_status"]["is_valid"])
        self.assertIn("Test error", data["validation_status"]["errors"])
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        timestamp = datetime.now()
        data = {
            "value": "dict_value",
            "source": "device",
            "timestamp": timestamp.isoformat(),
            "is_modified": False
        }
        
        param = ParameterValue.from_dict(data)
        
        self.assertEqual(param.value, "dict_value")
        self.assertEqual(param.source, "device")
        self.assertFalse(param.is_modified)
        # Timestamps might have slight differences due to precision
        self.assertAlmostEqual(
            param.timestamp.timestamp(),
            timestamp.timestamp(),
            places=0
        )
    
    def test_from_dict_with_validation(self):
        """Test creation from dictionary with validation status."""
        data = {
            "value": "test",
            "validation_status": {
                "is_valid": False,
                "errors": ["Test error"],
                "warnings": ["Test warning"]
            }
        }
        
        param = ParameterValue.from_dict(data)
        
        self.assertIsNotNone(param.validation_status)
        self.assertFalse(param.validation_status.is_valid)
        self.assertIn("Test error", param.validation_status.errors)
        self.assertIn("Test warning", param.validation_status.warnings)
    
    def test_from_dict_invalid_timestamp(self):
        """Test handling of invalid timestamp in dictionary."""
        data = {
            "value": "test",
            "timestamp": "invalid_timestamp"
        }
        
        param = ParameterValue.from_dict(data)
        
        # Should default to current time
        self.assertIsNotNone(param.timestamp)
        self.assertIsInstance(param.timestamp, datetime)
    
    def test_mark_modified(self):
        """Test marking parameter as modified."""
        param = ParameterValue(value="test", is_modified=False)
        original_timestamp = param.timestamp
        
        # Wait a tiny bit to ensure timestamp changes
        import time
        time.sleep(0.001)
        
        param.mark_modified()
        
        self.assertTrue(param.is_modified)
        self.assertGreater(param.timestamp, original_timestamp)
    
    def test_set_validation_result(self):
        """Test setting validation result."""
        param = ParameterValue(value="test")
        validation = ValidationResult(is_valid=True)
        
        param.set_validation_result(validation)
        
        self.assertEqual(param.validation_status, validation)


class TestUniversalProfile(unittest.TestCase):
    """Test cases for UniversalProfile class."""
    
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
        
        # Add some parameters
        self.profile.set_parameter_value("apn", "internet.com", "user")
        self.profile.set_parameter_value("port", 80, "device")
    
    def test_creation(self):
        """Test profile creation."""
        self.assertEqual(self.profile.name, "Test Profile")
        self.assertEqual(self.profile.version, "1.0")
        self.assertIsInstance(self.profile.created_at, datetime)
        self.assertIsInstance(self.profile.modified_at, datetime)
        self.assertEqual(len(self.profile.parameters), 2)
    
    def test_post_init_string_timestamps(self):
        """Test handling of string timestamps in post_init."""
        now = datetime.now()
        profile = UniversalProfile(
            name="Test",
            version="1.0",
            created_at=now.isoformat(),
            modified_at=now.isoformat(),
            metadata=self.metadata
        )
        
        self.assertIsInstance(profile.created_at, datetime)
        self.assertIsInstance(profile.modified_at, datetime)
    
    def test_get_parameter_value(self):
        """Test getting parameter values."""
        self.assertEqual(self.profile.get_parameter_value("apn"), "internet.com")
        self.assertEqual(self.profile.get_parameter_value("port"), 80)
        self.assertIsNone(self.profile.get_parameter_value("nonexistent"))
    
    def test_set_parameter_value_new(self):
        """Test setting a new parameter value."""
        original_modified = self.profile.modified_at
        
        # Wait a tiny bit to ensure timestamp changes
        import time
        time.sleep(0.001)
        
        self.profile.set_parameter_value("new_param", "new_value", "user")
        
        self.assertEqual(self.profile.get_parameter_value("new_param"), "new_value")
        self.assertEqual(self.profile.parameters["new_param"].source, "user")
        self.assertTrue(self.profile.parameters["new_param"].is_modified)
        self.assertGreater(self.profile.modified_at, original_modified)
    
    def test_set_parameter_value_existing(self):
        """Test updating an existing parameter value."""
        self.profile.set_parameter_value("apn", "new.apn.com", "user")
        
        self.assertEqual(self.profile.get_parameter_value("apn"), "new.apn.com")
        self.assertTrue(self.profile.parameters["apn"].is_modified)
    
    def test_get_parameter_info(self):
        """Test getting complete parameter information."""
        info = self.profile.get_parameter_info("apn")
        
        self.assertIsNotNone(info)
        self.assertEqual(info.value, "internet.com")
        self.assertEqual(info.source, "user")
        
        self.assertIsNone(self.profile.get_parameter_info("nonexistent"))
    
    def test_validate_basic(self):
        """Test basic profile validation without spec parser."""
        result = self.profile.validate()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_missing_name(self):
        """Test validation with missing name."""
        profile = UniversalProfile(
            name="",
            version="1.0",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            metadata=self.metadata
        )
        
        result = profile.validate()
        
        self.assertFalse(result.is_valid)
        self.assertIn("Profile name is required", result.errors)
    
    def test_validate_missing_version(self):
        """Test validation with missing version."""
        profile = UniversalProfile(
            name="Test",
            version="",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            metadata=self.metadata
        )
        
        result = profile.validate()
        
        self.assertFalse(result.is_valid)
        self.assertIn("Profile version is required", result.errors)
    
    def test_get_modified_parameters(self):
        """Test getting modified parameters."""
        # Mark one parameter as not modified
        self.profile.parameters["port"].is_modified = False
        
        modified = self.profile.get_modified_parameters()
        
        self.assertEqual(len(modified), 1)
        self.assertIn("apn", modified)
        self.assertNotIn("port", modified)
    
    def test_get_parameters_by_source(self):
        """Test getting parameters by source."""
        user_params = self.profile.get_parameters_by_source("user")
        device_params = self.profile.get_parameters_by_source("device")
        
        self.assertEqual(len(user_params), 1)
        self.assertIn("apn", user_params)
        
        self.assertEqual(len(device_params), 1)
        self.assertIn("port", device_params)
    
    def test_clear_modifications(self):
        """Test clearing modification flags."""
        self.assertTrue(self.profile.parameters["apn"].is_modified)
        
        self.profile.clear_modifications()
        
        self.assertFalse(self.profile.parameters["apn"].is_modified)
        self.assertFalse(self.profile.parameters["port"].is_modified)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        data = self.profile.to_dict()
        
        self.assertEqual(data["name"], "Test Profile")
        self.assertEqual(data["version"], "1.0")
        self.assertIn("created_at", data)
        self.assertIn("modified_at", data)
        self.assertIn("metadata", data)
        self.assertIn("parameters", data)
        self.assertEqual(len(data["parameters"]), 2)
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = self.profile.to_dict()
        
        new_profile = UniversalProfile.from_dict(data)
        
        self.assertEqual(new_profile.name, self.profile.name)
        self.assertEqual(new_profile.version, self.profile.version)
        self.assertEqual(len(new_profile.parameters), len(self.profile.parameters))
        self.assertEqual(new_profile.get_parameter_value("apn"), "internet.com")
    
    def test_from_dict_defaults(self):
        """Test creation from dictionary with missing values."""
        data = {}
        
        profile = UniversalProfile.from_dict(data)
        
        self.assertEqual(profile.name, "Unnamed Profile")
        self.assertEqual(profile.version, "1.0")
        self.assertIsInstance(profile.created_at, datetime)
        self.assertIsInstance(profile.modified_at, datetime)
        self.assertEqual(len(profile.parameters), 0)
    
    def test_to_json(self):
        """Test JSON serialization."""
        json_str = self.profile.to_json()
        
        # Should be valid JSON
        data = json.loads(json_str)
        self.assertEqual(data["name"], "Test Profile")
        self.assertIn("parameters", data)
    
    def test_from_json(self):
        """Test JSON deserialization."""
        json_str = self.profile.to_json()
        
        new_profile = UniversalProfile.from_json(json_str)
        
        self.assertEqual(new_profile.name, self.profile.name)
        self.assertEqual(new_profile.get_parameter_value("apn"), "internet.com")
    
    def test_clone(self):
        """Test profile cloning."""
        cloned = self.profile.clone("Cloned Profile")
        
        self.assertEqual(cloned.name, "Cloned Profile")
        self.assertEqual(cloned.get_parameter_value("apn"), "internet.com")
        self.assertNotEqual(cloned.created_at, self.profile.created_at)
        self.assertFalse(cloned.parameters["apn"].is_modified)
    
    def test_clone_same_name(self):
        """Test cloning without changing name."""
        cloned = self.profile.clone()
        
        self.assertEqual(cloned.name, self.profile.name)
        self.assertNotEqual(cloned.created_at, self.profile.created_at)


if __name__ == '__main__':
    unittest.main()