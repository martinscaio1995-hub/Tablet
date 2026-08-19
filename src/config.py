import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str = _env("ANTHROPIC_API_KEY")

    tiktok_client_key: str = _env("TIKTOK_CLIENT_KEY")
    tiktok_client_secret: str = _env("TIKTOK_CLIENT_SECRET")
    tiktok_redirect_uri: str = _env("TIKTOK_REDIRECT_URI", "http://localhost:8787/callback")

    tiktok_access_token: str = _env("TIKTOK_ACCESS_TOKEN")
    tiktok_refresh_token: str = _env("TIKTOK_REFRESH_TOKEN")
    tiktok_open_id: str = _env("TIKTOK_OPEN_ID")
    tiktok_privacy_level: str = _env("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY")

    content_niche: str = _env("CONTENT_NICHE", "conteúdo geral")
    content_language: str = _env("CONTENT_LANGUAGE", "pt-BR")
    tts_voice: str = _env("TTS_VOICE", "pt-BR-FranciscaNeural")

    # Texto livre descrevendo o que promover (produto, marca, programa de
    # afiliados) para os agentes tecerem uma chamada natural no roteiro.
    affiliate_note: str = _env("AFFILIATE_NOTE", "")

    webapp_host: str = _env("WEBAPP_HOST", "0.0.0.0")
    webapp_port: int = int(_env("WEBAPP_PORT", "8000"))

    gemini_api_key: str = _env("GEMINI_API_KEY")
    elevenlabs_api_key: str = _env("ELEVENLABS_API_KEY")

    tiktok_shop_app_key: str = _env("TIKTOK_SHOP_APP_KEY")
    tiktok_shop_app_secret: str = _env("TIKTOK_SHOP_APP_SECRET")
    tiktok_shop_access_token: str = _env("TIKTOK_SHOP_ACCESS_TOKEN")
    tiktok_shop_shop_id: str = _env("TIKTOK_SHOP_SHOP_ID")

    assets_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    output_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    data_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    db_path: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "tablet.db"
    )


config = Config()
