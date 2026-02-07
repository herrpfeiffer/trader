# Autonomous Crypto Trading Agent
**BTC-USD High-Frequency Strategy with Risk Management**

**⚠️ CURRENT MODE: PAPER TRADING (Simulated, No Real Money)**

## 🆕 Recent Updates

**✅ Configuration System Overhaul (Feb 2026)**
- **Fixed:** Agent now properly loads settings from `config.json` (was using hardcoded defaults)
- **Enhanced:** Monitoring interval now configurable (default: 5 seconds, was 60 seconds)
- **Added:** Cloud deployment automation with systemd service management
- **Improved:** Real-time log monitoring commands for remote instances

**🐛 Bug Fixes:**
- Multiple agent instance detection and prevention
- Proper configuration loading from JSON files
- Service management improvements for 24/7 operation

---

## 📋 Overview

This is a semi-autonomous trading bot that:
- Monitors BTC-USD on 15-minute candles
- Uses technical analysis (ADX, Bollinger Bands, RSI, Volume, ATR)
- Executes trades based on predefined strategy
- Includes multiple circuit breakers and risk controls
- Runs in paper trading mode by default (simulated trades with real market data)

**Strategy Summary:**
- **Entry:** Price touches lower Bollinger Band + volume spike + trending market (ADX > 12.5) + RSI < 80
- **Exit:** Hybrid approach - take 50% profit at 1.5× risk, trail remaining position with ATR-based stop
- **Risk:** ATR-based stop losses, daily loss limits, max drawdown protection, volatility circuit breakers

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install pandas numpy requests --break-system-packages
```

### 2. Set API Credentials

Create API key at: https://www.coinbase.com/settings/api

For **paper trading** (current mode), create a **VIEW-ONLY** key (safer).

```bash
export COINBASE_API_KEY_NAME="your_api_key_name_here"
export COINBASE_PRIVATE_KEY="-----BEGIN EC PRIVATE KEY-----
your_private_key_here
-----END EC PRIVATE KEY-----"
```

**Or create a `.env` file:**
```bash
COINBASE_API_KEY_NAME=your_api_key_name_here
COINBASE_PRIVATE_KEY="-----BEGIN EC PRIVATE KEY-----
your_private_key_here
-----END EC PRIVATE KEY-----"
```

**Security Note:** Never commit these to git. The agent automatically loads from `.env` file if present.

### 3. Run the Bot

```bash
python crypto_agent.py
```

### 4. Monitor Output

The bot will:
- Check market every 5 seconds (configurable in `config.json`)
- Log all decisions to console and `trading_agent.log`
- Save all trades to `trades.jsonl`
- Alert on circuit breaker triggers

---

## 📊 Understanding the Output

### Normal Operation
```
2026-02-07 03:50:18 | INFO | Entry check | 15m ADX: 12.1 | 1h ADX: 19.2 | Price: $64352.00 | BB Lower: $63829.95 | Volume spike: False | Reason: 15m ADX too low (12.1 < 12.5)
2026-02-07 03:50:18 | INFO | Status | USD: $10000.00 | BTC: 0.000000 | Total: $10000.00 | Daily P&L: $0.00 | Position: NONE
2026-02-07 03:50:24 | INFO | Entry check | 15m ADX: 12.1 | 1h ADX: 19.2 | Price: $64352.00 | BB Lower: $63829.95 | Volume spike: False | Reason: 15m ADX too low (12.1 < 12.5)
```
*Note: Agent checks every 5 seconds (configurable in config.json)*

### Trade Execution
```
2026-02-05 14:30:42 | INFO | BUY EXECUTED: 0.012345 BTC @ $65432.10 | Stop: $64123.45 | Target: $67890.23 | Reason: ADX 15m:27.5 1h:28.3 | Price @ lower BB | Volume spike | RSI:42.1
```

### Position Management
```
2026-02-05 15:45:20 | INFO | PARTIAL PROFIT TAKEN: 50% sold @ $67890.23
2026-02-05 15:45:21 | INFO | Stop moved to breakeven @ $65432.10
2026-02-05 16:10:33 | INFO | Trailing stop updated to $66234.56
```

### Circuit Breakers
```
2026-02-05 17:22:11 | CRITICAL | 🚨 ALERT: VOLATILITY CIRCUIT BREAKER: 12.34% move in 1 hour
2026-02-05 17:22:12 | WARNING | Trading paused: VOLATILITY CIRCUIT BREAKER: 12.34% move in 1 hour
```

---

## 🎛️ Configuration

Edit `config.json` to tune parameters without touching code.

### Key Settings:

**Position Sizing:**
```json
"tier_1": { "max_balance": 100, "position_pct": 0.99 }
"tier_2": { "max_balance": 1000, "position_pct": 0.20 }
"tier_3": { "position_pct": 0.10 }
```

**Risk Controls:**
```json
"max_drawdown_pct": 0.20           // Pause at 20% total loss
"daily_loss_multiplier": 3.0       // Pause after 3× avg position loss in one day
"volatility_pause_threshold": 0.10 // Pause if 10%+ move in 1 hour
```

**Technical Indicators:**
```json
"adx": { "threshold": 25.0 }       // Only trade in trending markets
"rsi": { "overbought": 70.0 }      // Don't buy if RSI > 70
"volume": { "spike_multiplier": 1.5 }
```

**Monitoring & Performance:**
```json
"monitoring": {
  "check_interval_seconds": 5,     // How often to check market (default: 5s)
  "log_level": "INFO",             // DEBUG/INFO/WARNING/ERROR
  "description": "How often to check market (seconds), log verbosity"
}
```

---

## 🌐 Deployment & Cloud Setup

### Running on Google Cloud Platform (GCP)

For 24/7 operation, deploy on a GCP instance:

1. **Create GCP Instance:**
   ```bash
   gcloud compute instances create trading-bot-1 \
     --zone=us-west1-a \
     --machine-type=e2-micro \
     --image-family=ubuntu-2404-lts \
     --image-project=ubuntu-os-cloud
   ```

2. **Connect to Instance:**
   ```bash
   gcloud compute ssh mail2pufta@trading-bot-1 --zone=us-west1-a
   ```

3. **Deploy Code:**
   ```bash
   # On the GCP instance
   git clone https://github.com/herrpfeiffer/trader.git
   cd trader
   bash INSTALL.sh  # Automated setup script
   ```

4. **Configure Systemd Service:**
   The `setup_trader.sh` script automatically creates a systemd service for 24/7 operation:
   ```bash
   sudo systemctl status trader    # Check status
   sudo systemctl restart trader  # Restart service
   sudo systemctl logs trader -f  # View logs
   ```

### Real-time Log Monitoring

**From your local machine:**
```bash
# Basic real-time logs
gcloud compute ssh mail2pufta@trading-bot-1 --zone=us-west1-a \
  --command="cd ~/trading_bot && tail -f trading_agent.log"

