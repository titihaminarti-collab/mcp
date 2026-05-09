from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate


class HypotheticQuestion(BaseModel):
    questions: List[str] = Field(..., description="List of questions")


def get_hypothetic_question(parent_docs, llm):
    """
    基于父块生成假设性问题（结构化输出）。
    llm: 复用 MCP 的 LangChain LLM 实例（建议传入 LLMClient.llm）
    """
    if llm is None:
        raise ValueError("get_hypothetic_question 需要传入 MCP 的 LLM 实例")

    prompt = ChatPromptTemplate.from_template(
        """请基于以下文档生成3个假设性问题（必须使用JSON格式）:
{doc}

要求：
1. 输出必须为合法JSON格式，包含questions字段
2. questions字段的值是包含3个问题的数组
3. 使用中文提问
示例格式：
{{
  "questions": ["问题1", "问题2", "问题3"]
}}"""
    )

    chain = (
        {"doc": lambda x: x.page_content}
        | prompt
        | llm.with_structured_output(HypotheticQuestion)
        | (lambda x: x.questions)
    )
    return chain.batch(parent_docs, {"max_concurrency": 5})

