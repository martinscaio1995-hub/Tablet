import json

import anthropic

from src.config import config

MODEL = "claude-sonnet-5"


def generate_ideas(niche: str, count: int = 5) -> list[str]:
    """Ask Claude for `count` short-form video ideas for the given niche."""
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Gere {count} ideias de vídeo curto (TikTok) para o nicho: "
                    f"\"{niche}\". Cada ideia deve ser uma frase curta e específica, "
                    "não genérica. Responda APENAS com um array JSON de strings, "
                    "sem markdown, sem texto extra."
                ),
            }
        ],
    )

    text = message.content[0].text.strip()
    ideas = json.loads(text)
    if not isinstance(ideas, list):
        raise ValueError(f"Resposta inesperada do modelo: {text}")
    return [str(i) for i in ideas]


if __name__ == "__main__":
    for idea in generate_ideas(config.content_niche):
        print(f"- {idea}")
