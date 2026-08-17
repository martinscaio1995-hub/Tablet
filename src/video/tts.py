import asyncio

import edge_tts


async def _synthesize(text: str, voice: str, out_path: str) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def synthesize_narration(text: str, voice: str, out_path: str) -> str:
    """Generate an MP3 narration file from text using a free neural TTS voice."""
    asyncio.run(_synthesize(text, voice, out_path))
    return out_path
