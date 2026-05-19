#!/usr/bin/env python3
"""YouTube transcript crawler using Playwright.

Usage:
    python scripts/crawl_youtube_transcripts.py --channel dulcinea_studio --days 7 --max-videos 5
    python scripts/crawl_youtube_transcripts.py --channel all --headless
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

from googleapiclient.discovery import build
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.channel_config import policy_for, category_of

CHANNELS = [
    {"id": "UCehQiKylaW68H_OtRS36wGQ", "slug": "dulcinea_studio",   "name": "둘시네아",            "tab": "videos"},
    {"id": "UCfpaSruWW3S4dibonKXENjA", "slug": "tzuyang",            "name": "쯔양",               "tab": "videos"},
    {"id": "UCzgpOnor-MzT-1iflZil2GQ", "slug": "jaesunrang",         "name": "재선랑",             "tab": "videos"},
    {"id": "UC-OAmhcFgX9t_OF6fQ-4B1w", "slug": "kimjjamppong",       "name": "김쨈뽕",            "tab": "videos"},
    {"id": "UC-x55HF1-IilhxZOzwJm7JA", "slug": "kimsawon",           "name": "김사원",             "tab": "videos"},
    {"id": "UCJo6G1u0e_-wS-JQn3T-zEw", "slug": "moneycomics",        "name": "머니코믹스",         "tab": "videos"},
    {"id": "UCsJ6RuBiTVWRX156FVbeaGg", "slug": "shukaworld",         "name": "슈카월드",           "tab": "videos", "handle": "syukaworld"},
    {"id": "UChlv4GSd7OQl3js-jkLOnFA", "slug": "sampro_tv",          "name": "삼프로TV",           "tab": "videos"},
    {"id": "UCA_hgsFzmynpv1zkvA5A7jA", "slug": "jisik_inside",       "name": "지식인사이드",       "tab": "videos"},
    {"id": "UC6kZpTl39-_SqfBrF1-N2oQ", "slug": "yonhap_economy",     "name": "연합뉴스경제TV",     "tab": "videos"},
    {"id": "UCvrOll07bwpNzGhBHRB5_yw", "slug": "developmong",        "name": "웅덩이매수디벨롭몽", "tab": "videos"},
    {"id": "",                           "slug": "doniggangpae",       "name": "돈이깡패다",          "tab": "videos", "handle": "돈이깡패다"},
    {"id": "UCIipmgxpUxDmPP-ma3Ahvbw", "slug": "mk_wallstreet",      "name": "매경 월가월부",      "tab": "videos"},
    {"id": "UChY8VUjXv0aA7RF9hDQ0ISg", "slug": "sbs_gyoyangi",       "name": "교양이를 부탁해",    "tab": "videos"},
]


def parse_args():
    p = argparse.ArgumentParser(description="YouTube transcript crawler (Playwright)")
    p.add_argument("--channel", default="all",
                   help="Channel slug(s), comma-separated, or 'all' (default: all)")
    p.add_argument("--days", type=int, default=0,
                   help="Only collect videos uploaded within N days (0 = no limit)")
    p.add_argument("--max-videos", type=int, default=0,
                   help="Max videos per channel (0 = no limit)")
    p.add_argument("--headless", action="store_true",
                   help="Run in headless mode (default: show browser window)")
    p.add_argument("--output-dir", default="rawdata/transcripts",
                   help="Output directory (default: rawdata/transcripts)")
    p.add_argument("--no-skip-existing", action="store_true",
                   help="Re-collect even if transcript txt already exists")
    p.add_argument("--workers", type=int, default=3,
                   help="병렬 처리 worker 수 (기본: 3)")
    return p.parse_args()


def filter_channels(channel_arg: str) -> list[dict]:
    if channel_arg == "all":
        return CHANNELS
    slugs = [s.strip() for s in channel_arg.split(",")]
    result = []
    slug_set = {ch["slug"] for ch in CHANNELS}
    for slug in slugs:
        if slug not in slug_set:
            print(f"[ERROR] Unknown channel slug: '{slug}'", file=sys.stderr)
            print(f"  Available: {', '.join(sorted(slug_set))}", file=sys.stderr)
            sys.exit(1)
        result.append(next(ch for ch in CHANNELS if ch["slug"] == slug))
    return result


def _load_env_key(env_file: str, key: str) -> str:
    env_path = Path(__file__).parent.parent / env_file
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise ValueError(f"{key} not found in env or {env_file}")


import re as _re


def _iso_dur_sec(iso: str) -> int:
    """ISO8601 duration(PT#H#M#S) → 초. None/매치실패 시 0."""
    m = _re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "PT0S")
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def _filter_by_min_duration(youtube, videos: list, min_sec: int, ch: dict) -> list:
    """videos.list contentDetails로 duration 조회 → min_sec 미만(쇼츠/단편) 제외."""
    vids = [v["vid"] for v in videos]
    keep_ids = set()
    for i in range(0, len(vids), 50):
        chunk = vids[i:i + 50]
        resp = youtube.videos().list(
            part="contentDetails", id=",".join(chunk)
        ).execute()
        for it in resp.get("items", []):
            if _iso_dur_sec(it["contentDetails"]["duration"]) >= min_sec:
                keep_ids.add(it["id"])
    kept = [v for v in videos if v["vid"] in keep_ids]
    print(f"[{ch['name']}] 쇼츠/단편 필터: {len(videos)} → {len(kept)}개 "
          f"(min_duration_sec={min_sec})", flush=True)
    return kept


