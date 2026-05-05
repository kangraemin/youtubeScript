CREATE TABLE IF NOT EXISTS public.transcripts (
    vid        TEXT PRIMARY KEY,
    channel    TEXT NOT NULL,
    channel_slug TEXT NOT NULL,
    title      TEXT NOT NULL,
    published_at DATE,
    collected_at TIMESTAMPTZ,
    transcript TEXT,
    url        TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS transcripts_channel_slug_idx ON public.transcripts (channel_slug);
CREATE INDEX IF NOT EXISTS transcripts_published_at_idx ON public.transcripts (published_at);
