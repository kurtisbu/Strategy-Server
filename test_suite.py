import requests
import json
import os
from dotenv import load_dotenv
import time
from datetime import datetime

# Load environment variables
load_dotenv()

class TradingBotTester:
    def __init__(self):
        self.base_url = input("Enter your Replit URL (e.g., https://your-bot.username.repl.co): ").rstrip('/')
        self.webhook_secret = os.getenv('WEBHOOK_SECRET')

    def test_server_status(self):
        """Test if server is online and responding"""
        print("\n=== Testing Server Status ===")
        try:
            response = requests.get(f"{self.base_url}/")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {str(e)}")
            return False

    def test_credentials(self):
        """Test exchange API credentials"""
        print("\n=== Testing API Credentials ===")
        try:
            response = requests.get(f"{self.base_url}/check-credentials")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"Error: {str(e)}")

    def test_monitor(self):
        """Test monitor endpoint"""
        print("\n=== Testing Monitor Endpoint ===")
        try:
            response = requests.get(f"{self.base_url}/monitor")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"Error: {str(e)}")

    def test_forex_webhook(self):
        """Test forex trading webhook"""
        print("\n=== Testing Forex Trading Webhook ===")
        payload = {
            "secret": self.webhook_secret,
            "action": "buy",
            "symbol": "EUR_USD",
            "units": 100,
            "tp_pips": 50,
            "sl_pips": 30
        }

        headers = {
            'Content-Type': 'application/json'
        }

        try:
            print(f"Sending payload: {json.dumps(payload, indent=2)}")
            response = requests.post(
                f"{self.base_url}/webhook",
                json=payload,
                headers=headers
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"Error: {str(e)}")

    def test_crypto_webhook(self):
        """Test crypto trading webhook"""
        print("\n=== Testing Crypto Trading Webhook ===")
        payload = {
            "secret": self.webhook_secret,
            "action": "buy",
            "symbol": "BTCUSDT",
            "units": 0.001,
            "tp_pips": 50,
            "sl_pips": 30
        }

        headers = {
            'Content-Type': 'application/json'
        }

        try:
            print(f"Sending payload: {json.dumps(payload, indent=2)}")
            response = requests.post(
                f"{self.base_url}/webhook",
                json=payload,
                headers=headers
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"Error: {str(e)}")

    def monitor_trades(self, duration=60):
        """Monitor trades for a specified duration (in seconds)"""
        print(f"\n=== Monitoring Trades for {duration} seconds ===")
        start_time = time.time()

        try:
            while time.time() - start_time < duration:
                response = requests.get(f"{self.base_url}/monitor")
                data = response.json()

                print("\nCurrent Status:")
                print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                # Print Oanda positions
                oanda_data = data['exchanges']['oanda']
                print("\nOanda Positions:")
                if 'positions' in oanda_data and oanda_data['positions']:
                    for pos in oanda_data['positions']:
                        print(f"  {pos['instrument']}: {pos.get('unrealized_pl', 'N/A')}")
                else:
                    print("  No open positions")

                # Print Binance positions
                binance_data = data['exchanges']['binance']
                print("\nBinance Balances:")
                if 'balances' in binance_data:
                    for asset, balance in binance_data['balances'].items():
                        if float(balance['total']) > 0:
                            print(f"  {asset}: {balance['total']}")

                time.sleep(10)  # Wait 10 seconds before next check

        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
        except Exception as e:
            print(f"\nError during monitoring: {str(e)}")

def main():
    tester = TradingBotTester()

    while True:
        print("\nTrading Bot Test Suite")
        print("1. Test Server Status")
        print("2. Test API Credentials")
        print("3. Test Monitor Endpoint")
        print("4. Test Forex Trading Webhook")
        print("5. Test Crypto Trading Webhook")
        print("6. Monitor Trades (60s)")
        print("7. Run All Tests")
        print("8. Exit")

        choice = input("\nEnter your choice (1-8): ")

        if choice == '1':
            tester.test_server_status()
        elif choice == '2':
            tester.test_credentials()
        elif choice == '3':
            tester.test_monitor()
        elif choice == '4':
            tester.test_forex_webhook()
        elif choice == '5':
            tester.test_crypto_webhook()
        elif choice == '6':
            tester.monitor_trades()
        elif choice == '7':
            tester.test_server_status()
            tester.test_credentials()
            tester.test_monitor()
            tester.test_forex_webhook()
            tester.test_crypto_webhook()
            tester.monitor_trades(30)  # Monitor for 30 seconds
        elif choice == '8':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()