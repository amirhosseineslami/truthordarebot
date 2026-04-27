import requests
import json
from datetime import datetime # برای ساخت id های منحصر به فرد یا timestamp
import os
import dotenv

dotenv.load_dotenv()


# فرض کنید اینها از قبل تعریف شده‌اند
TOKEN = os.environ.get("BOT_TOKEN")

class Keypad():

    def create_simple_button(self, button_id, button_text):
        """یک دکمه ساده (Simple Button) برای کیبورد روبیکا می‌سازد."""
        return {
            "id": str(button_id), # اطمینان حاصل کنید که id رشته است
            "type": "Simple",
            "button_text": button_text
        }

    def create_keypad_row(self, buttons_list):
        """یک ردیف از دکمه‌ها برای کیبورد می‌سازد."""
        return {
            "buttons": buttons_list
        }

    def build_keypad(self, rows_data, resize_keyboard=True, one_time_keyboard=False):
        """کل ساختار chat_keypad را می‌سازد."""
        return {
            "rows": rows_data,
            "resize_keyboard": resize_keyboard,
            "one_time_keyboard": one_time_keyboard
        }
    

    def edit_chat_keypad(self, chat_id, keypad_data):
        """کیپد چت را عوض می کند."""
        url = f"https://botapi.rubika.ir/v3/{TOKEN}/editChatKeypad"
        data = {
            "chat_id": chat_id,
            "chat_keypad_type": "New", # یا "Old" بسته به نسخه API یا نیاز شما
            "chat_keypad": keypad_data
        }
        headers = {
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status() # خطاهای HTTP را بررسی می‌کند
            print(f"Message sent successfully to {chat_id}. Response: {response.text}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error sending message: {e}")
            return None


    def send_message_with_keypad(self, chat_id, text, keypad_data):
        """یک پیام با کیبورد مشخص ارسال می‌کند."""
        url = f"https://botapi.rubika.ir/v3/{TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "chat_keypad_type": "New", # یا "Old" بسته به نسخه API یا نیاز شما
            "chat_keypad": keypad_data
        }
        headers = {
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status() # خطاهای HTTP را بررسی می‌کند
            print(f"Message sent successfully to {chat_id}. Response: {response.text}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error sending message: {e}")
            return None

    def send_message_with_inline_keypad(self, chat_id, text, inline_keypad_data):
        """Send a message with an inline keyboard (buttons under the message)."""
        url = f"https://botapi.rubika.ir/v3/{TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "inline_keypad": inline_keypad_data   # key difference: inline_keypad
        }
        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            print(f"Inline keypad message sent to {chat_id}. Response: {response.text}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error sending inline keypad message: {e}")
            return None