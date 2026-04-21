from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import random

@dataclass
class Connection:
    """Represents a connection between two players using chat_id"""
    player1_chat_id: str
    player2_chat_id: str
    player1_username: Optional[str]
    player2_username: Optional[str]
    connected_at: datetime
    last_activity: datetime
    is_active: bool = True
    
    def get_other_chat_id(self, chat_id: str) -> Optional[str]:
        """Get the other player's chat_id"""
        if chat_id == self.player1_chat_id:
            return self.player2_chat_id
        elif chat_id == self.player2_chat_id:
            return self.player1_chat_id
        return None
    
    def get_other_username(self, chat_id: str) -> Optional[str]:
        """Get the other player's username for display"""
        if chat_id == self.player1_chat_id:
            return self.player2_username
        elif chat_id == self.player2_chat_id:
            return self.player1_username
        return None

class ConnectionManager:
    """
    Manages connections between players using chat_id as identifier
    """
    
    def __init__(self):
        self._connections: Dict[str, Connection] = {}  # chat_id -> Connection
        self._pending_requests: Dict[str, str] = {}  # requester_chat_id -> target_chat_id
        self._waiting_queue: List[str] = []  # chat_ids waiting for random pair
        self._chat_to_username: Dict[str, str] = {}  # chat_id -> username for display
    
    # ============================================
    # Queue Management (Restored functions)
    # ============================================
    
    def add_to_waiting_queue(self, chat_id: str, username: str = None) -> int:
        """
        Add player to waiting queue manually
        Returns: Position in queue (1-indexed)
        """
        if chat_id not in self._waiting_queue and chat_id not in self._connections:
            self._waiting_queue.append(chat_id)
            if username:
                self._chat_to_username[chat_id] = username
        return self.get_queue_position(chat_id)
    
    def remove_from_waiting_queue(self, chat_id: str) -> bool:
        """Remove player from waiting queue"""
        if chat_id in self._waiting_queue:
            self._waiting_queue.remove(chat_id)
            return True
        return False
    
    def get_queue_position(self, chat_id: str) -> int:
        """Get player's position in queue (1-indexed), returns 0 if not in queue"""
        if chat_id in self._waiting_queue:
            return self._waiting_queue.index(chat_id) + 1
        return 0
    
    def get_queue_size(self) -> int:
        """Get number of players waiting"""
        return len(self._waiting_queue)
    
    def get_waiting_players(self) -> List[str]:
        """Get list of waiting players' chat_ids"""
        return self._waiting_queue.copy()
    
    def is_in_queue(self, chat_id: str) -> bool:
        """Check if player is in waiting queue"""
        return chat_id in self._waiting_queue
    
    # ============================================
    # Random Pairing - Multiple ways
    # ============================================
    
    def pair_random(self, chat_id: str = None, username: str = None) -> Optional[Tuple[str, str]]:
        """
        Connect player to a random waiting player immediately
        
        Args:
            chat_id: The player's chat_id (if None, just pair two waiting players)
            username: Player's username for display (optional)
        
        Returns:
            If chat_id provided: (connected_chat_id, connected_username) or None
            If chat_id is None: (chat_id1, chat_id2) or None
        """
        # Store username if provided
        if chat_id and username:
            self._chat_to_username[chat_id] = username
        
        # Case 1: Specific player wants to pair
        if chat_id:
            # Check if already connected
            if chat_id in self._connections:
                return None
            
            
            # If someone is waiting, connect immediately
            if self._waiting_queue:

                other_chat_id = None
                for ichat in self._waiting_queue:
                    if ichat.strip().lower() not in chat_id:
                        other_chat_id = ichat
                
                if other_chat_id == None:
                    return None

                # # Otherwise remove the first user in the
                # other_chat_id = self._waiting_queue.pop(0)

                # if other_chat_id.strip() in chat_id.strip():
                #     self._waiting_queue.append(other_chat_id)

                #     # Try again if there is another user
                #     if self.get_queue_size == 1:
                #         return
                #     else:
                #         other_chat_id = self._waiting_queue.pop(0)

                other_username = self._chat_to_username.get(other_chat_id, other_chat_id[:8])
                
                # Create connection
                self.connect(chat_id, other_chat_id, username, other_username)
                print("connecteddddddddd\"", chat_id,"\"", other_chat_id,"\"", username, other_username)
                
                return (other_chat_id, other_username)
            
            # No one waiting, add to queue
            if chat_id not in self._waiting_queue:
                self._waiting_queue.append(chat_id)
            
            return None
        
        # Case 2: Just pair any two waiting players
        else:
            if len(self._waiting_queue) >= 2:
                chat_id1 = self._waiting_queue.pop(0)
                chat_id2 = self._waiting_queue.pop(0)
                username1 = self._chat_to_username.get(chat_id1, chat_id1[:8])
                username2 = self._chat_to_username.get(chat_id2, chat_id2[:8])
                
                self.connect(chat_id1, chat_id2, username1, username2)
                
                return (chat_id1, chat_id2)
            
            return None
    
    # ============================================
    # Direct Connection
    # ============================================
    
    def connect(self, chat_id1: str, chat_id2: str, 
                username1: str = None, username2: str = None) -> bool:
        """
        Connect two players directly
        """
        # Check if either is already connected
        if chat_id1 in self._connections or chat_id2 in self._connections:
            return False
        
        # Store usernames
        if username1:
            self._chat_to_username[chat_id1] = username1
        if username2:
            self._chat_to_username[chat_id2] = username2
        
        # Create connection
        connection = Connection(
            player1_chat_id=chat_id1,
            player2_chat_id=chat_id2,
            player1_username=username1 or chat_id1[:8],
            player2_username=username2 or chat_id2[:8],
            connected_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        # Store connection for both
        self._connections[chat_id1] = connection
        self._connections[chat_id2] = connection
        
        # Remove from queue if they were waiting
        self.remove_from_waiting_queue(chat_id1)
        self.remove_from_waiting_queue(chat_id2)
        
        return True
    
    def disconnect(self, chat_id: str) -> bool:
        """Disconnect a player"""
        if chat_id not in self._connections:
            return False
        
        connection = self._connections[chat_id]
        other_chat_id = connection.get_other_chat_id(chat_id)
        
        # Remove both
        del self._connections[chat_id]
        if other_chat_id and other_chat_id in self._connections:
            del self._connections[other_chat_id]
        
        return True
    
    # ============================================
    # Connection Requests (Optional)
    # ============================================
    
    def request_connection(self, from_chat_id: str, to_chat_id: str) -> bool:
        """Send connection request to specific player"""
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
        """Accept pending connection request"""
        # Find requester
        requester = None
        for req, target in self._pending_requests.items():
            if target == accepting_chat_id:
                requester = req
                break
        
        if not requester:
            return None
        
        requester_username = self._chat_to_username.get(requester)
        
        # Remove request
        del self._pending_requests[requester]
        
        # Create connection
        self.connect(requester, accepting_chat_id, requester_username, accepting_username)
        
        return (requester, accepting_chat_id, requester_username, accepting_username)
    
    def reject_request(self, chat_id: str) -> bool:
        """Reject pending connection request"""
        for req, target in list(self._pending_requests.items()):
            if target == chat_id:
                del self._pending_requests[req]
                return True
        return False
    
    def cancel_request(self, chat_id: str) -> bool:
        """Cancel own pending request"""
        if chat_id in self._pending_requests:
            del self._pending_requests[chat_id]
            return True
        return False
    
    def has_pending_request(self, chat_id: str) -> bool:
        """Check if player has pending request"""
        return chat_id in self._pending_requests
    
    def get_pending_request_target(self, chat_id: str) -> Optional[str]:
        """Get who this player requested"""
        return self._pending_requests.get(chat_id)
    
    def get_pending_request_from(self, chat_id: str) -> Optional[str]:
        """Get who requested this player"""
        for req, target in self._pending_requests.items():
            if target == chat_id:
                return req
        return None
    
    # ============================================
    # Message Forwarding
    # ============================================
    
    def forward_message(self, from_chat_id: str, message: str) -> Optional[str]:
        """Forward message to connected partner"""
        if from_chat_id not in self._connections:
            return None
        
        connection = self._connections[from_chat_id]
        connection.last_activity = datetime.now()
        
        return connection.get_other_chat_id(from_chat_id)
    
    # ============================================
    # Status & Info
    # ============================================
    
    def is_connected(self, chat_id: str) -> bool:
        """Check if player is connected"""
        return chat_id in self._connections
    
    def get_connection_info(self, chat_id: str) -> Optional[dict]:
        """Get connection details"""
        if chat_id not in self._connections:
            return None
        
        connection = self._connections[chat_id]
        return {
            'connected_to_chat_id': connection.get_other_chat_id(chat_id),
            'connected_to_username': connection.get_other_username(chat_id),
            'connected_since': connection.connected_at,
            'last_activity': connection.last_activity
        }
    
    def set_username(self, chat_id: str, username: str):
        """Store username for display"""
        if username:
            self._chat_to_username[chat_id] = username
    
    def get_username(self, chat_id: str) -> str:
        """Get username for display"""
        return self._chat_to_username.get(chat_id, chat_id[:8])
    
    def get_stats(self) -> dict:
        """Get statistics"""
        return {
            'active_connections': len(self._connections) // 2,
            'pending_requests': len(self._pending_requests),
            'waiting_players': len(self._waiting_queue),
            'connected_players': len(set(self._connections.keys()))
        }
    
    def cleanup_inactive(self, timeout_minutes: int = 30) -> int:
        """Disconnect inactive connections"""
        now = datetime.now()
        to_disconnect = []
        
        for chat_id, connection in self._connections.items():
            if (now - connection.last_activity).seconds > timeout_minutes * 60:
                to_disconnect.append(chat_id)
        
        for chat_id in to_disconnect:
            self.disconnect(chat_id)
        
        return len(to_disconnect)

# Global instance
connection_manager = ConnectionManager()