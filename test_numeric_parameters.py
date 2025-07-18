"""
Test script for numeric parameter controls and validation.

This script tests the numeric parameter controls (Vibration, Timers, Sensitivity)
including range validation, UI interaction, and command generation.
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

class NumericParameterTest(unittest.TestCase):
    """Test numeric parameter controls and validation."""
    
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
    
    def test_vibration_parameter_validation(self):
        """Test vibration parameter validation."""
        # Test valid values
        for value in ["0", "1", "100", "255"]:
            result = self.validation_service.validate_parameter("vibration", value)
            self.assertTrue(result.is_valid, f"Value {value} should be valid for vibration")
        
        # Test invalid values
        for value in ["-1", "256", "abc", "1.5"]:
            result = self.validation_service.validate_parameter("vibration", value)
            self.assertFalse(result.is_valid, f"Value {value} should be invalid for vibration")
    
    def test_timer_parameter_validation(self):
        """Test timer parameter validation."""
        # Test valid values for timer_ign_on
        for value in ["1", "30", "1000", "65500"]:
            result = self.validation_service.validate_parameter("timer_ign_on", value)
            self.assertTrue(result.is_valid, f"Value {value} should be valid for timer_ign_on")
        
        # Test invalid values for timer_ign_on
        for value in ["0", "65501", "abc", "-10"]:
            result = self.validation_service.validate_parameter("timer_ign_on", value)
            self.assertFalse(result.is_valid, f"Value {value} should be invalid for timer_ign_on")
        
        # Test valid values for timer_ign_off
        for value in ["1", "300", "1000", "65500"]:
            result = self.validation_service.validate_parameter("timer_ign_off", value)
            self.assertTrue(result.is_valid, f"Value {value} should be valid for timer_ign_off")
        
        # Test invalid values for timer_ign_off
        for value in ["0", "65501", "abc", "-10"]:
            result = self.validation_service.validate_parameter("timer_ign_off", value)
            self.assertFalse(result.is_valid, f"Value {value} should be invalid for timer_ign_off")
    
    def test_sensitivity_parameter_validation(self):
        """Test sensitivity parameter validation."""
        # Test valid values
        for value in ["1", "5", "10"]:
            result = self.validation_service.validate_parameter("sensitivity", value)
            self.assertTrue(result.is_valid, f"Value {value} should be valid for sensitivity")
        
        # Test invalid values
        for value in ["0", "11", "abc", "5.5", "-1"]:
            result = self.validation_service.validate_parameter("sensitivity", value)
            self.assertFalse(result.is_valid, f"Value {value} should be invalid for sensitivity")
    
    def test_command_generation_for_numeric_parameters(self):
        """Test command generation for numeric parameters."""
        # Test vibration command
        command = self.device_command_mapper.get_command("vibration", "3")
        self.assertEqual(command, "ATSMS:SZCS#VIBL=3#")
        
        # Test timer commands
        command = self.device_command_mapper.get_command(
            "timer_ign_on", 
            "30", 
            {"timer_ign_off": "300"}
        )
        self.assertEqual(command, "ATSMS:TIMER,30,300#")
        
        command = self.device_command_mapper.get_command(
            "timer_ign_off", 
            "300", 
            {"timer_ign_on": "30"}
        )
        self.assertEqual(command, "ATSMS:TIMER,30,300#")
        
        # Test sensitivity command
        command = self.device_command_mapper.get_command("sensitivity", "5")
        self.assertEqual(command, "ATSMS:SZCS#SENSITIVITY=5#")
    
    def test_numeric_parameter_edge_cases(self):
        """Test numeric parameter edge cases."""
        # Test minimum values
        result = self.validation_service.validate_parameter("vibration", "0")
        self.assertTrue(result.is_valid)
        
        result = self.validation_service.validate_parameter("sensitivity", "1")
        self.assertTrue(result.is_valid)
        
        result = self.validation_service.validate_parameter("timer_ign_on", "1")
        self.assertTrue(result.is_valid)
        
        # Test maximum values
        result = self.validation_service.validate_parameter("vibration", "255")
        self.assertTrue(result.is_valid)
        
        result = self.validation_service.validate_parameter("sensitivity", "10")
        self.assertTrue(result.is_valid)
        
        result = self.validation_service.validate_parameter("timer_ign_on", "65500")
        self.assertTrue(result.is_valid)
        
        # Test just beyond limits
        result = self.validation_service.validate_parameter("vibration", "256")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, "MAX_VALUE")
        
        result = self.validation_service.validate_parameter("sensitivity", "11")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, "MAX_VALUE")
        
        result = self.validation_service.validate_parameter("timer_ign_on", "65501")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, "MAX_VALUE")
        
        result = self.validation_service.validate_parameter("vibration", "-1")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, "MIN_VALUE")
        
        result = self.validation_service.validate_parameter("sensitivity", "0")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, "MIN_VALUE")
    
    def test_numeric_parameter_type_validation(self):
        """Test numeric parameter type validation."""
        # Test non-integer values
        result = self.validation_service.validate_parameter("vibration", "3.5")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, "INTEGER_REQUIRED")
        
        result = self.validation_service.validate_parameter("sensitivity", "5.5")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, "INTEGER_REQUIRED")
        
        # Test non-numeric values
        result = self.validation_service.validate_parameter("vibration", "abc")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, "NUMERIC_REQUIRED")
        
        result = self.validation_service.validate_parameter("sensitivity", "five")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, "NUMERIC_REQUIRED")
        
        # Test empty values
        result = self.validation_service.validate_parameter("vibration", "")
        self.assertTrue(result.is_valid)  # Not required
        
        # Test None values
        result = self.validation_service.validate_parameter("vibration", None)
        self.assertTrue(result.is_valid)  # Not required

if __name__ == '__main__':
    unittest.main()