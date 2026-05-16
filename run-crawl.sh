#!/bin/bash
set -e
cd /Users/ram/programming/vibecoding/youtubeScript
source .env.local
mkdir -p rawdata/transcripts
.venv/bin/python scripts/crawl_youtube_transcripts.py --headless --workers 3 >> rawdata/transcripts/_cron.log 2>&1
.venv/bin/python scripts/upload_transcripts.py >> rawdata/transcripts/_cron.log 2>&1
