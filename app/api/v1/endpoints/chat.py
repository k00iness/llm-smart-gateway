import logging
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException

from app.models.request import ChatCompletionRequest
from app.models.response import ChatCompletionResponse, Choice, ResponseMessage, Usage
from app.services.semantic_cache import semantic_cache_service
from app.services.llm_router import llm_router_service
from app.services.metrics import metrics_service
from app.core.rate_limiter import rate_limiter
from app.core.security import get_current_client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    client: str = Depends(get_current_client),
):
    start_time = time.time()

    # 1. Rate limit per authenticated client
    try:
        await rate_limiter.check_rate_limit(client)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Rate limit check failed: %s", e)

    # 2. Semantic cache lookup
    last_user_message = request.get_last_user_message()
    if last_user_message:
        cached_result = await semantic_cache_service.search_cache(last_user_message)
        if cached_result:
            latency = round((time.time() - start_time) * 1000, 2)
            await metrics_service.record(
                cached=True, latency_ms=latency, tokens=cached_result.get("tokens", 0)
            )
            return ChatCompletionResponse(
                id=f"chatcmpl-cache-{uuid.uuid4().hex[:8]}",
                created=int(time.time()),
                model="semantic-cache-hit",
                choices=[Choice(index=0,
                                message=ResponseMessage(role="assistant", content=cached_result["response"]),
                                finish_reason="stop")],
                usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                cached=True,
                latency_ms=latency,
            )

    # 3. LLM call through the router (with automatic fallback)
    result = await llm_router_service.generate_response(messages=request.messages)
    total_tokens = result.prompt_tokens + result.completion_tokens

    # 4. Save in the cache
    if last_user_message and result.content:
        await semantic_cache_service.save_to_cache(
            last_user_message, result.content, result.model, total_tokens
        )

    latency = round((time.time() - start_time) * 1000, 2)
    await metrics_service.record(
        cached=False, latency_ms=latency, tokens=total_tokens, fallback=result.fallback
    )

    shown_model = f"{result.model} (fallback)" if result.fallback else result.model
    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
        created=int(time.time()),
        model=shown_model,
        choices=[Choice(index=0,
                        message=ResponseMessage(role="assistant", content=result.content),
                        finish_reason="stop")],
        usage=Usage(prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    total_tokens=total_tokens),
        cached=False,
        latency_ms=latency,
    )