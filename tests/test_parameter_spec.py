"""
Unit tests for parameter specification data models.
"""

import unittest
from models.parameter_spec import (
    UIElementType,
    ParameterField,
    ParameterCommands,
    ParameterSpec
)
from models.validation_result import ValidationResult


class TestUIElementType(unittest.TestCase):
    """Test cases for UIElementType enum."""
    
    def test_enum_values(self):
        """Test that all expected enum values exist."""
        self.assertEqual(UIElementType.TEXT_INPUT.value, "text_input")
        self.assertEqual(UIElementType.NUMBER_INPUT.value, "number_input")
        self.assertEqual(UIElementType.DROPDOWN.value, "dropdown")
        self.assertEqual(UIElementType.TOGGLE_SWITCH.value, "toggle_switch")
        self.assertEqual(UIElementType.SLIDER.value, "slider")


class TestParameterField(unittest.TestCase):
    """Test cases for ParameterField class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.text_field = ParameterField(
            name="apn",
            label="APN",
            ui_element=UIElementType.TEXT_INPUT,
            validation="Accepts a standard APN name"
        )
        
        self.number_field = ParameterField(
            name="port",
            label="Port",
            ui_element=UIElementType.NUMBER_INPUT,
            validation="1-65535",
            unit="port"
        )
        
        self.dropdown_field = ParameterField(
            name="protocol",
            label="Protocol",
            ui_element=UIElementType.DROPDOWN,
            options=["GT06 (0x60)", "CRX3 (0x22)", "CRX (0x12)"]
        )
        
        self.conditional_field = ParameterField(
            name="on_voltage",
            label="ON Voltage",
            ui_element=UIElementType.NUMBER_INPUT,
            visibility_condition="ignition_mode == 'Virtual por bateria (Virtual by battery)'"
        )
    
    def test_field_creation(self):
        """Test basic field creation."""
        self.assertEqual(self.text_field.name, "apn")
        self.assertEqual(self.text_field.label, "APN")
        self.assertEqual(self.text_field.ui_element, UIElementType.TEXT_INPUT)
    
    def test_validate_value_number_range(self):
        """Test validation for number fields with range."""
        # Valid values
        self.assertTrue(self.number_field.validate_value(80))
        self.assertTrue(self.number_field.validate_value(1))
        self.assertTrue(self.number_field.validate_value(65535))
        
        # Invalid values
        self.assertFalse(self.number_field.validate_value(0))
        self.assertFalse(self.number_field.validate_value(65536))
        self.assertFalse(self.number_field.validate_value("invalid"))
    
    def test_validate_value_dropdown(self):
        """Test validation for dropdown fields."""
        # Valid values
        self.assertTrue(self.dropdown_field.validate_value("GT06 (0x60)"))
        self.assertTrue(self.dropdown_field.validate_value("CRX3 (0x22)"))
        
        # Invalid values
        self.assertFalse(self.dropdown_field.validate_value("Invalid Protocol"))
        self.assertFalse(self.dropdown_field.validate_value(""))
    
    def test_validate_value_no_validation(self):
        """Test validation when no validation rules are specified."""
        self.assertTrue(self.text_field.validate_value("any value"))
        self.assertTrue(self.text_field.validate_value(""))
        self.assertTrue(self.text_field.validate_value(123))
    
    def test_get_default_value(self):
        """Test getting default values for different field types."""
        toggle_field = ParameterField("test", "Test", UIElementType.TOGGLE_SWITCH)
        self.assertFalse(toggle_field.get_default_value())
        
        number_field = ParameterField("test", "Test", UIElementType.NUMBER_INPUT)
        self.assertEqual(number_field.get_default_value(), 0)
        
        self.assertEqual(self.dropdown_field.get_default_value(), "GT06 (0x60)")
        
        text_field = ParameterField("test", "Test", UIElementType.TEXT_INPUT)
        self.assertEqual(text_field.get_default_value(), "")
    
    def test_is_visible_no_condition(self):
        """Test visibility when no condition is specified."""
        self.assertTrue(self.text_field.is_visible({}))
        self.assertTrue(self.text_field.is_visible({"any": "context"}))
    
    def test_is_visible_with_condition(self):
        """Test visibility with conditions."""
        context_true = {"ignition_mode": "Virtual por bateria (Virtual by battery)"}
        context_false = {"ignition_mode": "Física (Physical)"}
        
        self.assertTrue(self.conditional_field.is_visible(context_true))
        self.assertFalse(self.conditional_field.is_visible(context_false))
    
    def test_is_visible_boolean_condition(self):
        """Test visibility with boolean conditions."""
        bool_field = ParameterField(
            "test", "Test", UIElementType.TEXT_INPUT,
            visibility_condition="enabled == true"
        )
        
        self.assertTrue(bool_field.is_visible({"enabled": True}))
        self.assertFalse(bool_field.is_visible({"enabled": False}))
    
    def test_is_visible_invalid_condition(self):
        """Test visibility with invalid conditions defaults to visible."""
        invalid_field = ParameterField(
            "test", "Test", UIElementType.TEXT_INPUT,
            visibility_condition="invalid condition format"
        )
        
        self.assertTrue(invalid_field.is_visible({}))


class TestParameterCommands(unittest.TestCase):
    """Test cases for ParameterCommands class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.simple_commands = ParameterCommands(
            set_command="APN,<apn>,<user>,<password>#",
            read_command="APN#"
        )
        
        self.complex_commands = ParameterCommands(
            set_physical="SZCS#ACCLINE=1#ACC_CFG=0-000-000",
            set_accelerometer="SZCS#ACCLINE=0#ACC_CFG=0-000-000",
            set_battery="SZCS#ACCLINE=1#ACC_CFG=1-<on_voltage>-<off_voltage>"
        )
    
    def test_format_set_command(self):
        """Test formatting set commands with values."""
        values = {
            "apn": "internet.com",
            "user": "testuser",
            "password": "testpass"
        }
        
        expected = "APN,internet.com,testuser,testpass#"
        result = self.simple_commands.format_set_command(values)
        self.assertEqual(result, expected)
    
    def test_format_set_command_partial_values(self):
        """Test formatting with partial values."""
        values = {"apn": "internet.com"}
        
        result = self.simple_commands.format_set_command(values)
        # Should replace available placeholders
        self.assertIn("internet.com", result)
        # Should leave unreplaced placeholders
        self.assertIn("<user>", result)
        self.assertIn("<password>", result)
    
    def test_format_set_command_no_command(self):
        """Test formatting when no set command is available."""
        empty_commands = ParameterCommands()
        result = empty_commands.format_set_command({"any": "value"})
        self.assertIsNone(result)
    
    def test_parse_read_response(self):
        """Test parsing device responses."""
        response = "internet.com,user,pass"
        result = self.simple_commands.parse_read_response(response)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["value_0"], "internet.com")
        self.assertEqual(result["value_1"], "user")
        self.assertEqual(result["value_2"], "pass")
    
    def test_parse_read_response_with_hash(self):
        """Test parsing responses that end with #."""
        response = "internet.com,user,pass#"
        result = self.simple_commands.parse_read_response(response)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["value_0"], "internet.com")
    
    def test_parse_read_response_empty(self):
        """Test parsing empty responses."""
        result = self.simple_commands.parse_read_response("")
        self.assertIsNone(result)
        
        result = self.simple_commands.parse_read_response(None)
        self.assertIsNone(result)


