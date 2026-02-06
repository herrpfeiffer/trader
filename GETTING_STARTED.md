# 🚀 GETTING STARTED - Read This First

## What You Just Got

A complete autonomous crypto trading system with:
- ✅ Paper trading mode (simulated, no real money)
- ✅ BTC-USD high-frequency strategy
- ✅ Multiple risk management circuit breakers
- ✅ Real-time monitoring and alerts
- ✅ Performance analysis tools

---

## ⚡ Quick Start (5 Minutes)

### Step 1: Get API Credentials

1. Go to https://www.coinbase.com/settings/api
2. Click "New API Key"
3. For **paper trading** (recommended): Select **VIEW ONLY** permissions
4. Save your:
   - API Key
   - API Secret
   - Passphrase

### Step 2: Set Environment Variables

**On Mac/Linux:**
```bash
export COINBASE_API_KEY="your_key_here"
export COINBASE_API_SECRET="your_secret_here"
export COINBASE_API_PASSPHRASE="your_passphrase_here"
```

**On Windows (PowerShell):**
```powershell
$env:COINBASE_API_KEY="your_key_here"
$env:COINBASE_API_SECRET="your_secret_here"
$env:COINBASE_API_PASSPHRASE="your_passphrase_here"
```

### Step 3: Run Pre-Flight Check

```bash
python3 preflight.py
```

This validates everything is set up correctly.

### Step 4: Start the Bot

```bash
python3 crypto_agent.py
```

Or use the convenience script:
```bash
./run.sh
```

---

## 📁 Files Included

| File | Purpose |
|------|---------|
| `crypto_agent.py` | Main trading engine (1,000+ lines) |
| `config.json` | Strategy parameters (tune without coding) |
| `README.md` | Comprehensive documentation |
| `preflight.py` | Setup validation script |
| `analyze_performance.py` | Trade analysis and stats |
| `run.sh` | Quick-start launcher |
| `.env.example` | Template for API credentials |
| `.gitignore` | Protects sensitive data from git |

---

## 📊 What Happens When You Run It

1. **Connects to Coinbase** (using your API key)
2. **Fetches BTC price data** every 60 seconds
3. **Calculates indicators** (ADX, Bollinger Bands, RSI, Volume, ATR)
4. **Looks for entry signals:**
   - Price touches lower Bollinger Band
   - Volume spike (>1.5× average)
   - Trending market (ADX > 25 on both 15m and 1h)
   - RSI not overbought (<70)
5. **Executes trades** (simulated in paper mode)
6. **Manages positions:**
   - Sets ATR-based stop loss
   - Takes 50% profit at 1.5× risk
   - Trails remaining position
   - Force-closes after 12 hours
7. **Monitors risk:**
   - Pauses if 10% volatility in 1 hour
   - Pauses if daily loss exceeds 3× avg position
   - Pauses if total drawdown hits 20%
8. **Logs everything** to `trading_agent.log` and `trades.jsonl`

---

## 🎯 Your First 30 Days

**Week 1: Monitor & Learn**
- Run the bot continuously
- Watch how it makes decisions
- Read the logs to understand entry/exit logic
- Don't touch anything yet

**Week 2: Analyze Performance**
```bash
python3 analyze_performance.py
```
- Check win rate (target: 55-65%)
- Check profit factor (target: >1.5)
- Identify patterns in losses

**Week 3: Tune Parameters**
Edit `config.json`:
- If too many false signals → raise ADX threshold to 30
- If stops hit too often → widen to 2.5× ATR
- If missing good moves → lower volume spike to 1.3×

**Week 4: Validate Results**
- Total P&L positive?
- Consistent weekly gains?
- Max drawdown acceptable?
- If YES to all → consider going live with **small capital**
- If NO → keep tuning or try different strategy

---

## ⚠️ Critical Warnings

