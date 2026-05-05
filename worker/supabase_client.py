import os
from supabase import create_client, Client


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
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
