from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import random

# ------------------------------------------------------------
# Constants for gender
GENDER_UNKNOWN = 0
GENDER_MALE = 1
GENDER_FEMALE = 2

# Preferred gender can be same values, plus 'any' (represented as -1 or None)
PREFER_ANY = -1

# ------------------------------------------------------------
@dataclass
class Connection:
    player1_chat_id: str
    player2_chat_id: str
    player1_username: Optional[str]
    player2_username: Optional[str]
    connected_at: datetime
    last_activity: datetime
    is_active: bool = True

    def get_other_chat_id(self, chat_id: str) -> Optional[str]:
        if chat_id == self.player1_chat_id:
            return self.player2_chat_id
        elif chat_id == self.player2_chat_id:
            return self.player1_chat_id
        return None

    def get_other_username(self, chat_id: str) -> Optional[str]:
        if chat_id == self.player1_chat_id:
            return self.player2_username
        elif chat_id == self.player2_chat_id:
            return self.player1_username
        return None


@dataclass
class WaitingUser:
    """Data for a user waiting in the random pairing queue"""
    chat_id: str
    username: str
    gender: int = GENDER_UNKNOWN
    preferred_gender: int = PREFER_ANY
    is_pro: bool = False
    joined_at: datetime = field(default_factory=datetime.now)


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, Connection] = {}
        self._pending_requests: Dict[str, str] = {}
        self._waiting_queue: List[WaitingUser] = []
        self._pro_waiting_queue: List[WaitingUser] = []      # Premium users only
        self._regular_waiting_queue: List[WaitingUser] = []  # Non-premium users
        self._chat_to_username: Dict[str, str] = {}
        self._user_preferences: Dict[str, dict] = {}

    # ------------------------------------------------------------
    # User preferences
    # ------------------------------------------------------------
    def set_user_preferences(self, chat_id: str, gender: int, 
                             preferred_gender: int = PREFER_ANY, 
                             is_pro: bool = False):
        """Store user preferences (gender, desired gender, pro status)"""
        self._user_preferences[chat_id] = {
            'gender': gender,
            'preferred_gender': preferred_gender,
            'is_pro': is_pro
        }

    def get_user_preferences(self, chat_id: str) -> dict:
        """Retrieve stored preferences, default values if not set"""
        if chat_id in self._user_preferences:
            return self._user_preferences[chat_id]
        return {'gender': GENDER_UNKNOWN, 'preferred_gender': PREFER_ANY, 'is_pro': False}

    # ------------------------------------------------------------
    # Queue Management with separate queues for pro/regular
    # ------------------------------------------------------------
    def _get_user_queue(self, chat_id: str) -> Optional[List[WaitingUser]]:
        """Get which queue the user is in (if any)"""
        for wu in self._pro_waiting_queue:
            if wu.chat_id == chat_id:
                return self._pro_waiting_queue
        for wu in self._regular_waiting_queue:
            if wu.chat_id == chat_id:
                return self._regular_waiting_queue
        return None

    def add_to_waiting_queue(self, chat_id: str, username: str = None,
                             gender: int = None, preferred_gender: int = None,
                             is_pro: bool = None) -> int:
        """
        Add player to waiting queue based on pro status.
        Returns position in queue (1-indexed) after insertion.
        """
        if chat_id in self._connections:
            return 0
        
        # Remove if already in queue
        self.remove_from_waiting_queue(chat_id)

        # Get or use passed preferences
        pref = self.get_user_preferences(chat_id)
        actual_gender = gender if gender is not None else pref['gender']
        actual_preferred = preferred_gender if preferred_gender is not None else pref['preferred_gender']
        actual_pro = is_pro if is_pro is not None else pref['is_pro']

        if username:
            self._chat_to_username[chat_id] = username

        waiting_user = WaitingUser(
            chat_id=chat_id,
            username=username or self._chat_to_username.get(chat_id, chat_id[:8]),
            gender=actual_gender,
            preferred_gender=actual_preferred,
            is_pro=actual_pro
        )
        
        # Add to appropriate queue
        if actual_pro:
            self._pro_waiting_queue.append(waiting_user)
            return len(self._pro_waiting_queue)
        else:
            self._regular_waiting_queue.append(waiting_user)
            return len(self._regular_waiting_queue)

    def remove_from_waiting_queue(self, chat_id: str) -> bool:
        """Remove a specific user from waiting queue"""
        for i, wu in enumerate(self._pro_waiting_queue):
            if wu.chat_id == chat_id:
                self._pro_waiting_queue.pop(i)
                return True
        for i, wu in enumerate(self._regular_waiting_queue):
            if wu.chat_id == chat_id:
                self._regular_waiting_queue.pop(i)
                return True
        return False

    def get_queue_position(self, chat_id: str) -> int:
        """Returns 1-indexed position, 0 if not in queue"""
        for i, wu in enumerate(self._pro_waiting_queue):
            if wu.chat_id == chat_id:
                return i + 1
        for i, wu in enumerate(self._regular_waiting_queue):
            if wu.chat_id == chat_id:
                return i + 1
        return 0

    def get_queue_size(self) -> int:
        return len(self._pro_waiting_queue) + len(self._regular_waiting_queue)

    def get_waiting_players(self) -> List[str]:
        """Return chat_ids of waiting players (backward compatibility)"""
        return [wu.chat_id for wu in self._pro_waiting_queue] + \
               [wu.chat_id for wu in self._regular_waiting_queue]

    def is_in_queue(self, chat_id: str) -> bool:
        return any(wu.chat_id == chat_id for wu in self._pro_waiting_queue) or \
               any(wu.chat_id == chat_id for wu in self._regular_waiting_queue)

    def get_queue_stats(self) -> dict:
        """Get detailed queue statistics"""
        return {
            'total_waiting': self.get_queue_size(),
            'pro_waiting': len(self._pro_waiting_queue),
            'regular_waiting': len(self._regular_waiting_queue)
        }

    # ------------------------------------------------------------
    # Gender Compatibility Check
    # ------------------------------------------------------------
    def _is_gender_compatible(self, user1_gender: int, user1_preferred: int,
                               user2_gender: int, user2_preferred: int) -> bool:
        """
        Check if two users are compatible based on gender preferences.
        Returns True if both users' preferences are satisfied.
        """
        # Check user1's preference against user2's gender
        user1_satisfied = (user1_preferred == PREFER_ANY or user1_preferred == user2_gender)
        # Check user2's preference against user1's gender
        user2_satisfied = (user2_preferred == PREFER_ANY or user2_preferred == user1_gender)
        
        return user1_satisfied and user2_satisfied

    # ------------------------------------------------------------
    # Priority Matching with Gender Filter
    # ------------------------------------------------------------
    def _find_matching_partner(self, requester_chat_id: str, 
                                requester_prefs: dict,
                                search_queue: List[WaitingUser]) -> Optional[WaitingUser]:
        """
        Find a matching partner in a specific queue.
        Prioritizes gender compatibility first, then pro status.
        """
        compatible = []
        
        for wu in search_queue:
            if wu.chat_id == requester_chat_id:
                continue
            
            # Check gender compatibility
            if self._is_gender_compatible(
                requester_prefs['gender'], requester_prefs['preferred_gender'],
                wu.gender, wu.preferred_gender
            ):
                compatible.append(wu)
        
        if not compatible:
            return None
        
        # Sort by: pro status first, then oldest waiting time
        compatible.sort(key=lambda x: (-x.is_pro, x.joined_at))
        return compatible[0]

    def pair_random(self, chat_id: str = None, username: str = None) -> Optional[Tuple[str, str]]:
        """
        Connect player to the best waiting partner.
        Priority: Pro users first, then regular users.
        """
        if chat_id and username:
            self._chat_to_username[chat_id] = username

        if chat_id:
            # Already connected?
            if chat_id in self._connections:
                return None

            requester_prefs = self.get_user_preferences(chat_id)
            requester_prefs['username'] = username
            requester_prefs['chat_id'] = chat_id
            
            # Determine requester's pro status
            is_requester_pro = requester_prefs.get('is_pro', False)
            
            # STEP 1: Search in pro queue first (if requester wants pro partner or is pro)
            # Pro queue always searched first to prioritize pro users
            best_match = self._find_matching_partner(chat_id, requester_prefs, self._pro_waiting_queue)
            
            # STEP 2: If no match in pro queue, search in regular queue
            if not best_match:
                best_match = self._find_matching_partner(chat_id, requester_prefs, self._regular_waiting_queue)
            
            # STEP 3: If requester is pro and no one is waiting, add to pro queue
            # If requester is regular and no one is waiting, add to regular queue
            if best_match:
                # Remove matched user from queue
                self.remove_from_waiting_queue(best_match.chat_id)
                other_username = best_match.username
                other_chat_id = best_match.chat_id
                # Create connection
                self.connect(chat_id, other_chat_id, username, other_username)
                return (other_chat_id, other_username)
            else:
                # No match available – add requester to appropriate queue
                self.add_to_waiting_queue(chat_id, username)
                return None
        else:
            # Legacy: pair any two waiting users (prioritize pro queue)
            if len(self._pro_waiting_queue) >= 2:
                wu1 = self._pro_waiting_queue.pop(0)
                wu2 = self._pro_waiting_queue.pop(0)
                self.connect(wu1.chat_id, wu2.chat_id, wu1.username, wu2.username)
                return (wu1.chat_id, wu2.chat_id)
            elif len(self._pro_waiting_queue) == 1 and len(self._regular_waiting_queue) >= 1:
                wu1 = self._pro_waiting_queue.pop(0)
                wu2 = self._regular_waiting_queue.pop(0)
                self.connect(wu1.chat_id, wu2.chat_id, wu1.username, wu2.username)
                return (wu1.chat_id, wu2.chat_id)
            elif len(self._regular_waiting_queue) >= 2:
                wu1 = self._regular_waiting_queue.pop(0)
                wu2 = self._regular_waiting_queue.pop(0)
                self.connect(wu1.chat_id, wu2.chat_id, wu1.username, wu2.username)
                return (wu1.chat_id, wu2.chat_id)
            return None

    # ------------------------------------------------------------
    # Direct Connection
    # ------------------------------------------------------------
    def connect(self, chat_id1: str, chat_id2: str,
                username1: str = None, username2: str = None) -> bool:
        if chat_id1 in self._connections or chat_id2 in self._connections:
            return False
        if username1:
            self._chat_to_username[chat_id1] = username1
        if username2:
            self._chat_to_username[chat_id2] = username2
        conn = Connection(
            player1_chat_id=chat_id1,
            player2_chat_id=chat_id2,
            player1_username=username1 or chat_id1[:8],
            player2_username=username2 or chat_id2[:8],
            connected_at=datetime.now(),
            last_activity=datetime.now()
        )
        self._connections[chat_id1] = conn
        self._connections[chat_id2] = conn
        self.remove_from_waiting_queue(chat_id1)
        self.remove_from_waiting_queue(chat_id2)
        return True

    def disconnect(self, chat_id: str) -> bool:
        if chat_id not in self._connections:
            return False
        other = self._connections[chat_id].get_other_chat_id(chat_id)
        del self._connections[chat_id]
        if other and other in self._connections:
            del self._connections[other]
        return True

    # ------------------------------------------------------------
    # Connection Requests (Optional)
    # ------------------------------------------------------------
    def request_connection(self, from_chat_id: str, to_chat_id: str) -> bool:
        if from_chat_id in self._connections or to_chat_id in self._connections:
            return False
        if to_chat_id in self._pending_requests.values():
            return False
        if from_chat_id == to_chat_id:
            return False
        
        self._pending_requests[from_chat_id] = to_chat_id
        return True

    def accept_request(self, accepting_chat_id: str, 
                      accepting_username: str = None) -> Optional[Tuple[str, str, str, str]]:
        requester = None
        for req, target in self._pending_requests.items():
            if target == accepting_chat_id:
                requester = req
                break
        
        if not requester:
            return None
        
        requester_username = self._chat_to_username.get(requester)
        del self._pending_requests[requester]
        self.connect(requester, accepting_chat_id, requester_username, accepting_username)
        return (requester, accepting_chat_id, requester_username, accepting_username)

    def reject_request(self, chat_id: str) -> bool:
        for req, target in list(self._pending_requests.items()):
            if target == chat_id:
                del self._pending_requests[req]
                return True
        return False

    def cancel_request(self, chat_id: str) -> bool:
        if chat_id in self._pending_requests:
            del self._pending_requests[chat_id]
            return True
        return False

    def has_pending_request(self, chat_id: str) -> bool:
        return chat_id in self._pending_requests

    def get_pending_request_target(self, chat_id: str) -> Optional[str]:
        return self._pending_requests.get(chat_id)

    def get_pending_request_from(self, chat_id: str) -> Optional[str]:
        for req, target in self._pending_requests.items():
            if target == chat_id:
                return req
        return None

    # ------------------------------------------------------------
    # Message Forwarding
    # ------------------------------------------------------------
    def forward_message(self, from_chat_id: str, message: str) -> Optional[str]:
        if from_chat_id not in self._connections:
            return None
        conn = self._connections[from_chat_id]
        conn.last_activity = datetime.now()
        return conn.get_other_chat_id(from_chat_id)

    # ------------------------------------------------------------
    # Status & Info
    # ------------------------------------------------------------
    def is_connected(self, chat_id: str) -> bool:
        return chat_id in self._connections

    def get_connection_info(self, chat_id: str) -> Optional[dict]:
        if chat_id not in self._connections:
            return None
        conn = self._connections[chat_id]
        return {
            'connected_to_chat_id': conn.get_other_chat_id(chat_id),
            'connected_to_username': conn.get_other_username(chat_id),
            'connected_since': conn.connected_at,
            'last_activity': conn.last_activity
        }

    def set_username(self, chat_id: str, username: str):
        if username:
            self._chat_to_username[chat_id] = username

    def get_username(self, chat_id: str) -> str:
        return self._chat_to_username.get(chat_id, chat_id[:8])

    def get_stats(self) -> dict:
        return {
            'active_connections': len(self._connections) // 2,
            'pending_requests': len(self._pending_requests),
            'queue_stats': self.get_queue_stats(),
            'connected_players': len(set(self._connections.keys()))
        }

    def cleanup_inactive(self, timeout_minutes: int = 30) -> int:
        now = datetime.now()
        to_disconnect = []
        for chat_id, conn in self._connections.items():
            if (now - conn.last_activity).seconds > timeout_minutes * 60:
                to_disconnect.append(chat_id)
        for chat_id in to_disconnect:
            self.disconnect(chat_id)
        return len(to_disconnect)


    def get_queue_stats(self) -> dict:
        """Get detailed queue statistics"""
        return {
            'total_waiting': self.get_queue_size(),
            'pro_waiting': len(self._pro_waiting_queue),
            'regular_waiting': len(self._regular_waiting_queue)
        }

    def get_queue_position_with_type(self, chat_id: str) -> tuple:
        """
        Returns (position, queue_type) where queue_type is 'pro' or 'regular'
        """
        for i, wu in enumerate(self._pro_waiting_queue):
            if wu.chat_id == chat_id:
                return (i + 1, 'pro')
        for i, wu in enumerate(self._regular_waiting_queue):
            if wu.chat_id == chat_id:
                return (i + 1, 'regular')
        return (0, None)

# Global instance
connection_manager = ConnectionManager()