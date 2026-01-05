from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# Import our Logic Modules
from modules.riskon_engine.model import RiskonODE
from modules.allocation_core.agent import AllocationAgent
from modules.sentinel_guard.analyzer import Sentinel

app = FastAPI(title="RecoverAI Core API", version="1.0.0")

# --- INSTANTIATE ENGINES ---
risk_engine = RiskonODE(decay_rate=0.03, boost_factor=0.15)
allocation_agent = AllocationAgent(risk_engine)
sentinel = Sentinel()

# --- DATA MODELS ---
class InteractionLog(BaseModel):
    date_offset: int  # e.g. 5 days ago

class CaseData(BaseModel):
    case_id: str
    company_name: str
    amount: float
    initial_score: float # Credit Score normalized 0-1
    age_days: int
    history_logs: List[int] # Days when interactions occurred

class AuditRequest(BaseModel):
    text: str

# --- ENDPOINTS ---

@app.get("/")
def health_check():
    return {"status": "active", "system": "RecoverAI Agentic Core"}

@app.post("/api/v1/analyze")
def analyze_case(case: CaseData):
    """
    Hyper-Intelligent Endpoint:
    1. Calculates Recovery Probability (ODE)
    2. Decides Allocation Strategy (Agent)
    """
    case_dict = case.dict()
    
    # Run the Allocation Agent (which internally calls Risk Engine)
    decision = allocation_agent.allocate_case(case_dict)
    
    # Also get raw score for UI display
    raw_score = risk_engine.predict_probability(
        case.initial_score, 
        case.age_days, 
        case.history_logs
    )
    
    return {
        "case_id": case.case_id,
        "riskon_score": round(raw_score, 4),
        "allocation_decision": decision
    }

@app.post("/api/v1/sentinel/audit")
def audit_interaction(request: AuditRequest):
    """
    Real-time Compliance Audit
    """
    result = sentinel.scan_interaction(request.text)
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
