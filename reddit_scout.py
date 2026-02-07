#!/usr/bin/env python3
"""
Reddit Scout - Monitors crypto subreddits for trending coins and sentiment
SECURITY: Uses security framework for all external requests and data validation
"""

import time
import re
from datetime import datetime
from intel_hub import IntelHub, Signal
import logging

# SECURITY: Import security framework
from security_framework import (
    security_validator, credential_manager, trading_protection, 
    data_privacy, require_security_validation, SecurityError
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

class RedditScout:
    """Monitor crypto subreddits for investment signals"""
    
    def __init__(self):
        self.hub = IntelHub()
        
        # Subreddits to monitor
        self.subreddits = [
            'cryptocurrency', 
            'CryptoMoonShots',
            'altcoins',
            'ethtrader',
            'Bitcoin'
        ]
        
        # Common crypto symbols to track
        self.symbols = {
            'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOGE', 'AVAX', 'DOT', 'MATIC',
            'SHIB', 'LTC', 'UNI', 'LINK', 'ATOM', 'FTM', 'ALGO', 'XLM', 'VET', 'ICP',
            'NEAR', 'APE', 'MANA', 'SAND', 'CRO', 'FTT', 'LRC', 'GRT', 'ENJ', 'COMP'
        }
        
        # Sentiment keywords
        self.bullish_words = {
            'moon', 'bullish', 'buy', 'pump', 'rocket', 'breakout', 'surge', 
            'rally', 'uptrend', 'hodl', 'gem', 'undervalued', 'potential'
        }
        
        self.bearish_words = {
            'dump', 'crash', 'bearish', 'sell', 'drop', 'falling', 'decline',
            'overvalued', 'bubble', 'scam', 'rug', 'avoid'
        }
        
    @require_security_validation
    def scan_subreddit(self, subreddit: str, limit: int = 25) -> dict:
        """Scan a subreddit for crypto mentions and sentiment with security validation"""
        try:
            # SECURITY: Sanitize inputs
            subreddit = security_validator.sanitize_input(subreddit, "subreddit")
            limit = min(max(int(limit), 1), 100)  # Clamp limit between 1-100
            
            # SECURITY: Check rate limits
            if not security_validator.check_rate_limit('reddit', subreddit):
                raise SecurityError(f"Rate limit exceeded for r/{subreddit}")
            
            # SECURITY: Validate URL and create secure session
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
            security_validator.validate_url(url, 'reddit')
            
            session = security_validator.create_secure_session('reddit')
            
            # SECURITY: Log data access
            data_privacy.log_data_access("reddit_posts", f"r/{subreddit}", limit)
            
            response = session.get(url)
            response.raise_for_status()
            
            data = response.json()
            posts = data['data']['children']
            
            results = {
                'subreddit': subreddit,
                'posts_scanned': len(posts),
                'symbol_mentions': {},
                'sentiment_scores': {},
                'total_engagement': 0
            }
            
            for post in posts:
                post_data = post['data']
                
                # SECURITY: Sanitize text data
                title = security_validator.sanitize_input(post_data.get('title', ''), 'reddit.title')
                selftext = security_validator.sanitize_input(post_data.get('selftext', ''), 'reddit.selftext')
                text = f"{title} {selftext}"
                
                # SECURITY: Scrub any sensitive data
                text = data_privacy.scrub_sensitive_data(text, 'reddit_post')
                
                # Track engagement (with bounds checking)
                score = max(0, min(int(post_data.get('score', 0)), 1000000))  # Cap at 1M
                comments = max(0, min(int(post_data.get('num_comments', 0)), 100000))  # Cap at 100K
                engagement = score + comments * 2  # Weight comments higher
                
                results['total_engagement'] += engagement
                
                # Find crypto symbols
                symbols_found = self.extract_symbols(text)
                
                for symbol in symbols_found:
                    if symbol not in results['symbol_mentions']:
                        results['symbol_mentions'][symbol] = 0
                        results['sentiment_scores'][symbol] = []
                    
                    results['symbol_mentions'][symbol] += 1
                    
                    # Calculate sentiment for this mention
                    sentiment = self.calculate_sentiment(text)
                    results['sentiment_scores'][symbol].append({
                        'sentiment': sentiment,
                        'engagement': engagement,
                        'title': post_data.get('title', '')[:100]
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error scanning r/{subreddit}: {e}")
            return {'error': str(e)}
    
    def extract_symbols(self, text: str) -> set:
        """Extract crypto symbols from text"""
        text_upper = text.upper()
        found_symbols = set()
        
        for symbol in self.symbols:
            # Look for $SYMBOL, SYMBOL, or SYMBOL/USD patterns
            patterns = [
                rf'\${symbol}\b',
                rf'\b{symbol}\b',
                rf'\b{symbol}/USD\b',
                rf'\b{symbol}-USD\b'
            ]
            
            for pattern in patterns:
                if re.search(pattern, text_upper):
                    found_symbols.add(symbol)
                    break
                    
        return found_symbols
    
    def calculate_sentiment(self, text: str) -> float:
        """Calculate sentiment score (-1.0 to 1.0)"""
        text_lower = text.lower()
        
        bullish_count = sum(1 for word in self.bullish_words if word in text_lower)
        bearish_count = sum(1 for word in self.bearish_words if word in text_lower)
        
        total_sentiment_words = bullish_count + bearish_count
        
        if total_sentiment_words == 0:
            return 0.0  # Neutral
        
        # Calculate sentiment score
        sentiment = (bullish_count - bearish_count) / total_sentiment_words
        return max(-1.0, min(1.0, sentiment))
    
    def generate_signals(self):
        """Scan all subreddits and generate signals"""
        logger.info("🔍 Starting Reddit scan...")
        
        all_mentions = {}
        all_sentiments = {}
        
        # Scan each subreddit
        for subreddit in self.subreddits:
            logger.info(f"Scanning r/{subreddit}...")
            results = self.scan_subreddit(subreddit)
            
            if 'error' in results:
                continue
                
            # Aggregate mentions across subreddits
            for symbol, count in results['symbol_mentions'].items():
                if symbol not in all_mentions:
                    all_mentions[symbol] = 0
                    all_sentiments[symbol] = []
                
                all_mentions[symbol] += count
                all_sentiments[symbol].extend(results['sentiment_scores'][symbol])
        
        # Generate signals for symbols with enough mentions
        for symbol, mention_count in all_mentions.items():
            if mention_count < 2:  # Skip symbols with too few mentions
                continue
                
            # Calculate average sentiment
            sentiments = [item['sentiment'] for item in all_sentiments[symbol]]
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
            
            # Calculate engagement weight
            engagements = [item['engagement'] for item in all_sentiments[symbol]]
            total_engagement = sum(engagements)
            
            # Generate signal strength (0.0 to 1.0)
            mention_strength = min(mention_count / 10.0, 1.0)  # Normalize mentions
            sentiment_strength = (avg_sentiment + 1.0) / 2.0   # Convert -1,1 to 0,1
            engagement_strength = min(total_engagement / 1000.0, 1.0)  # Normalize engagement
            
            # Weighted average
            signal_strength = (mention_strength * 0.4 + 
                             sentiment_strength * 0.4 + 
                             engagement_strength * 0.2)
            
            # Confidence based on sample size
            confidence = min(mention_count / 5.0, 1.0)
            
            # Determine signal type
            if avg_sentiment > 0.2:
                signal_type = 'positive_sentiment'
            elif avg_sentiment < -0.2:
                signal_type = 'negative_sentiment'
            else:
                signal_type = 'neutral_buzz'
            
            # Create signal
            signal = Signal(
                source='reddit',
                symbol=symbol,
                signal_type=signal_type,
                strength=signal_strength,
                confidence=confidence,
                timestamp=datetime.now().isoformat(),
                details={
                    'mentions': mention_count,
                    'avg_sentiment': round(avg_sentiment, 3),
                    'total_engagement': total_engagement,
                    'subreddits_count': len([s for s in all_sentiments[symbol]]),
                    'sample_titles': [item['title'] for item in all_sentiments[symbol][:3]]
                }
            )
            
            # Add to hub
            self.hub.add_signal(signal)
            
            logger.info(f"Generated signal for {symbol}: {signal_strength:.3f} "
                       f"(mentions: {mention_count}, sentiment: {avg_sentiment:.2f})")
    
    def run_continuous(self, interval_minutes: int = 30):
        """Run scout continuously"""
        logger.info(f"🚀 Reddit Scout started (scanning every {interval_minutes} minutes)")
        
        while True:
            try:
                self.generate_signals()
                logger.info(f"💤 Sleeping for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Reddit Scout stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in continuous run: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

def main():
    """Run Reddit scout once"""
    scout = RedditScout()
    scout.generate_signals()
    
    # Show results
    hub = IntelHub()
    hub.print_report()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        scout = RedditScout()
        scout.run_continuous()
    else:
        main()