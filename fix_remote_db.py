import pymysql

conn = pymysql.connect(
    host='gina.iran.liara.ir',
    port=31884,
    user='root',
    password='hmnKSq0dnqbZcifjUNKcuYiM',
    database='hopeful_mendeleev'
)
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE users ADD COLUMN age INT DEFAULT NULL")
    print("✅ Added column 'age'")
except Exception as e:
    print(f"age column already exists or error: {e}")
try:
    cursor.execute("ALTER TABLE users ADD COLUMN city VARCHAR(100) DEFAULT NULL")
    print("✅ Added column 'city'")
except Exception as e:
    print(f"city column already exists or error: {e}")

conn.commit()
cursor.close()
conn.close()
print("Done.")