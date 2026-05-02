# sync_manager.py
import json
import time
import threading
import atexit
from typing import Optional, List, Dict, Any
from peewee import SqliteDatabase, Model, CharField, IntegerField, BigIntegerField, BooleanField, TextField
from playhouse.shortcuts import model_to_dict
from models.user import User as RemoteUser
from database import db as remote_db   # your MySQL connection

# -------------------------------------------------------------------
# Local SQLite database and LocalUser model (mirrors RemoteUser)
# -------------------------------------------------------------------
local_db = SqliteDatabase('bot_local.db')

class LocalUser(Model):
    # Sync tracking
    last_synced_at = BigIntegerField(default=0)
    is_dirty = BooleanField(default=True)

    # Identification
    user_id = CharField(max_length=100, unique=True, index=True)
    username = CharField(max_length=100, null=True, index=True)
    first_name = CharField(max_length=255, null=True)
    last_name = CharField(max_length=255, null=True)
    chat_id = CharField(max_length=100, index=True)

    # Game & preferences
    coin = IntegerField(default=0)
    score = IntegerField(default=0)
    level = IntegerField(default=1)
    game_state = TextField(default='{}')
    blocked_users = TextField(default='[]')
    sex = IntegerField(default=0)
    language = CharField(max_length=10, default='fa')
    age = IntegerField(null=True)          # Age in years (optional)
    city = CharField(max_length=100, null=True)  # City name (optional)

    # Status
    subscription_date = BigIntegerField(default=0)
    is_active = BooleanField(default=True)
    is_banned = BooleanField(default=False)

    # Statistics
    total_games_played = IntegerField(default=0)
    total_wins = IntegerField(default=0)
    total_losses = IntegerField(default=0)
    total_messages = IntegerField(default=0)
    last_seen = BigIntegerField(default=0)

    class Meta:
        database = local_db
        table_name = 'users'

    def to_remote_dict(self):
        return model_to_dict(self, exclude=[LocalUser.id, LocalUser.last_synced_at])

    @classmethod
    def from_remote(cls, remote_user: RemoteUser):
        local, created = cls.get_or_create(
            user_id=remote_user.user_id,
            chat_id=remote_user.chat_id,
            defaults={
                'username': remote_user.username,
                'first_name': remote_user.first_name,
                'last_name': remote_user.last_name,
                'coin': remote_user.coin,
                'score': remote_user.score,
                'level': remote_user.level,
                'game_state': remote_user.game_state,
                'blocked_users': remote_user.blocked_users,
                'sex': remote_user.sex,
                'language': remote_user.language,
                'subscription_date': remote_user.subscription_date,
                'is_active': remote_user.is_active,
                'is_banned': remote_user.is_banned,
                'total_games_played': remote_user.total_games_played,
                'total_wins': remote_user.total_wins,
                'total_losses': remote_user.total_losses,
                'total_messages': remote_user.total_messages,
                'last_seen': remote_user.last_seen,
                'last_synced_at': int(time.time()),
                'is_dirty': False,
                'age': remote_user.age,
                'city': remote_user.city,  
            }
        )
        if not created:
            for field in ['username', 'first_name', 'last_name', 'coin', 'score',
                          'level', 'game_state', 'blocked_users', 'sex', 'language',
                          'subscription_date', 'is_active', 'is_banned',
                          'total_games_played', 'total_wins', 'total_losses',
                          'total_messages', 'last_seen','age','city']:
                setattr(local, field, getattr(remote_user, field))
            local.last_synced_at = int(time.time())
            local.is_dirty = False
            local.save()
        return local
    
    def extend_subscription(self, days: int):
        """Extend subscription by days (for local user)"""
        import time
        current = self.subscription_date if self.subscription_date > int(time.time()) else int(time.time())
        self.subscription_date = current + (days * 86400)
        self.is_dirty = True   # mark for sync
        self.save()
            
    @property
    def is_subscribed(self) -> bool:
        """Check if user has active subscription"""
        import time
        return self.subscription_date > int(time.time())
    

    # ============================================
    # Statistics Methods
    # ============================================
    def record_game_result(self, won: bool):
        self.total_games_played += 1
        if won:
            self.total_wins += 1
        else:
            self.total_losses += 1
        self.is_dirty = True
        self.save()

    def record_message(self):
        self.total_messages += 1
        self.is_dirty = True
        self.save()

    def update_last_seen(self):
        import time
        self.last_seen = int(time.time())
        self.is_dirty = True
        self.save()

    # ============================================
    # Status Methods (ban, activate, etc.)
    # ============================================
    def ban(self):
        self.is_banned = True
        self.is_active = False
        self.is_dirty = True
        self.save()

    def unban(self):
        self.is_banned = False
        self.is_active = True
        self.is_dirty = True
        self.save()

    def deactivate(self):
        self.is_active = False
        self.is_dirty = True
        self.save()

    def activate(self):
        self.is_active = True
        self.is_dirty = True
        self.save()

    # ============================================
    # Blocking Methods
    # ============================================
    def block_user(self, chat_id_to_block: str) -> bool:
        blocked = self.blocked_users_list
        if chat_id_to_block not in blocked:
            blocked.append(chat_id_to_block)
            self.blocked_users = json.dumps(blocked)
            self.is_dirty = True
            self.save()
            return True
        return False

    def unblock_user(self, chat_id_to_unblock: str) -> bool:
        blocked = self.blocked_users_list
        if chat_id_to_unblock in blocked:
            blocked.remove(chat_id_to_unblock)
            self.blocked_users = json.dumps(blocked)
            self.is_dirty = True
            self.save()
            return True
        return False

    def is_blocked(self, chat_id_to_check: str) -> bool:
        return chat_id_to_check in self.blocked_users_list

    # ============================================
    # Game State Methods
    # ============================================
    def get_game_state(self, key: str, default=None):
        return self.game_state_dict.get(key, default)

    def clear_game_state(self):
        self.game_state = '{}'
        self.is_dirty = True
        self.save()
    
    def display_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        elif self.username:
            return self.username
        else:
            return "Unknown"


