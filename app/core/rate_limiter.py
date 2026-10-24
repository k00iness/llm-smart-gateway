import time

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.core.config import settings


class RateLimiter:
    def __init__(self):
        self.redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )

    async def check_rate_limit(self, user_id: str):
        """Vérifie les limites par minute et par heure pour cet utilisateur."""
        now = int(time.time())
        minute_key = f"rate_limit:{user_id}:m:{now // 60}"
        hour_key = f"rate_limit:{user_id}:h:{now // 3600}"

        # Les 4 commandes partent ensemble : plus rapide, et INCR + EXPIRE restent liés
        pipe = self.redis_client.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 120)
        pipe.incr(hour_key)
        pipe.expire(hour_key, 7200)
        minute_count, _, hour_count, _ = await pipe.execute()

        if minute_count > settings.RATE_LIMIT_PER_MINUTE:
            retry_after = 60 - now % 60
            detail = f"Limite dépassée ({settings.RATE_LIMIT_PER_MINUTE} req/min)."
        elif hour_count > settings.RATE_LIMIT_PER_HOUR:
            retry_after = 3600 - now % 3600
            detail = f"Limite dépassée ({settings.RATE_LIMIT_PER_HOUR} req/heure)."
        else:
            return

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"{detail} Réessayez dans {retry_after} s.",
            headers={"Retry-After": str(retry_after)},
        )


rate_limiter = RateLimiter()