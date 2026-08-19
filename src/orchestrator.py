import os
import random
import time

from src.agents.idea_agent import generate_ideas
from src.agents.script_agent import VideoScript, write_script
from src.agents.trends_agent import research_trends
from src.config import config
from src.video.builder import build_video
from src.video.tts import synthesize_narration


def run_pipeline(
    niche: str | None = None,
    idea: str | None = None,
    post: bool = False,
    use_trends: bool = True,
) -> dict:
    """idea -> script -> narration -> video -> (optionally) post to TikTok.

    `post=False` (default) only produces the video locally for you to review.
    Pass `post=True` to also publish it via the TikTok Content Posting API.

    `use_trends=True` (default) pesquisa o que está em alta no nicho antes
    de gerar a ideia, e usa o produto sugerido pela tendência como CTA de
    afiliado quando `AFFILIATE_NOTE` não estiver preenchido no `.env`.
    Ignorado quando `idea` já é passado explicitamente.
    """
    niche = niche or config.content_niche
    affiliate_note = config.affiliate_note

    if not idea:
        trends = research_trends(niche, count=5) if use_trends else None
        ideas = generate_ideas(niche, count=5, trends=trends)
        idea = random.choice(ideas)

        if not affiliate_note and trends:
            matching = next((t for t in trends if t["product_tie_in"]), None)
            if matching:
                affiliate_note = matching["product_tie_in"]

    script: VideoScript = write_script(
        idea, language=config.content_language, affiliate_note=affiliate_note
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
