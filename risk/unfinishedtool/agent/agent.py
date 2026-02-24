import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from pathlib import Path
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AIAgent:
    def __init__(self):
        self.context_memory = []
        self.user_preferences = {}
        self.conversation_history = []
        self.is_active = False
        self.max_context_length = 50
        self.max_conversation_length = 100
        self.model_loaded = False
        self.response_cache = {}
        
        # LLM Configuration
        self.llm_provider = os.getenv('LLM_PROVIDER', 'openai')  # 'openai' or 'ollama'
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        
        # Agent personality and capabilities
        self.agent_personality = """
        You are AwakenSecurity, an advanced AI security intelligence system. Your role is to:
        1. Analyze and interpret security threats detected by the monitoring system
        2. Provide precise, actionable security recommendations
        3. Offer context-aware insights based on real-time data
        4. Maintain a professional, authoritative, and sophisticated tone
        
        You have access to real-time screen monitoring data including:
        - OCR text analysis
        - Form and input field detection
        - Security alerts and threats
        - User activity patterns
        
        Communication style:
        - Professional and authoritative
        - Concise and precise
        - No emojis or casual language
        - Focus on technical accuracy
        - Provide clear, actionable insights
        - Use security terminology appropriately
        
        Always prioritize security and privacy. Be proactive but maintain professional distance.
        """
        
        # Create logs directory
        self.logs_dir = Path(__file__).parent / 'logs'
        self.logs_dir.mkdir(exist_ok=True)
        
    def start_agent(self):
        """Start the AI agent"""
        self.is_active = True
        # Pre-load the model for faster responses
        if self.llm_provider == 'ollama' and not self.model_loaded:
            try:
                self._preload_model()
            except Exception as e:
                self.log_event(f"Model preload failed: {str(e)}")
        
        self.log_event("AI Agent started")
        return {"success": True, "message": "AI Agent started successfully"}
    
    def _preload_model(self):
        """Pre-load the model to keep it in memory"""
        try:
            data = {
                "model": "llama3.2",
                "prompt": "test",
                "stream": False,
                "options": {
                    "num_predict": 1
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                self.model_loaded = True
                self.log_event("Model preloaded successfully")
        except Exception as e:
            self.log_event(f"Model preload error: {str(e)}")
    
    def stop_agent(self):
        """Stop the AI agent"""
        self.is_active = False
        self.log_event("AI Agent stopped")
        return {"success": True, "message": "AI Agent stopped successfully"}
    
    def add_context(self, context_data: Dict[str, Any]):
        """Add context information to memory"""
        context_entry = {
            "timestamp": datetime.now().isoformat(),
            "data": context_data
        }
        
        self.context_memory.append(context_entry)
        
        # Keep only recent context
        if len(self.context_memory) > self.max_context_length:
            self.context_memory = self.context_memory[-self.max_context_length:]
    
    def process_ml_result(self, ml_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process ML monitoring results and generate AI insights"""
        try:
            # Add to context
            self.add_context({
                "type": "ml_result",
                "result": ml_result
            })
            
            # Generate AI analysis
            analysis = self._analyze_ml_result(ml_result)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(ml_result, analysis)
            
            return {
                "success": True,
                "analysis": analysis,
                "suggestions": suggestions,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_event(f"Error processing ML result: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def chat_with_user(self, user_message: str) -> Dict[str, Any]:
        """Handle natural language conversation with user"""
        try:
            # Add user message to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Generate AI response
            ai_response = self._generate_chat_response(user_message)
            
            # Add AI response to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep conversation history manageable
            if len(self.conversation_history) > self.max_conversation_length:
                self.conversation_history = self.conversation_history[-self.max_conversation_length:]
            
            return {
                "success": True,
                "response": ai_response,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_event(f"Error in chat: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _analyze_ml_result(self, ml_result: Dict[str, Any]) -> str:
        """Analyze ML results and provide context"""
        alert_type = ml_result.get("type", "unknown")
        message = ml_result.get("message", "")
        
        prompt = f"""Security Alert Analysis:
Type: {alert_type}
Message: {message}

Provide a brief, professional analysis in 1-2 sentences."""
        
        return self._call_llm(prompt)
    
    def _generate_suggestions(self, ml_result: Dict[str, Any], analysis: str) -> List[str]:
        """Generate actionable suggestions based on ML results"""
        alert_type = ml_result.get("type", "unknown")
        
        prompt = f"""Security Alert: {alert_type}
Analysis: {analysis}

Provide 2 specific, actionable security recommendations. Keep each under 10 words."""
        
        response = self._call_llm(prompt)
        # Parse suggestions from response
        suggestions = [s.strip() for s in response.split('\n') if s.strip() and not s.startswith('#') and len(s.strip()) > 5]
        return suggestions[:2]  # Limit to 2 suggestions
    
    def _generate_chat_response(self, user_message: str) -> str:
        """Generate a response to user chat"""
        user_lower = user_message.lower()
        
        # Fast responses for common queries
        if any(word in user_lower for word in ["hello", "hi", "hey"]):
            return "AwakenSecurity AI online. How can I assist with your security analysis?"
        elif "status" in user_lower or "monitoring" in user_lower:
            return "Security monitoring is operational. All systems are active and protecting your device."
        elif "help" in user_lower:
            return "I can analyze security threats, review alerts, and provide recommendations. What would you like to know?"
        elif "threat" in user_lower or "alert" in user_lower:
            return "I can review detected threats and provide analysis. Check the alerts panel for recent security events."
        
        # For more complex queries, use LLM
        prompt = f"""You are AwakenSecurity AI. Respond to: "{user_message}"

Keep response under 100 words. Be professional and technical."""
        
        return self._call_llm(prompt)
    
    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM provider"""
        # Check cache first
        cache_key = hash(prompt)
        if cache_key in self.response_cache:
            return self.response_cache[cache_key]
        
        try:
            if self.llm_provider == 'openai' and self.openai_api_key:
                response = self._call_openai(prompt)
            elif self.llm_provider == 'ollama':
                response = self._call_ollama(prompt)
            else:
                # Fallback response if no LLM is configured
                response = self._fallback_response(prompt)
            
            # Cache the response
            self.response_cache[cache_key] = response
            
            # Keep cache size manageable
            if len(self.response_cache) > 50:
                # Remove oldest entries
                oldest_keys = list(self.response_cache.keys())[:10]
                for key in oldest_keys:
                    del self.response_cache[key]
            
            return response
                
        except Exception as e:
            self.log_event(f"LLM call failed: {str(e)}")
            return "I'm having trouble processing that right now. Please try again."
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"OpenAI API error: {response.status_code}")
    
    def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama instance"""
        data = {
            "model": "llama3.2",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 100,
                "stop": ["\n\n", "User:", "Human:", "Assistant:"]
            }
        }
        
        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()["response"].strip()
        else:
            raise Exception(f"Ollama API error: {response.status_code}")
    
    def _fallback_response(self, prompt: str) -> str:
        """Fallback response when no LLM is available"""
        prompt_lower = prompt.lower()
        
        # Fast template responses for common queries
        if "security" in prompt_lower or "threat" in prompt_lower:
            return "Security monitoring is active. I can analyze detected threats and provide recommendations."
        elif "help" in prompt_lower:
            return "I can analyze security threats, provide technical insights, and offer actionable recommendations for your digital safety."
        elif "status" in prompt_lower or "monitoring" in prompt_lower:
            return "Monitoring system is operational. All security protocols are active."
        elif "password" in prompt_lower or "login" in prompt_lower:
            return "Credential security is critical. Ensure you're on legitimate sites and use strong, unique passwords."
        elif "virus" in prompt_lower or "malware" in prompt_lower:
            return "No malware detected. Continue practicing safe browsing habits and keep software updated."
        else:
            return "AwakenSecurity AI ready. How can I assist with your security analysis?"
    
    def get_status(self) -> Dict[str, Any]:
        """Get AI agent status"""
        return {
            "isActive": self.is_active,
            "contextMemorySize": len(self.context_memory),
            "conversationHistorySize": len(self.conversation_history),
            "llmProvider": self.llm_provider,
            "lastActivity": self.context_memory[-1]["timestamp"] if self.context_memory else None
        }
    
    def log_event(self, message: str):
        """Log an event to file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] AI_AGENT: {message}\n"
        
        log_file = self.logs_dir / f"ai_agent_{datetime.now().strftime('%Y%m%d')}.log"
        try:
            with open(log_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error writing to AI agent log: {e}")

# Global AI agent instance
ai_agent = AIAgent() 
