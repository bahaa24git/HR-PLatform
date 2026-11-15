ALTER TABLE ai_messages ADD COLUMN access_hash TEXT NOT NULL DEFAULT '';
ALTER TABLE ai_messages ADD COLUMN result_json TEXT;
CREATE INDEX ai_messages_user_history ON ai_messages(user_id,id);
INSERT INTO schema_versions(version) VALUES(10);
