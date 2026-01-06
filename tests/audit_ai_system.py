import asyncio
import os
import sys
import json

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.riskon_engine.model import RiskonODE
from modules.sentinel_guard.analyzer import Sentinel
from modules.allocation_core.agent import AllocationAgent

async def audit_ai_system():
    print("="*60)
    print("RECOVERAI - INTELLIGENCE LAYER AUDIT")
    print("="*60)

    # 1. Initialize Engines
    risk_engine = RiskonODE(decay_rate=0.03, boost_factor=0.15)
    sentinel = Sentinel()
    allocation_agent = AllocationAgent(risk_engine)

    # 2. Test Case Definition
    initial_score = 0.50 # Neutral customer
    age_days = 30
    
    print(f"\n[1/3] INITIAL STATE")
    print(f"  - Initial Credit Score: {initial_score*100}%")
    print(f"  - Invoice Age: {age_days} days")

    # 3. Step 1: Baseline Probability
    p0 = risk_engine.predict_probability(initial_score, age_days, [])
    print(f"  - Predicted Recovery Probability (Baseline): {p0:.2%}")
    
    decision0 = allocation_agent.allocate_case({"initial_score": initial_score, "age_days": age_days, "history_logs": []})
    print(f"  - Allocation Decision: {decision0['action']} ({decision0['reason']})")

    # 4. Step 2: Simulate a positive interaction (PTP)
    print(f"\n[2/3] SIMULATING INTERACTION")
    ptp_text = "I promise to pay the full amount by next Friday. Sorry for the delay."
    print(f"  - Debtor says: \"{ptp_text}\"")
    
    compliance_ptp = sentinel.scan_interaction(ptp_text)
    print(f"  - Sentinel Scan Result: {compliance_ptp['risk_level']} Risk")
    print(f"  - Detected Intent: {compliance_ptp['intent']}")
    
    # 5. Step 3: Recalculate Probability with Boost
    # Map the detected intent to a weight
    weight = 1.0 + compliance_ptp.get('sentiment_score', 0.0)
    if compliance_ptp.get('intent') == "PTP":
        weight += 1.0 # Significant boost
    
    p1 = risk_engine.predict_probability(
        initial_score, 
        age_days, 
        [{"day": 15, "weight": weight}]
    )
    
    print(f"\n[3/3] AUDIT RESULTS")
    print(f"  - Before Interaction: {p0:.2%}")
    print(f"  - After PTP Boost: {p1:.2%}")
    
    if p1 > p0:
        print(f"\n[PASS] Intelligence Loop Verified: Probability intelligently adjusted based on intent.")
    else:
        print(f"\n[FAIL] Intelligence Loop Error: Probability did not react to positive interaction.")

    print("="*60)

if __name__ == "__main__":
    asyncio.run(audit_ai_system())
