from contextlib import AsyncExitStack
from typing import Any, Dict
from langchain_core.tools import Tool
from mcp_project.mcp.mcp_client import get_mcp_client

class MCPAdapter:
    def __init__(self, mcp_url):
        self.mcp_url = mcp_url
        self.mcp_client = get_mcp_client(self.mcp_url)

        self._session = None
        self._exit_stack = AsyncExitStack()

    async def __aenter__(self):
        try:
            self._session = await self._exit_stack.enter_async_context(
                self.mcp_client.connect()
            )
            return self
        except Exception as e:
            raise e

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.close()
        self._session = None

    @property
    def session(self):
        if self._session is None:
            raise RuntimeError(
                "session not initialized, call `mcp_client.connect()` first"
            )
        return self._session

    async def get_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> str:
        server_prompts = await self.session.get_prompt(prompt_name, arguments)
        return server_prompts

    async def get_resource(self, uri: str) -> str:
        server_prompts = await self.session.get_resource(uri)
        return server_prompts

    async def get_langchain_tools(self):
        try:
            # 1.获取server中tool列表
            server_tools = await self.session.list_tools()
            print(server_tools)
            # 2.定义空列表用于存放转换之后的
            langchain_tools = []
            # 3.遍历
            for server_tool in server_tools:
                langchain_tool = Tool(
                    name=server_tool.name,
                    description=server_tool.description or f"MCP tool {server_tool.name}",
                    func=None,
                    coroutine=self._create_tool_function(server_tool.name),
                )
                langchain_tools.append(langchain_tool)
            return langchain_tools
        except Exception as e:
            raise e

    def _create_tool_function(self, tool_name: str):
        async def tool_function(**kwargs):
            try:
                result = await self.session.call_tool(tool_name, kwargs)
                if hasattr(result, "content") and result.content:
                    return str(result.content[0].text)
                return str(result)
            except Exception as e:
                raise e
        return tool_function

_instance = None
def get_adapter(mcp_url: str):
    global _instance
    if _instance is None:
        _instance = MCPAdapter(mcp_url)
    return _instance