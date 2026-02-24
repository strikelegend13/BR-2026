from flask import Flask, jsonify, request
from flask_cors import CORS
from monitor import monitor
from ai_agent import ai_agent
import threading
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for Electron app

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": time.time()})

@app.route('/monitor/start', methods=['POST'])
def start_monitoring():
    """Start the monitoring process"""
    try:
        result = monitor.start_monitoring()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/monitor/stop', methods=['POST'])
def stop_monitoring():
    """Stop the monitoring process"""
    try:
        result = monitor.stop_monitoring()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/monitor/status', methods=['GET'])
def get_status():
    """Get current monitoring status"""
    try:
        status = monitor.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/monitor/settings', methods=['PUT'])
def update_settings():
    """Update monitoring settings"""
    try:
        settings = request.json
        result = monitor.update_settings(settings)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/monitor/alerts', methods=['GET'])
def get_alerts():
    """Get recent alerts"""
    try:
        alerts = monitor.alerts[-20:]  # Last 20 alerts
        return jsonify({"alerts": alerts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# AI Agent endpoints
@app.route('/ai/start', methods=['POST'])
def start_ai_agent():
    """Start the AI agent"""
    try:
        result = ai_agent.start_agent()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/ai/stop', methods=['POST'])
def stop_ai_agent():
    """Stop the AI agent"""
    try:
        result = ai_agent.stop_agent()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/ai/status', methods=['GET'])
def get_ai_status():
    """Get AI agent status"""
    try:
        status = ai_agent.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ai/chat', methods=['POST'])
def chat_with_ai():
    """Chat with the AI agent"""
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({"success": False, "message": "Message is required"}), 400
        
        result = ai_agent.chat_with_user(data['message'])
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

def run_server(host='0.0.0.0', port=5001):
    """Run the Flask server"""
    app.run(host=host, port=port, debug=False, threaded=True)

if __name__ == '__main__':
    print("Starting AwakenSecurity API Server...")
    print("API will be available at http://localhost:5001")
    run_server() 
