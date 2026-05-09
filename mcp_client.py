from contextlib import asynccontextmanager
from mcp_project.utils.logger import get_logger
from fastmcp import Client
from typing import Optional, Any, Dict,List

logger = get_logger(__name__)

class MCPClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self.mcp_client: Optional[Client] = None

    @asynccontextmanager
    async def connect(self):
        try:
            logger.info(f"Connecting to {self.url}")
            self.mcp_client = Client(
                self.url
            )
            async with self.mcp_client:
                await self.mcp_client.ping()
                yield self
        except Exception as e:
            logger.error(e)
            raise

    async def list_tools(self) -> List[Any]:
        """获取 MCP 服务器提供的工具列表"""
        if not self.mcp_client:
            raise RuntimeError("MCP client not connected, call connect() first")
        return await self.mcp_client.list_tools()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用 MCP 工具"""
        if not self.mcp_client:
            raise RuntimeError("MCP client not connected, call connect() first")
        return await self.mcp_client.call_tool(tool_name, arguments)

    async def get_prompt(self, prompt_name: str, arguments: Dict[str, Any]):
        try:
            logger.info(f"")
            if arguments is None:
                arguments = {}
            response = await self.mcp_client.get_prompt(prompt_name, arguments)
            return response.messages[0].content.text
        except Exception as e:
            logger.error(e)
            raise

    async def close(self):
        """关闭 MCP 客户端连接"""
        if self.mcp_client:
            await self.mcp_client.__aexit__(None, None, None)
            self.mcp_client = None

_instance = None
def get_mcp_client(mcp_url: str):
    global _instance
    if _instance is None:
        _instance = MCPClient(url=mcp_url)
    return _instance

"""
get_prompt方法的返回值：
{
    "..." : "...",
    "messages": [{
        "role": "user", 
        "content": {
            "type": "text",
            "text": "..."
        }
    }]
}
"""