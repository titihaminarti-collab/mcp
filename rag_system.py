# rag_system.py
import uuid
from langchain_core.prompts import PromptTemplate
from typing import List, Tuple
from langchain_core.documents import Document
from .llm_generation import LLMGenerationManager
from .Query_Optimize import optimize_question
from ..utils.llm_utils import LLMFactory


class RagSystem:
    def __init__(self, config, db_manager, vector_store, retriever):
        self.config = config
        self.db_manager = db_manager
        self.vector_store = vector_store
        self.retriever = retriever
        self.llm = LLMFactory.chat()

        # 原来的 rag_prompt 可以保留或后续逐步弃用
        self.rag_prompt = PromptTemplate(
            template="""
            你是一个智能助手。必须基于提供的文档内容回答用户的问题.

            文档内容:
            {context}

            历史对话:
            {chat_history}

            用户问题: {question}

            要求：
            1. 只能基于文档内容回答。
            2. 不要编造任何信息。
            3. 如果文档中没有相关内容，回答"未在文档中找到相关信息"。
            4. 请用中文清晰、准确地回答。
            """,
            input_variables=["context", "chat_history", "question"],
        )

        # 新增：初始化生成管理器
        self.llm_gen_manager = LLMGenerationManager(self.llm)
        self.generate_and_verify = self.llm_gen_manager.build_generation_chain()

    def generate_session_id(self):
        return str(uuid.uuid4())

    def rag_chat(self, question: str, document_ids: List[int], session_id: str) -> Tuple[str, List[Document]]:
        """
        RAG 对话

        参数:
            question: 用户问题
            document_ids: 限定的文档ID列表
            session_id: 会话ID

        返回:
            (回答内容, 检索到的文档列表)
        """

        try:
            # 1. 查询优化（根据配置选择策略，这里示例使用 "composite"）
            optimized_q = optimize_question(question, self.llm, strategy="composite")
            print(f"[DEBUG] 原始问题: {question}")
            print(f"[DEBUG] 优化后查询: {optimized_q}")

            # 2. 使用优化后的查询进行检索
            retrieved_docs = self.retriever.final_retrieve(optimized_q, document_ids=document_ids)

            # 3. 构建上下文（可以保留原有的编号方式，方便引用）
            context_blocks = []
            for idx, doc in enumerate(retrieved_docs, start=1):
                context_blocks.append(f"[文档 {idx}]\n{doc.page_content}")
            context = "\n\n".join(context_blocks)

            # 4. 获取历史对话
            chat_history = self.db_manager.get_chats_history(session_id)
            history_text = "\n".join([
                f"用户: {chat.user_message}\n助手: {chat.assistant_message}"
                for chat in chat_history
            ])

            # 5. 调用 LLMGenerationManager 生成答案（带引用和自验证）
            inputs = {
                "question": question,  # 注意：这里用原始问题，不是优化后的查询
                "context": context,
                "chat_history": history_text
            }
            ai_answer = self.generate_and_verify(inputs)

            # 6. 保存对话历史
            self.db_manager.save_chat_history(
                session_id,
                question,
                ai_answer,
                document_ids='.'.join(map(str, document_ids)) if document_ids else None,
            )

            print(f"\n 回答生成完成")
            print(f"  检索文档数: {len(retrieved_docs)}")
            print(f"  Context 长度: {len(context)} 字符")
            print(f"  回答长度: {len(ai_answer)} 字符\n")

            return ai_answer, retrieved_docs

        except Exception as e:
            print(f"RAG Chat 错误: {e}")
            return f"处理您的问题时出现错误: {str(e)}", []

    def normal_chat(self, question: str, session_id: str) -> str:
        """普通对话模式"""
        try:
            chat_history = self.db_manager.get_chats_history(session_id)
            messages = []
            for chat in chat_history:
                messages.append(f"Human:{chat.user_message}")
                messages.append(f"Chat:{chat.assistant_message}")
            messages.append(f"Human: {question}")
            conversation_context = "\n".join(messages)
            response = self.llm.invoke(conversation_context + "\nAssistant:")
            ai_answer = response.content

            self.db_manager.save_chat_history(
                session_id,
                question,
                ai_answer,
            )
            return ai_answer
        except Exception as e:
            print(f" Normal Chat 错误: {e}")
            return f"处理您的问题时出现错误: {str(e)}"
