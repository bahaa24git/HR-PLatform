CREATE TABLE invoices(id INTEGER PRIMARY KEY, contract_id INTEGER NOT NULL REFERENCES client_contracts(id), number TEXT NOT NULL UNIQUE, issued TEXT NOT NULL, due TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>0), status TEXT NOT NULL DEFAULT 'Draft' CHECK(status IN ('Draft','Issued','Cancelled')), notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
ALTER TABLE payments ADD COLUMN invoice_id INTEGER REFERENCES invoices(id);
CREATE INDEX payments_invoice ON payments(invoice_id);
INSERT INTO schema_versions(version) VALUES(13);
