import unittest
from services.i18n_service import I18nService
from services.validation_service import ValidationService

class TestServerIpValidation(unittest.TestCase):
    """Test the server_ip validation."""
    
    def setUp(self):
        """Set up the test environment."""
        self.i18n = I18nService()
        self.validation_service = ValidationService(self.i18n)
    
    def test_valid_ip_addresses(self):
        """Test that valid IP addresses pass validation."""
        valid_ips = [
            '192.168.1.1',
            '10.0.0.1',
            '172.16.0.1',
            '255.255.255.255',
            '0.0.0.0'
        ]
        
        for ip in valid_ips:
            result = self.validation_service.validate_parameter('server_ip', ip)
            self.assertTrue(result.is_valid, f"IP address {ip} should be valid")
        
        print("Valid IP addresses test passed!")
    
    def test_valid_urls(self):
        """Test that valid URLs pass validation."""
        valid_urls = [
            'example.com',
            'sub.example.com',
            'sub-domain.example.com',
            'example.co.uk',
            'example-domain.com'
        ]
        
        for url in valid_urls:
            result = self.validation_service.validate_parameter('server_ip', url)
            self.assertTrue(result.is_valid, f"URL {url} should be valid")
        
        print("Valid URLs test passed!")
    
    def test_invalid_inputs(self):
        """Test that invalid inputs fail validation."""
        invalid_inputs = [
            'invalid url',  # Contains space
            'invalid@url',  # Contains @
            '192.168.1',    # Incomplete IP
            '192.168.1.300',  # Invalid IP (300 > 255)
            'http://example.com',  # Contains protocol
            'example.com/path',  # Contains path
            '-example.com',  # Starts with hyphen
            'example-.com',  # Ends with hyphen
            'example..com',  # Double dot
        ]
        
        for input_value in invalid_inputs:
            result = self.validation_service.validate_parameter('server_ip', input_value)
            self.assertFalse(result.is_valid, f"Input {input_value} should be invalid")
            self.assertEqual(result.error_code, 'INVALID_SERVER_URL_IP', f"Error code for {input_value} should be INVALID_SERVER_URL_IP")
        
        # Test empty string separately (should be REQUIRED_FIELD)
        result = self.validation_service.validate_parameter('server_ip', '')
        self.assertFalse(result.is_valid, "Empty string should be invalid")
        self.assertEqual(result.error_code, 'REQUIRED_FIELD', "Error code for empty string should be REQUIRED_FIELD")
        
        print("Invalid inputs test passed!")
    
    def test_error_message(self):
        """Test that the error message is correct."""
        result = self.validation_service.validate_parameter('server_ip', 'invalid url')
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_code, 'INVALID_SERVER_URL_IP')
        self.assertIn('URL ou endereço IP válido', result.error_message, "Error message should mention URL or IP address")
        
        print("Error message test passed!")
        print(f"Error message: {result.error_message}")

if __name__ == "__main__":
    unittest.main()