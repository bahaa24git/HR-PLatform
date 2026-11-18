-- Additive policy and authorization metadata. Existing records and relationships remain intact.
ALTER TABLE attendance ADD COLUMN classification TEXT NOT NULL DEFAULT 'Unclassified'
    CHECK(classification IN ('Normal','Late','Absent','Unclassified'));
ALTER TABLE attendance ADD COLUMN review_status TEXT NOT NULL DEFAULT 'Not required'
    CHECK(review_status IN ('Not required','Pending','Excused','Unauthorized'));
UPDATE attendance
   SET classification=CASE
       WHEN check_in IS NULL THEN 'Unclassified'
       WHEN substr(check_in,12,5)>'11:00' THEN 'Absent'
       WHEN substr(check_in,12,5)>'09:15' THEN 'Late'
       ELSE 'Normal' END,
       review_status=CASE WHEN check_in IS NOT NULL AND substr(check_in,12,5)>'11:00' THEN 'Pending' ELSE 'Not required' END;
CREATE TABLE attendance_reviews(
    id INTEGER PRIMARY KEY,
    attendance_id INTEGER NOT NULL REFERENCES attendance(id),
    reviewer_user_id INTEGER NOT NULL REFERENCES users(id),
    decision TEXT NOT NULL CHECK(decision IN ('Excused','Unauthorized')),
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_attendance_reviews_record ON attendance_reviews(attendance_id,id);
CREATE TABLE onboarding_exceptions(
    id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    starts_on TEXT NOT NULL,
    ends_on TEXT NOT NULL,
    reason TEXT NOT NULL,
    granted_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(ends_on>=starts_on)
);
ALTER TABLE project_members ADD COLUMN capabilities TEXT NOT NULL DEFAULT '[]';
INSERT OR IGNORE INTO settings(key,value) VALUES('absence_deduction_days','4');
UPDATE settings SET value='18' WHERE key='end_hour';
UPDATE settings SET value='15' WHERE key='grace_minutes';
UPDATE settings SET value='false' WHERE key='late_deduction';
-- Fresh non-demo installations still need neutral runtime configuration. Existing
-- company values are preserved because all defaults use INSERT OR IGNORE.
INSERT OR IGNORE INTO settings(key,value) VALUES('company_name','"Your Company"');
INSERT OR IGNORE INTO settings(key,value) VALUES('currency','"EGP"');
INSERT OR IGNORE INTO settings(key,value) VALUES('timezone','"Africa/Cairo"');
INSERT OR IGNORE INTO settings(key,value) VALUES('start_hour','9');
INSERT OR IGNORE INTO settings(key,value) VALUES('end_hour','18');
INSERT OR IGNORE INTO settings(key,value) VALUES('grace_minutes','15');
INSERT OR IGNORE INTO settings(key,value) VALUES('absence_deduction_days','4');
INSERT OR IGNORE INTO settings(key,value) VALUES('workdays','[6,0,1,2,3]');
INSERT OR IGNORE INTO settings(key,value) VALUES('overtime_multiplier','1.5');
INSERT OR IGNORE INTO settings(key,value) VALUES('working_days','22');
INSERT OR IGNORE INTO settings(key,value) VALUES('late_deduction','false');
INSERT OR IGNORE INTO settings(key,value) VALUES('notice_days','30');
INSERT OR IGNORE INTO settings(key,value) VALUES('geofence','{"enabled":false,"apply_remote":false,"latitude":0,"longitude":0,"radius_m":300}');
INSERT OR IGNORE INTO settings(key,value) VALUES('survey_minimum','3');
INSERT INTO schema_versions(version) VALUES(11);
