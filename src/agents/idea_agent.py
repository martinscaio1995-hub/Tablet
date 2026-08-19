import json

import anthropic

from src.config import config

MODEL = "claude-sonnet-5"


def generate_ideas(niche: str, count: int = 5, trends: list[dict] | None = None) -> list[str]:
    """Ask Claude for `count` short-form video ideas for the given niche.

    `trends` (opcional) vem de `trends_agent.research_trends`: quando
    presente, as ideias são ancoradas nesses ângulos em alta em vez de
    genéricas.
    """
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    trends_context = ""
    if trends:
        linhas = "\n".join(
            f"- {t['topic']}: {t['angle']} (por quê: {t['why_now']})" for t in trends
        )
        trends_context = (
            "\n\nAncore as ideias nestas tendências reais e recentes do nicho "
            f"em vez de temas genéricos:\n{linhas}"
        )

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Gere {count} ideias de vídeo curto (TikTok) para o nicho: "
                    f"\"{niche}\".{trends_context}\n\nCada ideia deve ser uma frase "
                    "curta e específica, não genérica. Responda APENAS com um array "
                    "JSON de strings, sem markdown, sem texto extra."
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
