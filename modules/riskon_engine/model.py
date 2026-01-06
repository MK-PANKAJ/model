import numpy as np
from scipy.integrate import odeint

class RiskonODE:
    def __init__(self, decay_rate=0.05, boost_factor=0.2):
        self.decay_rate = decay_rate  # 'k': How fast hope dies (5% per day)
        self.boost_factor = boost_factor # 'I': Impact of a DCA call

    def recovery_dynamics(self, P, t, weighted_interactions):
        """
        The Differential Equation: dP/dt = -kP + Weighted_Interaction_Effect
        weighted_interactions: dict of {day: boost_weight}
        """
        # 1. Natural Decay
        dP_dt = -self.decay_rate * P
        
        # 2. Weighted Interaction Boost
        day = int(t)
        if day in weighted_interactions:
            # boost_weight is a multiplier (e.g., 2.0 for PTP, 0.5 for neutral)
            dP_dt += self.boost_factor * weighted_interactions[day]
            
        return dP_dt

    def predict_probability(self, initial_prob, days_overdue, interaction_data):
        """
        Solves the ODE to predict current Probability of Recovery.
        
        :param initial_prob: Starting score (0.0 to 1.0)
        :param days_overdue: How many days has the invoice been open?
        :param interaction_data: List of dicts: {'day': int, 'weight': float}
        """
        # Convert interaction_data to dictionary for fast lookup
        weighted_interactions = {item['day']: item['weight'] for item in interaction_data}

        # Time steps (0 to days_overdue)
        t = np.linspace(0, days_overdue, days_overdue + 1)
        
        # Solve ODE
        solution = odeint(
            self.recovery_dynamics, 
            initial_prob, 
            t, 
            args=(weighted_interactions,)
        )
        
        # Return the final probability (clamped between 0 and 1)
        current_probability = max(0.0, min(1.0, solution[-1][0]))
        return current_probability

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
