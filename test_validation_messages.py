import unittest
from services.i18n_service import I18nService
from services.validation_service import ValidationService

class TestValidationMessages(unittest.TestCase):
    """Test the validation messages for server_ip and server_port."""
    
    def setUp(self):
        """Set up the test environment."""
        self.i18n = I18nService('pt_BR')  # Force Portuguese language
        self.validation_service = ValidationService(self.i18n)
    
    def test_server_ip_message(self):
        """Test that the server_ip validation message uses the translated name."""
        # Test with an invalid URL/IP
        result = self.validation_service.validate_parameter('server_ip', 'invalid url')
        self.assertFalse(result.is_valid)
        
        # Check that the error message uses "URL/IP" instead of "server_ip"
        self.assertIn('URL/IP', result.error_message)
        self.assertNotIn('server_ip', result.error_message)
        
        print("Server IP message test passed!")
        print(f"Error message: {result.error_message}")
    
    def test_server_port_message(self):
        """Test that the server_port validation message uses the translated name."""
        # Test with an invalid port number
        result = self.validation_service.validate_parameter('server_port', '999999')
        self.assertFalse(result.is_valid)
        
        # Check that the error message uses "Porta do Servidor" instead of "server_port"
        self.assertIn('Porta do Servidor', result.error_message)
        self.assertNotIn('server_port', result.error_message)
        
        print("Server port message test passed!")
        print(f"Error message: {result.error_message}")

if __name__ == "__main__":
    unittest.main()