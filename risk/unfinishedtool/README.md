# AwakenSecurity
For non-profit security tools

A cross-platform security monitoring app with Electron, Python, and FastAPI components.


# Heavily unfinished, ml analysis and ocr detection are necessary to implement 

## Quick Start

```bash
# Install dependencies first
cd python-agent && pip install -r requirements.txt
cd ../electron-app && npm install

# Start both services with one command
python start_app.py
```
Manual Startup

#### 1. Install Python Dependencies
```bash
cd python-agent
pip install -r requirements.txt
```

#### 2. Install Node.js Dependencies
```bash
cd electron-app
npm install
```

#### 3. Start Python Monitoring API
```bash
cd python-agent
python api_server.py
```

#### 4. Start Electron App (in new terminal)
```bash
cd electron-app
npm run dev
```

## How It Works

### Architecture
- **Electron App**: Modern React-based UI for user interaction and status display
- **Python Agent**: Screen monitoring, OCR, and ML analysis engine
- **API Server**: Flask-based communication layer between Electron and Python
- **Monitoring Engine**: Real-time screen capture and threat detection

### Security Features
- **OCR Detection**: Scans for sensitive keywords like "password", "credit card", "SSN"
- **Form Detection**: Identifies potential input fields using computer vision
- **Configurable Alerts**: Customizable monitoring intervals and detection settings
- **Local Processing**: All analysis happens on your device, no data sent to cloud

### Monitoring Capabilities
- Screen capture every 1-60 seconds (configurable)
- Text extraction and keyword analysis
- Edge detection for form identification
- Real-time alert generation
- Comprehensive logging system

## Development

### Project Structure
```
AwakenSecurity/
├── electron-app/          # Desktop UI (React + Electron)
│   ├── src/              # React components
│   ├── main.js           # Electron main process
│   └── preload.js        # IPC bridge
├── python-agent/         # Monitoring engine
│   ├── monitor.py        # Core monitoring logic
│   ├── api_server.py     # Flask API server
│   └── logs/             # Monitoring logs
├── backend/              # Future FastAPI backend
└── start_app.py          # Automated startup script
```

### API Endpoints
- `GET /health` - Health check
- `POST /monitor/start` - Start monitoring
- `POST /monitor/stop` - Stop monitoring
- `GET /monitor/status` - Get monitoring status
- `PUT /monitor/settings` - Update settings
- `GET /monitor/alerts` - Get recent alerts

## Configuration

### Monitoring Settings
- **Interval**: 1-60 seconds between captures
- **OCR Detection**: Enable/disable text analysis
- **ML Analysis**: Enable/disable computer vision features

### Suspicious Keywords
The system monitors for these sensitive terms:
- Passwords and login information
- Credit card and financial data
- Social security numbers
- Personal identification data
- Contact information

## Security Notes
- **Local-First**: All monitoring and ML run on the user's device
- **No Cloud Storage**: Logs and sensitive data are never stored remotely
- **Privacy-Focused**: Only minimal metadata for buddy/accountability features
- **Configurable**: Users control what gets monitored and when

## Troubleshooting

### Common Issues
1. **Python API not starting**: Check if port 5000 is available
2. **Electron app not loading**: Ensure Node.js and npm are installed
3. **OCR not working**: Install Tesseract OCR on your system
4. **Screen capture fails**: Check display permissions on macOS

### Dependencies
- Python 3.7+
- Node.js 16+
- Tesseract OCR
- OpenCV
- Electron

## License
This project is licensed under the MIT License - see the LICENSE file for details.

---
**Note**: This is a security monitoring tool. Use responsibly and in accordance with applicable laws and regulations.
