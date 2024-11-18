"""
Trading Bot Server
Main application file handling web routes and trading functionality.
Supports both Forex (Oanda) and Crypto (Binance) trading.
"""

# Standard library imports
import json
import os
from datetime import datetime
from typing import Dict, Any, Tuple
from collections import deque
from pathlib import Path

from datetime import datetime, timedelta
import pytz

# Third-party imports
from flask import Flask, request, jsonify
import logging

# Local imports
from exchange_handler import MultiExchangeHandler

# ===============================
# Configuration and Setup
# ===============================

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("debug_log.txt"),
              logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize exchange handler
exchange_handler = MultiExchangeHandler()

# Initialize storage for recent activity
MAX_HISTORY_SIZE = 50
recent_webhooks = deque(maxlen=MAX_HISTORY_SIZE)
recent_trades = deque(maxlen=MAX_HISTORY_SIZE)

# ===============================
# Helper Functions
# ===============================


def initialize_log_file(log_path: Path) -> list:
    """Initialize or read from log file"""
    try:
        if not log_path.exists():
            with open(log_path, 'w') as f:
                init_message = f"{datetime.now().isoformat()} - Log file initialized\n"
                f.write(init_message)
            return ["Log file initialized"]

        with open(log_path, 'r') as f:
            all_logs = [line.strip() for line in f.readlines() if line.strip()]
            return all_logs[-20:] if all_logs else ["No logs available"]
    except Exception as e:
        logger.error(f"Error handling log file: {str(e)}")
        return [f"Error reading logs: {str(e)}"]


def validate_webhook_data(data: Dict) -> Tuple[bool, str]:
    """Validate incoming webhook data"""
    # Verify secret
    if data.get('secret') != os.getenv('WEBHOOK_SECRET'):
        return False, "Unauthorized"

    # Check required fields
    required_fields = ['action', 'symbol', 'risk']
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    return True, ""



def is_forex_market_open() -> tuple[bool, datetime | None]:
    """
    Check if forex market is open and calculate next open time if closed.
    Returns tuple of (is_open: bool, next_open: datetime | None)

    Forex Market Hours (EST):
    - Opens: Sunday 5:00 PM
    - Closes: Friday 5:00 PM
    - Closed: Friday 5:00 PM to Sunday 5:00 PM
    """
    # Get current time in EST
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)

    # Get current weekday (0 = Monday, 6 = Sunday)
    weekday = now.weekday()
    current_hour = now.hour
    current_minute = now.minute

    # Convert to 24-hour time for comparison
    current_time = current_hour + (current_minute / 60)

    # Market closed scenarios
    if weekday == 4 and current_time >= 17:  # Friday after 5 PM
        # Next open is Sunday at 5 PM
        days_to_add = 2
        next_open = now.replace(hour=17, minute=0, second=0,
                                microsecond=0) + timedelta(days=days_to_add)
        return False, next_open

    elif weekday == 5:  # Saturday
        # Next open is Sunday at 5 PM
        days_to_add = 1
        next_open = now.replace(hour=17, minute=0, second=0,
                                microsecond=0) + timedelta(days=days_to_add)
        return False, next_open

    elif weekday == 6 and current_time < 17:  # Sunday before 5 PM
        # Opens today at 5 PM
        next_open = now.replace(hour=17, minute=0, second=0, microsecond=0)
        return False, next_open

    # Market is open
    return True, None


def get_market_hours_status() -> dict:
    """Get detailed market hours status including next market events"""
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)

    is_open, next_open = is_forex_market_open()

    # Calculate next close if market is open
    next_close = None
    if is_open:
        if now.weekday() == 4:  # Friday
            next_close = now.replace(hour=17,
                                     minute=0,
                                     second=0,
                                     microsecond=0)
        else:
            # Next close is today at 5 PM if we're approaching it, otherwise tomorrow
            next_close = now.replace(hour=17,
                                     minute=0,
                                     second=0,
                                     microsecond=0)
            if next_close < now:
                next_close += timedelta(days=1)

    return {
        'is_open': is_open,
        'current_time': now,
        'next_open': next_open,
        'next_close': next_close,
        'timezone': 'EST',
        'current_session': get_trading_session(now)
    }


def get_trading_session(time: datetime) -> str:
    """
    Determine current trading session based on time

    Trading Sessions (EST):
    - Sydney: 5:00 PM - 2:00 AM
    - Tokyo: 7:00 PM - 4:00 AM
    - London: 3:00 AM - 12:00 PM
    - New York: 8:00 AM - 5:00 PM
    """
    hour = time.hour

    sessions = []

    # Check each session (overlaps are possible)
    if 17 <= hour <= 23 or hour < 2:  # 5 PM - 2 AM
        sessions.append('Sydney')

    if 19 <= hour <= 23 or hour < 4:  # 7 PM - 4 AM
        sessions.append('Tokyo')

    if 3 <= hour < 12:  # 3 AM - 12 PM
        sessions.append('London')

    if 8 <= hour < 17:  # 8 AM - 5 PM
        sessions.append('New York')

    return ' & '.join(sessions) if sessions else 'No active session'


