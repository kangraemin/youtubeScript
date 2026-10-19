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

# 자막 패널 세그먼트 셀렉터 — 신 UI 우선. 구 UI는 body renderer 하위도 이 셀렉터로 잡힌다.
SEGMENT_SELECTORS = [
    "transcript-segment-view-model",    # 신 YouTube UI
    "ytd-transcript-segment-renderer",  # 구 YouTube UI
]
PANEL_TIMEOUT_MS = 12_000
# 연속 실패 N건이면 채널 조기 종료. 런 초반 정상 → 중반부터 전건 실패는 소프트 스로틀 시그니처라
# 계속 때려도 수집량은 늘지 않고 차단 지속시간과 락 점유만 늘어난다.
CONSEC_FAIL_LIMIT = 8
# 같은 영상이 이 횟수만큼 실패하면 크롤 대상에서 뺀다. 자막이 아예 없는 영상을 매 회차 다시 때리지 않기 위해서다.
# 빠진 영상은 <slug>/_failed.json에 남고, 먹방 채널은 whisper_fallback.py가 오디오로 받는다.
GIVEUP_FAILS = 3
# 런 전체 상한(분). 건당 타임아웃만으론 회차 길이가 유계가 아니라서(실패 139건 × 135초 = 5시간+)
# 공유 락을 7시간 넘게 쥐고 2시간 cron을 전부 스킵시켰다(2026-10-03).
DEFAULT_RUN_MINUTES = 90

from scripts.channel_config import CHANNELS  # noqa: E402 — 채널 정의는 channel_config 한 곳에만 둔다


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
    p.add_argument("--max-minutes", type=int, default=DEFAULT_RUN_MINUTES,
                   help="런 전체 상한(분). 넘으면 남은 영상은 다음 회차로 (0 = 무제한)")
    p.add_argument("--workers", type=int, default=3,
                   help="병렬 처리 worker 수 (기본: 3)")
    p.add_argument("--dry-list", action="store_true",
                   help="영상 목록만 세고 끝낸다(자막 수집·_list.json 저장 안 함)")
    p.add_argument("--crawl-cap", type=int, default=0,
                   help="채널당 이번 회차에 새로 받을 영상 수 상한 (0 = 정책값/무제한). 며칠에 나눠 받는 백필용")
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


def _attach_duration(youtube, videos: list, min_sec: int, ch: dict) -> list:
    """videos.list로 duration을 조회해 각 항목에 duration_sec을 붙이고,
    min_sec > 0이면 그 미만(쇼츠/단편)을 제외한다.

    duration은 필터가 꺼진 채널에서도 조회한다 — 웹 쇼츠 필터가 길이를 쓰기 때문.
    videos 항목은 save_list_json이 그대로 _list.json에 쓰므로 upload까지 자동 전파된다.
    videos.list는 50개당 1 unit이라 quota 부담이 거의 없다.
    """
    vids = [v["vid"] for v in videos]
    dur: dict[str, int] = {}
    for i in range(0, len(vids), 50):
        resp = youtube.videos().list(
            part="contentDetails", id=",".join(vids[i:i + 50])
        ).execute()
        for it in resp.get("items", []):
            dur[it["id"]] = _iso_dur_sec(it["contentDetails"]["duration"])

    for v in videos:
        v["duration_sec"] = dur.get(v["vid"], -1)  # -1 = 조회 불가(삭제·비공개)

    kept = [v for v in videos if min_sec <= 0 or v["duration_sec"] >= min_sec]
    if min_sec > 0:
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
    title_include = ch.get("title_include")
    videos = []

    def _finalize(vs: list) -> list:
        if not vs:
            return vs
        min_dur = policy_for(ch["slug"]).get("min_duration_sec", 0)
        return _attach_duration(youtube, vs, min_dur, ch)

    if tab == "streams":
        req = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            type="video",
            eventType="completed",
            maxResults=50,
            order="date",
        )
        # search는 order=date로 정렬을 요청하지만 라이브 완료본은 publishedAt이 실제
        # 방송일과 어긋나는 경우가 있어 여기서도 조기 return 대신 연속 카운트로 끊는다.
        STALE_RUN_LIMIT = 200
        stale_run = 0
        while req:
            resp = req.execute()
            for item in resp.get("items", []):
                vid = item["id"]["videoId"]
                title = item["snippet"]["title"]
                published_at = item["snippet"]["publishedAt"]
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                # 시리즈만 받는 채널(먹을텐데). max_videos보다 먼저 걸러야 상한이 시리즈 기준이 된다.
                if title_include and title_include not in title:
                    continue
                if cutoff and pub_dt < cutoff:
                    stale_run += 1
                    if stale_run >= STALE_RUN_LIMIT:
                        return _finalize(videos)
                    continue
                stale_run = 0
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
        # uploads 플레이리스트는 대체로 최신순이지만 정렬이 보장되지 않는다.
        # 특히 라이브는 예약 생성 시각이 publishedAt이 되기도 해서 순서가 뒤섞인다.
        # 예전엔 cutoff 미달을 하나 만나면 바로 return했는데, 그 탓에 알상무는 9번째 항목
        # 하나 때문에 30일치 92건 중 8건만 받고 끝났다(2026-09-01 확인).
        # 이제는 건너뛰되, 연속으로 오래된 항목이 이어지면 그때 멈춘다.
        STALE_RUN_LIMIT = 200  # 50개짜리 4페이지 연속으로 cutoff 밖이면 과거 구간으로 판단
        stale_run = 0
        while req:
            resp = req.execute()
            for item in resp.get("items", []):
                snippet = item["snippet"]
                vid = snippet["resourceId"]["videoId"]
                title = snippet["title"]
                published_at = snippet["publishedAt"]
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                # 시리즈만 받는 채널(먹을텐데). max_videos보다 먼저 걸러야 상한이 시리즈 기준이 된다.
                if title_include and title_include not in title:
                    continue
                if cutoff and pub_dt < cutoff:
                    stale_run += 1
                    if stale_run >= STALE_RUN_LIMIT:
                        return _finalize(videos)
                    continue
                stale_run = 0
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


