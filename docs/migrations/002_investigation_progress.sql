-- Investigation progress persistence (tutorial-aligned schema)
-- Applied via InsForge MCP run-raw-sql or dashboard SQL editor.

ALTER TABLE investigations
  ALTER COLUMN status SET DEFAULT 'running';

ALTER TABLE investigations
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS investigation_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  investigation_id UUID NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
  step TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  message TEXT,
  details JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT investigation_progress_step_unique UNIQUE (investigation_id, step),
  CONSTRAINT investigation_progress_status_check
    CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_investigation_progress_investigation_id
  ON investigation_progress (investigation_id);

ALTER TABLE investigation_progress ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS investigation_progress_select_own ON investigation_progress;
CREATE POLICY investigation_progress_select_own ON investigation_progress
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM investigations i
      WHERE i.id = investigation_progress.investigation_id
        AND i.user_id = auth.uid()::text
    )
  );

DROP POLICY IF EXISTS investigations_update_own ON investigations;
CREATE POLICY investigations_update_own ON investigations
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid()::text)
  WITH CHECK (user_id = auth.uid()::text);
