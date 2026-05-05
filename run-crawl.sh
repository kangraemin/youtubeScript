#!/bin/bash
set -e
cd /Users/ram/programming/vibecoding/youtubeScript
source .env.local
mkdir -p rawdata/transcripts
.venv/bin/python scripts/crawl_youtube_transcripts.py --days 60 --headless --workers 3 >> rawdata/transcripts/_cron.log 2>&1
