#!/usr/bin/env python3
"""
Crypto Intelligence Hub - Aggregates signals from multiple scouts
SECURITY: Uses security framework for all operations
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import logging

# SECURITY: Import security framework
from security_framework import (
    security_validator, credential_manager, trading_protection, 
    data_privacy, require_security_validation, SecurityError
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Signal:
    """Individual signal from a scout agent"""
    source: str          # 'reddit', 'market', 'news', etc.
    symbol: str          # 'BTC', 'ETH', 'DOGE', etc.
    signal_type: str     # 'momentum', 'sentiment', 'volume', etc.
    strength: float      # 0.0 to 1.0
    confidence: float    # 0.0 to 1.0 
    timestamp: str
    details: Dict        # Additional context
    
@dataclass 
class Opportunity:
    """Ranked investment opportunity"""
    symbol: str
    composite_score: float
    signals: List[Signal]
    recommendation: str   # 'STRONG_BUY', 'BUY', 'WATCH', 'AVOID'
    risk_level: str      # 'LOW', 'MEDIUM', 'HIGH'
    last_updated: str

class IntelHub:
    """Central intelligence aggregator"""
    
    def __init__(self):
        self.data_dir = Path("./intel_data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Signal storage
        self.signals_file = self.data_dir / "signals.json"
        self.opportunities_file = self.data_dir / "opportunities.json"
        
        # Scoring weights
        self.weights = {
            'reddit': 0.3,
            'market': 0.5, 
            'news': 0.2
        }
        
        # Thresholds
        self.min_signals = 2  # Minimum signals needed for recommendation
        self.score_thresholds = {
            'STRONG_BUY': 0.8,
            'BUY': 0.6,
            'WATCH': 0.4,
            'AVOID': 0.2
        }
        
    @require_security_validation
    def add_signal(self, signal: Signal):
        """Add new signal from scout agent with security validation"""
        try:
            # SECURITY: Validate signal data
            signal.symbol = security_validator.sanitize_input(signal.symbol, "signal.symbol")
            signal.source = security_validator.sanitize_input(signal.source, "signal.source")
            signal.signal_type = security_validator.sanitize_input(signal.signal_type, "signal.signal_type")
            
            # SECURITY: Validate signal strength/confidence ranges
            if not (0.0 <= signal.strength <= 1.0):
                raise SecurityError(f"Invalid signal strength: {signal.strength}")
            if not (0.0 <= signal.confidence <= 1.0):
                raise SecurityError(f"Invalid signal confidence: {signal.confidence}")
            
            # SECURITY: Sanitize details
            if signal.details:
                signal.details = security_validator.sanitize_input(signal.details, "signal.details")
            
            # SECURITY: Log data access
            data_privacy.log_data_access("signal", signal.source, 1)
            
            signals = self.load_signals()
            signals.append(asdict(signal))
            
            # Keep only last 24 hours of signals
            cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
            signals = [s for s in signals if s['timestamp'] > cutoff]
            
            self.save_signals(signals)
            logger.info(f"Added {signal.source} signal for {signal.symbol}: {signal.strength:.2f}")
            
        except Exception as e:
            logger.error(f"Security validation failed for signal: {e}")
            raise SecurityError(f"Signal validation failed: {e}")
        
    def analyze_opportunities(self) -> List[Opportunity]:
        """Analyze all signals and generate ranked opportunities"""
        signals = self.load_signals()
        
        # Group signals by symbol
        by_symbol = {}
        for signal_data in signals:
            symbol = signal_data['symbol']
            if symbol not in by_symbol:
                by_symbol[symbol] = []
            by_symbol[symbol].append(Signal(**signal_data))
            
        opportunities = []
        
        for symbol, symbol_signals in by_symbol.items():
            # Skip if not enough signals
            if len(symbol_signals) < self.min_signals:
                continue
                
            # Calculate composite score
            score = self.calculate_composite_score(symbol_signals)
            
            # Determine recommendation
            recommendation = self.get_recommendation(score)
            risk_level = self.assess_risk(symbol_signals)
            
            opportunity = Opportunity(
                symbol=symbol,
                composite_score=score,
                signals=symbol_signals,
                recommendation=recommendation,
                risk_level=risk_level,
                last_updated=datetime.now().isoformat()
            )
            
            opportunities.append(opportunity)
            
        # Sort by score (highest first)
        opportunities.sort(key=lambda x: x.composite_score, reverse=True)
        
        # Save opportunities
        self.save_opportunities(opportunities)
        
        return opportunities
    
    def calculate_composite_score(self, signals: List[Signal]) -> float:
        """Calculate weighted composite score for a symbol"""
        if not signals:
            return 0.0
            
        # Group by source and take average
        source_scores = {}
        for signal in signals:
            if signal.source not in source_scores:
                source_scores[signal.source] = []
            source_scores[signal.source].append(signal.strength * signal.confidence)
            
        # Calculate weighted average
        weighted_sum = 0.0
        total_weight = 0.0
        
        for source, scores in source_scores.items():
            weight = self.weights.get(source, 0.1)
            avg_score = sum(scores) / len(scores)
            weighted_sum += avg_score * weight
            total_weight += weight
            
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def get_recommendation(self, score: float) -> str:
        """Convert score to recommendation"""
        for rec, threshold in self.score_thresholds.items():
            if score >= threshold:
                return rec
        return 'AVOID'
    
    def assess_risk(self, signals: List[Signal]) -> str:
        """Assess risk level based on signals"""
        # Simple heuristic: more signals = lower risk
        if len(signals) >= 4:
            return 'LOW'
        elif len(signals) >= 3:
            return 'MEDIUM' 
        else:
            return 'HIGH'
    
    def get_top_opportunities(self, limit: int = 5) -> List[Opportunity]:
        """Get top N opportunities"""
        opportunities = self.analyze_opportunities()
        
        # Filter for actionable recommendations
        actionable = [opp for opp in opportunities 
                     if opp.recommendation in ['STRONG_BUY', 'BUY']]
        
        return actionable[:limit]
    
    def print_report(self):
        """Print intelligence report"""
        opportunities = self.analyze_opportunities()
        
        print("\n" + "="*60)
        print("🚀 CRYPTO INTELLIGENCE REPORT")
        print("="*60)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Opportunities Found: {len(opportunities)}")
        print()
        
        for i, opp in enumerate(opportunities[:10], 1):
            print(f"{i:2d}. {opp.symbol:8s} | Score: {opp.composite_score:.3f} | "
                  f"{opp.recommendation:10s} | Risk: {opp.risk_level}")
            
            # Show signal breakdown
            for signal in opp.signals[-3:]:  # Last 3 signals
                print(f"     └─ {signal.source:8s}: {signal.strength:.2f} "
                      f"({signal.signal_type})")
        print()
    
    def load_signals(self) -> List[Dict]:
        """Load signals from file"""
        if not self.signals_file.exists():
            return []
        try:
            with open(self.signals_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def save_signals(self, signals: List[Dict]):
        """Save signals to file"""
        with open(self.signals_file, 'w') as f:
            json.dump(signals, f, indent=2)
    
    def save_opportunities(self, opportunities: List[Opportunity]):
        """Save opportunities to file"""
        data = [asdict(opp) for opp in opportunities]
        with open(self.opportunities_file, 'w') as f:
            json.dump(data, f, indent=2)

def main():
    """Run intelligence analysis"""
    hub = IntelHub()
    
    # Analyze current signals
    hub.print_report()
    
    # Get actionable opportunities
    top_opps = hub.get_top_opportunities()
    
    if top_opps:
        print("🎯 ACTIONABLE OPPORTUNITIES:")
        for opp in top_opps:
            print(f"   {opp.symbol}: {opp.recommendation} (Score: {opp.composite_score:.3f})")
    else:
        print("⏳ No strong opportunities at this time.")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()