#!/bin/bash
# Crypto Trading Agent - Quick Setup Script

echo "=========================================="
echo "Crypto Trading Agent Setup"
echo "=========================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install pandas numpy requests --break-system-packages -q
echo "✓ Dependencies installed"
echo ""

# Check for API credentials
if [ -z "$COINBASE_API_KEY" ]; then
    echo "⚠️  WARNING: COINBASE_API_KEY not set"
    echo ""
    echo "To set your API credentials:"
    echo "  export COINBASE_API_KEY='your_key_here'"
    echo "  export COINBASE_API_SECRET='your_secret_here'"
    echo "  export COINBASE_API_PASSPHRASE='your_passphrase_here'"
    echo ""
    echo "Get your API key at: https://www.coinbase.com/settings/api"
    echo "(For paper trading, create a VIEW-ONLY key)"
    echo ""
    exit 1
else
    echo "✓ API credentials found"
    echo ""
fi

# Create logs directory
mkdir -p logs
echo "✓ Logs directory created"
echo ""

# Run the agent
echo "=========================================="
echo "Starting Trading Agent in PAPER TRADING mode"
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

python3 crypto_agent.py
