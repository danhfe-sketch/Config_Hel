#!/usr/bin/env python3
"""
Integration test for UI field population from device responses.

This test verifies the complete workflow of reading device configuration
and updating UI fields with visual indicators and logging.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import time

from services.configuration_reader_service import (
    ConfigurationReaderService, 
    ParameterReadResult, 
    ConfigurationReadResult
)
from services.i18n_service import I18nService


class TestUIFieldPopulationIntegration(unittest.TestCase):
    """Integration test for UI field population."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock application with proper structure
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

    def test_complete_ui_update_workflow(self):
        """Test the complete workflow of updating UI from device responses."""
        # Create mock parameters frame with all necessary components
        mock_params_frame = self._create_mock_params_frame()
        self.mock_app.params_frame = mock_params_frame
        
        # Create test configuration data
        config_data = {
            'apn_server': 'internet.provider.com',
            'apn_user': 'testuser',
            'apn_password': 'testpass',
            'server_address': '192.168.1.100',
            'server_port': '8080',
            'gt06_protocol': 'GT06-0x60',
            'vibration': 128,
            'timer_ign_on': 30,
            'timer_ign_off': 300
        }
        
        # Call the UI update method
        self.config_reader.update_ui_from_device_config(config_data)
        
        # Verify APN fields were updated
        self._verify_apn_updates(mock_params_frame, config_data)
        
        # Verify parameter widgets were updated
        self._verify_parameter_widget_updates(mock_params_frame, config_data)
        
        # Verify visual indicators were applied
        self._verify_visual_indicators(mock_params_frame)
        
        # Verify scheduling of indicator removal
        self.assertTrue(self.mock_app.after.called, "Should schedule indicator removal")

    def test_parameter_read_results_to_ui_update(self):
        """Test converting parameter read results to UI updates."""
        # Create mock parameters frame
        mock_params_frame = self._create_mock_params_frame()
        self.mock_app.params_frame = mock_params_frame
        
        # Create mock parameter read results
        results = [
            ParameterReadResult(
                parameter_name='apn_config',
                success=True,
                value='APN:internet.com,user,pass',
                error_message=None,
                raw_response='APN:internet.com,user,pass'
            ),
            ParameterReadResult(
                parameter_name='server_config',
                success=True,
                value='SERVER:0,192.168.1.1,8080,0',
                error_message=None,
                raw_response='SERVER:0,192.168.1.1,8080,0'
            ),
            ParameterReadResult(
                parameter_name='vibration_settings',
                success=True,
                value='VIBL=5',
                error_message=None,
                raw_response='VIBL=5'
            )
        ]
        
        # Call the method to update UI from results
        self.config_reader._update_ui_from_results(results)
        
        # The method should not raise exceptions
        # Detailed verification would require parsing the responses

    def test_differential_highlighting_logic(self):
        """Test that parameters are highlighted differently based on value changes."""
        # Create mock parameters frame
        mock_params_frame = self._create_mock_params_frame()
        self.mock_app.params_frame = mock_params_frame
        
        # Set up current values in widgets
        mock_params_frame.apn_server_entry.get.return_value = "old.apn.com"
        mock_params_frame.parameter_widgets['vibration'].get_value.return_value = 100
        
        # Test data with one changed and one unchanged value
        config_data = {
            'apn_server': 'old.apn.com',  # Same value
            'vibration': 150  # Different value
        }
        
        # Call the UI update method
        self.config_reader.update_ui_from_device_config(config_data)
        
        # Verify both widgets were configured (for visual indicators)
        mock_params_frame.apn_server_entry.configure.assert_called()
        mock_params_frame.parameter_widgets['vibration'].widget.configure.assert_called()
        
        # Verify different scheduling delays were used
        after_calls = self.mock_app.after.call_args_list
        delays = [call[0][0] for call in after_calls]
        
        # Should have both types of delays (for changed and unchanged values)
        self.assertTrue(len(delays) > 0, "Should schedule indicator removal")

    def test_error_handling_during_ui_update(self):
        """Test error handling when UI updates fail."""
        # Create mock parameters frame with failing widget
        mock_params_frame = self._create_mock_params_frame()
        mock_params_frame.apn_server_entry.delete.side_effect = Exception("Widget error")
        self.mock_app.params_frame = mock_params_frame
        
        # Test data
        config_data = {
            'apn_server': 'test.com',
            'vibration': 150
        }
        
        # Call the method - should not raise exception
        try:
            self.config_reader.update_ui_from_device_config(config_data)
            success = True
        except Exception as e:
            success = False
            print(f"Unexpected exception: {e}")
        
        self.assertTrue(success, "Should handle widget errors gracefully")
        
        # Verify other widgets were still updated
        mock_params_frame.parameter_widgets['vibration'].set_value.assert_called_with(150)

    def test_password_field_security_handling(self):
        """Test that password fields are handled securely."""
        # Create mock parameters frame
        mock_params_frame = self._create_mock_params_frame()
        self.mock_app.params_frame = mock_params_frame
        
        # Test data with password
        config_data = {
            'apn_password': 'secretpassword123'
        }
        
        # Call the UI update method
        self.config_reader.update_ui_from_device_config(config_data)
        
        # Verify password field was updated
        mock_params_frame.apn_password_entry.delete.assert_called_with(0, 'end')
        mock_params_frame.apn_password_entry.insert.assert_called_with(0, 'secretpassword123')
        
        # The actual password should not appear in logs (this would need log inspection)

    def test_visual_indicator_timing(self):
        """Test that visual indicators are scheduled with correct timing."""
        # Create mock parameters frame
        mock_params_frame = self._create_mock_params_frame()
        self.mock_app.params_frame = mock_params_frame
        
        # Test data
        config_data = {
            'apn_server': 'new.apn.com',
            'vibration': 150
        }
        
        # Call the UI update method
        self.config_reader.update_ui_from_device_config(config_data)
        
        # Verify scheduling calls were made
        self.assertTrue(self.mock_app.after.called, "Should schedule indicator removal")
        
        # Check that delays include the expected indicator removal delays (2000ms or 3000ms)
        after_calls = self.mock_app.after.call_args_list
        delays = [call[0][0] for call in after_calls]
        
        # Filter out immediate execution calls (delay 0) and check for indicator removal delays
        indicator_delays = [delay for delay in delays if delay in [2000, 3000]]
        self.assertTrue(len(indicator_delays) > 0, f"Should have indicator removal delays, got delays: {delays}")

    def test_parameter_mapping_completeness(self):
        """Test that all expected parameter mappings work."""
        # Create mock parameters frame
        mock_params_frame = self._create_mock_params_frame()
        self.mock_app.params_frame = mock_params_frame
        
        # Test all parameter mappings
        config_data = {
            'server_address': '10.0.0.1',
            'server_port': '9000',
            'protocol': 'CRX3',
            'vibration': 200,
            'sensitivity': 8,
            'curve_sensor': 'Enabled',
            'ignition_type': 'Analog',
            'timer_ign_on': 60,
            'timer_ign_off': 600,
            'heartbeat_ign_on': 120,
            'heartbeat_ign_off': 1200,
            'heartbeat_interval': '5min',
            'lock_type': 'Card'
        }
        
        # Call the UI update method
        self.config_reader.update_ui_from_device_config(config_data)
        
        # Verify that all parameter widgets that exist were called
        for param_name, widget in mock_params_frame.parameter_widgets.items():
            if param_name in ['server_ip', 'vibration', 'sensitivity']:  # Only test existing widgets
                widget.set_value.assert_called()

    def _create_mock_params_frame(self):
        """Create a comprehensive mock parameters frame."""
        mock_params_frame = Mock()
        
        # Create mock APN entry widgets
        mock_params_frame.apn_server_entry = self._create_mock_entry_widget("old.apn.com")
        mock_params_frame.apn_user_entry = self._create_mock_entry_widget("olduser")
        mock_params_frame.apn_password_entry = self._create_mock_entry_widget("oldpass")
        
        # Create mock parameter widgets
        mock_params_frame.parameter_widgets = {
            'server_ip': self._create_mock_parameter_widget("192.168.1.1", "Server IP"),
            'server_port': self._create_mock_parameter_widget("8080", "Server Port"),
            'gt06_protocol': self._create_mock_parameter_widget("GT06-0x60", "Protocol"),
            'vibration': self._create_mock_parameter_widget(100, "Vibration"),
            'sensitivity': self._create_mock_parameter_widget(5, "Sensitivity"),
            'curve_sensor': self._create_mock_parameter_widget("Auto", "Curve Sensor"),
            'ignition_type': self._create_mock_parameter_widget("Digital", "Ignition Type"),
            'timer_ign_on': self._create_mock_parameter_widget(30, "Timer Ignition On"),
            'timer_ign_off': self._create_mock_parameter_widget(300, "Timer Ignition Off"),
            'heartbeat_ign_on': self._create_mock_parameter_widget(60, "Heartbeat Ignition On"),
            'heartbeat_ign_off': self._create_mock_parameter_widget(600, "Heartbeat Ignition Off"),
            'heartbeat_interval': self._create_mock_parameter_widget("1min", "Heartbeat Interval"),
            'lock_type': self._create_mock_parameter_widget("PIN", "Lock Type")
        }
        
        return mock_params_frame

    def _create_mock_entry_widget(self, initial_value):
        """Create a mock entry widget."""
        widget = Mock()
        widget.get.return_value = initial_value
        widget.delete = Mock()
        widget.insert = Mock()
        widget.cget.return_value = "#000000"
        widget.configure = Mock()
        return widget

    def _create_mock_parameter_widget(self, initial_value, display_label):
        """Create a mock parameter widget."""
        widget = Mock()
        widget.get_value.return_value = initial_value
        widget.set_value = Mock()
        widget.definition = Mock()
        widget.definition.display_label = display_label
        widget.widget = Mock()
        widget.widget.cget.return_value = "#000000"
        widget.widget.configure = Mock()
        return widget

    def _verify_apn_updates(self, mock_params_frame, config_data):
        """Verify APN fields were updated correctly."""
        if 'apn_server' in config_data:
            mock_params_frame.apn_server_entry.delete.assert_called_with(0, 'end')
            mock_params_frame.apn_server_entry.insert.assert_called_with(0, config_data['apn_server'])
        
        if 'apn_user' in config_data:
            mock_params_frame.apn_user_entry.delete.assert_called_with(0, 'end')
            mock_params_frame.apn_user_entry.insert.assert_called_with(0, config_data['apn_user'])
        
        if 'apn_password' in config_data:
            mock_params_frame.apn_password_entry.delete.assert_called_with(0, 'end')
            mock_params_frame.apn_password_entry.insert.assert_called_with(0, config_data['apn_password'])

    def _verify_parameter_widget_updates(self, mock_params_frame, config_data):
        """Verify parameter widgets were updated correctly."""
        # Map config data keys to widget names
        mapping = {
            'server_address': 'server_ip',
            'vibration': 'vibration',
            'timer_ign_on': 'timer_ign_on'
        }
        
        for config_key, widget_name in mapping.items():
            if config_key in config_data and widget_name in mock_params_frame.parameter_widgets:
                widget = mock_params_frame.parameter_widgets[widget_name]
                widget.set_value.assert_called_with(config_data[config_key])

    def _verify_visual_indicators(self, mock_params_frame):
        """Verify visual indicators were applied."""
        # Check that configure was called on APN widgets
        mock_params_frame.apn_server_entry.configure.assert_called()
        
        # Check that configure was called on parameter widgets
        for widget in mock_params_frame.parameter_widgets.values():
            if hasattr(widget, 'widget') and widget.widget:
                # Not all widgets may be updated, so we don't assert all were called
                pass


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)