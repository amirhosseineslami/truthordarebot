import requests

response = requests.post(
    "https://gateway.zibal.ir/v1/request",
    json={
        "merchant": "67dd1e096f3803e5a6970b65",  # Your merchant ID
        "amount": 10000,      # Minimum amount for testing
        "callbackUrl": "https://hibilit.ir/callback",  # Your callback URL
        "description": "Test payment"
    }
)

print(response.json())
# If you get result: 100 → Success! Your IP is authorized
# If you get result: 102 → IP not authorized