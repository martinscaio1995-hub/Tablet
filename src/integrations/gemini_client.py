"""Geração de imagem (Gemini / "Nano Banana") para artes de anúncio.

Precisa de GEMINI_API_KEY no .env — chave de API do Google AI Studio
(aistudio.google.com/apikey), cobrada por uso, separada da assinatura
Google AI Pro do app/site.
"""
import base64

from google import genai

from src.config import config

MODEL = "gemini-3.1-flash-image"


class GeminiError(RuntimeError):
    pass


def generate_image(prompt: str, output_path: str) -> str:
    """Gera uma imagem a partir de um prompt e salva em `output_path`."""
    if not config.gemini_api_key:
        raise GeminiError("GEMINI_API_KEY não configurada no .env")

    client = genai.Client(api_key=config.gemini_api_key)
    interaction = client.interactions.create(model=MODEL, input=prompt)

    image = getattr(interaction, "output_image", None)
    if image is None or not getattr(image, "data", None):
        raise GeminiError(f"Gemini não retornou imagem para o prompt: {prompt!r}")

    with open(output_path, "wb") as f:
        f.write(base64.b64decode(image.data))
    return output_path


if __name__ == "__main__":
    generate_image(
        "Foto de produto de um rolo de filamento PLA colorido ao lado de "
        "uma impressora 3D Bambu Lab A1, fundo de estúdio limpo, luz suave",
        "output/teste_gemini.png",
    )
