"""
Unit tests for the ProfileUIPopulator service.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from models.universal_profile import UniversalProfile, ProfileMetadata, ParameterValue
from models.validation_result import ValidationResult
from services.profile_ui_populator import ProfileUIPopulator
from services.parameter_specification_parser import ParameterSpecificationParser
from ui.parameter_ui_element_factory import UIElementConfig


class TestProfileUIPopulator(unittest.TestCase):
    """Test cases for the ProfileUIPopulator service."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock specification parser
        self.mock_spec_parser = Mock(spec=ParameterSpecificationParser)
        self.profile_ui_populator = ProfileUIPopulator(self.mock_spec_parser)
        
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
        apn_element.set_visibility = Mock()
        ui_elements["apn_settings"] = apn_element
        
        server_element = Mock()
        server_element.get_value.return_value = {"address": "192.168.1.1", "port": 8080}
        server_element.validate.return_value = True
        server_element.get_validation_error.return_value = None
        server_element.set_value = Mock()
        server_element.set_visibility = Mock()
        ui_elements["server_settings"] = server_element
        
        protocol_element = Mock()
        protocol_element.get_value.return_value = "GT06 (0x60)"
        protocol_element.validate.return_value = True
        protocol_element.get_validation_error.return_value = None
        protocol_element.set_value = Mock()
        protocol_element.set_visibility = Mock()
        ui_elements["protocol"] = protocol_element
        
        return ui_elements

    def test_populate_ui_from_profile_success(self):
        """Test successful population of UI elements from a profile."""
        # Setup mock parameter specifications
        mock_apn_spec = Mock()
        mock_apn_spec.visibility_condition = None
        
        mock_server_spec = Mock()
        mock_server_spec.visibility_condition = None
        
        mock_protocol_spec = Mock()
        mock_protocol_spec.visibility_condition = None
        
        self.mock_spec_parser.parse_specifications.return_value = {
            "apn_settings": mock_apn_spec,
            "server_settings": mock_server_spec,
            "protocol": mock_protocol_spec
        }
        
        self.mock_spec_parser.get_parameter_spec.side_effect = [
            mock_apn_spec,
            mock_server_spec,
            mock_protocol_spec
        ]
        
        # Test the method
        result = self.profile_ui_populator.populate_ui_from_profile(
            self.sample_profile, 
            self.sample_ui_elements
        )
        
        # Verify results
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 0)
        
        # Verify that set_value was called on UI elements
        self.sample_ui_elements["apn_settings"].set_value.assert_called_once_with(
            {"apn": "test.apn", "user": "testuser", "password": "testpass"}
        )
        self.sample_ui_elements["server_settings"].set_value.assert_called_once_with(
            {"address": "192.168.1.1", "port": 8080}
        )
        self.sample_ui_elements["protocol"].set_value.assert_called_once_with(
            "GT06 (0x60)"
        )

    def test_populate_ui_from_profile_with_validation_error(self):
        """Test population of UI elements with validation errors."""
        # Setup mock parameter specifications
        mock_apn_spec = Mock()
        mock_apn_spec.visibility_condition = None
        
        self.mock_spec_parser.parse_specifications.return_value = {
            "apn_settings": mock_apn_spec
        }
        
        self.mock_spec_parser.get_parameter_spec.return_value = mock_apn_spec
        
        # Make the UI element validation fail
        self.sample_ui_elements["apn_settings"].validate.return_value = False
        self.sample_ui_elements["apn_settings"].get_validation_error.return_value = "Invalid APN format"
        
        # Test the method
        result = self.profile_ui_populator.populate_ui_from_profile(
            self.sample_profile, 
            self.sample_ui_elements
        )
        
        # Verify results
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Validation failed for apn_settings", result.errors[0])

    def test_extract_validated_field_values_success(self):
        """Test successful extraction of validated field values."""
        # Test the method
        values, result = self.profile_ui_populator.extract_validated_field_values(
            self.sample_ui_elements
        )
        
        # Verify results
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 0)
        
        # Verify extracted values
        self.assertIn("apn_settings", values)
        self.assertIn("server_settings", values)
        self.assertIn("protocol", values)
        
        self.assertEqual(values["apn_settings"], 
                        {"apn": "test.apn", "user": "testuser", "password": "testpass"})
        self.assertEqual(values["server_settings"], 
                        {"address": "192.168.1.1", "port": 8080})
        self.assertEqual(values["protocol"], "GT06 (0x60)")

    def test_extract_validated_field_values_with_error(self):
        """Test extraction of validated field values with UI element error."""
        # Make one UI element fail
        self.sample_ui_elements["apn_settings"].get_value.side_effect = Exception("UI Error")
        
        # Test the method
        values, result = self.profile_ui_populator.extract_validated_field_values(
            self.sample_ui_elements
        )
        
        # Verify results
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Failed to extract value from apn_settings", result.errors[0])

    def test_apply_visibility_conditions(self):
        """Test applying visibility conditions to UI elements."""
        # Setup context values - match the condition format
        context = {
            "ignition_mode": "Virtual por bateria (Virtual by battery)"
        }
        
        # Setup mock parameter specifications
        mock_voltage_spec = Mock()
        mock_voltage_spec.visibility_condition = "ignition_mode == 'Virtual por bateria (Virtual by battery)'"
        
        self.mock_spec_parser.parse_specifications.return_value = {
            "on_voltage": mock_voltage_spec
        }
        
        # Add a voltage UI element
        voltage_element = Mock()
        voltage_element.set_visibility = Mock()
        ui_elements = {"on_voltage": voltage_element}
        
        # Test the method
        self.profile_ui_populator.apply_visibility_conditions(ui_elements, context)
        
        # Verify that set_visibility was called with True
        voltage_element.set_visibility.assert_called_once_with(True)

    def test_evaluate_visibility_condition_true(self):
        """Test evaluating a visibility condition that should be true."""
        condition = "field_name == 'value'"
        context = {"field_name": "value"}
        
        result = self.profile_ui_populator._evaluate_visibility_condition(condition, context)
        
        self.assertTrue(result)

    def test_evaluate_visibility_condition_false(self):
        """Test evaluating a visibility condition that should be false."""
        condition = "field_name == 'value'"
        context = {"field_name": "different_value"}
        
        result = self.profile_ui_populator._evaluate_visibility_condition(condition, context)
        
        self.assertFalse(result)

    def test_evaluate_visibility_condition_boolean_true(self):
        """Test evaluating a visibility condition with boolean true."""
        condition = "enabled == true"
        context = {"enabled": True}
        
        result = self.profile_ui_populator._evaluate_visibility_condition(condition, context)
        
        self.assertTrue(result)

    def test_evaluate_visibility_condition_boolean_false(self):
        """Test evaluating a visibility condition with boolean false."""
        condition = "enabled == false"
        context = {"enabled": True}
        
        result = self.profile_ui_populator._evaluate_visibility_condition(condition, context)
        
        self.assertFalse(result)

    def test_get_field_dependencies(self):
        """Test getting field dependencies for a parameter."""
        # Setup mock parameter specification
        mock_param_spec = Mock()
        mock_param_spec.visibility_condition = "dependent_field == 'value'"
        
        # Setup mock field specifications
        mock_field1 = Mock()
        mock_field1.visibility_condition = "another_field == 'value'"
        mock_field2 = Mock()
        mock_field2.visibility_condition = None
        
        mock_param_spec.fields = [mock_field1, mock_field2]
        
        self.mock_spec_parser.get_parameter_spec.return_value = mock_param_spec
        
        # Test the method
        dependencies = self.profile_ui_populator.get_field_dependencies("test_parameter")
        
        # Verify results
        self.assertIn("dependent_field", dependencies)
        self.assertIn("another_field", dependencies)

    def test_create_ui_element_configs_from_profile(self):
        """Test creating UI element configurations from profile data."""
        # Setup mock parameter specifications
        mock_apn_spec = Mock()
        mock_apn_spec.ui_element = Mock()
        mock_apn_spec.ui_element.value = "complex"
        mock_apn_spec.label = "Configuração APN"
        mock_apn_spec.options = None
        mock_apn_spec.unit = None
        
        mock_protocol_spec = Mock()
        mock_protocol_spec.ui_element = Mock()
        mock_protocol_spec.ui_element.value = "dropdown"
        mock_protocol_spec.label = "Tipo de protocolo"
        mock_protocol_spec.options = ["GT06 (0x60)", "CRX3 (0x22)", "CRX (0x12)"]
        mock_protocol_spec.unit = None
        
        self.mock_spec_parser.parse_specifications.return_value = {
            "apn_settings": mock_apn_spec,
            "protocol": mock_protocol_spec
        }
        
        # Test the method
        configs = self.profile_ui_populator.create_ui_element_configs_from_profile(
            self.sample_profile
        )
        
        # Verify results
        self.assertIn("apn_settings", configs)
        self.assertIn("protocol", configs)
        
        # Verify config properties
        apn_config = configs["apn_settings"]
        self.assertEqual(apn_config.element_type, "complex")
        self.assertEqual(apn_config.label, "Configuração APN")
        self.assertEqual(apn_config.default_value, {"apn": "test.apn", "user": "testuser", "password": "testpass"})

    def test_validate_profile_data_integrity(self):
        """Test validating profile data integrity."""
        # Setup mock validation results
        mock_validation_result = Mock()
        mock_validation_result.is_valid = True
        mock_validation_result.errors = []
        mock_validation_result.warnings = []
        
        self.mock_spec_parser.validate_parameter_value.return_value = mock_validation_result
        
        # Test the method
        result = self.profile_ui_populator.validate_profile_data_integrity(
            self.sample_profile
        )
        
        # Verify results
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 0)

    def test_map_profile_to_ui_structure(self):
        """Test mapping profile data to UI structure."""
        # Test the method
        ui_structure = self.profile_ui_populator.map_profile_to_ui_structure(
            self.sample_profile
        )
        
        # Verify results
        self.assertIn("apn_settings", ui_structure)
        self.assertIn("server_settings", ui_structure)
        self.assertIn("protocol", ui_structure)
        
        # Verify structure
        self.assertEqual(ui_structure["apn_settings"], 
                        {"apn": "test.apn", "user": "testuser", "password": "testpass"})
        self.assertEqual(ui_structure["server_settings"], 
                        {"address": "192.168.1.1", "port": 8080})
        self.assertEqual(ui_structure["protocol"], "GT06 (0x60)")

    def test_update_ui_elements_from_profile(self):
        """Test updating UI elements from profile data."""
        # Create mock section widgets
        mock_section_widgets = {}
        
        # Create mock network parameters section
        mock_network_section = Mock()
        mock_apn_widget = Mock()
        mock_apn_widget.widget_type = 'complex'
        mock_apn_widget.ui_elements = {
            'apn': Mock(),
            'user': Mock(),
            'password': Mock()
        }
        mock_network_section.parameters = {
            'apn_settings': mock_apn_widget
        }
        mock_section_widgets['network_parameters'] = mock_network_section
        
        # Create mock service parameters section
        mock_service_section = Mock()
        mock_protocol_widget = Mock()
        mock_protocol_widget.widget_type = 'simple'
        mock_protocol_widget.ui_elements = {'main': Mock()}
        mock_service_section.parameters = {
            'protocol': mock_protocol_widget
        }
        mock_section_widgets['service_parameters'] = mock_service_section
        
        # Setup profile with matching parameter names
        profile = self.sample_profile
        
        # Test the method
        result = self.profile_ui_populator.update_ui_elements_from_profile(
            profile, 
            mock_section_widgets
        )
        
        # Verify results
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)


if __name__ == '__main__':
    unittest.main()