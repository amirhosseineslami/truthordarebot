from peewee import CharField, IntegerField, DateTimeField
from .base import BaseModel
from datetime import datetime

class Offset(BaseModel):
    __tablename__ = 'offsets'
    
    next_offset_id = CharField(max_length=100, default='0')
    message_count = IntegerField(default=0)
    last_request_time = DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = 'offsets'
    
    @classmethod
    def get(cls) -> str:
        """Get next_offset_id - returns '0' if no record exists"""
        record = cls.select().first()
        return record.next_offset_id if record else '0'
    
    @classmethod
    def store(cls, next_offset_id: str, message_count: int = 0):
        """Store next_offset_id"""
        cls.delete().execute()  # Remove old record
        cls.create(
            next_offset_id=next_offset_id, 
            message_count=message_count,
            last_request_time=datetime.now()
        )