def get_channel_videos_api(youtube, ch: dict, max_videos: int, days_limit: int) -> list[dict]:
    """YouTube Data API v3으로 채널 영상/스트림 목록 수집."""
    cutoff = None
    if days_limit > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_limit)

    channel_id = ch["id"]

    if not channel_id:
        handle = ch.get("handle", "")
        resp = youtube.channels().list(part="id", forHandle=handle).execute()
        items = resp.get("items", [])
        if not items:
            print(f"  [API] handle '{handle}' 채널 찾기 실패", flush=True)
            return []
        channel_id = items[0]["id"]
        print(f"  [API] handle '{handle}' → {channel_id}", flush=True)

    tab = ch.get("tab", "videos")
    videos = []

    def _finalize(vs: list) -> list:
        min_dur = policy_for(ch["slug"]).get("min_duration_sec", 0)
        if min_dur > 0 and vs:
            return _filter_by_min_duration(youtube, vs, min_dur, ch)
        return vs

    if tab == "streams":
        req = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            type="video",
            eventType="completed",
            maxResults=50,
            order="date",
        )
        while req:
            resp = req.execute()
            for item in resp.get("items", []):
                vid = item["id"]["videoId"]
                title = item["snippet"]["title"]
                published_at = item["snippet"]["publishedAt"]
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                if cutoff and pub_dt < cutoff:
                    return _finalize(videos)
                videos.append({"url": f"https://www.youtube.com/watch?v={vid}", "vid": vid, "title": title, "meta": published_at[:10], "channel": ch["name"]})
                if max_videos > 0 and len(videos) >= max_videos:
                    return _finalize(videos)
            req = youtube.search().list_next(req, resp)
    else:
        uploads_id = "UU" + channel_id[2:]
        req = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_id,
            maxResults=50,
        )
        while req:
            resp = req.execute()
            for item in resp.get("items", []):
                snippet = item["snippet"]
                vid = snippet["resourceId"]["videoId"]
                title = snippet["title"]
                published_at = snippet["publishedAt"]
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                if cutoff and pub_dt < cutoff:
                    return _finalize(videos)
                videos.append({"url": f"https://www.youtube.com/watch?v={vid}", "vid": vid, "title": title, "meta": published_at[:10], "channel": ch["name"]})
                if max_videos > 0 and len(videos) >= max_videos:
                    return _finalize(videos)
            req = youtube.playlistItems().list_next(req, resp)

    return _finalize(videos)


def _ts_to_seconds(ts: str) -> int | None:
    """'M:SS' 또는 'H:MM:SS' → 초. 파싱 불가 시 None."""
    parts = (ts or "").strip().split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return None


def dedup_segments(segments: list[dict]) -> list[dict]:
    """패널 N배 마운트로 [전체S][전체S...] 형태로 수집된 세그먼트에서
    타임스탬프가 되돌아가는 첫 지점(= 중복 사이클 시작) 이전까지만 keep.
    정상 transcript는 타임스탬프 단조 비감소이므로 무변경."""
    if not segments:
        return segments
    prev = -1
    for i, seg in enumerate(segments):
        sec = _ts_to_seconds(seg.get("timestamp", ""))
        if sec is None:
            continue
        if sec < prev:                 # 타임스탬프 역행 = 중복 사이클 진입
            return segments[:i]
        prev = sec
    return segments


