#!/usr/bin/env python3
"""
Autonomous Crypto Trading Agent - Paper Trading Mode
BTC-USD High-Frequency Strategy with Risk Management
"""

import os
import json
import time
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np

# Load .env file if it exists
def load_env_file(env_path='.env'):
    """Load environment variables from .env file"""
    if not os.path.exists(env_path):
        return
    
    try:
        with open(env_path, 'r') as f:
            content = f.read()
        
        # Split by lines but preserve structure
        lines = content.split('\n')
        current_key = None
        current_value = []
        in_quoted_value = False
        
        for line in lines:
            original_line = line
            line = line.rstrip()
            
            # Skip comments and empty lines (unless we're in a multi-line value)
            if not current_key and (not line or line.strip().startswith('#')):
                continue
            
            # Check if this is a new KEY=VALUE line
            if '=' in line and not line.strip().startswith('-----') and not current_key:
                # Parse new KEY=VALUE
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Check if value starts with a quote (multi-line value)
                if value.startswith('"') or value.startswith("'"):
                    quote_char = value[0]
                    in_quoted_value = True
                    # Remove opening quote
                    value = value[1:]
                    current_key = key
                    current_value = [value] if value else []
                    
                    # Check if it also ends with a quote (single line)
                    if value.endswith(quote_char) and len(value) > 1:
                        # Single line quoted value
                        value = value[:-1]  # Remove closing quote
                        os.environ[key] = value.replace('\\n', '\n').replace('\\t', '\t')
                        current_key = None
                        current_value = []
                        in_quoted_value = False
                else:
                    # Single line unquoted value
                    if key and not os.getenv(key):
                        os.environ[key] = value
            elif current_key:
                # Continuation of multi-line value
                stripped = line.strip()
                
                # Check for closing quote
                if in_quoted_value and (stripped.endswith('"') or stripped.endswith("'")):
                    # Remove closing quote
                    if stripped.endswith('"'):
                        stripped = stripped[:-1]
                    elif stripped.endswith("'"):
                        stripped = stripped[:-1]
                    if stripped:
                        current_value.append(stripped)
                    # Save the value
                    full_value = '\n'.join(current_value)
                    # Convert escape sequences
                    full_value = full_value.replace('\\n', '\n').replace('\\t', '\t')
                    os.environ[current_key] = full_value
                    current_key = None
                    current_value = []
                    in_quoted_value = False
                else:
                    # Add line to current value (preserve structure for private keys)
                    current_value.append(line)
            
    except Exception as e:
        logging.warning(f"Could not load .env file: {e}")

# Load .env file at startup
load_env_file()

# ==============================================================================
# CONFIGURATION
# ==============================================================================

@dataclass
class Config:
    """Trading configuration"""
    # API Settings (New Coinbase Advanced Trade API format)
    api_key_name: str = os.getenv('COINBASE_API_KEY_NAME', '')
    private_key: str = os.getenv('COINBASE_PRIVATE_KEY', '')
    
    # Trading Parameters
    asset_pair: str = "BTC-USD"
    timeframe: str = "15m"  # 15-minute candles
    confirmation_timeframe: str = "1h"  # 1-hour confirmation
    
    # Position Sizing (tiered)
    size_tier_1_max: float = 100.0  # Up to $100: use 99%
    size_tier_1_pct: float = 0.99
    size_tier_2_max: float = 1000.0  # $100-$1000: use 20%
    size_tier_2_pct: float = 0.20
    size_tier_3_pct: float = 0.10  # $10,000+: use 10%
    
    # Technical Indicators
    adx_period: int = 14
    adx_threshold: float = 25.0  # Trending market threshold
    bb_period: int = 20
    bb_std: float = 2.0
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    atr_period: int = 14
    volume_spike_multiplier: float = 1.5
    
    # Risk Management
    atr_stop_multiplier: float = 2.0  # Stop loss distance
    profit_target_ratio: float = 1.5  # Take 50% profit at 1.5x risk
    trailing_stop_multiplier: float = 1.5  # Trail with 1.5x ATR
    max_position_hours: int = 12  # Force close after 12 hours
    daily_loss_multiplier: float = 3.0  # 3x avg position risk
    max_drawdown_pct: float = 0.20  # 20% total drawdown triggers pause
    volatility_pause_threshold: float = 0.10  # 10% move in 1 hour
    sharp_drop_alert_threshold: float = 0.05  # 5% drop in 15 min
    
    # Paper Trading
    paper_trading: bool = True
    paper_balance_usd: float = 10000.0
    paper_balance_btc: float = 0.0
    
    # Fees & Slippage
    taker_fee: float = 0.006  # 0.6%
    slippage: float = 0.001  # 0.1% avg slippage
    
    # Monitoring
    check_interval_seconds: int = 60
    log_level: str = "INFO"


