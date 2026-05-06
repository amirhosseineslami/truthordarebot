# flood_manager.py
import time
from collections import deque
from typing import Dict, Optional
from dataclasses import dataclass
import threading

@dataclass
class FloodRecord:
    timestamps: deque
    warning_strike: int = 0
    last_warning_time: float = 0

class FloodManager:
    """
    Manages anti‑flood detection per user.
    """
    def __init__(self, window_seconds: int = 5, max_messages: int = 5,
                 warning_cooldown_seconds: int = 60, max_strikes: int = 2):
        self.window = window_seconds
        self.max_msgs = max_messages
        self.warning_cooldown = warning_cooldown_seconds
        self.max_strikes = max_strikes
        self._records: Dict[str, FloodRecord] = {}
        self._lock = threading.Lock()

    def check_and_record(self, user_id: str) -> tuple[bool, bool, int]:
        """
        Returns (is_flood, should_warn, current_strike)
        - is_flood: True if user exceeded limit in this window
        - should_warn: True if this is the first strike in current cooldown
        - current_strike: strike count after increment
        """
        now = time.time()
        with self._lock:
            if user_id not in self._records:
                self._records[user_id] = FloodRecord(timestamps=deque())

            rec = self._records[user_id]
            # Clean old timestamps
            while rec.timestamps and rec.timestamps[0] < now - self.window:
                rec.timestamps.popleft()

            # Add current message
            rec.timestamps.append(now)
            msg_count = len(rec.timestamps)

            if msg_count <= self.max_msgs:
                # No flood – reset strike if outside cooldown
                if rec.last_warning_time + self.warning_cooldown < now:
                    rec.warning_strike = 0
                return False, False, rec.warning_strike

            # Flood detected
            # Count if this is a new strike (only once per flood event)
            if rec.last_warning_time + self.warning_cooldown < now:
                rec.warning_strike += 1
                rec.last_warning_time = now
                should_warn = True
            else:
                should_warn = False

            return True, should_warn, rec.warning_strike

    def reset_user(self, user_id: str):
        """Completely reset flood state for a user (e.g., after blocking)"""
        with self._lock:
            if user_id in self._records:
                del self._records[user_id]

    def get_strike(self, user_id: str) -> int:
        with self._lock:
            return self._records.get(user_id, FloodRecord(timestamps=deque())).warning_strike

# Global instance (tune params: 5 messages in 5 seconds, 2 strikes = block)
flood_manager = FloodManager(window_seconds=5, max_messages=5,
                             warning_cooldown_seconds=60, max_strikes=2)