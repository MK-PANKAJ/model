from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
from datetime import datetime
import json

# Import our Logic Modules
from modules.riskon_engine.model import RiskonODE
from modules.allocation_core.agent import AllocationAgent
from modules.sentinel_guard.analyzer import Sentinel

# Import Database Modules
from modules.database import Base, engine, get_db, InvoiceDB, DebtorDB, UserDB, SessionLocal, InteractionLogDB, StatusHistoryDB
from sqlalchemy.orm import Session
from fastapi import Depends, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from modules.security import verify_password, create_access_token, verify_token, get_password_hash
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

    # --- SENTINEL COMPLIANCE CHECK ---
    # Simulate a transcript for compliance scanning
    # In production, this would be real interaction text
    simulated_transcript = f"Regarding outstanding debt of {case.amount} from {case.company_name}"
    compliance_result = sentinel.scan_interaction(simulated_transcript)
    risk_level = compliance_result.get("risk_level", "UNKNOWN")

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
        decision=decision["action"],
        risk_level=risk_level
    )
    db.add(db_invoice)
    db.commit()
    
    return {
        "case_id": case.case_id,
        "riskon_score": round(raw_score, 4),
        "allocation_decision": decision,
        "compliance": {"risk_level": risk_level},
        "db_status": "SAVED"
    }

@app.post("/api/v1/sentinel/audit")
def audit_interaction(request: AuditRequest, current_user: str = Depends(verify_token)):
    """
    Real-time Compliance Audit
    """
    result = sentinel.scan_interaction(request.text)
    return result

class InteractionRequest(BaseModel):
    text: str

