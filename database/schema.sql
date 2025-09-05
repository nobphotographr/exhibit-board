-- Create custom types
CREATE TYPE jp_prefecture AS ENUM (
  '北海道','青森県','岩手県','宮城県','秋田県','山形県','福島県',
  '茨城県','栃木県','群馬県','埼玉県','千葉県','東京都','神奈川県',
  '新潟県','富山県','石川県','福井県','山梨県','長野県','岐阜県',
  '静岡県','愛知県','三重県','滋賀県','京都府','大阪府','兵庫県',
  '奈良県','和歌山県','鳥取県','島根県','岡山県','広島県','山口県',
  '徳島県','香川県','愛媛県','高知県','福岡県','佐賀県','長崎県',
  '熊本県','大分県','宮崎県','鹿児島県','沖縄県'
);

CREATE TYPE event_status AS ENUM ('published', 'pending', 'rejected');

-- Create events table
CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  host_name TEXT,
  x_url TEXT CHECK (x_url IS NULL OR x_url ~ '^https?://(x\.com|twitter\.com)/'),
  ig_url TEXT CHECK (ig_url IS NULL OR ig_url ~ '^https?://(www\.)?instagram\.com/'),
  threads_url TEXT CHECK (threads_url IS NULL OR threads_url ~ '^https?://(www\.)?threads\.net/'),
  venue TEXT NOT NULL,
  address TEXT,
  prefecture jp_prefecture NOT NULL,
  price TEXT,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL CHECK (end_date >= start_date),
  announce_url TEXT NOT NULL UNIQUE,
  notes TEXT,
  status event_status NOT NULL DEFAULT 'published' CHECK (status IN ('published', 'pending', 'rejected')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_events_start_date ON events(start_date);
CREATE INDEX IF NOT EXISTS idx_events_end_date ON events(end_date);
CREATE INDEX IF NOT EXISTS idx_events_prefecture ON events(prefecture);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
CREATE INDEX IF NOT EXISTS idx_events_announce_url ON events(announce_url);

-- Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_events_updated_at 
  BEFORE UPDATE ON events 
  FOR EACH ROW 
  EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- Public read access for published events
CREATE POLICY "Public read access for published events" ON events
  FOR SELECT 
  USING (status = 'published');

-- Service role can insert/update/delete
CREATE POLICY "Service role full access" ON events
  FOR ALL
  USING (auth.role() = 'service_role');

-- Anonymous read access (for client-side queries)
CREATE POLICY "Anonymous read access for published events" ON events
  FOR SELECT 
  TO anon
  USING (status = 'published');

-- Grant necessary permissions
GRANT SELECT ON events TO anon;
GRANT ALL ON events TO service_role;