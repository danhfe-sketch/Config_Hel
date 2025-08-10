"""
Unit tests for UniversalProfileService UI integration methods.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.universal_profile_service import UniversalProfileService
from models.universal_profile import UniversalProfile, ProfileMetadata, ParameterValue
from models.validation_result import ValidationResult
from services.parameter_specification_parser import ParameterSpecificationParser


class TestUniversalProfileServiceUIIntegration(unittest.TestCase):
    """Test cases for UniversalProfileService UI integration methods."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock specification parser
        self.mock_spec_parser = Mock(spec=ParameterSpecificationParser)
        
        # Create the UniversalProfileService instance
        self.profile_service = UniversalProfileService(self.mock_spec_parser)
        
        # Create a sample profile for testing
        self.sample_profile = self._create_sample_profile()
        
        # Create sample UI elements for testing
        self.sample_ui_elements = self._create_sample_ui_elements()

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
            created_at=datetime.now(),
            modified_at=datetime.now(),
            metadata=metadata
        )
        
        # Add some sample parameters
        profile.set_parameter_value("apn_settings", {"apn": "test.apn", "user": "testuser", "password": "testpass"}, "user")
        profile.set_parameter_value("server_settings", {"address": "192.168.1.1", "port": 8080}, "user")
        profile.set_parameter_value("protocol", "GT06 (0x60)", "user")
        
        return profile

    def _create_sample_ui_elements(self):
        """Create sample UI elements for testing."""
        ui_elements = {}
        
        # Create mock UI elements
        apn_element = Mock()
        apn_element.get_value.return_value = {"apn": "test.apn", "user": "testuser", "password": "testpass"}
        apn_element.validate.return_value = True
        apn_element.get_validation_error.return_value = None
        apn_element.set_value = Mock()
        ui_elements["network_parameters.apn_settings"] = apn_element
        
        server_element = Mock()
        server_element.get_value.return_value = {"address": "192.168.1.1", "port": 8080}
        server_element.validate.return_value = True
        server_element.get_validation_error.return_value = None
        server_element.set_value = Mock()
        ui_elements["network_parameters.server_settings"] = server_element
        
        protocol_element = Mock()
        protocol_element.get_value.return_value = "GT06 (0x60)"
        protocol_element.validate.return_value = True
        protocol_element.get_validation_error.return_value = None
        protocol_element.set_value = Mock()
        ui_elements["service_parameters.protocol"] = protocol_element
        
        return ui_elements

    @patch('services.universal_profile_service.ProfileUIPopulator')
    def test_extract_validated_ui_values_success(self, mock_profile_ui_populator_class):
        """Test successful extraction of validated UI values."""
        # Setup mock ProfileUIPopulator
        mock_profile_ui_populator = Mock()
        mock_profile_ui_populator_class.return_value = mock_profile_ui_populator
        
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
        
        # Configure the mock ProfileUIPopulator
        mock_profile_ui_populator.extract_validated_field_values.return_value = (
            mock_values, mock_validation_result
        )
        
        # Create a new profile service with the mocked ProfileUIPopulator
        profile_service = UniversalProfileService(self.mock_spec_parser)
        
        # Test the method
        values, result = profile_service.extract_validated_ui_values(self.sample_ui_elements)
        
        # Verify results
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 0)
        
        # Verify extracted values
        self.assertIn("network_parameters.apn_settings", values)
        self.assertIn("network_parameters.server_settings", values)
        self.assertIn("service_parameters.protocol", values)
        
        # Verify that the ProfileUIPopulator method was called
        mock_profile_ui_populator.extract_validated_field_values.assert_called_once_with(
            self.sample_ui_elements
        )

    @patch('services.universal_profile_service.ProfileUIPopulator')
    def test_populate_ui_from_profile_data_success(self, mock_profile_ui_populator_class):
        """Test successful population of UI from profile data."""
        # Setup mock ProfileUIPopulator
        mock_profile_ui_populator = Mock()
        mock_profile_ui_populator_class.return_value = mock_profile_ui_populator
        
        # Setup mock validation result
        mock_validation_result = Mock()
        mock_validation_result.is_valid = True
        mock_validation_result.errors = []
        mock_validation_result.warnings = []
        
        # Configure the mock ProfileUIPopulator
        mock_profile_ui_populator.populate_ui_from_profile.return_value = mock_validation_result
        
        # Create a new profile service with the mocked ProfileUIPopulator
        profile_service = UniversalProfileService(self.mock_spec_parser)
        
        # Test the method
        result = profile_service.populate_ui_from_profile_data(
            self.sample_profile, 
            self.sample_ui_elements
        )
        
        # Verify results
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 0)
        
        # Verify that the ProfileUIPopulator method was called
        mock_profile_ui_populator.populate_ui_from_profile.assert_called_once_with(
            self.sample_profile, 
            self.sample_ui_elements
        )

    @patch('services.universal_profile_service.ProfileUIPopulator')
    def test_get_field_dependencies_for_parameter(self, mock_profile_ui_populator_class):
        """Test getting field dependencies for a parameter."""
        # Setup mock ProfileUIPopulator
        mock_profile_ui_populator = Mock()
        mock_profile_ui_populator_class.return_value = mock_profile_ui_populator
        
        # Setup mock return value
        mock_dependencies = ["dependent_field1", "dependent_field2"]
        mock_profile_ui_populator.get_field_dependencies.return_value = mock_dependencies
        
        # Create a new profile service with the mocked ProfileUIPopulator
        profile_service = UniversalProfileService(self.mock_spec_parser)
        
        # Test the method
        dependencies = profile_service.get_field_dependencies_for_parameter("test_parameter")
        
        # Verify results
        self.assertEqual(dependencies, mock_dependencies)
        mock_profile_ui_populator.get_field_dependencies.assert_called_once_with("test_parameter")

    @patch('services.universal_profile_service.ProfileUIPopulator')
    def test_apply_visibility_conditions_to_profile(self, mock_profile_ui_populator_class):
        """Test applying visibility conditions to a profile."""
        # Setup mock ProfileUIPopulator
        mock_profile_ui_populator = Mock()
        mock_profile_ui_populator_class.return_value = mock_profile_ui_populator
        
        # Create a new profile service with the mocked ProfileUIPopulator
        profile_service = UniversalProfileService(self.mock_spec_parser)
        
        # Test the method
        profile_service.apply_visibility_conditions_to_profile(
            self.sample_profile, 
            {"context": "value"}
        )
        
        # Verify that the ProfileUIPopulator method was called
        mock_profile_ui_populator.validate_profile_data_integrity.assert_called_once_with(
            self.sample_profile
        )


if __name__ == '__main__':
    unittest.main()