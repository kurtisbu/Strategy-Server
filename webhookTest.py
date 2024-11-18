import requests
import os
import json
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

def calculate_sl_tp(price, action, pips=50):
    """Calculate stop loss and take profit prices based on pips"""
    # Convert pips to price movement (0.0001 for most forex pairs)
    pip_value = 0.0001
    pip_movement = pips * pip_value

    if action.lower() == 'buy':
        stop_loss = round(price - pip_movement, 4)
        take_profit = round(price + pip_movement, 4)
    else:  # sell
        stop_loss = round(price + pip_movement, 4)
        take_profit = round(price - pip_movement, 4)

    return stop_loss, take_profit

def test_trade(webhook_url, payload, test_name="Default Test"):
    """Execute a test trade and print results"""
    print(f"\n=== Running Test: {test_name} ===")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    headers = {
        'Content-Type': 'application/json',
        'X-Webhook-Secret': WEBHOOK_SECRET
    }

    try:
        print(f"Sending request to: {webhook_url}")
        response = requests.post(webhook_url, json=payload, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def run_test():
    webhook_url = input("Enter your Replit webhook URL: ")

    # Current price - in a real system, you'd get this from the API
    current_price = 1.0800  # Example price for EUR/USD
    action = "buy"  # or "sell"

    # Calculate SL/TP based on 50 pips
    stop_loss, take_profit = calculate_sl_tp(current_price, action, 50)

    # Test trade with 50 pip SL/TP
    test_payload = {
        "strategy": "MA_Cross",
        "action": action,
        "symbol": "EUR_USD",
        "units": 100,
        "price": current_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "timestamp": datetime.now().isoformat()
    }

    print("\nExecuting market order...")
    print(f"Stop Loss: {stop_loss} ({50} pips)")
    print(f"Take Profit: {take_profit} ({50} pips)")
    test_trade(webhook_url, test_payload, "Market Order with 50 pip SL/TP")

if __name__ == "__main__":
    run_test()