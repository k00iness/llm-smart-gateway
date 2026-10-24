import asyncio
import logging
import re
import uuid
import time
from typing import Optional, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import settings
from app.services.embedding import embedding_service

logger = logging.getLogger(__name__)

OPPOSITES = [
    {"enable", "disable"}, {"add", "remove"}, {"install", "uninstall"},
    {"start", "stop"}, {"open", "close"}, {"on", "off"}, {"show", "hide"},
    {"allow", "block"}, {"increase", "decrease"}, {"include", "exclude"},
    {"lock", "unlock"}, {"encrypt", "decrypt"}, {"create", "delete"},
    {"before", "after"}, {"with", "without"}, {"true", "false"},
]
NEGATIONS = {"not", "no", "never", "without", "dont", "don't", "cannot", "can't"}


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z']+", text.lower()))


def _conflicting(a: str, b: str) -> bool:
    """True if two similar questions differ by an opposite word or a negation."""
    wa, wb = _words(a), _words(b)
    only_a, only_b = wa - wb, wb - wa
    for pair in OPPOSITES:
        if (pair & only_a) and (pair & only_b):
            return True
    return (NEGATIONS & wa) != (NEGATIONS & wb)


class SemanticCacheService:
    def __init__(self):
        self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        for attempt in range(15):
            try:
                self._ensure_collection_exists()
                break
            except Exception as e:
                logger.warning("Qdrant not ready (attempt %d): %s", attempt + 1, e)
                time.sleep(1)

    def _ensure_collection_exists(self):
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
            )

    def _search_sync(self, query_text: str) -> Optional[Dict[str, Any]]:
        try:
            query_vector = embedding_service.generate_embedding(query_text)
            if query_vector is None or len(query_vector) == 0:
                return None

            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=1,
                score_threshold=settings.SIMILARITY_THRESHOLD,
            )
            if response.points:
                hit = response.points[0]
                cached_query = hit.payload.get("query", "")
                if re.findall(r"\d+", cached_query) != re.findall(r"\d+", query_text):
                    return None  # same wording, different numbers: not the same question
                if _conflicting(cached_query, query_text):
                    return None  # opposite meaning (enable/disable, add/remove, negation)
                return {
                    "response": hit.payload.get("response"),
                    "score": hit.score,
                    "tokens": hit.payload.get("total_tokens", 0),
                }
            return None
        except Exception as e:
            logger.warning("Cache search failed: %s", e)
            return None

    def _save_sync(self, query_text: str, response_text: str, model: str = "", tokens: int = 0):
        try:
            vector = embedding_service.generate_embedding(query_text)
            if vector is None or len(vector) == 0:
                return
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={
                            "query": query_text,
                            "response": response_text,
                            "model": model,
                            "total_tokens": tokens,
                        },
                    )
                ],
            )
        except Exception as e:
            logger.warning("Cache save failed: %s", e)

    async def search_cache(self, query_text: str) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(self._search_sync, query_text)

    async def save_to_cache(self, query_text: str, response_text: str, model: str = "", tokens: int = 0):
        await asyncio.to_thread(self._save_sync, query_text, response_text, model, tokens)


semantic_cache_service = SemanticCacheService()