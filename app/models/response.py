from typing import List, Optional
from pydantic import BaseModel, Field


class ResponseMessage(BaseModel):
    role: str = "assistant"
    content: str


class Choice(BaseModel):
    index: int = 0
    message: ResponseMessage
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage
    cached: bool = Field(default=False, description="Indique si la réponse provient du cache sémantique")
    latency_ms: float = Field(..., description="Temps de réponse en millisecondes")


class MetricsResponse(BaseModel):
    total_requests: int
    cache_hits: int
    cache_misses: int
    cache_hit_ratio: float
    total_tokens_saved: int
    estimated_cost_saved_usd: float
    avg_latency_ms: float
    fallbacks: int = 0
    avg_latency_cache_ms: float = 0.0
    avg_latency_llm_ms: float = 0.0