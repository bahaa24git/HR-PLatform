CREATE TABLE lead_statuses(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, position INTEGER NOT NULL);
INSERT INTO lead_statuses(name,position) VALUES('New',1),('Contacted',2),('Qualified',3),('Meeting Scheduled',4),('Proposal Sent',5),('Negotiation',6),('Won',7),('Lost',8);
INSERT INTO schema_versions(version) VALUES(9);