# Filtered view (trades & signals only)
gcloud compute ssh mail2pufta@trading-bot-1 --zone=us-west1-a \
  --command="cd ~/trading_bot && tail -f trading_agent.log | grep -E 'BUY|SELL|Entry check|Status'"

# Interactive session
gcloud compute ssh mail2pufta@trading-bot-1 --zone=us-west1-a
# Then: cd ~/trading_bot && tail -f trading_agent.log
```

**Service Management:**
```bash
# Restart after config changes
gcloud compute ssh mail2pufta@trading-bot-1 --zone=us-west1-a \
  --command="cd ~/trading_bot && git pull && sudo systemctl restart trader"

# Check service status
gcloud compute ssh mail2pufta@trading-bot-1 --zone=us-west1-a \
  --command="sudo systemctl status trader --no-pager -l"
```

---

## 📈 Performance Tracking

### View Trades Log
```bash
cat trades.jsonl | jq '.'
```

### Performance Summary
The bot prints a summary when stopped (Ctrl+C):
```
==================== PERFORMANCE SUMMARY ====================
Trades today: 5 buys, 5 sells
Win rate: 60.0%
Average P&L per trade: $12.34
Daily P&L: $61.70
Total P&L: $234.56
============================================================
```

### Analysis Script (Optional)
```python
import pandas as pd

