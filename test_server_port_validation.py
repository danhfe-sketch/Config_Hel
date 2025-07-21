import unittest
from services.i18n_service import I18nService
from services.validation_service import ValidationService

class TestServerPortValidation(unittest.TestCase):
    """Test the server_port validation."""
    
    def setUp(self):
        """Set up the test environment."""
        self.i18n = I18nService('pt_BR')  # Use Portuguese for testing
        self.validation_service = ValidationService(self.i18n)
    
    def test_valid_port_numbers(self):
        """Test that valid port numbers pass validation."""
        valid_ports = [
            '1',      # Minimum valid port
            '80',     # HTTP port
            '443',    # HTTPS port
            '8080',   # Common alternative HTTP port
            '65535'   # Maximum valid port
        ]
        
        for port in valid_ports:
            result = self.validation_service.validate_parameter('server_port', port)
            self.assertTrue(result.is_valid, f"Port {port} should be valid")
        
        print("Valid port numbers test passed!")
    
    def test_invalid_port_numbers(self):
        """Test that invalid port numbers fail validation."""
        invalid_ports = [
            '0',       # Below minimum (1)
            '65536',   # Above maximum (65535)
            '70000',   # Way above maximum
            '-1',      # Negative number
            'abc',     # Non-numeric
            '12.34'    # Non-integer
        ]
        
        for port in invalid_ports:
            result = self.validation_service.validate_parameter('server_port', port)
            self.assertFalse(result.is_valid, f"Port {port} should be invalid")
            
            # Check that the error code is one of the expected validation error codes
            self.assertIn(result.error_code, ['RANGE_ERROR', 'MIN_VALUE', 'MAX_VALUE', 'NUMERIC_REQUIRED', 'INTEGER_REQUIRED', 'REQUIRED_FIELD'], 
                         f"Error code for {port} should be a valid validation error code")
        
        print("Invalid port numbers test passed!")
    
    def test_error_messages(self):
        """Test that the error messages are correct."""
        # Test out of range
        result = self.validation_service.validate_parameter('server_port', '65536')
        self.assertFalse(result.is_valid)
        self.assertIn('deve ser no máximo 65535', result.error_message)
        
        # Test non-numeric
        result = self.validation_service.validate_parameter('server_port', 'abc')
        self.assertFalse(result.is_valid)
        self.assertIn('deve ser um valor numérico', result.error_message)
        
        print("Error messages test passed!")
        print(f"Below minimum error: {result.error_message}")

if __name__ == "__main__":
    unittest.main()