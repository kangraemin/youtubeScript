#!/usr/bin/env python3
"""stdin/argv로 받은 summary JSON을 transcripts.summary에 UPDATE.

사용법:
    echo '<summary JSON>' | python3 scripts/save_summary.py <vid>

summary JSON에 `_model` 키가 있으면 분리해서 summary_model 컬럼에 저장.
summarized_at은 현재 UTC 시각으로 자동 채움.

`"schema": "v3"` 요약은 저장 전에 prompts/summary-guidelines.md의 "저장 전 자체 검증"을
기계 검증한다. 위반이 있으면 저장하지 않고 위반 목록을 stderr에 내고 exit 2.
(schema 키가 없는 v2 요약은 검증 없이 그대로 저장 — 기존 절차 호환)
"""
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.supabase_client import get_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

V3_CONTENT_TYPES = {"market_brief", "interview", "deep_analysis", "explainer",
                    "news_digest", "entertainment", "clip"}
V3_SHORT_TYPES = {"entertainment", "clip"}
POSITION_ACTIONS = {"buy", "sell", "add", "reduce", "hold", "plan_buy", "plan_sell"}
# 가이드라인 목표치(tldr 120자·quote 150자)보다 조금 느슨하게 막는다.
# 모델이 글자 수를 정확히 못 세서 목표치로 막으면 재시도만 늘고 품질 차이는 없다.
TLDR_MAX = 150
QUOTE_MAX = 180
OUTPUT_RATIO_MAX = 0.25
# 짧은 영상은 25%가 너무 작다. 손으로 쓴 v3 모범 샘플(12분·원문 4,856자)도 3,429자였다 —
# JSON 키·ts만으로 수백 자가 든다. 바닥 4,000자를 두고, 25%는 긴 라이브의 비대화를 막는 데 쓴다.
OUTPUT_FLOOR = 4000
CHAPTER_COVERAGE = 0.85
COVERAGE_MIN_SEC = 180  # 3분 미만은 chapters 커버리지를 보지 않는다

_TS_LINE = re.compile(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s?(.*)$")


def _ts_sec(ts: str):
    try:
        parts = [int(x) for x in str(ts).strip().split(":")]
    except ValueError:
        return None
    if not 2 <= len(parts) <= 3:
        return None
    sec = 0
    for x in parts:
        sec = sec * 60 + x
    return sec


def _norm(text: str) -> str:
    # 자동 자막은 문장부호·띄어쓰기가 들쭉날쭉하다. 글자·숫자만 남겨 비교한다.
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text or "")


def _parse_transcript(raw: str):
    """(본문 텍스트, 마지막 타임스탬프 초) — 헤더(제목·URL·video_id)는 버린다."""
    texts, last = [], None
    for line in raw.splitlines():
        m = _TS_LINE.match(line.strip())
        if not m:
            continue
        sec = _ts_sec(m.group(1))
        if sec is not None:
            last = sec
        texts.append(m.group(2))
    return " ".join(texts), last


def find_transcript(vid: str):
    for path in [f"/tmp/summarize_target_{vid}.txt",
                 *glob.glob(os.path.join(ROOT, "rawdata", "transcripts", "*", f"{vid}.txt"))]:
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            with open(path, encoding="utf-8") as f:
                return f.read()
    return None


def _quotes(summary: dict):
    """(위치, quote) 목록 — 모든 섹션의 quote 필드."""
    out = []
    for key in ("key_points", "positions"):
        for i, it in enumerate(summary.get(key) or []):
            if isinstance(it, dict) and it.get("quote"):
                out.append((f"{key}[{i}]", it["quote"]))
    return out


