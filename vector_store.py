import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document

from ..config.settings import settings
from .embed import get_embed_model


class VectorStore:
    """
    向量存储（Chroma 持久化）：
    - parent_docs: 父块集合
    - child_docs: 子块集合
    """

    def __init__(self):
        self.embedding = get_embed_model()
        self.chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)

        self.parent_vector_store = Chroma(
            client=self.chroma_client,
            collection_name="parent_docs",
            embedding_function=self.embedding,
        )
        self.child_vector_store = Chroma(
            client=self.chroma_client,
            collection_name="child_docs",
            embedding_function=self.embedding,
        )

    def add_docs_to_vectorstore(self, parent_docs: list[Document], child_docs: list[Document], doc_id: int):
        """
        写入父块/子块到向量库，并为每个 chunk 写入 document_id 元数据。
        """
        for doc in parent_docs + child_docs:
            doc.metadata["document_id"] = doc_id

        parent_ids = self.parent_vector_store.add_documents(parent_docs)
        child_ids = self.child_vector_store.add_documents(child_docs)
        return parent_ids, child_ids

    def get_parent_docs(self, child_docs: list[Document]) -> list[Document]:
        parent_ids = set()
        for doc in child_docs:
            if "parent_id" in doc.metadata:
                parent_ids.add(doc.metadata["parent_id"])
        return self.get_parent_docs_by_metadata(list(parent_ids))

    def get_parent_docs_by_metadata(self, parent_ids: list[str]) -> list[Document]:
        if not parent_ids:
            return []

        parent_docs: list[Document] = []
        for parent_id in parent_ids:
            try:
                results = self.parent_vector_store.get(
                    where={"parent_id": parent_id},
                    include=["documents", "metadatas"],
                )
                docs = results.get("documents", []) or []
                metas = results.get("metadatas", []) or []
                for content, meta in zip(docs, metas):
                    parent_docs.append(Document(page_content=content, metadata=meta or {}))
            except Exception:
                continue
        return parent_docs

