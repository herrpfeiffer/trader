#!/usr/bin/env python3
"""
Launch Script for Crypto Intelligence Network
"""

import subprocess
import time
import signal
import sys
from pathlib import Path
import argparse

class ScoutLauncher:
    """Manage multiple scout agents"""
    
    def __init__(self):
        self.processes = []
        self.running = False
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n🛑 Shutting down scout network...")
        self.stop_all()
        sys.exit(0)
    
    def launch_single(self, scout_name: str):
        """Launch a single scout for testing"""
        scouts = {
            'reddit': 'reddit_scout.py',
            'market': 'market_scout.py', 
            'intel': 'intel_hub.py'
        }
        
        if scout_name not in scouts:
            print(f"❌ Unknown scout: {scout_name}")
            print(f"Available scouts: {list(scouts.keys())}")
            return
        
        script = scouts[scout_name]
        if not Path(script).exists():
            print(f"❌ Script not found: {script}")
            return
        
        print(f"🚀 Launching {scout_name} scout...")
        
        if scout_name == 'intel':
            # Just run analysis once
            subprocess.run(['python3', script])
        else:
            # Run with --continuous flag
            subprocess.run(['python3', script, '--continuous'])
    
    def launch_all(self):
        """Launch all scout agents"""
        print("🚀 Starting Crypto Intelligence Network...")
        print("   Press Ctrl+C to stop all agents")
        
        # Setup signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        
        scouts = [
            ('Reddit Scout', 'reddit_scout.py'),
            ('Market Scout', 'market_scout.py')
        ]
        
        self.running = True
        
        for name, script in scouts:
            if not Path(script).exists():
                print(f"❌ {script} not found, skipping {name}")
                continue
            
            print(f"   Starting {name}...")
            process = subprocess.Popen(['python3', script, '--continuous'])
            self.processes.append((name, process))
            time.sleep(2)  # Stagger startup
        
        if not self.processes:
            print("❌ No scouts launched")
            return
        
        print(f"✅ {len(self.processes)} scouts running")
        print("   Monitor with: python3 intel_hub.py")
        print("   Stop with: Ctrl+C")
        
        # Keep running until stopped
        try:
            while self.running:
                # Check if any process died
                for name, process in self.processes[:]:
                    if process.poll() is not None:
                        print(f"⚠️  {name} stopped unexpectedly")
                        self.processes.remove((name, process))
                
                if not self.processes:
                    print("❌ All scouts stopped")
                    break
                
                time.sleep(10)
                
        except KeyboardInterrupt:
            self.signal_handler(None, None)
    
    def stop_all(self):
        """Stop all running processes"""
        self.running = False
        
        for name, process in self.processes:
            print(f"   Stopping {name}...")
            process.terminate()
            
            # Wait for graceful shutdown
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"   Force killing {name}...")
                process.kill()
        
        self.processes.clear()
        print("✅ All scouts stopped")
    
    def show_status(self):
        """Show current intelligence status"""
        print("📊 Current Intelligence Status")
        print("-" * 40)
        
        # Run intel hub analysis
        subprocess.run(['python3', 'intel_hub.py'])
    
    def run_demo(self):
        """Run a quick demo of all components"""
        print("🎭 DEMO: Crypto Intelligence Network")
        print("=" * 50)
        
        # Test each component
        components = [
            ("Reddit Scout", "reddit_scout.py"),
            ("Market Scout", "market_scout.py"),
            ("Intelligence Hub", "intel_hub.py")
        ]
        
        for name, script in components:
            if not Path(script).exists():
                print(f"❌ {name}: {script} not found")
                continue
            
            print(f"\n🔍 Testing {name}...")
            try:
                result = subprocess.run(['python3', script], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    print(f"✅ {name}: Working")
                else:
                    print(f"⚠️  {name}: Error - {result.stderr}")
            except subprocess.TimeoutExpired:
                print(f"⏱️  {name}: Timeout (may need API access)")
            except Exception as e:
                print(f"❌ {name}: Exception - {e}")

def main():
    parser = argparse.ArgumentParser(description='Crypto Intelligence Network Launcher')
    parser.add_argument('command', choices=['demo', 'reddit', 'market', 'intel', 'all', 'status'],
                      help='Command to run')
    
    args = parser.parse_args()
    launcher = ScoutLauncher()
    
    if args.command == 'demo':
        launcher.run_demo()
    elif args.command == 'all':
        launcher.launch_all()
    elif args.command == 'status':
        launcher.show_status()
    else:
        launcher.launch_single(args.command)

if __name__ == "__main__":
    main()