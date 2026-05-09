from __future__ import annotations

from typing import List, Optional

import jieba
import numpy as np
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from ..config.settings import settings
from .database import ChildChunk, ParentChunk
from .embed import get_embed_model
from .local_reranker import get_local_reranker
from .post_retrieve import PostRetrievalProcessor
from .vector_store import VectorStore


class UnifiedEnhancedRetriever:
    def __init__(self, config, vector_store: VectorStore, db_manager):
        self.config = config
        self.vector_store = vector_store
        self.db_manager = db_manager

        self.embed_model = get_embed_model()
        self.reranker = get_local_reranker()
        self.top_k = config.TOP_K

        self.bm25: Optional[BM25Okapi] = None
        self.bm25_documents: list[Document] = []
        self.bm25_corpus: list[list[str]] = []

        self.post_processor = PostRetrievalProcessor(config=config, reranker_model=self.reranker)

    # -------- BM25 索引管理 --------
    def add_documents_to_bm25(self, documents: List[Document]):
        if not documents:
            return
        self.bm25_documents.extend(documents)
        for doc in documents:
            self.bm25_corpus.append(list(jieba.cut(doc.page_content)))
        self.bm25 = BM25Okapi(self.bm25_corpus)

    def clear_bm25_index(self):
        self.bm25 = None
        self.bm25_documents = []
        self.bm25_corpus = []

    # -------- 多路召回 --------
    def _semantic_search(self, query: str, document_ids: Optional[List[int]] = None) -> List[Document]:
        try:
            search_kwargs = {"k": self.top_k * self.config.SEMANTIC_POOL_MULTIPLIER}
            if document_ids:
                search_kwargs["filter"] = {"document_id": {"$in": [int(i) for i in document_ids]}}
            retriever = self.vector_store.child_vector_store.as_retriever(search_kwargs=search_kwargs)
            return retriever.invoke(query)
        except Exception:
            return []

    def _bm25_search(self, query: str) -> List[Document]:
        if self.bm25 is None or not self.bm25_documents:
            return []
        try:
            tokenized_query = list(jieba.cut(query))
            scores = self.bm25.get_scores(tokenized_query)
            top_k = min(self.top_k * self.config.BM25_RRF_POOL_MULTIPLIER, len(scores))
            top_indices = np.argsort(scores)[::-1][:top_k]

            results: list[Document] = []
            for idx in top_indices:
                if scores[idx] > 0:
                    doc = self.bm25_documents[idx]
                    doc.metadata["bm25_score"] = float(scores[idx])
                    results.append(doc)
            return results
        except Exception:
            return []

    def _summary_search(self, query: str) -> List[Document]:
        session = self.db_manager.get_session()
        try:
            child_chunks = session.query(ChildChunk).filter(ChildChunk.summary.isnot(None)).all()
            if not child_chunks:
                return []

            query_embedding = self.embed_model.embed_query(query)
            threshold = self.config.SUMMARY_SIMILARITY_THRESHOLD

            scored: list[tuple[Document, float]] = []
            for chunk in child_chunks:
                if not chunk.summary:
                    continue
                summary_embedding = self.embed_model.embed_query(chunk.summary)
                similarity = float(
                    np.dot(query_embedding, summary_embedding)
                    / (np.linalg.norm(query_embedding) * np.linalg.norm(summary_embedding) + 1e-8)
                )
                if similarity <= threshold:
                    continue

                parent = session.query(ParentChunk).filter(ParentChunk.id == chunk.parent_chunk_id).first()
                if not parent:
                    continue

                scored.append(
                    (
                        Document(
                            page_content=parent.content,
                            metadata={
                                "parent_id": parent.parent_id,
                                "child_id": chunk.child_id,
                                "summary": chunk.summary,
                                "retrieval_method": "summary",
                                "summary_score": similarity,
                            },
                        ),
                        similarity,
                    )
                )

            seen = set()
            unique: list[Document] = []
            for doc, score in sorted(scored, key=lambda x: x[1], reverse=True):
                pid = doc.metadata.get("parent_id")
                if pid in seen:
                    continue
                seen.add(pid)
                doc.metadata["summary_score"] = score
                unique.append(doc)
            return unique[: self.top_k * self.config.SEMANTIC_POOL_MULTIPLIER]
        except Exception:
            return []
        finally:
            session.close()

    def _hypothetical_question_search(self, query: str) -> List[Document]:
        session = self.db_manager.get_session()
        try:
            parent_chunks = session.query(ParentChunk).filter(ParentChunk.hypothetic_questions.isnot(None)).all()
            if not parent_chunks:
                return []

            query_embedding = self.embed_model.embed_query(query)
            threshold = self.config.QUESTION_SIMILARITY_THRESHOLD

            scored: list[tuple[Document, float]] = []
            for chunk in parent_chunks:
                questions = chunk.hypothetic_questions or []
                if isinstance(questions, str):
                    # 兼容历史存储为字符串的情况
                    try:
                        import json

                        questions = json.loads(questions)
                    except Exception:
                        questions = []

                best_q = ""
                best_sim = 0.0
                for q in questions:
                    if not q:
                        continue
                    q_emb = self.embed_model.embed_query(q)
                    sim = float(
                        np.dot(query_embedding, q_emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(q_emb) + 1e-8)
                    )
                    if sim > best_sim:
                        best_sim = sim
                        best_q = q

                if best_sim <= threshold:
                    continue

                scored.append(
                    (
                        Document(
                            page_content=chunk.content,
                            metadata={
                                "parent_id": chunk.parent_id,
                                "matched_question": best_q,
                                "retrieval_method": "hypothetical_question",
                                "question_score": best_sim,
                            },
                        ),
                        best_sim,
                    )
                )

            scored.sort(key=lambda x: x[1], reverse=True)
            docs: list[Document] = []
            for doc, score in scored[: self.top_k * self.config.SEMANTIC_POOL_MULTIPLIER]:
                doc.metadata["question_score"] = score
                docs.append(doc)
            return docs
        except Exception:
            return []
        finally:
            session.close()

    # -------- 父块关联 --------
    def _get_parent_documents(self, child_docs: List[Document]) -> List[Document]:
        if not child_docs:
            return []
        parent_ids = {doc.metadata.get("parent_id") for doc in child_docs if doc.metadata.get("parent_id")}
        if not parent_ids:
            return child_docs
        parent_docs = self.vector_store.get_parent_docs_by_metadata(list(parent_ids))
        return parent_docs if parent_docs else child_docs

    # -------- 主入口 --------
    def retrieve(self, query: str, document_ids: Optional[List[int]] = None) -> List[Document]:
        semantic_results = self._semantic_search(query, document_ids=document_ids)
        bm25_results = self._bm25_search(query)
        summary_results = self._summary_search(query)
        question_results = self._hypothetical_question_search(query)

        retrieval_results: list[list[Document]] = []
        if semantic_results:
            retrieval_results.append(semantic_results)
        if bm25_results:
            retrieval_results.append(bm25_results)
        if summary_results:
            retrieval_results.append(summary_results)
        if question_results:
            retrieval_results.append(question_results)

        if not retrieval_results:
            return []

        final_docs = self.post_processor.process(
            original_query=query,
            retrieval_results=retrieval_results,
            top_k=self.top_k,
        )
        return self._get_parent_documents(final_docs)

