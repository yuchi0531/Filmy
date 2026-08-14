"""認証（fail-closed）・レート制限（XFFスプーフィング対策・メモリ掃除）のテスト。"""

import time

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

import app.rate_limit as rate_limit
from app.config import settings
from app.main import app


# --- 認証（fail-closed） ---


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_auth_fail_closed_in_production(monkeypatch, client):
    """production かつ APIキー未設定なら 503 を返す（fail-closed）。"""
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "api_key", "")

    r = client.get("/api/movies/now")
    assert r.status_code == 503


def test_auth_skipped_in_development(monkeypatch, client):
    """development かつ APIキー未設定なら認証をスキップする（既存テスト互換）。"""
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "api_key", "")

    # 認証スキップ後、実処理（スクレイパー）に入るため、ここでは認証由来の
    # 401/503 が返らないことを確認する（503 はスクレイパー側で変換され得るため、
    # 認証由来でないこと＝401 でないことを検証する）。
    r = client.get("/api/movies/now")
    assert r.status_code != 401
    assert r.status_code != 503 or r.json().get("detail") != "API key not configured"


def test_auth_valid_key_in_production(monkeypatch, client):
    """production で正しいキーを渡せば認証を通る（後続は処理次第）。"""
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "api_key", "secret-key")

    r = client.get("/api/movies/now", headers={"X-API-Key": "secret-key"})
    # 認証は通るので、認証由来の 401/503 ではないこと
    assert r.status_code != 401
    if r.status_code == 503:
        assert r.json().get("detail") != "API key not configured"


# --- レート制限: X-Forwarded-For スプーフィング対策 ---


def _make_request(client_host: str, headers: dict[str, str] | None = None) -> Request:
    """スコープから Request を構築するヘルパー。"""
    header_list = [
        (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "client": (client_host, 12345),
        "headers": header_list,
    }
    return Request(scope)


def test_client_ip_direct_no_trusted_proxy(monkeypatch):
    """信頼プロキシ未設定時は XFF を無視し、直結IPを使う（スプーフィング無効）。"""
    monkeypatch.setattr(settings, "trusted_proxies", "")
    req = _make_request("1.2.3.4", {"X-Forwarded-For": "9.9.9.9"})
    assert rate_limit._client_ip(req) == "1.2.3.4"


def test_client_ip_untrusted_proxy_ignores_xff(monkeypatch):
    """request.client.host が信頼プロキシにない場合は XFF を信頼しない。"""
    monkeypatch.setattr(settings, "trusted_proxies", "10.0.0.1")
    # 直結IPが 1.2.3.4（信頼プロキシ外）なら、XFF を無視して 1.2.3.4 を使う
    req = _make_request("1.2.3.4", {"X-Forwarded-For": "9.9.9.9"})
    assert rate_limit._client_ip(req) == "1.2.3.4"


def test_client_ip_trusted_proxy_uses_xff(monkeypatch):
    """信頼プロキシ経由なら XFF のクライアントIPを採用する。"""
    monkeypatch.setattr(settings, "trusted_proxies", "10.0.0.1")
    req = _make_request("10.0.0.1", {"X-Forwarded-For": "9.9.9.9"})
    assert rate_limit._client_ip(req) == "9.9.9.9"


def test_client_ip_trusted_proxy_chain_uses_last_untrusted(monkeypatch):
    """複数プロキシ経由（XFF = client, proxy1, proxy2）で末尾が信頼プロキシなら
    その1つ前（クライアント）を採用する。"""
    monkeypatch.setattr(settings, "trusted_proxies", "10.0.0.2")
    req = _make_request(
        "10.0.0.2", {"X-Forwarded-For": "9.9.9.9, 10.0.0.1, 10.0.0.2"}
    )
    assert rate_limit._client_ip(req) == "10.0.0.1"


# --- レート制限: メモリリーク対策（IPキーの掃除） ---


def test_rate_limit_removes_stale_ip_keys(monkeypatch):
    """60秒より古い記録しかないIPキーは辞書から削除される。"""
    monkeypatch.setattr(settings, "rate_limit_per_minute", 10)
    monkeypatch.setattr(settings, "trusted_proxies", "")

    # 古い記録を直接注入して、掃除対象のIPを作る
    stale = time.monotonic() - 120.0
    with rate_limit._lock:
        rate_limit._requests["old-ip"] = [stale]

    req = _make_request("new-ip")
    rate_limit.rate_limit(req)

    with rate_limit._lock:
        assert "old-ip" not in rate_limit._requests
        # 新しいIPは記録されている
        assert "new-ip" in rate_limit._requests


def test_rate_limit_enforces_limit(monkeypatch):
    """同一IPからのリクエストが上限を超えると 429 になる。"""
    monkeypatch.setattr(settings, "rate_limit_per_minute", 2)
    monkeypatch.setattr(settings, "trusted_proxies", "")

    req = _make_request("1.1.1.1")
    rate_limit.rate_limit(req)
    rate_limit.rate_limit(req)
    with pytest.raises(HTTPException) as exc:
        rate_limit.rate_limit(req)
    assert exc.value.status_code == 429