# -------------------------------------------------------------------
# SyncManager – hybrid online/offline/periodic sync
# -------------------------------------------------------------------
class SyncManager:
    def __init__(self, mode='periodic', sync_interval_hours=2, pull_on_start=True):
        self.mode = mode
        self.sync_interval_seconds = sync_interval_hours * 3600
        self._sync_thread = None
        self._stop_event = threading.Event()

        # Connect local DB and create tables
        local_db.connect()
        local_db.create_tables([LocalUser], safe=True)

        if mode == 'online':
            remote_db.create_tables([RemoteUser], safe=True)

        # Ensure remote table exists (create if missing)
        if not RemoteUser.table_exists():
            RemoteUser.create_table()
            print("✅ Created missing 'users' table in remote database")

        # Add any missing columns to remote table (must happen before pulling)
        self._ensure_remote_columns()

        if pull_on_start:
            self.pull_all_from_remote()

        atexit.register(self.sync_on_exit)

        
    # -----------------------------------------------------------------
    # User existence and lookup (no creation)
    # -----------------------------------------------------------------
    def user_exists(self, user_id: str = None, chat_id: str = None) -> bool:
        query = LocalUser.select()
        if user_id:
            query = query.where(LocalUser.user_id == user_id)
        elif chat_id:
            query = query.where(LocalUser.chat_id == chat_id)
        else:
            raise ValueError("Either user_id or chat_id must be provided")
        return query.exists()

    def find_user(self, user_id: str = None, chat_id: str = None) -> Optional[LocalUser]:
        if not (user_id or chat_id):
            raise ValueError("Either user_id or chat_id must be provided")
        if user_id:
            try:
                return LocalUser.get(LocalUser.user_id == user_id)
            except LocalUser.DoesNotExist:
                return None
        else:
            try:
                return LocalUser.get(LocalUser.chat_id == chat_id)
            except LocalUser.DoesNotExist:
                return None

    # -----------------------------------------------------------------
    # Get or create user
    # -----------------------------------------------------------------
    def get_user(self, user_id: str, chat_id: str, **defaults) -> LocalUser:
        local_user, created = LocalUser.get_or_create(
            user_id=user_id,
            chat_id=chat_id,
            defaults={
                'username': defaults.get('username'),
                'first_name': defaults.get('first_name'),
                'last_name': defaults.get('last_name'),
                'coin': defaults.get('coin', 5),
                'language': defaults.get('language', 'fa'),
                'game_state': '{}',
                'blocked_users': '[]',
                'is_dirty': True,
            }
        )
        if created and self.mode == 'online':
            self._push_to_remote(local_user)
            local_user.is_dirty = False
            local_user.save()
        return local_user

    def update_user(self, local_user: LocalUser):
        local_user.is_dirty = True
        local_user.save()
        if self.mode == 'online':
            self._push_to_remote(local_user)

    # -----------------------------------------------------------------
    # Sync primitives
    # -----------------------------------------------------------------
    def _push_to_remote(self, local_user: LocalUser):
        try:
            data = local_user.to_remote_dict()
            remote_user, created = RemoteUser.get_or_create(
                user_id=local_user.user_id,
                chat_id=local_user.chat_id,
                defaults=data
            )
            if not created:
                for key, value in data.items():
                    setattr(remote_user, key, value)
                remote_user.save()
            local_user.is_dirty = False
            local_user.last_synced_at = int(time.time())
            local_user.save()
        except Exception as e:
            print(f"Push error for {local_user.user_id}: {e}")

    def sync_all_dirty(self):
        dirty = LocalUser.select().where(LocalUser.is_dirty == True)
        count = dirty.count()
        for user in dirty:
            self._push_to_remote(user)
        if count:
            print(f"Synced {count} dirty user(s).")

    def pull_all_from_remote(self):
        print("Pulling all users from remote to local...")
        remote_count = RemoteUser.select().count()
        for i, remote in enumerate(RemoteUser.select(), 1):
            LocalUser.from_remote(remote)
            if i % 100 == 0:
                print(f"  Pulled {i}/{remote_count} users")
        print(f"Pull complete. {remote_count} users synced to local.")

    def sync_on_exit(self):
        if self.mode in ('periodic', 'online'):
            print("Syncing before exit...")
            self.sync_all_dirty()
        else:
            print("Offline mode – no sync on exit.")

    # -----------------------------------------------------------------
    # Periodic sync (background thread)
    # -----------------------------------------------------------------
    def start_periodic_sync(self):
        if self.mode != 'periodic':
            return
        if self._sync_thread and self._sync_thread.is_alive():
            return

        def sync_loop():
            while not self._stop_event.wait(self.sync_interval_seconds):
                if not self._stop_event.is_set():
                    self.sync_all_dirty()

        self._sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self._sync_thread.start()

    def stop_periodic_sync(self):
        self._stop_event.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=2)

    def set_mode(self, new_mode: str):
        old_mode = self.mode
        self.mode = new_mode
        if old_mode == 'periodic':
            self.stop_periodic_sync()
        if new_mode == 'periodic':
            self.start_periodic_sync()
        elif new_mode == 'online':
            self.sync_all_dirty()

    def _ensure_remote_columns(self):
        """Add any columns that exist in RemoteUser but are missing in the remote table."""
        # Get existing columns
        try:
            cursor = remote_db.execute_sql("SHOW COLUMNS FROM users")
            existing = {row[0] for row in cursor.fetchall()}
        except Exception as e:
            print(f"⚠️ Cannot inspect remote table: {e}")
            return

        model_fields = RemoteUser._meta.fields
        for name, field in model_fields.items():
            if name in ('id', 'created_at', 'updated_at'):
                continue
            if name not in existing:
                # Determine SQL type
                from peewee import CharField, IntegerField, BigIntegerField, BooleanField, TextField
                if isinstance(field, CharField):
                    sql_type = f"VARCHAR({field.max_length})"
                elif isinstance(field, IntegerField):
                    sql_type = "INT"
                elif isinstance(field, BigIntegerField):
                    sql_type = "BIGINT"
                elif isinstance(field, BooleanField):
                    sql_type = "BOOLEAN"
                elif isinstance(field, TextField):
                    sql_type = "TEXT"
                else:
                    sql_type = "TEXT"

                # Handle default – always quote string defaults
                default = field.default
                if default is not None:
                    if isinstance(default, str):
                        default_clause = f"DEFAULT '{default}'"
                    else:
                        default_clause = f"DEFAULT {default}"
                else:
                    default_clause = ""

                null_clause = "" if field.null else "NOT NULL"
                alter_sql = f"ALTER TABLE users ADD COLUMN {name} {sql_type} {null_clause} {default_clause}".strip()
                try:
                    remote_db.execute_sql(alter_sql)
                    print(f"✅ Added missing column '{name}'")
                except Exception as e:
                    print(f"⚠️ Failed to add column {name}: {e}")



                    
