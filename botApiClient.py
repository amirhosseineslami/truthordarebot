import requests, os, dotenv

dotenv.load_dotenv()
TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = f"https://botapi.rubika.ir/v3/{TOKEN}/"
TIMEOUT_CONNECTION_RUBIKA = int(os.environ.get("TIMEOUT_CONNECTION_RUBIKA", "60"))
import time
import logging
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)


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
        response = requests.post(url,json=data,timeout=TIMEOUT_CONNECTION_RUBIKA)
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
        

    def send_message_with_metadata(self, chat_id: str, text: str, metadata_parts: list,
                                disable_notification: bool = False,
                                reply_to_message_id: str = None) -> dict:
        """
        Send a message with rich formatting (bold, italic, underline, strike, links, mentions).

        Args:
            chat_id: Target chat ID.
            text: The message text (plain UTF‑16 string).
            metadata_parts: List of MetadataPart dicts, each must contain:
                - type: one of 'Bold', 'Italic', 'Underline', 'Strike', 'Link', 'MentionText'
                - from_index: start index in the text (UTF‑16)
                - length: length of the affected substring (UTF‑16)
                - link_url: required if type == 'Link'
                - mention_text_user_id: required if type == 'MentionText'
            disable_notification: If True, no notification for the user.
            reply_to_message_id: ID of the message to reply to.

        Returns:
            API response as dict.
        """
        url = BASE_URL + "sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "metadata": {
                "meta_data_parts": metadata_parts
            },
            "disable_notification": disable_notification
        }
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()


    def edit_message_text(self, chat_id: str, message_id: str, text: str,
                        metadata_parts: list = None) -> dict:
        """
        Edit an existing message's text and optionally its metadata.

        Args:
            chat_id: Chat containing the message.
            message_id: ID of the message to edit.
            text: New text for the message.
            metadata_parts: Optional list of MetadataPart dicts.
                        If omitted, existing metadata is removed.
                        To keep existing metadata, you must re‑send the same parts.

        Returns:
            API response as dict.
        """
        url = BASE_URL + "editMessageText"
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        }
        if metadata_parts is not None:
            data["metadata"] = {
                "meta_data_parts": metadata_parts
            }

        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()

