import time
import json
import threading
import cv2
import numpy as np
from mss import mss
import pytesseract
from datetime import datetime
import os
import sys
from pathlib import Path
from ai_agent import ai_agent

class SecurityMonitor:
    def __init__(self):
        self.is_running = False
        self.monitoring_thread = None
        self.sct = mss()
        self.alerts = []
        self.last_activity = None
        self.monitoring_interval = 5  # seconds
        self.enable_ocr = True
        self.enable_ml = True
        
        # Suspicious keywords for OCR detection
        self.suspicious_keywords = [
            'password', 'login', 'credit card', 'ssn', 'social security',
            'bank account', 'routing number', 'pin', 'cvv', 'expiry',
            'username', 'email', 'phone', 'address', 'dob', 'birth'
        ]
        
        # Create logs directory
        self.logs_dir = Path(__file__).parent / 'logs'
        self.logs_dir.mkdir(exist_ok=True)
        
    def start_monitoring(self):
        """Start the monitoring process"""
        if self.is_running:
            return {"success": False, "message": "Monitoring already running"}
        
        self.is_running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        self.log_event("Monitoring started")
        return {"success": True, "message": "Monitoring started successfully"}
    
    def stop_monitoring(self):
        """Stop the monitoring process"""
        if not self.is_running:
            return {"success": False, "message": "Monitoring not running"}
        
        self.is_running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)
        
        self.log_event("Monitoring stopped")
        return {"success": True, "message": "Monitoring stopped successfully"}
    
    def get_status(self):
        """Get current monitoring status"""
        return {
            "isRunning": self.is_running,
            "lastActivity": self.last_activity,
            "alerts": self.alerts[-10:],  # Last 10 alerts
            "monitoringInterval": self.monitoring_interval,
            "enableOCR": self.enable_ocr,
            "enableML": self.enable_ml
        }
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                self._capture_and_analyze()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                self.log_event(f"Error in monitoring loop: {str(e)}")
                time.sleep(1)
    
    def _capture_and_analyze(self):
        """Capture screen and analyze for security threats"""
        try:
            # Capture screen
            screenshot = self.sct.grab(self.sct.monitors[1])  # Primary monitor
            img = np.array(screenshot)
            
            # Convert to RGB for processing
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
            
            # Update last activity
            self.last_activity = datetime.now().isoformat()
            
            # Perform OCR if enabled
            if self.enable_ocr:
                self._perform_ocr_analysis(img_rgb)
            
            # Perform ML analysis if enabled
            if self.enable_ml:
                self._perform_ml_analysis(img_rgb)
                
        except Exception as e:
            self.log_event(f"Error capturing screen: {str(e)}")
    
    def _perform_ocr_analysis(self, img):
        """Perform OCR analysis on the captured image"""
        try:
            # Extract text from image
            text = pytesseract.image_to_string(img).lower()
            
            # Check for suspicious keywords
            found_keywords = []
            for keyword in self.suspicious_keywords:
                if keyword in text:
                    found_keywords.append(keyword)
            
            if found_keywords:
                alert_msg = f"Potential sensitive data detected: {', '.join(found_keywords)}"
                self._add_alert(alert_msg, "OCR_DETECTION")
                
        except Exception as e:
            self.log_event(f"Error in OCR analysis: {str(e)}")
    
    def _perform_ml_analysis(self, img):
        """Perform basic ML analysis on the captured image"""
        try:
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            
            # Basic edge detection to identify forms or input fields
            edges = cv2.Canny(gray, 50, 150)
            
            # Count potential form elements (rectangular shapes)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Look for rectangular shapes that might be input fields
            potential_inputs = 0
            for contour in contours:
                # Approximate the contour to a polygon
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # If it's a rectangle (4 points), it might be an input field
                if len(approx) == 4:
                    area = cv2.contourArea(contour)
                    if 100 < area < 10000:  # Reasonable size for input fields
                        potential_inputs += 1
            
            # Alert if many potential input fields detected
            if potential_inputs > 5:
                alert_msg = f"Multiple potential input fields detected ({potential_inputs})"
                self._add_alert(alert_msg, "ML_DETECTION")
                
        except Exception as e:
            self.log_event(f"Error in ML analysis: {str(e)}")
    
    def _add_alert(self, message, alert_type):
        """Add a new security alert"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "type": alert_type,
            "severity": "medium"
        }
        
        self.alerts.append(alert)
        self.log_event(f"ALERT: {message}")
        
        # Process with AI agent for enhanced insights
        if ai_agent.is_active:
            try:
                ml_result = {
                    "alert": alert,
                    "type": alert_type,
                    "message": message,
                    "timestamp": alert["timestamp"]
                }
                ai_analysis = ai_agent.process_ml_result(ml_result)
                if ai_analysis["success"]:
                    alert["ai_analysis"] = ai_analysis["analysis"]
                    alert["ai_suggestions"] = ai_analysis["suggestions"]
                    self.log_event(f"AI Analysis: {ai_analysis['analysis']}")
            except Exception as e:
                self.log_event(f"AI processing failed: {str(e)}")
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def log_event(self, message):
        """Log an event to file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        log_file = self.logs_dir / f"monitor_{datetime.now().strftime('%Y%m%d')}.log"
        try:
            with open(log_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error writing to log: {e}")
    
    def update_settings(self, settings):
        """Update monitoring settings"""
        if 'monitoringInterval' in settings:
            self.monitoring_interval = max(1, min(60, settings['monitoringInterval']))
        if 'enableOCR' in settings:
            self.enable_ocr = settings['enableOCR']
        if 'enableML' in settings:
            self.enable_ml = settings['enableML']
        
        self.log_event(f"Settings updated: {settings}")
        return {"success": True, "message": "Settings updated"}

# Global monitor instance
monitor = SecurityMonitor()

def main():
    """Main function for standalone operation"""
    print("AwakenSecurity Monitor Starting...")
    print("Press Ctrl+C to stop")
    
    try:
        # Start monitoring
        result = monitor.start_monitoring()
        print(result["message"])
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop_monitoring()
        print("Monitor stopped.")

if __name__ == "__main__":
    main()
