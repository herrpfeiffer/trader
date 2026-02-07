#!/usr/bin/env python3
"""
Performance Analyzer - Review Trading Results
Analyzes trades.jsonl to show strategy performance
"""

import json
import pandas as pd
from datetime import datetime
import sys

def load_trades(filepath='trades.jsonl'):
    """Load trades from JSONL file"""
    trades = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                trades.append(json.loads(line))
    except FileNotFoundError:
        print(f"❌ No trades file found at {filepath}")
        print("The bot hasn't executed any trades yet.")
        sys.exit(1)
    
    return pd.DataFrame(trades)

def analyze_performance(df):
    """Calculate and display performance metrics"""
    
    # Separate buys and sells
    buys = df[df['action'] == 'BUY']
    sells = df[df['action'] == 'SELL']
    
    if len(sells) == 0:
        print("📊 No completed trades yet (no sells)")
        print(f"Open positions: {len(buys)}")
        return
    
    print("=" * 60)
    print("TRADING PERFORMANCE ANALYSIS")
    print("=" * 60)
    print()
    
    # Basic stats
    print("📈 OVERVIEW")
    print(f"  Total buys:  {len(buys)}")
    print(f"  Total sells: {len(sells)}")
    print(f"  Open positions: {len(buys) - len(sells)}")
    print()
    
    # P&L Analysis
    total_pnl = sells['pnl'].sum()
    avg_pnl = sells['pnl'].mean()
    
    winning_trades = sells[sells['pnl'] > 0]
    losing_trades = sells[sells['pnl'] < 0]
    
    win_rate = len(winning_trades) / len(sells) * 100 if len(sells) > 0 else 0
    
    avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
    avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
    
    profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if len(losing_trades) > 0 and losing_trades['pnl'].sum() != 0 else float('inf')
    
    print("💰 PROFIT & LOSS")
    print(f"  Total P&L:     ${total_pnl:,.2f}")
    print(f"  Avg P&L/trade: ${avg_pnl:,.2f}")
    print(f"  Win rate:      {win_rate:.1f}%")
    print(f"  Profit factor: {profit_factor:.2f}" + (" (excellent)" if profit_factor > 2 else " (good)" if profit_factor > 1.5 else ""))
    print()
    
    print("🎯 WIN/LOSS BREAKDOWN")
    print(f"  Winning trades: {len(winning_trades)}")
    print(f"  Average win:    ${avg_win:,.2f}")
    print(f"  Largest win:    ${winning_trades['pnl'].max():,.2f}" if len(winning_trades) > 0 else "  Largest win:    N/A")
    print()
    print(f"  Losing trades:  {len(losing_trades)}")
    print(f"  Average loss:   ${avg_loss:,.2f}")
    print(f"  Largest loss:   ${losing_trades['pnl'].min():,.2f}" if len(losing_trades) > 0 else "  Largest loss:   N/A")
    print()
    
    # Risk metrics
    if 'pnl_pct' in sells.columns:
        avg_return_pct = sells['pnl_pct'].mean()
        best_trade_pct = sells['pnl_pct'].max()
        worst_trade_pct = sells['pnl_pct'].min()
        
        print("📊 RETURNS")
        print(f"  Avg return:    {avg_return_pct:+.2f}%")
        print(f"  Best trade:    {best_trade_pct:+.2f}%")
        print(f"  Worst trade:   {worst_trade_pct:+.2f}%")
        print()
    
    # Hold time analysis
    if 'hold_time' in sells.columns:
        avg_hold = sells['hold_time'].mean()
        print("⏱️  HOLD TIME")
        print(f"  Average:       {avg_hold:.2f} hours")
        print(f"  Shortest:      {sells['hold_time'].min():.2f} hours")
        print(f"  Longest:       {sells['hold_time'].max():.2f} hours")
        print()
    
    # Exit reason breakdown
    if 'reason' in sells.columns:
        print("🚪 EXIT REASONS")
        for reason, count in sells['reason'].value_counts().items():
            print(f"  {reason}: {count}")
        print()
    
    # Time-based analysis
    if 'timestamp' in sells.columns:
        sells['date'] = pd.to_datetime(sells['timestamp']).dt.date
        daily_pnl = sells.groupby('date')['pnl'].sum()
        
        print("📅 DAILY PERFORMANCE")
        for date, pnl in daily_pnl.items():
            print(f"  {date}: ${pnl:+,.2f}")
        print()
    
    # Final balance
    if 'balance_usd' in sells.columns and 'balance_btc' in sells.columns:
        final_usd = sells['balance_usd'].iloc[-1]
        final_btc = sells['balance_btc'].iloc[-1]
        
        print("💼 CURRENT BALANCE")
        print(f"  USD:  ${final_usd:,.2f}")
        print(f"  BTC:  {final_btc:.6f}")
        print()
    
    print("=" * 60)
    
    # Recommendations
    print()
    print("💡 RECOMMENDATIONS")
    
    if win_rate < 50:
        print("  ⚠️  Win rate below 50% - strategy may need tuning")
    elif win_rate > 65:
        print("  ✓ Strong win rate - strategy performing well")
    
    if profit_factor < 1.5:
        print("  ⚠️  Low profit factor - losses eating into gains")
    elif profit_factor > 2:
        print("  ✓ Excellent profit factor - winners >> losers")
    
    if avg_hold < 2:
        print("  💡 Very short hold times - consider reducing trade frequency to cut fees")
    
    if len(sells) < 10:
        print("  📊 Small sample size - need more trades for statistical significance")
    
    print()

def main():
    """Main analysis"""
    print()
    df = load_trades()
    
    if len(df) == 0:
        print("❌ No trades in file")
        return
    
    analyze_performance(df)

if __name__ == "__main__":
    main()
