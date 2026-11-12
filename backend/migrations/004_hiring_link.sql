ALTER TABLE candidates ADD COLUMN employee_id INTEGER REFERENCES employees(id);
INSERT INTO schema_versions(version) VALUES(4);
