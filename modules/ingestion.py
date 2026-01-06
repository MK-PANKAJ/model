import pandas as pd
from sqlalchemy.orm import Session
from modules.database import DebtorDB, InvoiceDB, engine
import io

def process_csv_upload(file_contents: bytes, db: Session):
    """
    Reads a FedEx CSV export and ingests it into Cloud SQL.
    Expected Columns: 'company_name', 'amount', 'age_days', 'credit_score'
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
                # 1. Get or Create Debtor
                debtor_name = row.get("company_name", "Unknown")
                credit_score = float(row.get("credit_score", 0.5))
                
                debtor = db.query(DebtorDB).filter(DebtorDB.name == debtor_name).first()
                if not debtor:
                    debtor = DebtorDB(name=debtor_name, credit_score=credit_score, is_sample=0)
                    db.add(debtor)
                    db.commit()
                    db.refresh(debtor)
                
                # 2. Create Invoice
                new_invoice = InvoiceDB(
                    debtor_id=debtor.id,
                    amount=float(row.get("amount", 0)),
                    age_days=int(row.get("age_days", 0)),
                    p_score=0.0,      # Will be calculated by Agent later
                    decision="PENDING" # Needs Allocation
                )
                db.add(new_invoice)
                results["inserted"] += 1
                
            except Exception as row_err:
                print(f"Row {index} Error: {row_err}")
                results["errors"].append(f"Row {index}: {str(row_err)}")
                db.rollback()
        
        db.commit()
        return results
        
    except Exception as e:
        return {"error": str(e)}
