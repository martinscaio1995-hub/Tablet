import json

import anthropic

from src.config import config

MODEL = "claude-sonnet-5"


def score_viability(
    niche: str,
    topic: str,
    why_now: str,
    angle: str,
    product_tie_in: str = "",
    sales_context: str = "",
) -> dict:
    """Julga se vale a pena virar essa tendência em vídeo, do ponto de vista
    de audiência (a tendência ainda está viva?) e de afiliado (dá pra
    vender algo nela?).

    Retorna {"score" (0-100), "recommendation" ("criar_agora" | "esperar" |
    "pular"), "reasoning"}.
    """
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    sales_block = (
        f"\n\nHistórico de vendas do canal até agora (use para calibrar o "
        f"julgamento — o que já vendeu bem pesa a favor de temas parecidos):\n"
        f"{sales_context}"
        if sales_context
        else ""
    )

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "score": {"type": "integer", "minimum": 0, "maximum": 100},
                        "recommendation": {
                            "type": "string",
                            "enum": ["criar_agora", "esperar", "pular"],
                        },
                        "reasoning": {"type": "string"},
                    },
                    "required": ["score", "recommendation", "reasoning"],
                    "additionalProperties": False,
                },
            }
        },
        messages=[
            {
                "role": "user",
                "content": (
                    f"Nicho do canal: \"{niche}\".\n"
                    f"Tendência encontrada: \"{topic}\".\n"
                    f"Por que está em alta agora: \"{why_now}\".\n"
                    f"Ângulo de vídeo proposto: \"{angle}\".\n"
                    f"Produto de afiliado que encaixaria: "
                    f"\"{product_tie_in or 'nenhum sugerido'}\"."
                    f"{sales_block}\n\n"
                    "Avalie se vale a pena investir tempo criando este vídeo "
                    "AGORA, considerando: (1) a tendência ainda tem fôlego ou "
                    "já é tarde para pegar o pico de alcance; (2) o ângulo é "
                    "específico o bastante para se destacar, ou é genérico "
                    "demais; (3) existe encaixe natural e não forçado com um "
                    "produto de afiliado, ou o vídeo só faz sentido sem venda; "
                    "(4) o esforço de produção compensa o retorno esperado "
                    "(alcance + comissão).\n\n"
                    "score: 0-100, onde 100 é 'largue tudo e grave agora'.\n"
                    "recommendation: 'criar_agora' (score alto, janela boa), "
                    "'esperar' (tema tem potencial mas não é urgente, ou falta "
                    "contexto/material seu para fazer bem-feito), ou 'pular' "
                    "(baixo retorno esperado ou risco de soar forçado).\n"
                    "reasoning: 2-4 frases diretas explicando o porquê, em "
                    "português."
                ),
            }
        ],
    )

    text = next(b.text for b in message.content if b.type == "text")
    return json.loads(text)