class TestParameterSpec(unittest.TestCase):
    """Test cases for ParameterSpec class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.simple_spec = ParameterSpec(
            name="protocol",
            label="Protocol Type",
            section="Service Parameters",
            ui_element=UIElementType.DROPDOWN,
            options=["GT06 (0x60)", "CRX3 (0x22)", "CRX (0x12)"],
            commands=ParameterCommands(
                set_command="SZCS#GT06SEL=<value>",
                read_command="CXCS#GT06SEL"
            )
        )
        
        self.complex_spec = ParameterSpec(
            name="apn_settings",
            label="APN Configuration",
            section="Network Parameters",
            description="Configures the APN, username, and password",
            fields=[
                ParameterField("apn", "APN", UIElementType.TEXT_INPUT),
                ParameterField("user", "User", UIElementType.TEXT_INPUT),
                ParameterField("password", "Password", UIElementType.TEXT_INPUT)
            ],
            commands=ParameterCommands(
                set_command="APN,<apn>,<user>,<password>#",
                read_command="APN#"
            )
        )
        
        self.number_spec = ParameterSpec(
            name="port",
            label="Port",
            section="Network",
            ui_element=UIElementType.NUMBER_INPUT,
            validation="1-65535"
        )
    
    def test_spec_creation(self):
        """Test basic spec creation."""
        self.assertEqual(self.simple_spec.name, "protocol")
        self.assertEqual(self.simple_spec.label, "Protocol Type")
        self.assertEqual(self.simple_spec.section, "Service Parameters")
        self.assertEqual(self.simple_spec.ui_element, UIElementType.DROPDOWN)
    
    def test_post_init_string_ui_element(self):
        """Test conversion of string ui_element to enum."""
        spec = ParameterSpec(
            name="test",
            label="Test",
            section="Test",
            ui_element="dropdown"
        )
        self.assertEqual(spec.ui_element, UIElementType.DROPDOWN)
    
    def test_post_init_invalid_ui_element(self):
        """Test handling of invalid ui_element strings."""
        spec = ParameterSpec(
            name="test",
            label="Test",
            section="Test",
            ui_element="invalid_element"
        )
        self.assertIsNone(spec.ui_element)
    
    def test_validate_value_simple_parameter(self):
        """Test validation for simple parameters."""
        # Valid value
        result = self.simple_spec.validate_value("GT06 (0x60)")
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        
        # Invalid value
        result = self.simple_spec.validate_value("Invalid Protocol")
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_validate_value_complex_parameter(self):
        """Test validation for complex parameters with fields."""
        # Valid value
        valid_value = {
            "apn": "internet.com",
            "user": "testuser",
            "password": "testpass"
        }
        result = self.complex_spec.validate_value(valid_value)
        self.assertTrue(result.is_valid)
        
        # Invalid value (not a dictionary)
        result = self.complex_spec.validate_value("not a dict")
        self.assertFalse(result.is_valid)
        self.assertIn("expects a dictionary", result.errors[0])
    
    def test_validate_value_number_range(self):
        """Test validation for number parameters with ranges."""
        # Valid values
        result = self.number_spec.validate_value(80)
        self.assertTrue(result.is_valid)
        
        result = self.number_spec.validate_value(1)
        self.assertTrue(result.is_valid)
        
        result = self.number_spec.validate_value(65535)
        self.assertTrue(result.is_valid)
        
        # Invalid values
        result = self.number_spec.validate_value(0)
        self.assertFalse(result.is_valid)
        
        result = self.number_spec.validate_value(65536)
        self.assertFalse(result.is_valid)
        
        result = self.number_spec.validate_value("invalid")
        self.assertFalse(result.is_valid)
    
    def test_get_default_value_simple(self):
        """Test getting default values for simple parameters."""
        self.assertEqual(self.simple_spec.get_default_value(), "GT06 (0x60)")
        
        toggle_spec = ParameterSpec("test", "Test", "Test", ui_element=UIElementType.TOGGLE_SWITCH)
        self.assertFalse(toggle_spec.get_default_value())
    
    def test_get_default_value_complex(self):
        """Test getting default values for complex parameters."""
        defaults = self.complex_spec.get_default_value()
        self.assertIsInstance(defaults, dict)
        self.assertIn("apn", defaults)
        self.assertIn("user", defaults)
        self.assertIn("password", defaults)
        self.assertEqual(defaults["apn"], "")
    
    def test_is_visible_no_condition(self):
        """Test visibility when no condition is specified."""
        self.assertTrue(self.simple_spec.is_visible({}))
    
    def test_is_visible_with_condition(self):
        """Test visibility with conditions."""
        conditional_spec = ParameterSpec(
            name="test",
            label="Test",
            section="Test",
            visibility_condition="enabled == true"
        )
        
        self.assertTrue(conditional_spec.is_visible({"enabled": True}))
        self.assertFalse(conditional_spec.is_visible({"enabled": False}))
    
    def test_get_visible_fields(self):
        """Test getting visible fields based on context."""
        # All fields visible by default
        visible = self.complex_spec.get_visible_fields({})
        self.assertEqual(len(visible), 3)
        
        # Test with conditional field
        conditional_field = ParameterField(
            "conditional", "Conditional", UIElementType.TEXT_INPUT,
            visibility_condition="show_advanced == true"
        )
        
        spec_with_conditional = ParameterSpec(
            name="test",
            label="Test",
            section="Test",
            fields=[
                ParameterField("always_visible", "Always", UIElementType.TEXT_INPUT),
                conditional_field
            ]
        )
        
        # Without condition met
        visible = spec_with_conditional.get_visible_fields({})
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0].name, "always_visible")
        
        # With condition met
        visible = spec_with_conditional.get_visible_fields({"show_advanced": True})
        self.assertEqual(len(visible), 2)
    
    def test_get_visible_fields_no_fields(self):
        """Test getting visible fields when no fields are defined."""
        visible = self.simple_spec.get_visible_fields({})
        self.assertEqual(len(visible), 0)


if __name__ == '__main__':
    unittest.main()