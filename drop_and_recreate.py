import pymysql
from database import db as remote_db

remote_db.execute_sql("DROP TABLE IF EXISTS users")
print("Table dropped. Next restart will recreate it with all columns.")