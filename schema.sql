-- RecoverAI Database Schema (Phase 1)

-- 1. THE DEBTOR PROFILE
CREATE TABLE debtors (
    debtor_id UUID PRIMARY KEY,
    company_name VARCHAR(255),
    industry_segment VARCHAR(50),
    contract_start_date DATE,
    payment_terms INT, 
    aggregated_credit_score INT,
    total_lifetime_value DECIMAL(12,2)
);

-- 2. THE INVOICE (The Core Unit of Work)
CREATE TABLE invoices (
    invoice_id UUID PRIMARY KEY,
    debtor_id UUID REFERENCES debtors(debtor_id),
    invoice_date DATE,
    due_date DATE,
    total_amount DECIMAL(12,2),
    outstanding_balance DECIMAL(12,2),
    status VARCHAR(20),
    
    -- AI META-DATA
    recovery_probability_score DECIMAL(5,4),
    predicted_recovery_date DATE,
    allocation_group VARCHAR(50)
);

-- 3. INTERACTION HISTORY
CREATE TABLE interaction_logs (
    interaction_id UUID PRIMARY KEY,
    invoice_id UUID REFERENCES invoices(invoice_id),
    agent_id UUID,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    channel VARCHAR(10),
    
    -- SENTINEL OUTPUTS
    sentiment_score DECIMAL(3,2),
    flagged_violation BOOLEAN DEFAULT FALSE,
    violation_tags TEXT[],
    
    -- CONTENT
    transcript_summary TEXT,
    blockchain_hash VARCHAR(66)
);
