"""
Sample Data Generator for RecoverAI
Populates the database with realistic debt cases for testing and demo purposes.
"""

from modules.database import SessionLocal, DebtorDB, InvoiceDB, Base, engine

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Sample debtors with varying credit profiles
SAMPLE_DEBTORS = [
    {"name": "Acme Logistics Pvt Ltd", "credit_score": 0.85},
    {"name": "Global Trade Enterprises", "credit_score": 0.62},
    {"name": "StartUp Technologies Inc", "credit_score": 0.91},
    {"name": "Retail Solutions Corp", "credit_score": 0.45},
    {"name": "Manufacturing Co", "credit_score": 0.73},
    {"name": "E-Commerce Ventures", "credit_score": 0.38},
    {"name": "Construction Builders Ltd", "credit_score": 0.67},
    {"name": "Healthcare Services", "credit_score": 0.82},
]

# Sample invoices with varying amounts and ages
SAMPLE_INVOICES = [
    {"debtor_idx": 0, "amount": 154000, "age_days": 12},
    {"debtor_idx": 1, "amount": 420000, "age_days": 45},
    {"debtor_idx": 2, "amount": 21000, "age_days": 5},
    {"debtor_idx": 3, "amount": 285000, "age_days": 89},
    {"debtor_idx": 4, "amount": 135000, "age_days": 23},
    {"debtor_idx": 5, "amount": 567000, "age_days": 120},
    {"debtor_idx": 6, "amount": 98000, "age_days": 34},
    {"debtor_idx": 7, "amount": 76000, "age_days": 8},
]

def add_sample_data():
    db = SessionLocal()
    
    try:
        print("[*] Adding sample debtors...")
        debtor_objects = []
        
        for debtor_data in SAMPLE_DEBTORS:
            # Check if debtor already exists
            existing = db.query(DebtorDB).filter(DebtorDB.name == debtor_data["name"]).first()
            if existing:
                print(f"  [SKIP] {debtor_data['name']} (already exists)")
                debtor_objects.append(existing)
            else:
                debtor = DebtorDB(**debtor_data, is_sample=1)  # Mark as sample
                db.add(debtor)
                db.flush()  # Get the ID
                debtor_objects.append(debtor)
                print(f"  [OK] Added {debtor_data['name']}")
        
        db.commit()
        
        print("\n[*] Adding sample invoices...")
        for invoice_data in SAMPLE_INVOICES:
            debtor = debtor_objects[invoice_data["debtor_idx"]]
            
            # Check if invoice already exists for this debtor with same amount
            existing_invoice = db.query(InvoiceDB).filter(
                InvoiceDB.debtor_id == debtor.id,
                InvoiceDB.amount == invoice_data["amount"]
            ).first()
            
            if existing_invoice:
                print(f"  [SKIP] invoice for {debtor.name} (already exists)")
            else:
                invoice = InvoiceDB(
                    debtor_id=debtor.id,
                    amount=invoice_data["amount"],
                    age_days=invoice_data["age_days"],
                    p_score=0.0,  # Will be calculated when analyzed
                    decision="PENDING",
                    risk_level="UNKNOWN",
                    status="PENDING"
                )
                db.add(invoice)
                print(f"  [OK] Added Rs.{invoice_data['amount']:,} invoice for {debtor.name}")
        
        db.commit()
        
        print("\n[SUCCESS] Sample data loaded!")
        print(f"[DATA] Total Debtors: {db.query(DebtorDB).count()}")
        print(f"[DATA] Total Invoices: {db.query(InvoiceDB).count()}")
        print(f"[DATA] Total Outstanding: Rs.{sum([inv.amount for inv in db.query(InvoiceDB).filter(InvoiceDB.status == 'PENDING').all()]):,}")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("RecoverAI - Sample Data Generator")
    print("=" * 50)
    add_sample_data()
