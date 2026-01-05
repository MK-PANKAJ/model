import json
import os
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    VERTEX_AVAILABLE = True
except ImportError:
    VERTEX_AVAILABLE = False

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class Sentinel:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT") # Auto-set on Cloud Run
        self.model = None
        
        # Initialize Vertex AI if possible
        if VERTEX_AVAILABLE and self.project_id:
            try:
                vertexai.init(project=self.project_id, location="us-central1")
                self.model = GenerativeModel("gemini-pro")
                print("Sentinel: Vertex AI Gemini Pro Initialized.")
            except Exception as e:
                print(f"Sentinel: Vertex AI Init Failed ({e}). Using VADER fallback.")

        # Load banned keywords (Simulated hard-coded list for Phase 1)
        self.banned_words = [
            "jail", "police", "arrest", "warrant", # False legal threats
            "stupid", "idiot", "liar",             # Personal insults
            "immediately or else",                 # Aggressive ultimatums
            "ruin your credit"                     # Specific FDCPA violations
        ]

    def scan_interaction(self, text_content):
        """
        Analyzes an interaction for Compliance Risk.
        Returns: { 'risk_level': str, 'flags': list, 'sentiment': float }
        """
        
        # 1. GENERATIVE AI CHECK (The Brain)
        # If enabled, ask Gemini for a sophisticated legal opinion
        if self.model:
            try:
                prompt = f"""
                Analyze the following debt collection transcript as a Compliance Officer.
                Check for harassment, threats, or FDCPA violations.
                Transcript: "{text_content}"
                
                Respond ONLY with valid JSON:
                {{
                    "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
                    "violation_flags": ["list of specific issues found"],
                    "reasoning": "brief explanation"
                }}
                """
                response = self.model.generate_content(prompt)
                # Clean markdown blocks if Gemini adds them
                raw_json = response.text.replace("```json", "").replace("```", "")
                ai_result = json.loads(raw_json)
                
                # Merge with Sentiment Score (Hybrid Approach)
                ai_result["sentiment_score"] = self.analyzer.polarity_scores(text_content)['compound']
                ai_result["source"] = "Vertex AI (Gemini Pro)"
                return ai_result

            except Exception as e:
                print(f"Sentinel: Vertex AI Analysis Failed ({e}). Falling back to Rules.")

        # 2. FALLBACK RULES (Old VADER/Keyword Logic)
        flags = []
        text_lower = text_content.lower()

        # KEYWORD CHECK (The Hard Guardrail)
        for word in self.banned_words:
            if word in text_lower:
                flags.append(f"VIOLATION_KEYWORD: '{word}'")

        # SENTIMENT CHECK (The Soft Guardrail)
        sentiment_score = self.analyzer.polarity_scores(text_content)['compound']
        
        # RISK CLASSIFICATION
        risk_level = "LOW"
        if len(flags) > 0:
            risk_level = "CRITICAL"
        elif sentiment_score < -0.5:
            risk_level = "HIGH"
        elif sentiment_score < -0.1:
            risk_level = "MEDIUM"
            
        return {
            "risk_level": risk_level,
            "sentiment_score": round(sentiment_score, 2),
            "violation_flags": flags,
            "audit_recommendation": "Human Review" if risk_level in ["HIGH", "CRITICAL"] else "Auto-Approve",
            "source": "Rules Engine (VADER)"
        }

# --- SIMULATION ---
if __name__ == "__main__":
    guard = Sentinel()
    
    # Test Case 1: Normal Interaction
    log_1 = "Hello, I am calling to discuss the invoice overdue by 40 days. Can we set up a plan?"
    print(f"Log 1: {guard.scan_interaction(log_1)}")
    
    # Test Case 2: Aggressive Violation
    log_2 = "Listen you liar, if you don't pay we will send the police to arrest you."
    print(f"Log 2: {guard.scan_interaction(log_2)}")
