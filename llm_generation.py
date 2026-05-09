from __future__ import annotations

import logging
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ..utils.logger import get_logger


def _unwrap_langchain_llm(llm: Any):
    """
    兼容两种输入：
    - 直接传入 LangChain ChatModel（有 .invoke/.ainvoke/.stream 等）
    - 传入 MCP 的 LLMClient（有 .llm 属性，且 .invoke 返回 str）
    """
    if llm is None:
        return None
    if hasattr(llm, "invoke") and hasattr(llm, "ainvoke") and not hasattr(llm, "llm"):
        return llm
    if hasattr(llm, "llm"):
        return llm.llm
    return llm


class LLMGenerationManager:
    """
    答案生成管理：
    1. 答案生成 + 引用格式约束
    2. 幻觉自检（Self-RAG grading）
    3. 自检失败时的保守修正重写
    """

    def __init__(self, llm):
        self.llm = _unwrap_langchain_llm(llm)
        if self.llm is None:
            raise ValueError("LLMGenerationManager 需要传入 MCP 的 LLM 实例（或其底层 langchain llm）")
        self.logger = get_logger(__name__)

    def build_generation_chain(self):
        generation_prompt = ChatPromptTemplate.from_template(
            """你是一个专业的文档分析助手。请根据以下提供的文档内容回答用户的问题。

【核心要求】：
1. 只能根据提供的上下文回答，绝不能编造（杜绝幻觉）。
2. 回答时，必须在每句话或每个数据后标注引用来源。
3. 引用格式必须严格使用：【来源：第x章 第x.x节】
4. 如果同一信息来自多个章节，写为：【来源：第3章 3.1.2节，第5章 5.1节】
5. 如果给定的上下文无法回答该问题，请直接回答“根据提供的文档，我无法回答此问题。”

【参考文档】：
{context}

【用户问题】: {question}

请给出你的回答："""
        )

        hallucination_prompt = ChatPromptTemplate.from_template(
            """你是一个严格的审核专家。判断【生成的回答】是否完全基于【参考文档】，是否包含未在文档中提及的编造内容（幻觉）。

【参考文档】：
{context}

【生成的回答】：
{generation}

判断标准：
- 完全基于文档（没有幻觉）输出 "yes"
- 包含文档中没有的信息（有幻觉）输出 "no"
请只输出 "yes" 或 "no"。"""
        )

        gen_chain = generation_prompt | self.llm | StrOutputParser()
        check_chain = hallucination_prompt | self.llm | StrOutputParser()

        def generate_and_verify(inputs: dict) -> str:
            question = inputs["question"]
            context_str = inputs.get("context", "")
            if not context_str.strip():
                return "没有检索到任何相关文档，无法回答。"

            generation = gen_chain.invoke({"context": context_str, "question": question})
            if "无法回答" in generation:
                return generation

            check_result = check_chain.invoke({"context": context_str, "generation": generation}).strip().lower()
            if "yes" in check_result:
                return generation

            correction_prompt = ChatPromptTemplate.from_template(
                """你之前的回答可能包含了未在参考文档中提及的信息（产生了幻觉）。
请重新回答用户问题，严格剔除所有文档中没有提到的内容。如果文档中没有相关信息，请明确说明。
记得保留并标注引用来源，引用格式必须严格使用：【来源：第x章 第x.x节】

【参考文档】：
{context}

【用户问题】: {question}"""
            )
            correction_chain = correction_prompt | self.llm | StrOutputParser()
            return correction_chain.invoke({"context": context_str, "question": question})

        return generate_and_verify

