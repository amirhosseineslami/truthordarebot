import time
import requests
import os

MERCHANT_ID = "zibal"               # Your Zibal merchant ID
MERCHANT_ID = os.environ.get("MERCHANT_ID", "zibal" )

CALLBACK_URL =  os.environ.get("CALLBACK_URL")  # Optional (not used for polling)

def create_zibal_payment(amount_tomans: int):
    """
    Creates a payment request on Zibal.
    Returns {'success': bool, 'track_id': ..., 'payment_link': ...} or error.
    """
    amount_rials = amount_tomans * 10   # Zibal expects Rials
    url = "https://gateway.zibal.ir/v1/request"
    payload = {
        "merchant": MERCHANT_ID,
        "amount": amount_rials,
        "callbackUrl": CALLBACK_URL,
        "description": f"Purchase in Bot - {amount_tomans} Tomans",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        result = resp.json()
        if result.get('result') == 100:
            track_id = result['trackId']
            payment_link = f"https://gateway.zibal.ir/start/{track_id}"
            return {
                'success': True,
                'track_id': track_id,
                'payment_link': payment_link
            }
        else:
            error_msg = result.get('message', f"Error code: {result.get('result')}")
            return {'success': False, 'error': error_msg}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def check_zibal_payment(track_id: str):
    """Poll Zibal to see if payment is completed."""
    url = "https://gateway.zibal.ir/v1/verify"
    payload = {
        "merchant": MERCHANT_ID,
        "trackId": track_id
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        result = resp.json()
        if result.get('result') == 100:
            return {
                'paid': True,
                'ref_number': result.get('refNumber'),
                'card_number': result.get('cardNumber'),
                'amount': result.get('amount') // 10   # convert back to Tomans
            }
        elif result.get('result') == 202:
            return {'paid': False, 'status': 'pending'}
        else:
            return {'paid': False, 'error': f"Error code: {result.get('result')}"}
    except Exception as e:
        return {'paid': False, 'error': str(e)}