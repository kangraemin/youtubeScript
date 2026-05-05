"""YouTube 자막 API — 로컬 rawdata/transcripts 기반."""
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from transcript_fetcher import fetch_transcript

app = FastAPI(title="YouTube Transcript API")


@app.get("/transcript")
def get_transcript(video_id: str = Query(..., description="YouTube 영상 ID")):
    segments = fetch_transcript(video_id)
    if segments is None:
        return JSONResponse(
            status_code=404,
            content={"error": "No transcript found", "video_id": video_id},
        )
    return {"video_id": video_id, "segments": segments, "count": len(segments)}


@app.get("/health")
def health():
    return {"status": "ok"}
