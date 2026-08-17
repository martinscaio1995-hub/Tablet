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


def write_script(idea: str, language: str = "pt-BR") -> VideoScript:
    """Turn a video idea into a hook, voiceover script, caption and hashtags."""
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Idioma: {language}. Ideia de vídeo curto: \"{idea}\".\n\n"
                    "Escreva:\n"
                    "1. hook: uma frase de abertura (primeiros 2s) que prenda atenção\n"
                    "2. narration: roteiro completo para narração em voz, 25-45s falado, "
                    "linguagem natural e direta, sem marcações de tempo\n"
                    "3. caption: legenda curta para a postagem\n"
                    "4. hashtags: lista de 5 a 8 hashtags relevantes (sem #)\n\n"
                    "Responda APENAS com um objeto JSON com essas 4 chaves, sem markdown."
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
    )


if __name__ == "__main__":
    script = write_script("3 erros comuns ao estudar para provas")
    print(script)
