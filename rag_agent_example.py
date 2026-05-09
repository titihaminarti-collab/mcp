"""
RAGAgent 使用示例和规范说明
"""

from rag_agent import RAGAgent
from ..rag.database import DatabaseManager
import asyncio


# ============= 示例 1：使用默认配置 =============
async def example_default():
    """使用默认 LLM 和数据库管理器"""
    agent = RAGAgent()

    # 简单问询
    response = await agent.rag_answer(
        user_query="PDF中关于第二章的内容是什么？"
    )

    print(f"成功: {response.success}")
    print(f"答案: {response.content}")
    print(f"元数据: {response.metadata}")


# ============= 示例 2：使用文档标签过滤 =============
async def example_with_doc_tag():
    """指定文档标签，只在某些文档中搜索"""
    agent = RAGAgent()

    # 使用 doc_tag 过滤
    response = await agent.rag_answer(
        user_query="标准的制定背景是什么？",
        doc_tag="12,13"  # 仅在 document_id 为 12 和 13 的文档中搜索
    )

    print(f"成功: {response.success}")
    if response.success:
        print(f"答案: {response.content}")
        print(f"检索文档数: {response.metadata.get('retrieved_docs')}")
    else:
        print(f"错误: {response.error}")


# ============= 示例 3：注入自定义 LLM 和数据库 =============
async def example_custom_components():
    """注入自定义的 LLM 和数据库管理器"""
    from ..utils.llm_utils import LLMFactory

    # 获取特定工厂的 LLM
    llm_client = LLMFactory.chat()
    db_manager = DatabaseManager()

    # 创建 Agent 时注入自定义组件
    agent = RAGAgent(llm=llm_client.llm, db_manager=db_manager)

    response = await agent.rag_answer(
        user_query="这个文档的核心内容是什么？"
    )

    print(f"成功: {response.success}")
    if response.success:
        print(f"答案: {response.content[:200]}...")
        print(f"统计信息:")
        print(f"  - 检索文档数: {response.metadata.get('retrieved_docs')}")
        print(f"  - 上下文长度: {response.metadata.get('context_length')}")


# ============= 规范：AgentResponse 响应格式 =============
"""
RAGAgent.rag_answer() 返回的 AgentResponse 包含：

1. success (bool):  是否成功
2. content (str):   生成的答案（成功时）
3. error (str):     错误信息（失败时）
4. metadata (dict): 结构化元数据
   - doc_tag: 输入的文档标签
   - document_ids: 解析后的文档ID列表
   - retrieved_docs: 检索到的文档数
   - context_length: 上下文总长度
5. extra (dict):    额外字段（当前为空，预留给前端）

示例响应：
{
    "success": true,
    "content": "根据提供的文档...",
    "error": null,
    "metadata": {
        "doc_tag": "12,13",
        "document_ids": [12, 13],
        "retrieved_docs": 5,
        "context_length": 2560
    },
    "extra": {}
}
"""

# ============= 规范：内部流程 =============
"""
RAGAgent.rag_answer() 的完整流程：

1. 输入验证
   - 检查 user_query 不为空
   - 解析 doc_tag（支持 "12,13" 或 "12 13" 或单个 "12"）

2. 多路召回检索 (FinalRetrieval)
   - 向量语义搜索 (Chroma 向量数据库)
   - BM25 关键词搜索
   - 子块摘要相似度搜索
   - 父块假设性问题搜索

3. 重排序与后处理 (PostRetrievalProcessor)
   - RRF (Reciprocal Rank Fusion) 融合多路结果
   - 去重和冗余过滤
   - 相似度阈值过滤
   - CrossEncoder 精排
   - LongContextReorder 解决 Lost-in-the-Middle

4. 上下文构建
   - 将排序后的文档拼接为上下文字符串

5. LLM 生成与自验证 (LLMGenerationManager)
   - 生成答案（要求标注来源）
   - 幻觉检测（Self-RAG）
   - 失败时修正重写

6. 返回响应
   - 包装为 AgentResponse 标准格式
   - 附加元数据用于监控和分析
"""

if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_default())
    # asyncio.run(example_with_doc_tag())
    # asyncio.run(example_custom_components())

