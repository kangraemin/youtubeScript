import os
import time
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

_ENV_LOCAL = Path(__file__).resolve().parent.parent / ".env.local"

# EADDRNOTAVAIL(49), ECONNRESET(54), ETIMEDOUT(60), ECONNREFUSED(61), EHOSTDOWN(64), EHOSTUNREACH(65)
_TRANSIENT_ERRNOS = {49, 54, 60, 61, 64, 65}

# httpx/httpcore가 던지는 일시적 연결 계열 예외 (클래스명으로 판정 — httpx 임포트 의존 회피)
_TRANSIENT_EXC_NAMES = {
    "ConnectError",
    "ConnectTimeout",
    "ReadTimeout",
    "ReadError",
    "WriteError",
    "RemoteProtocolError",
    "PoolTimeout",
}


def _is_transient(exc: BaseException) -> bool:
    """일시적 네트워크 오류인지 판정 — 소켓 고갈·연결 리셋·타임아웃 계열만 재시도 대상.

    supabase-py는 httpx 예외를 그대로 올리거나 다른 예외로 감싸므로
    __cause__/__context__ 체인을 따라 내려가며 확인한다.
    """
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, OSError) and cur.errno in _TRANSIENT_ERRNOS:
            return True
        if type(cur).__name__ in _TRANSIENT_EXC_NAMES:
            return True
        cur = cur.__cause__ or cur.__context__
    return False


def call_with_retry(fn, tries: int = 5, base_delay: float = 2.0):
    """일시적 네트워크 오류에 한해 지수 백오프 재시도. 그 외 예외는 즉시 전파.

    2026-08-15 사고: cron 중첩으로 소켓이 고갈되자 첫 DB 호출 한 번의 실패만으로
    전 채널 작업이 '총 0개'로 끝났고 17일간 수집이 멈췄다.
    공유 락(run-crawl.sh / cron_backfill.sh)이 1차 방어, 이 함수가 2차 방어다.
    """
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            if not _is_transient(e) or i == tries - 1:
                raise
            time.sleep(base_delay * (2 ** i))


def get_client() -> Client:
    load_dotenv(_ENV_LOCAL)  # override=False — 기존 env 우선
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Supabase 자격 증명 없음: SUPABASE_URL/NEXT_PUBLIC_SUPABASE_URL 및 "
            "SUPABASE_SERVICE_KEY/SUPABASE_SERVICE_ROLE_KEY 중 하나씩 필요"
        )
    return create_client(url, key)


def get_channels(client: Client) -> list[dict]:
    res = client.table("channels").select("*").execute()
    return res.data


def insert_to_queue(client: Client, video_id: str, channel_id: str) -> None:
    client.table("processing_queue").upsert(
        {"video_id": video_id, "channel_id": channel_id, "status": "pending"},
        on_conflict="video_id",
    ).execute()


def get_pending_videos(client: Client, limit: int = 20) -> list[dict]:
    res = (
        client.table("processing_queue")
        .select("*")
        .in_("status", ["pending", "failed"])
        .lt("retry_count", 3)
        .order("created_at")
        .limit(limit)
        .execute()
    )
    return res.data


def update_queue_status(
    client: Client, video_id: str, status: str, error_message: str | None = None
) -> None:
    data: dict = {"status": status}
    if error_message:
        data["error_message"] = error_message
    if status == "failed":
        # increment retry_count via raw update
        row = (
            client.table("processing_queue")
            .select("retry_count")
            .eq("video_id", video_id)
            .single()
            .execute()
        )
        data["retry_count"] = (row.data.get("retry_count", 0) or 0) + 1
    if status == "done":
        from datetime import datetime, timezone

        data["processed_at"] = datetime.now(timezone.utc).isoformat()

    client.table("processing_queue").update(data).eq("video_id", video_id).execute()


def upsert_restaurant(client: Client, restaurant: dict) -> int:
    """Upsert restaurant and return its id."""
    res = (
        client.table("restaurants")
        .upsert(restaurant, on_conflict="name,address")
        .execute()
    )
    if res.data:
        return res.data[0]["id"]
    # fallback: query by name+address
    q = client.table("restaurants").select("id").eq("name", restaurant["name"])
    if restaurant.get("address"):
        q = q.eq("address", restaurant["address"])
    row = q.limit(1).execute()
    return row.data[0]["id"]


def upsert_video(client: Client, video: dict) -> None:
    client.table("videos").upsert(
        video, on_conflict="video_id,restaurant_id"
    ).execute()


def get_existing_video_ids(client: Client) -> set[str]:
    res = client.table("processing_queue").select("video_id").execute()
    return {r["video_id"] for r in res.data}


def save_extraction_result(client: Client, video_id: str, result: list[dict]) -> None:
    """Save Claude extraction result JSON to processing_queue."""
    import json
    client.table("processing_queue").update(
        {"extraction_result": json.dumps(result, ensure_ascii=False)}
    ).eq("video_id", video_id).execute()


def get_cached_extraction(client: Client, video_id: str) -> list[dict] | None:
    """Get cached extraction result from processing_queue."""
    import json
    res = (
        client.table("processing_queue")
        .select("extraction_result")
        .eq("video_id", video_id)
        .single()
        .execute()
    )
    raw = res.data.get("extraction_result") if res.data else None
    if raw:
        return json.loads(raw) if isinstance(raw, str) else raw
    return None
