#!/usr/bin/env python3
"""미요약 transcript 1편을 원자적으로 claim 후 fetch.

여러 세션이 동시에 실행돼도 같은 vid를 두 번 잡지 않도록
`FOR UPDATE SKIP LOCKED` + `summary_started_at` 타임아웃(10분) 사용.
Management API + Personal Access Token으로 raw SQL 실행
(PostgREST는 FOR UPDATE SKIP LOCKED 미지원).

메타데이터는 stdout JSON, transcript 본문은 /tmp/summarize_target.txt로 dump.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.channel_config import STOCK_ECON_SLUGS

TARGET_PATH = "/tmp/summarize_target.txt"
CHUNK_SIZE = 320
CLAIM_TIMEOUT_MIN = 10


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _env(name: str) -> str:
    v = os.environ.get(name)
    if v:
        return v
    # youtubeScript .env.local 우선, 그다음 tax-watcher (PAT가 거기 있음)
    env_paths = [
        os.path.join(PROJECT_ROOT, ".env.local"),
        "/Users/ram/programming/vibecoding/tax-watcher/.env",
        os.path.expanduser("~/.claude/.env"),
    ]
    for p in env_paths:
        if not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{name}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _project_ref() -> str:
    # youtubeScript는 NEXT_PUBLIC_SUPABASE_URL이 정본 (.env.local)
    url = _env("NEXT_PUBLIC_SUPABASE_URL") or _env("SUPABASE_URL")
    # https://<ref>.supabase.co
    return url.replace("https://", "").split(".", 1)[0]


def run_sql(query: str) -> list:
    pat = _env("SUPABASE_PAT")
    ref = _project_ref()
    if not pat or not ref:
        raise SystemExit("SUPABASE_PAT / project ref 미설정")
    req = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{ref}/database/query",
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {pat}",
            "Content-Type": "application/json",
            # Cloudflare 1010 차단 우회 — urllib 기본 UA는 블록됨
            "User-Agent": "curl/8.7.1",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    slugs_sql = ",".join(f"'{s}'" for s in STOCK_ECON_SLUGS)
    query = f"""
    UPDATE public.transcripts
    SET summary_started_at = NOW()
    WHERE vid = (
      SELECT vid FROM public.transcripts
      WHERE summary IS NULL
        AND transcript IS NOT NULL
        AND channel_slug IN ({slugs_sql})
        AND (summary_started_at IS NULL
             OR summary_started_at < NOW() - INTERVAL '{CLAIM_TIMEOUT_MIN} minutes')
      ORDER BY published_at DESC
      LIMIT 1
      FOR UPDATE SKIP LOCKED
    )
    RETURNING vid, channel, channel_slug, title, published_at, transcript, url;
    """
    rows = run_sql(query)

    if not rows:
        try:
            os.remove(TARGET_PATH)
        except FileNotFoundError:
            pass
        print(json.dumps({"empty": True}))
        return 0

    row = rows[0]
    t = row.pop("transcript") or ""

    with open(TARGET_PATH, "w", encoding="utf-8") as f:
        f.write(t)

    lines = t.count("\n") + (1 if t and not t.endswith("\n") else 0)
    row["transcript_path"] = TARGET_PATH
    row["transcript_chars"] = len(t)
    row["transcript_lines"] = lines
    row["chunk_size"] = CHUNK_SIZE
    row["read_chunks"] = -(-lines // CHUNK_SIZE) if lines else 0

    print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