# -------------------------------------------------------------------
# UserManager – high‑level user operations (complete)
# -------------------------------------------------------------------
class UserManager:
    def __init__(self, sync_manager: SyncManager):
        self.sync = sync_manager

    # ---------- existence & retrieval ----------
    def exists(self, user_id: str = None, chat_id: str = None) -> bool:
        return self.sync.user_exists(user_id, chat_id)

    def get(self, user_id: str = None, chat_id: str = None) -> Optional[LocalUser]:
        return self.sync.find_user(user_id, chat_id)

    def get_or_create(self, user_id: str, chat_id: str, **defaults) -> LocalUser:
        return self.sync.get_user(user_id, chat_id, **defaults)

    # ---------- getters ----------
    def display_name(self, user: LocalUser) -> str:
        return user.display_name

    def full_name(self, user: LocalUser) -> str:
        return user.full_name

    def sex(self, user: LocalUser) -> int:
        return user.sex

    def language(self, user: LocalUser) -> str:
        return user.language

    def coin(self, user: LocalUser) -> int:
        return user.coin

    def score(self, user: LocalUser) -> int:
        return user.score

    def level(self, user: LocalUser) -> int:
        return user.level

    def game_state(self, user: LocalUser, key: str = None, default=None):
        if key:
            return user.get_game_state(key, default)
        return user.game_state_dict

    def blocked_users(self, user: LocalUser) -> List[str]:
        return user.blocked_users_list

    def is_subscribed(self, user: LocalUser) -> bool:
        return user.is_subscribed

    def subscription_days_left(self, user: LocalUser) -> int:
        return user.get_subscription_days_left()

    def win_rate(self, user: LocalUser) -> float:
        return user.win_rate

    # ---------- setters (auto sync) ----------
    def set_first_name(self, user: LocalUser, value: str):
        user.first_name = value
        self.sync.update_user(user)

    def set_last_name(self, user: LocalUser, value: str):
        user.last_name = value
        self.sync.update_user(user)

    def set_username(self, user: LocalUser, value: str):
        user.username = value
        self.sync.update_user(user)

    def set_sex(self, user: LocalUser, value: int):
        if value not in (0,1,2):
            raise ValueError("Sex must be 0,1,2")
        user.sex = value
        self.sync.update_user(user)

    def set_language(self, user: LocalUser, value: str):
        if value not in ('fa','en'):
            raise ValueError("Language must be 'fa' or 'en'")
        user.language = value
        self.sync.update_user(user)

    def set_age(self, user: LocalUser, age: int):
        user.age = age
        self.sync.update_user(user)

    def get_age(self, user: LocalUser) -> Optional[int]:
        return user.age

    def set_city(self, user: LocalUser, city: str):
        user.city = city
        self.sync.update_user(user)

    def get_city(self, user: LocalUser) -> Optional[str]:
        return user.city

    # ---------- game economy ----------
    def add_coins(self, user: LocalUser, amount: int) -> int:
        user.coin += amount
        self.sync.update_user(user)
        return user.coin

    def remove_coins(self, user: LocalUser, amount: int) -> bool:
        if user.coin >= amount:
            user.coin -= amount
            self.sync.update_user(user)
            return True
        return False

    def add_score(self, user: LocalUser, points: int) -> int:
        user.add_score(points)   # this already calls save() and marks dirty
        # But add_score calls save() which calls super().save(), not our update_user.
        # To ensure sync, we call update_user again.
        self.sync.update_user(user)
        return user.score

    def set_level(self, user: LocalUser, new_level: int):
        if new_level < 1:
            raise ValueError("Level must be >=1")
        user.level = new_level
        self.sync.update_user(user)

    # ---------- game state (JSON) ----------
    def set_game_state(self, user: LocalUser, key: str, value: Any):
        user.update_game_state(key, value)   # saves internally, marks dirty
        self.sync.update_user(user)   # ensure sync (though already dirty)

    def get_game_state(self, user: LocalUser, key: str, default=None):
        return user.get_game_state(key, default)

    def clear_game_state(self, user: LocalUser):
        user.clear_game_state()
        self.sync.update_user(user)

    # ---------- blocking ----------
    def block_user(self, user: LocalUser, chat_id_to_block: str) -> bool:
        return user.block_user(chat_id_to_block)

    def unblock_user(self, user: LocalUser, chat_id_to_unblock: str) -> bool:
        return user.unblock_user(chat_id_to_unblock)

    def is_blocked(self, user: LocalUser, chat_id_to_check: str) -> bool:
        return user.is_blocked(chat_id_to_check)

    # ---------- subscription ----------
    def extend_subscription(self, user: LocalUser, days: int):
        user.extend_subscription(days)

    # ---------- statistics ----------
    def record_game_result(self, user: LocalUser, won: bool):
        user.record_game_result(won)

    def record_message(self, user: LocalUser):
        user.record_message()

    def update_last_seen(self, user: LocalUser):
        user.update_last_seen()

    # ---------- status ----------
    def ban_user(self, user: LocalUser):
        user.ban()

    def unban_user(self, user: LocalUser):
        user.unban()

    def deactivate_user(self, user: LocalUser):
        user.deactivate()

    def activate_user(self, user: LocalUser):
        user.activate()

    # ---------- bulk / admin ----------
    def get_all_users(self, limit: int = None, offset: int = 0) -> List[LocalUser]:
        query = LocalUser.select()
        if limit:
            query = query.limit(limit).offset(offset)
        return list(query)

    def get_leaderboard(self, limit: int = 10) -> List[LocalUser]:
        return list(LocalUser.select().order_by(LocalUser.score.desc()).limit(limit))

    def get_richest(self, limit: int = 10) -> List[LocalUser]:
        return list(LocalUser.select().order_by(LocalUser.coin.desc()).limit(limit))

    def get_by_language(self, lang: str) -> List[LocalUser]:
        return list(LocalUser.select().where(LocalUser.language == lang))

    def get_inactive_users(self, days: int = 30) -> List[LocalUser]:
        threshold = int(time.time()) - (days * 86400)
        return list(LocalUser.select().where(LocalUser.last_seen < threshold))

    def add_coins_all(self, amount: int, condition=None) -> int:
        query = LocalUser.update(coin=LocalUser.coin + amount)
        if condition:
            query = query.where(condition)
        count = query.execute()
        LocalUser.update(is_dirty=True).execute()
        return count
    


if __name__ == "__main__":
    # Example usage
    sync_mgr = SyncManager(mode='periodic', sync_interval_hours=1, pull_on_start=True)
    user_mgr = UserManager(sync_mgr)

    # Create or get a user
    user = user_mgr.get_or_create(user_id="12345", chat_id="67890", first_name="Alice", language="en")
    print("User:", user.to_remote_dict())

    # Update some fields
    user_mgr.set_sex(user, 2)
    user_mgr.add_coins(user, 50)
    print("Updated User:", user.to_remote_dict())