# Load trades
trades = pd.read_json('trades.jsonl', lines=True)

# Filter sells
sells = trades[trades['action'] == 'SELL']

# Stats
print(f"Total trades: {len(sells)}")
print(f"Win rate: {(sells['pnl'] > 0).mean() * 100:.1f}%")
print(f"Total P&L: ${sells['pnl'].sum():.2f}")
print(f"Avg win: ${sells[sells['pnl'] > 0]['pnl'].mean():.2f}")
print(f"Avg loss: ${sells[sells['pnl'] < 0]['pnl'].mean():.2f}")
```

---

## ⚠️ Circuit Breakers

The bot automatically pauses trading when:

1. **Volatility Spike:** BTC moves >10% in 1 hour
2. **Daily Loss Limit:** Loses >3× average position risk in one day (~6-9% of account)
3. **Max Drawdown:** Total account drops 20% from peak
4. **Manual Override:** You can pause by creating a file named `PAUSE` in the same directory

**To resume after pause:**
- Volatility/Daily Loss: Auto-resumes next day (00:00 UTC)
- Max Drawdown: Requires manual restart after you investigate
- Manual: Delete the `PAUSE` file

---

## 🚨 Alerts

**Sharp Drop Alert:** Triggers if BTC drops >5% in 15 minutes (does NOT pause trading, just alerts you)

Current implementation logs alerts to console/file. To add email/SMS:

```python
def _alert(self, message: str):
    self.logger.critical(f"🚨 ALERT: {message}")
    
    # Email example
    import smtplib
    # ... add your email logic here
    
    # SMS example (Twilio)
    # ... add your SMS logic here
