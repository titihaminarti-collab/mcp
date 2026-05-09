from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # FastAPI settings
    app_name: str = "Intelligent Connected Platform API"
    app_version: str = "1.0.0"
    app_description: str = "API for Intelligent Connected Platform"

    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000

    # CORS settings
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]  # Vue dev server

    # MCP settings (from existing config)
    mcp_server_url: str = "http://localhost:3000"  # Adjust as needed

    # logging
    log_level: str = "INFO"

    # Qwen settings
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-turbo"

    # Other settings can be added here

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()