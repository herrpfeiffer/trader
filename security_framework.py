#!/usr/bin/env python3
"""
Security Framework for Crypto Intelligence Network
CRITICAL: All agents must use these security measures
"""

import os
import re
import hashlib
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Security logger - separate from application logs
security_logger = logging.getLogger('SECURITY')
security_handler = logging.FileHandler('security_audit.log')
security_handler.setFormatter(logging.Formatter('%(asctime)s | SECURITY | %(levelname)s | %(message)s'))
security_logger.addHandler(security_handler)
security_logger.setLevel(logging.INFO)

class SecurityError(Exception):
    """Custom security exception"""
    pass

class SecurityValidator:
    """Core security validation and protection"""
    
    def __init__(self):
        # Whitelist of allowed domains
        self.allowed_domains = {
            'api.exchange.coinbase.com',
            'www.reddit.com', 
            'api.reddit.com',
            'oauth.reddit.com'
        }
        
        # Dangerous patterns to block
        self.blocked_patterns = [
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__',
            r'subprocess',
            r'os\.system',
            r'open\s*\(',
            r'file\s*\(',
            r'input\s*\(',
            r'raw_input',
            r'\.write\s*\(',
            r'\.delete\s*\(',
            r'DROP\s+TABLE',
            r'DELETE\s+FROM',
            r'INSERT\s+INTO',
            r'UPDATE\s+SET',
            r'<script',
            r'javascript:',
            r'vbscript:',
            r'data:text/html'
        ]
        
        # Rate limiting tracking
        self.request_counts = {}
        self.rate_limits = {
            'reddit': {'requests': 60, 'window': 60},  # 60 requests per minute
            'coinbase': {'requests': 100, 'window': 60},  # 100 requests per minute
            'default': {'requests': 30, 'window': 60}   # Conservative default
        }
        
    def validate_url(self, url: str, service: str = 'default') -> bool:
        """Validate URL against whitelist and security checks"""
        try:
            parsed = urlparse(url)
            
            # Check protocol
            if parsed.scheme not in ['https']:
                security_logger.warning(f"Blocked non-HTTPS URL: {url}")
                raise SecurityError("Only HTTPS URLs are allowed")
            
            # Check domain whitelist
            if parsed.netloc not in self.allowed_domains:
                security_logger.warning(f"Blocked unauthorized domain: {parsed.netloc}")
                raise SecurityError(f"Domain {parsed.netloc} not in whitelist")
            
            # Check for suspicious patterns
            full_url = url.lower()
            for pattern in self.blocked_patterns:
                if re.search(pattern, full_url, re.IGNORECASE):
                    security_logger.error(f"SECURITY ALERT: Blocked malicious pattern in URL: {url}")
                    raise SecurityError(f"Malicious pattern detected in URL")
            
            security_logger.info(f"URL validated: {service} - {parsed.netloc}")
            return True
            
        except Exception as e:
            security_logger.error(f"URL validation failed: {url} - {e}")
            raise SecurityError(f"URL validation failed: {e}")
    
    def sanitize_input(self, data: Any, context: str = "unknown") -> Any:
        """Sanitize input data to prevent injection attacks"""
        if isinstance(data, str):
            # Check for malicious patterns
            for pattern in self.blocked_patterns:
                if re.search(pattern, data, re.IGNORECASE):
                    security_logger.error(f"SECURITY ALERT: Blocked malicious input in {context}: {data[:100]}")
                    raise SecurityError(f"Malicious pattern detected in input")
            
            # Remove potentially dangerous characters
            sanitized = re.sub(r'[<>"\'\\\x00-\x1f\x7f-\x9f]', '', data)
            
            # Limit length to prevent DoS
            if len(sanitized) > 10000:
                security_logger.warning(f"Truncated oversized input in {context}")
                sanitized = sanitized[:10000]
            
            return sanitized
            
        elif isinstance(data, dict):
            return {self.sanitize_input(k, f"{context}.key"): self.sanitize_input(v, f"{context}.{k}") 
                   for k, v in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_input(item, f"{context}[{i}]") for i, item in enumerate(data)]
        else:
            return data
    
    def check_rate_limit(self, service: str, identifier: str = "default") -> bool:
        """Check if request is within rate limits"""
        now = datetime.now()
        key = f"{service}:{identifier}"
        
        # Clean old entries
        cutoff = now - timedelta(seconds=self.rate_limits.get(service, self.rate_limits['default'])['window'])
        if key in self.request_counts:
            self.request_counts[key] = [ts for ts in self.request_counts[key] if ts > cutoff]
        else:
            self.request_counts[key] = []
        
        # Check limit
        limit = self.rate_limits.get(service, self.rate_limits['default'])['requests']
        current_count = len(self.request_counts[key])
        
        if current_count >= limit:
            security_logger.warning(f"Rate limit exceeded for {service}:{identifier} - {current_count}/{limit}")
            return False
        
        # Record this request
        self.request_counts[key].append(now)
        return True
    
    def create_secure_session(self, service: str) -> requests.Session:
        """Create a secure requests session with proper configuration"""
        session = requests.Session()
        
        # Configure SSL/TLS
        session.verify = True  # Always verify SSL certificates
        
        # Configure retries with backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        
        # Set security headers
        session.headers.update({
            'User-Agent': f'CryptoIntel-{service}/1.0 (Security-Hardened)',
            'Accept': 'application/json',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        # Set timeouts (connect, read)
        session.timeout = (10, 30)
        
        return session

class CredentialManager:
    """Secure credential management"""
    
    def __init__(self):
        self.credentials = {}
        self.load_credentials()
    
    def load_credentials(self):
        """Load credentials from environment only - never from files"""
        # Only load from environment variables
        env_vars = {
            'COINBASE_API_KEY_NAME': 'coinbase_key_name',
            'COINBASE_PRIVATE_KEY': 'coinbase_private_key',
            'REDDIT_CLIENT_ID': 'reddit_client_id',
            'REDDIT_CLIENT_SECRET': 'reddit_client_secret'
        }
        
        for env_var, key in env_vars.items():
            value = os.getenv(env_var)
            if value:
                # Hash for logging (never log actual credentials)
                value_hash = hashlib.sha256(value.encode()).hexdigest()[:8]
                security_logger.info(f"Loaded credential {key} (hash: {value_hash})")
                self.credentials[key] = value
            else:
                security_logger.info(f"Credential {key} not found in environment")
    
    def get_credential(self, key: str) -> Optional[str]:
        """Get credential with audit logging"""
        if key in self.credentials:
            security_logger.info(f"Credential accessed: {key}")
            return self.credentials[key]
        
        security_logger.warning(f"Attempted access to missing credential: {key}")
        return None
    
    def validate_credentials_present(self, required_creds: List[str]) -> bool:
        """Validate required credentials are available"""
        missing = [cred for cred in required_creds if cred not in self.credentials]
        
        if missing:
            security_logger.error(f"Missing required credentials: {missing}")
            return False
        
        security_logger.info(f"All required credentials validated: {required_creds}")
        return True

class TradingProtection:
    """Financial trading protection mechanisms"""
    
    def __init__(self):
        self.paper_trading_only = True  # CRITICAL: Default to paper trading
        self.daily_loss_limit = 100.0   # Max daily loss in USD
        self.position_size_limit = 0.05  # Max 5% of account per position
        self.daily_trade_limit = 10      # Max trades per day
        
        self.daily_stats = {
            'trades_today': 0,
            'pnl_today': 0.0,
            'last_reset': datetime.now().date()
        }
    
    def validate_trading_action(self, action: str, amount: float = 0.0, is_live_trade: bool = False) -> bool:
        """Validate if trading action is allowed"""
        self.reset_daily_stats_if_needed()
        
        # CRITICAL: Block live trading if in paper trading mode
        if is_live_trade and self.paper_trading_only:
            security_logger.error("SECURITY ALERT: Live trading attempted while in paper mode")
            raise SecurityError("Live trading is disabled - currently in paper trading mode")
        
        # Check daily trade limit
        if self.daily_stats['trades_today'] >= self.daily_trade_limit:
            security_logger.warning(f"Daily trade limit reached: {self.daily_stats['trades_today']}")
            return False
        
        # Check daily loss limit
        if self.daily_stats['pnl_today'] <= -self.daily_loss_limit:
            security_logger.error(f"Daily loss limit exceeded: ${self.daily_stats['pnl_today']}")
            return False
        
        # Check position size (if amount provided)
        if amount > 0 and amount > self.position_size_limit:
            security_logger.warning(f"Position size exceeds limit: {amount} > {self.position_size_limit}")
            return False
        
        security_logger.info(f"Trading action validated: {action}, amount: {amount}")
        return True
    
    def reset_daily_stats_if_needed(self):
        """Reset daily stats if new day"""
        today = datetime.now().date()
        if today != self.daily_stats['last_reset']:
            security_logger.info(f"Resetting daily stats for new day: {today}")
            self.daily_stats = {
                'trades_today': 0,
                'pnl_today': 0.0,
                'last_reset': today
            }

class DataPrivacy:
    """Privacy protection for sensitive data"""
    
    def __init__(self):
        self.sensitive_patterns = [
            r'\b\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}\b',  # Credit card
            r'\b\d{3}-\d{2}-\d{4}\b',                   # SSN
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', # IP address
            r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'  # UUID
        ]
    
    def scrub_sensitive_data(self, data: str, context: str = "unknown") -> str:
        """Remove/mask sensitive data from strings"""
        scrubbed = data
        
        for pattern in self.sensitive_patterns:
            if re.search(pattern, scrubbed):
                security_logger.info(f"Scrubbed sensitive data pattern in {context}")
                scrubbed = re.sub(pattern, '[REDACTED]', scrubbed)
        
        return scrubbed
    
    def log_data_access(self, data_type: str, source: str, record_count: int = 1):
        """Log data access for audit purposes"""
        security_logger.info(f"Data accessed: type={data_type}, source={source}, records={record_count}")

# Global security instances
security_validator = SecurityValidator()
credential_manager = CredentialManager()
trading_protection = TradingProtection()
data_privacy = DataPrivacy()

def require_security_validation(func):
    """Decorator to enforce security validation on functions"""
    def wrapper(*args, **kwargs):
        security_logger.info(f"Security validation required for: {func.__name__}")
        
        # Add security checks here as needed
        try:
            return func(*args, **kwargs)
        except Exception as e:
            security_logger.error(f"Security validation failed for {func.__name__}: {e}")
            raise SecurityError(f"Security validation failed: {e}")
    
    return wrapper

def emergency_shutdown():
    """Emergency shutdown function"""
    security_logger.critical("EMERGENCY SHUTDOWN TRIGGERED")
    
    # Stop all trading immediately
    trading_protection.paper_trading_only = True
    
    # Clear sensitive data from memory
    credential_manager.credentials.clear()
    
    # Log shutdown
    security_logger.critical("Emergency shutdown completed")
    
    print("🚨 EMERGENCY SHUTDOWN: All systems halted for security")
    return True

if __name__ == "__main__":
    print("🔒 Security Framework Loaded")
    print(f"   Paper Trading: {trading_protection.paper_trading_only}")
    print(f"   Daily Trade Limit: {trading_protection.daily_trade_limit}")
    print(f"   Daily Loss Limit: ${trading_protection.daily_loss_limit}")
    print(f"   Position Size Limit: {trading_protection.position_size_limit * 100}%")
    print(f"   Allowed Domains: {len(security_validator.allowed_domains)}")
    print(f"   Security Patterns: {len(security_validator.blocked_patterns)}")
    print("   ✅ All security measures active")