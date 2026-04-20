from peewee import Model, DateTimeField
from database import db
from datetime import datetime

class BaseModel(Model):
    """Base model with common timestamp fields"""
    
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    
    def save(self, *args, **kwargs):
        """Override save to update updated_at automatically"""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    class Meta:
        database = db
        abstract = True