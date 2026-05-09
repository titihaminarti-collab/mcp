"""
最终检索模块 - 使用统一增强检索器
"""

from typing import List, Optional

from langchain_core.documents import Document

from ..config.settings import settings
from .enhanced_retrieve import UnifiedEnhancedRetriever
from .vector_store import VectorStore


class FinalRetrieval:
    """
    最终检索类 - 封装统一增强检索器
    """

    def __init__(self, vectordb: VectorStore | None = None, db_manager=None):
        self.vectordb = vectordb or VectorStore()
        if db_manager is None:
            raise ValueError("FinalRetrieval 需要传入 MCP 的 DatabaseManager 实例")
        self.db_manager = db_manager

        self.retriever = UnifiedEnhancedRetriever(settings, self.vectordb, self.db_manager)
        self._restore_bm25_from_vectordb()

    def _restore_bm25_from_vectordb(self):
        """
        启动时，从 Chroma (child_docs) 中提取现有历史文本以重建 BM25 内存索引
        """
        try:
            existing_data = self.vectordb.child_vector_store.get()
            docs = existing_data.get("documents", [])
            metadatas = existing_data.get("metadatas", [])
            if docs:
                restored_docs = [
                    Document(page_content=doc, metadata=meta or {}) for doc, meta in zip(docs, metadatas)
                ]
                self.add_documents(restored_docs)
        except Exception:
            # 失败不阻塞服务启动
            return

    def add_documents(self, documents: List[Document]):
        self.retriever.add_documents_to_bm25(documents)

    def final_retrieve(self, query: str, document_ids: Optional[List[int]] = None) -> List[Document]:
        return self.retriever.retrieve(query, document_ids)

    def clear_bm25(self):
        self.retriever.clear_bm25_index()
