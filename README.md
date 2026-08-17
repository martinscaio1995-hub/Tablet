# Tablet — pipeline de agentes para conteúdo do TikTok

Pipeline em Python que usa agentes (Claude) para gerar ideias e roteiros,
monta o vídeo (narração TTS + legendas + seus clipes/imagens) e publica
via **API oficial do TikTok** (Content Posting API).

Calibrado para nicho de **impressão 3D (Bambu Lab A1)** com afiliados,
mas o nicho é 100% configurável via `CONTENT_NICHE`.

> Não usa automação de navegador nem simula um usuário no app — só a API
> oficial, que é a forma suportada e dentro dos termos de uso do TikTok
> para postar conteúdo programaticamente.

## Como funciona

```
ideia (Claude) -> roteiro/legenda/hashtags (Claude) -> narração (TTS)
   -> vídeo vertical 1080x1920 (seus clipes/imagens em assets/ + legendas)
   -> publicar no TikTok (API oficial)
```

## 1. Instalar dependências

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

O `moviepy` precisa do `ffmpeg` instalado no sistema (`apt install ffmpeg`
ou `brew install ffmpeg`).

## 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Preencha `ANTHROPIC_API_KEY` (para os agentes) e `CONTENT_NICHE` (o nicho
do seu conteúdo).

## 3. Criar o app no TikTok for Developers (necessário para postar)

O TikTok não permite postar via bots comuns — é preciso criar um app
oficial:

1. Acesse [developers.tiktok.com](https://developers.tiktok.com) e crie
   uma conta de desenvolvedor.
2. Crie um novo app. Anote o **Client Key** e o **Client Secret**
   (aba "Basic Information").
3. Nas configurações do app, ative o produto **"Content Posting API"**
   com **"Direct Post"**, e adicione o escopo `video.publish`.
4. Registre uma **Redirect URI**: para testar localmente use
   `http://localhost:8787/callback` (precisa bater exatamente com
   `TIKTOK_REDIRECT_URI` no seu `.env`).
5. Coloque `TIKTOK_CLIENT_KEY` e `TIKTOK_CLIENT_SECRET` no `.env`.

### Importante: modo privado até a auditoria

Apps novos (não auditados) só conseguem postar em **modo privado
(SELF_ONLY)** — visível só para você, não para seguidores nem para o
For You. Para postar publicamente, você precisa submeter o app para
auditoria do TikTok depois de testar a integração. Isso é uma regra do
TikTok, não uma limitação deste projeto. `TIKTOK_PRIVACY_LEVEL=SELF_ONLY`
já vem configurado assim por padrão no `.env.example`.

## 4. Autorizar sua conta do TikTok (uma vez)

```bash
python cli.py auth
```

Isso abre uma URL para você logar e autorizar o app na sua conta do
TikTok, e imprime `TIKTOK_ACCESS_TOKEN` / `TIKTOK_REFRESH_TOKEN` /
`TIKTOK_OPEN_ID` para você colar no `.env`.

## 5. Adicionar material de vídeo (opcional)

Coloque clipes (`.mp4`) ou imagens (`.jpg`/`.png`) na pasta `assets/`.
O gerador de vídeo monta o fundo a partir desses arquivos; se a pasta
estiver vazia, usa um fundo escuro liso.

### Fluxo de esforço mínimo com a Bambu Lab A1

A A1 grava timelapse automaticamente de cada impressão (verifique se a
opção "Timelapse" está ativa no Bambu Studio / na tela da impressora).
O fluxo com menos trabalho manual é:

1. Depois de imprimir, copie o `.mp4` do timelapse (do cartão SD ou da
   Bambu Handy) para `assets/`.
2. Rode `python cli.py run --idea "nome/descrição rápida da peça que você imprimiu"`.
3. O agente escreve o roteiro em cima dessa ideia, narra por cima do seu
   timelapse real e já gera a legenda com hashtags (e CTA de afiliado,
   se `AFFILIATE_NOTE` estiver preenchido no `.env`).

Sem gravar nada extra além do que a impressora já grava sozinha.

### Afiliados

Preencha `AFFILIATE_NOTE` no `.env` descrevendo o que quer promover (um
filamento, um acessório, um upgrade). O agente de roteiro tece uma
chamada natural no vídeo em vez de um jingle de propaganda. Recomendado
usar **TikTok Shop**: o produto fica vinculado direto no vídeo, sem
precisar mandar ninguém pra um link externo — isso tende a converter
melhor no TikTok do que Amazon Associates. Configurar o catálogo de
produtos no TikTok Shop é feito pelo TikTok Seller Center, fora do
escopo deste projeto.

## 6. Usar

```bash
# ver ideias sem gerar vídeo
python cli.py ideas --niche "finanças pessoais para jovens"

# gerar um vídeo (não posta, só salva em output/)
python cli.py run --niche "finanças pessoais para jovens"

# gerar e publicar no TikTok (modo privado até a auditoria)
python cli.py run --niche "finanças pessoais para jovens" --post

# usar uma ideia específica em vez de gerar uma
python cli.py run --idea "3 erros que fazem você perder dinheiro no PIX" --post
```

## 7. Agendamento automático (opcional)

```bash
python -m src.scheduler
```

Roda o pipeline todo dia num horário fixo (`SCHEDULE_HOUR` no `.env`,
padrão 18h). Por segurança, **só posta automaticamente se você definir
`POST_ON_SCHEDULE=true`** no `.env` — por padrão ele só gera o vídeo em
`output/` para você revisar antes de postar manualmente com `--post`.

## Estrutura

```
src/
  agents/idea_agent.py     -> gera ideias de vídeo (Claude)
  agents/script_agent.py   -> gera hook/roteiro/legenda/hashtags (Claude)
  video/tts.py             -> narração via edge-tts (gratuito, sem API key)
  video/builder.py         -> monta o vídeo final (moviepy/ffmpeg)
  tiktok/auth.py           -> fluxo OAuth2 (autorização e refresh de token)
  tiktok/client.py         -> Content Posting API (upload + publicação)
  orchestrator.py          -> junta tudo (ideia -> roteiro -> vídeo -> post)
  scheduler.py             -> execução recorrente opcional
cli.py                     -> interface de linha de comando
assets/                    -> seus clipes/imagens de fundo
output/                    -> vídeos e áudios gerados
```
