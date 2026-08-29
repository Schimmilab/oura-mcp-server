"""OAuth2 authentication for the Oura API.

Oura deprecated Personal Access Tokens in August 2026: existing ones keep working
for a while, new ones cannot be created. This module implements the authorization
code flow described at https://cloud.ouraring.com/docs/authentication.

⛔ The critical difference to most OAuth2 providers — and the reason this module is
more careful than it looks: **Oura refresh tokens are single-use.** The docs state
"The refresh token is single-use and invalidated after use". If a refresh succeeds
but persisting the new pair fails, or two processes refresh concurrently, the
account is locked out and the user must re-authorize interactively.

Two mechanisms guard against that:

1. **A file lock** around the whole refresh. Several MCP server processes can run at
   once (one per client session, plus cron jobs), and without the lock they would
   race to spend the same single-use token.
2. **An atomic write** (temp file + ``os.replace``) so a crash mid-write cannot leave
   a truncated ``.env`` behind — which would lose the only copy of the new token.

Inside the lock the tokens are re-read from disk first: if another process already
refreshed while we waited, we adopt its result instead of burning a second token.
"""

from __future__ import annotations

import base64
import fcntl
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx

# Endpoints — verified against https://cloud.ouraring.com/docs/authentication (2026-08-29)
AUTH_URL = "https://cloud.ouraring.com/oauth/authorize"
TOKEN_URL = "https://api.ouraring.com/oauth/token"

# Refresh this long before nominal expiry.
REFRESH_SKEW = timedelta(minutes=5)


class OuraAuthError(Exception):
    """Raised when authentication cannot be completed or repaired automatically."""


