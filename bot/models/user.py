# models/user.py
import json
from peewee import CharField, IntegerField, BigIntegerField, BooleanField, TextField
from .base import BaseModel   # ensure BaseModel is imported

class User(BaseModel):
    """
    User model for bottle game - stores all user-related data
    """
    
    __tablename__ = 'users'

    # Identification Fields
    user_id = CharField(max_length=100, unique=True, index=True)
    username = CharField(max_length=100, null=True, index=True)
    first_name = CharField(max_length=255, null=True)
    last_name = CharField(max_length=255, null=True)
    chat_id = CharField(max_length=100, index=True)

    # Game Related Fields
    coin = IntegerField(default=0)
    score = IntegerField(default=0)
    level = IntegerField(default=1)
    game_state = TextField(default='{}')  # Store JSON as string
    blocked_users = TextField(default='[]')  # JSON list of blocked user chat_ids
    
    # User Preferences
    sex = IntegerField(default=0)  # 0: unknown, 1: male, 2: female
    language = CharField(max_length=10, default='fa')
    age = IntegerField(null=True)          # Age in years
    city = CharField(max_length=100, null=True)   # City name
    
    # Subscription & Status
    subscription_date = BigIntegerField(default=0)
    is_active = BooleanField(default=False)
    is_banned = BooleanField(default=False)
    
    # Statistics
    total_games_played = IntegerField(default=0)
    total_wins = IntegerField(default=0)
    total_losses = IntegerField(default=0)
    total_messages = IntegerField(default=0)
    last_seen = BigIntegerField(default=0)
    
    @property
    def full_name(self) -> str:
        if self.first_name:
            return f"{self.first_name} {self.last_name or ''}".strip()
        return self.username or self.user_id
    
    @property
    def display_name(self) -> str:
        if self.first_name:
            return self.first_name
        if self.username:
            return f"@{self.username}"
        return self.user_id
    
    @property
    def win_rate(self) -> float:
        if self.total_games_played == 0:
            return 0.0
        return (self.total_wins / self.total_games_played) * 100
    
    @property
    def is_subscribed(self) -> bool:
        import time
        return self.subscription_date > int(time.time())
    
    @property
    def game_state_dict(self) -> dict:
        try:
            return json.loads(self.game_state) if self.game_state else {}
        except:
            return {}
    
    def add_coins(self, amount: int) -> int:
        self.coin += amount
        self.save()
        return self.coin
    
    def save(self, *args, **kwargs):
        self.is_dirty = True
        return super().save(*args, **kwargs)
    
    def remove_coins(self, amount: int) -> bool:
        if self.coin >= amount:
            self.coin -= amount
            self.save()
            return True
        return False
    
    def has_enough_coins(self, amount: int) -> bool:
        return self.coin >= amount
    
    def add_score(self, points: int) -> int:
        self.score += points
        new_level = (self.score // 1000) + 1
        if new_level > self.level:
            self.level = new_level
        self.save()
        return self.score
    
    def get_score_to_next_level(self) -> int:
        next_level_threshold = self.level * 1000
        return next_level_threshold - self.score
    
    def record_game_result(self, won: bool):
        self.total_games_played += 1
        if won:
            self.total_wins += 1
        else:
            self.total_losses += 1
        self.save()
    
    def record_message(self):
        self.total_messages += 1
        self.save()
    
    def update_last_seen(self):
        import time
        self.last_seen = int(time.time())
        self.save()
    
    def extend_subscription(self, days: int):
        import time
        current = self.subscription_date if self.subscription_date > int(time.time()) else int(time.time())
        self.subscription_date = current + (days * 86400)
        self.save()
    
    def get_subscription_days_left(self) -> int:
        import time
        if not self.is_subscribed:
            return 0
        remaining = self.subscription_date - int(time.time())
        return max(0, remaining // 86400)
    
    def update_game_state(self, key: str, value):
        state = self.game_state_dict
        state[key] = value
        self.game_state = json.dumps(state)
        self.save()
    
    def get_game_state(self, key: str, default=None):
        return self.game_state_dict.get(key, default)
    
    def clear_game_state(self):
        self.game_state = '{}'
        self.save()
    
    def set_game_state_dict(self, state: dict):
        self.game_state = json.dumps(state)
        self.save()

    @property
    def blocked_users_list(self) -> list:
        try:
            return json.loads(self.blocked_users) if self.blocked_users else []
        except:
            return []

    def block_user(self, chat_id_to_block: str) -> bool:
        blocked = self.blocked_users_list
        if chat_id_to_block not in blocked:
            blocked.append(chat_id_to_block)
            self.blocked_users = json.dumps(blocked)
            self.save()
            return True
        return False

    def unblock_user(self, chat_id_to_unblock: str) -> bool:
        blocked = self.blocked_users_list
        if chat_id_to_unblock in blocked:
            blocked.remove(chat_id_to_unblock)
            self.blocked_users = json.dumps(blocked)
            self.save()
            return True
        return False

    def is_blocked(self, chat_id_to_check: str) -> bool:
        return chat_id_to_check in self.blocked_users_list
    
    def ban(self):
        self.is_banned = True
        self.is_active = False
        self.save()
    
    def unban(self):
        self.is_banned = False
        self.is_active = True
        self.save()
    
    def deactivate(self):
        self.is_active = False
        self.save()
    
    def activate(self):
        self.is_active = True
        self.save()
    
    def to_dict(self, detailed: bool = False) -> dict:
        result = {
            'user_id': self.user_id,
            'username': self.username,
            'display_name': self.display_name,
            'full_name': self.full_name,
            'chat_id': self.chat_id,
            'coin': self.coin,
            'score': self.score,
            'level': self.level,
        }
        if detailed:
            result.update({
                'first_name': self.first_name,
                'last_name': self.last_name,
                'sex': self.sex,
                'language': self.language,
                'is_active': self.is_active,
                'is_banned': self.is_banned,
                'is_subscribed': self.is_subscribed,
                'subscription_days_left': self.get_subscription_days_left(),
                'total_games_played': self.total_games_played,
                'total_wins': self.total_wins,
                'total_losses': self.total_losses,
                'win_rate': round(self.win_rate, 2),
                'total_messages': self.total_messages,
                'last_seen': self.last_seen,
                'game_state': self.game_state_dict,
                'blocked_users': self.blocked_users_list,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            })
        return result
    
    @classmethod
    def create_new(cls, user_id: str, chat_id: str, username: str = None, 
                   first_name: str = None, last_name: str = None) -> 'User':
        return cls.create(
            user_id=user_id,
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            coin=100,
            score=0,
            level=1,
            game_state='{}',
            sex=0,
            language='fa',
            subscription_date=0,
            is_active=True,
            is_banned=False,
            total_games_played=0,
            total_wins=0,
            total_losses=0,
            total_messages=0,
            last_seen=0
        )
    
    @classmethod
    def get_or_create_user(cls, user_id: str, chat_id: str, **kwargs) -> tuple:
        user, created = cls.get_or_create(
            user_id=user_id,
            chat_id=chat_id,
            defaults={
                'username': kwargs.get('username'),
                'first_name': kwargs.get('first_name'),
                'last_name': kwargs.get('last_name'),
                'coin': kwargs.get('coin', 100),
                'language': kwargs.get('language', 'fa'),
                'game_state': '{}'
            }
        )
        return user, created
    
    def __str__(self):
        return f"User(id={self.user_id}, name={self.display_name}, coins={self.coin}, level={self.level})"
    
    def __repr__(self):
        return self.__str__()