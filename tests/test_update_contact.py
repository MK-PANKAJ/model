from fastapi.testclient import TestClient
from main import app
from modules.database import Base, engine, SessionLocal, InvoiceDB, DebtorDB
from modules.security import verify_token

# Reset DB for test
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)
app.dependency_overrides[verify_token] = lambda: "test_user"

def test_update_contact_route():
    # 1. Create a sample debtor and invoice
    db = SessionLocal()
    debtor = DebtorDB(name="Test Debtor", phone="1234567890")
    db.add(debtor)
    db.commit()
    db.refresh(debtor)
    
    invoice = InvoiceDB(debtor_id=debtor.id, amount=1000, p_score=0.5, status="PENDING")
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    case_id = f"C-{invoice.id}"
    
    # 2. Test the endpoint
    payload = {"phone": "9876543210"}
    response = client.post(f"/api/v1/cases/{case_id}/update_contact", json=payload)
    
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # 3. Verify in DB
    db.refresh(debtor)
    assert debtor.phone == "9876543210"
    db.close()

if __name__ == "__main__":
    test_update_contact_route()
