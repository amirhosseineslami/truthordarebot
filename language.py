import json
import os

class LanguageManager:
    def __init__(self, locales_dir="locales"):
        self.locales_dir = locales_dir
        self.translations = {}
        self.load_all_languages()
    
    def load_all_languages(self):
        """Load all language JSON files"""
        for file in os.listdir(self.locales_dir):
            if file.endswith('.json'):
                lang_code = file.replace('.json', '')
                with open(f"{self.locales_dir}/{file}", 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)
    
    def get_text(self, key, lang='fa', **kwargs):
        """Get translated text by key"""
        # Default to Persian if language not found
        text = self.translations.get(lang, self.translations.get('fa', {})).get(key, key)
        
        # Replace placeholders (e.g., {score})
        for key, value in kwargs.items():
            text = text.replace(f"{{{key}}}", str(value))
        
        return text

# Create global instance
lang = LanguageManager()