import numpy as np
from scipy.integrate import odeint

class RiskonODE:
    def __init__(self, decay_rate=0.05, boost_factor=0.2):
        self.decay_rate = decay_rate  # 'k': How fast hope dies (5% per day)
        self.boost_factor = boost_factor # 'I': Impact of a DCA call

    def recovery_dynamics(self, P, t, interactions):
        """
        The Differential Equation: dP/dt = -kP + Interaction_Effect
        """
        # 1. Natural Decay (The longer it waits, the lower P becomes)
        dP_dt = -self.decay_rate * P
        
        # 2. Interaction Boost (Did we call them today?)
        # t is current time step. We check if an interaction happened at 'int(t)'
        if int(t) in interactions:
            dP_dt += self.boost_factor
            
        return dP_dt

    def predict_probability(self, initial_prob, days_overdue, interaction_days):
        """
        Solves the ODE to predict current Probability of Recovery.
        
        :param initial_prob: Starting score (0.0 to 1.0) based on credit score.
        :param days_overdue: How many days has the invoice been open?
        :param interaction_days: List of days when DCA contacted debtor [3, 10, 15]
        """
        # Time steps (0 to days_overdue)
        t = np.linspace(0, days_overdue, days_overdue + 1)
        
        # Solve ODE
        # We pass 'args' to the function to handle the interactions list
        solution = odeint(
            self.recovery_dynamics, 
            initial_prob, 
            t, 
            args=(interaction_days,)
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
