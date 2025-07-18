"""
Unit tests for ValidationService - Comprehensive parameter validation testing.

Tests all validation scenarios including edge cases for vibration levels,
timer settings, sensitivity ranges, dropdown selections, and radio button groups.
"""

import unittest
from unittest.mock import Mock
from services.validation_service import ValidationService, ValidationResult
from services.i18n_service import I18nService


class TestValidationService(unittest.TestCase):
    """Test cases for ValidationService parameter validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock I18nService for testing
        self.mock_i18n = Mock(spec=I18nService)
        self.mock_i18n.get.side_effect = lambda key, default: default
        
        self.validation_service = ValidationService(self.mock_i18n)
    
    def test_vibration_validation(self):
        """Test vibration level validation (1-6 range)."""
        # Valid values
        self.assertTrue(self.validation_service.validate_parameter('vibration', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('vibration', 3).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('vibration', 6).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('vibration', '4').is_valid)
        
        # Invalid values - below minimum
        result = self.validation_service.validate_parameter('vibration', 0)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        # Invalid values - above maximum
        result = self.validation_service.validate_parameter('vibration', 7)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        
        # Invalid values - non-integer
        result = self.validation_service.validate_parameter('vibration', 3.5)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INTEGER_REQUIRED')
        
        # Invalid values - non-numeric
        result = self.validation_service.validate_parameter('vibration', 'abc')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_NUMBER')
    
    def test_sensitivity_validation(self):
        """Test sensitivity level validation (1-10 range)."""
        # Valid values
        self.assertTrue(self.validation_service.validate_parameter('sensitivity', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('sensitivity', 5).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('sensitivity', 10).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('sensitivity', '7').is_valid)
        
        # Invalid values - below minimum
        result = self.validation_service.validate_parameter('sensitivity', 0)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        # Invalid values - above maximum
        result = self.validation_service.validate_parameter('sensitivity', 11)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        
        # Invalid values - non-integer
        result = self.validation_service.validate_parameter('sensitivity', 5.5)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INTEGER_REQUIRED')
    
    def test_timer_validation(self):
        """Test timer settings validation (1-65500 range)."""
        # Valid values for ignition on timer
        self.assertTrue(self.validation_service.validate_parameter('timer_ign_on', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('timer_ign_on', 30).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('timer_ign_on', 65500).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('timer_ign_on', '300').is_valid)
        
        # Valid values for ignition off timer
        self.assertTrue(self.validation_service.validate_parameter('timer_ign_off', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('timer_ign_off', 60).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('timer_ign_off', 65500).is_valid)
        
        # Invalid values - below minimum
        result = self.validation_service.validate_parameter('timer_ign_on', 0)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        # Invalid values - above maximum
        result = self.validation_service.validate_parameter('timer_ign_off', 65501)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        
        # Invalid values - non-integer
        result = self.validation_service.validate_parameter('timer_ign_on', 30.5)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INTEGER_REQUIRED')
    
    def test_heartbeat_validation(self):
        """Test heartbeat timer validation (60-300 range)."""
        # Valid values
        self.assertTrue(self.validation_service.validate_parameter('heartbeat_ign_on', 60).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('heartbeat_ign_on', 180).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('heartbeat_ign_on', 300).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('heartbeat_ign_off', '120').is_valid)
        
        # Invalid values - below minimum
        result = self.validation_service.validate_parameter('heartbeat_ign_on', 59)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        # Invalid values - above maximum
        result = self.validation_service.validate_parameter('heartbeat_ign_off', 301)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
    
    def test_speed_validation(self):
        """Test speed-related parameter validation."""
        # Speed limit validation (1-255)
        self.assertTrue(self.validation_service.validate_parameter('speed_limit', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('speed_limit', 120).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('speed_limit', 255).is_valid)
        
        result = self.validation_service.validate_parameter('speed_limit', 0)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        result = self.validation_service.validate_parameter('speed_limit', 256)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        
        # Speed time validation (5-600)
        self.assertTrue(self.validation_service.validate_parameter('speed_time', 5).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('speed_time', 30).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('speed_time', 600).is_valid)
        
        result = self.validation_service.validate_parameter('speed_time', 4)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        result = self.validation_service.validate_parameter('speed_time', 601)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
    
    def test_angle_validation(self):
        """Test angle-related parameter validation."""
        # Angle speed validation (1-20)
        self.assertTrue(self.validation_service.validate_parameter('angle_speed', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('angle_speed', 10).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('angle_speed', 20).is_valid)
        
        result = self.validation_service.validate_parameter('angle_speed', 0)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        result = self.validation_service.validate_parameter('angle_speed', 21)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        
        # Angle value validation (5-90)
        self.assertTrue(self.validation_service.validate_parameter('angle_value', 5).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('angle_value', 45).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('angle_value', 90).is_valid)
        
        result = self.validation_service.validate_parameter('angle_value', 4)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        result = self.validation_service.validate_parameter('angle_value', 91)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
    

    
    def test_text_validation(self):
        """Test text parameter validation."""
        # APN server validation
        self.assertTrue(self.validation_service.validate_parameter('apn_server', 'internet.provider.com').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('apn_server', 'apn.mobile.net').is_valid)
        
        # Test max length
        long_apn = 'a' * 51  # Exceeds 50 character limit
        result = self.validation_service.validate_parameter('apn_server', long_apn)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_LENGTH')
        
        # Test required field
        result = self.validation_service.validate_parameter('apn_server', '')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'REQUIRED_FIELD')
        
        # APN user/password (optional fields)
        self.assertTrue(self.validation_service.validate_parameter('apn_user', '').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('apn_password', '').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('apn_user', 'username').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('apn_password', 'password').is_valid)
    
    def test_ip_address_validation(self):
        """Test IP address validation."""
        # Valid IP addresses
        self.assertTrue(self.validation_service.validate_parameter('server_ip', '192.168.1.1').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('server_ip', '10.0.0.1').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('server_ip', '255.255.255.255').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('server_ip', '0.0.0.0').is_valid)
        
        # Invalid IP addresses
        result = self.validation_service.validate_parameter('server_ip', '256.1.1.1')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_IP')
        
        result = self.validation_service.validate_parameter('server_ip', '192.168.1')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_IP')
        
        result = self.validation_service.validate_parameter('server_ip', 'not.an.ip.address')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_IP')
    
    def test_domain_validation(self):
        """Test domain name validation."""
        # Valid domains
        self.assertTrue(self.validation_service.validate_parameter('server_domain', 'example.com').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('server_domain', 'sub.domain.example.org').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('server_domain', 'test-server.net').is_valid)
        
        # Invalid domains
        result = self.validation_service.validate_parameter('server_domain', 'invalid..domain')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_DOMAIN')
        
        result = self.validation_service.validate_parameter('server_domain', '-invalid.com')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_DOMAIN')
        
        # Test max length
        long_domain = 'a' * 51 + '.com'  # Exceeds 50 character limit
        result = self.validation_service.validate_parameter('server_domain', long_domain)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_LENGTH')
    
    def test_phone_validation(self):
        """Test phone number validation."""
        # Valid phone numbers
        self.assertTrue(self.validation_service.validate_parameter('phone_number', '1234567890').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('phone_number', '+55 11 99999-9999').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('phone_number', '(11) 9999-9999').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('phone_number', '11999999999').is_valid)
        
        # Invalid phone numbers
        result = self.validation_service.validate_parameter('phone_number', '123abc')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_PHONE')
        
        result = self.validation_service.validate_parameter('phone_number', '123')  # Too short
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'PHONE_TOO_SHORT')
        
        result = self.validation_service.validate_parameter('phone_number', '1' * 16)  # Too long
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'PHONE_TOO_LONG')
    
    def test_port_validation(self):
        """Test server port validation."""
        # Valid ports
        self.assertTrue(self.validation_service.validate_parameter('server_port', 80).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('server_port', 443).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('server_port', 8080).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('server_port', 65535).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('server_port', '3000').is_valid)
        
        # Invalid ports
        result = self.validation_service.validate_parameter('server_port', 0)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        result = self.validation_service.validate_parameter('server_port', 65536)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        
        result = self.validation_service.validate_parameter('server_port', 80.5)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INTEGER_REQUIRED')
    
    def test_dropdown_validation(self):
        """Test dropdown parameter validation."""
        # Heartbeat interval dropdown
        valid_intervals = ['30s', '1min', '5min', '10min', '30min', '1hr', '2hr', '6hr', '12hr', '24hr']
        for interval in valid_intervals:
            self.assertTrue(self.validation_service.validate_parameter('heartbeat_interval', interval).is_valid)
        
        result = self.validation_service.validate_parameter('heartbeat_interval', '15min')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Curve sensor dropdown
        valid_sensors = ['Enabled', 'Disabled', 'Auto']
        for sensor in valid_sensors:
            self.assertTrue(self.validation_service.validate_parameter('curve_sensor', sensor).is_valid)
        
        result = self.validation_service.validate_parameter('curve_sensor', 'Manual')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Protocol type dropdown
        valid_protocols = ['TCP', 'UDP']
        for protocol in valid_protocols:
            self.assertTrue(self.validation_service.validate_parameter('protocol_type', protocol).is_valid)
        
        result = self.validation_service.validate_parameter('protocol_type', 'HTTP')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Network type dropdown
        valid_networks = ['AUTO', '4G', '2G']
        for network in valid_networks:
            self.assertTrue(self.validation_service.validate_parameter('network_type', network).is_valid)
        
        result = self.validation_service.validate_parameter('network_type', '3G')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Sleep mode dropdown
        valid_sleep_modes = ['Disabled', 'Sleep', 'Deep Sleep']
        for mode in valid_sleep_modes:
            self.assertTrue(self.validation_service.validate_parameter('sleep_mode', mode).is_valid)
        
        result = self.validation_service.validate_parameter('sleep_mode', 'Hibernate')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Alert type dropdown
        valid_alerts = ['GPRS', 'SMS+GPRS']
        for alert in valid_alerts:
            self.assertTrue(self.validation_service.validate_parameter('alert_type', alert).is_valid)
        
        result = self.validation_service.validate_parameter('alert_type', 'SMS')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # GT06 protocol dropdown
        valid_protocols = ['GT06', 'CRX3', 'CRX']
        for protocol in valid_protocols:
            self.assertTrue(self.validation_service.validate_parameter('gt06_protocol', protocol).is_valid)
        
        result = self.validation_service.validate_parameter('gt06_protocol', 'INVALID')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # VoLTE switch dropdown
        valid_switches = ['2G', '4G']
        for switch in valid_switches:
            self.assertTrue(self.validation_service.validate_parameter('volte_switch', switch).is_valid)
        
        result = self.validation_service.validate_parameter('volte_switch', '3G')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Relay state dropdown
        valid_states = ['OFF', 'ON']
        for state in valid_states:
            self.assertTrue(self.validation_service.validate_parameter('relay_state', state).is_valid)
        
        result = self.validation_service.validate_parameter('relay_state', 'AUTO')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
    
    def test_radio_button_validation(self):
        """Test radio button group validation."""
        # Lock type radio buttons
        valid_lock_types = ['PIN', 'Card']
        for lock_type in valid_lock_types:
            self.assertTrue(self.validation_service.validate_parameter('lock_type', lock_type).is_valid)
        
        result = self.validation_service.validate_parameter('lock_type', 'Biometric')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Ignition type radio buttons
        valid_ignition_types = ['Digital', 'Analog']
        for ignition_type in valid_ignition_types:
            self.assertTrue(self.validation_service.validate_parameter('ignition_type', ignition_type).is_valid)
        
        result = self.validation_service.validate_parameter('ignition_type', 'Virtual')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Timezone direction radio buttons
        valid_directions = ['E', 'W']
        for direction in valid_directions:
            self.assertTrue(self.validation_service.validate_parameter('timezone_direction', direction).is_valid)
        
        result = self.validation_service.validate_parameter('timezone_direction', 'N')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Transmission mode radio buttons
        valid_modes = ['TCP', 'UDP']
        for mode in valid_modes:
            self.assertTrue(self.validation_service.validate_parameter('transmission_mode', mode).is_valid)
        
        result = self.validation_service.validate_parameter('transmission_mode', 'HTTP')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
    
    def test_additional_numeric_validation(self):
        """Test validation for additional numeric parameters."""
        # Jammer time validation (1-60)
        self.assertTrue(self.validation_service.validate_parameter('jammer_time', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('jammer_time', 30).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('jammer_time', 60).is_valid)
        
        result = self.validation_service.validate_parameter('jammer_time', 0)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        result = self.validation_service.validate_parameter('jammer_time', 61)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        
        # Jammer signal validation (1-100)
        self.assertTrue(self.validation_service.validate_parameter('jammer_signal', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('jammer_signal', 50).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('jammer_signal', 100).is_valid)
        
        result = self.validation_service.validate_parameter('jammer_signal', 0)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        result = self.validation_service.validate_parameter('jammer_signal', 101)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        
        # Jammer frequency validation (1-10)
        self.assertTrue(self.validation_service.validate_parameter('jammer_freq', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('jammer_freq', 5).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('jammer_freq', 10).is_valid)
        
        result = self.validation_service.validate_parameter('jammer_freq', 0)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        result = self.validation_service.validate_parameter('jammer_freq', 11)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        
        # ACC voltage validation (6-60)
        self.assertTrue(self.validation_service.validate_parameter('acc_on_voltage', 6).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('acc_on_voltage', 12).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('acc_on_voltage', 60).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('acc_off_voltage', 24).is_valid)
        
        result = self.validation_service.validate_parameter('acc_on_voltage', 5)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        result = self.validation_service.validate_parameter('acc_off_voltage', 61)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        
        # Timezone validation
        self.assertTrue(self.validation_service.validate_parameter('timezone_hours', 0).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('timezone_hours', 6).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('timezone_hours', 12).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('timezone_minutes', 0).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('timezone_minutes', 30).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('timezone_minutes', 59).is_valid)
        
        result = self.validation_service.validate_parameter('timezone_hours', -1)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        result = self.validation_service.validate_parameter('timezone_hours', 13)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        
        result = self.validation_service.validate_parameter('timezone_minutes', 60)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
    
    def test_additional_numeric_parameters_validation(self):
        """Test validation for additional numeric parameters."""
        # Vibration window validation (1-60)
        self.assertTrue(self.validation_service.validate_parameter('vibration_window', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('vibration_window', 30).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('vibration_window', 60).is_valid)
        
        result = self.validation_service.validate_parameter('vibration_window', 0)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        result = self.validation_service.validate_parameter('vibration_window', 61)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        
        # Vibration threshold validation (1-100)
        self.assertTrue(self.validation_service.validate_parameter('vibration_threshold', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('vibration_threshold', 50).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('vibration_threshold', 100).is_valid)
        
        result = self.validation_service.validate_parameter('vibration_threshold', 0)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        result = self.validation_service.validate_parameter('vibration_threshold', 101)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        
        # Power alert time validation (1-60)
        self.assertTrue(self.validation_service.validate_parameter('power_alert_t1', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('power_alert_t1', 30).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('power_alert_t1', 60).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('power_alert_t2', 15).is_valid)
        
        result = self.validation_service.validate_parameter('power_alert_t1', 0)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        
        result = self.validation_service.validate_parameter('power_alert_t2', 61)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
    
    def test_phone_number_parameters_validation(self):
        """Test validation for phone number parameters."""
        phone_params = ['sos_phone1', 'sos_phone2', 'sos_phone3', 'center_phone1', 'center_phone2', 'center_phone3']
        
        for param in phone_params:
            # Valid phone numbers
            self.assertTrue(self.validation_service.validate_parameter(param, '1234567890').is_valid)
            self.assertTrue(self.validation_service.validate_parameter(param, '+55 11 99999-9999').is_valid)
            self.assertTrue(self.validation_service.validate_parameter(param, '(11) 9999-9999').is_valid)
            
            # Empty values should be valid (optional fields)
            self.assertTrue(self.validation_service.validate_parameter(param, '').is_valid)
            self.assertTrue(self.validation_service.validate_parameter(param, None).is_valid)
            
            # Invalid phone numbers
            result = self.validation_service.validate_parameter(param, '123abc')
            self.assertFalse(result.is_valid)
            self.assertEqual(result.error_code, 'INVALID_PHONE')
            
            result = self.validation_service.validate_parameter(param, '123')  # Too short
            self.assertFalse(result.is_valid)
            self.assertEqual(result.error_code, 'PHONE_TOO_SHORT')
            
            result = self.validation_service.validate_parameter(param, '1' * 16)  # Too long
            self.assertFalse(result.is_valid)
            self.assertEqual(result.error_code, 'PHONE_TOO_LONG')
    
    def test_password_validation(self):
        """Test password parameter validation."""
        # Valid passwords
        self.assertTrue(self.validation_service.validate_parameter('password', 'test').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('password', 'password123').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('password', '1234567890123456789').is_valid)  # 19 chars
        
        # Empty password should be valid (optional field)
        self.assertTrue(self.validation_service.validate_parameter('password', '').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('password', None).is_valid)
        
        # Too short password
        result = self.validation_service.validate_parameter('password', '123')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_LENGTH')
        
        # Too long password
        result = self.validation_service.validate_parameter('password', '123456789012345678901')  # 21 chars
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_LENGTH')
    
    def test_additional_dropdown_parameters_validation(self):
        """Test validation for additional dropdown parameters."""
        # Power alert type dropdown
        valid_power_alerts = ['GPRS', 'SMS+GPRS']
        for alert in valid_power_alerts:
            self.assertTrue(self.validation_service.validate_parameter('power_alert_type', alert).is_valid)
        
        result = self.validation_service.validate_parameter('power_alert_type', 'SMS')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Battery alert type dropdown
        valid_battery_alerts = ['GPRS', 'SMS+GPRS']
        for alert in valid_battery_alerts:
            self.assertTrue(self.validation_service.validate_parameter('battery_alert_type', alert).is_valid)
        
        result = self.validation_service.validate_parameter('battery_alert_type', 'EMAIL')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Movement alert type dropdown
        valid_movement_alerts = ['GPRS', 'SMS+GPRS']
        for alert in valid_movement_alerts:
            self.assertTrue(self.validation_service.validate_parameter('movement_alert_type', alert).is_valid)
        
        result = self.validation_service.validate_parameter('movement_alert_type', 'INVALID')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # ACC alert type dropdown
        valid_acc_alerts = ['GPRS', 'SMS+GPRS']
        for alert in valid_acc_alerts:
            self.assertTrue(self.validation_service.validate_parameter('acc_alert_type', alert).is_valid)
            self.assertTrue(self.validation_service.validate_parameter('acc_off_alert_type', alert).is_valid)
        
        result = self.validation_service.validate_parameter('acc_alert_type', 'PUSH')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Jammer alert type dropdown
        valid_jammer_alerts = ['GPRS', 'SMS+GPRS']
        for alert in valid_jammer_alerts:
            self.assertTrue(self.validation_service.validate_parameter('jammer_alert_type', alert).is_valid)
        
        result = self.validation_service.validate_parameter('jammer_alert_type', 'WEBHOOK')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Speed alert type dropdown
        valid_speed_alerts = ['GPRS', 'SMS+GPRS']
        for alert in valid_speed_alerts:
            self.assertTrue(self.validation_service.validate_parameter('speed_alert_type', alert).is_valid)
        
        result = self.validation_service.validate_parameter('speed_alert_type', 'CALL')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # GPS source type dropdown
        valid_gps_sources = ['Disabled', 'Enabled']
        for source in valid_gps_sources:
            self.assertTrue(self.validation_service.validate_parameter('gps_source_type', source).is_valid)
        
        result = self.validation_service.validate_parameter('gps_source_type', 'Auto')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Parameter lock state dropdown
        valid_lock_states = ['Unlock', 'Lock']
        for state in valid_lock_states:
            self.assertTrue(self.validation_service.validate_parameter('parameter_lock_state', state).is_valid)
        
        result = self.validation_service.validate_parameter('parameter_lock_state', 'Partial')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SELECTION')
    
    def test_comprehensive_edge_cases(self):
        """Test comprehensive edge cases for all parameter types."""
        # Test boundary values for all numeric parameters
        numeric_params = [
            ('vibration', 1, 6),
            ('sensitivity', 1, 10),
            ('timer_ign_on', 1, 65500),
            ('timer_ign_off', 1, 65500),
            ('heartbeat_ign_on', 60, 300),
            ('heartbeat_ign_off', 60, 300),
            ('speed_limit', 1, 255),
            ('speed_time', 5, 600),
            ('angle_speed', 1, 20),
            ('angle_value', 5, 90),
            ('blind_speed', 0, 20),
            ('defense_time', 1, 60),
            ('moving_radius', 100, 1000),
            ('sleep_time', 1, 1440),
            ('jammer_time', 1, 60),
            ('jammer_signal', 1, 100),
            ('jammer_freq', 1, 10),
            ('acc_on_voltage', 6, 60),
            ('acc_off_voltage', 6, 60),
            ('timezone_hours', 0, 12),
            ('timezone_minutes', 0, 59),
            ('vibration_window', 1, 60),
            ('vibration_threshold', 1, 100),
            ('power_alert_t1', 1, 60),
            ('power_alert_t2', 1, 60),
            ('server_port', 1, 65535)
        ]
        
        for param_name, min_val, max_val in numeric_params:
            # Test minimum boundary
            self.assertTrue(self.validation_service.validate_parameter(param_name, min_val).is_valid, 
                          f'{param_name} should accept minimum value {min_val}')
            
            # Test maximum boundary
            self.assertTrue(self.validation_service.validate_parameter(param_name, max_val).is_valid,
                          f'{param_name} should accept maximum value {max_val}')
            
            # Test below minimum
            if min_val > 0:
                result = self.validation_service.validate_parameter(param_name, min_val - 1)
                self.assertFalse(result.is_valid, f'{param_name} should reject value below minimum')
                self.assertEqual(result.error_code, 'MIN_VALUE')
            
            # Test above maximum
            result = self.validation_service.validate_parameter(param_name, max_val + 1)
            self.assertFalse(result.is_valid, f'{param_name} should reject value above maximum')
            self.assertEqual(result.error_code, 'MAX_VALUE')
        
        # Test all dropdown parameters with invalid selections
        dropdown_params = [
            'heartbeat_interval', 'curve_sensor', 'protocol_type', 'network_type',
            'sleep_mode', 'alert_type', 'gt06_protocol', 'volte_switch', 'relay_state',
            'power_alert_type', 'battery_alert_type', 'movement_alert_type',
            'acc_alert_type', 'acc_off_alert_type', 'jammer_alert_type',
            'speed_alert_type', 'gps_source_type', 'parameter_lock_state'
        ]
        
        for param_name in dropdown_params:
            result = self.validation_service.validate_parameter(param_name, 'INVALID_OPTION')
            self.assertFalse(result.is_valid, f'{param_name} should reject invalid selection')
            self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Test all radio button parameters with invalid selections
        radio_params = ['lock_type', 'ignition_type', 'transmission_mode', 'timezone_direction']
        
        for param_name in radio_params:
            result = self.validation_service.validate_parameter(param_name, 'INVALID_RADIO')
            self.assertFalse(result.is_valid, f'{param_name} should reject invalid radio selection')
            self.assertEqual(result.error_code, 'INVALID_SELECTION')
        
        # Test text parameters with various edge cases
        text_params = ['apn_user', 'apn_password', 'password']
        
        for param_name in text_params:
            # Test with numeric input (should be converted to string)
            result = self.validation_service.validate_parameter(param_name, 12345)
            # Optional fields should pass
            self.assertTrue(result.is_valid or result.error_code in ['MIN_LENGTH', 'INVALID_FORMAT'])
    
    def test_parameter_info_and_utility_methods(self):
        """Test utility methods for parameter information."""
        # Test get_parameter_info
        vibration_info = self.validation_service.get_parameter_info('vibration')
        self.assertIsNotNone(vibration_info)
        self.assertEqual(vibration_info['type'], 'numeric')
        self.assertEqual(vibration_info['min'], 1)
        self.assertEqual(vibration_info['max'], 6)
        
        # Test get_parameter_info for unknown parameter
        unknown_info = self.validation_service.get_parameter_info('unknown_param')
        self.assertIsNone(unknown_info)
        
        # Test get_all_parameters
        all_params = self.validation_service.get_all_parameters()
        self.assertIsInstance(all_params, list)
        self.assertIn('vibration', all_params)
        self.assertIn('sensitivity', all_params)
        self.assertIn('apn_server', all_params)
        self.assertIn('heartbeat_interval', all_params)
        self.assertIn('lock_type', all_params)
        
        # Verify we have all the new parameters
        new_params = [
            'vibration_window', 'vibration_threshold', 'power_alert_t1', 'power_alert_t2',
            'sos_phone1', 'sos_phone2', 'sos_phone3', 'center_phone1', 'center_phone2', 'center_phone3',
            'password', 'power_alert_type', 'battery_alert_type', 'movement_alert_type',
            'acc_alert_type', 'acc_off_alert_type', 'jammer_alert_type', 'speed_alert_type',
            'gps_source_type', 'parameter_lock_state'
        ]
        
        for param in new_params:
            self.assertIn(param, all_params, f'New parameter {param} should be in parameter list')
    
    def test_validation_with_suggested_values(self):
        """Test validation results that include suggested values."""
        # Test numeric parameter with suggested minimum value
        result = self.validation_service.validate_parameter('vibration', 0)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MIN_VALUE')
        self.assertEqual(result.suggested_value, '1')
        
        # Test numeric parameter with suggested maximum value
        result = self.validation_service.validate_parameter('sensitivity', 15)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MAX_VALUE')
        self.assertEqual(result.suggested_value, '10')
        
        # Test parameter with no suggested value
        result = self.validation_service.validate_parameter('apn_server', '')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'REQUIRED_FIELD')
        self.assertIsNone(result.suggested_value)

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test None values
        result = self.validation_service.validate_parameter('apn_user', None)
        self.assertTrue(result.is_valid)  # Optional field
        
        result = self.validation_service.validate_parameter('apn_server', None)
        self.assertFalse(result.is_valid)  # Required field
        self.assertEqual(result.error_code, 'REQUIRED_FIELD')
        
        # Test empty strings
        result = self.validation_service.validate_parameter('apn_password', '')
        self.assertTrue(result.is_valid)  # Optional field
        
        result = self.validation_service.validate_parameter('apn_server', '   ')
        self.assertFalse(result.is_valid)  # Required field with whitespace
        self.assertEqual(result.error_code, 'REQUIRED_FIELD')
        
        # Test boundary values
        self.assertTrue(self.validation_service.validate_parameter('vibration', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('vibration', 6).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('sensitivity', 1).is_valid)
        self.assertTrue(self.validation_service.validate_parameter('sensitivity', 10).is_valid)
        
        # Test string representations of numbers
        self.assertTrue(self.validation_service.validate_parameter('vibration', '3').is_valid)
        self.assertTrue(self.validation_service.validate_parameter('server_port', '8080').is_valid)
        
        # Test float to int conversion
        self.assertTrue(self.validation_service.validate_parameter('vibration', 3.0).is_valid)
        
        result = self.validation_service.validate_parameter('vibration', 3.7)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INTEGER_REQUIRED')
    
    def test_unknown_parameter(self):
        """Test validation of unknown parameters."""
        result = self.validation_service.validate_parameter('unknown_param', 'value')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'UNKNOWN_PARAMETER')
    
    def test_connection_validation(self):
        """Test connection requirement validation."""
        # Mock serial service with connection
        mock_serial_connected = Mock()
        mock_serial_connected.is_connected = True
        
        result = self.validation_service.validate_connection_required(mock_serial_connected)
        self.assertTrue(result.is_valid)
        
        # Mock serial service without connection
        mock_serial_disconnected = Mock()
        mock_serial_disconnected.is_connected = False
        
        result = self.validation_service.validate_connection_required(mock_serial_disconnected)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'CONNECTION_REQUIRED')
        
        # Mock serial service without is_connected attribute
        mock_serial_no_attr = Mock()
        del mock_serial_no_attr.is_connected
        
        result = self.validation_service.validate_connection_required(mock_serial_no_attr)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'CONNECTION_REQUIRED')
    
    def test_profile_validation(self):
        """Test configuration profile validation."""
        # Valid profile
        valid_profile = {
            'version': '1.0',
            'apn_config': {
                'apn_server': 'internet.provider.com',
                'apn_user': 'user',
                'apn_password': 'pass'
            },
            'device_parameters': {
                'vibration': 3,
                'sensitivity': 5
            }
        }
        
        result = self.validation_service.validate_profile_data(valid_profile)
        self.assertTrue(result.is_valid)
        
        # Invalid profile - not a dictionary
        result = self.validation_service.validate_profile_data('not a dict')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_PROFILE_FORMAT')
        
        # Invalid profile - missing version
        invalid_profile = {
            'apn_config': {
                'apn_server': 'internet.provider.com'
            }
        }
        
        result = self.validation_service.validate_profile_data(invalid_profile)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'MISSING_PROFILE_SECTION')
        
        # Invalid profile - invalid parameter values
        invalid_values_profile = {
            'version': '1.0',
            'device_parameters': {
                'vibration': 7,  # Exceeds maximum (valid range is 1-6)
                'sensitivity': 0   # Below minimum
            }
        }
        
        result = self.validation_service.validate_profile_data(invalid_values_profile)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'PROFILE_VALIDATION_ERRORS')
    
    def test_parameter_info_methods(self):
        """Test parameter information retrieval methods."""
        # Test get_parameter_info
        vibration_info = self.validation_service.get_parameter_info('vibration')
        self.assertIsNotNone(vibration_info)
        self.assertEqual(vibration_info['type'], 'numeric')
        self.assertEqual(vibration_info['min'], 1)
        self.assertEqual(vibration_info['max'], 6)
        
        unknown_info = self.validation_service.get_parameter_info('unknown_param')
        self.assertIsNone(unknown_info)
        
        # Test get_all_parameters
        all_params = self.validation_service.get_all_parameters()
        self.assertIsInstance(all_params, list)
        self.assertIn('vibration', all_params)
        self.assertIn('sensitivity', all_params)
        self.assertIn('heartbeat_interval', all_params)
        self.assertIn('lock_type', all_params)


if __name__ == '__main__':
    unittest.main()