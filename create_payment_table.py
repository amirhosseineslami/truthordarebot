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
cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    chat_id VARCHAR(100) NOT NULL,
    track_id VARCHAR(100) NOT NULL UNIQUE,
    amount INT DEFAULT 0,
    product_id VARCHAR(50) DEFAULT 'coins',
    product_quantity INT DEFAULT 0,
    product_name VARCHAR(255) DEFAULT '',
    status VARCHAR(20) DEFAULT 'pending',
    ref_number VARCHAR(100),
    card_number VARCHAR(20),
    paid_at BIGINT DEFAULT 0,
    expires_at BIGINT DEFAULT 0,
    metadata TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_status (user_id, status),
    INDEX idx_track_id (track_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")
conn.commit()
cursor.close()
conn.close()
print("✅ Payments table created")