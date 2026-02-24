#!/usr/bin/env python3
"""
AwakenSecurity Startup Script
Starts both the Python monitoring service and the Electron app
"""

import subprocess
import sys
import time
import os
import signal
import threading
from pathlib import Path

class AppStarter:
    def __init__(self):
        self.python_process = None
        self.electron_process = None
        self.running = True
        
    def start_python_api(self):
        """Start the Python API server"""
        print("Starting Python monitoring API...")
        python_dir = Path(__file__).parent / "python-agent"
        
        try:
            self.python_process = subprocess.Popen(
                [sys.executable, "api_server.py"],
                cwd=python_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(f"Python API started with PID: {self.python_process.pid}")
            return True
        except Exception as e:
            print(f"Failed to start Python API: {e}")
            return False
    
    def start_electron_app(self):
        """Start the Electron app"""
        print("Starting Electron app...")
        electron_dir = Path(__file__).parent / "electron-app"
        
        try:
            # Set NODE_ENV for development
            env = os.environ.copy()
            env['NODE_ENV'] = 'development'
            
            self.electron_process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=electron_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(f"Electron app started with PID: {self.electron_process.pid}")
            return True
        except Exception as e:
            print(f"Failed to start Electron app: {e}")
            return False
    
    def wait_for_python_api(self):
        """Wait for Python API to be ready"""
        import requests
        max_attempts = 30
        attempt = 0
        
        print("Waiting for Python API to be ready...")
        while attempt < max_attempts and self.running:
            try:
                response = requests.get("http://localhost:5000/health", timeout=1)
                if response.status_code == 200:
                    print("Python API is ready!")
                    return True
            except:
                pass
            
            attempt += 1
            time.sleep(1)
        
        print("Python API failed to start within 30 seconds")
        return False
    
    def monitor_processes(self):
        """Monitor both processes and restart if needed"""
        while self.running:
            # Check Python process
            if self.python_process and self.python_process.poll() is not None:
                print("Python API process died, restarting...")
                self.start_python_api()
            
            # Check Electron process
            if self.electron_process and self.electron_process.poll() is not None:
                print("Electron app process died, restarting...")
                self.start_electron_app()
            
            time.sleep(5)
    
    def cleanup(self):
        """Clean up processes on exit"""
        print("\nShutting down...")
        self.running = False
        
        if self.python_process:
            print("Stopping Python API...")
            self.python_process.terminate()
            try:
                self.python_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.python_process.kill()
        
        if self.electron_process:
            print("Stopping Electron app...")
            self.electron_process.terminate()
            try:
                self.electron_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.electron_process.kill()
        
        print("Cleanup complete")
    
    def run(self):
        """Main run method"""
        # Set up signal handlers
        signal.signal(signal.SIGINT, lambda s, f: self.cleanup())
        signal.signal(signal.SIGTERM, lambda s, f: self.cleanup())
        
        try:
            # Start Python API
            if not self.start_python_api():
                return False
            
            # Wait for Python API to be ready
            if not self.wait_for_python_api():
                return False
            
            # Start Electron app
            if not self.start_electron_app():
                return False
            
            # Start monitoring thread
            monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
            monitor_thread.start()
            
            print("\n" + "="*50)
            print("AwakenSecurity is running!")
            print("Electron app: http://localhost:3000")
            print("Python API: http://localhost:5000")
            print("Press Ctrl+C to stop")
            print("="*50 + "\n")
            
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

def main():
    """Main entry point"""
    print("AwakenSecurity Startup Script")
    print("Starting both Python monitoring service and Electron app...")
    
    starter = AppStarter()
    starter.run()

if __name__ == "__main__":
    main() 
