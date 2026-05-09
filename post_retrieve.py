from __future__ import annotations

from typing import List

from langchain_core.documents import Document
from langchain_community.document_transformers import EmbeddingsRedundantFilter, LongContextReorder
from langchain_classic.retrievers.document_compressors import (
    CrossEncoderReranker,
    DocumentCompressorPipeline,
    EmbeddingsFilter,
)

from ..config.settings import settings
from .embed import get_embed_model


class PostRetrievalProcessor:
    """
    检索后处理流水线：
    1. RRF 融合
    2. 上下文压缩（去冗余 + 相似度过滤）
    3. Cross-Encoder 精排
    4. LongContextReorder（解决 Lost-in-the-Middle）
    """

    def __init__(self, config, reranker_model=None):
        self.config = config
        self.embeddings_model = get_embed_model()
        self.reranker_model = reranker_model

    def reciprocal_rank_fusion(self, results: List[List[Document]], k: int | None = None) -> List[Document]:
        k = k or self.config.RRF_K
        fused_scores: dict[tuple[str, str | None], float] = {}
        doc_map: dict[tuple[str, str | None], Document] = {}

        for docs in results:
            for rank, doc in enumerate(docs):
                key = (doc.page_content, doc.metadata.get("parent_id"))
                if key not in fused_scores:
                    fused_scores[key] = 0.0
                    doc_map[key] = doc
                fused_scores[key] += 1 / (rank + k)

        sorted_keys = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)
        return [doc_map[key] for key in sorted_keys]

    def context_compression(
        self,
        docs: List[Document],
        query: str,
        similarity_threshold: float | None = None,
    ) -> List[Document]:
        if not docs:
            return []

        similarity_threshold = similarity_threshold or self.config.COMPRESSION_SIMILARITY_THRESHOLD

        redundant_filter = EmbeddingsRedundantFilter(embeddings=self.embeddings_model)
        relevant_filter = EmbeddingsFilter(embeddings=self.embeddings_model, similarity_threshold=similarity_threshold)
        pipeline = DocumentCompressorPipeline(transformers=[redundant_filter, relevant_filter])
        return pipeline.compress_documents(docs, query)

    def rerank(self, docs: List[Document], query: str, top_k: int) -> List[Document]:
        if not self.reranker_model or not docs:
            return docs[:top_k]
        reranker = CrossEncoderReranker(model=self.reranker_model, top_n=top_k)
        return reranker.compress_documents(docs, query)

    def long_context_reorder(self, docs: List[Document]) -> List[Document]:
        if not docs:
            return []
        return LongContextReorder().transform_documents(docs)

    def process(self, original_query: str, retrieval_results: List[List[Document]], top_k: int) -> List[Document]:
        fused_docs = self.reciprocal_rank_fusion(retrieval_results)
        compressed_docs = self.context_compression(fused_docs, original_query)
        reranked_docs = self.rerank(compressed_docs, original_query, top_k=top_k)
        return self.long_context_reorder(reranked_docs)
