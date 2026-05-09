from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


class ChildSummary:
    def __init__(self, llm):
        if llm is None:
            raise ValueError("ChildSummary 需要传入 MCP 的 LLM 实例")
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_template("总结下面的文档：\n\n{doc}")
        self.parser = StrOutputParser()

    def get_child_summary(self, child_docs):
        chain = ({"doc": lambda x: x.page_content} | self.prompt | self.llm | self.parser)
        return chain.batch(child_docs, {"max_concurrency": 5})
