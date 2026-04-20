import json
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import time
import requests
from botApiClient import BotApiClient


apiClient = BotApiClient()


# Enums for type safety
class MessageSenderType(Enum):
    USER = "User"
    BOT = "Bot"
    GROUP = "Group"
    CHANNEL = "Channel"

class UpdateType(Enum):
    NEW_MESSAGE = "NewMessage"
    EDIT_MESSAGE = "EditMessage"
    DELETE_MESSAGE = "DeleteMessage"
    INLINE_MESSAGE = "InlineMessage"

@dataclass
class Message:
    """Clean representation of a Rubika message"""
    message_id: str
    text: str
    time: int
    datetime: datetime
    is_edited: bool
    sender_type: str
    sender_id: str
    chat_id: str
    update_type: str
    update_time: int
    
    # Optional fields (None if not present)
    reply_to_message_id: Optional[str] = None
    file: Optional[Dict] = None
    location: Optional[Dict] = None
    sticker: Optional[Dict] = None
    contact: Optional[Dict] = None
    poll: Optional[Dict] = None
    
    @property
    def time_readable(self) -> str:
        """Get human-readable time"""
        return self.datetime.strftime("%Y-%m-%d %H:%M:%S")
    
    @property
    def is_private(self) -> bool:
        """Check if message is from private chat"""
        return self.chat_id.startswith('u')
    
    @property
    def is_group(self) -> bool:
        """Check if message is from group"""
        return self.chat_id.startswith('g')

@dataclass
class UpdateResponse:
    """Clean representation of the entire API response"""
    status: str
    updates: List[Message]
    next_offset_id: Optional[str] = None
    
    @property
    def has_updates(self) -> bool:
        return len(self.updates) > 0
    
    @property
    def message_count(self) -> int:
        return len(self.updates)

class RubikaMessageParser:
    """Clean parser for Rubika API responses"""
    
    def __init__(self):
        self.raw_response = None
        self.parsed_response = None
    
    def parse_response(self, response_data: Dict[str, Any]) -> UpdateResponse:
        """
        Parse raw API response into clean UpdateResponse object
        
        Args:
            response_data: Raw JSON response from Rubika API
            
        Returns:
            UpdateResponse with clean message objects
        """
        self.raw_response = response_data
        
        status = response_data.get('status', 'UNKNOWN')
        data = response_data.get('data', {})
        updates_raw = data.get('updates', [])
        next_offset_id = data.get('next_offset_id')
        
        parsed_messages = []
        
        for update in updates_raw:
            message = self._parse_single_update(update)
            if message:
                parsed_messages.append(message)
        
        self.parsed_response = UpdateResponse(
            status=status,
            updates=parsed_messages,
            next_offset_id=next_offset_id
        )
        
        return self.parsed_response
    
    def _parse_single_update(self, update: Dict[str, Any]) -> Optional[Message]:
        """Parse a single update object into a Message object"""
        try:
            update_type = update.get('type')
            chat_id = update.get('chat_id')
            update_time = int(update.get('update_time', 0))
            
            # Get the message data (could be in 'new_message' or 'message' field)
            message_data = update.get('new_message') or update.get('message')
            
            if not message_data:
                return None
            
            # Parse time
            time_stamp = int(message_data.get('time', 0))
            message_datetime = datetime.fromtimestamp(time_stamp) if time_stamp else None
            
            # Create clean Message object
            return Message(
                message_id=message_data.get('message_id', ''),
                text=message_data.get('text', ''),
                time=time_stamp,
                datetime=message_datetime,
                is_edited=message_data.get('is_edited', False),
                sender_type=message_data.get('sender_type', ''),
                sender_id=message_data.get('sender_id', ''),
                chat_id=chat_id,
                update_type=update_type,
                update_time=update_time,
                reply_to_message_id=message_data.get('reply_to_message_id'),
                file=message_data.get('file'),
                location=message_data.get('location'),
                sticker=message_data.get('sticker'),
                contact=message_data.get('contact_message'),
                poll=message_data.get('poll')
            )
            
        except Exception as e:
            print(f"Error parsing update: {e}")
            return None
    
    def get_text_messages(self) -> List[Message]:
        """Get only text messages"""
        if not self.parsed_response:
            return []
        return [msg for msg in self.parsed_response.updates if msg.text]
    
    def get_messages_from_user(self, user_id: str) -> List[Message]:
        """Get messages from specific user"""
        if not self.parsed_response:
            return []
        return [msg for msg in self.parsed_response.updates if msg.sender_id == user_id]
    
    def get_messages_from_chat(self, chat_id: str) -> List[Message]:
        """Get messages from specific chat"""
        if not self.parsed_response:
            return []
        return [msg for msg in self.parsed_response.updates if msg.chat_id == chat_id]
    
    def print_clean_summary(self):
        """Print a clean summary of all messages"""
        if not self.parsed_response:
            print("No parsed response available")
            return
        
        print(f"\n{'='*60}")
        print(f"📊 UPDATE SUMMARY")
        print(f"{'='*60}")
        print(f"Status: {self.parsed_response.status}")
        print(f"Total Messages: {self.parsed_response.message_count}")
        print(f"Next Offset: {self.parsed_response.next_offset_id}")
        print(f"{'='*60}\n")
        
        for i, msg in enumerate(self.parsed_response.updates, 1):
            print(f"📨 Message {i}:")
            print(f"   ├─ Chat ID: {msg.chat_id}")
            print(f"   ├─ From: {msg.sender_type} ({msg.sender_id})")
            print(f"   ├─ Text: {msg.text[:50] if msg.text else '[No Text]'}")
            print(f"   ├─ Time: {msg.time_readable}")
            print(f"   ├─ Message ID: {msg.message_id}")
            print(f"   └─ Is Edited: {msg.is_edited}")
            print()

