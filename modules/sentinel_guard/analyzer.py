import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class Sentinel:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
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
        flags = []
        text_lower = text_content.lower()

        # 1. KEYWORD CHECK (The Hard Guardrail)
        for word in self.banned_words:
            if word in text_lower:
                flags.append(f"VIOLATION_KEYWORD: '{word}'")

        # 2. SENTIMENT CHECK (The Soft Guardrail)
        # Compound score: -1 (Most Negative) to +1 (Most Positive)
        sentiment_score = self.analyzer.polarity_scores(text_content)['compound']
        
        # 3. RISK CLASSIFICATION
        risk_level = "LOW"
        
        if len(flags) > 0:
            risk_level = "CRITICAL" # Auto-Fail: Contains banned words
        elif sentiment_score < -0.5:
            risk_level = "HIGH"     # Warning: Hostile tone detected
        elif sentiment_score < -0.1:
            risk_level = "MEDIUM"   # Caution: Negative tone
            
        return {
            "risk_level": risk_level,
            "sentiment_score": round(sentiment_score, 2),
            "violation_flags": flags,
            "audit_recommendation": "Human Review" if risk_level in ["HIGH", "CRITICAL"] else "Auto-Approve"
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
