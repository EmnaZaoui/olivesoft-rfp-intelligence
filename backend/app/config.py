from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://olivesoft:olivesoft_pwd@localhost:5432/olivesoft_rfp"
    ollama_host: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.1:8b"
    ollama_embed_model: str = "nomic-embed-text"
    embedding_dim: int = 768
    serper_api_key: str = ""
    mcp_server_url: str = "http://127.0.0.1:8100/sse"
    app_env: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()