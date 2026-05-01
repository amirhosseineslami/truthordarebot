import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

# ------------------------------
# Enums
# ------------------------------
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

class ChatType(Enum):
    USER = "User"
    GROUP = "Group"
    CHANNEL = "Channel"

# ------------------------------
# Data Models
# ------------------------------
@dataclass
class CallbackQuery:
    callback_id: str
    user_id: str
    chat_id: str
    message_id: str
    data: str          # This is the button's id
    from_user: dict
    chat_instance: str

@dataclass
class Chat:
    """Complete chat information (user, group, channel)"""
    chat_id: str
    chat_type: str
    user_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    member_count: int = 0

    @property
    def display_name(self) -> str:
        if self.chat_type == "User":
            return self.first_name or self.username or self.user_id or self.chat_id
        return self.title or self.username or self.chat_id

    @property
    def full_name(self) -> str:
        if self.chat_type == "User":
            return f"{self.first_name or ''} {self.last_name or ''}".strip() or self.username or self.user_id or self.chat_id
        return self.display_name

    @property
    def is_private(self) -> bool:
        return self.chat_type == "User"

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> 'Chat':
        return cls(
            chat_id=data.get('chat_id', ''),
            chat_type=data.get('chat_type', 'User'),
            user_id=data.get('user_id'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            username=data.get('username'),
            title=data.get('title'),
            description=data.get('description'),
            member_count=data.get('member_count', 0)
        )


@dataclass
class Message:
    """Complete message with optional enriched sender info"""
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
    reply_to_message_id: Optional[str] = None
    file: Optional[Dict] = None
    location: Optional[Dict] = None
    sticker: Optional[Dict] = None
    contact: Optional[Dict] = None
    poll: Optional[Dict] = None

    # Enriched fields (filled after calling enrich_message_with_chat)
    sender_username: Optional[str] = field(default=None, repr=False)
    sender_first_name: Optional[str] = field(default=None, repr=False)
    sender_last_name: Optional[str] = field(default=None, repr=False)
    _chat_info: Optional[Chat] = field(default=None, repr=False)

    # Properties for easy access
    @property
    def time_readable(self) -> str:
        return self.datetime.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def is_private(self) -> bool:
        return self.chat_id.startswith('u')

    @property
    def is_group(self) -> bool:
        return self.chat_id.startswith('g')
    
    @property
    def is_channel(self) -> bool:
        return self.chat_id.startswith('c')
    
    def get_chat_type(self):
        if self.is_group:
            return 'group'
        elif self.is_channel:
            return 'channel'
        else:
            return 'private'

    @property
    def sender_display_name(self) -> str:
        """Best available display name (enriched if possible)"""
        if self.sender_first_name:
            return self.sender_first_name
        if self.sender_username:
            return f"@{self.sender_username}"
        return self.sender_id

    @property
    def sender_full_name(self) -> str:
        if self.sender_first_name:
            return f"{self.sender_first_name} {self.sender_last_name or ''}".strip()
        return self.sender_display_name

    @property
    def preview(self, length: int = 50) -> str:
        if self.text:
            preview = self.text[:length]
            return preview + "..." if len(self.text) > length else preview
        elif self.file:
            return f"[File: {self.file.get('file_name', 'unknown')}]"
        elif self.location:
            return "[Location]"
        elif self.sticker:
            return "[Sticker]"
        return "[Non-text message]"

    def attach_chat_info(self, chat: Chat):
        """Enrich the message with sender details from the chat object"""
        self._chat_info = chat
        if chat.chat_type == "User":
            self.sender_username = chat.username
            self.sender_first_name = chat.first_name
            self.sender_last_name = chat.last_name

    def to_dict(self) -> dict:
        return {
            'message_id': self.message_id,
            'chat_id': self.chat_id,
            'text': self.text,
            'time': self.time_readable,
            'sender_id': self.sender_id,
            'sender_name': self.sender_display_name,
            'sender_username': self.sender_username,
            'is_edited': self.is_edited,
            'preview': self.preview,
        }


@dataclass
class UpdateResponse:
    status: str
    updates: List[Message]
    next_offset_id: Optional[str] = None

    @property
    def has_updates(self) -> bool:
        return len(self.updates) > 0

    @property
    def message_count(self) -> int:
        return len(self.updates)


@dataclass
class ChatInfoResponse:
    status: str
    chat: Optional[Chat] = None

    @property
    def ok(self) -> bool:
        return self.status == "OK" and self.chat is not None


# ------------------------------
# Main Parser Class
# ------------------------------
class RubikaParser:
    @staticmethod
    def _ensure_dict(data):
        """Convert JSON string to dict if needed."""
        if isinstance(data, str):
            try:
                return json.loads(data)
            except:
                return {}
        return data

    @staticmethod
    def parse_updates(response_data: Dict[str, Any]) -> UpdateResponse:
        response_data = RubikaParser._ensure_dict(response_data)
        status = response_data.get('status', 'UNKNOWN')
        data = response_data.get('data', {})
        updates_raw = data.get('updates', [])
        next_offset_id = data.get('next_offset_id')
        messages = []
        for update in updates_raw:
            msg = RubikaParser._parse_single_update(update)
            if msg:
                messages.append(msg)
        return UpdateResponse(status, messages, next_offset_id)

    @staticmethod
    def _parse_single_update(update: Dict[str, Any]) -> Optional[Message]:
        if 'callback_query' in update:
            cq = update['callback_query']
            return CallbackQuery(
                callback_id=cq.get('id', ''),
                user_id=cq.get('from', {}).get('id', ''),
                chat_id=cq.get('message', {}).get('chat', {}).get('id', ''),
                message_id=cq.get('message', {}).get('message_id', ''),
                data=cq.get('data', ''),
                from_user=cq.get('from', {}),
                chat_instance=cq.get('chat_instance', '')
            )

        try:
            update_type = update.get('type')
            chat_id = update.get('chat_id')
            update_time = int(update.get('update_time', 0))
            message_data = update.get('new_message') or update.get('message')
            if not message_data:
                return None
            time_stamp = int(message_data.get('time', 0))
            message_datetime = datetime.fromtimestamp(time_stamp) if time_stamp else None
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

    @staticmethod
    def parse_chat_info(response_data) -> ChatInfoResponse:
        response_data = RubikaParser._ensure_dict(response_data)
        status = response_data.get('status', 'UNKNOWN')
        if status != "OK":
            return ChatInfoResponse(status=status, chat=None)
        data = response_data.get('data', {})
        chat_data = data.get('chat')
        if not chat_data:
            return ChatInfoResponse(status=status, chat=None)
        chat = Chat.from_api(chat_data)
        return ChatInfoResponse(status=status, chat=chat)

    @staticmethod
    def fetch_chat(api_client, chat_id: str, cache: dict = None) -> Optional[Chat]:
        if cache and chat_id in cache:
            return cache[chat_id]
        response = api_client.get_chat_info(chat_id)
        chat = RubikaParser.parse_chat_info(response).chat
        if chat and cache is not None:
            cache[chat_id] = chat
        return chat

    @staticmethod
    def enrich_message_with_chat(api_client, message: Message, cache: dict = None) -> Message:
        chat = RubikaParser.fetch_chat(api_client, message.chat_id, cache)
        if chat:
            message.attach_chat_info(chat)
        return message