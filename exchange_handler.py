from binance.client import Client
from binance.exceptions import BinanceAPIException
from oandapyV20 import API
from oandapyV20.exceptions import V20Error
from oandapyV20.endpoints.orders import OrderCreate
from oandapyV20.endpoints.trades import TradeCRCDO
from typing import Dict, Any, Tuple
import os
import logging
from oandapyV20.endpoints.accounts import AccountSummary, AccountDetails
from oandapyV20.endpoints.positions import OpenPositions


class MultiExchangeHandler:

    def __init__(self):
        # Initialize Oanda
        self.oanda_api = API(access_token=os.getenv('OANDA_API_KEY'),
                             environment=os.getenv('OANDA_ENVIRONMENT',
                                                   'practice'))
        self.oanda_account_id = os.getenv('OANDA_ACCOUNT_ID')

        # Initialize Binance
        self.binance_client = Client(
            api_key=os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('BINANCE_API_SECRET'),
            testnet=os.getenv('BINANCE_TESTNET', 'True').lower() == 'true')

        self.logger = logging.getLogger(__name__)

    def determine_exchange(self, symbol: str) -> str:
        """Determine which exchange to use based on the symbol"""
        if '_' in symbol:
            return 'oanda'
        elif 'USDT' in symbol or 'BTC' in symbol:
            return 'binance'
        else:
            raise ValueError(f"Cannot determine exchange for symbol: {symbol}")

    def execute_trade(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade on appropriate exchange"""
        try:
            exchange = self.determine_exchange(data['symbol'])
            if exchange == 'oanda':
                return self.execute_oanda_trade(data)
            else:
                return self.execute_binance_trade(data)
        except Exception as e:
            self.logger.error(f"Trade execution error: {str(e)}")
            raise

    def execute_oanda_trade(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade on Oanda"""
        try:
            # Create market order
            order_data = {
                "order": {
                    "type":
                    "MARKET",
                    "instrument":
                    data['symbol'],
                    "units":
                    str(data['units'] if data['action'].lower() ==
                        'buy' else -data['units']),
                    "timeInForce":
                    "FOK",
                    "positionFill":
                    "DEFAULT"
                }
            }

            order_request = OrderCreate(self.oanda_account_id, data=order_data)
            response = self.oanda_api.request(order_request)

            # Get filled price and trade ID
            filled_price = float(response['orderFillTransaction']['price'])
            trade_id = str(
                response['orderFillTransaction']['tradeOpened']['tradeID'])

            # Set SL/TP if provided
            if 'sl_pips' in data and 'tp_pips' in data:
                sl_price, tp_price = self.calculate_sl_tp(
                    filled_price, data['action'], float(data['sl_pips']),
                    float(data['tp_pips']))

                # Modify trade with SL/TP
                sl_tp_data = {
                    "stopLoss": {
                        "price": str(sl_price),
                        "timeInForce": "GTC"
                    },
                    "takeProfit": {
                        "price": str(tp_price),
                        "timeInForce": "GTC"
                    }
                }

                modify_request = TradeCRCDO(accountID=self.oanda_account_id,
                                            tradeID=trade_id,
                                            data=sl_tp_data)
                modification = self.oanda_api.request(modify_request)

            return {
                'status': 'success',
                'exchange': 'oanda',
                'order': response,
                'filled_price': filled_price,
                'trade_id': trade_id,
                'sl_price': sl_price if 'sl_pips' in data else None,
                'tp_price': tp_price if 'tp_pips' in data else None
            }

        except V20Error as e:
            self.logger.error(f"Oanda API error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error in Oanda trade execution: {str(e)}")
            raise

    def execute_binance_trade(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade on Binance"""
        try:
            symbol = data['symbol']
            side = data['action'].upper()
            quantity = data['units']

            # Get symbol info for precision
            symbol_info = self.binance_client.get_symbol_info(symbol)

            # Create market order
            order = self.binance_client.create_order(symbol=symbol,
                                                     side=side,
                                                     type='MARKET',
                                                     quantity=quantity)

            result = {
                'status':
                'success',
                'exchange':
                'binance',
                'order':
                order,
                'filled_price':
                float(order['fills'][0]['price']) if order['fills'] else None,
            }

            # Add SL/TP if provided
            if 'sl_pips' in data and order['fills']:
                filled_price = float(order['fills'][0]['price'])
                sl_price, tp_price = self.calculate_sl_tp(
                    filled_price, data['action'], float(data['sl_pips']),
                    float(data['tp_pips']))

                # Place stop loss order
                sl_order = self.binance_client.create_order(
                    symbol=symbol,
                    side='SELL' if side == 'BUY' else 'BUY',
                    type='STOP_LOSS_LIMIT',
                    quantity=quantity,
                    price=str(sl_price),
                    stopPrice=str(sl_price),
                    timeInForce='GTC')

                # Place take profit order
                tp_order = self.binance_client.create_order(
                    symbol=symbol,
                    side='SELL' if side == 'BUY' else 'BUY',
                    type='LIMIT',
                    quantity=quantity,
                    price=str(tp_price),
                    timeInForce='GTC')

                result.update({
                    'sl_order': sl_order,
                    'tp_order': tp_order,
                    'sl_price': sl_price,
                    'tp_price': tp_price
                })

            return result

        except BinanceAPIException as e:
            self.logger.error(f"Binance API error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error in Binance trade execution: {str(e)}")
            raise

    def calculate_sl_tp(self, price: float, action: str, sl_pips: float,
                        tp_pips: float) -> Tuple[float, float]:
        """Calculate stop loss and take profit prices"""
        pip_value = 0.0001
        sl_distance = sl_pips * pip_value
        tp_distance = tp_pips * pip_value

        if action.lower() == 'buy':
            sl_price = price - (price * sl_distance)
            tp_price = price + (price * tp_distance)
        else:
            sl_price = price + (price * sl_distance)
            tp_price = price - (price * tp_distance)

        return round(sl_price, 5), round(tp_price, 5)

    def get_oanda_account_summary(self) -> Dict:
        """Get Oanda account summary using proper endpoint"""
        try:
            # Use proper endpoint objects
            account_summary = AccountSummary(self.oanda_account_id)
            summary_response = self.oanda_api.request(account_summary)

            positions = OpenPositions(accountID=self.oanda_account_id)
            positions_response = self.oanda_api.request(positions)

            return {
                'balance':
                float(summary_response['account']['balance']),
                'open_trades_count':
                int(summary_response['account']['openTradeCount']),
                'floating_pl':
                float(summary_response['account']['unrealizedPL']),
                'realized_pl':
                float(summary_response['account']['pl']),
                'positions':
                positions_response['positions']
            }
        except Exception as e:
            self.logger.error(f"Error getting Oanda account summary: {str(e)}")
            raise

    def get_binance_account_summary(self) -> Dict:
        """Get Binance account summary with proper error handling"""
        try:
            # Get account info
            account = self.binance_client.get_account()

            # Calculate total USDT value
            total_value_usdt = 0
            balances = {}

            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked

                if total > 0:
                    asset = balance['asset']
                    if asset == 'USDT':
                        value_usdt = total
                    else:
                        try:
                            ticker = self.binance_client.get_symbol_ticker(
                                symbol=f"{asset}USDT")
                            price_usdt = float(ticker['price'])
                            value_usdt = total * price_usdt
                        except:
                            value_usdt = 0

                    balances[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total,
                        'value_usdt': value_usdt
                    }
                    total_value_usdt += value_usdt

            return {
                'total_value_usdt': total_value_usdt,
                'trading_enabled': account['canTrade'],
                'balances': balances
            }
        except BinanceAPIException as e:
            self.logger.error(f"Binance API error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(
                f"Error getting Binance account summary: {str(e)}")
            raise