def get_transcript(page, vid: str) -> list[dict] | None:
    """Open video, click transcript button, extract segments.

    Selector strategy (confirmed via live DOM inspection 2026-05):
    1. button[aria-label="스크립트 표시"]  — description 패널 내 직접 노출 버튼
    2. "추가 작업" 버튼 클릭 후 메뉴에서 "스크립트 열기" 항목 클릭
    3. ytd-video-description-transcript-section-renderer 내 첫 번째 button
    """
    try:
        page.goto(f"https://www.youtube.com/watch?v={vid}", wait_until="domcontentloaded", timeout=30000)
    except Exception:
        return None
    time.sleep(3)

    # Step 1: 설명란 더보기 펼치기 (스크립트 표시 버튼이 숨어있을 수 있음)
    for expand_sel in [
        "tp-yt-paper-button#expand",
        "ytd-text-inline-expander #expand",
        "#description-inline-expander #expand",
    ]:
        try:
            el = page.query_selector(expand_sel)
            if el and el.is_visible():
                el.click()
                time.sleep(1)
                break
        except Exception:
            continue

    # Step 2: "스크립트 표시" 버튼 직접 클릭 (가장 신뢰도 높음)
    clicked = False
    direct_selectors = [
        'button[aria-label="스크립트 표시"]',
        'button[aria-label="Show transcript"]',
    ]
    for sel in direct_selectors:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                clicked = True
                print(f"    [transcript] clicked via: {sel}")
                break
        except Exception:
            continue

    # Step 3: "추가 작업" 메뉴 → "스크립트 열기"
    if not clicked:
        more_selectors = [
            'button[aria-label="추가 작업"]',
            'button[aria-label="More actions"]',
        ]
        for more_sel in more_selectors:
            try:
                more_btns = page.query_selector_all(more_sel)
                # description 영역에 있는 버튼 우선 (처음 1~2개가 player 영역)
                target = more_btns[1] if len(more_btns) >= 2 else (more_btns[0] if more_btns else None)
                if target and target.is_visible():
                    target.click()
                    time.sleep(1)
                    # 메뉴 항목 탐색
                    for item_sel in [
                        'ytd-menu-service-item-renderer yt-formatted-string:has-text("스크립트")',
                        'tp-yt-paper-item:has-text("스크립트")',
                        'yt-formatted-string:has-text("스크립트 열기")',
                        'yt-formatted-string:has-text("Open transcript")',
                    ]:
                        try:
                            item = page.query_selector(item_sel)
                            if item and item.is_visible():
                                item.click()
                                clicked = True
                                print(f"    [transcript] clicked via menu: {item_sel}")
                                break
                        except Exception:
                            continue
                    if clicked:
                        break
                    # 메뉴 못 찾으면 Escape로 닫기
                    page.keyboard.press("Escape")
                    time.sleep(0.5)
            except Exception:
                continue

    # Step 4: ytd-video-description-transcript-section-renderer 내 버튼 fallback
    if not clicked:
        try:
            btn = page.query_selector("ytd-video-description-transcript-section-renderer button")
            if btn and btn.is_visible():
                btn.click()
                clicked = True
                print("    [transcript] clicked via transcript-section-renderer")
        except Exception:
            pass

    if not clicked:
        print(f"    [transcript] no transcript button found for {vid}")
        return None

    # 패널 로드 대기 — 신 UI(transcript-segment-view-model) 우선, 구 UI fallback
    panel_loaded = False
    matched_sel = None
    for seg_sel in [
        "transcript-segment-view-model",           # 신 YouTube UI
        "ytd-transcript-segment-renderer",          # 구 YouTube UI
        "ytd-transcript-body-renderer ytd-transcript-segment-renderer",
    ]:
        try:
            page.wait_for_selector(seg_sel, timeout=45000)
            panel_loaded = True
            matched_sel = seg_sel
            break
        except PlaywrightTimeout:
            continue

    if not panel_loaded:
        print(f"    [transcript] panel did not load for {vid}")
        return None

    result = []
    if matched_sel == "transcript-segment-view-model":
        # 신 YouTube UI
        segments = page.query_selector_all("transcript-segment-view-model")
        for seg in segments:
            try:
                ts_el = seg.query_selector(".ytwTranscriptSegmentViewModelTimestamp")
                text_el = seg.query_selector("span.ytAttributedStringHost")
                if not ts_el or not text_el:
                    continue
                ts = ts_el.inner_text().strip()
                text = text_el.inner_text().strip()
                if text:
                    result.append({"timestamp": ts, "text": text})
            except Exception:
                continue
    else:
        # 구 YouTube UI
        segments = page.query_selector_all("ytd-transcript-segment-renderer")
        for seg in segments:
            try:
                ts_el = seg.query_selector(".segment-timestamp")
                text_el = seg.query_selector(".segment-text")
                if not ts_el or not text_el:
                    continue
                ts = ts_el.inner_text().strip()
                text = text_el.inner_text().strip()
                if text:
                    result.append({"timestamp": ts, "text": text})
            except Exception:
                continue
    return dedup_segments(result) or None


