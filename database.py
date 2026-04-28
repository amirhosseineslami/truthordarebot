from peewee import MySQLDatabase
import os

DB_CONFIG = {
    'database': 'hopeful_mendeleev',
    'user': 'root',
    'password': 'hmnKSq0dnqbZcifjUNKcuYiM',
    'host': 'gina.iran.liara.ir',
    'port': 31884,
    'charset': 'utf8mb4'
}

db = MySQLDatabase(**DB_CONFIG)

def init_db(create_tables=True):
    try:
        db.connect()
        print("✅ Database connected")
        
        if create_tables:
            from models.user import User
            from models.offset import Offset
            from models.payment import Payment   # ✅ moved here
            
            db.create_tables([User, Offset, Payment], safe=True)
            print("✅ Tables created/verified")
        
        return db
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise

def close_db():
    if not db.is_closed():
        db.close()
        print("✅ Database closed")