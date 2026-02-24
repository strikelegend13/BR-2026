# AI Agent Setup Guide

## Quick Setup (2-3 minutes)

### 1. Install Dependencies
```bash
cd python-agent
pip install -r requirements.txt
```

### 2. Configure LLM (Choose One Option)

#### Option A: OpenAI (Recommended for testing)
1. Get an API key from [OpenAI](https://platform.openai.com/api-keys)
2. Create a `.env` file in the `python-agent` directory:
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
```

#### Option B: Local Ollama (Free, requires setup)
1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Run: `ollama pull llama2`
3. Create a `.env` file:
```bash
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
```

### 3. Start the App
```bash
# From the root directory
python start_app.py
```
###  AI Agent Features
- **Smart Security Analysis**: AI interprets your ML results and provides context
- **Natural Language Chat**: Talk to your security assistant
- **Proactive Suggestions**: Get actionable security advice
- **Context Memory**: AI remembers recent activity and patterns

###  Enhanced Monitoring
- Your existing ML now has AI-powered insights
- Alerts include AI analysis and suggestions
- Better understanding of security threats

###  Chat Interface
- Click the 🤖 button in the app header
- Ask questions about security
- Get personalized advice

## Example Conversations

**User**: "What security threats have you detected?"
**AI**: "I've detected 3 potential input fields on your screen, which could be a login form. This is normal for legitimate sites, but be cautious of phishing attempts."

**User**: "How can I stay safe online?"
**AI**: "Based on your recent activity, I recommend: 1) Enable two-factor authentication on your accounts, 2) Use a password manager, 3) Be careful with public WiFi networks."

**User**: "What does that OCR alert mean?"
**AI**: "The OCR detected the word 'password' on your screen. This could be a legitimate login page, but I recommend checking the URL to ensure it's from the expected website."

## Troubleshooting

### AI Not Responding
- Check your `.env` file configuration
- Ensure the LLM provider is running (Ollama) or API key is valid (OpenAI)
- Check the logs in `python-agent/logs/ai_agent_*.log`

### Slow Responses
- OpenAI: Check your internet connection
- Ollama: Ensure you have enough RAM (4GB+ recommended)

### Fallback Mode
If no LLM is configured, the AI will use fallback responses for basic questions.

## Next Steps
Future enhancements will include:
- More sophisticated behavioral analysis
- Automated security actions
- Voice interaction
- Advanced personalization 
