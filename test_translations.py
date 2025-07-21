import unittest
from services.i18n_service import I18nService

class TestTranslations(unittest.TestCase):
    """Test the translations for main_server in different languages."""
    
    def test_main_server_translations(self):
        """Test that main_server is correctly translated in all languages."""
        # Test Portuguese translation
        i18n_pt = I18nService('pt_BR')
        self.assertEqual(i18n_pt.get('main_server'), 'Servidor Principal', 
                         "main_server should be 'Servidor Principal' in Portuguese")
        
        # Test English translation
        i18n_en = I18nService('en_US')
        self.assertEqual(i18n_en.get('main_server'), 'Main Server', 
                         "main_server should be 'Main Server' in English")
        
        # Test Spanish translation
        i18n_es = I18nService('es_ES')
        self.assertEqual(i18n_es.get('main_server'), 'Servidor Principal', 
                         "main_server should be 'Servidor Principal' in Spanish")
        
        print("Main server translations test passed!")
        print(f"Portuguese: {i18n_pt.get('main_server')}")
        print(f"English: {i18n_en.get('main_server')}")
        print(f"Spanish: {i18n_es.get('main_server')}")

if __name__ == "__main__":
    unittest.main()