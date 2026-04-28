from peewee import CharField, IntegerField, BigIntegerField, BooleanField, DateTimeField, TextField
from .base import BaseModel
from datetime import datetime, timedelta
import time
from zibal_helper import create_zibal_payment

class Payment(BaseModel):
    __tablename__ = 'payments'

    user_id = CharField(max_length=100, index=True)
    chat_id = CharField(max_length=100, index=True)

    track_id = CharField(max_length=100, unique=True, index=True)
    amount = IntegerField(default=0)          # in Tomans (not Rials)

    product_id = CharField(max_length=50, default='coins')
    product_quantity = IntegerField(default=0)
    product_name = CharField(max_length=255, default='')

    status = CharField(max_length=20, default='pending')  # pending, paid, failed, expired
    ref_number = CharField(max_length=100, null=True)
    card_number = CharField(max_length=20, null=True)

    paid_at = BigIntegerField(default=0)
    expires_at = BigIntegerField(default=0)   # timestamp

    metadata = TextField(default='{}')

    class Meta:
        table_name = 'payments'
        indexes = ((('user_id', 'status'), False), (('track_id',), True))

    @classmethod
    def create_payment(cls, user_id: str, chat_id: str, amount_tomans: int,
                       product_id: str, product_quantity: int, product_name: str,
                       expires_minutes: int = 30) -> dict:
        """Create payment record and Zibal request"""

        # Call Zibal to get track_id and payment link
        result = create_zibal_payment(amount_tomans)
        if not result['success']:
            return result

        now = int(time.time())
        payment = cls.create(
            user_id=user_id,
            chat_id=chat_id,
            track_id=result['track_id'],
            amount=amount_tomans,
            product_id=product_id,
            product_quantity=product_quantity,
            product_name=product_name,
            status='pending',
            expires_at=now + expires_minutes * 60,
            metadata='{}'
        )
        return {
            'success': True,
            'track_id': payment.track_id,
            'payment_link': result['payment_link'],
            'amount': amount_tomans   # <-- add this line
        }

    @classmethod
    def verify_payment(cls, track_id: str) -> dict:
        """Verify payment via Zibal (called by polling)"""
        import time
        from zibal_helper import check_zibal_payment

        try:
            payment = cls.get(cls.track_id == track_id)
        except cls.DoesNotExist:
            return {'success': False, 'error': 'Payment record not found'}

        if payment.status == 'paid':
            return {'success': True, 'already_paid': True}

        if payment.expires_at < int(time.time()):
            payment.status = 'expired'
            payment.save()
            return {'success': False, 'error': 'Payment link expired'}

        # Check with Zibal
        status = check_zibal_payment(track_id)
        if status.get('paid'):
            payment.status = 'paid'
            payment.ref_number = status.get('ref_number')
            payment.card_number = status.get('card_number')
            payment.paid_at = int(time.time())
            payment.save()
            return {
                'success': True,
                'amount': payment.amount,
                'ref_number': payment.ref_number,
                'product_id': payment.product_id,
                'product_quantity': payment.product_quantity
            }
        else:
            return {'success': False, 'error': status.get('error', 'Still pending')}