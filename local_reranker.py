import os
from pathlib import Path

from huggingface_hub import snapshot_download
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

from ..config.settings import settings


_LOCAL_RERANKER_CACHE: dict[str, HuggingFaceCrossEncoder] = {}


def get_local_reranker(model_id: str | None = None) -> HuggingFaceCrossEncoder:
    """
    返回本地 CrossEncoder 重排序模型（默认 bge-reranker-v2-m3）。

    - 本地缺失时自动下载到 `mcp_project/my_models/reranker_models/<model_name>`
    """
    os.environ["HF-ENDPOINT"] = settings.HF_ENDPOINT

    model_id = model_id or settings.RERANK_MODEL_ID
    if model_id in _LOCAL_RERANKER_CACHE:
        return _LOCAL_RERANKER_CACHE[model_id]

    root_dir = Path(__file__).resolve().parent.parent
    rerank_model_dir = root_dir / "my_models" / "reranker_models"
    rerank_model_dir.mkdir(parents=True, exist_ok=True)

    model_folder_name = model_id.split("/")[-1]
    local_save_path = rerank_model_dir / model_folder_name

    config_path = local_save_path / "config.json"
    if not config_path.exists():
        snapshot_download(
            repo_id=model_id,
            local_dir=local_save_path,
            ignore_patterns=["*.msgpack", "*.h5", "coreml/*", "*.DS_Store", "imgs/*"],
        )

    _LOCAL_RERANKER_CACHE[model_id] = HuggingFaceCrossEncoder(model_name=model_id)
    return _LOCAL_RERANKER_CACHE[model_id]

