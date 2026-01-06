from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# Import our Logic Modules
from modules.riskon_engine.model import RiskonODE
from modules.allocation_core.agent import AllocationAgent
from modules.sentinel_guard.analyzer import Sentinel

# Import Database Modules
from modules.database import Base, engine, get_db, InvoiceDB, DebtorDB, UserDB
from sqlalchemy.orm import Session
from fastapi import Depends, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from modules.security import verify_password, create_access_token, verify_token
from modules.security import verify_password, create_access_token, verify_token
from modules.ingestion import process_csv_upload
from modules.payments import create_payment_link

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

# --- STARTUP: AUTO-CREATE ADMIN (MVP ONLY) ---
from modules.security import get_password_hash
@app.on_event("startup")
def create_default_admin():
    print("--- STARTUP: Initializing Admin User ---")
    try:
        db = SessionLocal()
        try:
            user = db.query(UserDB).filter(UserDB.username == "admin").first()
            if not user:
                print("Creating default admin user...")
                hashed_pw = get_password_hash("password123")
                admin = UserDB(username="admin", hashed_password=hashed_pw)
                db.add(admin)
                db.commit()
                print("Admin user created successfully.")
            else:
                # FORCE RESET PASSWORD (Self-Healing for MVP)
                print("Admin exists. Resetting password to ensure compatibility...")
                hashed_pw = get_password_hash("password123")
                user.hashed_password = hashed_pw
                db.commit()
                print("Admin password reset successfully.")
        except Exception as e:
            print(f"Startup DB Error: {e}")
            # Do NOT raise, just log it so the app can still start
        finally:
            db.close()
    except Exception as outer_e:
        print(f"Startup Critical Error: {outer_e}")
    print("--- STARTUP: Complete ---")

# --- DATA MODELS ---
# --- AUTH ENDPOINT ---
@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

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

@app.post("/api/v1/ingest")
async def ingest_csv(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: str = Depends(verify_token)):
    """
    Upload FedEx CSV Export -> Cloud SQL
    """
    content = await file.read()
    results = process_csv_upload(content, db)
    return results

class PaymentRequest(BaseModel):
    case_id: str
    amount: float

@app.post("/api/v1/payment/create")
def generate_payment_link(request: PaymentRequest, current_user: str = Depends(verify_token)):
    return create_payment_link(request.case_id, request.amount)

@app.post("/api/v1/analyze")
def analyze_case(case: CaseData, db: Session = Depends(get_db), current_user: str = Depends(verify_token)):
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
def audit_interaction(request: AuditRequest, current_user: str = Depends(verify_token)):
    """
    Real-time Compliance Audit
    """
    result = sentinel.scan_interaction(request.text)
    return result

@app.get("/api/v1/cases")
def get_pending_cases(db: Session = Depends(get_db), current_user: str = Depends(verify_token)):
    """
    Fetch all pending invoices from the database.
    """
    results = []
    # Join Invoice with Debtor to get company name
    invoices = db.query(InvoiceDB, DebtorDB).join(DebtorDB, InvoiceDB.debtor_id == DebtorDB.id).filter(InvoiceDB.status == "PENDING").all()
    
    for inv, debtor in invoices:
        results.append({
            "case_id": f"C-{inv.id}", # Simple ID generation
            "companyName": debtor.name,
            "amount": inv.amount,
            "initial_score": debtor.credit_score,
            "age_days": inv.age_days,
            "history": [], # Placeholder until InteractionLog table is linked
            "pScore": inv.p_score,
            "suggestedAction": inv.decision,
            "status": inv.status
        })
    return results

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
