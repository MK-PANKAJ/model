import pandas as pd
from sqlalchemy.orm import Session
from modules.database import DebtorDB, InvoiceDB, engine
import io

def process_csv_upload(file_contents: bytes, db: Session):
    """
    Reads a FedEx CSV export and ingests it into Cloud SQL.
    Expected Columns: 'company_name', 'amount', 'age_days', 'credit_score', 'phone'
    """
    try:
        # Load CSV into Pandas DataFrame
        df = pd.read_csv(io.BytesIO(file_contents))
        
        # Standardize Columns (Lowercase, strip spaces)
        df.columns = [c.lower().strip() for c in df.columns]
        
        # AUTO-CLEANUP: Remove ONLY sample data (is_sample=1) when real data is uploaded
        # SAFETY: Real data (is_sample=0) is NEVER deleted by this logic
        print("[*] Checking for sample data to remove...")
        sample_debtors = db.query(DebtorDB).filter(DebtorDB.is_sample == 1).all()
        
        if len(sample_debtors) > 0:
            print(f"[CLEANUP] Found {len(sample_debtors)} sample debtors (is_sample=1):")
            for sample_debtor in sample_debtors:
                print(f"  - Removing: {sample_debtor.name} (ID: {sample_debtor.id}, is_sample: {sample_debtor.is_sample})")
                # Delete all invoices for this sample debtor
                invoice_count = db.query(InvoiceDB).filter(InvoiceDB.debtor_id == sample_debtor.id).count()
                db.query(InvoiceDB).filter(InvoiceDB.debtor_id == sample_debtor.id).delete()
                # Delete the sample debtor
                db.delete(sample_debtor)
                print(f"    -> Deleted {invoice_count} invoice(s)")
            db.commit()
            print(f"[OK] Sample data cleanup complete")
        else:
            print("[OK] No sample data found (all existing data is real)")
        
        results = {"total": 0, "inserted": 0, "errors": []}
        results["total"] = len(df)
        
        for index, row in df.iterrows():
            try:
                # 1. Get or Create/Update Debtor
                debtor_name = str(row.get("company_name", "Unknown")).strip()
                credit_score = float(row.get("credit_score", 0.5))
                phone = str(row.get("phone", "")).strip()
                
                debtor = db.query(DebtorDB).filter(DebtorDB.name == debtor_name).first()
                if not debtor:
                    debtor = DebtorDB(name=debtor_name, credit_score=credit_score, phone=phone, is_sample=0)
                    db.add(debtor)
                    db.commit()
                    db.refresh(debtor)
                else:
                    # Sync info if changed
                    if credit_score != debtor.credit_score or (phone and phone != debtor.phone):
                        debtor.credit_score = credit_score
                        if phone: debtor.phone = phone
                        db.commit()
                
                # 2. Check for Duplicate Invoice (Avoid double-billing)
                amount = float(row.get("amount", 0))
                age_days = int(row.get("age_days", 0))
                
                existing_invoice = db.query(InvoiceDB).filter(
                    InvoiceDB.debtor_id == debtor.id,
                    InvoiceDB.amount == amount,
                    InvoiceDB.status != "CLOSED" # Allow re-ingesting if closed? No, usually not.
                ).first()
                
                if not existing_invoice:
                    new_invoice = InvoiceDB(
                        debtor_id=debtor.id,
                        amount=amount,
                        age_days=age_days,
                        p_score=0.0,      # Will be calculated by Agent later
                        decision="PENDING",
                        status="PENDING"
                    )
                    db.add(new_invoice)
                    results["inserted"] += 1
                else:
                    results["errors"].append(f"Row {index}: Duplicate invoice for {debtor_name} rejected.")
                
            except Exception as row_err:
                print(f"Row {index} Error: {row_err}")
                results["errors"].append(f"Row {index}: {str(row_err)}")
                db.rollback()
        
        db.commit()
        return results
        
    except Exception as e:
        return {"error": str(e)}
