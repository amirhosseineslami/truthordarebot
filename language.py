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
        data = self.translations.get(lang, self.translations.get('fa', {}))
        value = data.get(key, key)
        
        # اگر مقدار لیست بود، یک عضو تصادفی انتخاب کن
        if isinstance(value, list):
            import random
            value = random.choice(value)
        
        # Replace placeholders
        for k, v in kwargs.items():
            value = value.replace(f"{{{k}}}", str(v))
        
        return value

# Create global instance
lang = LanguageManager()