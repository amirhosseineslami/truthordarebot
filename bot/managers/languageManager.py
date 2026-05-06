import json
import os
from pathlib import Path

class LanguageManager:
    def __init__(self, locales_dir="locales"):

        
        # Get the directory where THIS file is located
        # This file is at: .../bot/managers/languageManager.py
        current_dir = Path(__file__).parent  # This gives .../bot/managers/
        
        # Go up one level to bot/ directory
        bot_dir = current_dir.parent  # This gives .../bot/
        
        # Now look for locales in bot/
        self.locales_dir = str(bot_dir / locales_dir)  # .../bot/locales
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