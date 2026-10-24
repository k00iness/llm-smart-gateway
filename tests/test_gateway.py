import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.core.security import get_current_client
from app.main import app
from app.services.llm_router import LLMResult, llm_router_service
from app.services.metrics import metrics_service
from app.services.semantic_cache import _conflicting, semantic_cache_service

KEY = "test-key-123"
HEADERS = {"Authorization": f"Bearer {KEY}"}
BODY = {"messages": [{"role": "user", "content": "What is Redis?"}]}

client = TestClient(app)


@pytest.fixture(autouse=True)
def fake_services(monkeypatch):
    """Replace Redis, Qdrant and Groq with mocks so tests are fast and free."""
    monkeypatch.setattr(settings, "CLIENT_API_KEYS", f"{KEY}:tester")

    class Mocks:
        search = AsyncMock(return_value=None)               # default: cache miss
        save = AsyncMock()
        llm = AsyncMock(return_value=LLMResult(
            content="Redis is an in-memory store.", model="test-model",
            prompt_tokens=10, completion_tokens=20))
        limit = AsyncMock()
        record = AsyncMock()

    monkeypatch.setattr(semantic_cache_service, "search_cache", Mocks.search)
    monkeypatch.setattr(semantic_cache_service, "save_to_cache", Mocks.save)
    monkeypatch.setattr(llm_router_service, "generate_response", Mocks.llm)
    monkeypatch.setattr(rate_limiter, "check_rate_limit", Mocks.limit)
    monkeypatch.setattr(metrics_service, "record", Mocks.record)
    return Mocks


# ---------- cache guards ----------

def test_opposites_are_conflicting():
    assert _conflicting("How do I enable dark mode?", "How do I disable dark mode?")
    assert _conflicting("How do I add a user?", "How do I remove a user?")


def test_negation_is_conflicting():
    assert _conflicting("Can I use this?", "Can I not use this?")


def test_paraphrase_is_not_conflicting():
    assert not _conflicting("What is a REST API?", "Explain what a REST API is.")


# ---------- authentication ----------

def test_valid_key_returns_client_name():
    assert asyncio.run(get_current_client(f"Bearer {KEY}")) == "tester"


@pytest.mark.parametrize("header", [None, "", "Bearer wrong-key", "wrong-key", "Bearer "])
def test_bad_keys_are_rejected(header):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_client(header))
    assert exc.value.status_code == 401


def test_endpoint_requires_key():
    assert client.post("/v1/chat/completions", json=BODY).status_code == 401


# ---------- endpoint behaviour ----------

def test_cache_miss_calls_llm_and_saves(fake_services):
    r = client.post("/v1/chat/completions", json=BODY, headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["cached"] is False
    assert data["model"] == "test-model"
    assert data["usage"]["total_tokens"] == 30          # real counts, not fake ones
    fake_services.llm.assert_awaited_once()
    fake_services.save.assert_awaited_once()


def test_cache_hit_skips_llm(fake_services):
    fake_services.search.return_value = {"response": "cached answer", "score": 0.99, "tokens": 50}
    r = client.post("/v1/chat/completions", json=BODY, headers=HEADERS)
    data = r.json()
    assert data["cached"] is True
    assert data["model"] == "semantic-cache-hit"
    assert data["choices"][0]["message"]["content"] == "cached answer"
    fake_services.llm.assert_not_awaited()               # no LLM call, no cost


def test_fallback_is_labelled(fake_services):
    fake_services.llm.return_value = LLMResult(
        content="from llama3", model="llama3", fallback=True)
    r = client.post("/v1/chat/completions", json=BODY, headers=HEADERS)
    assert r.json()["model"] == "llama3 (fallback)"


def test_rate_limit_returns_429(fake_services):
    fake_services.limit.side_effect = HTTPException(
        status_code=429, detail="Limit exceeded", headers={"Retry-After": "30"})
    r = client.post("/v1/chat/completions", json=BODY, headers=HEADERS)
    assert r.status_code == 429
    assert r.headers["Retry-After"] == "30"
    fake_services.llm.assert_not_awaited()


# ---------- metrics access ----------

def test_metrics_rejects_client_key():
    assert client.get("/v1/metrics", headers=HEADERS).status_code == 401