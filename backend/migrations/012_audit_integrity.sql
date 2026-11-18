CREATE TABLE holidays(id INTEGER PRIMARY KEY, name TEXT NOT NULL, day TEXT NOT NULL UNIQUE, paid INTEGER NOT NULL DEFAULT 1 CHECK(paid IN (0,1)));
ALTER TABLE campaigns ADD COLUMN extension_reason TEXT NOT NULL DEFAULT '';
CREATE TABLE attendance_corrections(id INTEGER PRIMARY KEY, attendance_id INTEGER NOT NULL REFERENCES attendance(id), actor_id INTEGER NOT NULL REFERENCES users(id), before_data TEXT NOT NULL, after_data TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX attendance_employee_classification ON attendance(employee_id,day,classification,review_status);
CREATE INDEX payroll_employee_month_status ON payroll(employee_id,month,status);
CREATE INDEX leave_employee_period_status ON leave_requests(employee_id,start,end,status);
INSERT INTO schema_versions(version) VALUES(12);
