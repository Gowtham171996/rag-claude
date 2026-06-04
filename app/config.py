from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",   # silently drop any env vars not declared here
    )

    # Auth
    api_key: str

    # Ollama (LLM + embeddings — runs as Docker container)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:4b"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    embedding_dim: int = 1024  # qwen3-embedding:0.6b output dimension

    # Anthropic Claude (optional fallback LLM)
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # App
    log_level: str = "INFO"
    app_version: str = "1.0.0"


settings = Settings()
