"""
Test script for dropdown parameter controls.

This script tests the dropdown parameter controls (Heart Beat, Curve Sensor)
including validation, UI interaction, and command generation.
"""

import unittest
import tkinter as tk
import customtkinter as ctk
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.i18n_service import I18nService
from services.validation_service import ValidationService
from services.device_command_mapper import DeviceCommandMapper

class DropdownParameterTest(unittest.TestCase):
    """Test dropdown parameter controls."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        # Create a mock root window
        cls.root = ctk.CTk()
        cls.root.withdraw()  # Hide the window
        
        # Initialize services
        cls.i18n = I18nService()
        cls.validation_service = ValidationService(cls.i18n)
        cls.device_command_mapper = DeviceCommandMapper()
        
        # Create a mock app with required attributes
        cls.app = MagicMock()
        cls.app.root = cls.root
        cls.app.i18n = cls.i18n
        cls.app.validation_service = cls.validation_service
        cls.app.device_command_mapper = cls.device_command_mapper
        
        # Create log frame mock
        cls.app.log_frame = MagicMock()
        cls.app.log_frame.log_message = MagicMock()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        cls.root.destroy()
    
    def setUp(self):
        """Set up before each test."""
        # Create a frame for testing
        self.test_frame = ctk.CTkFrame(self.root)
        
        # Reset mocks
        self.app.log_frame.log_message.reset_mock()
    
    def tearDown(self):
        """Clean up after each test."""
        self.test_frame.destroy()
    
    def test_heartbeat_interval_validation(self):
        """Test heartbeat interval parameter validation."""
        # Test valid values
        valid_values = ['30s', '1min', '5min', '10min', '30min', '1hr', '2hr', '6hr', '12hr', '24hr']
        for value in valid_values:
            result = self.validation_service.validate_parameter("heartbeat_interval", value)
            self.assertTrue(result.is_valid, f"Value {value} should be valid for heartbeat_interval")
        
        # Test invalid values
        invalid_values = ['0s', '2min', '3hr', 'invalid']
        for value in invalid_values:
            result = self.validation_service.validate_parameter("heartbeat_interval", value)
            self.assertFalse(result.is_valid, f"Value {value} should be invalid for heartbeat_interval")
    
    def test_curve_sensor_validation(self):
        """Test curve sensor parameter validation."""
        # Test valid values
        valid_values = ['Enabled', 'Disabled', 'Auto']
        for value in valid_values:
            result = self.validation_service.validate_parameter("curve_sensor", value)
            self.assertTrue(result.is_valid, f"Value {value} should be valid for curve_sensor")
        
        # Test invalid values
        invalid_values = ['On', 'Off', 'Yes', 'No', 'invalid']
        for value in invalid_values:
            result = self.validation_service.validate_parameter("curve_sensor", value)
            self.assertFalse(result.is_valid, f"Value {value} should be invalid for curve_sensor")
    
    def test_protocol_type_validation(self):
        """Test protocol type parameter validation."""
        # Test valid values
        valid_values = ['TCP', 'UDP']
        for value in valid_values:
            result = self.validation_service.validate_parameter("protocol_type", value)
            self.assertTrue(result.is_valid, f"Value {value} should be valid for protocol_type")
        
        # Test invalid values
        invalid_values = ['HTTP', 'HTTPS', 'FTP', 'invalid']
        for value in invalid_values:
            result = self.validation_service.validate_parameter("protocol_type", value)
            self.assertFalse(result.is_valid, f"Value {value} should be invalid for protocol_type")
    
    def test_network_type_validation(self):
        """Test network type parameter validation."""
        # Test valid values
        valid_values = ['AUTO', '4G', '2G']
        for value in valid_values:
            result = self.validation_service.validate_parameter("network_type", value)
            self.assertTrue(result.is_valid, f"Value {value} should be valid for network_type")
        
        # Test invalid values
        invalid_values = ['3G', '5G', 'LTE', 'invalid']
        for value in invalid_values:
            result = self.validation_service.validate_parameter("network_type", value)
            self.assertFalse(result.is_valid, f"Value {value} should be invalid for network_type")
    
    def test_command_generation_for_dropdown_parameters(self):
        """Test command generation for dropdown parameters."""
        # Test heartbeat interval command
        command = self.device_command_mapper.get_command("heartbeat_interval", "1min")
        self.assertEqual(command, "ATSMS:HBT,60#")
        
        # Test curve sensor command
        command = self.device_command_mapper.get_command("curve_sensor", "Enabled")
        self.assertEqual(command, "ATSMS:SZCS#CURVE=1#")
        
        command = self.device_command_mapper.get_command("curve_sensor", "Disabled")
        self.assertEqual(command, "ATSMS:SZCS#CURVE=0#")
        
        command = self.device_command_mapper.get_command("curve_sensor", "Auto")
        self.assertEqual(command, "ATSMS:SZCS#CURVE=2#")
        
        # Test protocol type command
        command = self.device_command_mapper.get_command("protocol_type", "TCP")
        self.assertEqual(command, "ATSMS:SZCS#GT06SEL=0#")
        
        command = self.device_command_mapper.get_command("protocol_type", "UDP")
        self.assertEqual(command, "ATSMS:SZCS#GT06SEL=1#")
        
        # Test network type command
        command = self.device_command_mapper.get_command("network_type", "AUTO")
        self.assertEqual(command, "ATSMS:SZCS#NETSELECT=0#")
        
        command = self.device_command_mapper.get_command("network_type", "4G")
        self.assertEqual(command, "ATSMS:SZCS#NETSELECT=1#")
        
        command = self.device_command_mapper.get_command("network_type", "2G")
        self.assertEqual(command, "ATSMS:SZCS#NETSELECT=2#")
    
    def test_value_mapping_for_dropdown_parameters(self):
        """Test value mapping for dropdown parameters."""
        # Test heartbeat interval mapping
        self.assertEqual(self.device_command_mapper._map_value("heartbeat_interval", "30s"), "30")
        self.assertEqual(self.device_command_mapper._map_value("heartbeat_interval", "1min"), "60")
        self.assertEqual(self.device_command_mapper._map_value("heartbeat_interval", "5min"), "300")
        self.assertEqual(self.device_command_mapper._map_value("heartbeat_interval", "1hr"), "3600")
        self.assertEqual(self.device_command_mapper._map_value("heartbeat_interval", "24hr"), "86400")
        
        # Test curve sensor mapping
        self.assertEqual(self.device_command_mapper._map_value("curve_sensor", "Disabled"), "0")
        self.assertEqual(self.device_command_mapper._map_value("curve_sensor", "Enabled"), "1")
        self.assertEqual(self.device_command_mapper._map_value("curve_sensor", "Auto"), "2")
        
        # Test protocol type mapping
        self.assertEqual(self.device_command_mapper._map_value("transmission_mode", "TCP"), "0")
        self.assertEqual(self.device_command_mapper._map_value("transmission_mode", "UDP"), "1")
        
        # Test network type mapping
        self.assertEqual(self.device_command_mapper._map_value("network_select", "AUTO"), "0")
        self.assertEqual(self.device_command_mapper._map_value("network_select", "4G"), "1")
        self.assertEqual(self.device_command_mapper._map_value("network_select", "2G"), "2")

if __name__ == '__main__':
    unittest.main()