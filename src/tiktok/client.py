"""Thin client for TikTok's official Content Posting API (direct post, FILE_UPLOAD).

Docs: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
"""
import math
import os
import time

import requests

API_BASE = "https://open.tiktokapis.com/v2"
MAX_SINGLE_CHUNK = 64 * 1024 * 1024  # 64MB
CHUNK_SIZE = 10 * 1024 * 1024  # 10MB
TERMINAL_STATUSES = {"PUBLISH_COMPLETE", "FAILED"}


class TikTokAPIError(RuntimeError):
    pass


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }


def get_creator_info(access_token: str) -> dict:
    """Query allowed privacy levels / creator constraints. Call this before posting."""
    resp = requests.post(
        f"{API_BASE}/post/publish/creator_info/query/",
        headers=_headers(access_token),
        json={},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("error", {}).get("code") not in (None, "ok"):
        raise TikTokAPIError(str(data["error"]))
    return data["data"]


def _chunk_plan(video_size: int) -> tuple[int, int]:
    if video_size <= MAX_SINGLE_CHUNK:
        return video_size, 1
    total_chunks = math.ceil(video_size / CHUNK_SIZE)
    return CHUNK_SIZE, total_chunks


def post_video(
    access_token: str,
    video_path: str,
    title: str,
    privacy_level: str = "SELF_ONLY",
    disable_duet: bool = False,
    disable_stitch: bool = False,
    disable_comment: bool = False,
    poll_interval: float = 3.0,
    poll_timeout: float = 180.0,
) -> dict:
    """Upload and publish a local video file via the FILE_UPLOAD flow.

    Returns the final status payload once the upload reaches a terminal state.
    Note: until your TikTok app passes audit, all posts are forced to SELF_ONLY
    (private, visible only to the account owner) regardless of privacy_level.
    """
    video_size = os.path.getsize(video_path)
    chunk_size, total_chunk_count = _chunk_plan(video_size)

    init_resp = requests.post(
        f"{API_BASE}/post/publish/video/init/",
        headers=_headers(access_token),
        json={
            "post_info": {
                "title": title,
                "privacy_level": privacy_level,
                "disable_duet": disable_duet,
                "disable_stitch": disable_stitch,
                "disable_comment": disable_comment,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunk_count,
            },
        },
        timeout=30,
    )
    init_resp.raise_for_status()
    init_data = init_resp.json()
    if init_data.get("error", {}).get("code") not in (None, "ok"):
        raise TikTokAPIError(str(init_data["error"]))

    publish_id = init_data["data"]["publish_id"]
    upload_url = init_data["data"]["upload_url"]

    with open(video_path, "rb") as f:
        for chunk_index in range(total_chunk_count):
            start = chunk_index * chunk_size
            end = min(start + chunk_size, video_size) - 1
            f.seek(start)
            chunk_bytes = f.read(end - start + 1)

            put_resp = requests.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(chunk_bytes)),
                    "Content-Range": f"bytes {start}-{end}/{video_size}",
                },
                data=chunk_bytes,
                timeout=120,
            )
            if put_resp.status_code not in (200, 201, 206):
                raise TikTokAPIError(
                    f"Falha no upload do chunk {chunk_index}: "
                    f"{put_resp.status_code} {put_resp.text}"
                )

    return _poll_status(access_token, publish_id, poll_interval, poll_timeout)


def _poll_status(access_token: str, publish_id: str, interval: float, timeout: float) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.post(
            f"{API_BASE}/post/publish/status/fetch/",
            headers=_headers(access_token),
            json={"publish_id": publish_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("data", {}).get("status")
        if status in TERMINAL_STATUSES:
            return data["data"]
        time.sleep(interval)
    raise TikTokAPIError(f"Timeout aguardando publish_id={publish_id} finalizar.")
