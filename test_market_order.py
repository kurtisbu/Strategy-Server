import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

def test_market_order(webhook_url):
    """Execute a test market order with variable TP/SL"""

    # Test payload with different TP and SL distances
    payload = {
        "action": "buy",
        "symbol": "EUR_USD",
        "units": 100,
        "tp_pips": 60,  # Taking profit at 60 pips
        "sl_pips": 30   # Stop loss at 30 pips
    }

    headers = {
        'Content-Type': 'application/json',
        'X-Webhook-Secret': WEBHOOK_SECRET
    }

    try:
        print("\n=== Executing Market Order with Variable TP/SL ===")
        print(f"Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(webhook_url, json=payload, headers=headers)

        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("\nTrade Summary:")
            data = response.json()['trade_details']
            print(f"Entry Price: {data['filled_price']}")
            print(f"Stop Loss: {data['stop_loss']} ({data['sl_pips']} pips)")
            print(f"Take Profit: {data['take_profit']} ({data['tp_pips']} pips)")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    webhook_url = input("Enter your Replit webhook URL: ")
    test_market_order(webhook_url)