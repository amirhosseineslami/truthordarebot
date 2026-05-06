import threading
import time
from typing import Dict, Optional
from bot.models.payment import Payment
from bot.services.payment_service import check_zibal_payment
from bot.models.sync_manager import SyncManager,UserManager
import bot.models.database as database 

class PaymentManager:
    def __init__(self, sync_manager:SyncManager, user_manager:UserManager, send_message_func):
        self.sync = sync_manager
        self.user_mgr = user_manager
        self.send_message = send_message_func   # your bot's send function
        self._polling_threads = {}
        self._stop_polling = {}
        self._ensure_tables()

        

        
    PRODUCTS = {
        'coins_5': {
            'name': '🧩 پک شروع (5 سکه) (تخفیف: 4,000 تومان)',
            'en': '🧩 Starter Pack (5 coins) (save 4,000 Toman)',
            'amount': 9900,
            'coins': 5
        },
        'coins_50': {
            'name': '⭐ استاندارد (50 سکه)',
            'en': '⭐ Standard (50 coins)',
            'amount': 139000,
            'coins': 50
        },
        'coins_100': {
            'name': '🔥 بیشترین فروش (100 سکه) (تخفیف: 89,000 تومان)',
            'en': '🔥 Best Seller (100 coins) (save 89,000 Toman)',
            'amount': 189000,
            'coins': 100
        },
        'coins_250': {
            'name': '🚀 پک حرفه ای (250 سکه) (تخفیف: 296,000 تومان)',
            'en': '🚀 Pro Pack (250 coins) (save 296,000 Toman)',
            'amount': 399000,
            'coins': 250
        },
        'coins_600': {
            'name': '👑 پک اسطوره ای (600 سکه) (تخفیف: 769,000 تومان)',
            'en': '👑 Legend Pack (600 coins) (save 769,000 Toman)',
            'amount': 899000,
            'coins': 600
        }
    }

    def _ensure_tables(self):
        from bot.models.payment import Payment
        # Make sure the database is connected first
        if database.db.is_closed():
            database.db.connect()
        database.db.create_tables([Payment], safe=True)


    def get_products(self):
        return self.PRODUCTS

    def create_purchase(self, user, chat_id: str, product_id: str) -> dict:
        if product_id not in self.PRODUCTS:
            return {'success': False, 'error': 'محصول نامعتبر'}
        prod = self.PRODUCTS[product_id]

        result = Payment.create_payment(
            user_id=user.user_id,
            chat_id=chat_id,
            amount_tomans=prod['amount'],
            product_id=product_id,
            product_quantity=prod.get('coins', prod.get('premium_days', 0)),
            product_name=prod['name']
        )
        if result['success']:
            # Start background polling
            self._start_polling(user.user_id, result['track_id'], chat_id, prod['name'])
        return result

    def _start_polling(self, user_id: str, track_id: str, chat_id: str, product_name: str):
        if user_id in self._polling_threads:
            return

        def poll():
            for attempt in range(60):   # 60 * 10 = 600 seconds (10 minutes)
                if self._stop_polling.get(user_id, False):
                    break
                time.sleep(10)

                # Check payment status
                payment = Payment.get_or_none(Payment.track_id == track_id)
                if payment and payment.status == 'paid':
                    self._grant_purchase(payment)
                    self.send_message(chat_id, f"✅ پرداخت {product_name} با موفقیت انجام شد!\n🔢 شماره پیگیری: {payment.ref_number}")
                    self._stop_polling_for_user(user_id)
                    break

                # Check expiry
                import time as tm
                if payment and payment.expires_at < int(tm.time()):
                    payment.status = 'expired'
                    payment.save()
                    self.send_message(chat_id, "⏰ لینک پرداخت منقضی شد. لطفاً دوباره /buy را بزنید.")
                    self._stop_polling_for_user(user_id)
                    break

        self._stop_polling[user_id] = False
        thread = threading.Thread(target=poll, daemon=True)
        thread.start()
        self._polling_threads[user_id] = thread

    def _stop_polling_for_user(self, user_id: str):
        self._stop_polling[user_id] = True
        self._polling_threads.pop(user_id, None)
        self._stop_polling.pop(user_id, None)

    def _grant_purchase(self, payment: Payment):
        user = self.sync.find_user(user_id=payment.user_id)
        if not user:
            return
        prod = self.PRODUCTS.get(payment.product_id, {})
        if payment.product_id.startswith('coins'):
            self.user_mgr.add_coins(user, payment.product_quantity)
            self.sync.update_user(user)
        elif payment.product_id.startswith('premium'):
            self.user_mgr.extend_subscription(user,payment.product_quantity)

    @classmethod
    def get_pending_payments(cls, user_id: str = None):
        """Get all pending payments, optionally filtered by user_id"""
        query = cls.select().where(cls.status == 'pending')
        if user_id:
            query = query.where(cls.user_id == user_id)
        return list(query.order_by(cls.created_at.desc()))

    def manual_check(self, user_id: str) -> dict:
        """Called when user types /check"""

        # Get the most recent pending payment for this user
        pending = list(Payment.select()
                    .where((Payment.user_id == user_id) & (Payment.status == 'pending'))
                    .order_by(Payment.created_at.desc())
                    .limit(1))
        
        if not pending:
            return {'success': False, 'error': 'No pending payment found'}
        
        payment = pending[0]
        result = Payment.verify_payment(payment.track_id)
        
        if result.get('success') and not result.get('already_paid'):
            self._grant_purchase(payment)
            self._stop_polling_for_user(user_id)
        
        return result