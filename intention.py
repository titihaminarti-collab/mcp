from mcp_project.mcp.mcp_adapter import MCPAdapter
from mcp_project.utils.logger import get_logger
from mcp_project.workflow.state import AgentResponse
from mcp_project.agents.base import BaseAgent
logger = get_logger(__name__)
class Intent(BaseAgent):
    def __init__(self, mcp_tools, mcp_adapter: MCPAdapter):
        super().__init__(mcp_tools, mcp_adapter, 'intention_recognizer')
        logger.info("[初始化]==>第一次意图识别agent初始化完成")

    async def intent(self, user_input: str) -> AgentResponse:
        try:
            logger.info('第一次意图识别中...')
            prompt = await self.mcp_adapter.get_prompt(
                'get_intention_prompt',
                arguments={
                    'user_input': user_input
                }
            )
            response = await self.llm.ainvoke(prompt)
            # 此response为：content='意图: travel\n置信度: 0.95' additional_kwargs={...}
            # 先拿到里面的content为str
            if hasattr(response, 'content'):
                response_text = response.content
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)

            intent = 'chat'
            confidence = 0.5
            if 'travel' in response_text:
                intent = 'travel'

            if "置信度:" in response_text or "confidence:" in response_text.lower():
                try:
                    if "置信度:" in response_text:
                        score = response_text.split("置信度:")[-1].split("\n")[0]
                    else:
                        score = response_text.lower().split("confidence:")[-1].split("\n")[0]
                    confidence = float(score.strip())
                except:
                    confidence = 0.7 if intent == "travel" else 0.5

            logger.info(f"[第一次意图识别成功]==>类型为：{intent}  置信度为：{confidence}")
            return AgentResponse(
                success=True,
                content={
                    'intent': intent,
                    'confidence': confidence,
                },
                metadata={'user_input': user_input}
            )

        except Exception as e:
            logger.error(f'[第一次意图识别失败]==>{e}')
            return AgentResponse(
                success=False,
                content={
                    'intent': 'chat',
                    'confidence': 0.5,
                },
                error=str(e)
            )
