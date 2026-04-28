import zibal.zibal as zibal
import time
import requests

merchant_id = "zibal"  # Your merchant ID
callback_url = "https://hibilit.ir/callback"  # Your callback URL (won't be used for polling)

def create_payment(amount_tomans):
    """Step 1: Create payment and return payment link"""
    zb = zibal.zibal(merchant_id, callback_url=callback_url)
    
    # Convert Tomans to Rials (Zibal expects Rials)
    amount_rials = amount_tomans * 10
    
    # Create payment request
    request_to_zibal = zb.request(amount_rials)
    
    if request_to_zibal['result'] == 100:
        track_id = request_to_zibal['trackId']
        payment_link = f"https://gateway.zibal.ir/start/{track_id}"
        
        print(f"✅ Payment created successfully!")
        print(f"📝 Track ID: {track_id}")
        print(f"🔗 Payment link: {payment_link}")
        print(f"\n👤 Send this link to your user:")
        print(f"   {payment_link}")
        
        return {
            'success': True,
            'track_id': track_id,
            'payment_link': payment_link
        }
    else:
        print(f"❌ Error: {zb.request_result(request_to_zibal['result'])}")
        return {
            'success': False,
            'error_code': request_to_zibal['result']
        }

def check_payment_status(track_id):
    """Step 2: Poll Zibal to check if user has paid"""
    zb = zibal.zibal(merchant_id, callback_url=callback_url)
    verify_result = zb.verify(track_id)
    
    if verify_result['result'] == 100:
        # Payment successful!
        return {
            'paid': True,
            'ref_number': verify_result.get('refNumber'),
            'card_number': verify_result.get('cardNumber'),
            'amount': verify_result.get('amount')
        }
    elif verify_result['result'] == 202:
        # Still pending, waiting for user to pay
        return {
            'paid': False,
            'status': 'pending'
        }
    else:
        # Failed or error
        return {
            'paid': False,
            'status': 'failed',
            'error': zb.verify_result(verify_result['result'])
        }

def poll_for_payment(track_id, timeout_seconds=300, check_interval=5):
    """
    Automatically poll Zibal until payment is completed or timeout
    
    Args:
        track_id: The track ID from create_payment()
        timeout_seconds: Maximum time to wait (default 5 minutes)
        check_interval: How often to check (default 5 seconds)
    """
    start_time = time.time()
    attempts = 0
    
    print(f"\n🔄 Polling for payment {track_id}...")
    print(f"⏱️  Will check every {check_interval} seconds for {timeout_seconds} seconds")
    
    while time.time() - start_time < timeout_seconds:
        attempts += 1
        status = check_payment_status(track_id)
        
        if status['paid']:
            print(f"\n✅ Payment confirmed after {attempts} checks!")
            print(f"📋 Reference Number: {status['ref_number']}")
            print(f"💳 Card Number: {status['card_number']}")
            return status
            
        elif status['status'] == 'failed':
            print(f"\n❌ Payment failed: {status.get('error', 'Unknown error')}")
            return status
            
        else:
            # Still pending
            elapsed = int(time.time() - start_time)
            print(f"⏳ Check #{attempts}: Still pending... (Elapsed: {elapsed}s)")
            
        time.sleep(check_interval)
    
    print(f"\n⏰ Timeout reached after {timeout_seconds} seconds")
    return {'paid': False, 'status': 'timeout'}

# ========== EXAMPLE USAGE ==========

# Example 1: Just create payment and get link
print("=" * 50)
print("EXAMPLE 1: Create payment")
print("=" * 50)
payment = create_payment(10000)  # 10,000 Tomans

if payment['success']:
    # Send this link to your user via Telegram, SMS, etc.
    user_link = payment['payment_link']
    print(f"\n📤 Give this link to your user: {user_link}")
    
    # Example 2: Poll for payment (automatic)
    print("\n" + "=" * 50)
    print("EXAMPLE 2: Poll for payment")
    print("=" * 50)
    result = poll_for_payment(payment['track_id'], timeout_seconds=60, check_interval=3)
    
    if result['paid']:
        print("\n🎉 Payment verified! Grant access to user.")
    else:
        print("\n⚠️ Payment not completed within timeout.")