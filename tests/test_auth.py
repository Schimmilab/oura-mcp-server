"""Tests for the OAuth2 token lifecycle.

The cases here are the ones that can actually lock the user out, because Oura's
refresh tokens are single-use: a lost write, or two processes refreshing at once,
costs an interactive re-authorization.
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oura_mcp.api.auth import OuraAuth, OuraAuthError  # noqa: E402


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    """An isolated .env, with the process environment cleared of Oura keys."""
    for key in (
        "OURA_ACCESS_TOKEN",
        "OURA_REFRESH_TOKEN",
        "OURA_CLIENT_ID",
        "OURA_CLIENT_SECRET",
        "OURA_REDIRECT_URI",
    ):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / ".env"
    path.write_text("LOG_LEVEL=INFO\nOURA_ACCESS_TOKEN=old_access\nOURA_REFRESH_TOKEN=old_refresh\n")
    return path


def _auth(env_file):
    return OuraAuth(
        client_id="cid", client_secret="csecret", env_file=str(env_file)
    )


def test_reads_tokens_from_env_file(env_file):
    auth = _auth(env_file)
    auth.reload_tokens_from_env()
    assert auth.access_token == "old_access"
    assert auth.refresh_token == "old_refresh"


def test_save_preserves_unrelated_keys_and_is_mode_600(env_file):
    auth = _auth(env_file)
    auth.access_token, auth.refresh_token = "new_access", "new_refresh"
    auth._save_tokens_to_env()

    content = env_file.read_text()
    assert "LOG_LEVEL=INFO" in content, "unrelated keys must survive a token write"
    assert "OURA_ACCESS_TOKEN=new_access" in content
    assert "OURA_REFRESH_TOKEN=new_refresh" in content
    assert oct(env_file.stat().st_mode)[-3:] == "600"


def test_save_leaves_no_temp_files_behind(env_file):
    auth = _auth(env_file)
    auth.access_token, auth.refresh_token = "a", "b"
    auth._save_tokens_to_env()
    leftovers = [p.name for p in env_file.parent.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == [], f"atomic write left temp files: {leftovers}"


def test_refresh_adopts_a_pair_another_process_already_wrote(env_file):
    """The single-use guard: don't spend our token if someone else already rotated.

    Without this, two concurrent processes burn two refresh tokens and the loser is
    left holding a dead credential.
    """
    auth = _auth(env_file)
    auth.reload_tokens_from_env()

    # Simulate another process finishing a refresh while we were blocked on the lock.
    env_file.write_text(
        "LOG_LEVEL=INFO\nOURA_ACCESS_TOKEN=fresh_access\nOURA_REFRESH_TOKEN=fresh_refresh\n"
    )

    async def must_not_be_called(*_a, **_kw):  # pragma: no cover - guard
        raise AssertionError("refresh was sent although another process had rotated")

    result = asyncio.run(auth.refresh_access_token())
    assert result.get("reused") is True
    assert auth.access_token == "fresh_access"
    assert auth.refresh_token == "fresh_refresh"


def test_refresh_without_token_names_the_repair_step(env_file):
    env_file.write_text("LOG_LEVEL=INFO\n")
    auth = _auth(env_file)
    auth.access_token = auth.refresh_token = None
    with pytest.raises(OuraAuthError, match="generate_tokens.py"):
        asyncio.run(auth.refresh_access_token())


def test_authorization_url_omits_scope_by_default(env_file):
    """Blank scope makes Oura grant every scope the application is registered with.

    Keeping the scope list in the portal rather than in code means it cannot drift.
    """
    url = _auth(env_file).get_authorization_url(state="xyz")
    assert url.startswith("https://cloud.ouraring.com/oauth/authorize?")
    assert "response_type=code" in url
    assert "client_id=cid" in url
    assert "state=xyz" in url
    assert "scope=" not in url


def test_authorization_url_requires_client_id(env_file, monkeypatch):
    monkeypatch.delenv("OURA_CLIENT_ID", raising=False)
    auth = OuraAuth(client_id=None, client_secret="s", env_file=str(env_file))
    with pytest.raises(OuraAuthError, match="OURA_CLIENT_ID"):
        auth.get_authorization_url()


def test_get_headers_uses_bearer(env_file):
    auth = _auth(env_file)
    auth.access_token = "abc"
    assert auth.get_headers() == {"Authorization": "Bearer abc"}


def test_ensure_valid_token_without_any_credentials_explains_itself(env_file):
    env_file.write_text("LOG_LEVEL=INFO\n")
    auth = _auth(env_file)
    auth.access_token = auth.refresh_token = None
    with pytest.raises(OuraAuthError, match="generate_tokens.py"):
        asyncio.run(auth.ensure_valid_token())
