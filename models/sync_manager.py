import json
import time
import threading
import atexit
from peewee import SqliteDatabase, Model, CharField, IntegerField, BigIntegerField, BooleanField, TextField
from playhouse.shortcuts import model_to_dict, dict_to_model

# Import your remote User model (the one you already have)
from models.user import User as RemoteUser
from database import db as remote_db   # your MySQL connection

# ============================================================
# Local SQLite database and LocalUser model (mirrors RemoteUser)
# ============================================================
local_db = SqliteDatabase('bot_local.db')

class LocalUser(Model):
    """Local copy of User – same fields as RemoteUser."""
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
        """Convert local model to dict suitable for remote update."""
        data = model_to_dict(self, exclude=[LocalUser.id, LocalUser.last_synced_at])
        return data

    @classmethod
    def from_remote(cls, remote_user: RemoteUser):
        """Create or update local user from remote user."""
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
            }
        )
        if not created:
            # Update local fields from remote (overwrite)
            for field in ['username', 'first_name', 'last_name', 'coin', 'score',
                          'level', 'game_state', 'blocked_users', 'sex', 'language',
                          'subscription_date', 'is_active', 'is_banned',
                          'total_games_played', 'total_wins', 'total_losses',
                          'total_messages', 'last_seen']:
                setattr(local, field, getattr(remote_user, field))
            local.last_synced_at = int(time.time())
            local.is_dirty = False
            local.save()
        return local


# ============================================================
# SyncManager – handles hybrid online/offline/periodic modes
# ============================================================
class SyncManager:
    def __init__(self, mode='periodic', sync_interval_hours=2):
        """
        mode: 'online'   – write to both local and remote immediately
              'offline'  – write only to local (never sync)
              'periodic' – write to local, sync every N hours and on exit
        """
        self.mode = mode
        self.sync_interval_seconds = sync_interval_hours * 3600
        self._sync_thread = None
        self._stop_event = threading.Event()

        # Ensure local tables exist
        local_db.connect()
        local_db.create_tables([LocalUser], safe=True)

        # If mode is 'online', also ensure remote table exists
        if mode == 'online':
            remote_db.create_tables([RemoteUser], safe=True)

        # Register exit handler to sync dirty users
        atexit.register(self.sync_on_exit)

    # -----------------------------------------------------------------
    # Public user access methods (use these instead of direct User model)
    # -----------------------------------------------------------------
    def get_user(self, user_id: str, chat_id: str, **defaults):
        """
        Retrieve user from local storage (creates if not exists).
        If mode is 'online', also ensures remote user exists.
        Returns a LocalUser instance.
        """
        local_user, created = LocalUser.get_or_create(
            user_id=user_id,
            chat_id=chat_id,
            defaults={
                'username': defaults.get('username'),
                'first_name': defaults.get('first_name'),
                'last_name': defaults.get('last_name'),
                'coin': defaults.get('coin', 100),
                'language': defaults.get('language', 'fa'),
                'game_state': '{}',
                'blocked_users': '[]',
                'is_dirty': True,
            }
        )
        if created and self.mode == 'online':
            # Also create remote user
            self._push_to_remote(local_user)
            local_user.is_dirty = False
            local_user.save()
        return local_user

    def update_user(self, local_user: LocalUser):
        """
        Mark a local user as dirty and save.
        In online mode, immediately pushes to remote.
        """
        local_user.is_dirty = True
        local_user.save()
        if self.mode == 'online':
            self._push_to_remote(local_user)

    # -----------------------------------------------------------------
    # Sync methods
    # -----------------------------------------------------------------
    def _push_to_remote(self, local_user: LocalUser):
        """Push a single local user to remote MySQL."""
        try:
            data = local_user.to_remote_dict()
            # Find or create remote user
            remote_user, created = RemoteUser.get_or_create(
                user_id=local_user.user_id,
                chat_id=local_user.chat_id,
                defaults=data
            )
            if not created:
                # Update existing remote user
                for key, value in data.items():
                    setattr(remote_user, key, value)
                remote_user.save()
            # Mark local as synced
            local_user.is_dirty = False
            local_user.last_synced_at = int(time.time())
            local_user.save()
        except Exception as e:
            print(f"Sync error for {local_user.user_id}: {e}")

    def sync_all_dirty(self):
        """Push all dirty local users to remote."""
        dirty_users = LocalUser.select().where(LocalUser.is_dirty == True)
        count = dirty_users.count()
        for user in dirty_users:
            self._push_to_remote(user)
        print(f"Synced {count} dirty user(s).")

    def sync_on_exit(self):
        """Call this when the bot is shutting down."""
        if self.mode in ('periodic', 'online'):
            print("Syncing before exit...")
            self.sync_all_dirty()
        else:
            print("Offline mode – no sync on exit.")

    # -----------------------------------------------------------------
    # Background periodic sync (only for periodic mode)
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

    # -----------------------------------------------------------------
    # Optional: pull all remote users into local (initial migration)
    # -----------------------------------------------------------------
    def pull_all_from_remote(self):
        """Copy all remote users to local (overwrites local)."""
        for remote in RemoteUser.select():
            LocalUser.from_remote(remote)
        print("Pulled all users from remote to local.")

    # -----------------------------------------------------------------
    # Mode switching at runtime
    # -----------------------------------------------------------------
    def set_mode(self, new_mode: str):
        old_mode = self.mode
        self.mode = new_mode
        if old_mode == 'periodic':
            self.stop_periodic_sync()
        if new_mode == 'periodic':
            self.start_periodic_sync()
        elif new_mode == 'online':
            # Immediately sync all dirty
            self.sync_all_dirty()