# Simplified parser for quick use
class SimpleMessageParser:
    """Even simpler parser for quick message extraction"""
    
    @staticmethod
    def get_messages(response_data: Dict) -> List[Dict]:
        """Extract just the essential message data"""
        messages = []
        
        data = response_data.get('data', {})
        updates = data.get('updates', [])
        
        for update in updates:
            message_data = update.get('new_message') or update.get('message')
            if message_data:
                messages.append({
                    'chat_id': update.get('chat_id'),
                    'text': message_data.get('text', ''),
                    'sender_id': message_data.get('sender_id'),
                    'sender_type': message_data.get('sender_type'),
                    'time': message_data.get('time'),
                    'message_id': message_data.get('message_id')
                })
        
        return messages
    
    @staticmethod
    def get_last_message(response_data: Dict) -> Optional[Dict]:
        """Get only the last message"""
        messages = SimpleMessageParser.get_messages(response_data)
        return messages[-1] if messages else None
    
    @staticmethod
    def get_texts(response_data: Dict) -> List[str]:
        """Get just the text content of all messages"""
        messages = SimpleMessageParser.get_messages(response_data)
        return [msg['text'] for msg in messages if msg['text']]

# Example usage in your bot
def example_usage(messery_response):
    """Example of how to use the parser"""
    
    # Your messy JSON response
    messy_response = {
        'status': 'OK',
        'data': {
            'updates': [
                {
                    'type': 'NewMessage',
                    'chat_id': 'b0JpYX406Cx0a7d9c3afc07c381d452a',
                    'new_message': {
                        'message_id': '1642537411795972643',
                        'text': 'hi',
                        'time': '1776586429',
                        'is_edited': False,
                        'sender_type': 'User',
                        'sender_id': 'u0JpYX40c61685528a9fbb190913b0a2'
                    },
                    'update_time': 1776586430
                }
            ],
            'next_offset_id': '69e48ebe8566d54939935bcd'
        }
    }
    
    # Method 1: Using the full parser
    print("🔵 FULL PARSER EXAMPLE:")
    parser = RubikaMessageParser()
    parsed = parser.parse_response(messery_response)
    
    # Print clean summary
    parser.print_clean_summary()
    
    # Access messages easily
    for message in parsed.updates:
        print(f"User {message.sender_id} said: {message.text}")
        print(f"At: {message.time_readable}")
        print(f"Chat: {message.chat_id}")
        print(f"Is private: {message.is_private}")
        print()
    
    # Method 2: Using the simple parser
    print("\n🔵 SIMPLE PARSER EXAMPLE:")
    texts = SimpleMessageParser.get_texts(messy_response)
    print(f"All texts: {texts}")
    
    last_msg = SimpleMessageParser.get_last_message(messy_response)
    print(f"Last message: {last_msg}")
    
    # Method 3: Get messages by type
    print("\n🔵 FILTERED MESSAGES:")
    user_messages = parser.get_messages_from_user('u0JpYX40c61685528a9fbb190913b0a2')
    print(f"Messages from specific user: {len(user_messages)}")
    
    chat_messages = parser.get_messages_from_chat('b0JpYX406Cx0a7d9c3afc07c381d452a')
    print(f"Messages in specific chat: {len(chat_messages)}")
    
    text_messages = parser.get_text_messages()
    print(f"Text messages only: {len(text_messages)}")

# Integration with your bot
def simple_bot_integration(token):
    """Simple example of integrating with your bot"""
    
    # Your existing bot code
    url = f"https://botapi.rubika.ir/v3/{token}/"
    last_update_id = 0
    
    parser = RubikaMessageParser()
    
    while True:
        try:
            response = requests.post(url + "getUpdates", json={"offset": last_update_id})
            data = response.json()
            
            # Parse the messy response into clean objects
            parsed_response = parser.parse_response(data)
            
            if parsed_response.has_updates:
                for message in parsed_response.updates:
                    print(f"\n✅ Received clean message:")
                    print(f"   Chat: {message.chat_id}")
                    print(f"   From: {message.sender_id}")
                    print(f"   Text: {message.text}")
                    
                    # Simple command handling
                    if message.text == "/start":
                        apiClient.send_message(message.chat_id, "Welcome to the game! 🎮")
                    elif message.text == "/help":
                        apiClient.send_message(message.chat_id, "Available commands: /start, /help")
                    else:
                        apiClient.send_message(message.chat_id, f"You said: {message.text}")
                    
                    last_update_id = int(message.update_time) + 1
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    example_usage()