TIMEDTEXT_WAIT_TICKS = 30  # 0.5s × 30 = 최대 15초 (광고 감기 + CC 요청 왕복)

# 반환: "ad"(광고 감는 중) / "cc"(CC를 방금 켬) / "wait"
_PLAYER_NUDGE_JS = """(ccClicked) => {
  const player = document.querySelector('#movie_player');
  const v = document.querySelector('video');
  if (player && player.classList.contains('ad-showing')) {
    const skip = document.querySelector('.ytp-skip-ad-button, .ytp-ad-skip-button, .ytp-ad-skip-button-modern');
    if (skip) skip.click();
    if (v && isFinite(v.duration) && v.duration > 0) v.currentTime = v.duration;
    return 'ad';
  }
  const cc = document.querySelector('.ytp-subtitles-button');
  if (!ccClicked && cc && cc.getAttribute('aria-pressed') === 'false') { cc.click(); return 'cc'; }
  return 'wait';
}"""


def _fmt_ts(sec: float) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def segments_from_json3(data: dict, chunk_sec: float = 5.0) -> list[dict]:
    """플레이어 timedtext(fmt=json3) 응답 → 패널과 같은 {timestamp, text} 세그먼트.

    ASR 자막은 단어 단위 이벤트라 그대로 쓰면 줄 수가 패널의 3배가 된다.
    chunk_sec 단위로 묶어 패널 세그먼트와 비슷한 밀도로 맞춘다.
    """
    out: list[dict] = []
    cur_start = None
    buf: list[str] = []
    for ev in (data or {}).get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(sg.get("utf8", "") for sg in segs).replace("\n", " ").strip()
        if not text:
            continue
        start = ev.get("tStartMs", 0) / 1000
        if cur_start is None:
            cur_start = start
        elif start - cur_start >= chunk_sec:
            out.append({"timestamp": _fmt_ts(cur_start), "text": " ".join(buf)})
            cur_start, buf = start, []
        buf.append(text)
    if buf:
        out.append({"timestamp": _fmt_ts(cur_start), "text": " ".join(buf)})
    return out