def validate_v3(summary: dict, transcript_raw) -> list:
    errs = []
    if summary.get("content_type") not in V3_CONTENT_TYPES:
        errs.append(f"content_type은 {sorted(V3_CONTENT_TYPES)} 중 하나여야 함: {summary.get('content_type')!r}")
    short = summary.get("content_type") in V3_SHORT_TYPES

    tldr = summary.get("tldr")
    if not isinstance(tldr, str) or not tldr.strip():
        errs.append("tldr 필수")
    elif len(tldr) > TLDR_MAX:
        errs.append(f"tldr {len(tldr)}자 — {TLDR_MAX}자 이내로 줄일 것(목표 120자)")

    wg = summary.get("watch_guide")
    if not isinstance(wg, dict) or wg.get("verdict") not in {"skip", "skim", "watch"} or not wg.get("why"):
        errs.append("watch_guide는 {verdict: skip|skim|watch, why} 필수")

    kps = summary.get("key_points")
    lo, hi = (1, 3) if short else (1, 10)
    if not isinstance(kps, list) or not lo <= len(kps) <= hi:
        errs.append(f"key_points {lo}~{hi}개 필요 (현재 {len(kps) if isinstance(kps, list) else 0})")
    else:
        for i, kp in enumerate(kps):
            if not isinstance(kp, dict) or not kp.get("point"):
                errs.append(f"key_points[{i}].point 필수")

    for i, p in enumerate(summary.get("positions") or []):
        if not isinstance(p, dict):
            continue
        if p.get("action") not in POSITION_ACTIONS:
            errs.append(f"positions[{i}].action은 {sorted(POSITION_ACTIONS)} 중 하나: {p.get('action')!r}")
        if not p.get("quote"):
            errs.append(f"positions[{i}].quote 필수 — 매매 근거 발화가 없으면 positions가 아니라 key_points로")

    for key, cap in (("numbers", 8), ("terms", 5), ("takeaways", 5)):
        n = len(summary.get(key) or [])
        if n > cap:
            errs.append(f"{key} {n}개 — 최대 {cap}개")

    quotes = _quotes(summary)
    seen = {}
    for where, q in quotes:
        if len(q) > QUOTE_MAX:
            errs.append(f"{where}.quote {len(q)}자 — {QUOTE_MAX}자 이내 근거 1개만(목표 150자)")
        k = _norm(q)
        if k in seen:
            errs.append(f"{where}.quote가 {seen[k]}와 중복 — 같은 quote는 한 항목에만")
        else:
            seen[k] = where

    if transcript_raw is None:
        print("v3 검증: transcript를 찾지 못해 원문 대조·분량·커버리지 검사는 건너뜀", file=sys.stderr)
        return errs

    body, last_sec = _parse_transcript(transcript_raw)
    body_norm = _norm(body)
    for where, q in quotes:
        if _norm(q) and _norm(q) not in body_norm:
            errs.append(f"{where}.quote가 transcript에 없음 — 원문 그대로 옮길 것: {q[:60]!r}")

    out_len = len(json.dumps(summary, ensure_ascii=False))
    limit = max(int(len(body) * OUTPUT_RATIO_MAX), OUTPUT_FLOOR)
    if out_len > limit:
        errs.append(f"출력 {out_len}자 > 상한 {limit}자(원문 {len(body)}자의 25%) — 항목·detail을 줄일 것")

    if not short and last_sec and last_sec >= COVERAGE_MIN_SEC:
        chs = [_ts_sec(c.get("ts")) for c in (summary.get("chapters") or []) if isinstance(c, dict)]
        chs = [c for c in chs if c is not None]
        need = int(last_sec * CHAPTER_COVERAGE)
        if not chs:
            errs.append("chapters 필수(5~15개)")
        elif max(chs) < need:
            errs.append(f"chapters 마지막 ts {max(chs)}s < 영상 길이 {last_sec}s의 85%({need}s) — 후반부까지 읽고 chapters를 채울 것")
    return errs


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: save_summary.py <vid>  (stdin에 summary JSON)", file=sys.stderr)
        return 1

    vid = sys.argv[1]
    raw = sys.stdin.read()
    summary = json.loads(raw)
    model = summary.pop("_model", "claude-sonnet-4-6")

    if summary.get("schema") == "v3":
        errs = validate_v3(summary, find_transcript(vid))
        if errs:
            print(f"v3 검증 실패 ({vid}) — 저장하지 않음:", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
            return 2

    db = get_client()
    db.table("transcripts").update({
        "summary": summary,
        "summarized_at": datetime.now(timezone.utc).isoformat(),
        "summary_model": model,
    }).eq("vid", vid).execute()

    # 새 요약 반영 — 홈/latest 캐시 무효화 (실패해도 저장은 유지)
    try:
        import urllib.parse
        import urllib.request

        base = os.environ.get("REVALIDATE_URL")
        sec = os.environ.get("REVALIDATE_SECRET")
        if base and sec:
            u = f"{base.rstrip('/')}/api/revalidate?secret={urllib.parse.quote(sec)}"
            urllib.request.urlopen(
                urllib.request.Request(u, method="POST"), timeout=8
            ).read()
    except Exception as e:
        print(f"revalidate skip: {e}", file=sys.stderr)

    print(f"saved: {vid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
