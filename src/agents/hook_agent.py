"""Gerador de hooks — a primeira frase do vídeo.

O hook é o maior fator isolado de visualização: se os 2 primeiros
segundos não seguram, o resto do vídeo não existe para o algoritmo.
Por isso ele é gerado em várias opções para você escolher, e não junto
com o roteiro.
"""
import json

import anthropic

from src.config import config

MODEL = "claude-sonnet-5"

# Padrões de abertura que comprovadamente seguram atenção em vídeo curto.
PADROES = """
- Contradição: afirma o oposto do senso comum ("Parei de X e melhorou")
- Erro custoso: aponta um erro que a pessoa provavelmente comete
- Curiosidade aberta: começa uma história sem entregar o final
- Número concreto: dado específico e surpreendente
- Endereçamento direto: fala com um grupo específico ("Se você tem X...")
- Antes/depois: promete uma transformação visível
"""


def generate_hooks(
    niche: str,
    topic: str,
    angle: str,
    count: int = 5,
    performance_context: str = "",
) -> list[dict]:
    """Gera `count` hooks alternativos para o mesmo assunto.

    `performance_context` é o histórico de hooks já postados com as views
    que deram — quando presente, o agente calibra pelo que funciona com a
    SUA audiência em vez da média da internet.

    Cada item: {"hook", "padrao", "por_que_funciona"}.
    """
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    aprendizado = (
        "\n\nHooks que você já postou e o resultado real que deram "
        "(ordenados por views). Aprenda o padrão do que funciona com esta "
        f"audiência específica e puxe os novos hooks nessa direção:\n"
        f"{performance_context}"
        if performance_context
        else ""
    )

    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "hooks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "hook": {"type": "string"},
                                    "padrao": {"type": "string"},
                                    "por_que_funciona": {"type": "string"},
                                },
                                "required": ["hook", "padrao", "por_que_funciona"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["hooks"],
                    "additionalProperties": False,
                },
            }
        },
        messages=[
            {
                "role": "user",
                "content": (
                    f"Nicho: \"{niche}\".\n"
                    f"Assunto: \"{topic}\".\n"
                    f"Ângulo do vídeo: \"{angle}\".{aprendizado}\n\n"
                    f"Escreva {count} hooks alternativos — a PRIMEIRA FRASE "
                    "falada do vídeo curto, aquela que decide se a pessoa "
                    "continua assistindo ou desliza.\n\n"
                    f"Use padrões diferentes entre si:{PADROES}\n"
                    "Regras:\n"
                    "- No máximo 12 palavras cada. Curto é o ponto.\n"
                    "- Português brasileiro falado, natural, sem formalidade.\n"
                    "- Nada de 'você sabia que' nem 'hoje eu vou te mostrar' — "
                    "são aberturas mortas, o algoritmo já viu demais.\n"
                    "- Sem clickbait que o vídeo não entrega: promessa falsa "
                    "derruba retenção e afunda o alcance.\n\n"
                    "Para cada um: 'hook' (a frase), 'padrao' (qual dos "
                    "padrões acima usou) e 'por_que_funciona' (uma frase "
                    "curta explicando o gatilho)."
                ),
            }
        ],
    )

    text = next(b.text for b in message.content if b.type == "text")
    return list(json.loads(text)["hooks"])
