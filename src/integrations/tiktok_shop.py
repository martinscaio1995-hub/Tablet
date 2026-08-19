"""Cliente para puxar comissões de afiliado do TikTok Shop.

IMPORTANTE — leia antes de tentar usar isso: a API de vendas do TikTok
Shop (Partner Center / Affiliate API) é uma aprovação de PARCEIRO DE
NEGÓCIO, separada e mais pesada que o app "TikTok for Developers" usado
em src/tiktok/ para postar vídeos. Normalmente exige CNPJ, análise da
TikTok e leva dias/semanas — não é algo que se resolve só com uma chave
de API. Detalhes em docs/tiktok-shop-vendas.md.

Enquanto isso não estiver aprovado, use o dashboard (rota /sales) para
registrar vendas manualmente — é o que store.add_sale() já suporta.
Esta função existe para o dia em que o acesso de parceiro estiver ativo.
"""
from src.config import config


class TikTokShopNotConfigured(RuntimeError):
    pass


def sync_recent_orders() -> list[dict]:
    """Busca pedidos/comissões recentes via TikTok Shop Partner API.

    Não implementado: requer aprovação como parceiro no TikTok Shop
    Partner Center (developers.tiktokshop.com), que este projeto não
    pode obter por você. Depois de aprovado e com as credenciais no
    .env, implemente aqui a chamada a
    GET /affiliate_partner/202410/orders (ou endpoint equivalente da
    versão vigente da API) e mapeie o retorno para
    src.store.add_sale(..., source="tiktok_shop").
    """
    if not config.tiktok_shop_access_token:
        raise TikTokShopNotConfigured(
            "TikTok Shop ainda não configurado — veja "
            "docs/tiktok-shop-vendas.md. Por enquanto, registre vendas "
            "manualmente pelo dashboard (/sales)."
        )
    raise NotImplementedError(
        "Credenciais presentes, mas a chamada à Partner API ainda não foi "
        "implementada — veja o docstring desta função."
    )