class OuraAuth:
    """Holds Oura OAuth2 credentials and keeps the access token valid.

    Tokens live in the project ``.env`` so that a rotation performed by one process
    is visible to the next one without a restart.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        env_file: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("OURA_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("OURA_CLIENT_SECRET")
        self.redirect_uri = (
            redirect_uri
            or os.getenv("OURA_REDIRECT_URI")
            or "http://localhost:8080/callback"
        )

        self._env_file_override = env_file
        self._env_file_cached: Optional[Path] = None

        self.access_token: Optional[str] = os.getenv("OURA_ACCESS_TOKEN") or None
        self.refresh_token: Optional[str] = os.getenv("OURA_REFRESH_TOKEN") or None
        self.token_expires_at: Optional[datetime] = None

    # ------------------------------------------------------------------ paths

    @property
    def env_file(self) -> Path:
        """Path to the ``.env`` that stores the tokens (project root)."""
        if self._env_file_cached is None:
            if self._env_file_override:
                self._env_file_cached = Path(self._env_file_override)
            else:
                # src/oura_mcp/api/auth.py -> project root
                self._env_file_cached = Path(__file__).resolve().parents[3] / ".env"
        return self._env_file_cached

    @property
    def _lock_file(self) -> Path:
        return self.env_file.with_name(self.env_file.name + ".lock")

    @contextmanager
    def _token_lock(self, timeout_note: str = ""):
        """Serialize token refreshes across processes.

        Oura's refresh tokens are single-use, so two processes refreshing at the same
        time would spend the same token and one of them would be left with a dead
        credential. ``flock`` is advisory but sufficient here: every writer goes
        through this one code path.
        """
        self._lock_file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._lock_file, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    # ------------------------------------------------------------- env access

    def _read_env(self) -> dict:
        """Parse the ``.env`` into a dict. Missing file yields an empty dict."""
        values: dict[str, str] = {}
        if not self.env_file.exists():
            return values
        try:
            for line in self.env_file.read_text().splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                values[key.strip()] = value.strip()
        except OSError:
            return {}
        return values

    def reload_tokens_from_env(self) -> None:
        """Adopt tokens written by another process or a fresh authorization.

        Called before every refresh so that a rotation performed elsewhere is picked
        up instead of being overwritten with a stale value.
        """
        values = self._read_env()
        if values.get("OURA_ACCESS_TOKEN"):
            self.access_token = values["OURA_ACCESS_TOKEN"]
        if values.get("OURA_REFRESH_TOKEN"):
            self.refresh_token = values["OURA_REFRESH_TOKEN"]

    def _save_tokens_to_env(self) -> None:
        """Persist the current token pair atomically, preserving other keys.

        Written to a temp file in the same directory and then ``os.replace``d, so a
        crash mid-write cannot truncate the file. Losing the ``.env`` here would mean
        losing the only copy of a single-use refresh token.
        """
        if not self.access_token or not self.refresh_token:
            return

        values = self._read_env()
        values["OURA_ACCESS_TOKEN"] = self.access_token
        values["OURA_REFRESH_TOKEN"] = self.refresh_token

        target = self.env_file
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(target.parent), prefix=".env.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as handle:
                for key, value in values.items():
                    handle.write(f"{key}={value}\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, target)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        # Keep this process's environment in step with what was just written.
        os.environ["OURA_ACCESS_TOKEN"] = self.access_token
        os.environ["OURA_REFRESH_TOKEN"] = self.refresh_token

    # ------------------------------------------------------------------- flow

    def get_authorization_url(self, state: str = "", scope: str = "") -> str:
        """Build the consent URL.

        ``scope`` is deliberately empty by default: Oura requests every scope the
        application was registered with when the parameter is blank. Keeping the
        scope list in the application registration rather than in code means there is
        exactly one place to change it, and no hard-coded scope name can drift out of
        sync with the portal.
        """
        if not self.client_id:
            raise OuraAuthError("OURA_CLIENT_ID is not set — add it to .env")

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        if scope:
            params["scope"] = scope
        if state:
            params["state"] = state
        query = "&".join(f"{k}={httpx.QueryParams({k: v})[k]}" for k, v in params.items())
        return f"{AUTH_URL}?{query}"

    def _basic_auth_header(self) -> dict:
        """Client credentials via HTTP Basic, as the Oura docs allow.

        Preferred over form fields so the secret does not end up in request bodies
        that get logged by intermediaries.
        """
        raw = f"{self.client_id}:{self.client_secret}".encode()
        return {"Authorization": "Basic " + base64.b64encode(raw).decode()}

    def _apply_token_response(self, data: dict) -> None:
        access = data.get("access_token")
        refresh = data.get("refresh_token")
        if not access:
            raise OuraAuthError(f"Token response contained no access_token: {data}")
        self.access_token = access
        if refresh:
            self.refresh_token = refresh
        expires_in = data.get("expires_in")
        self.token_expires_at = (
            datetime.now() + timedelta(seconds=int(expires_in)) if expires_in else None
        )

    async def exchange_code_for_token(self, code: str, save: bool = True) -> dict:
        """Trade the authorization code for a token pair."""
        if not self.client_id or not self.client_secret:
            raise OuraAuthError("OURA_CLIENT_ID / OURA_CLIENT_SECRET are not set")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers=self._basic_auth_header(),
            )
        if response.status_code >= 400:
            raise OuraAuthError(
                f"Code exchange failed ({response.status_code}): {response.text}"
            )

        data = response.json()
        with self._token_lock():
            self._apply_token_response(data)
            if save:
                self._save_tokens_to_env()
        return data

    async def refresh_access_token(self, save: bool = True) -> dict:
        """Spend the refresh token for a new pair.

        Holds the cross-process lock for the whole operation and re-reads the stored
        tokens first, so a refresh that another process completed while we waited is
        adopted rather than duplicated.
        """
        if not self.client_id or not self.client_secret:
            raise OuraAuthError("OURA_CLIENT_ID / OURA_CLIENT_SECRET are not set")

        with self._token_lock():
            previous_refresh = self.refresh_token
            self.reload_tokens_from_env()

            # Someone else refreshed while we waited for the lock: their token pair is
            # the live one. Spending ours would invalidate theirs.
            if (
                previous_refresh
                and self.refresh_token
                and self.refresh_token != previous_refresh
            ):
                return {"access_token": self.access_token, "reused": True}

            if not self.refresh_token:
                raise OuraAuthError(
                    "No refresh token available — run `python generate_tokens.py` "
                    "to authorize once."
                )

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                    },
                    headers=self._basic_auth_header(),
                )

            if response.status_code >= 400:
                raise OuraAuthError(
                    "Refresh failed — the refresh token is single-use and may already "
                    "have been spent. Re-authorize with `python generate_tokens.py`. "
                    f"Oura responded {response.status_code}: {response.text}"
                )

            data = response.json()
            self._apply_token_response(data)
            if save:
                self._save_tokens_to_env()
            return data

    # ------------------------------------------------------------ token usage

    async def ensure_valid_token(self) -> None:
        """Make sure ``access_token`` is usable, refreshing pre-emptively if needed."""
        if not self.access_token:
            self.reload_tokens_from_env()
        if not self.access_token and not self.refresh_token:
            raise OuraAuthError(
                "No Oura credentials found. Run `python generate_tokens.py` once to "
                "authorize this application."
            )
        if not self.access_token:
            await self.refresh_access_token()
            return

        # Tokens loaded from .env carry no expiry. Rather than guess one, use the
        # token and let a 401 drive the refresh — that path re-reads .env, so an
        # externally rotated token heals itself.
        if self.token_expires_at is None:
            return

        if datetime.now() >= self.token_expires_at - REFRESH_SKEW:
            await self.refresh_access_token()

    def get_headers(self) -> dict:
        if not self.access_token:
            raise OuraAuthError("No access token available")
        return {"Authorization": f"Bearer {self.access_token}"}
