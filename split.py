from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter

from ..config.settings import settings
from .child_summary import ChildSummary
from .parent_hypothetic_question import get_hypothetic_question


class ParentChildSplitter:
    """
    父子分块（MarkdownHeader 父块 + SemanticChunker 子块）
    并可选：
    - 子块摘要生成
    - 父块假设性问题生成
    """

    def __init__(self, config, llm=None):
        self.config = config
        self.llm = llm  # 复用 MCP 的 LLM（建议传入 LLMClient.llm）

        self.headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]
        self.parent_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False,
        )

        model_path = Path(__file__).resolve().parent.parent / "my_models" / "embedding_models" / "bge-m3"
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=str(model_path),
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self.child_splitter = SemanticChunker(
            embeddings=self.embedding_model,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=90,
        )

    def pc_splitter(self, loaded_documents, file_name, generate_summaries=True, generate_questions=True):
        parent_docs: list[Document] = []
        child_docs: list[Document] = []

        for doc in loaded_documents:
            if not doc.page_content or not doc.page_content.strip():
                continue
            parent_splits = self.parent_splitter.split_text(doc.page_content)

            for i, parent_split in enumerate(parent_splits):
                parent_id = f"{file_name}_parent_{i}"
                parent_doc = Document(
                    page_content=parent_split.page_content,
                    metadata={
                        **doc.metadata,
                        **parent_split.metadata,
                        "parent_id": parent_id,
                        "doc_type": "parent",
                    },
                )
                parent_docs.append(parent_doc)

                child_chunks = self.child_splitter.split_documents([parent_doc])
                for j, child_split in enumerate(child_chunks):
                    child_split.metadata.update(
                        {
                            "parent_id": parent_id,
                            "child_id": f"{file_name}_child_{i}_{j}",
                            "doc_type": "child",
                        }
                    )
                    child_docs.append(child_split)

        child_summaries = None
        parent_questions = None

        if generate_summaries and child_docs:
            if self.llm is None:
                raise ValueError("生成子块摘要需要传入 llm（复用 MCP LLM 实例）")
            child_summaries = ChildSummary(self.llm).get_child_summary(child_docs)

        if generate_questions and parent_docs:
            if self.llm is None:
                raise ValueError("生成父块假设性问题需要传入 llm（复用 MCP LLM 实例）")
            parent_questions = get_hypothetic_question(parent_docs, self.llm)

        return parent_docs, child_docs, child_summaries, parent_questions

