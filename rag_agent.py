from __future__ import annotations

from typing import List, Optional

from langchain_core.documents import Document

from .base import BaseAgent
from ..workflow.state import AgentResponse
from ..utils.logger import get_logger
from ..rag.database import DatabaseManager
from ..rag.final_retrieve import FinalRetrieval
from ..rag.Query_Optimize import optimize_question
from ..rag.rag_system import RagSystem
from ..rag.vector_store import VectorStore
from ..config.settings import settings


logger = get_logger(__name__)


class RAGAgent(BaseAgent):
    """
    RAG Agent:
    - 检索：FinalRetrieval（多路召回 + 重排序 + 父块关联）
    - 生成：LLMGenerationManager（引用 + 自验证）
    """

    def __init__(self, mcp_tools, mcp_adapter, agent_type: str = "rag_agent", db_manager: DatabaseManager | None = None):
        """
        初始化 RAG Agent

        Args:
            mcp_tools: MCP 工具列表
            mcp_adapter: MCP 适配器
            agent_type: Agent 类型
            db_manager: 数据库管理器（可选，默认新建）
        """
        super().__init__(mcp_tools, mcp_adapter, agent_type)
        self.db_manager = db_manager or DatabaseManager()
        self.vector_store = VectorStore()
        self.retriever = FinalRetrieval(db_manager=self.db_manager)
        self.rag_system = RagSystem(settings, self.db_manager, self.vector_store, self.retriever)

    async def run(self, user_query: str, doc_tag: str = None, session_id: str = None) -> AgentResponse:
        """
        统一 run 方法

        Args:
            user_query: 用户问题
            doc_tag: 文档标签
            session_id: 会话ID

        Returns:
            AgentResponse
        """
        return self.rag_answer(user_query, doc_tag, session_id)

    def _parse_doc_tag_to_ids(self, doc_tag: Optional[str]) -> Optional[List[int]]:
        """
        将前端单选框传入的 doc_tag 尽量解析为 document_ids（int 列表）。

        兼容：
        - "12"
        - "12,13"
        - "12 13"
        - None / 空串
        """
        if doc_tag is None:
            return None
        s = str(doc_tag).strip()
        if not s:
            return None

        # 常见分隔符统一为逗号
        for sep in [" ", "，", ";", "；", "|"]:
            s = s.replace(sep, ",")
        parts = [p.strip() for p in s.split(",") if p.strip()]
        ids: list[int] = []
        for p in parts:
            if p.isdigit():
                ids.append(int(p))
            else:
                # 非数字 tag 目前无法映射到 document_id
                return None
        return ids or None

    def _build_context(self, docs: List[Document]) -> str:
        """
        将检索到的文档列表构建为上下文字符串

        Args:
            docs: 文档列表

        Returns:
            格式化的上下文字符串
        """
        blocks = []
        for idx, doc in enumerate(docs, start=1):
            blocks.append(f"[文档 {idx}]\n{doc.page_content}")
        return "\n\n".join(blocks)

    def rag_answer(self, user_query: str, doc_tag: str = None, session_id: str = None) -> AgentResponse:
        """
        核心方法：RAG 文档问答

        流程：
        1. 解析用户问题和文档标签
        2. 查询优化
        3. 调用多路召回检索器（向量+BM25+摘要+假设问题）
        4. 进行重排序和后处理
        5. LLM 生成答案（带幻觉自检）
        6. 保存对话历史
        7. 返回结构化响应

        Args:
            user_query: 用户问题
            doc_tag: 文档标签（可选，用于过滤文档，支持逗号/空格分隔多个ID）
            session_id: 会话ID（可选，默认生成）

        Returns:
            AgentResponse: 统一响应格式
                - success: bool，是否成功
                - content: str，生成的答案
                - error: str，错误信息（失败时）
                - metadata: dict，包含检索统计（文档数、检索方法等）
                - extra: dict，额外信息（当前为空）
        """
        try:
            q = (user_query or "").strip()
            if not q:
                logger.warning("[RAG] 用户问题为空")
                return AgentResponse(
                    success=False,
                    content="",
                    error="user_query 不能为空",
                    metadata={},
                )

            if session_id is None:
                session_id = self.rag_system.generate_session_id()

            logger.info(f"[RAG] 收到问题: {q}")
            if doc_tag is not None:
                logger.info(f"[RAG] doc_tag: {doc_tag}")

            # 解析 doc_tag 为 document_ids
            document_ids = self._parse_doc_tag_to_ids(doc_tag)
            if doc_tag and document_ids is None:
                logger.warning(f"[RAG] doc_tag 无法解析为 document_id，将忽略过滤: {doc_tag}")

            # 查询优化
            optimized_q = optimize_question(q, self.llm, strategy="composite")
            logger.info(f"[RAG] 优化后查询: {optimized_q}")

            # 执行检索
            logger.info("[RAG] 开始检索（多路召回：向量+BM25+摘要+假设问题）...")
            try:
                retrieved_docs = self.retriever.final_retrieve(optimized_q, document_ids=document_ids)
                logger.info(f"[RAG] 检索完成，获得 {len(retrieved_docs)} 个文档")
            except Exception as e:
                logger.error(f"[RAG] 检索失败: {e}", exc_info=True)
                return AgentResponse(
                    success=False,
                    content="",
                    error=f"检索失败: {str(e)}",
                    metadata={"doc_tag": doc_tag},
                )

            if not retrieved_docs:
                logger.warning("[RAG] 未检索到相关文档")
                return AgentResponse(
                    success=False,
                    content="",
                    error="未找到相关文档",
                    metadata={
                        "doc_tag": doc_tag,
                        "document_ids": document_ids,
                        "retrieved_docs": 0,
                    },
                )

            # 构建上下文
            context = self._build_context(retrieved_docs)
            logger.info(f"[RAG] 上下文构建完成，长度: {len(context)} 字符")

            # 生成答案（LLM + 自验证）
            logger.info("[RAG] 开始生成答案（带幻觉自检）...")
            try:
                answer = self.rag_system.generate_and_verify(
                    {
                        "question": q,
                        "context": context,
                        "chat_history": "",
                    }
                )
                logger.info(f"[RAG] ✓ 答案生成完成，长度: {len(answer)} 字符")
            except Exception as e:
                logger.error(f"[RAG] 答案生成失败: {e}", exc_info=True)
                return AgentResponse(
                    success=False,
                    content="",
                    error=f"答案生成失败: {str(e)}",
                    metadata={
                        "doc_tag": doc_tag,
                        "document_ids": document_ids,
                        "retrieved_docs": len(retrieved_docs),
                    },
                )

            # 保存对话历史
            self.db_manager.save_chat_history(
                session_id,
                q,
                answer,
                document_ids='.'.join(map(str, document_ids)) if document_ids else None,
            )

            logger.info("[RAG] ✓ RAG 问答流程完成")
            return AgentResponse(
                success=True,
                content=answer,
                error=None,
                metadata={
                    "doc_tag": doc_tag,
                    "document_ids": document_ids,
                    "retrieved_docs": len(retrieved_docs),
                    "context_length": len(context),
                    "session_id": session_id,
                },
            )

        except Exception as e:
            logger.error(f"[RAG] 处理异常: {e}", exc_info=True)
            return AgentResponse(
                success=False,
                content="",
                error=f"处理异常: {str(e)}",
                metadata={"doc_tag": doc_tag},
            )
