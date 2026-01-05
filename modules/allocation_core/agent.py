class AllocationAgent:
    def __init__(self, risk_engine):
        self.risk_engine = risk_engine

    def allocate_case(self, case_data):
        # 1. Ask the Brain for the Score
        p_score = self.risk_engine.predict_probability(
            case_data['initial_score'], 
            case_data['age_days'], 
            case_data['history_logs']
        )

        # 2. Decision Logic (The "Agentic" part)
        if p_score > 0.70:
            # High Probability -> Send to Low-Cost Digital Channel first
            return {
                "action": "ALLOCATE_DIGITAL",
                "channel": "Email_Campaign_A",
                "reason": "High likelihood of self-cure."
            }
        
        elif 0.30 <= p_score <= 0.70:
            # Medium Probability -> Send to Best Performing Human Agency
            return {
                "action": "ALLOCATE_AGENCY",
                "target": "Agency_Alpha (Top Performer)",
                "reason": "Requires human negotiation."
            }
            
        else:
            # Low Probability -> Long-tail strategy / Legal Review
            return {
                "action": "ALLOCATE_LEGAL",
                "target": "Internal_Legal_Review",
                "reason": "Score below threshold for DCA effort."
            }
