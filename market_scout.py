#!/usr/bin/env python3
"""
Market Scout - Monitors Coinbase for top gainers/losers, volume spikes, and momentum  
SECURITY: Uses security framework for all API requests and data validation
"""

import time
from datetime import datetime, timedelta
from intel_hub import IntelHub, Signal
import logging

# SECURITY: Import security framework  
from security_framework import (
    security_validator, credential_manager, trading_protection,
    data_privacy, require_security_validation, SecurityError
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

class MarketScout:
    """Monitor market data for investment signals"""
    
    def __init__(self):
        self.hub = IntelHub()
        self.base_url = "https://api.exchange.coinbase.com"
        
        # Track previous data for change detection
        self.previous_data = {}
        
    @require_security_validation
    def get_all_products(self):
        """Get all trading pairs from Coinbase with security validation"""
        try:
            # SECURITY: Check rate limits
            if not security_validator.check_rate_limit('coinbase', 'products'):
                raise SecurityError("Rate limit exceeded for Coinbase products API")
            
            url = f"{self.base_url}/products"
            
            # SECURITY: Validate URL and create secure session
            security_validator.validate_url(url, 'coinbase')
            session = security_validator.create_secure_session('coinbase')
            
            # SECURITY: Log data access
            data_privacy.log_data_access("coinbase_products", "api.exchange.coinbase.com")
            
            response = session.get(url)
            response.raise_for_status()
            
            products = response.json()
            
            # Filter for USD pairs only
            usd_pairs = [p for p in products 
                        if p['quote_currency'] == 'USD' and p['status'] == 'online']
            
            return usd_pairs
            
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            return []
    
    @require_security_validation  
    def get_24hr_stats(self):
        """Get 24hr statistics for all products with security validation"""
        try:
            # SECURITY: Check rate limits
            if not security_validator.check_rate_limit('coinbase', 'stats'):
                raise SecurityError("Rate limit exceeded for Coinbase stats API")
            
            url = f"{self.base_url}/products/stats"
            security_validator.validate_url(url, 'coinbase')
            session = security_validator.create_secure_session('coinbase')
            
            data_privacy.log_data_access("coinbase_stats", "api.exchange.coinbase.com")
            
            response = session.get(url)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error fetching 24hr stats: {e}")
            return {}
    
    def get_ticker_data(self, product_ids):
        """Get current ticker data for products"""
        ticker_data = {}
        
        # Get data in batches to avoid rate limits
        for i in range(0, len(product_ids), 10):
            batch = product_ids[i:i+10]
            
            for product_id in batch:
                try:
                    response = requests.get(f"{self.base_url}/products/{product_id}/ticker", 
                                          timeout=5)
                    if response.status_code == 200:
                        ticker_data[product_id] = response.json()
                    
                    time.sleep(0.1)  # Rate limit protection
                    
                except Exception as e:
                    logger.warning(f"Error fetching ticker for {product_id}: {e}")
                    continue
        
        return ticker_data
    
    def analyze_market_data(self):
        """Analyze market data and generate signals"""
        logger.info("📊 Analyzing market data...")
        
        # Get products and stats
        products = self.get_all_products()
        if not products:
            return
        
        stats = self.get_24hr_stats()
        if not stats:
            return
        
        # Get current ticker data
        product_ids = [p['id'] for p in products]
        tickers = self.get_ticker_data(product_ids)
        
        signals_generated = 0
        
        for product in products:
            product_id = product['id']
            base_currency = product['base_currency']
            
            # Skip if no data
            if product_id not in stats or product_id not in tickers:
                continue
            
            try:
                stat = stats[product_id]
                ticker = tickers[product_id]
                
                # Extract metrics
                price = float(ticker.get('price', 0))
                volume_24hr = float(stat.get('volume', 0))
                price_change_24hr = float(stat.get('price_change_24h', 0))
                price_change_pct = float(stat.get('price_change_percent_24h', 0)) * 100
                
                if price == 0 or volume_24hr == 0:
                    continue
                
                # Generate signals based on different criteria
                signals = []
                
                # 1. Price momentum signal
                if abs(price_change_pct) >= 5.0:  # Significant price movement
                    signal_type = 'price_breakout' if price_change_pct > 0 else 'price_breakdown'
                    strength = min(abs(price_change_pct) / 20.0, 1.0)  # Cap at 20%
                    confidence = min(volume_24hr / 100000, 1.0)  # Higher volume = higher confidence
                    
                    signals.append(Signal(
                        source='market',
                        symbol=base_currency,
                        signal_type=signal_type,
                        strength=strength,
                        confidence=confidence,
                        timestamp=datetime.now().isoformat(),
                        details={
                            'price': price,
                            'price_change_24hr': price_change_24hr,
                            'price_change_pct': price_change_pct,
                            'volume_24hr': volume_24hr,
                            'product_id': product_id
                        }
                    ))
                
                # 2. Volume spike signal (need previous data)
                if product_id in self.previous_data:
                    prev_volume = self.previous_data[product_id].get('volume_24hr', volume_24hr)
                    if prev_volume > 0:
                        volume_change = (volume_24hr - prev_volume) / prev_volume
                        
                        if volume_change > 0.5:  # 50%+ volume increase
                            strength = min(volume_change, 2.0) / 2.0  # Cap at 200% increase
                            confidence = 0.8  # Volume spikes are usually significant
                            
                            signals.append(Signal(
                                source='market',
                                symbol=base_currency,
                                signal_type='volume_spike',
                                strength=strength,
                                confidence=confidence,
                                timestamp=datetime.now().isoformat(),
                                details={
                                    'current_volume': volume_24hr,
                                    'previous_volume': prev_volume,
                                    'volume_change_pct': volume_change * 100,
                                    'price': price,
                                    'product_id': product_id
                                }
                            ))
                
                # 3. Momentum continuation signal
                if price_change_pct > 2.0 and volume_24hr > 50000:  # Positive momentum with volume
                    # Check if this is building momentum (simplified)
                    strength = min(price_change_pct / 10.0, 1.0)  # Normalize to 10%
                    confidence = min(volume_24hr / 200000, 1.0)
                    
                    signals.append(Signal(
                        source='market',
                        symbol=base_currency,
                        signal_type='momentum_continuation',
                        strength=strength,
                        confidence=confidence,
                        timestamp=datetime.now().isoformat(),
                        details={
                            'price': price,
                            'price_change_pct': price_change_pct,
                            'volume_24hr': volume_24hr,
                            'product_id': product_id
                        }
                    ))
                
                # Add signals to hub
                for signal in signals:
                    self.hub.add_signal(signal)
                    signals_generated += 1
                    
                    logger.info(f"Generated {signal.signal_type} signal for {base_currency}: "
                              f"{signal.strength:.3f} ({price_change_pct:+.2f}%)")
                
                # Store current data for next comparison
                self.previous_data[product_id] = {
                    'volume_24hr': volume_24hr,
                    'price': price,
                    'timestamp': datetime.now().isoformat()
                }
                
            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing {product_id}: {e}")
                continue
        
        logger.info(f"Generated {signals_generated} market signals")
    
    def get_top_movers(self, limit: int = 10):
        """Get top gainers and losers"""
        logger.info("🚀 Finding top movers...")
        
        stats = self.get_24hr_stats()
        if not stats:
            return [], []
        
        # Convert to list with price change data
        movers = []
        for product_id, stat in stats.items():
            try:
                if '-USD' not in product_id:
                    continue
                    
                price_change_pct = float(stat.get('price_change_percent_24h', 0)) * 100
                volume = float(stat.get('volume', 0))
                
                if abs(price_change_pct) > 0.1 and volume > 1000:  # Filter noise
                    movers.append({
                        'symbol': product_id.replace('-USD', ''),
                        'product_id': product_id,
                        'price_change_pct': price_change_pct,
                        'volume': volume,
                        'price': float(stat.get('last', 0))
                    })
                    
            except (ValueError, KeyError):
                continue
        
        # Sort by price change
        movers.sort(key=lambda x: x['price_change_pct'], reverse=True)
        
        gainers = movers[:limit]
        losers = movers[-limit:]
        
        return gainers, losers
    
    def print_market_report(self):
        """Print current market analysis"""
        gainers, losers = self.get_top_movers()
        
        print("\n" + "="*50)
        print("📊 MARKET ANALYSIS REPORT")
        print("="*50)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n🚀 TOP GAINERS:")
        for i, gainer in enumerate(gainers, 1):
            print(f"{i:2d}. {gainer['symbol']:8s} | {gainer['price_change_pct']:+6.2f}% | "
                  f"Vol: ${gainer['volume']:,.0f}")
        
        print(f"\n📉 TOP LOSERS:")
        for i, loser in enumerate(losers, 1):
            print(f"{i:2d}. {loser['symbol']:8s} | {loser['price_change_pct']:+6.2f}% | "
                  f"Vol: ${loser['volume']:,.0f}")
        
        print("\n" + "="*50)
    
    def run_continuous(self, interval_minutes: int = 15):
        """Run scout continuously"""
        logger.info(f"📊 Market Scout started (scanning every {interval_minutes} minutes)")
        
        while True:
            try:
                self.analyze_market_data()
                logger.info(f"💤 Sleeping for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Market Scout stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in continuous run: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

def main():
    """Run market scout once"""
    scout = MarketScout()
    
    # Show market report
    scout.print_market_report()
    
    # Generate signals
    scout.analyze_market_data()
    
    # Show combined intelligence
    hub = IntelHub()
    hub.print_report()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        scout = MarketScout()
        scout.run_continuous()
    else:
        main()