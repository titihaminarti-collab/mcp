from typing import List, Dict, Optional
from langchain_core.tools import Tool
from abc import ABC
from mcp_project.mcp.mcp_adapter import MCPAdapter
from mcp_project.utils.llm_utils import LLMFactory
from mcp_project.utils.logger import get_logger

class BaseAgent(ABC):

    def __init__(self, mcp_tools: List[Tool], mcp_adapter: MCPAdapter, agent_type: str):
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.llm = self._create_llm(agent_type)
        self.mcp_tools: Dict[str, Tool] = {tool.name: tool for tool in mcp_tools}
        self.mcp_adapter = mcp_adapter

        self.logger.info(f"{self.__class__.__name__} 初始化完成 (Type: {agent_type})")

    def _create_llm(self, agent_type: str):
        mapping = {
            "intention_recognizer": LLMFactory.intention_recognize,
            "travel_intention": LLMFactory.travel_intention_recognize,
            "hotel_searcher": LLMFactory.c_trip_hotel_search,
            "ticket_searcher": LLMFactory.c_trip_ticket_search,
            "summary_hotels": LLMFactory.summary_hotels,
            "summary_tickets": LLMFactory.summary_tickets,
            "retriever": LLMFactory.retrieve,
            "reviewer": LLMFactory.review,
            "rag_agent": LLMFactory.rag_agent,
            "ticket_summary": LLMFactory.summary_tickets,
            "hotel_summary": LLMFactory.summary_hotels,
            "ticket_review": LLMFactory.review,
            "hotel_review": LLMFactory.review,
            "baidu_map_agent": LLMFactory.chat,
        }
        creator = mapping.get(agent_type.lower())
        if not creator:
            raise ValueError(f"未定义的 Agent 类型: {agent_type}")
        return creator()

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        tool = self.mcp_tools.get(tool_name)
        if not tool:
            self.logger.warning(f"工具{tool_name}在当前 MCP 环境中未找到")
        return tool