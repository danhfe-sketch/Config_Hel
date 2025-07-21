import unittest
import tkinter as tk
import customtkinter as ctk
import os
import sys
import json
from unittest.mock import MagicMock, patch

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
from services.i18n_service import I18nService
from services.validation_service import ValidationService
from services.device_command_mapper import DeviceCommandMapper

class TestIntegrationRadioButtons(unittest.TestCase):
    """Integration test for radio button parameters and protocol options."""
    
    def setUp(self):
        """Set up the test environment."""
        self.i18n = I18nService()
        self.validation_service = ValidationService(self.i18n)
        self.device_command_mapper = DeviceCommandMapper()
    
    def test_protocol_integration(self):
        """Test that protocol options are correctly integrated."""
        # Check validation rules
        gt06_protocol_rules = self.validation_service.get_parameter_info('gt06_protocol')
        self.assertIsNotNone(gt06_protocol_rules, "Protocol validation rules not found")
        
        # Check allowed values
        allowed_values = gt06_protocol_rules.get('allowed_values', [])
        expected_values = ['GT06-0x60', 'GT06-0x12', 'CRX3']
        for value in expected_values:
            self.assertIn(value, allowed_values, f"{value} protocol option not found")
        
        # Check command mapper
        protocol_mappings = self.device_command_mapper.value_mappings.get('gt06_protocol', {})
        for value in expected_values:
            self.assertIn(value, protocol_mappings, f"{value} protocol mapping not found")
        
        # Test command generation
        for protocol in expected_values:
            command = self.device_command_mapper.get_command('gt06_protocol', protocol)
            self.assertIsNotNone(command, f"Command generation failed for {protocol}")
            self.assertTrue(command.startswith("ATSMS:"), f"Command prefix missing for {protocol}")
            self.assertIn(protocol_mappings[protocol], command, f"Protocol value not in command for {protocol}")
        
        print("Protocol integration test passed!")
        print(f"Protocol allowed values: {allowed_values}")
        print(f"Protocol mappings: {protocol_mappings}")
        print(f"Sample command: {self.device_command_mapper.get_command('gt06_protocol', 'GT06-0x60')}")

if __name__ == "__main__":
    unittest.main()