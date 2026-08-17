"""One-time local OAuth2 flow to obtain a TikTok user access token.

Run: python -m src.tiktok.auth
Requires TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET and TIKTOK_REDIRECT_URI
(matching a redirect URI registered on your TikTok app) to be set in .env.

Prints the resulting access_token / refresh_token / open_id so you can
copy them into your .env — nothing is transmitted anywhere else.
"""
import http.server
import secrets
import threading
import urllib.parse
import webbrowser

import requests

from src.config import config

AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
SCOPES = "user.info.basic,video.publish"


def build_authorize_url(state: str) -> str:
    params = {
        "client_key": config.tiktok_client_key,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": config.tiktok_redirect_uri,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": config.tiktok_client_key,
            "client_secret": config.tiktok_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": config.tiktok_redirect_uri,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": config.tiktok_client_key,
            "client_secret": config.tiktok_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _run_local_flow() -> None:
    if not config.tiktok_client_key or not config.tiktok_client_secret:
        raise SystemExit(
            "Defina TIKTOK_CLIENT_KEY e TIKTOK_CLIENT_SECRET no .env antes de rodar isso."
        )

    state = secrets.token_urlsafe(16)
    result = {}
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if params.get("state", [""])[0] != state:
                self.wfile.write(b"<h1>Estado invalido. Feche esta aba e tente novamente.</h1>")
                return
            code = params.get("code", [None])[0]
            if not code:
                self.wfile.write(b"<h1>Autorizacao negada ou sem 'code'.</h1>")
                done.set()
                return
            result["code"] = code
            self.wfile.write("<h1>Autorizado! Pode fechar esta aba e voltar ao terminal.</h1>".encode())
            done.set()

    server = http.server.HTTPServer(("localhost", 8787), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = build_authorize_url(state)
    print(f"Abra esta URL e autorize o app no TikTok:\n\n{url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    done.wait(timeout=300)
    server.shutdown()

    if "code" not in result:
        raise SystemExit("Nao recebi o codigo de autorizacao a tempo.")

    token_data = exchange_code_for_token(result["code"])
    if "access_token" not in token_data:
        raise SystemExit(f"Falha ao trocar o codigo por token: {token_data}")

    print("\nSucesso! Copie estes valores para o seu .env:\n")
    print(f"TIKTOK_ACCESS_TOKEN={token_data['access_token']}")
    print(f"TIKTOK_REFRESH_TOKEN={token_data['refresh_token']}")
    print(f"TIKTOK_OPEN_ID={token_data['open_id']}")


def get_valid_access_token() -> str:
    """Refresh the access token using the stored refresh token.

    TikTok access tokens are short-lived; call this right before posting
    instead of relying on a possibly-stale TIKTOK_ACCESS_TOKEN.
    """
    if not config.tiktok_refresh_token:
        raise SystemExit(
            "TIKTOK_REFRESH_TOKEN nao configurado. Rode `python -m src.tiktok.auth` primeiro."
        )
    token_data = refresh_access_token(config.tiktok_refresh_token)
    if "access_token" not in token_data:
        raise SystemExit(f"Falha ao renovar o token: {token_data}")
    return token_data["access_token"]


if __name__ == "__main__":
    _run_local_flow()
