import os
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from huggingface_hub import snapshot_download

from ..config.settings import settings


_LOCAL_EMBEDDER_CACHE: dict[str, HuggingFaceEmbeddings] = {}


def get_embed_model(model_id: str | None = None) -> HuggingFaceEmbeddings:
    """
    返回一个可复用的 Embedding 模型（默认 bge-m3）。

    说明：
    - 如果本地没有模型，会自动下载到 `mcp_project/my_models/embedding_models/<model_name>`
    - 与 Advanced RAG 保持一致的“本地优先”策略
    """
    os.environ["HF-ENDPOINT"] = settings.HF_ENDPOINT

    model_id = model_id or settings.EMBED_MODEL_ID
    if model_id in _LOCAL_EMBEDDER_CACHE:
        return _LOCAL_EMBEDDER_CACHE[model_id]

    root_dir = Path(__file__).resolve().parent.parent
    embed_model_dir = root_dir / "my_models" / "embedding_models"
    embed_model_dir.mkdir(parents=True, exist_ok=True)

    model_folder_name = model_id.split("/")[-1]
    local_save_path = embed_model_dir / model_folder_name

    config_path = local_save_path / "config.json"
    if not config_path.exists():
        snapshot_download(
            repo_id=model_id,
            local_dir=local_save_path,
            ignore_patterns=["*.msgpack", "*.h5", "coreml/*", "*.DS_Store", "imgs/*"],
        )

    _LOCAL_EMBEDDER_CACHE[model_id] = HuggingFaceEmbeddings(
        model_name=str(local_save_path) if local_save_path.exists() else model_id,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    return _LOCAL_EMBEDDER_CACHE[model_id]
