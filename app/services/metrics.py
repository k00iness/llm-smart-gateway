import logging
from redis.asyncio import Redis

from app.core.config import settings
from app.models.response import MetricsResponse

logger = logging.getLogger(__name__)
KEY = "metrics:totals"


class MetricsService:
    def __init__(self):
        self.redis = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)

    async def record(self, *, cached: bool, latency_ms: float, tokens: int, fallback: bool = False):
        """Never raises: a metrics failure must not break a user request."""
        try:
            pipe = self.redis.pipeline()
            pipe.hincrby(KEY, "total_requests", 1)
            if cached:
                pipe.hincrby(KEY, "cache_hits", 1)
                pipe.hincrby(KEY, "tokens_saved", tokens)
                pipe.hincrbyfloat(KEY, "latency_cache_sum", latency_ms)
            else:
                pipe.hincrby(KEY, "cache_misses", 1)
                pipe.hincrby(KEY, "tokens_used", tokens)
                pipe.hincrbyfloat(KEY, "latency_llm_sum", latency_ms)
                if fallback:
                    pipe.hincrby(KEY, "fallbacks", 1)
            await pipe.execute()
        except Exception as e:
            logger.warning("Metrics recording failed: %s", e)

    async def snapshot(self) -> MetricsResponse:
        d = await self.redis.hgetall(KEY)
        total = int(d.get("total_requests", 0))
        hits = int(d.get("cache_hits", 0))
        misses = int(d.get("cache_misses", 0))
        saved = int(d.get("tokens_saved", 0))
        cache_sum = float(d.get("latency_cache_sum", 0))
        llm_sum = float(d.get("latency_llm_sum", 0))
        return MetricsResponse(
            total_requests=total,
            cache_hits=hits,
            cache_misses=misses,
            cache_hit_ratio=round(hits / total, 3) if total else 0.0,
            total_tokens_saved=saved,
            estimated_cost_saved_usd=round(saved / 1000 * settings.COST_PER_1K_TOKENS_USD, 6),
            avg_latency_ms=round((cache_sum + llm_sum) / total, 2) if total else 0.0,
            fallbacks=int(d.get("fallbacks", 0)),
            avg_latency_cache_ms=round(cache_sum / hits, 2) if hits else 0.0,
            avg_latency_llm_ms=round(llm_sum / misses, 2) if misses else 0.0,
        )


metrics_service = MetricsService()