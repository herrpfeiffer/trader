#!/usr/bin/env python3
"""
Demo Data Generator - Creates sample signals to test the intelligence system
"""

from datetime import datetime
from intel_hub import IntelHub, Signal
import random

def generate_demo_signals():
    """Generate realistic demo signals"""
    hub = IntelHub()
    
    # Demo Reddit signals
    reddit_signals = [
        Signal('reddit', 'ETH', 'positive_sentiment', 0.8, 0.9, datetime.now().isoformat(),
               {'mentions': 15, 'avg_sentiment': 0.6, 'subreddits': ['cryptocurrency', 'ethereum']}),
        Signal('reddit', 'SOL', 'positive_sentiment', 0.7, 0.8, datetime.now().isoformat(),
               {'mentions': 8, 'avg_sentiment': 0.4, 'subreddits': ['CryptoMoonShots']}),
        Signal('reddit', 'DOGE', 'neutral_buzz', 0.5, 0.6, datetime.now().isoformat(),
               {'mentions': 12, 'avg_sentiment': 0.1, 'subreddits': ['cryptocurrency']}),
    ]
    
    # Demo Market signals  
    market_signals = [
        Signal('market', 'ETH', 'price_breakout', 0.9, 0.95, datetime.now().isoformat(),
               {'price_change_pct': 8.5, 'volume_24hr': 150000}),
        Signal('market', 'AVAX', 'volume_spike', 0.75, 0.8, datetime.now().isoformat(),
               {'volume_change_pct': 120, 'price_change_pct': 3.2}),
        Signal('market', 'SOL', 'momentum_continuation', 0.65, 0.7, datetime.now().isoformat(),
               {'price_change_pct': 5.1, 'volume_24hr': 80000}),
    ]
    
    # Add all signals
    for signal in reddit_signals + market_signals:
        hub.add_signal(signal)
    
    print("✅ Demo signals generated!")
    return len(reddit_signals) + len(market_signals)

if __name__ == "__main__":
    count = generate_demo_signals()
    print(f"Generated {count} demo signals")
    
    # Show the intelligence report
    hub = IntelHub()
    hub.print_report()