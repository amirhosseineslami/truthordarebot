import pymysql

# Your database connection details (from .env or hardcoded)
conn = pymysql.connect(
    host='gina.iran.liara.ir',
    port=31884,
    user='root',
    password='hmnKSq0dnqbZcifjUNKcuYiM',
    database='hopeful_mendeleev',
    charset='utf8mb4'
)

cursor = conn.cursor()

# List of columns that should exist in the remote `users` table
columns_to_add = {
    'blocked_users': "TEXT DEFAULT '[]'",
    'game_state': "TEXT DEFAULT '{}'",
    'language': "VARCHAR(10) DEFAULT 'fa'",
    'sex': "INT DEFAULT 0",
    'total_games_played': "INT DEFAULT 0",
    'total_wins': "INT DEFAULT 0",
    'total_losses': "INT DEFAULT 0",
    'total_messages': "INT DEFAULT 0",
    'last_seen': "BIGINT DEFAULT 0",
    'is_active': "BOOLEAN DEFAULT 1",
    'is_banned': "BOOLEAN DEFAULT 0",
    'subscription_date': "BIGINT DEFAULT 0",
    'score': "INT DEFAULT 0",
    'level': "INT DEFAULT 1",
    'coin': "INT DEFAULT 100",
    'first_name': "VARCHAR(255)",
    'last_name': "VARCHAR(255)",
    'username': "VARCHAR(100)",
}

# Check existing columns
cursor.execute("SHOW COLUMNS FROM users")
existing = {row[0] for row in cursor.fetchall()}

for col, definition in columns_to_add.items():
    if col not in existing:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            print(f"✅ Added column {col}")
        except Exception as e:
            print(f"⚠️ Failed to add {col}: {e}")

conn.commit()
cursor.close()
conn.close()
print("Done.")