@app.post("/api/v1/cases/{case_id}/log_interaction")
def log_interaction(
    case_id: str,
    interaction: InteractionRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """
    Log a debtor interaction and perform real-time Sentinel compliance check.
    Returns compliance result immediately.
    """
    try:
        # Extract numeric ID from case_id like "C-123"
        invoice_id = int(case_id.replace("C-", ""))
        invoice = db.query(InvoiceDB).filter(InvoiceDB.id == invoice_id).first()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Run Sentinel compliance check on the interaction text
        compliance_result = sentinel.scan_interaction(interaction.text)
        
        # Create interaction log
        log_entry = InteractionLogDB(
            invoice_id=invoice_id,
            created_at=datetime.utcnow().isoformat(),
            interaction_text=interaction.text,
            risk_level=compliance_result.get("risk_level", "UNKNOWN"),
            sentiment_score=compliance_result.get("sentiment_score", 0.0),
            violation_flags=json.dumps(compliance_result.get("violation_flags", []))
        )
        db.add(log_entry)
        db.flush() # Ensure log has an ID and is visible for subsequent queries
        
        # --- AGENTIC AUTO-UPDATES ---
        
        # 1. ANALYZE INTENT & RECALCULATE SCORE
        # Fetch debtor for initial credit score
        debtor = db.query(DebtorDB).filter(DebtorDB.id == invoice.debtor_id).first()
        
        # Calculate interaction weights for ODE
        # We'll map logs to days relative to invoice age
        all_logs = db.query(InteractionLogDB).filter(InteractionLogDB.invoice_id == invoice_id).all()
        interaction_data = []
        for log in all_logs:
            # For simulation, we'll assign random distinct days if multiples occur same day
            # In a real system, we'd use timestamps. Here we'll use log sequence as 'days' proxy
            # or just assume they happen at regular intervals within the age_days.
            # Simpler: use log.id % age_days as a stable pseudo-day
            day = (log.id * 7) % (invoice.age_days + 1) 
            
            # Determine weight: Sentiment (-1 to 1) + Intent Bonus
            weight = 1.0 + log.sentiment_score
            if compliance_result.get("intent") == "PTP": weight += 1.0
            if log.risk_level == "CRITICAL": weight -= 2.0
            
            interaction_data.append({"day": day, "weight": max(0.0, weight)})

        # Recalculate p_score
        new_p_score = risk_engine.predict_probability(
            initial_prob=debtor.credit_score,
            days_overdue=invoice.age_days,
            interaction_data=interaction_data
        )
        invoice.p_score = new_p_score

        # 2. AUTOMATED STATUS TRANSITIONS
        timestamp = datetime.utcnow().isoformat()
        
        # Auto-update status to IN_PROGRESS on first interaction (if PENDING)
        if invoice.status == "PENDING":
            old_status = invoice.status
            invoice.status = "IN_PROGRESS"
            
            status_history = StatusHistoryDB(
                invoice_id=invoice_id,
                old_status=old_status,
                new_status="IN_PROGRESS",
                changed_by="SYSTEM",
                changed_at=timestamp,
                reason="First interaction logged",
                auto_updated=1
            )
            db.add(status_history)
        
        # Auto-update status to UNDER_REVIEW if PTP (Promise to Pay) Detected
        if compliance_result.get("intent") == "PTP" and invoice.status == "IN_PROGRESS":
            old_status = invoice.status
            invoice.status = "UNDER_REVIEW"
            
            ptp_history = StatusHistoryDB(
                invoice_id=invoice_id,
                old_status=old_status,
                new_status="UNDER_REVIEW",
                changed_by="SYSTEM",
                changed_at=timestamp,
                reason="Promise to Pay detected by AI Sentinel",
                auto_updated=1
            )
            db.add(ptp_history)

        # If critical risk, update invoice risk_level and escalate
        if compliance_result.get("risk_level") == "CRITICAL":
            invoice.risk_level = "CRITICAL"
            # Auto-escalate
            if invoice.status in ["IN_PROGRESS", "UNDER_REVIEW"]:
                old_status = invoice.status
                invoice.status = "ESCALATED"
                
                escalate_history = StatusHistoryDB(
                    invoice_id=invoice_id,
                    old_status=old_status,
                    new_status="ESCALATED",
                    changed_by="SYSTEM",
                    changed_at=timestamp,
                    reason="Critical compliance violation detected",
                    auto_updated=1
                )
                db.add(escalate_history)
        
        db.commit()
        db.refresh(log_entry)
        
        return {
            "status": "success",
            "log_id": log_entry.id,
            "compliance": compliance_result,
            "new_p_score": round(invoice.p_score, 4),
            "new_invoice_status": invoice.status,
            "message": "Interaction logged and analyzed. Case probability & status updated."
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case_id format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/cases/{case_id}/analyze_audio")
async def analyze_audio_interaction(
    case_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """
    Multimodal: Receive audio recording -> Gemini STT + Compliance -> Log to DB
    """
    try:
        content = await file.read()
        analysis = await sentinel.analyze_audio(content, file.content_type)
        
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=analysis["error"])
            
        # Log the result just like a manual text log
        invoice_id = int(case_id.replace("C-", ""))
        invoice = db.query(InvoiceDB).filter(InvoiceDB.id == invoice_id).first()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Case not found")
            
        # Create log entry from transcript
        log_entry = InteractionLogDB(
            invoice_id=invoice_id,
            created_at=datetime.utcnow().isoformat(),
            interaction_text=f"[VOICE RECORDING] {analysis.get('transcript', '')}",
            risk_level=analysis.get("risk_level", "UNKNOWN"),
            sentiment_score=0.0, # STT might not give sentiment directly yet
            violation_flags=json.dumps(analysis.get("violation_flags", []))
        )
        db.add(log_entry)
        db.flush()

        # Recalculate score (Shared Logic)
        debtor = db.query(DebtorDB).filter(DebtorDB.id == invoice.debtor_id).first()
        all_logs = db.query(InteractionLogDB).filter(InteractionLogDB.invoice_id == invoice_id).all()
        interaction_data = []
        for log in all_logs:
            day = (log.id * 7) % (invoice.age_days + 1) 
            weight = 1.0 # Default
            if analysis.get("intent") == "PTP": weight += 1.0
            interaction_data.append({"day": day, "weight": max(0.0, weight)})

        invoice.p_score = risk_engine.predict_probability(
            initial_prob=debtor.credit_score,
            days_overdue=invoice.age_days,
            interaction_data=interaction_data
        )

        # Status Update
        if invoice.status == "PENDING":
            invoice.status = "IN_PROGRESS"
        if analysis.get("intent") == "PTP" and invoice.status == "IN_PROGRESS":
            invoice.status = "UNDER_REVIEW"
        
        db.commit()
        
        return {
            "status": "success",
            "analysis": analysis,
            "new_p_score": round(invoice.p_score, 4),
            "new_invoice_status": invoice.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class StatusUpdateRequest(BaseModel):
    new_status: str  # PENDING, IN_PROGRESS, UNDER_REVIEW, RESOLVED, CLOSED, ESCALATED
    reason: Optional[str] = None

@app.patch("/api/v1/cases/{case_id}/status")
def update_case_status(
    case_id: str,
    update: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """
    Update case status manually with validation and history tracking.
    """
    # Valid status transitions
    VALID_TRANSITIONS = {
        "PENDING": ["IN_PROGRESS", "CLOSED"],
        "IN_PROGRESS": ["UNDER_REVIEW", "RESOLVED", "CLOSED", "ESCALATED"],
        "UNDER_REVIEW": ["IN_PROGRESS", "RESOLVED", "ESCALATED"],
        "RESOLVED": ["CLOSED"],
        "ESCALATED": ["UNDER_REVIEW", "CLOSED"],
        "CLOSED": []  # Final state
    }
    
    try:
        # Extract numeric ID from case_id like "C-123"
        invoice_id = int(case_id.replace("C-", ""))
        invoice = db.query(InvoiceDB).filter(InvoiceDB.id == invoice_id).first()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Case not found")
        
        old_status = invoice.status
        new_status = update.new_status.upper()
        
        # Validate transition
        if old_status not in VALID_TRANSITIONS:
            raise HTTPException(status_code=400, detail=f"Invalid current status: {old_status}")
        
        if new_status not in VALID_TRANSITIONS[old_status]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition: {old_status} → {new_status}"
            )
        
        # Update invoice status
        invoice.status = new_status
        
        # Set timestamps based on new status
        timestamp = datetime.utcnow().isoformat()
        if new_status == "RESOLVED" and not invoice.resolved_at:
            invoice.resolved_at = timestamp
        elif new_status == "CLOSED":
            if not invoice.closed_at:
                invoice.closed_at = timestamp
            if update.reason:
                invoice.closed_reason = update.reason
        
        # Create status history entry
        history = StatusHistoryDB(
            invoice_id=invoice_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=current_user,
            changed_at=timestamp,
            reason=update.reason,
            auto_updated=0  # Manual update
        )
        db.add(history)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Status updated from {old_status} to {new_status}",
            "case_id": case_id,
            "new_status": new_status,
            "resolved_at": invoice.resolved_at,
            "closed_at": invoice.closed_at
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case_id format")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

class ManualCaseRequest(BaseModel):
    company_name: str
    amount: float
    credit_score: float
    phone: Optional[str] = None

@app.post("/api/v1/cases/create")
def create_manual_case(case: ManualCaseRequest, db: Session = Depends(get_db), current_user: str = Depends(verify_token)):
    """
    Manually add a single debt case via UI.
    """
    try:
        # Create or get debtor
        debtor = db.query(DebtorDB).filter(DebtorDB.name == case.company_name).first()
        if not debtor:
            debtor = DebtorDB(name=case.company_name, credit_score=case.credit_score, phone=case.phone, is_sample=0)
            db.add(debtor)
            db.commit()
            db.refresh(debtor)
        
        # Create invoice
        invoice = InvoiceDB(
            debtor_id=debtor.id,
            amount=case.amount,
            age_days=case.age_days,
            p_score=0.0,
            decision="PENDING",
            risk_level="UNKNOWN",
            status="PENDING"
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        return {
            "status": "success",
            "case_id": f"C-{invoice.id}",
            "message": f"Case created for {case.company_name}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/cases")
def get_pending_cases(db: Session = Depends(get_db), current_user: str = Depends(verify_token)):
    """
    Fetch all pending invoices from the database.
    """
    results = []
    # Join Invoice with Debtor to get company name
    invoices = db.query(InvoiceDB, DebtorDB).join(DebtorDB, InvoiceDB.debtor_id == DebtorDB.id).filter(InvoiceDB.status == "PENDING").all()
    
    for inv, debtor in invoices:
        # Fetch interaction logs for this invoice
        logs = db.query(InteractionLogDB).filter(
            InteractionLogDB.invoice_id == inv.id
        ).order_by(InteractionLogDB.created_at.desc()).all()
        
        results.append({
            "case_id": f"C-{inv.id}", # Simple ID generation
            "companyName": debtor.name,
            "phone": debtor.phone,
            "amount": inv.amount,
            "initial_score": debtor.credit_score,
            "age_days": inv.age_days,
            "history": [
                {
                    "id": log.id,
                    "date": log.created_at,
                    "text": log.interaction_text,
                    "riskLevel": log.risk_level,
                    "sentimentScore": log.sentiment_score,
                    "violationFlags": json.loads(log.violation_flags) if log.violation_flags else []
                }
                for log in logs
            ],
            "pScore": inv.p_score,
            "suggestedAction": inv.decision,
            "status": inv.status,
            "riskLevel": inv.risk_level if inv.risk_level else "UNKNOWN"
        })
    return results

@app.get("/api/v1/payment/success")
def payment_success_callback(case_id: str, db: Session = Depends(get_db)):
    """
    Stripe redirects here after successful payment.
    Updates invoice status to RESOLVED.
    """
    try:
        # Extract numeric ID from case_id like "C-123"
        invoice_id = int(case_id.replace("C-", ""))
        invoice = db.query(InvoiceDB).filter(InvoiceDB.id == invoice_id).first()
        
        if invoice:
            old_status = invoice.status
            invoice.status = "RESOLVED"
            timestamp = datetime.utcnow().isoformat()
            invoice.resolved_at = timestamp
            
            # Create status history
            history = StatusHistoryDB(
                invoice_id=invoice_id,
                old_status=old_status,
                new_status="RESOLVED",
                changed_by="SYSTEM",
                changed_at=timestamp,
       reason="Payment received via Stripe",
                auto_updated=1
            )
            db.add(history)
            db.commit()
            
            # Redirect to frontend with success banner
            domain = os.getenv("DOMAIN_URL", "https://MK-PANKAJ.github.io/model")
            return {"status": "success", "redirect": f"{domain}?payment=success&case_id={case_id}"}
        else:
            raise HTTPException(status_code=404, detail="Invoice not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case_id format")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
