import unittest
from services.validation_service import ValidationService
from services.i18n_service import I18nService
from services.device_command_mapper import DeviceCommandMapper

class TestParameterSequence(unittest.TestCase):
    """Test the parameter sequence implementation."""
    
    def setUp(self):
        """Set up the test environment."""
        self.i18n = I18nService()
        self.validation_service = ValidationService(self.i18n)
        self.device_command_mapper = DeviceCommandMapper()
    
    def test_protocol_options(self):
        """Test that the protocol options are correctly defined."""
        # Check validation rules for protocol options
        gt06_protocol_rules = self.validation_service.get_parameter_info('gt06_protocol')
        self.assertIsNotNone(gt06_protocol_rules, "Protocol validation rules not found")
        
        # Check that the allowed values include the required options
        allowed_values = gt06_protocol_rules.get('allowed_values', [])
        self.assertIn('GT06-0x60', allowed_values, "GT06-0x60 protocol option not found")
        self.assertIn('GT06-0x12', allowed_values, "GT06-0x12 protocol option not found")
        self.assertIn('CRX3', allowed_values, "CRX3 protocol option not found")
        
        # Check that the command mapper has the correct mappings
        protocol_mappings = self.device_command_mapper.value_mappings.get('gt06_protocol', {})
        self.assertIn('GT06-0x60', protocol_mappings, "GT06-0x60 protocol mapping not found")
        self.assertIn('GT06-0x12', protocol_mappings, "GT06-0x12 protocol mapping not found")
        self.assertIn('CRX3', protocol_mappings, "CRX3 protocol mapping not found")
        
        print("Protocol options test passed!")
        print(f"Protocol allowed values: {allowed_values}")
        print(f"Protocol mappings: {protocol_mappings}")

if __name__ == "__main__":
    unittest.main()