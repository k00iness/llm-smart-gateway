from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Application
    PROJECT_NAME: str = "LLM Smart Gateway"
    ENVIRONMENT: str = "development"
    PORT: int = 8000

    # Primary LLM
    GROQ_API_KEY: str = ""
    PRIMARY_MODEL: str = "openai/gpt-oss-20b"


    # Fallback LLM
    FALLBACK_LLM_URL: str = "http://localhost:11434/v1"
    FALLBACK_MODEL: str = "llama3"

    # Vector DB (Qdrant)
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "llm_cache"
    SIMILARITY_THRESHOLD: float = 0.93

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # Embeddings
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    LATENCY_THRESHOLD_SECONDS: float = 20.0
        # Authentification : "cle1:nom1,cle2:nom2"
    CLIENT_API_KEYS: str = ""
    ADMIN_API_KEY: str = ""

    # Limitation de débit, par clé API client
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    COST_PER_1K_TOKENS_USD: float = 0.0005   # rough price used to estimate savings
    MAX_COMPLETION_TOKENS: int = 4096
settings = Settings()