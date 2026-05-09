import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    QWEN_API_KEY: str
    QWEN_BASE_URL: str
    QWEN_MODEL: str

    MCP_SERVER_URL: str = "http://127.0.0.1:8056/sse"
    BAIDU_MAP_AK: str = ""

    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs/app.log")

    # ----------- Chunking / Retrieval -----------
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K: int = 5

    # ----------- Vector store (Chroma) -----------
    CHROMA_PERSIST_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "my_models",
                                           "vector_store", "chroma_db")

    # ----------- Embedding / Reranker -----------
    HF_ENDPOINT: str = "https://hf-mirror.com"
    EMBED_MODEL_ID: str = "BAAI/bge-m3"
    RERANK_MODEL_ID: str = "BAAI/bge-reranker-v2-m3"

    # ----------- Retriever thresholds -----------
    SUMMARY_SIMILARITY_THRESHOLD: float = 0.3
    QUESTION_SIMILARITY_THRESHOLD: float = 0.35
    BM25_RRF_POOL_MULTIPLIER: int = 3
    SEMANTIC_POOL_MULTIPLIER: int = 2

    # ----------- Post-retrieval -----------
    COMPRESSION_SIMILARITY_THRESHOLD: float = 0.4
    RRF_K: int = 60

    # ----------- MySQL (optional; for RAG database manager) -----------
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "123456"
    MYSQL_DATABASE: str = "advancedrag"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()