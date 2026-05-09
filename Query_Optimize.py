"""
查询优化模块：根据策略返回优化后的单个查询字符串
策略: baseline, rewrite, hyde, multi_query, composite
"""

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


def rewrite_query(question: str, llm: BaseLanguageModel) -> str:
    prompt = ChatPromptTemplate.from_template("请将用户问题改写为适合搜索的专业描述。原始问题: {question}")
    return (prompt | llm | StrOutputParser()).invoke({"question": question})


def hyde_query(question: str, llm: BaseLanguageModel) -> str:
    prompt = ChatPromptTemplate.from_template("请针对以下问题写一个简短的模拟回答：{question}")
    return (prompt | llm | StrOutputParser()).invoke({"question": question})


def multi_query_first(question: str, llm: BaseLanguageModel) -> str:
    prompt = ChatPromptTemplate.from_template("请为以下问题生成3个不同角度的搜索查询，每行一个：\n{question}")
    result = (prompt | llm | StrOutputParser()).invoke({"question": question})
    queries = [q.strip() for q in result.split("\n") if q.strip()]
    return queries[0] if queries else question


def composite_query(question: str, llm: BaseLanguageModel) -> str:
    rewritten = rewrite_query(question, llm)
    prompt = ChatPromptTemplate.from_template("作为一个搜索专家，请针对描述 '{rq}' 提供3个相关的搜索查询，每行一个。")
    result = (prompt | llm | StrOutputParser()).invoke({"rq": rewritten})
    queries = [q.strip() for q in result.split("\n") if q.strip()]
    return queries[0] if queries else rewritten


def optimize_question(question: str, llm: BaseLanguageModel, strategy: str = "composite") -> str:
    if strategy == "baseline":
        return question
    if strategy == "rewrite":
        return rewrite_query(question, llm)
    if strategy == "hyde":
        return hyde_query(question, llm)
    if strategy == "multi_query":
        return multi_query_first(question, llm)
    if strategy == "composite":
        return composite_query(question, llm)
    raise ValueError(f"未知策略: {strategy}，可选: baseline, rewrite, hyde, multi_query, composite")

