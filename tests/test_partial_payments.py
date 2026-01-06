import sys
import os
import json
import requests
from sqlalchemy.orm import Session
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.getcwd())

from modules.database import SessionLocal, InvoiceDB, DebtorDB, StatusHistoryDB
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def setup_test_data(db: Session):
    # Create a test debtor
    debtor = DebtorDB(
        name="Partial Pay Corp",
        phone="9876543210",
        credit_score=0.75
    )
    db.add(debtor)
    db.commit()
    db.refresh(debtor)

    # Create a test invoice for 1000
    invoice = InvoiceDB(
        debtor_id=debtor.id,
        amount=1000.0,
        age_days=10,
        status="PENDING",
        p_score=0.5
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return debtor, invoice

def test_partial_payment_flow():
    db = SessionLocal()
    try:
        debtor, invoice = setup_test_data(db)
        case_id = f"C-{invoice.id}"
        print(f"Created Test Case: {case_id} for Rs. {invoice.amount}")

        # 1. Partial Payment of 400
        print("\n--- Simulating Partial Payment of Rs. 400 ---")
        response = client.get(f"/api/v1/payment/success?case_id={case_id}&amount_paid=400")
        assert response.status_code == 200
        
        db.refresh(invoice)
        print(f"Status: {invoice.status}")
        print(f"Paid Amount: Rs. {invoice.paid_amount}")
        print(f"Remaining: Rs. {invoice.amount - invoice.paid_amount}")
        
        assert invoice.status == "IN_PROGRESS"
        assert invoice.paid_amount == 400.0

        # 2. Final Payment of 600
        print("\n--- Simulating Final Payment of Rs. 600 ---")
        response = client.get(f"/api/v1/payment/success?case_id={case_id}&amount_paid=600")
        assert response.status_code == 200
        
        db.refresh(invoice)
        print(f"Status: {invoice.status}")
        print(f"Paid Amount: Rs. {invoice.paid_amount}")
        print(f"Remaining: Rs. {invoice.amount - invoice.paid_amount}")
        
        assert invoice.status == "RESOLVED"
        assert invoice.paid_amount == 1000.0
        assert invoice.resolved_at is not None

        # 3. Check Status History
        history = db.query(StatusHistoryDB).filter(StatusHistoryDB.invoice_id == invoice.id).all()
        print(f"\nStatus History Logs: {len(history)}")
        for log in history:
            print(f"  - {log.old_status} -> {log.new_status} | Reason: {log.reason}")

        print("\n✅ Partial Payment Flow Verified Successfully!")

    finally:
        # Cleanup
        db.delete(invoice)
        db.delete(debtor)
        db.commit()
        db.close()

if __name__ == "__main__":
    test_partial_payment_flow()