# ==============================================================================
# LOGGING SETUP
# ==============================================================================

def setup_logging(level: str = "INFO"):
    """Configure logging"""
    log_format = '%(asctime)s | %(levelname)s | %(message)s'
    logging.basicConfig(
        level=getattr(logging, level),
        format=log_format,
        handlers=[
            logging.FileHandler('trading_agent.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# ==============================================================================
# COINBASE API CLIENT
# ==============================================================================

class CoinbaseClient:
    """Coinbase Advanced Trade API client using JWT authentication"""
    
    def __init__(self, api_key_name: str, private_key: str):
        self.api_key_name = api_key_name
        # Extract UUID from API key name if it's a full path
        # Format: organizations/.../apiKeys/UUID or just UUID
        if '/apiKeys/' in api_key_name:
            self.api_key_uuid = api_key_name.split('/apiKeys/')[-1]
        else:
            self.api_key_uuid = api_key_name
        self.private_key = private_key
        self.base_url = "https://api.coinbase.com"
        
        # Load private key (handle newlines in environment variable)
        try:
            # Clean up the private key string (remove extra whitespace/newlines)
            private_key_clean = private_key.strip()
            if '\n' not in private_key_clean and 'BEGIN' in private_key_clean:
                # If newlines are escaped, replace them
                private_key_clean = private_key_clean.replace('\\n', '\n')
            
            if private_key_clean.startswith('-----BEGIN'):
                # PEM format - load the private key
                self.private_key_obj = serialization.load_pem_private_key(
                    private_key_clean.encode(),
                    password=None,
                    backend=default_backend()
                )
            else:
                raise ValueError("Private key must be in PEM format starting with -----BEGIN")
        except Exception as e:
            logging.error(f"Failed to load private key: {e}")
            logging.error("Make sure COINBASE_PRIVATE_KEY contains the full PEM key including BEGIN/END lines")
            self.private_key_obj = None
    
    def _generate_jwt(self, method: str, path: str, body: str = '') -> str:
        """Generate JWT token for Coinbase Advanced Trade API"""
        if not self.private_key_obj:
            raise ValueError("Private key not loaded")
        
        # Format URI for JWT (method + host + path)
        uri = f"{method} api.coinbase.com{path}"
        now = int(time.time())
        
        # Create JWT payload according to Coinbase App API spec
        # See: https://docs.cdp.coinbase.com/coinbase-app/authentication-authorization/api-key-authentication
        payload = {
            'sub': self.api_key_name,  # Full API key name: organizations/{org_id}/apiKeys/{key_id}
            'iss': 'cdp',  # Issuer must be 'cdp' for Coinbase App API
            'nbf': now,
            'exp': now + 120,  # 2 minute expiration
            'uri': uri
        }
        
        # Generate random nonce for security (16 bytes = 32 hex characters)
        nonce = secrets.token_hex(16)
        
        # Sign JWT with ES256 algorithm
        # Include kid (key ID) and nonce in headers as per Coinbase App API spec
        try:
            token = jwt.encode(
                payload,
                self.private_key_obj,
                algorithm='ES256',
                headers={
                    'kid': self.api_key_name,  # Key ID header
                    'nonce': nonce  # Random nonce for security
                }
            )
            return token
        except Exception as e:
            logging.error(f"JWT encoding failed: {e}")
            raise
    
    def _request(self, method: str, path: str, params: dict = None, body: dict = None) -> dict:
        """Make authenticated API request using JWT"""
        body_str = json.dumps(body) if body else ''
        
        # Generate JWT token
        try:
            jwt_token = self._generate_jwt(method, path, body_str)
        except Exception as e:
            logging.error(f"Failed to generate JWT: {e}")
            return {}
        
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Content-Type': 'application/json'
        }
        
        url = self.base_url + path
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=body, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"API request failed: {e}")
            return {}
    
    def _granularity_to_enum(self, seconds: int) -> str:
        """Convert seconds to Coinbase granularity enum string"""
        mapping = {
            60: 'ONE_MINUTE',
            300: 'FIVE_MINUTE',
            900: 'FIFTEEN_MINUTE',
            1800: 'THIRTY_MINUTE',
            3600: 'ONE_HOUR',
            7200: 'TWO_HOUR',
            14400: 'FOUR_HOUR',
            21600: 'SIX_HOUR',
            86400: 'ONE_DAY'
        }
        return mapping.get(seconds, 'FIFTEEN_MINUTE')  # Default to 15min
    
    def get_candles(self, product_id: str, granularity: int, start: str = None, end: str = None) -> List[List]:
        """Get historical candles
        Granularity: 60=1m, 300=5m, 900=15m, 3600=1h, 21600=6h, 86400=1d
        Start/end: Can be ISO string or Unix timestamp (will be converted to Unix timestamp)
        Returns: [[timestamp, low, high, open, close, volume], ...]
        """
        path = f"/api/v3/brokerage/products/{product_id}/candles"
        granularity_enum = self._granularity_to_enum(granularity)
        params = {'granularity': granularity_enum}
        
        # Convert ISO strings to Unix timestamps if needed
        if start:
            if isinstance(start, str) and 'T' in start:
                # ISO format - convert to Unix timestamp
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    params['start'] = str(int(dt.timestamp()))
                except:
                    params['start'] = start
            else:
                params['start'] = str(start) if not isinstance(start, str) else start
        
        if end:
            if isinstance(end, str) and 'T' in end:
                # ISO format - convert to Unix timestamp
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    params['end'] = str(int(dt.timestamp()))
                except:
                    params['end'] = end
            else:
                params['end'] = str(end) if not isinstance(end, str) else end
        
        data = self._request('GET', path, params=params)
        # Handle new API response format
        if isinstance(data, dict):
            if 'candles' in data:
                return data['candles']
            elif 'result' in data and isinstance(data['result'], dict):
                return data['result'].get('candles', [])
        return data if isinstance(data, list) else []
    
    def get_ticker(self, product_id: str) -> dict:
        """Get current ticker"""
        path = f"/api/v3/brokerage/products/{product_id}/ticker"
        return self._request('GET', path)
    
    def place_order(self, product_id: str, side: str, size: float, order_type: str = 'market') -> dict:
        """Place order (DISABLED IN PAPER MODE)"""
        logging.warning("place_order called but paper trading is enabled - order not executed")
        return {}


# ==============================================================================
# TECHNICAL INDICATORS
# ==============================================================================

class Indicators:
    """Technical indicator calculations"""
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()
    
    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average Directional Index"""
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr = Indicators.atr(high, low, close, 1)
        
        plus_di = 100 * (plus_dm.rolling(period).mean() / tr.rolling(period).mean())
        minus_di = 100 * (minus_dm.rolling(period).mean() / tr.rolling(period).mean())
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        
        return adx
    
    @staticmethod
    def bollinger_bands(close: pd.Series, period: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands (upper, middle, lower)"""
        middle = close.rolling(period).mean()
        std_dev = close.rolling(period).std()
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        return upper, middle, lower
    
    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi


# ==============================================================================
# TRADING STRATEGY
# ==============================================================================

@dataclass
class Position:
    """Active position tracking"""
    entry_price: float
    size: float  # BTC amount
    entry_time: datetime
    stop_loss: float
    take_profit: float
    partial_taken: bool = False
    breakeven_moved: bool = False


class TradingStrategy:
    """BTC-USD high-frequency strategy with risk management"""
    
    def __init__(self, config: Config, client: CoinbaseClient):
        self.config = config
        self.client = client
        self.logger = logging.getLogger(__name__)
        
        # Paper trading state
        self.balance_usd = config.paper_balance_usd
        self.balance_btc = config.paper_balance_btc
        self.peak_balance = config.paper_balance_usd
        
        # Position tracking
        self.position: Optional[Position] = None
        self.trades_today = []
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        
        # Circuit breakers
        self.trading_paused = False
        self.pause_reason = ""
        self.last_check_time = None
        
    def get_candles_df(self, granularity: int, periods: int = 100) -> pd.DataFrame:
        """Fetch and format candle data"""
        # Use Unix timestamps for Coinbase API
        now = int(time.time())
        start_ts = now - (granularity * periods)
        end_ts = now
        
        candles = self.client.get_candles(
            self.config.asset_pair,
            granularity,
            start=str(start_ts),
            end=str(end_ts)
        )
        
        if not candles:
            return pd.DataFrame()
        
        df = pd.DataFrame(candles, columns=['timestamp', 'low', 'high', 'open', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        for col in ['low', 'high', 'open', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        return df
    
    def calculate_indicators(self, df: pd.DataFrame) -> dict:
        """Calculate all technical indicators"""
        indicators = {}
        
        # ATR
        indicators['atr'] = Indicators.atr(df['high'], df['low'], df['close'], self.config.atr_period).iloc[-1]
        
        # ADX
        indicators['adx'] = Indicators.adx(df['high'], df['low'], df['close'], self.config.adx_period).iloc[-1]
        
        # Bollinger Bands
        upper, middle, lower = Indicators.bollinger_bands(df['close'], self.config.bb_period, self.config.bb_std)
        indicators['bb_upper'] = upper.iloc[-1]
        indicators['bb_middle'] = middle.iloc[-1]
        indicators['bb_lower'] = lower.iloc[-1]
        
        # RSI
        indicators['rsi'] = Indicators.rsi(df['close'], self.config.rsi_period).iloc[-1]
        
        # Volume
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]
        indicators['volume_spike'] = current_volume > (avg_volume * self.config.volume_spike_multiplier)
        
        # Current price
        indicators['price'] = df['close'].iloc[-1]
        
        return indicators
    
    def check_volatility_circuit_breaker(self, df_15m: pd.DataFrame):
        """Check for extreme volatility and pause if needed"""
        if len(df_15m) < 4:
            return
        
        # Check last hour (4 x 15min candles)
        recent = df_15m.tail(4)
        high_1h = recent['high'].max()
        low_1h = recent['low'].min()
        pct_move = (high_1h - low_1h) / low_1h
        
        if pct_move > self.config.volatility_pause_threshold:
            self.trading_paused = True
            self.pause_reason = f"VOLATILITY CIRCUIT BREAKER: {pct_move*100:.2f}% move in 1 hour"
            self.logger.critical(self.pause_reason)
            self._alert(self.pause_reason)
    
    def check_sharp_drop(self, df_15m: pd.DataFrame):
        """Alert on sharp price drops"""
        if len(df_15m) < 2:
            return
        
        last_candle = df_15m.iloc[-1]
        prev_candle = df_15m.iloc[-2]
        
        drop_pct = (prev_candle['close'] - last_candle['close']) / prev_candle['close']
        
        if drop_pct > self.config.sharp_drop_alert_threshold:
            alert_msg = f"SHARP DROP ALERT: BTC dropped {drop_pct*100:.2f}% in 15 minutes (${prev_candle['close']:.2f} → ${last_candle['close']:.2f})"
            self.logger.warning(alert_msg)
            self._alert(alert_msg)
    
    def check_drawdown_limit(self):
        """Check total drawdown circuit breaker"""
        current_total = self.balance_usd + (self.balance_btc * self._get_current_price())
        drawdown = (self.peak_balance - current_total) / self.peak_balance
        
        if drawdown >= self.config.max_drawdown_pct:
            self.trading_paused = True
            self.pause_reason = f"MAX DRAWDOWN REACHED: {drawdown*100:.2f}% (limit: {self.config.max_drawdown_pct*100:.2f}%)"
            self.logger.critical(self.pause_reason)
            self._alert(self.pause_reason)
            
            # Close any open position
            if self.position:
                self._close_position("Drawdown limit triggered")
    
    def check_daily_loss_limit(self):
        """Check daily loss circuit breaker"""
        avg_position_risk = self._calculate_position_size(self._get_current_price()) * 0.03  # Assume ~3% avg risk
        daily_loss_limit = avg_position_risk * self.config.daily_loss_multiplier
        
        if self.daily_pnl < -daily_loss_limit:
            self.trading_paused = True
            self.pause_reason = f"DAILY LOSS LIMIT: ${self.daily_pnl:.2f} (limit: ${-daily_loss_limit:.2f})"
            self.logger.critical(self.pause_reason)
            self._alert(self.pause_reason)
            
            # Close any open position
            if self.position:
                self._close_position("Daily loss limit triggered")
    
    def _get_current_price(self) -> float:
        """Get current BTC price"""
        ticker = self.client.get_ticker(self.config.asset_pair)
        # Ticker endpoint returns list of trades - get price from most recent trade
        if isinstance(ticker, dict) and 'trades' in ticker:
            trades = ticker.get('trades', [])
            if trades and len(trades) > 0:
                # Most recent trade is first in list
                return float(trades[0].get('price', 0))
        # Fallback: try direct price field (for other response formats)
        if isinstance(ticker, dict):
            return float(ticker.get('price', 0))
        return 0.0
    
    def _calculate_position_size(self, current_price: float) -> float:
        """Calculate position size based on tiered rules"""
        if current_price <= 0:
            self.logger.warning("Invalid price for position size calculation")
            return 0.0
        if self.balance_usd <= self.config.size_tier_1_max:
            return self.balance_usd * self.config.size_tier_1_pct / current_price
        elif self.balance_usd <= self.config.size_tier_2_max:
            return self.balance_usd * self.config.size_tier_2_pct / current_price
        else:
            return self.balance_usd * self.config.size_tier_3_pct / current_price
    
    def _execute_buy(self, price: float, indicators: dict, reason: str):
        """Execute buy order (paper trading)"""
        size_btc = self._calculate_position_size(price)
        cost_usd = size_btc * price
        fee = cost_usd * self.config.taker_fee
        slippage_cost = cost_usd * self.config.slippage
        total_cost = cost_usd + fee + slippage_cost
        
        if total_cost > self.balance_usd:
            self.logger.warning(f"Insufficient funds: need ${total_cost:.2f}, have ${self.balance_usd:.2f}")
            return
        
        # Calculate stop loss and take profit
        atr = indicators['atr']
        stop_loss = price - (atr * self.config.atr_stop_multiplier)
        risk_distance = price - stop_loss
        take_profit = price + (risk_distance * self.config.profit_target_ratio)
        
        # Update balances
        self.balance_usd -= total_cost
        self.balance_btc += size_btc
        
        # Create position
        self.position = Position(
            entry_price=price,
            size=size_btc,
            entry_time=datetime.utcnow(),
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        trade_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'BUY',
            'price': price,
            'size': size_btc,
            'cost': total_cost,
            'fee': fee,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'reason': reason,
            'balance_usd': self.balance_usd,
            'balance_btc': self.balance_btc
        }
        
        self.trades_today.append(trade_log)
        self.logger.info(f"BUY EXECUTED: {size_btc:.6f} BTC @ ${price:.2f} | Stop: ${stop_loss:.2f} | Target: ${take_profit:.2f} | Reason: {reason}")
        self._save_trade(trade_log)
    
    def _close_position(self, reason: str):
        """Close current position"""
        if not self.position:
            return
        
        current_price = self._get_current_price()
        size_btc = self.position.size
        revenue_usd = size_btc * current_price
        fee = revenue_usd * self.config.taker_fee
        slippage_cost = revenue_usd * self.config.slippage
        net_revenue = revenue_usd - fee - slippage_cost
        
        # Calculate P&L
        entry_cost = self.position.size * self.position.entry_price
        pnl = net_revenue - entry_cost
        pnl_pct = (pnl / entry_cost) * 100
        
        # Update balances
        self.balance_usd += net_revenue
        self.balance_btc -= size_btc
        
        # Update P&L tracking
        self.daily_pnl += pnl
        self.total_pnl += pnl
        
        # Update peak balance
        current_total = self.balance_usd + (self.balance_btc * current_price)
        if current_total > self.peak_balance:
            self.peak_balance = current_total
        
        trade_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'SELL',
            'price': current_price,
            'size': size_btc,
            'revenue': net_revenue,
            'fee': fee,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'hold_time': (datetime.utcnow() - self.position.entry_time).total_seconds() / 3600,
            'reason': reason,
            'balance_usd': self.balance_usd,
            'balance_btc': self.balance_btc
        }
        
        self.trades_today.append(trade_log)
        self.logger.info(f"SELL EXECUTED: {size_btc:.6f} BTC @ ${current_price:.2f} | P&L: ${pnl:.2f} ({pnl_pct:+.2f}%) | Reason: {reason}")
        self._save_trade(trade_log)
        
        self.position = None
    
    def _manage_position(self, current_price: float, indicators: dict):
        """Manage open position (stops, targets, trailing)"""
        if not self.position:
            return
        
        # Check max hold time
        hold_hours = (datetime.utcnow() - self.position.entry_time).total_seconds() / 3600
        if hold_hours >= self.config.max_position_hours:
            self._close_position(f"Max hold time reached ({hold_hours:.1f} hours)")
            return
        
        # Check stop loss
        if current_price <= self.position.stop_loss:
            self._close_position(f"Stop loss hit (${self.position.stop_loss:.2f})")
            return
        
        # Check take profit (partial)
        if not self.position.partial_taken and current_price >= self.position.take_profit:
            # Take 50% profit
            partial_size = self.position.size * 0.5
            revenue = partial_size * current_price * (1 - self.config.taker_fee - self.config.slippage)
            self.balance_usd += revenue
            self.balance_btc -= partial_size
            self.position.size -= partial_size
            self.position.partial_taken = True
            
            self.logger.info(f"PARTIAL PROFIT TAKEN: 50% sold @ ${current_price:.2f}")
        
        # Move stop to breakeven after partial profit
        if self.position.partial_taken and not self.position.breakeven_moved:
            self.position.stop_loss = self.position.entry_price
            self.position.breakeven_moved = True
            self.logger.info(f"Stop moved to breakeven @ ${self.position.entry_price:.2f}")
        
        # Trailing stop (after breakeven move)
        if self.position.breakeven_moved:
            atr = indicators['atr']
            trailing_stop = current_price - (atr * self.config.trailing_stop_multiplier)
            if trailing_stop > self.position.stop_loss:
                self.position.stop_loss = trailing_stop
                self.logger.info(f"Trailing stop updated to ${trailing_stop:.2f}")
    
    def _check_entry_signal(self, df_15m: pd.DataFrame, df_1h: pd.DataFrame, indicators_15m: dict, indicators_1h: dict) -> Tuple[bool, str]:
        """Check for entry signal"""
        # 1. ADX trending market (both timeframes)
        if indicators_15m['adx'] < self.config.adx_threshold:
            return False, f"15m ADX too low ({indicators_15m['adx']:.1f} < {self.config.adx_threshold})"
        
        if indicators_1h['adx'] < self.config.adx_threshold:
            return False, f"1h ADX too low ({indicators_1h['adx']:.1f} < {self.config.adx_threshold})"
        
        # 2. Price at lower Bollinger Band
        price = indicators_15m['price']
        if price > indicators_15m['bb_lower'] * 1.01:  # Allow 1% margin
            return False, f"Price not at lower BB (${price:.2f} > ${indicators_15m['bb_lower']:.2f})"
        
        # 3. Volume spike
        if not indicators_15m['volume_spike']:
            return False, "No volume spike detected"
        
        # 4. RSI filter
        if indicators_15m['rsi'] > self.config.rsi_overbought:
            return False, f"RSI overbought ({indicators_15m['rsi']:.1f} > {self.config.rsi_overbought})"
        
        # All conditions met
        reason = f"ADX 15m:{indicators_15m['adx']:.1f} 1h:{indicators_1h['adx']:.1f} | Price @ lower BB | Volume spike | RSI:{indicators_15m['rsi']:.1f}"
        return True, reason
    
    def run_cycle(self):
        """Execute one trading cycle"""
        try:
            # Reset daily tracking at midnight UTC
            now = datetime.utcnow()
            if self.last_check_time and self.last_check_time.date() != now.date():
                self.logger.info(f"New trading day | Yesterday P&L: ${self.daily_pnl:.2f} | Trades: {len(self.trades_today)}")
                self.trades_today = []
                self.daily_pnl = 0.0
                self.trading_paused = False
                self.pause_reason = ""
            
            self.last_check_time = now
            
            # Fetch market data
            df_15m = self.get_candles_df(900, 100)  # 15-min candles
            df_1h = self.get_candles_df(3600, 100)  # 1-hour candles
            
            if df_15m.empty or df_1h.empty:
                self.logger.warning("Failed to fetch candle data")
                return
            
            # Calculate indicators
            indicators_15m = self.calculate_indicators(df_15m)
            indicators_1h = self.calculate_indicators(df_1h)
            
            # Safety checks
            self.check_volatility_circuit_breaker(df_15m)
            self.check_sharp_drop(df_15m)
            self.check_drawdown_limit()
            self.check_daily_loss_limit()
            
            if self.trading_paused:
                self.logger.warning(f"Trading paused: {self.pause_reason}")
                return
            
            # Position management
            if self.position:
                self._manage_position(indicators_15m['price'], indicators_15m)
            
            # Entry logic (only if no position)
            if not self.position:
                signal, reason = self._check_entry_signal(df_15m, df_1h, indicators_15m, indicators_1h)
                if signal:
                    self._execute_buy(indicators_15m['price'], indicators_15m, reason)
                else:
                    self.logger.debug(f"No entry signal: {reason}")
            
            # Log status
            current_total = self.balance_usd + (self.balance_btc * indicators_15m['price'])
            self.logger.info(
                f"Status | USD: ${self.balance_usd:.2f} | BTC: {self.balance_btc:.6f} | "
                f"Total: ${current_total:.2f} | Daily P&L: ${self.daily_pnl:.2f} | "
                f"Position: {'OPEN' if self.position else 'NONE'}"
            )
            
        except Exception as e:
            self.logger.error(f"Error in trading cycle: {e}", exc_info=True)
    
    def _alert(self, message: str):
        """Send alert (currently just logs, can extend to email/SMS)"""
        self.logger.critical(f"🚨 ALERT: {message}")
        # TODO: Add email/SMS/webhook notifications here
    
    def _save_trade(self, trade: dict):
        """Save trade to log file"""
        with open('trades.jsonl', 'a') as f:
            f.write(json.dumps(trade) + '\n')
    
    def print_performance_summary(self):
        """Print performance stats"""
        if not self.trades_today:
            return
        
        buys = [t for t in self.trades_today if t['action'] == 'BUY']
        sells = [t for t in self.trades_today if t['action'] == 'SELL']
        
        if sells:
            winning_trades = [t for t in sells if t['pnl'] > 0]
            win_rate = len(winning_trades) / len(sells) * 100 if sells else 0
            avg_pnl = sum(t['pnl'] for t in sells) / len(sells)
            
            self.logger.info("=" * 60)
            self.logger.info("PERFORMANCE SUMMARY")
            self.logger.info(f"Trades today: {len(buys)} buys, {len(sells)} sells")
            self.logger.info(f"Win rate: {win_rate:.1f}%")
            self.logger.info(f"Average P&L per trade: ${avg_pnl:.2f}")
            self.logger.info(f"Daily P&L: ${self.daily_pnl:.2f}")
            self.logger.info(f"Total P&L: ${self.total_pnl:.2f}")
            self.logger.info("=" * 60)


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

def main():
    """Main trading loop"""
    # Load config
    config = Config()
    
    # Setup logging
    logger = setup_logging(config.log_level)
    
    # Validate API credentials
    if not config.api_key_name or not config.private_key:
        logger.error("Missing API credentials. Set COINBASE_API_KEY_NAME and COINBASE_PRIVATE_KEY environment variables.")
        return
    
    # Initialize
    client = CoinbaseClient(config.api_key_name, config.private_key)
    strategy = TradingStrategy(config, client)
    
    logger.info("=" * 60)
    logger.info("CRYPTO TRADING AGENT STARTED")
    logger.info(f"Mode: {'PAPER TRADING' if config.paper_trading else 'LIVE TRADING'}")
    logger.info(f"Asset: {config.asset_pair}")
    logger.info(f"Starting balance: ${config.paper_balance_usd:.2f}")
    logger.info(f"Check interval: {config.check_interval_seconds}s")
    logger.info("=" * 60)
    
    # Main loop
    try:
        while True:
            strategy.run_cycle()
            time.sleep(config.check_interval_seconds)
    
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("SHUTTING DOWN")
        strategy.print_performance_summary()
        logger.info("=" * 60)
    
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