# ===============================
# Route Handlers
# ===============================


@app.route('/')
def home():
    """Home endpoint providing API status and available endpoints"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'dashboard': '/dashboard',
            'webhook': '/webhook (POST)',
            'monitor': '/monitor (GET)',
            'market_status': '/market-status (GET)'
        }
    })


@app.route('/dashboard')
def dashboard():
    """Serve the trading dashboard interface"""
    try:
        templates_dir = Path('templates')
        templates_dir.mkdir(exist_ok=True)

        dashboard_path = templates_dir / 'dashboard.html'
        if dashboard_path.exists():
            return dashboard_path.read_text()
        return "Dashboard template not found. Please create templates/dashboard.html", 404
    except Exception as e:
        logger.error(f"Error serving dashboard: {str(e)}")
        return str(e), 500


@app.route('/market-status')
def market_status():
    """
    Get current forex market status, hours, and session information.
    Returns market open/closed status, next market events, and current trading session.
    """
    try:
        status = get_market_hours_status()

        response = {
            'market_open':
            status['is_open'],
            'current_time':
            status['current_time'].isoformat(),
            'next_open':
            status['next_open'].isoformat() if status['next_open'] else None,
            'next_close':
            status['next_close'].isoformat() if status['next_close'] else None,
            'trading_hours':
            "Sunday 5:00 PM EST to Friday 5:00 PM EST",
            'current_session':
            status['current_session'],
            'timezone':
            status['timezone'],
            'sessions': {
                'Sydney': '5:00 PM - 2:00 AM EST',
                'Tokyo': '7:00 PM - 4:00 AM EST',
                'London': '3:00 AM - 12:00 PM EST',
                'New York': '8:00 AM - 5:00 PM EST'
            },
            'message':
            "Market is open" if status['is_open'] else "Market is closed"
        }

        logger.info(
            f"Market status checked: {'Open' if status['is_open'] else 'Closed'}"
        )
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in market status: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error',
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/monitor')
def monitor():
    """Provide current trading status across all exchanges"""
    try:
        # Initialize response structure
        response_data = {
            'status': 'online',
            'timestamp': datetime.now().isoformat(),
            'exchanges': {
                'oanda': {
                    'error': None,
                    'balance': 0,
                    'open_trades_count': 0,
                    'floating_pl': 0,
                    'realized_pl': 0,
                    'positions': []
                },
                'binance': {
                    'error': None,
                    'total_value_usdt': 0,
                    'trading_enabled': False,
                    'balances': {}
                }
            },
            'recent_trades': list(recent_trades)
        }

        # Get exchange data
        for exchange, method in [
            ('oanda', exchange_handler.get_oanda_account_summary),
            ('binance', exchange_handler.get_binance_account_summary)
        ]:
            try:
                exchange_data = method()
                response_data['exchanges'][exchange].update(exchange_data)
            except Exception as e:
                response_data['exchanges'][exchange]['error'] = str(e)
                logger.error(f"{exchange.title()} error: {str(e)}")

        # Add logs
        response_data['recent_logs'] = initialize_log_file(
            Path('debug_log.txt'))
        logger.info("Monitor endpoint accessed")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in monitor endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming trading signals from TradingView"""
    logger.info("Webhook endpoint hit")
    logger.info(f"Headers: {dict(request.headers)}")

    try:
        # Parse and validate webhook data
        webhook_data = request.json
        logger.info(
            f"Parsed webhook data: {json.dumps(webhook_data, indent=2)}")

        is_valid, error_message = validate_webhook_data(webhook_data)
        if not is_valid:
            return jsonify({'error': error_message}), 401

        # Remove secret and execute trade
        webhook_data.pop('secret', None)
        trade_response = exchange_handler.execute_trade(webhook_data)

        # Store trade history
        timestamp = datetime.now().isoformat()
        recent_webhooks.append({'timestamp': timestamp, 'data': webhook_data})
        recent_trades.append({
            'timestamp': timestamp,
            'details': trade_response
        })

        return jsonify({
            'status': 'success',
            'message': 'Trade executed successfully',
            'data': trade_response
        }), 200

    except Exception as e:
        error_msg = f"Error processing webhook: {str(e)}"
        logger.error(error_msg)
        return jsonify({'error': error_msg}), 500


@app.route('/test-log')
def test_log():
    """Generate test log entries"""
    logger.info("Test log entry")
    logger.warning("Test warning entry")
    logger.error("Test error entry")
    return jsonify({'status': 'success', 'message': 'Test logs created'})


# ===============================
# Main Entry Point
# ===============================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
