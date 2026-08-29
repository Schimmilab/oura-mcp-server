#!/usr/bin/env python3
"""One-off Oura OAuth2 authorization.

Run this once (and again only if the refresh token is ever lost):

    python generate_tokens.py

It opens the Oura consent screen, catches the redirect on a short-lived local
HTTP server, exchanges the code and writes the token pair into ``.env``.

⚠️ Oura refresh tokens are single-use. Everything after this script rotates them
automatically; if that chain ever breaks, run this again.
"""

from __future__ import annotations

import asyncio
import secrets
import sys
import socket
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent / ".env")

from oura_mcp.api.auth import OuraAuth, OuraAuthError  # noqa: E402

_result: dict = {}


class _CallbackHandler(BaseHTTPRequestHandler):
    """Catches the single redirect Oura sends back to the redirect URI."""

    def do_GET(self):  # noqa: N802 - name mandated by BaseHTTPRequestHandler
        parsed = urlparse(self.path)

        # Browsers fetch /favicon.ico unprompted. Answering it here — instead of
        # letting it be mistaken for the callback — is why this server keeps
        # serving until a code actually arrives.
        if parsed.path.rstrip("/") not in ("", "/callback".rstrip("/")) or "code" not in parsed.query:
            if "error" not in parsed.query:
                self.send_response(204)
                self.end_headers()
                return

        query = parse_qs(parsed.query)
        _result["code"] = (query.get("code") or [None])[0]
        _result["state"] = (query.get("state") or [None])[0]
        _result["error"] = (query.get("error") or [None])[0]

        ok = _result["code"] and not _result["error"]
        body = (
            "<h2>Authorized.</h2><p>You can close this tab and return to the terminal.</p>"
            if ok
            else f"<h2>Authorization failed.</h2><pre>{_result.get('error')}</pre>"
        )
        self.send_response(200 if ok else 400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        """Silence the default stderr access log — it is noise here."""


async def main() -> int:
    auth = OuraAuth()

    missing = [
        name
        for name, value in (
            ("OURA_CLIENT_ID", auth.client_id),
            ("OURA_CLIENT_SECRET", auth.client_secret),
        )
        if not value
    ]
    if missing:
        print(f"⛔ Missing in .env: {', '.join(missing)}")
        print("   Register an application at https://cloud.ouraring.com/oauth/applications")
        return 2

    parsed = urlparse(auth.redirect_uri)
    host, port = parsed.hostname or "localhost", parsed.port or 80

    state = secrets.token_urlsafe(16)
    url = auth.get_authorization_url(state=state)

    # ⛔ Refuse to start if something else already owns the port. Without this the
    # OS may hand the callback to the other listener and the flow dies with a 404
    # that looks like an Oura problem — which is exactly what happened on 2026-08-29
    # (a pm2-managed static server held :8080).
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.settimeout(1)
    if probe.connect_ex((host if host != "0.0.0.0" else "127.0.0.1", port)) == 0:
        probe.close()
        print(f"⛔ Port {port} is already in use — the callback would go to that")
        print("   process instead of here. Free the port, or register a redirect URI")
        print("   on a free port in https://cloud.ouraring.com/oauth/applications")
        print(f"   and set OURA_REDIRECT_URI in .env to match it exactly.")
        return 2
    probe.close()

    server = HTTPServer((host, port), _CallbackHandler)
    server.timeout = 1

    def _serve_until_code():
        """Keep serving until the callback arrives — one request is not enough.

        The browser may hit /favicon.ico first; handling exactly one request would
        spend the server on that and never see the redirect.
        """
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline and not (_result.get("code") or _result.get("error")):
            server.handle_request()

    thread = threading.Thread(target=_serve_until_code, daemon=True)
    thread.start()

    print(f"── Opening the Oura consent screen …\n   {url}\n")
    webbrowser.open(url)
    print(f"   Waiting for the redirect on {auth.redirect_uri} …")

    thread.join(timeout=305)
    server.server_close()

    if not _result.get("code"):
        print(f"⛔ No authorization code received. {_result.get('error') or 'Timed out.'}")
        return 1

    # CSRF check: the state we sent must come back untouched.
    if _result.get("state") != state:
        print("⛔ State mismatch — aborting rather than trusting this redirect.")
        return 1

    try:
        await auth.exchange_code_for_token(_result["code"])
    except OuraAuthError as exc:
        print(f"⛔ {exc}")
        return 1

    print("✅ Tokens written to .env (OURA_ACCESS_TOKEN, OURA_REFRESH_TOKEN), mode 600.")
    print("   Verifying against the live API …")

    from oura_mcp.api.client import OuraClient  # noqa: E402
    from oura_mcp.utils.config import OuraAPIConfig  # noqa: E402

    client = OuraClient(OuraAPIConfig(), auth=auth)
    try:
        info = await client.get_personal_info()
        print(f"✅ Live call succeeded — API returned {len(info)} field(s).")
    except Exception as exc:  # noqa: BLE001 - report whatever the API said
        print(f"⚠️ Tokens stored, but the verification call failed: {exc}")
        return 1
    finally:
        await client.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
