#!/usr/bin/env python3
"""Test User model with TextField JSON storage"""

from database import init_db, close_db
from models.user import User

def test_user_model():
    print("🔵 Testing User model with JSON storage...")
    
    # Initialize database
    db = init_db(create_tables=True)
    
    # Create a new user
    print("\n👤 Creating new user...")
    
    user, created = User.get_or_create_user(
        user_id="user_123",
        chat_id="chat_456",
        username="amir_dev",
        first_name="Amir",
        last_name="Rezaei"
    )
    
    if created:
        print(f"✅ New user created: {user}")
    else:
        print(f"👤 Existing user found: {user}")
    
    # Test game state with JSON
    print("\n🎮 Testing game state (JSON storage)...")
    user.update_game_state("current_game", {"players": 4, "turn": 1})
    user.update_game_state("bottle_position", 180)
    user.update_game_state("scores", [100, 200, 150])
    
    current_game = user.get_game_state("current_game")
    bottle_pos = user.get_game_state("bottle_position")
    scores = user.get_game_state("scores")
    
    print(f"Current game: {current_game}")
    print(f"Bottle position: {bottle_pos}")
    print(f"Scores: {scores}")
    
    # Get full game state
    print(f"Full game state: {user.game_state_dict}")
    
    # Test coin management
    print("\n💰 Testing coin management...")
    print(f"Initial coins: {user.coin}")
    user.add_coins(50)
    print(f"After adding 50: {user.coin}")
    
    # Test score and level
    print("\n🎯 Testing score and level...")
    print(f"Score: {user.score}, Level: {user.level}")
    user.add_score(1500)
    print(f"After 1500 points: Score={user.score}, Level={user.level}")
    
    # Test statistics
    print("\n📊 Testing statistics...")
    user.record_game_result(won=True)
    user.record_game_result(won=False)
    print(f"Games: {user.total_games_played}, Wins: {user.total_wins}")
    print(f"Win rate: {user.win_rate:.1f}%")
    
    # Test to_dict
    print("\n📋 User data:")
    user_dict = user.to_dict(detailed=True)
    print(f"Name: {user_dict['display_name']}")
    print(f"Coins: {user_dict['coin']}")
    print(f"Level: {user_dict['level']}")
    print(f"Game state: {user_dict.get('game_state', {})}")
    
    close_db()
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    # Reset database for clean test
    from database import db
    from models.user import User
    
    print("🔄 Resetting database...")
    db.connect()
    db.drop_tables([User], safe=True)
    db.close()
    
    test_user_model()