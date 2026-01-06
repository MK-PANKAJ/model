import numpy as np
from scipy.integrate import odeint

class RiskonODE:
    def __init__(self, decay_rate=0.05, boost_factor=0.2):
        self.decay_rate = decay_rate  # 'k': How fast hope dies (5% per day)
        self.boost_factor = boost_factor # 'I': Impact of a DCA call

    def predict_probability(self, initial_prob, days_overdue, interaction_data):
        """
        Predicts Probability using a robust time-step integration.
        We use a step-based approach to ensure DCA boosts are accurately captured.
        """
        # 1. Setup
        dt = 0.1 # 0.1 day resolution
        P = float(initial_prob)
        total_days = int(days_overdue)
        steps = int(total_days / dt)
        
        # 2. Daily Boost Dictionary
        boosts = {int(item['day']): float(item['weight']) for item in interaction_data}
        
        # 3. Integration Loop
        applied_days = set() # Ensure boost applies once per day
        
        for i in range(steps):
            t = i * dt
            day = int(t)
            
            # A. Continuous Decay
            dP = -self.decay_rate * P * dt
            
            # B. Discrete Boost (Agentic Nudge)
            if day in boosts and day not in applied_days:
                # The boost is an impulse added to the probability
                P += self.boost_factor * boosts[day]
                applied_days.add(day)
            
            P += dP
            
            # Clamp during integration to prevent overflow/negative
            P = max(0.0, min(P, 1.0))
            
        return round(float(P), 4)

# --- SIMULATION ---
if __name__ == "__main__":
    # Example: Invoice is 30 days old. We called on Day 5 and Day 20.
    engine = RiskonODE(decay_rate=0.03, boost_factor=0.15)
    
    current_score = engine.predict_probability(
        initial_prob=0.8,       # Good customer initially
        days_overdue=30,        # 30 days late
        interaction_days=[5, 20] # We nudged them twice
    )
    
    print(f"Current Recovery Probability: {current_score:.2%}")
    # Output might be ~65% (Decayed from 80%, but boosted by calls)
