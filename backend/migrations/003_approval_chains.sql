CREATE TABLE leave_approval_steps(id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL REFERENCES leave_requests(id), ordinal INTEGER NOT NULL, approver_id INTEGER NOT NULL REFERENCES employees(id), status TEXT NOT NULL DEFAULT 'Queued', UNIQUE(request_id,ordinal));
INSERT OR IGNORE INTO settings(key,value) VALUES('approval_chain','["leader"]');
INSERT OR IGNORE INTO settings(key,value) VALUES('leave_count_mode','"calendar"');
INSERT INTO schema_versions(version) VALUES(3);
