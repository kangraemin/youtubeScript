#!/bin/bash
# NULL transcript 자동 수집 + DB 업로드 (cron용)
cd /Users/ram/programming/vibecoding/youtubeScript
source .env.local 2>/dev/null || true

LOG="rawdata/transcripts/_cron_auto.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 시작" >> "$LOG"

# NULL인 영상만 backfill
python3 scripts/backfill_transcripts.py --headless >> "$LOG" 2>&1

# Supabase 업로드
python3 -c "
import json, os, sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv('.env.local')
os.environ.setdefault('SUPABASE_URL', os.environ.get('NEXT_PUBLIC_SUPABASE_URL',''))
os.environ.setdefault('SUPABASE_SERVICE_KEY', os.environ.get('SUPABASE_SERVICE_ROLE_KEY',''))
sys.path.insert(0, 'worker')
from supabase_client import get_client

db = get_client()
TRANSCRIPTS_DIR = Path('rawdata/transcripts')
BATCH_SIZE = 20

def _parse_date(val):
    if not val: return None
    try:
        from datetime import date; date.fromisoformat(val); return val
    except: return None

total = 0
for slug_dir in sorted(TRANSCRIPTS_DIR.iterdir()):
    if not slug_dir.is_dir(): continue
    list_file = slug_dir / '_list.json'
    if not list_file.exists(): continue
    videos = json.load(open(list_file))
    rows = []
    for v in videos:
        vid = v.get('vid')
        if not vid: continue
        txt = slug_dir / f'{vid}.txt'
        transcript = txt.read_text(encoding='utf-8').strip() if txt.exists() else None
        if transcript is None: continue  # NULL은 건너뜀 (새로 생긴 것만)
        rows.append({'vid': vid, 'channel': v.get('channel',''), 'channel_slug': slug_dir.name,
                     'title': v.get('title',''), 'published_at': _parse_date(v.get('meta')),
                     'collected_at': v.get('collected_at') or None,
                     'transcript': transcript, 'url': v.get('url','')})
    for i in range(0, len(rows), BATCH_SIZE):
        try:
            db.table('transcripts').upsert(rows[i:i+BATCH_SIZE], on_conflict='vid').execute()
            total += len(rows[i:i+BATCH_SIZE])
        except Exception as e:
            print(f'  [{slug_dir.name}] 에러: {e}')
print(f'업로드: {total}개')
" >> "$LOG" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 완료" >> "$LOG"