def _fetch_via_api(vid: str) -> list[dict] | None:
    """youtube-transcript-api로 자막을 받는다(브라우저 없이). 실패하면 None → Playwright 경로로 넘어간다.

    YouTube가 이 경로의 IP를 막아도(RequestBlocked 등) 예외를 삼켜 수집이 멈추지 않게 한다.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        segs = YouTubeTranscriptApi().fetch(vid, languages=["ko", "a.ko", "ko-KR"])
    except Exception as e:
        print(f"    [transcript] api 실패 {vid}: {type(e).__name__}", flush=True)
        return None
    out = [{"timestamp": _fmt_ts(s.start), "text": s.text.replace("\n", " ").strip()} for s in segs]
    out = [s for s in out if s["text"]]
    return out or None


def get_transcript(page, vid: str) -> list[dict] | None:
    """youtube-transcript-api를 먼저 시도하고, 안 되면 스크립트 패널 → 플레이어 timedtext 순으로 받는다.

    page가 None이면 API 경로만 쓴다(브라우저를 띄우지 않는 회차).
    """
    segs = _fetch_via_api(vid)
    if segs:
        return segs
    if page is None:
        return None
    return _get_transcript_browser(page, vid)


def _get_transcript_browser(page, vid: str) -> list[dict] | None:
    """스크립트 패널로 수집하고, 패널이 실패하면 플레이어 timedtext 응답으로 대체한다.

    2026-10-06 실측: 소프트 스로틀 때 막히는 건 패널의 youtubei/v1/get_transcript
    (400 FAILED_PRECONDITION)뿐이고, 패널을 여는 순간 플레이어가 부르는
    /api/timedtext(fmt=json3)는 200으로 전체 자막을 준다. 직접 API를 치는 게 아니라
    페이지가 스스로 받은 응답을 엿듣는 것이라 별도 요청이 늘지 않는다.
    광고 자막도 같은 경로로 오므로 v= 가 이 영상인 응답만 쓴다.
    """
    captured: dict = {}

    def on_response(resp):
        url = resp.url
        if "/api/timedtext" not in url:
            return
        try:
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(url).query)
            if qs.get("v", [None])[0] != vid or qs.get("fmt", [None])[0] != "json3":
                return
            data = resp.json()
            if any(ev.get("segs") for ev in data.get("events", [])):
                captured["json3"] = data
        except Exception:
            pass

    page.on("response", on_response)
    try:
        result = _get_transcript_panel(page, vid)
        if result:
            return result
        # 플레이어는 (1) 본편이 재생 중이고 (2) 자막(CC)이 켜져 있을 때만 본편 timedtext를 받는다.
        # 광고가 돌면 광고 자막만 오고, CC가 꺼진 영상은 아예 요청이 없다(실측).
        # 광고는 끝으로 감고, 본편이 나오면 CC를 한 번 켜서 요청을 유도한다.
        cc_clicked = False
        for _ in range(TIMEDTEXT_WAIT_TICKS):
            if "json3" in captured:
                break
            try:
                state = page.evaluate(_PLAYER_NUDGE_JS, cc_clicked)
                if state == "cc":
                    cc_clicked = True
            except Exception:
                pass
            time.sleep(0.5)
        if "json3" in captured:
            segs = dedup_segments(segments_from_json3(captured["json3"]))
            if segs:
                print(f"    [transcript] fallback via timedtext: {len(segs)} segments")
                return segs
        return None
    finally:
        page.remove_listener("response", on_response)


def _get_transcript_panel(page, vid: str) -> list[dict] | None:
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

    # 패널 로드 대기 — 셀렉터를 콤마로 묶어 1회만 기다린다. 예전엔 3개를 45초씩 순차 대기해
    # 소프트 스로틀(런 중반부터 세그먼트가 안 옴) 상태에서 실패 1건이 135초를 태웠다.
    try:
        page.wait_for_selector(", ".join(SEGMENT_SELECTORS), timeout=PANEL_TIMEOUT_MS)
    except PlaywrightTimeout:
        print(f"    [transcript] panel did not load for {vid}")
        return None
    # 신 UI가 있으면 신 UI 파서, 아니면 구 UI 파서
    matched_sel = (
        "transcript-segment-view-model"
        if page.query_selector("transcript-segment-view-model")
        else "ytd-transcript-segment-renderer"
    )

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
    # 원자적 교체 — upload가 크롤과 독립 스케줄로 돌므로 반쯤 쓴 파일을 읽으면 안 된다
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_failed(out_dir: str, slug: str) -> dict:
    path = Path(out_dir) / slug / "_failed.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_failed(out_dir: str, slug: str, failed: dict):
    path = Path(out_dir) / slug / "_failed.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(failed, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def process_channel(ch, headless, output_dir, max_videos, days, skip_existing, deadline=None,
                    dry_list=False, crawl_cap=0):
    prefix = f"[{ch['name']}]"
    if deadline and time.time() >= deadline:
        print(f"{prefix} 런 상한 도달 — 이번 회차 건너뜀", flush=True)
        return {"slug": ch["slug"], "ok": 0, "skip": 0, "fail": 0, "stopped": "deadline"}
    api_key = os.environ.get("YOUTUBE_API_KEY") or _load_env_key(".env.local", "YOUTUBE_API_KEY")
    youtube = build("youtube", "v3", developerKey=api_key)

    # CLI --days > 0 이면 override, 아니면 카테고리 정책
    effective_days = days if days > 0 else policy_for(ch["slug"])["days"]
    cat = category_of(ch["slug"])

    print(f"\n{prefix} ===== {ch['slug']} (category={cat}, days={effective_days}) =====", flush=True)
    videos = get_channel_videos_api(youtube, ch, max_videos, effective_days)
    print(f"{prefix} 수집 영상: {len(videos)}개", flush=True)
    if dry_list:
        have = sum(1 for v in videos if (Path(output_dir) / ch["slug"] / f"{v['vid']}.txt").exists())
        print(f"{prefix} [dry-list] 전체 {len(videos)} / 자막 있음 {have} / 남음 {len(videos) - have}", flush=True)
        return {"slug": ch["slug"], "ok": 0, "skip": have, "fail": 0, "stopped": "dry-list",
                "remaining": len(videos) - have, "total": len(videos)}

    keyword = ch.get("keyword")
    if keyword:
        before = len(videos)
        videos = [v for v in videos if keyword in v.get("title", "")]
        print(f"{prefix} keyword 필터 '{keyword}': {before} → {len(videos)}개", flush=True)
    save_list_json(output_dir, ch["slug"], videos)

    ok = skip = fail = 0
    total = len(videos)

    failed = load_failed(output_dir, ch["slug"])
    videos_to_crawl = [
        v for v in videos
        if not (skip_existing and (
            (Path(output_dir) / ch["slug"] / f"{v['vid']}.txt").exists()
            or failed.get(v["vid"], {}).get("count", 0) >= GIVEUP_FAILS
        ))
    ]
    skip = total - len(videos_to_crawl)
    pending = len(videos_to_crawl)

    # heavy 채널은 큐가 수백 건이라 스로틀 상태에서 소모 시간이 비례해 커진다 → 회차당 상한
    cap = crawl_cap or policy_for(ch["slug"]).get("crawl_cap", 0)
    if cap and len(videos_to_crawl) > cap:
        print(f"{prefix} 큐 cap {cap} 적용: {len(videos_to_crawl)} → {cap}", flush=True)
        videos_to_crawl = videos_to_crawl[:cap]

    stopped = None
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
            consec_fail = 0
            for i, v in enumerate(videos_to_crawl, 1):
                if deadline and time.time() >= deadline:
                    stopped = "deadline"
                    print(f"{prefix} 런 상한 도달 — {i - 1}/{len(videos_to_crawl)}에서 중단", flush=True)
                    break
                segments = get_transcript(page, v["vid"])
                if segments:
                    save_transcript(output_dir, ch["slug"], v["vid"], v["title"], v["url"], segments)
                    ok += 1
                    consec_fail = 0
                    failed.pop(v["vid"], None)
                else:
                    fail += 1
                    f = failed.setdefault(v["vid"], {"count": 0, "title": v["title"], "url": v["url"]})
                    f["count"] += 1
                    f["last"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    consec_fail += 1
                    if consec_fail >= CONSEC_FAIL_LIMIT:
                        stopped = "circuit"
                        print(f"{prefix} [서킷브레이커] 연속 실패 {consec_fail}건 — 소프트 스로틀 의심, 채널 조기 종료", flush=True)
                        break
                if (ok + fail) % 10 == 0:
                    print(f"{prefix} 진행 {i}/{len(videos_to_crawl)} (ok={ok} skip={skip} fail={fail})", flush=True)
            context.close()
            browser.close()
        save_failed(output_dir, ch["slug"], failed)

    remaining = max(pending - ok - fail, 0) + sum(
        1 for v in videos_to_crawl if 0 < failed.get(v["vid"], {}).get("count", 0) < GIVEUP_FAILS)
    print(f"{prefix} 완료: ok={ok} skip={skip} fail={fail} remaining={remaining}"
          + (f" stopped={stopped}" if stopped else ""), flush=True)
    return {"slug": ch["slug"], "ok": ok, "skip": skip, "fail": fail, "stopped": stopped,
            "remaining": remaining, "total": total}


def main():
    args = parse_args()
    channels = filter_channels(args.channel)
    skip_existing = not args.no_skip_existing
    workers = min(args.workers, len(channels))
    deadline = time.time() + args.max_minutes * 60 if args.max_minutes > 0 else None
    print(f"총 {len(channels)}개 채널, {workers} workers로 병렬 실행 (런 상한 {args.max_minutes or '무제한'}분)")

    remaining_total = 0
    clean = True
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                process_channel, ch, args.headless, args.output_dir,
                args.max_videos, args.days, skip_existing, deadline,
                args.dry_list, args.crawl_cap,
            ): ch for ch in channels
        }
        for future in as_completed(futures):
            ch = futures[future]
            try:
                r = future.result()
                remaining_total += r.get("remaining", 0)
                if r.get("stopped") not in (None, "dry-list"):
                    clean = False
                print(f"[완료] {r['slug']}: ok={r['ok']} skip={r['skip']} fail={r['fail']}"
                      + (f" stopped={r['stopped']}" if r.get("stopped") else ""))
            except Exception as e:
                clean = False
                print(f"[실패] {ch['slug']}: {e}")

    print(f"\n남은 영상 합계: {remaining_total}")
    # 백필 크론(cron_food_backfill.sh)이 이 줄을 보고 스스로 멈춘다
    if clean and remaining_total == 0 and not args.dry_list:
        print("BACKFILL COMPLETE")
    print("\nALL DONE")


if __name__ == "__main__":
    main()
