"""
Test script for radio button group controls.

This script tests the radio button group controls (Lock Type, Ignition Type, Protocol)
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

class RadioButtonParameterTest(unittest.TestCase):
    """Test radio button group controls."""
    
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
    
    def test_lock_type_validation(self):
        """Test lock type parameter validation."""
        # Test valid values
        valid_values = ['PIN', 'Card']
        for value in valid_values:
            result = self.validation_service.validate_parameter("lock_type", value)
            self.assertTrue(result.is_valid, f"Value {value} should be valid for lock_type")
        
        # Test invalid values
        invalid_values = ['Password', 'Fingerprint', 'Face', 'invalid']
        for value in invalid_values:
            result = self.validation_service.validate_parameter("lock_type", value)
            self.assertFalse(result.is_valid, f"Value {value} should be invalid for lock_type")
    
    def test_ignition_type_validation(self):
        """Test ignition type parameter validation."""
        # Test valid values
        valid_values = ['Digital', 'Analog']
        for value in valid_values:
            result = self.validation_service.validate_parameter("ignition_type", value)
            self.assertTrue(result.is_valid, f"Value {value} should be valid for ignition_type")
        
        # Test invalid values
        invalid_values = ['Virtual', 'Physical', 'Auto', 'invalid']
        for value in invalid_values:
            result = self.validation_service.validate_parameter("ignition_type", value)
            self.assertFalse(result.is_valid, f"Value {value} should be invalid for ignition_type")
    
    def test_transmission_mode_validation(self):
        """Test transmission mode parameter validation."""
        # Test valid values
        valid_values = ['TCP', 'UDP']
        for value in valid_values:
            result = self.validation_service.validate_parameter("transmission_mode", value)
            self.assertTrue(result.is_valid, f"Value {value} should be valid for transmission_mode")
        
        # Test invalid values
        invalid_values = ['HTTP', 'HTTPS', 'FTP', 'invalid']
        for value in invalid_values:
            result = self.validation_service.validate_parameter("transmission_mode", value)
            self.assertFalse(result.is_valid, f"Value {value} should be invalid for transmission_mode")
    
    def test_timezone_direction_validation(self):
        """Test timezone direction parameter validation."""
        # Test valid values
        valid_values = ['E', 'W']
        for value in valid_values:
            result = self.validation_service.validate_parameter("timezone_direction", value)
            self.assertTrue(result.is_valid, f"Value {value} should be valid for timezone_direction")
        
        # Test invalid values
        invalid_values = ['N', 'S', 'East', 'West', 'invalid']
        for value in invalid_values:
            result = self.validation_service.validate_parameter("timezone_direction", value)
            self.assertFalse(result.is_valid, f"Value {value} should be invalid for timezone_direction")
    
    def test_command_generation_for_radio_parameters(self):
        """Test command generation for radio button parameters."""
        # Test lock type command
        command = self.device_command_mapper.get_command("lock_type", "PIN")
        self.assertEqual(command, "ATSMS:SZCS#LOCKTYPE=0#")
        
        command = self.device_command_mapper.get_command("lock_type", "Card")
        self.assertEqual(command, "ATSMS:SZCS#LOCKTYPE=1#")
        
        # Test ignition type command
        command = self.device_command_mapper.get_command("ignition_type", "Digital")
        self.assertEqual(command, "ATSMS:SZCS#ACCLINE=0#ACC_CFG=0-000-000")
        
        command = self.device_command_mapper.get_command("ignition_type", "Analog")
        self.assertEqual(command, "ATSMS:SZCS#ACCLINE=1#ACC_CFG=0-000-000")
        
        # Test transmission mode command
        command = self.device_command_mapper.get_command("transmission_mode", "TCP")
        self.assertEqual(command, "ATSMS:SZCS#PROTOCOL=0#")
        
        command = self.device_command_mapper.get_command("transmission_mode", "UDP")
        self.assertEqual(command, "ATSMS:SZCS#PROTOCOL=1#")
    
    def test_value_mapping_for_radio_parameters(self):
        """Test value mapping for radio button parameters."""
        # Test lock type mapping
        self.assertEqual(self.device_command_mapper._map_value("lock_type", "PIN"), "0")
        self.assertEqual(self.device_command_mapper._map_value("lock_type", "Card"), "1")
        
        # Test ignition type mapping
        self.assertEqual(self.device_command_mapper._map_value("ignition_type", "Digital"), "0")
        self.assertEqual(self.device_command_mapper._map_value("ignition_type", "Analog"), "1")
        
        # Test transmission mode mapping
        self.assertEqual(self.device_command_mapper._map_value("transmission_mode", "TCP"), "0")
        self.assertEqual(self.device_command_mapper._map_value("transmission_mode", "UDP"), "1")
    
    def test_radio_button_group_creation(self):
        """Test radio button group creation and interaction."""
        # Create a StringVar for the radio group
        radio_var = tk.StringVar(value="PIN")
        
        # Create radio buttons
        pin_radio = ctk.CTkRadioButton(
            self.test_frame,
            text="PIN",
            variable=radio_var,
            value="PIN"
        )
        pin_radio.grid(row=0, column=0, padx=10, pady=5)
        
        card_radio = ctk.CTkRadioButton(
            self.test_frame,
            text="Card",
            variable=radio_var,
            value="Card"
        )
        card_radio.grid(row=0, column=1, padx=10, pady=5)
        
        # Test initial value
        self.assertEqual(radio_var.get(), "PIN")
        
        # Test changing value
        radio_var.set("Card")
        self.assertEqual(radio_var.get(), "Card")
        
        # Test validation of the selected value
        result = self.validation_service.validate_parameter("lock_type", radio_var.get())
        self.assertTrue(result.is_valid)
        
        # Test command generation with the selected value
        command = self.device_command_mapper.get_command("lock_type", radio_var.get())
        self.assertEqual(command, "ATSMS:SZCS#LOCKTYPE=1#")

if __name__ == '__main__':
    unittest.main()