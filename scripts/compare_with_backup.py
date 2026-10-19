#!/usr/bin/env python3
"""옛 추출(백업 테이블)과 새 추출을 영상별로 비교한다.

새 prompt_version으로 끝난 영상만 본다. 영상마다 가게 이름을 세 갈래로 나눈다:
둘 다 있음 / 옛것에만 있음 / 새것에만 있음. 결과는 rawdata/reports/compare-<date>.md.

Usage:
    python scripts/compare_with_backup.py
"""
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))

from restaurant_extractor import PROMPT_VERSION  # noqa: E402
from supabase_client import get_client  # noqa: E402

BACKUP_R = "restaurants_backup_20261019"
BACKUP_V = "videos_backup_20261019"


def _all(q, page=1000) -> list[dict]:
    out, i = [], 0
    while True:
        rows = q.range(i, i + page - 1).execute().data or []
        out += rows
        if len(rows) < page:
            return out
        i += page


def _key(name: str) -> str:
    return re.sub(r"\s+|본점$|\S+점$", "", name or "")


def names_by_video(db, rest_table: str, video_table: str, vids: set[str]) -> dict[str, set[str]]:
    rest = {r["id"]: r["name"] for r in _all(db.table(rest_table).select("id,name"))}
    out = defaultdict(set)
    for v in _all(db.table(video_table).select("video_id,restaurant_id")):
        if v["video_id"] in vids and v.get("restaurant_id") in rest:
            out[v["video_id"]].add(rest[v["restaurant_id"]])
    return out


def main():
    db = get_client()
    done = {q["video_id"] for q in _all(db.table("processing_queue").select("video_id")
                                        .eq("prompt_version", PROMPT_VERSION)
                                        .in_("status", ["done", "no_restaurant"]))}
    old = names_by_video(db, BACKUP_R, BACKUP_V, done)
    new = names_by_video(db, "restaurants", "videos", done)

    both = only_old = only_new = 0
    lines = []
    for vid in sorted(set(old) | set(new)):
        o = {_key(n): n for n in old.get(vid, set())}
        n = {_key(x): x for x in new.get(vid, set())}
        b, oo, nn = o.keys() & n.keys(), o.keys() - n.keys(), n.keys() - o.keys()
        both, only_old, only_new = both + len(b), only_old + len(oo), only_new + len(nn)
        if oo or nn:
            lines.append(f"- [{vid}](https://youtu.be/{vid}) "
                         f"옛것만: {', '.join(o[k] for k in oo) or '-'} / 새것만: {', '.join(n[k] for k in nn) or '-'}")

    text = "\n".join([
        f"# 옛 추출 vs 새 추출 ({date.today().isoformat()}, prompt {PROMPT_VERSION})",
        "",
        f"- 비교한 영상: {len(done)} (옛 기록 있음 {len(old)})",
        f"- 둘 다 있음: {both}",
        f"- 옛것에만 있음: {only_old}",
        f"- 새것에만 있음: {only_new}",
        "",
        "## 다른 영상",
        *(lines or ["- 없음"]),
        "",
    ])
    out = ROOT / f"rawdata/reports/compare-{date.today().isoformat()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
