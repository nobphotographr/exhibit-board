DO $$
BEGIN
  CREATE TYPE candidate_status AS ENUM ('pending', 'approved', 'rejected', 'imported');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  CREATE TYPE ingestion_source AS ENUM ('x', 'website', 'manual');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS event_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_fingerprint TEXT NOT NULL UNIQUE,
  extracted JSONB NOT NULL,
  confidence NUMERIC(4, 3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  status candidate_status NOT NULL DEFAULT 'pending',
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS candidate_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES event_candidates(id) ON DELETE CASCADE,
  source_type ingestion_source NOT NULL,
  source_key TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_name TEXT,
  author_handle TEXT,
  content_hash TEXT,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source_type, source_key)
);

CREATE INDEX IF NOT EXISTS idx_event_candidates_status ON event_candidates(status);
CREATE INDEX IF NOT EXISTS idx_event_candidates_last_seen ON event_candidates(last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_candidate_sources_candidate ON candidate_sources(candidate_id);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_event_candidates_updated_at ON event_candidates;
CREATE TRIGGER update_event_candidates_updated_at
  BEFORE UPDATE ON event_candidates
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE event_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_sources ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'event_candidates'
      AND policyname = 'Service role full access to event candidates'
  ) THEN
    CREATE POLICY "Service role full access to event candidates" ON event_candidates
      FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'candidate_sources'
      AND policyname = 'Service role full access to candidate sources'
  ) THEN
    CREATE POLICY "Service role full access to candidate sources" ON candidate_sources
      FOR ALL USING (auth.role() = 'service_role');
  END IF;
END $$;

GRANT ALL ON event_candidates TO service_role;
GRANT ALL ON candidate_sources TO service_role;
