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

    # --- Apify (option alternative de détection) ---
    apify_api_token: str = ""
    apify_search_actor: str = "apify/google-search-scraper"
    apify_crawler_actor: str = "apify/website-content-crawler"
    apify_country_code: str = "tn"
    apify_language_code: str = "fr"
    apify_custom_actor_id: str = ""
    apify_custom_actor_input: str = "{}"

    class Config:
        env_file = ".env"


settings = Settings()