### DO NOT:
- ❌ Switch to live trading without 30+ days of paper trading
- ❌ Risk money you can't afford to lose
- ❌ Ignore circuit breaker alerts
- ❌ Commit API credentials to git
- ❌ Run multiple instances (will conflict)
- ❌ Trade during exchange maintenance windows

### DO:
- ✅ Start with paper trading
- ✅ Analyze performance weekly
- ✅ Keep position sizes small initially
- ✅ Monitor logs daily
- ✅ Set phone alerts for critical errors
- ✅ Have a kill switch plan (know how to stop it remotely)

---

## 🔧 Common Issues & Fixes

**"Missing API credentials"**
- Run `echo $COINBASE_API_KEY` to verify it's set
- Make sure no extra spaces in the values

**"Failed to fetch candle data"**
- Check internet connection
- Coinbase might be down (check status.coinbase.com)
- Rate limit hit (wait 60 seconds)

**"No entry signal" every check**
- This is normal! Most of the time, conditions won't be met
- Markets are only trending ~30% of the time
- If it goes days with no trades → market is choppy, strategy is correctly avoiding it

**Bot crashes overnight**
- Check `trading_agent.log` for the error
- Common causes: internet dropout, Coinbase API change
- Use a process manager like `screen` or `tmux` for persistence

---

## 📈 Performance Expectations

**Realistic targets (based on similar strategies):**
- Win rate: 55-65%
- Monthly return: 3-8% (in good conditions)
- Max drawdown: 10-20%
- Trades per week: 5-15 (varies with market)

**Red flags (indicates strategy needs work):**
- Win rate <45%
- Monthly return negative for 2+ months
- Max drawdown >25%
- Average hold time <30 minutes (fee drag)

---

## 🚀 Going Live (When Ready)

**Only after:**
1. ✅ 30+ days paper trading
2. ✅ Positive total P&L in simulation
3. ✅ Win rate >55%
4. ✅ You understand every parameter
5. ✅ You can afford to lose 100% of the capital

**Steps:**
1. Create **TRADE** permission API key (not view-only)
2. Edit `crypto_agent.py` line ~95: `paper_trading: bool = False`
3. Deposit small amount ($100-500) to test
4. Monitor first 5 trades closely
5. Gradually increase capital if successful

**Start conservatively:**
- Use 10% max drawdown (not 20%)
- Trade smaller position sizes
- Tighten daily loss limits

---

## 📞 Need Help?

**Check logs first:**
```bash
tail -f trading_agent.log  # Live monitoring
grep ERROR trading_agent.log  # Find errors
```

**Analyze trades:**
```bash
python3 analyze_performance.py
```

**Validate setup:**
```bash
python3 preflight.py
```

---

## 🎓 Learning Resources

**Understanding the indicators:**
- ADX: https://www.investopedia.com/terms/a/adx.asp
- Bollinger Bands: https://www.investopedia.com/terms/b/bollingerbands.asp
- RSI: https://www.investopedia.com/terms/r/rsi.asp

**Risk management:**
- Position sizing: https://www.investopedia.com/terms/p/positionsizing.asp
- Stop losses: https://www.investopedia.com/terms/s/stop-lossorder.asp

**Coinbase API:**
- Documentation: https://docs.cloud.coinbase.com/

---

## ✅ Final Checklist Before Running

- [ ] Installed Python 3.7+
- [ ] Installed dependencies (pandas, numpy, requests)
- [ ] Created Coinbase API key (VIEW-ONLY for paper trading)
- [ ] Set environment variables (API_KEY, API_SECRET, API_PASSPHRASE)
- [ ] Ran `python3 preflight.py` → all checks passed
- [ ] Read `README.md` sections on circuit breakers
- [ ] Understand this is paper trading (no real money)
- [ ] Know how to stop the bot (Ctrl+C)
- [ ] Ready to monitor logs daily

**If all checked → you're ready to run:**
```bash
python3 crypto_agent.py
```

**Good luck, and remember: Paper trade first, trade smart always.**
