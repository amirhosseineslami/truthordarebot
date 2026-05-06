import requests, os, dotenv
import time
import logging
from requests.exceptions import RequestException, Timeout, ConnectionError

dotenv.load_dotenv()
TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = f"https://botapi.rubika.ir/v3/{TOKEN}/"
TIMEOUT_CONNECTION_RUBIKA = int(os.environ.get("TIMEOUT_CONNECTION_RUBIKA", "60"))
MAX_RETRIES_TO_RUBIKA = int(os.environ.get("MAX_RETRIES_TO_RUBIKA", "3"))

logger = logging.getLogger(__name__)


class BotApiClient:
    
    def _request_with_retry(self, url: str, data: dict, method: str = "POST", 
                           max_retries: int = MAX_RETRIES_TO_RUBIKA) -> dict:
        """
        Internal method to make HTTP requests with automatic retries and exponential backoff.
        """
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                if method.upper() == "POST":
                    response = requests.post(url, json=data, timeout=TIMEOUT_CONNECTION_RUBIKA)
                else:
                    response = requests.get(url, json=data, timeout=TIMEOUT_CONNECTION_RUBIKA)
                
                response.raise_for_status()
                
                # Return JSON if response is JSON, otherwise return text
                try:
                    return response.json()
                except:
                    return {"response": response.text}
                    
            except (RequestException, Timeout, ConnectionError) as e:
                last_exception = e
                logger.warning(f"Attempt {attempt}/{max_retries} failed for {url}: {e}")
                
                # Only retry on server errors (5xx) or network issues
                if hasattr(e, 'response') and e.response is not None:
                    if e.response.status_code < 500:
                        # Don't retry on client errors (4xx)
                        raise e
                
                if attempt < max_retries:
                    # Exponential backoff: 1s, 2s, 4s, 8s...
                    sleep_time = 2 ** (attempt - 1)
                    time.sleep(sleep_time)
        
        # All attempts exhausted
        raise Exception(f"Request failed after {max_retries} attempts. Last error: {last_exception}")

    # ============================================
    # Core Methods with Retry Logic
    # ============================================
    
    def send_message(self, chat_id: str, text: str, disable_notification: bool = False,
                    reply_to_message_id: str | None = None, max_retries: int = MAX_RETRIES_TO_RUBIKA) -> dict:
        """
        Sends a text message to a chat with automatic retries.
        """
        data = {
            "chat_id": chat_id,
            "text": text,
            "disable_notification": disable_notification,
        }
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        url = BASE_URL + 'sendMessage'
        return self._request_with_retry(url, data, max_retries=max_retries)

    def get_updates(self, offset_id: str | None = None, limit: int = 100, 
                   max_retries: int = MAX_RETRIES_TO_RUBIKA) -> dict:
        """
        Gets updates from the bot API with retries.
        """
        params = {"limit": limit}
        if offset_id:
            params["offset_id"] = offset_id
        
        url = BASE_URL + "getUpdates"
        return self._request_with_retry(url, params, max_retries=max_retries)

    def delete_message(self, chat_id: str, message_id: str, 
                      max_retries: int = MAX_RETRIES_TO_RUBIKA) -> dict:
        """
        Deletes a message with retries.
        """
        data = {
            "chat_id": chat_id,
            "message_id": message_id
        }
        url = BASE_URL + "deleteMessage"
        return self._request_with_retry(url, data, max_retries=max_retries)

    def get_chat_info(self, chat_id: str, max_retries: int = MAX_RETRIES_TO_RUBIKA) -> dict:
        """
        Gets chat information with retries.
        Returns dict (converts text response to dict if needed).
        """
        data = {"chat_id": chat_id}
        url = BASE_URL + "getChat"
        result = self._request_with_retry(url, data, max_retries=max_retries)
        
        # If result is dict with 'response' key (from text response), parse it
        if isinstance(result, dict) and 'response' in result and isinstance(result['response'], str):
            import json
            try:
                return json.loads(result['response'])
            except:
                return result
        return result

    def send_message_with_metadata(self, chat_id: str, text: str, metadata_parts: list,
                                   disable_notification: bool = False,
                                   reply_to_message_id: str = None,
                                   max_retries: int = MAX_RETRIES_TO_RUBIKA) -> dict:
        """
        Send a message with rich formatting (bold, italic, underline, strike, links, mentions).
        """
        url = BASE_URL + "sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "metadata": {"meta_data_parts": metadata_parts},
            "disable_notification": disable_notification
        }
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        return self._request_with_retry(url, data, max_retries=max_retries)

    def edit_message_text(self, chat_id: str, message_id: str, text: str,
                          metadata_parts: list = None,
                          max_retries: int = MAX_RETRIES_TO_RUBIKA) -> dict:
        """
        Edit an existing message's text and optionally its metadata.
        """
        url = BASE_URL + "editMessageText"
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        }
        if metadata_parts is not None:
            data["metadata"] = {"meta_data_parts": metadata_parts}

        return self._request_with_retry(url, data, max_retries=max_retries)

    # ============================================
    # Optional: Batch Send Messages
    # ============================================
    
    def send_batch_messages(self, messages: list, max_retries: int = MAX_RETRIES_TO_RUBIKA) -> list:
        """
        Send multiple messages sequentially (or you could use threading).
        Each message should be a dict with keys: chat_id, text, etc.
        """
        results = []
        for msg in messages:
            try:
                result = self.send_message(
                    chat_id=msg['chat_id'],
                    text=msg['text'],
                    disable_notification=msg.get('disable_notification', False),
                    reply_to_message_id=msg.get('reply_to_message_id'),
                    max_retries=max_retries
                )
                results.append({'success': True, 'result': result})
            except Exception as e:
                results.append({'success': False, 'error': str(e)})
        return results