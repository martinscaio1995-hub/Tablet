import glob
import os
import random
import textwrap

from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)

WIDTH, HEIGHT = 1080, 1920
SUPPORTED_VIDEO = (".mp4", ".mov", ".m4v")
SUPPORTED_IMAGE = (".jpg", ".jpeg", ".png")


def _fit_vertical(clip):
    """Scale+crop a clip to fill a 1080x1920 frame."""
    scale = max(WIDTH / clip.w, HEIGHT / clip.h)
    clip = clip.resize(scale)
    x_center, y_center = clip.w / 2, clip.h / 2
    return clip.crop(
        x_center=x_center, y_center=y_center, width=WIDTH, height=HEIGHT
    )


def _background_clip(duration: float, assets_dir: str):
    """Build a background of `duration` seconds from files in assets_dir.

    Falls back to a plain dark background if no assets are supplied.
    """
    files = sorted(glob.glob(os.path.join(assets_dir, "*")))
    files = [f for f in files if f.lower().endswith(SUPPORTED_VIDEO + SUPPORTED_IMAGE)]

    if not files:
        return ColorClip(size=(WIDTH, HEIGHT), color=(18, 18, 20)).set_duration(duration)

    random.shuffle(files)
    clips = []
    remaining = duration
    i = 0
    while remaining > 0:
        f = files[i % len(files)]
        i += 1
        if f.lower().endswith(SUPPORTED_IMAGE):
            seg_len = min(4.0, remaining)
            clip = ImageClip(f).set_duration(seg_len)
        else:
            src = VideoFileClip(f)
            seg_len = min(src.duration, remaining)
            clip = src.subclip(0, seg_len)
        clips.append(_fit_vertical(clip))
        remaining -= seg_len

    return concatenate_videoclips(clips, method="compose")


def _caption_clips(narration: str, duration: float):
    """Split narration into sentence chunks shown as burned-in captions,
    timed proportionally across the clip duration."""
    sentences = [s.strip() for s in narration.replace("\n", " ").split(".") if s.strip()]
    if not sentences:
        return []

    weights = [max(len(s), 1) for s in sentences]
    total_weight = sum(weights)

    clips = []
    t = 0.0
    for sentence, weight in zip(sentences, weights):
        seg_len = duration * (weight / total_weight)
        wrapped = "\n".join(textwrap.wrap(sentence, width=28))
        txt = (
            TextClip(
                wrapped,
                fontsize=64,
                color="white",
                font="DejaVu-Sans-Bold",
                stroke_color="black",
                stroke_width=3,
                method="caption",
                size=(WIDTH - 120, None),
                align="center",
            )
            .set_position(("center", "center"))
            .set_start(t)
            .set_duration(seg_len)
        )
        clips.append(txt)
        t += seg_len

    return clips


def build_video(narration_audio_path: str, narration_text: str, assets_dir: str, out_path: str) -> str:
    """Assemble a vertical TikTok-ready video: background + burned captions + narration audio."""
    audio = AudioFileClip(narration_audio_path)
    duration = audio.duration

    background = _background_clip(duration, assets_dir).set_duration(duration)
    captions = _caption_clips(narration_text, duration)

    video = CompositeVideoClip([background, *captions], size=(WIDTH, HEIGHT)).set_audio(audio)
    video = video.set_duration(duration)

    video.write_videofile(
        out_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
        logger=None,
    )
    return out_path
