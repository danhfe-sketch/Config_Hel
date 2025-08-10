"""
Unit tests for the Universal Profile Service.

This module contains comprehensive tests for profile creation, validation,
and transformation methods in the Universal Profile Service.
"""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from models.parameter_spec import ParameterSpec, ParameterCommands, UIElementType, ParameterField
from models.universal_profile import UniversalProfile, ProfileMetadata, ParameterValue
from models.validation_result import ValidationResult
from services.parameter_specification_parser import ParameterSpecificationParser
from services.universal_profile_service import UniversalProfileService


class TestUniversalProfileService(unittest.TestCase):
    """Test cases for the Universal Profile Service."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock parameter specification parser
        self.mock_spec_parser = Mock(spec=ParameterSpecificationParser)
        
        # Create test parameter specifications
        self.test_param_spec = ParameterSpec(
            name="test_param",
            label="Test Parameter",
            section="Test Section",
            ui_element=UIElementType.NUMBER_INPUT,
            validation="1-100",
            commands=ParameterCommands(
                set_command="SET_TEST <value>",
                read_command="READ_TEST"
            )
        )
        
        self.complex_param_spec = ParameterSpec(
            name="complex_param",
            label="Complex Parameter",
            section="Test Section",
            fields=[
                ParameterField(
                    name="field1",
                    label="Field 1",
                    ui_element=UIElementType.NUMBER_INPUT,
                    validation="0-255"
                ),
                ParameterField(
                    name="field2",
                    label="Field 2",
                    ui_element=UIElementType.TOGGLE_SWITCH
                )
            ],
            commands=ParameterCommands(
                set_command="SET_COMPLEX <field1>,<field2>",
                read_command="READ_COMPLEX"
            )
        )
        
        # Configure mock parser
        self.mock_spec_parser.get_parameter_spec.side_effect = self._mock_get_parameter_spec
        self.mock_spec_parser.get_all_parameters.return_value = ["test_param", "complex_param"]
        
        # Create service instance
        self.service = UniversalProfileService(self.mock_spec_parser)
    
    def _mock_get_parameter_spec(self, param_name: str):
        """Mock implementation of get_parameter_spec."""
        if param_name == "test_param":
            return self.test_param_spec
        elif param_name == "complex_param":
            return self.complex_param_spec
        return None
    
    def test_create_profile_from_ui_simple_parameters(self):
        """Test creating a profile from UI values with simple parameters."""
        ui_values = {
            "test_param": 50,
            "unknown_param": "test_value"
        }
        
        profile = self.service.create_profile_from_ui(ui_values, "Test Profile")
        
        # Verify profile structure
        self.assertEqual(profile.name, "Test Profile")
        self.assertEqual(profile.version, "1.0")
        self.assertIsInstance(profile.created_at, datetime)
        self.assertIsInstance(profile.modified_at, datetime)
        
        # Verify metadata
        self.assertEqual(profile.metadata.device_model, "LT32 PRO")
        self.assertEqual(profile.metadata.created_by, "LT32 PRO Configurator")
        
        # Verify parameters
        self.assertIn("test_param", profile.parameters)
        self.assertIn("unknown_param", profile.parameters)
        
        # Check known parameter
        test_param = profile.parameters["test_param"]
        self.assertEqual(test_param.value, 50)
        self.assertEqual(test_param.source, "user")
        self.assertTrue(test_param.is_modified)
        self.assertIsNotNone(test_param.validation_status)
        
        # Check unknown parameter
        unknown_param = profile.parameters["unknown_param"]
        self.assertEqual(unknown_param.value, "test_value")
        self.assertEqual(unknown_param.source, "user")
        self.assertTrue(unknown_param.is_modified)
        self.assertIsNotNone(unknown_param.validation_status)
        self.assertTrue(len(unknown_param.validation_status.warnings) > 0)
    
    def test_create_profile_from_ui_complex_parameters(self):
        """Test creating a profile from UI values with complex parameters."""
        ui_values = {
            "complex_param": {
                "field1": 128,
                "field2": True
            }
        }
        
        profile = self.service.create_profile_from_ui(ui_values, "Complex Profile")
        
        # Verify complex parameter
        self.assertIn("complex_param", profile.parameters)
        complex_param = profile.parameters["complex_param"]
        
        self.assertIsInstance(complex_param.value, dict)
        self.assertEqual(complex_param.value["field1"], 128)
        self.assertEqual(complex_param.value["field2"], True)
        self.assertEqual(complex_param.source, "user")
    
    def test_create_profile_from_device_simple_response(self):
        """Test creating a profile from device responses with simple parameters."""
        device_responses = {
            "test_param": "75",
            "unknown_param": "device_value"
        }
        
        # Mock the command parsing
        self.test_param_spec.commands.parse_read_response = Mock(return_value={"value_0": "75"})
        
        profile = self.service.create_profile_from_device(device_responses, "Device Profile")
        
        # Verify profile structure
        self.assertEqual(profile.name, "Device Profile")
        self.assertEqual(profile.metadata.tags.get("source"), "device")
        
        # Verify parameters
        self.assertIn("test_param", profile.parameters)
        self.assertIn("unknown_param", profile.parameters)
        
        # Check known parameter
        test_param = profile.parameters["test_param"]
        self.assertEqual(test_param.value, 75)  # Should be converted to int
        self.assertEqual(test_param.source, "device")
        self.assertFalse(test_param.is_modified)
        
        # Check unknown parameter (raw response)
        unknown_param = profile.parameters["unknown_param"]
        self.assertEqual(unknown_param.value, "device_value")
        self.assertEqual(unknown_param.source, "device")
    
    def test_create_profile_from_device_complex_response(self):
        """Test creating a profile from device responses with complex parameters."""
        device_responses = {
            "complex_param": "200,1"
        }
        
        # Mock the command parsing for complex parameter
        self.complex_param_spec.commands.parse_read_response = Mock(
            return_value={"value_0": "200", "value_1": "1"}
        )
        
        profile = self.service.create_profile_from_device(device_responses, "Complex Device Profile")
        
        # Verify complex parameter
        self.assertIn("complex_param", profile.parameters)
        complex_param = profile.parameters["complex_param"]
        
        self.assertIsInstance(complex_param.value, dict)
        self.assertEqual(complex_param.value["field1"], 200)
        self.assertEqual(complex_param.value["field2"], True)  # "1" converted to True
        self.assertEqual(complex_param.source, "device")
    
    def test_save_profile_to_file(self):
        """Test saving a profile to a JSON file."""
        # Create a test profile
        profile = self._create_test_profile()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_profile.json"
            
            # Save profile
            result = self.service.save_profile_to_file(profile, str(file_path))
            
            # Verify save was successful
            self.assertTrue(result)
            self.assertTrue(file_path.exists())
            
            # Verify file content
            with open(file_path, 'r', encoding='utf-8') as file:
                saved_data = json.load(file)
            
            self.assertEqual(saved_data["name"], "Test Profile")
            self.assertEqual(saved_data["version"], "1.0")
            self.assertIn("parameters", saved_data)
    
    def test_save_profile_to_file_creates_directory(self):
        """Test that saving a profile creates necessary directories."""
        profile = self._create_test_profile()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "subdir" / "test_profile.json"
            
            # Save profile (should create subdir)
            result = self.service.save_profile_to_file(profile, str(file_path))
            
            # Verify save was successful and directory was created
            self.assertTrue(result)
            self.assertTrue(file_path.exists())
            self.assertTrue(file_path.parent.exists())
    
    def test_load_profile_from_file(self):
        """Test loading a profile from a JSON file."""
        # Create and save a test profile
        original_profile = self._create_test_profile()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_profile.json"
            
            # Save original profile
            self.service.save_profile_to_file(original_profile, str(file_path))
            
            # Load profile
            loaded_profile = self.service.load_profile_from_file(str(file_path))
            
            # Verify loaded profile
            self.assertEqual(loaded_profile.name, original_profile.name)
            self.assertEqual(loaded_profile.version, original_profile.version)
            self.assertEqual(len(loaded_profile.parameters), len(original_profile.parameters))
            
            # Check specific parameter
            self.assertIn("test_param", loaded_profile.parameters)
            loaded_param = loaded_profile.parameters["test_param"]
            original_param = original_profile.parameters["test_param"]
            self.assertEqual(loaded_param.value, original_param.value)
            self.assertEqual(loaded_param.source, original_param.source)
    
    def test_load_profile_from_nonexistent_file(self):
        """Test loading a profile from a non-existent file."""
        with self.assertRaises(FileNotFoundError):
            self.service.load_profile_from_file("nonexistent_file.json")
    
    def test_load_profile_from_invalid_json(self):
        """Test loading a profile from an invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write("invalid json content")
            temp_file_path = temp_file.name
        
        try:
            with self.assertRaises(ValueError):
                self.service.load_profile_from_file(temp_file_path)
        finally:
            Path(temp_file_path).unlink()
    
    def test_validate_profile_valid(self):
        """Test validating a valid profile."""
        profile = self._create_test_profile()
        
        # Mock validation to return valid results
        self.test_param_spec.validate_value = Mock(return_value=ValidationResult(is_valid=True))
        
        result = self.service.validate_profile(profile)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_profile_with_errors(self):
        """Test validating a profile with validation errors."""
        profile = self._create_test_profile()
        profile.name = ""  # Invalid name
        
        # Mock validation to return errors
        validation_result = ValidationResult(is_valid=False)
        validation_result.add_error("Value out of range")
        self.test_param_spec.validate_value = Mock(return_value=validation_result)
        
        result = self.service.validate_profile(profile)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(len(result.errors) > 0)
        self.assertIn("Profile name is required", result.errors)
    
    def test_validate_profile_adds_missing_parameters(self):
        """Test that validation adds missing parameters with default values."""
        profile = self._create_test_profile()
        
        # Remove a parameter that should exist
        del profile.parameters["complex_param"]
        
        # Mock default value
        self.complex_param_spec.get_default_value = Mock(return_value={"field1": 0, "field2": False})
        self.complex_param_spec.validate_value = Mock(return_value=ValidationResult(is_valid=True))
        
        result = self.service.validate_profile(profile)
        
        # Verify parameter was added back
        self.assertIn("complex_param", profile.parameters)
        added_param = profile.parameters["complex_param"]
        self.assertEqual(added_param.source, "default")
        self.assertTrue(len(result.warnings) > 0)
    
    def test_migrate_profile(self):
        """Test migrating a profile to current specifications."""
        profile = self._create_test_profile()
        
        # Remove a parameter to simulate old profile format
        del profile.parameters["complex_param"]
        original_modified_time = profile.modified_at
        
        # Mock default value for missing parameter
        self.complex_param_spec.get_default_value = Mock(return_value={"field1": 0, "field2": False})
        
        migrated_profile = self.service.migrate_profile(profile)
        
        # Verify migration
        self.assertIn("complex_param", migrated_profile.parameters)
        self.assertEqual(migrated_profile.parameters["complex_param"].source, "default")
        self.assertGreater(migrated_profile.modified_at, original_modified_time)
        self.assertEqual(migrated_profile.metadata.parameter_spec_version, "1.0")
    
    def test_get_profile_summary(self):
        """Test getting a profile summary."""
        profile = self._create_test_profile()
        
        summary = self.service.get_profile_summary(profile)
        
        # Verify summary structure
        self.assertIn("name", summary)
        self.assertIn("version", summary)
        self.assertIn("total_parameters", summary)
        self.assertIn("modified_parameters", summary)
        self.assertIn("device_parameters", summary)
        self.assertIn("user_parameters", summary)
        self.assertIn("default_parameters", summary)
        self.assertIn("validation_errors", summary)
        self.assertIn("validation_warnings", summary)
        self.assertIn("metadata", summary)
        
        # Verify values
        self.assertEqual(summary["name"], "Test Profile")
        self.assertEqual(summary["total_parameters"], len(profile.parameters))
    
    def test_compare_profiles(self):
        """Test comparing two profiles."""
        profile1 = self._create_test_profile()
        profile2 = self._create_test_profile()
        profile2.name = "Modified Profile"
        
        # Modify profile2
        profile2.set_parameter_value("test_param", 100)
        profile2.set_parameter_value("new_param", "new_value")
        del profile2.parameters["complex_param"]
        
        comparison = self.service.compare_profiles(profile1, profile2)
        
        # Verify comparison results
        self.assertIn("added_parameters", comparison)
        self.assertIn("removed_parameters", comparison)
        self.assertIn("changed_parameters", comparison)
        self.assertIn("unchanged_parameters", comparison)
        
        self.assertIn("new_param", comparison["added_parameters"])
        self.assertIn("complex_param", comparison["removed_parameters"])
        
        # Check changed parameters
        changed_params = {item["parameter"] for item in comparison["changed_parameters"]}
        self.assertIn("test_param", changed_params)
    
    def test_parse_device_response_simple(self):
        """Test parsing simple device responses."""
        # Mock command parsing
        self.test_param_spec.commands.parse_read_response = Mock(return_value={"value_0": "42"})
        
        result = self.service._parse_device_response(self.test_param_spec, "42")
        
        self.assertEqual(result, 42)  # Should be converted to int
    
    def test_parse_device_response_complex(self):
        """Test parsing complex device responses."""
        # Mock command parsing
        self.complex_param_spec.commands.parse_read_response = Mock(
            return_value={"value_0": "150", "value_1": "0"}
        )
        
        result = self.service._parse_device_response(self.complex_param_spec, "150,0")
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["field1"], 150)
        self.assertEqual(result["field2"], False)  # "0" converted to False
    
    def test_convert_field_value_number(self):
        """Test converting field values for number inputs."""
        field = ParameterField(
            name="test_field",
            label="Test Field",
            ui_element=UIElementType.NUMBER_INPUT
        )
        
        result = self.service._convert_field_value(field, "123")
        self.assertEqual(result, 123)
        
        result = self.service._convert_field_value(field, "123.45")
        self.assertEqual(result, 123.45)
        
        # Test invalid number
        result = self.service._convert_field_value(field, "invalid")
        self.assertEqual(result, field.get_default_value())
    
    def test_convert_field_value_toggle(self):
        """Test converting field values for toggle switches."""
        field = ParameterField(
            name="test_field",
            label="Test Field",
            ui_element=UIElementType.TOGGLE_SWITCH
        )
        
        # Test various true values
        for true_value in ["true", "1", "on", "yes", "TRUE", "ON"]:
            result = self.service._convert_field_value(field, true_value)
            self.assertTrue(result)
        
        # Test various false values
        for false_value in ["false", "0", "off", "no", "FALSE", "OFF"]:
            result = self.service._convert_field_value(field, false_value)
            self.assertFalse(result)
    
    def _create_test_profile(self) -> UniversalProfile:
        """Create a test profile for testing."""
        metadata = ProfileMetadata(
            parameter_spec_version="1.0",
            created_by="Test",
            device_model="LT32 PRO"
        )
        
        profile = UniversalProfile(
            name="Test Profile",
            version="1.0",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            metadata=metadata
        )
        
        # Add test parameters
        profile.set_parameter_value("test_param", 50, "user")
        profile.set_parameter_value("complex_param", {"field1": 100, "field2": True}, "user")
        
        return profile


if __name__ == '__main__':
    unittest.main()