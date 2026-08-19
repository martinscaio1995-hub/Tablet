"""Dashboard web: ver tendências, decidir se vale a pena criar conteúdo,
gerar roteiro/vídeo/imagem/música, e acompanhar vendas.

Rodar: python cli.py webapp   (ou uvicorn src.webapp.app:app --host 0.0.0.0 --port 8000)
"""
import json
import os
import time
import urllib.parse

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src import store
from src.agents.script_agent import write_script
from src.agents.trends_agent import research_trends
from src.agents.viability_agent import score_viability
from src.config import config
from src.integrations.gemini_client import GeminiError, generate_image
from src.integrations.music_client import MusicGenerationError, generate_music
from src.video.builder import build_video
from src.video.tts import synthesize_narration

BASE_DIR = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app = FastAPI(title="Painel do canal")

static_dir = os.path.join(BASE_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def _startup():
    store.init_db()
    os.makedirs(config.output_dir, exist_ok=True)


def _redirect(path: str, ok: str | None = None, error: str | None = None) -> RedirectResponse:
    params = {}
    if ok:
        params["ok"] = ok
    if error:
        params["error"] = error
    qs = f"?{urllib.parse.urlencode(params)}" if params else ""
    return RedirectResponse(f"{path}{qs}", status_code=303)


def _sales_context_text() -> str:
    summary = store.sales_summary()
    if not summary["by_product"]:
        return ""
    lines = [
        f"- {p['product']}: R$ {p['total'] / 100:.2f} em {p['n']} venda(s)"
        for p in summary["by_product"]
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- dashboard --

@app.get("/")
def dashboard(request: Request, ok: str | None = None, error: str | None = None):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "active": "dashboard",
            "items": store.list_content(),
            "sales_summary": store.sales_summary(),
            "default_niche": config.content_niche,
            "ok": ok,
            "error": error,
        },
    )


@app.post("/trends/refresh")
def trends_refresh(niche: str = Form("")):
    niche = niche.strip() or config.content_niche
    try:
        trends = research_trends(niche, count=5)
    except Exception as e:  # noqa: BLE001 - superfície de erro pro usuário
        return _redirect("/", error=f"Falha ao pesquisar tendências: {e}")

    sales_context = _sales_context_text()
    for trend in trends:
        item_id = store.insert_trend(niche, trend)
        try:
            verdict = score_viability(
                niche=niche,
                topic=trend["topic"],
                why_now=trend["why_now"],
                angle=trend["angle"],
                product_tie_in=trend.get("product_tie_in", ""),
                sales_context=sales_context,
            )
            store.update_viability(
                item_id, verdict["score"], verdict["recommendation"], verdict["reasoning"]
            )
        except Exception:
            pass  # a tendência já foi salva; só fica sem nota de viabilidade

    return _redirect("/", ok=f"{len(trends)} tendência(s) pesquisada(s).")


# ------------------------------------------------------------------- content --

@app.get("/content/{item_id}")
def content_detail(request: Request, item_id: int, ok: str | None = None, error: str | None = None):
    item = store.get_content(item_id)
    if not item:
        return _redirect("/", error="Conteúdo não encontrado.")
    item["hashtags_list"] = json.loads(item["hashtags"]) if item.get("hashtags") else []
    return templates.TemplateResponse(
        "content_detail.html",
        {"request": request, "item": item, "ok": ok, "error": error},
    )


@app.post("/content/{item_id}/script")
def content_script(item_id: int):
    item = store.get_content(item_id)
    if not item:
        return _redirect("/", error="Conteúdo não encontrado.")
    try:
        script = write_script(
            item["angle"],
            language=config.content_language,
            affiliate_note=item["product_tie_in"] or config.affiliate_note,
        )
        store.update_script(item_id, item["angle"], script)
    except Exception as e:  # noqa: BLE001
        return _redirect(f"/content/{item_id}", error=f"Falha ao gerar roteiro: {e}")
    return _redirect(f"/content/{item_id}", ok="Roteiro gerado.")


