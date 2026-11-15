CREATE TABLE case_access(user_id INTEGER NOT NULL REFERENCES users(id), complaint_id INTEGER NOT NULL REFERENCES complaints(id), granted_by INTEGER NOT NULL REFERENCES users(id), PRIMARY KEY(user_id,complaint_id));
INSERT INTO schema_versions(version) VALUES(8);
