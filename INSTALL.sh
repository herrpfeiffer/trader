#!/bin/bash
# Complete installation - Run on trading-bot-1
set -e
CURRENT_USER=$(whoami)
APP_DIR="$HOME/trader"
echo "Installing Trading Agent..."
cd ~
rm -rf trader 2>/dev/null || true
git clone https://github.com/herrpfeiffer/trader.git 2>&1 || { echo "Git clone failed"; exit 1; }
cd "$APP_DIR"
mkdir -p "$APP_DIR/logs"
pip3 install --user -q pandas numpy requests PyJWT cryptography 2>&1 | grep -v "already satisfied" || true
[ ! -f "$APP_DIR/.env" ] && cat > "$APP_DIR/.env" << 'ENVEOF'
COINBASE_API_KEY_NAME=your_api_key_name_here
COINBASE_PRIVATE_KEY="-----BEGIN EC PRIVATE KEY-----
your_private_key_here
-----END EC PRIVATE KEY-----"
ENVEOF
chmod 600 "$APP_DIR/.env"
chmod +x "$APP_DIR"/*.py 2>/dev/null || true
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
sudo systemctl daemon-reload
sudo systemctl stop trader 2>/dev/null || true
sleep 1
sudo systemctl start trader
sudo systemctl enable trader
sleep 3
sudo systemctl status trader --no-pager -l | head -25
