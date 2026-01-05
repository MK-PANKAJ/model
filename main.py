from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# Import our Logic Modules
from modules.riskon_engine.model import RiskonODE
from modules.allocation_core.agent import AllocationAgent
from modules.sentinel_guard.analyzer import Sentinel

# Import Database Modules
from modules.database import Base, engine, get_db, InvoiceDB, DebtorDB
from sqlalchemy.orm import Session
from fastapi import Depends

# Create the Database Tables (recoverai.db)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="RecoverAI Core API", version="1.0.0")

# --- CORS MIDDLEWARE (Required for Cloud/Frontend Integration) ---
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for MVP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
def analyze_case(case: CaseData, db: Session = Depends(get_db)):
    """
    Hyper-Intelligent Endpoint:
    1. Calculates Recovery Probability (ODE)
    2. Decides Allocation Strategy (Agent)
    3. SAVES result to Database
    """
    case_dict = case.dict()
    
    # Run the Allocation Agent
    decision = allocation_agent.allocate_case(case_dict)
    
    # Also get raw score for UI display
    raw_score = risk_engine.predict_probability(
        case.initial_score, 
        case.age_days, 
        case.history_logs
    )

    # --- SAVE TO DB (PERSISTENCE) ---
    # 1. Check if debtor exists, else create
    debtor = db.query(DebtorDB).filter(DebtorDB.name == case.company_name).first()
    if not debtor:
        debtor = DebtorDB(name=case.company_name, credit_score=case.initial_score)
        db.add(debtor)
        db.commit()
        db.refresh(debtor)

    # 2. Save the Analysis Record
    db_invoice = InvoiceDB(
        debtor_id=debtor.id,
        amount=case.amount,
        age_days=case.age_days,
        p_score=raw_score,
        decision=decision["action"]
    )
    db.add(db_invoice)
    db.commit()
    
    return {
        "case_id": case.case_id,
        "riskon_score": round(raw_score, 4),
        "allocation_decision": decision,
        "db_status": "SAVED"
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
