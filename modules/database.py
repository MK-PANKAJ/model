import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# 1. DATABASE SETUP
# Check for Cloud SQL URL (PostgreSQL) or fallback to Local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recoverai.db")

connect_args = {}
# SQLite needs this specific check_same_thread flag, Postgres does not
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. DEFINING THE TABLES (ORM)
class DebtorDB(Base):
    __tablename__ = "debtors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    credit_score = Column(Float)
    phone = Column(String, nullable=True)
    is_sample = Column(Integer, default=0)  # 0=Real, 1=Sample (for auto-cleanup)

class InvoiceDB(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    debtor_id = Column(Integer, ForeignKey("debtors.id"))
    amount = Column(Float)
    age_days = Column(Integer)
    # AI Scores
    p_score = Column(Float, default=0.0)
    decision = Column(String, default="PENDING")
    # Sentinel Compliance
    risk_level = Column(String, default="UNKNOWN")
    # Payment Status
    status = Column(String, default="PENDING")  # PENDING | IN_PROGRESS | UNDER_REVIEW | RESOLVED | CLOSED | ESCALATED
    resolved_at = Column(String, nullable=True)  # ISO timestamp when resolved
    closed_at = Column(String, nullable=True)  # ISO timestamp when closed
    closed_reason = Column(String, nullable=True)  # Reason for closing

class InteractionLogDB(Base):
    __tablename__ = "interaction_logs"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    created_at = Column(String)  # ISO timestamp
    interaction_text = Column(String)  # What the agent said/wrote
    risk_level = Column(String, default="UNKNOWN")  # Sentinel result
    sentiment_score = Column(Float, default=0.0)
    violation_flags = Column(String, default="[]")  # JSON as string for SQLite compatibility

class StatusHistoryDB(Base):
    __tablename__ = "status_history"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    old_status = Column(String)
    new_status = Column(String)
    changed_by = Column(String)  # username or "SYSTEM"
    changed_at = Column(String)  # ISO timestamp
    reason = Column(String, nullable=True)  # Optional reason for change
    auto_updated = Column(Integer, default=0)  # 0=Manual, 1=Automatic

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

# 3. HELPER TO GET DB SESSION
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
