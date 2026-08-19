# Vendas do TikTok Shop no dashboard

## Por que isso não é automático ainda

O projeto já publica vídeos via **TikTok for Developers** (Content Posting
API) — isso é só criar um app e autorizar sua conta, minutos.

Puxar **vendas/comissões** é outra API: a **TikTok Shop Partner API**
(developers.tiktokshop.com), e o acesso a ela é uma aprovação de negócio:
- Geralmente pede CNPJ/pessoa jurídica
- Passa por análise da TikTok, não é instantâneo
- É um cadastro totalmente separado do app usado para postar vídeos

Isso não é algo que eu resolvo escrevendo código — é um processo que só
você consegue iniciar, na sua conta.

## O que fazer agora: registro manual

O dashboard já tem uma tela de vendas (`/sales`) onde você lança cada
comissão manualmente — data, produto, valor. Isso já é suficiente para o
agente de viabilidade (`viability_agent`) considerar "o que já vendeu bem"
ao avaliar se vale a pena investir num novo vídeo parecido.

## Quando quiser automatizar de verdade

1. Configure sua loja em [seller.tiktokshop.com](https://seller.tiktokshop.com)
   e ative o programa de afiliados/creator, se ainda não tiver.
2. Peça acesso de parceiro em
   [developers.tiktokshop.com](https://developers.tiktokshop.com) —
   normalmente é preciso descrever o caso de uso (leitura de comissões de
   afiliado do seu próprio canal).
3. Depois de aprovado, preencha no `.env`: `TIKTOK_SHOP_APP_KEY`,
   `TIKTOK_SHOP_APP_SECRET`, `TIKTOK_SHOP_ACCESS_TOKEN`,
   `TIKTOK_SHOP_SHOP_ID`.
4. Me chame de volta — nesse ponto eu implemento
   `src/integrations/tiktok_shop.py::sync_recent_orders()` de verdade
   contra o endpoint vigente da API (a v202410 citada no código pode já
   ter mudado de versão até lá) e ligo um botão "sincronizar" na tela
   `/sales`.
