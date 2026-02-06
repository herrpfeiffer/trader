#!/bin/bash
# Complete setup script for trading-bot-1
# Run this on the GCP instance

set -e

CURRENT_USER=$(whoami)
APP_DIR="$HOME/trader"

echo "=========================================="
echo "Setting up Trading Agent"
echo "=========================================="
echo "User: $CURRENT_USER"
echo "Directory: $APP_DIR"
echo ""

# Step 1: Create directory
mkdir -p "$APP_DIR/logs"
cd "$APP_DIR" || { echo "Failed to create directory"; exit 1; }
echo "✓ Directory ready"
echo ""

# Step 2: Install dependencies
echo "Installing Python dependencies..."
pip3 install --user -q pandas numpy requests PyJWT cryptography 2>&1 | grep -v "already satisfied" || true
echo "✓ Dependencies installed"
echo ""

# Step 3: Create .env if missing
if [ ! -f "$APP_DIR/.env" ]; then
    cat > "$APP_DIR/.env" << 'ENVEOF'
COINBASE_API_KEY_NAME=your_api_key_name_here
COINBASE_PRIVATE_KEY="-----BEGIN EC PRIVATE KEY-----
your_private_key_here
-----END EC PRIVATE KEY-----"
ENVEOF
    chmod 600 "$APP_DIR/.env"
    echo "⚠️  Created .env template - EDIT IT with your API credentials!"
else
    echo "✓ .env file exists"
fi
echo ""

# Step 4: Make scripts executable
chmod +x "$APP_DIR"/*.py 2>/dev/null || true
echo "✓ Scripts executable"
echo ""

# Step 5: Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/trader.service > /dev/null << EOF
[Unit]
Description=Crypto Trading Agent
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$APP_DIR
Environment="PATH=/usr/bin:/usr/local/bin:/home/$CURRENT_USER/.local/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=/usr/bin/python3 $APP_DIR/crypto_agent.py
Restart=always
RestartSec=10
StandardOutput=append:$APP_DIR/logs/trader.log
StandardError=append:$APP_DIR/logs/trader.error.log

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Service file created"
echo ""

# Step 6: Start service
echo "Starting service..."
sudo systemctl daemon-reload
sudo systemctl stop trader 2>/dev/null || true
sleep 1
sudo systemctl start trader
sudo systemctl enable trader
sleep 3
echo ""

# Step 7: Check status
echo "=========================================="
echo "Service Status:"
echo "=========================================="
sudo systemctl status trader --no-pager -l | head -25
echo ""

if sudo systemctl is-active --quiet trader; then
    echo "✅ ✅ ✅ SERVICE IS RUNNING! ✅ ✅ ✅"
    echo ""
    echo "View logs: tail -f $APP_DIR/trading_agent.log"
else
    echo "❌ Service not running - check errors above"
fi
echo ""
