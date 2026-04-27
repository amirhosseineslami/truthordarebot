import pymysql

conn = pymysql.connect(
    host='gina.iran.liara.ir',
    port=31884,
    user='root',
    password='hmnKSq0dnqbZcifjUNKcuYiM',
    database='hopeful_mendeleev',
    charset='utf8mb4'
)
cursor = conn.cursor()

# Create the users table with all columns (matching your User model)
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL UNIQUE,
    username VARCHAR(100),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    chat_id VARCHAR(100) NOT NULL,
    coin INT DEFAULT 0,
    score INT DEFAULT 0,
    level INT DEFAULT 1,
    game_state TEXT DEFAULT '{}',
    blocked_users TEXT DEFAULT '[]',
    sex INT DEFAULT 0,
    language VARCHAR(10) DEFAULT 'fa',
    subscription_date BIGINT DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    is_banned BOOLEAN DEFAULT 0,
    total_games_played INT DEFAULT 0,
    total_wins INT DEFAULT 0,
    total_losses INT DEFAULT 0,
    total_messages INT DEFAULT 0,
    last_seen BIGINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    age INT DEFAULT NULL,
    city VARCHAR(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")
conn.commit()
cursor.close()
conn.close()
print("✅ Users table created successfully")