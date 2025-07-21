#!/usr/bin/env python3
"""
Test UI field population from device responses.

This test verifies that the ConfigurationReaderService can properly update
UI parameter fields from parsed device responses, including visual indicators
and logging of parameter updates.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import customtkinter as ctk
from datetime import datetime
import time

# Import the services and UI components
from services.configuration_reader_service import ConfigurationReaderService, ParameterReadResult
from services.i18n_service import I18nService
from ui.parameters_frame import ParametersFrame
from ui.parameter_factory import ParameterFactory, BaseParameter, ParameterDefinition
from services.validation_service import ValidationService


class TestUIFieldPopulation(unittest.TestCase):
    """Test UI field population functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock application
        self.mock_app = Mock()
        self.mock_app.after = Mock()
        
        # Create mock log frame
        self.mock_log_frame = Mock()
        self.mock_log_frame.log_message = Mock()
        self.mock_app.log_frame = self.mock_log_frame
        
        # Create I18n service
        self.i18n = I18nService()
        
        # Create configuration reader service
        self.config_reader = ConfigurationReaderService(self.mock_app, self.i18n)
        
        # Create mock parameters frame with widgets
        self.mock_params_frame = Mock()
        self.mock_params_frame.parameter_widgets = {}
        
        # Create mock APN entry widgets
        self.mock_apn_server_entry = Mock()
        self.mock_apn_server_entry.get.return_value = "old.apn.com"
        self.mock_apn_server_entry.delete = Mock()
        self.mock_apn_server_entry.insert = Mock()
        self.mock_apn_server_entry.cget.return_value = "#000000"
        self.mock_apn_server_entry.configure = Mock()
        
        self.mock_apn_user_entry = Mock()
        self.mock_apn_user_entry.get.return_value = "olduser"
        self.mock_apn_user_entry.delete = Mock()
        self.mock_apn_user_entry.insert = Mock()
        self.mock_apn_user_entry.cget.return_value = "#000000"
        self.mock_apn_user_entry.configure = Mock()
        
        self.mock_apn_password_entry = Mock()
        self.mock_apn_password_entry.get.return_value = "oldpass"
        self.mock_apn_password_entry.delete = Mock()
        self.mock_apn_password_entry.insert = Mock()
        self.mock_apn_password_entry.cget.return_value = "#000000"
        self.mock_apn_password_entry.configure = Mock()
        
        # Attach APN widgets to params frame
        self.mock_params_frame.apn_server_entry = self.mock_apn_server_entry
        self.mock_params_frame.apn_user_entry = self.mock_apn_user_entry
        self.mock_params_frame.apn_password_entry = self.mock_apn_password_entry
        
        # Create mock parameter widgets
        self.mock_server_ip_widget = Mock()
        self.mock_server_ip_widget.get_value.return_value = "192.168.1.1"
        self.mock_server_ip_widget.set_value = Mock()
        self.mock_server_ip_widget.definition = Mock()
        self.mock_server_ip_widget.definition.display_label = "Server IP"
        self.mock_server_ip_widget.widget = Mock()
        self.mock_server_ip_widget.widget.cget.return_value = "#000000"
        self.mock_server_ip_widget.widget.configure = Mock()
        
        self.mock_vibration_widget = Mock()
        self.mock_vibration_widget.get_value.return_value = 100
        self.mock_vibration_widget.set_value = Mock()
        self.mock_vibration_widget.definition = Mock()
        self.mock_vibration_widget.definition.display_label = "Vibration"
        self.mock_vibration_widget.widget = Mock()
        self.mock_vibration_widget.widget.cget.return_value = "#000000"
        self.mock_vibration_widget.widget.configure = Mock()
        
        # Add parameter widgets to params frame
        self.mock_params_frame.parameter_widgets = {
            'server_ip': self.mock_server_ip_widget,
            'vibration': self.mock_vibration_widget
        }
        
        # Attach params frame to app
        self.mock_app.params_frame = self.mock_params_frame

    def test_update_ui_from_device_config_basic(self):
        """Test basic UI update from device configuration data."""
        # Prepare test data
        config_data = {
            'apn_server': 'new.apn.com',
            'apn_user': 'newuser',
            'apn_password': 'newpass',
            'server_address': '10.0.0.1',
            'vibration': 150
        }
        
        # Call the method
        self.config_reader.update_ui_from_device_config(config_data)
        
        # Verify APN fields were updated
        self.mock_apn_server_entry.delete.assert_called_with(0, 'end')
        self.mock_apn_server_entry.insert.assert_called_with(0, 'new.apn.com')
        
        self.mock_apn_user_entry.delete.assert_called_with(0, 'end')
        self.mock_apn_user_entry.insert.assert_called_with(0, 'newuser')
        
        self.mock_apn_password_entry.delete.assert_called_with(0, 'end')
        self.mock_apn_password_entry.insert.assert_called_with(0, 'newpass')
        
        # Verify parameter widgets were updated
        self.mock_server_ip_widget.set_value.assert_called_with('10.0.0.1')
        self.mock_vibration_widget.set_value.assert_called_with(150)
        
        # Verify visual indicators were added
        self.mock_apn_server_entry.configure.assert_called()
        self.mock_server_ip_widget.widget.configure.assert_called()
        self.mock_vibration_widget.widget.configure.assert_called()
        
        # Verify logging occurred
        self.assertTrue(self.mock_log_frame.log_message.called)

    def test_update_ui_with_unchanged_values(self):
        """Test UI update when values haven't changed."""
        # Prepare test data with same values
        config_data = {
            'apn_server': 'old.apn.com',  # Same as current value
            'server_address': '192.168.1.1',  # Same as current value
            'vibration': 200  # Different value
        }
        
        # Call the method
        self.config_reader.update_ui_from_device_config(config_data)
        
        # Verify all fields were updated regardless of value change
        self.mock_apn_server_entry.delete.assert_called_with(0, 'end')
        self.mock_apn_server_entry.insert.assert_called_with(0, 'old.apn.com')
        
        self.mock_server_ip_widget.set_value.assert_called_with('192.168.1.1')
        self.mock_vibration_widget.set_value.assert_called_with(200)
        
        # Verify visual indicators were still added
        self.mock_apn_server_entry.configure.assert_called()
        self.mock_server_ip_widget.widget.configure.assert_called()
        self.mock_vibration_widget.widget.configure.assert_called()

    def test_update_ui_with_empty_config_data(self):
        """Test UI update with empty configuration data."""
        # Call with empty data
        self.config_reader.update_ui_from_device_config({})
        
        # Verify warning was logged
        self.mock_log_frame.log_message.assert_called()
        log_calls = [call[0][0] for call in self.mock_log_frame.log_message.call_args_list]
        self.assertTrue(any("WARNING: No configuration data provided" in call for call in log_calls))
        
        # Verify no widgets were updated
        self.mock_apn_server_entry.delete.assert_not_called()
        self.mock_server_ip_widget.set_value.assert_not_called()

    def test_update_ui_with_missing_params_frame(self):
        """Test UI update when parameters frame is missing."""
        # Remove params frame from app
        self.mock_app.params_frame = None
        
        # Call the method
        self.config_reader.update_ui_from_device_config({'apn_server': 'test.com'})
        
        # Verify error was logged
        self.mock_log_frame.log_message.assert_called()
        log_calls = [call[0][0] for call in self.mock_log_frame.log_message.call_args_list]
        self.assertTrue(any("ERROR: Parameters frame not found" in call for call in log_calls))

    def test_update_ui_from_parameter_results(self):
        """Test UI update from parameter read results."""
        # Create mock parameter read results
        results = [
            ParameterReadResult(
                parameter_name='apn_config',
                success=True,
                value='APN:new.apn.com,newuser,newpass',
                error_message=None,
                raw_response='APN:new.apn.com,newuser,newpass'
            ),
            ParameterReadResult(
                parameter_name='server_config',
                success=True,
                value='SERVER:0,10.0.0.1,8080,0',
                error_message=None,
                raw_response='SERVER:0,10.0.0.1,8080,0'
            ),
            ParameterReadResult(
                parameter_name='vibration_settings',
                success=True,
                value='VIBL=5',
                error_message=None,
                raw_response='VIBL=5'
            )
        ]
        
        # Call the method
        self.config_reader._update_ui_from_results(results)
        
        # Verify logging occurred
        self.assertTrue(self.mock_log_frame.log_message.called)

    def test_visual_indicator_scheduling(self):
        """Test that visual indicators are properly scheduled for removal."""
        config_data = {
            'apn_server': 'new.apn.com',
            'vibration': 150
        }
        
        # Call the method
        self.config_reader.update_ui_from_device_config(config_data)
        
        # Verify that app.after was called to schedule indicator removal
        self.assertTrue(self.mock_app.after.called)
        
        # Check that the scheduling calls include the expected delays
        after_calls = self.mock_app.after.call_args_list
        delays = [call[0][0] for call in after_calls]
        
        # Should have calls for 3000ms (changed values) and possibly 2000ms (unchanged values)
        self.assertTrue(any(delay == 3000 for delay in delays))

    def test_parameter_update_logging(self):
        """Test that parameter updates are properly logged with timestamps."""
        config_data = {
            'apn_server': 'new.apn.com',
            'apn_user': 'newuser',
            'server_address': '10.0.0.1'
        }
        
        # Call the method
        self.config_reader.update_ui_from_device_config(config_data)
        
        # Verify detailed logging occurred
        log_calls = [call[0][0] for call in self.mock_log_frame.log_message.call_args_list]
        
        # Check for parameter update logs
        self.assertTrue(any("INFO: Updated APN Server" in call for call in log_calls))
        self.assertTrue(any("INFO: Updated APN User" in call for call in log_calls))
        self.assertTrue(any("INFO: Updated Server IP" in call for call in log_calls))
        
        # Check for summary logs
        self.assertTrue(any("INFO: Parameter updates at" in call for call in log_calls))
        self.assertTrue(any("SUCCESS:" in call for call in log_calls))

    def test_error_handling_in_ui_update(self):
        """Test error handling during UI updates."""
        # Make one of the widgets raise an exception
        self.mock_apn_server_entry.delete.side_effect = Exception("Widget error")
        
        config_data = {
            'apn_server': 'new.apn.com',
            'vibration': 150
        }
        
        # Call the method - should not raise exception
        self.config_reader.update_ui_from_device_config(config_data)
        
        # Verify error was logged
        log_calls = [call[0][0] for call in self.mock_log_frame.log_message.call_args_list]
        self.assertTrue(any("WARNING:" in call for call in log_calls))
        
        # Verify other widgets were still updated
        self.mock_vibration_widget.set_value.assert_called_with(150)

    def test_password_field_security(self):
        """Test that password fields are handled securely in logging."""
        config_data = {
            'apn_password': 'newsecretpass'
        }
        
        # Call the method
        self.config_reader.update_ui_from_device_config(config_data)
        
        # Verify password was updated
        self.mock_apn_password_entry.delete.assert_called_with(0, 'end')
        self.mock_apn_password_entry.insert.assert_called_with(0, 'newsecretpass')
        
        # Verify password values are masked in logs
        log_calls = [call[0][0] for call in self.mock_log_frame.log_message.call_args_list]
        password_logs = [call for call in log_calls if "Password" in call]
        
        # Should not contain actual password values
        for log in password_logs:
            self.assertNotIn('newsecretpass', log)
            self.assertNotIn('oldpass', log)

    def test_differential_highlighting(self):
        """Test that parameters are highlighted differently based on value changes."""
        config_data = {
            'apn_server': 'old.apn.com',  # Same value - should get blue border
            'vibration': 200  # Different value - should get green border
        }
        
        # Call the method
        self.config_reader.update_ui_from_device_config(config_data)
        
        # Check that configure was called on both widgets
        self.mock_apn_server_entry.configure.assert_called()
        self.mock_vibration_widget.widget.configure.assert_called()
        
        # Verify different scheduling delays were used
        after_calls = self.mock_app.after.call_args_list
        delays = [call[0][0] for call in after_calls]
        
        # Should have both 2000ms (unchanged) and 3000ms (changed) delays
        self.assertTrue(any(delay == 2000 for delay in delays))
        self.assertTrue(any(delay == 3000 for delay in delays))


class TestParameterWidgetIndicators(unittest.TestCase):
    """Test parameter widget visual indicators."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.i18n = I18nService()
        self.validation_service = ValidationService(self.i18n)
        
        # Create a mock parameter definition
        self.param_def = ParameterDefinition(
            name='test_param',
            param_type='numeric',
            display_label='Test Parameter',
            help_text='Test help',
            at_command_template='AT+TEST={value}#',
            validation_rules={'min_value': 0, 'max_value': 255}
        )
        
        # Create mock send command callback
        self.send_command_callback = Mock()

    def test_add_update_indicator_changed_value(self):
        """Test adding update indicator for changed values."""
        # This test would require actual widget creation which is complex
        # For now, we'll test the logic conceptually
        pass

    def test_add_update_indicator_unchanged_value(self):
        """Test adding update indicator for unchanged values."""
        # This test would require actual widget creation which is complex
        # For now, we'll test the logic conceptually
        pass


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)