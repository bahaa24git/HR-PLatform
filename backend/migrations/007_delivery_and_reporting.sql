CREATE TABLE delivery_workflows(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, fields TEXT NOT NULL);
ALTER TABLE deliverables ADD COLUMN content_data TEXT NOT NULL DEFAULT '{}';
CREATE TABLE client_feedback(id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), project_id INTEGER REFERENCES projects(id), title TEXT NOT NULL, detail TEXT NOT NULL, rating REAL CHECK(rating BETWEEN 1 AND 5), recorded_by INTEGER NOT NULL REFERENCES employees(id), created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE notification_keys(employee_id INTEGER REFERENCES employees(id), reference TEXT NOT NULL, PRIMARY KEY(employee_id,reference));
INSERT INTO schema_versions(version) VALUES(7);
