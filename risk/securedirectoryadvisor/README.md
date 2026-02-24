# Basic file advisor with optional API integration

Designed specifically for **elderly and non-technical users**, this tool helps people stay safe online by checking files and websites *before* they open them — in plain, friendly English.
- Automatic Download Monitoring
- Ask a Trusted Contact
- Friendly Plain-English 
- Optional API Integration
- Scan History
- Settings Panel 

---

## 🚀 Getting Started

### Requirements

- Python 3.10 or later
- No additional packages needed — uses only Python's built-in libraries (`tkinter`, `os`, `hashlib`, `smtplib`, etc.)

### Running the App

```bash
# Navigate to the folder
cd secure_file_advisor

# Run
python3 main.py
```

On **Windows**, you can double-click `main.py` if Python is associated with `.py` files.

how to use:
check file, website or image, you can also add positions 

Now whenever a risky file or site is found, you'll see a **"Ask [Name] for Help"** button that opens your email app with a pre-written message.

### Automatic Monitoring
As soon as the app is running, it silently watches your Downloads folder. When any new file appears, it pops up a friendly notification asking if you'd like it checked.

---

## 🔑 Optional: Extra Protection with API Keys

For even stronger checking, you can add free API keys from:

- **VirusTotal** (https://www.virustotal.com) — checks files against 70+ antivirus engines
- **Google Safe Browsing** (https://developers.google.com/safe-browsing) — checks URLs against Google's database of dangerous sites

Both have free tiers sufficient for personal use. Add them in the Settings panel.

---

structure:

secure_file_advisor/
├── main.py              # Entry point — starts the app and the download monitor
├── modules/
│   ├── analyzer.py      # File and URL risk analysis logic
│   ├── config.py        # Persistent settings (saved to ~/.secure_file_advisor_config.json)
│   ├── contact.py       # Trusted contact messaging (email / SMS gateway)
│   ├── monitor.py       # Background download folder watcher
│   └── ui.py            # Full tkinter GUI
└── README.md

privacy:

- This tool runs entirely on your computer
- No files or personal data are ever uploaded without your knowledge
- VirusTotal and Google Safe Browsing checks only send a file *hash* (a fingerprint, not the file itself) or the URL — no personal information

This tool uses heuristics and optional third-party APIs. It is not a replacement for antivirus software. Always keep your operating system and antivirus up to date.

