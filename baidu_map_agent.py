import json
import ast
from mcp_project.agents.base import BaseAgent
from mcp_project.workflow.state import AgentResponse
from mcp_project.utils.logger import get_logger
logger = get_logger(__name__)

class BaiduMapAgent(BaseAgent):
    """百度地图智能助手 Agent"""

    def __init__(self, mcp_tools, mcp_adapter):
        super().__init__(mcp_tools, mcp_adapter, 'intention_recognize') #意图识别用的是同一个
        self.route_tool = self.get_tool('get_route')
        self.search_tool = self.get_tool('search_places')
        logger.info("BaiduMapAgent 初始化完成")

    async def process(self, user_input: str) -> AgentResponse:
        """处理用户的地图相关请求"""
        try:
            # 第一步：用LLM解析用户意图和参数
            resolved = await self._resolve_action(user_input)
            if resolved.get("error"):
                return AgentResponse(success=False, content=resolved["error"], error=resolved["error"])

            action = resolved.get("action")
            args = resolved.get("args", {})

            # 第二步：根据 action 调用对应的 MCP 工具
            if action == "route":
                if not self.route_tool:
                    return AgentResponse(success=False, content="未找到路线规划工具")
                # 注意：get_route 参数为 origin, destination, mode
                result_str = await self.route_tool.coroutine(**args)
                result = json.loads(result_str)
                if result.get("success"):
                    answer = f"路线规划成功：距离 {result['distance_km']} 公里，用时约 {result['duration_min']} 分钟。\n步骤：\n" + "\n".join(
                        result.get("steps", []))
                else:
                    answer = f"路线规划失败：{result.get('error')}"

            elif action == "search":
                if not self.search_tool:
                    return AgentResponse(success=False, content="未找到地点搜索工具")
                # search_places 参数：query, region, city_limit
                result_str = await self.search_tool.coroutine(query=args.get("keyword"), region=args.get("city", "全国"))
                result = json.loads(result_str)
                if result.get("success"):
                    places = result.get("results", [])
                    if places:
                        answer = f"找到 {len(places)} 个地点：\n"
                        for p in places[:5]:  # 最多5个
                            answer += f"- {p['name']}，地址：{p['address']}\n"
                    else:
                        answer = "未找到相关地点。"
                else:
                    answer = f"搜索失败：{result.get('error')}"
            else:
                answer = "抱歉，我没能理解您的地图需求。请尝试说'从天安门到鸟巢的驾车路线'或'搜索附近的咖啡馆'。"

            return AgentResponse(success=True, content=answer)

        except Exception as e:
            logger.error(f"BaiduMapAgent 处理失败: {e}")
            return AgentResponse(success=False, content=f"处理出错：{str(e)}", error=str(e))
    # 用户意图识别 + 信息提取
    async def _resolve_action(self, user_input: str) -> dict:
        """使用 LLM 解析用户意图并提取参数"""
        prompt = f"""
你是一个智能地图助手。请分析用户的输入，判断是需要“路线规划”还是“地点搜索”，并提取关键参数。

用户输入：{user_input}

请严格按照以下JSON格式返回，不要有其他文本：
- 如果是路线规划：{{"action": "route", "args": {{"origin": "起点", "destination": "终点", "mode": "driving/walking/transit/riding"}}}}
- 如果是地点搜索：{{"action": "search", "args": {{"keyword": "搜索关键词", "city": "城市名（可选）"}}}}
- 如果无法识别：{{"action": "unknown", "error": "原因"}}

例如：
输入："从北京西站到天安门的驾车路线" → {{"action": "route", "args": {{"origin": "北京西站", "destination": "天安门", "mode": "driving"}}}}
输入："上海南京路附近的咖啡馆" → {{"action": "search", "args": {{"keyword": "咖啡馆", "city": "上海"}}}}
"""
        response_text = await self.llm.ainvoke(prompt)
        # 清理可能的 markdown 代码块
        response_text = response_text.strip().replace("```json", "").replace("```", "").strip()
        try:
            resolved = ast.literal_eval(response_text)
            if not isinstance(resolved, dict):
                raise ValueError
            return resolved
        except Exception as e:
            logger.error(f"解析LLM返回失败: {response_text}, 错误: {e}")
            return {"action": "unknown", "error": f"无法解析用户输入：{user_input}"}