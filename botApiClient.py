import requests, os, dotenv

dotenv.load_dotenv()
TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = f"https://botapi.rubika.ir/v3/{TOKEN}/"

class BotApiClient:

    def send_message(self, chat_id:str, text: str, disable_notification:bool = False, reply_to_message_id : str | None = None) -> dict:
        """Sends a text message to a chat"""

        # cofigure the data that's gonne be sent
        data = {
            "chat_id" : chat_id,
            "text" : text,
            "disable_notification" : disable_notification,
        }
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        # The url to send the request to
        url = BASE_URL + f'sendMessage'
        
        # Let's now send the post request
        response = requests.post(url,json=data)
        response.raise_for_status()
        return response.json()
    
    

    def get_updates(self, offset_id:str|None = None, limit:int = 100) -> dict:

        """Gets updates from the bot API"""
        params = {
            "limit" : limit,
        }
        if offset_id:
            params["offset_id"] = offset_id
        
        url = BASE_URL + "getUpdates"
        response = requests.post(url=url, json=params)
        response.raise_for_status()
        return response.json()
    

    def delete_message(self, chat_id:str, message_id:str)->dict:

        data = {
            "chat_id" : chat_id,
            "message_id" : message_id
        }

        url = BASE_URL + f"deleteMessage"

        response = requests.post(url,json=data)
        response.raise_for_status()
        return response.json()
    

    def get_chat_info(self, chat_id:str)->dict:
        data = {
            "chat_id" : chat_id
        }
        url = BASE_URL + "getChat"
        response = requests.post(url,json=data)
        response.raise_for_status()
        return response.text
        

