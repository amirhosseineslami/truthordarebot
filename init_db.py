from database import init_db

# This will create all tables including offsets
init_db(create_tables=True)
print("✅ Database tables created")