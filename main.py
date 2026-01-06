import json
import requests
import asyncio
import uvicorn
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse
from fastapi import FastAPI, HTTPException, Request, Form, Response, Depends, status, File, UploadFile
from pydantic import BaseModel
import os
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
load_dotenv() # Load variables from .env if present

# Import our Logic Modules
from modules.riskon_engine.model import RiskonODE
from modules.allocation_core.agent import AllocationAgent
from modules.sentinel_guard.analyzer import Sentinel

# Import Database Modules
from modules.database import Base, engine, get_db, InvoiceDB, DebtorDB, UserDB, SessionLocal, InteractionLogDB, StatusHistoryDB
from sqlalchemy.orm import Session
# from fastapi import Depends, status, File, UploadFile  # Moved to line 7
from fastapi.security import OAuth2PasswordRequestForm
from modules.security import verify_password, create_access_token, verify_token, get_password_hash
from modules.ingestion import process_csv_upload
from modules.payments import create_payment_link
from add_sample_data import add_sample_data

# Create the Database Tables (recoverai.db)
# Base.metadata.create_all(bind=engine) # Moved to startup event for Cloud Build stability

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
def startup_event():
    print("--- STARTUP: Ensuring Database Tables ---")
    Base.metadata.create_all(bind=engine)
    
    print("--- STARTUP: Initializing Admin User ---")
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
            print("Admin exists. Resetting password...")
            user.hashed_password = get_password_hash("password123")
            db.commit()

        # --- INITIALIZE SAMPLE DATA ---
        add_sample_data()

    except Exception as e:
        print(f"Startup Error: {e}")
    finally:
        db.close()
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

    # --- SENTINEL COMPLIANCE CHECK (REMOVED FROM INITIAL ANALYSIS) ---
    # We only run compliance when an actual interaction log is created.
    # Initially we assume SAFE unless imported differently.
    risk_level = invoice_risk_level = "SAFE"

    # --- SAVE TO DB (PERSISTENCE) ---
    # 1. Check if debtor exists, else create
    debtor = db.query(DebtorDB).filter(DebtorDB.name == case.company_name).first()
    if not debtor:
        debtor = DebtorDB(name=case.company_name, credit_score=case.initial_score)
        db.add(debtor)
        db.commit()
        db.refresh(debtor)

    # 2. UPDATE EXISTING INVOICE INSTEAD OF CREATING NEW
    existing_invoice = None
    try:
        # Check if case_id is numeric (from database) or a string like "C-123"
        inv_id_str = str(case.case_id).replace("C-", "")
        if inv_id_str.isdigit():
            inv_id = int(inv_id_str)
            existing_invoice = db.query(InvoiceDB).filter(InvoiceDB.id == inv_id).first()
    except Exception:
        pass

    if existing_invoice:
        # Update Existing
        existing_invoice.p_score = raw_score
        existing_invoice.decision = decision["action"]
        existing_invoice.risk_level = risk_level
        existing_invoice.status = "IN_PROGRESS" # Mark as analyzed
        db.commit()
        db_invoice = existing_invoice
    else:
        # Create New (Fallback for manual entries not yet in DB)
        db_invoice = InvoiceDB(
            debtor_id=debtor.id,
            amount=case.amount,
            age_days=case.age_days,
            p_score=raw_score,
            decision=decision["action"],
            risk_level=risk_level,
            status="IN_PROGRESS"
        )
        db.add(db_invoice)
        db.commit()
        db.refresh(db_invoice)
    
    return {
        "case_id": f"C-{db_invoice.id}",
        "riskon_score": round(raw_score, 4),
        "allocation_decision": decision,
        "compliance": {"risk_level": risk_level},
        "db_status": "UPDATED" if existing_invoice else "SAVED"
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
            intent=compliance_result.get("intent", "GENERAL"),
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
            if log.intent == "PTP": weight += 1.0
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
            intent=analysis.get("intent", "GENERAL"),
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
            # Determine weight: Sentiment (-1 to 1) + Intent Bonus
            weight = 1.0 + log.sentiment_score
            if log.intent == "PTP": weight += 1.0
            if log.risk_level == "CRITICAL": weight -= 2.0
            
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

class ContactUpdateRequest(BaseModel):
    phone: str

@app.post("/api/v1/cases/{case_id}/update_contact")
def update_contact(case_id: str, request: ContactUpdateRequest, db: Session = Depends(get_db), current_user: str = Depends(verify_token)):
    """
    Update debtor phone number.
    """
    try:
        invoice_id = int(case_id.replace("C-", ""))
        invoice = db.query(InvoiceDB).filter(InvoiceDB.id == invoice_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Case not found")
            
        debtor = db.query(DebtorDB).filter(DebtorDB.id == invoice.debtor_id).first()
        debtor.phone = request.phone
        db.commit()
        
        return {"status": "success", "phone": debtor.phone}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class BridgeRequest(BaseModel):
    agent_phone: str
    debtor_phone: str

# --- TELEPHONY & ANALYSIS SYSTEM ---

@app.get("/api/v1/telephony/token")
def get_voice_token(current_user: str = Depends(verify_token)):
    """
    Generates a Twilio Access Token for the frontend VOIP client.
    """
    try:
        # Check if credentials are present
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        api_key = os.getenv("TWILIO_API_KEY")
        api_secret = os.getenv("TWILIO_API_SECRET")
        app_sid = os.getenv("TWILIO_APP_SID")
        
        if not all([account_sid, api_key, api_secret, app_sid]):
            raise HTTPException(status_code=500, detail="Twilio credentials missing in .env")

        token = AccessToken(
            account_sid,
            api_key,
            api_secret,
            identity=current_user
        )
        voice_grant = VoiceGrant(
            outgoing_application_sid=app_sid,
            incoming_allow=True
        )
        token.add_grant(voice_grant)
        return {"token": token.to_jwt()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token Error: {str(e)}")

@app.post("/api/v1/telephony/voice")
async def handle_voice_webhook(request: Request):
    """
    Twilio Voice Webhook: Orchestrates the call and enables recording.
    """
    form_data = await request.form()
    number_to_dial = form_data.get("To")
    # case_id can be passed as a custom parameter in the dial connection
    case_id = form_data.get("case_id", "UNKNOWN")

    response = VoiceResponse()
    
    if not number_to_dial:
        response.say("System Error. No number provided.")
        return Response(content=str(response), media_type="application/xml")

    print(f"[VOICE] Initiating Bridge to {number_to_dial} for Case {case_id}")

    # Connect to Debtor + Enable Recording
    # recording_status_callback will trigger our analysis loop
    dial = response.dial(
        caller_id=os.getenv("TWILIO_CALLER_ID", "+1234567890"),
        record="record-from-ringing-dual",
        recording_status_callback=f"{os.getenv('DOMAIN_URL')}/api/v1/telephony/recording_complete?case_id={case_id}",
        recording_status_callback_event="completed"
    )
    dial.number(number_to_dial)
    
    return Response(content=str(response), media_type="application/xml")

@app.post("/api/v1/telephony/recording_complete")
async def handle_recording_complete(
    case_id: str, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Post-Call AI Analysis Loop:
    1. Detects finished recording
    2. Downloads audio
    3. Analyzes with Sentinel (Gemini)
    4. Updates Riskon Score and Status
    """
    form_data = await request.form()
    recording_url = form_data.get("RecordingUrl")
    
    if not recording_url:
        return {"status": "ignored", "reason": "No recording URL"}

    print(f"[ANALYSIS] Triggered for Case {case_id}. Audio: {recording_url}")
    
    try:
        # A. Download Audio (Twilio recordings require auth if private)
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        audio_resp = requests.get(recording_url, auth=(account_sid, auth_token))
        audio_content = audio_resp.content
        
        # B. Analyze with Sentinel (Gemini Multimodal)
        # Assuming audio/wav as Twilio default
        analysis = await sentinel.analyze_audio(audio_content, "audio/wav")
        
        # C. Update Database
        # Extract invoice ID (C-XX format)
        try:
            invoice_id = int(case_id.replace("C-", ""))
        except:
            print(f"[ERROR] Invalid Case ID format: {case_id}")
            return {"status": "error", "message": "Invalid Case ID"}

        invoice = db.query(InvoiceDB).filter(InvoiceDB.id == invoice_id).first()
        
        if invoice:
            # 1. Save Transcription/Analysis to logs
            log = InteractionLogDB(
                invoice_id=invoice_id,
                created_at=datetime.utcnow().isoformat(),
                interaction_text=f"[AUTO-ANALYSIS] {analysis.get('transcript', 'Call Recorded')}",
                risk_level=analysis.get('risk_level', 'UNKNOWN'),
                intent=analysis.get('intent', 'GENERAL'),
                sentiment_score=0.0,
                violation_flags=json.dumps(analysis.get('violation_flags', []))
            )
            db.add(log)
            
            # 2. Recalculate Score
            # Define weights based on AI findings
            weight = 1.0
            if analysis.get("intent") == "PTP": weight = 2.0  # Big boost for promise to pay
            if analysis.get("risk_level") == "CRITICAL": weight = 0.0 # Compliance violation resets probability
            
            new_score = risk_engine.predict_probability(
                invoice.p_score,
                invoice.age_days,
                [{"day": invoice.age_days, "weight": weight}]
            )
            invoice.p_score = new_score
            
            # 3. Status Transitions
            if analysis.get("intent") == "PTP":
                invoice.status = "UNDER_REVIEW"
                # Add status history entry
                history = StatusHistoryDB(
                    invoice_id=invoice_id,
                    old_status="IN_PROGRESS", # Assume current
                    new_status="UNDER_REVIEW",
                    changed_by="SENTINEL_AI",
                    changed_at=datetime.utcnow().isoformat(),
                    reason="Automated intent detection: Promise to Pay",
                    auto_updated=1
                )
                db.add(history)
                
            db.commit()
            print(f"[SUCCESS] AI Loop Complete. Case {case_id} p_score -> {new_score}")
        else:
            print(f"[WARNING] Case ID {case_id} not found in DB")

    except Exception as e:
        print(f"[ERROR] Telephony Analysis Loop Failed: {e}")
        
    return {"status": "processed"}

@app.post("/api/v1/telephony/initiate_bridge")
def initiate_telephony_bridge(request: BridgeRequest, current_user: str = Depends(verify_token)):
    """
    Simulates a Twilio Programmable Voice Bridge.
    In production: Call Twilio API to connect Agent's Number to Debtor's Number.
    """
    print(f"[TELEPHONY BRIDGE] Initiating secure VOIP bridge...")
    print(f"[BRIDGE] Source: {request.agent_phone}")
    print(f"[BRIDGE] Target: {request.debtor_phone}")
    print(f"[BRIDGE] Recording: ENABLED (AI Sentinel Active)")
    
    return {
        "status": "success",
        "bridge_id": f"BRG-{datetime.utcnow().timestamp()}",
        "message": "Cloud Bridge Established. Ringing Agent now."
    }

class ManualCaseRequest(BaseModel):
    company_name: str
    amount: float
    age_days: int
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
