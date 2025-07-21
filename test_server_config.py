import unittest
from services.i18n_service import I18nService

class TestServerConfig(unittest.TestCase):
    """Test the server configuration translations."""
    
    def setUp(self):
        """Set up the test environment."""
        self.i18n = I18nService()
    
    def test_server_translations(self):
        """Test that the server translations are correctly defined."""
        # Check that the main server translation exists
        main_server = self.i18n.get("main_server")
        self.assertNotEqual(main_server, "_main_server_", "Main server translation not found")
        self.assertEqual(main_server, "Servidor Principal", "Main server translation incorrect")
        
        # Check that the URL/IP translation exists
        server_url_ip = self.i18n.get("server_url_ip")
        self.assertNotEqual(server_url_ip, "_server_url_ip_", "Server URL/IP translation not found")
        self.assertEqual(server_url_ip, "URL/IP:", "Server URL/IP translation incorrect")
        
        print("Server translations test passed!")
        print(f"Main server translation: {main_server}")
        print(f"Server URL/IP translation: {server_url_ip}")

if __name__ == "__main__":
    unittest.main()