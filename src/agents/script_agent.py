import json
from dataclasses import dataclass

import anthropic

from src.config import config

MODEL = "claude-sonnet-5"


@dataclass
class VideoScript:
    idea: str
    hook: str
    narration: str
    caption: str
    hashtags: list[str]
    cta: str = ""


def write_script(idea: str, language: str = "pt-BR", affiliate_note: str = "") -> VideoScript:
    """Turn a video idea into a hook, voiceover script, caption and hashtags.

    `affiliate_note` is free text describing what to promote (a product,
    brand, or program like TikTok Shop) — when set, the agent weaves a
    natural call-to-action into the narration instead of a hard sales line.
    """
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    affiliate_instruction = (
        f"\n\nEste vídeo também deve promover, de forma natural (sem soar "
        f"como propaganda forçada): \"{affiliate_note}\". Inclua uma "
        "chamada curta para ação (campo 'cta') como 'tá na vitrine/no "
        "carrinho aqui do TikTok' — nunca peça para clicar em link externo, "
        "já que o TikTok Shop vincula o produto direto no vídeo."
        if affiliate_note
        else ""
    )

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Idioma: {language}. Ideia de vídeo curto: \"{idea}\"."
                    f"{affiliate_instruction}\n\n"
                    "Escreva:\n"
                    "1. hook: uma frase de abertura (primeiros 2s) que prenda atenção\n"
                    "2. narration: roteiro completo para narração em voz, 25-45s falado, "
                    "linguagem natural e direta, sem marcações de tempo\n"
                    "3. caption: legenda curta para a postagem\n"
                    "4. hashtags: lista de 5 a 8 hashtags relevantes (sem #)\n"
                    "5. cta: chamada para ação curta (vazio se não houver promoção)\n\n"
                    "Responda APENAS com um objeto JSON com essas 5 chaves, sem markdown."
                ),
            }
        ],
    )

    text = message.content[0].text.strip()
    data = json.loads(text)
    return VideoScript(
        idea=idea,
        hook=data["hook"],
        narration=data["narration"],
        caption=data["caption"],
        hashtags=list(data["hashtags"]),
        cta=data.get("cta", ""),
    )


if __name__ == "__main__":
    script = write_script("3 erros comuns ao estudar para provas")
    print(script)