```

---

## 🔄 Switching to Live Trading

**⚠️ EXTREME CAUTION: This will trade real money. Only do this after:**
1. Running paper trading for 30+ days
2. Verifying positive returns in simulation
3. Understanding all risks involved
4. Starting with a small amount you can afford to lose

### Steps:

1. **Create Trading API Key**
   - Go to Coinbase → Settings → API
   - Create new key with **Trade** permissions
   - Save API Key, Secret, and Passphrase

2. **Update Environment Variables**
   ```bash
   export COINBASE_API_KEY="new_trading_key"
   export COINBASE_API_SECRET="new_trading_secret"
   export COINBASE_API_PASSPHRASE="new_passphrase"
   ```

3. **Edit `crypto_agent.py`**
   ```python
   # Line ~95
   paper_trading: bool = False  # Change to False
   paper_balance_usd: float = 0.0  # Not used in live mode
   ```

4. **Verify Funds**
   - Ensure you have USD in your Coinbase account
   - Bot will auto-detect balance
   - Start small (recommend $100-500 to test)

5. **Enable Actual Order Execution**
   The `place_order()` function is currently disabled. To enable:
   ```python
   # In CoinbaseClient.place_order() - remove the warning, implement actual order placement
   # Refer to Coinbase Advanced Trade API docs
   ```

6. **Test with Minimum Trade**
   - Monitor first few trades very closely
   - Verify stops and targets execute correctly
   - Check fee calculations match expectations

7. **Set Tighter Risk Limits Initially**
   ```json
   "max_drawdown_pct": 0.10  // Start with 10% instead of 20%
   "daily_loss_multiplier": 2.0  // Tighter daily limit
   ```

---

## 🛠️ Troubleshooting

### "Missing API credentials"
- Verify environment variables are set: `echo $COINBASE_API_KEY`
- Check for typos in variable names
- Ensure no extra spaces in credentials

### "Failed to fetch candle data"
- Check internet connection
- Verify API key has view permissions
- Coinbase might be rate-limiting (wait 60 seconds)

### "Insufficient funds"
- In paper trading: Bug in balance tracking (check `trading_agent.log`)
- In live trading: Deposit more funds or reduce position sizing

### Bot won't take trades
- Check `DEBUG` level logs: `grep "No entry signal" trading_agent.log | tail -20`
- Most common: ADX too low (market not trending)
- Increase logging: Set `"log_level": "DEBUG"` in config

### High fee drag
- Expected on small accounts (<$500)
- Each round-trip costs ~1.2% in fees
- Strategy needs >1.2% gain per trade to profit
- Consider weekly swing trading instead of high-frequency

### Config changes not taking effect
- **Symptom:** Agent still shows old intervals/settings after config.json changes
- **Cause:** Agent needs restart to reload configuration
- **Solution:** `sudo systemctl restart trader` (on GCP) or restart the Python process
- The agent now properly loads settings from `config.json` (fixed in recent update)

### Multiple agent instances running
- **Symptom:** Inconsistent log timing, multiple entries for same timestamp
- **Check:** `ps aux | grep crypto_agent` - should show only one process
- **Solution:** Kill all instances: `pkill -f crypto_agent.py` then restart properly
- **Prevention:** Always use systemd service (`sudo systemctl start trader`) instead of running manually

### Agent won't start after deployment
- **Check service status:** `sudo systemctl status trader`
- **View detailed logs:** `journalctl -u trader -f`
- **Common issues:**
  - Missing `.env` file with API credentials
  - Wrong file permissions: `chmod 600 .env`
  - Python dependencies: `pip3 install --user pandas numpy requests PyJWT cryptography`

---

## 📚 Strategy Deep Dive

### Why This Combination?

**ADX (Trend Filter):**
- Avoids choppy, sideways markets where indicators fail
- Only trades when there's clear directional momentum

**Bollinger Bands + Volume:**
- Lower band touch = potential oversold reversal
- Volume spike confirms institutional interest
- Reduces false signals vs. BB alone

**RSI Filter:**
- Prevents buying into parabolic blow-off tops
- Simple but effective overbought check

**ATR-based Stops:**
- Adapts to current volatility
- Tight in calm markets, wider in volatile markets
- Prevents getting stopped out by noise

**Hybrid Exit:**
- Locks in partial profit (reduces risk of giving back gains)
- Lets winners run with trailing stop (captures extended moves)
- 12-hour max hold prevents overnight gap risk

### Known Limitations

1. **Fee Drag:** High-frequency on small accounts gets destroyed by fees
2. **Whipsaw Risk:** 15-min timeframe still has false breakouts
3. **Gap Risk:** If BTC gaps down overnight (exchanges close, your stop doesn't trigger)
4. **Correlation Breakdown:** Indicators work until they don't (flash crashes, exchange outages)

### Improving Win Rate

After 30 days of paper trading, analyze:
- **Win rate by time of day:** Avoid trading during low-liquidity hours
- **Win rate by ADX level:** Raise threshold to 30+ if better results
- **Average hold time:** If winners close in <2 hours, tighten profit targets
- **Stop-loss hit rate:** If >70% of stops hit, widen to 2.5× ATR

---

## 🧪 Backtesting (Optional)

To test strategy on historical data:

```python
# Download historical data
import pandas as pd
from datetime import datetime, timedelta

# Fetch 90 days of 15-min candles
# Run strategy logic on each candle
# Track P&L, drawdowns, win rate

# This is left as an exercise - requires significant additional code
```

---

## 📞 Support & Disclaimers

**This is experimental software. Use at your own risk.**

- No warranty or guarantee of profits
- Cryptocurrency trading is extremely risky
- You can lose your entire investment
- Past performance (even in backtests) does not guarantee future results
- The creator is not responsible for any losses

**If you encounter bugs:**
- Check `trading_agent.log` for errors
- Verify your API credentials and permissions
- Test with paper trading first
- Start with minimum position sizes

**Legal:**
- Ensure algorithmic trading is legal in your jurisdiction
- You are responsible for taxes on gains
- Consult a financial advisor before risking real capital

---

## 🎯 What Success Looks Like

After 30 days of paper trading, you should see:
- Win rate: 55-65% (60%+ is excellent)
- Average winner : Average loser ratio > 1.5:1
- Max drawdown < 15%
- Sharpe ratio > 1.0 (if you calculate it)
- Consistent daily/weekly returns

If paper trading shows consistent losses, **DO NOT switch to live trading**. The strategy needs tuning or market conditions aren't favorable.

---

**Good luck, and trade responsibly.**