@app.post("/content/{item_id}/video")
def content_video(item_id: int):
    item = store.get_content(item_id)
    if not item or not item["narration"]:
        return _redirect(f"/content/{item_id}", error="Gere o roteiro primeiro.")
    ts = int(time.time())
    audio_path = os.path.join(config.output_dir, f"narration_{item_id}_{ts}.mp3")
    video_path = os.path.join(config.output_dir, f"video_{item_id}_{ts}.mp4")
    try:
        synthesize_narration(item["narration"], config.tts_voice, audio_path)
        build_video(audio_path, item["narration"], config.assets_dir, video_path)
        store.update_asset(item_id, "video_path", video_path)
    except Exception as e:  # noqa: BLE001
        return _redirect(f"/content/{item_id}", error=f"Falha ao gerar vídeo: {e}")
    return _redirect(f"/content/{item_id}", ok="Vídeo gerado.")


@app.post("/content/{item_id}/image")
def content_image(item_id: int, prompt: str = Form("")):
    item = store.get_content(item_id)
    if not item:
        return _redirect("/", error="Conteúdo não encontrado.")
    final_prompt = prompt.strip() or (
        f"Arte de anúncio vertical para TikTok sobre: {item['angle']}. "
        f"Produto em destaque: {item['product_tie_in'] or item['topic']}. "
        "Estilo foto de produto realista, bem iluminado."
    )
    image_path = os.path.join(config.output_dir, f"imagem_{item_id}_{int(time.time())}.png")
    try:
        generate_image(final_prompt, image_path)
        store.update_asset(item_id, "image_path", image_path)
    except GeminiError as e:
        return _redirect(f"/content/{item_id}", error=str(e))
    except Exception as e:  # noqa: BLE001
        return _redirect(f"/content/{item_id}", error=f"Falha ao gerar imagem: {e}")
    return _redirect(f"/content/{item_id}", ok="Imagem gerada.")


@app.post("/content/{item_id}/music")
def content_music(item_id: int, prompt: str = Form("")):
    item = store.get_content(item_id)
    if not item:
        return _redirect("/", error="Conteúdo não encontrado.")
    final_prompt = prompt.strip() or (
        f"Trilha instrumental curta para vídeo curto de TikTok sobre: "
        f"{item['angle']}. Sem vocais, energia condizente com o tema."
    )
    music_path = os.path.join(config.output_dir, f"musica_{item_id}_{int(time.time())}.mp3")
    try:
        generate_music(final_prompt, music_path)
        store.update_asset(item_id, "music_path", music_path)
    except MusicGenerationError as e:
        return _redirect(f"/content/{item_id}", error=str(e))
    except Exception as e:  # noqa: BLE001
        return _redirect(f"/content/{item_id}", error=f"Falha ao gerar música: {e}")
    return _redirect(f"/content/{item_id}", ok="Música gerada.")


@app.post("/content/{item_id}/posted")
def content_mark_posted(item_id: int):
    store.mark_posted(item_id)
    return _redirect(f"/content/{item_id}", ok="Marcado como postado.")


# --------------------------------------------------------------------- sales --

@app.get("/sales")
def sales_page(request: Request, ok: str | None = None, error: str | None = None):
    return templates.TemplateResponse(
        "sales.html",
        {
            "request": request,
            "active": "sales",
            "sales": store.list_sales(),
            "summary": store.sales_summary(),
            "ok": ok,
            "error": error,
        },
    )


@app.post("/sales")
def sales_add(
    product: str = Form(...),
    revenue: float = Form(...),
    sale_date: str = Form(...),
    note: str = Form(""),
    content_item_id: int | None = Form(None),
):
    store.add_sale(
        sale_date=sale_date,
        product=product,
        revenue_cents=round(revenue * 100),
        source="manual",
        note=note,
        content_item_id=content_item_id,
    )
    if content_item_id:
        return _redirect(f"/content/{content_item_id}", ok="Venda registrada.")
    return _redirect("/sales", ok="Venda registrada.")
