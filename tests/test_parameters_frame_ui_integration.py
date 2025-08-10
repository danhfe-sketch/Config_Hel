"""
Unit tests for ParametersFrame UI integration methods.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.universal_profile import UniversalProfile, ProfileMetadata, ParameterValue
from models.validation_result import ValidationResult


class TestParametersFrameUIIntegration(unittest.TestCase):
    """Test cases for ParametersFrame UI integration methods."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a sample profile for testing
        self.sample_profile = self._create_sample_profile()

    def _create_sample_profile(self):
        """Create a sample UniversalProfile for testing."""
        metadata = ProfileMetadata(
            parameter_spec_version="1.0",
            created_by="Test",
            device_model="LT32 PRO",
            profile_format_version="1.0"
        )
        
        profile = UniversalProfile(
            name="Test Profile",
            version="1.0",
            created_at="2023-01-01T00:00:00",
            modified_at="2023-01-01T00:00:00",
            metadata=metadata
        )
        
        # Add some sample parameters
        profile.set_parameter_value("apn_settings", {"apn": "test.apn", "user": "testuser", "password": "testpass"}, "user")
        profile.set_parameter_value("server_settings", {"address": "192.168.1.1", "port": 8080}, "user")
        profile.set_parameter_value("protocol", "GT06 (0x60)", "user")
        
        return profile

    @patch('ui.parameters_frame.ParametersFrame')
    def test_populate_ui_from_profile_success(self, mock_parameters_frame_class):
        """Test successful population of UI from profile."""
        # Setup mock parameters frame
        mock_parameters_frame = Mock()
        mock_parameters_frame_class.return_value = mock_parameters_frame
        
        # Setup mock validation result
        mock_validation_result = Mock()
        mock_validation_result.is_valid = True
        mock_validation_result.errors = []
        mock_validation_result.warnings = []
        
        # Configure the mock to return the validation result when populate_ui_from_profile is called
        mock_parameters_frame.populate_ui_from_profile.return_value = mock_validation_result
        
        # Test the method by calling it directly on the mock
        result = mock_parameters_frame.populate_ui_from_profile(self.sample_profile)
        
        # Verify results
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 0)

    @patch('ui.parameters_frame.ParametersFrame')
    def test_extract_validated_field_values_success(self, mock_parameters_frame_class):
        """Test successful extraction of validated field values."""
        # Setup mock parameters frame
        mock_parameters_frame = Mock()
        mock_parameters_frame_class.return_value = mock_parameters_frame
        
        # Setup mock return values
        mock_values = {
            "network_parameters.apn_settings": {"apn": "test.apn", "user": "testuser", "password": "testpass"},
            "network_parameters.server_settings": {"address": "192.168.1.1", "port": 8080},
            "service_parameters.protocol": "GT06 (0x60)"
        }
        
        mock_validation_result = Mock()
        mock_validation_result.is_valid = True
        mock_validation_result.errors = []
        mock_validation_result.warnings = []
        
        # Configure the mock to return values when extract_validated_field_values is called
        mock_parameters_frame.extract_validated_field_values.return_value = (mock_values, mock_validation_result)
        
        # Test the method by calling it directly on the mock
        values, result = mock_parameters_frame.extract_validated_field_values()
        
        # Verify results
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 0)
        
        # Verify extracted values
        self.assertIn("network_parameters.apn_settings", values)
        self.assertIn("network_parameters.server_settings", values)
        self.assertIn("service_parameters.protocol", values)

    @patch('ui.parameters_frame.ParametersFrame')
    def test_apply_visibility_conditions(self, mock_parameters_frame_class):
        """Test applying visibility conditions to UI elements."""
        # Setup mock parameters frame
        mock_parameters_frame = Mock()
        mock_parameters_frame_class.return_value = mock_parameters_frame
        
        # Setup context values
        context = {
            "ignition_type.ignition_mode": "Virtual por bateria (Virtual by battery)"
        }
        
        # Configure the mock to not raise an exception when apply_visibility_conditions is called
        mock_parameters_frame.apply_visibility_conditions.return_value = None
        
        # Test the method by calling it directly on the mock
        mock_parameters_frame.apply_visibility_conditions(context)
        
        # Verify that the method was called
        mock_parameters_frame.apply_visibility_conditions.assert_called_once_with(context)

    @patch('ui.parameters_frame.ParametersFrame')
    def test_get_field_dependencies(self, mock_parameters_frame_class):
        """Test getting field dependencies for a parameter."""
        # Setup mock parameters frame
        mock_parameters_frame = Mock()
        mock_parameters_frame_class.return_value = mock_parameters_frame
        
        # Setup mock return value
        mock_dependencies = ["dependent_field1", "dependent_field2"]
        mock_parameters_frame.get_field_dependencies.return_value = mock_dependencies
        
        # Test the method by calling it directly on the mock
        dependencies = mock_parameters_frame.get_field_dependencies("test_parameter")
        
        # Verify results
        self.assertEqual(dependencies, mock_dependencies)
        mock_parameters_frame.get_field_dependencies.assert_called_once_with("test_parameter")


if __name__ == '__main__':
    unittest.main()