def save_transcript(out_dir: str, slug: str, vid: str, title: str, url: str, segments: list[dict]):
    path = Path(out_dir) / slug / f"{vid}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    lines = [title, url, f"video_id: {vid}", f"collected_at: {collected_at}", ""]
    for s in segments:
        lines.append(f"{s['timestamp']} {s['text']}")
    path.write_text("\n".join(lines), encoding="utf-8")


def save_list_json(out_dir: str, slug: str, videos: list[dict]):
    if not videos:
        return
    path = Path(out_dir) / slug / "_list.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    entries = [{**v, "collected_at": collected_at} for v in videos]
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def process_channel(ch, headless, output_dir, max_videos, days, skip_existing):
    prefix = f"[{ch['name']}]"
    api_key = os.environ.get("YOUTUBE_API_KEY") or _load_env_key(".env.local", "YOUTUBE_API_KEY")
    youtube = build("youtube", "v3", developerKey=api_key)

    # CLI --days > 0 이면 override, 아니면 카테고리 정책
    effective_days = days if days > 0 else policy_for(ch["slug"])["days"]
    cat = category_of(ch["slug"])

    print(f"\n{prefix} ===== {ch['slug']} (category={cat}, days={effective_days}) =====", flush=True)
    videos = get_channel_videos_api(youtube, ch, max_videos, effective_days)
    print(f"{prefix} 수집 영상: {len(videos)}개", flush=True)

    keyword = ch.get("keyword")
    if keyword:
        before = len(videos)
        videos = [v for v in videos if keyword in v.get("title", "")]
        print(f"{prefix} keyword 필터 '{keyword}': {before} → {len(videos)}개", flush=True)
    save_list_json(output_dir, ch["slug"], videos)

    ok = skip = fail = 0
    total = len(videos)

    videos_to_crawl = [
        v for v in videos
        if not (skip_existing and (Path(output_dir) / ch["slug"] / f"{v['vid']}.txt").exists())
    ]
    skip = total - len(videos_to_crawl)

    if videos_to_crawl:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            for i, v in enumerate(videos_to_crawl, 1):
                segments = get_transcript(page, v["vid"])
                if segments:
                    save_transcript(output_dir, ch["slug"], v["vid"], v["title"], v["url"], segments)
                    ok += 1
                else:
                    fail += 1
                if (ok + fail) % 10 == 0:
                    print(f"{prefix} 진행 {i}/{len(videos_to_crawl)} (ok={ok} skip={skip} fail={fail})", flush=True)
            context.close()
            browser.close()

    print(f"{prefix} 완료: ok={ok} skip={skip} fail={fail}", flush=True)
    return {"slug": ch["slug"], "ok": ok, "skip": skip, "fail": fail}


def main():
    args = parse_args()
    channels = filter_channels(args.channel)
    skip_existing = not args.no_skip_existing
    workers = min(args.workers, len(channels))
    print(f"총 {len(channels)}개 채널, {workers} workers로 병렬 실행")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                process_channel, ch, args.headless, args.output_dir,
                args.max_videos, args.days, skip_existing
            ): ch for ch in channels
        }
        for future in as_completed(futures):
            ch = futures[future]
            try:
                r = future.result()
                print(f"[완료] {r['slug']}: ok={r['ok']} skip={r['skip']} fail={r['fail']}")
            except Exception as e:
                print(f"[실패] {ch['slug']}: {e}")

    print("\nALL DONE")


if __name__ == "__main__":
    main()
