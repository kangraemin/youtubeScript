#!/usr/bin/env python3
"""MukMap 파이프라인 일일 리포트 — 어제(KST) 처리 수·새 가게·검수 대기·실패·토큰.

rawdata/reports/daily-<date>.md에 쓰고 같은 내용을 stdout으로 낸다(cron 로그에 남는다).

Usage:
    python scripts/mukmap_daily_report.py [--date 2026-10-19]
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "worker"))

from supabase_client import get_client  # noqa: E402

KST = timezone(timedelta(hours=9))
USAGE_LOG = ROOT / "rawdata/reports/pipeline-usage.jsonl"


def _count(q) -> int:
    return q.execute().count or 0


def build(day: date) -> str:
    start = datetime(day.year, day.month, day.day, tzinfo=KST)
    end = start + timedelta(days=1)
    s, e = start.isoformat(), end.isoformat()
    db = get_client()

    def q(table):
        return db.table(table).select("id", count="exact", head=True)

    by_status = {st: _count(q("processing_queue").eq("status", st).gte("processed_at", s).lt("processed_at", e))
                 for st in ("done", "no_restaurant", "no_transcript")}
    failed = _count(q("processing_queue").eq("status", "failed").gte("created_at", s).lt("created_at", e))
    failed_total = _count(q("processing_queue").eq("status", "failed"))
    new_rest = _count(q("restaurants").gte("created_at", s).lt("created_at", e))
    review = _count(q("restaurants").eq("needs_review", True))
    visible = _count(q("restaurants").eq("is_visible", True))

    tok_in = tok_out = calls = 0
    if USAGE_LOG.exists():
        for line in USAGE_LOG.read_text(encoding="utf-8").splitlines():
            try:
                u = json.loads(line)
            except json.JSONDecodeError:
                continue
            if u.get("at", "").startswith(day.isoformat()):
                calls += 1
                tok_in += u.get("input_tokens", 0)
                tok_out += u.get("output_tokens", 0)

    return "\n".join([
        f"# MukMap 일일 리포트 {day.isoformat()}",
        "",
        "## 처리",
        f"- 가게 나온 영상: {by_status['done']}",
        f"- 가게 없는 영상: {by_status['no_restaurant']}",
        f"- 자막 없는 영상: {by_status['no_transcript']}",
        f"- 추출 실패: {failed} (누적 {failed_total})",
        "",
        "## 가게",
        f"- 새 가게: {new_rest}",
        f"- 검수 대기 전체: {review}",
        f"- 사이트에 보이는 가게: {visible}",
        "",
        "## 토큰 (claude -p 구독)",
        f"- 호출: {calls}",
        f"- 입력 {tok_in:,} / 출력 {tok_out:,}",
        "",
    ])


def main():
    p = argparse.ArgumentParser(description="MukMap 일일 리포트")
    p.add_argument("--date", help="YYYY-MM-DD (기본: 어제 KST)")
    args = p.parse_args()
    day = date.fromisoformat(args.date) if args.date else datetime.now(KST).date() - timedelta(days=1)
    text = build(day)
    out = ROOT / f"rawdata/reports/daily-{day.isoformat()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
