import os
import random
import time

from src.agents.idea_agent import generate_ideas
from src.agents.script_agent import VideoScript, write_script
from src.config import config
from src.video.builder import build_video
from src.video.tts import synthesize_narration


def run_pipeline(niche: str | None = None, idea: str | None = None, post: bool = False) -> dict:
    """idea -> script -> narration -> video -> (optionally) post to TikTok.

    `post=False` (default) only produces the video locally for you to review.
    Pass `post=True` to also publish it via the TikTok Content Posting API.
    """
    niche = niche or config.content_niche

    if not idea:
        ideas = generate_ideas(niche, count=5)
        idea = random.choice(ideas)

    script: VideoScript = write_script(
        idea, language=config.content_language, affiliate_note=config.affiliate_note
    )

    ts = int(time.time())
    audio_path = os.path.join(config.output_dir, f"narration_{ts}.mp3")
    video_path = os.path.join(config.output_dir, f"video_{ts}.mp4")

    synthesize_narration(script.narration, config.tts_voice, audio_path)
    build_video(audio_path, script.narration, config.assets_dir, video_path)

    result = {
        "idea": idea,
        "script": script,
        "video_path": video_path,
        "posted": False,
        "publish_status": None,
    }

    if post:
        from src.tiktok.auth import get_valid_access_token
        from src.tiktok.client import TikTokAPIError, post_video

        access_token = get_valid_access_token()
        caption_with_cta = f"{script.caption} {script.cta}".strip()
        title = f"{caption_with_cta} " + " ".join(f"#{h}" for h in script.hashtags)
        try:
            status = post_video(
                access_token=access_token,
                video_path=video_path,
                title=title,
                privacy_level=config.tiktok_privacy_level,
                is_branded_content=bool(script.cta),
            )
            result["posted"] = status.get("status") == "PUBLISH_COMPLETE"
            result["publish_status"] = status
        except TikTokAPIError as e:
            result["publish_status"] = {"error": str(e)}

    return result
