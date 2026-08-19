"""Geração de música (ElevenLabs Music) para trilha dos vídeos.

Precisa de ELEVENLABS_API_KEY no .env, com o produto "Music" habilitado
no plano — os pagamentos anteriores da conta apareceram como recusados
no Gmail, então confirme que a assinatura está ativa antes de usar.
"""
from elevenlabs.client import ElevenLabs

from src.config import config

MODEL = "music_v2"


class MusicGenerationError(RuntimeError):
    pass


def generate_music(prompt: str, output_path: str, length_ms: int = 20000) -> str:
    """Gera uma trilha a partir de um prompt e salva em `output_path` (mp3)."""
    if not config.elevenlabs_api_key:
        raise MusicGenerationError("ELEVENLABS_API_KEY não configurada no .env")

    client = ElevenLabs(api_key=config.elevenlabs_api_key)
    track = client.music.compose(
        prompt=prompt,
        music_length_ms=length_ms,
        model_id=MODEL,
    )

    with open(output_path, "wb") as f:
        for chunk in track:
            f.write(chunk)
    return output_path


if __name__ == "__main__":
    generate_music(
        "Trilha instrumental leve e curiosa para vídeo de timelapse de "
        "impressão 3D, upbeat mas discreta, sem vocais",
        "output/teste_musica.mp3",
        length_ms=15000,
    )
