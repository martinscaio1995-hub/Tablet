import json

import anthropic

from src.config import config

MODEL = "claude-sonnet-5"


def research_trends(niche: str, count: int = 5) -> list[dict]:
    """Pesquisa na web o que está bombando agora no nicho e retorna ângulos
    de vídeo prontos para virar ideia, já pensando em afiliados.

    Cada item: {"topic", "why_now", "angle", "product_tie_in"}.
    "product_tie_in" é o tipo de produto (não uma marca específica) que
    encaixaria naturalmente nesse vídeo — vira insumo do AFFILIATE_NOTE.
    """
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        tools=[
            {
                "type": "web_search_20260209",
                "name": "web_search",
                "max_uses": 6,
            }
        ],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "trends": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "topic": {"type": "string"},
                                    "why_now": {"type": "string"},
                                    "angle": {"type": "string"},
                                    "product_tie_in": {"type": "string"},
                                },
                                "required": [
                                    "topic",
                                    "why_now",
                                    "angle",
                                    "product_tie_in",
                                ],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["trends"],
                    "additionalProperties": False,
                },
            }
        },
        messages=[
            {
                "role": "user",
                "content": (
                    f"Pesquise na web o que está em alta AGORA (últimos 7-14 dias) "
                    f"relacionado a: \"{niche}\". Procure em fontes como TikTok, "
                    "Reddit, YouTube, fóruns e notícias do nicho — não invente, "
                    "baseie-se no que encontrar na busca.\n\n"
                    f"Retorne os {count} melhores ângulos de vídeo curto (TikTok), "
                    "cada um com:\n"
                    "- topic: o assunto/tendência específica encontrada\n"
                    "- why_now: por que está bombando agora (evento, lançamento, "
                    "problema comum, etc.)\n"
                    "- angle: o ângulo de vídeo específico para explorar isso "
                    "(não genérico)\n"
                    "- product_tie_in: que tipo de produto (filamento, upgrade, "
                    "acessório, ferramenta) encaixaria como afiliado nesse vídeo, "
                    "de forma natural — string vazia se nenhum encaixar bem"
                ),
            }
        ],
    )

    text = next(b.text for b in message.content if b.type == "text")
    data = json.loads(text)
    return list(data["trends"])


if __name__ == "__main__":
    for trend in research_trends(config.content_niche):
        print(f"- {trend['topic']} ({trend['why_now']})")
        print(f"  ângulo: {trend['angle']}")
        if trend["product_tie_in"]:
            print(f"  produto: {trend['product_tie_in']}")
