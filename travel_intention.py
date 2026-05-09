# 用于区分是查票还是查酒店还是百度地图
from mcp_project.agents.base import BaseAgent
from mcp_project.utils.logger import get_logger
from mcp_project.workflow.state import AgentResponse
logger = get_logger(__name__)
class TravelIntention(BaseAgent):
    def __init__(self, mcp_tools, mcp_adapter):
        super().__init__(mcp_tools, mcp_adapter, 'intention_recognize')
        logger.info("[初始化]==>第二次意图识别agent初始化完成")

    async def travel_intention(self, user_input):
        try:
            logger.info("Travel Intention")
            prompt = self.mcp_adapter.get_prompt(
                'travel_intention',#去server里写这个提示词
                arguments={
                    'user_input': user_input
                }
            )
            response = await self.llm.ainvoke(prompt)
            if hasattr(response, 'content'):
                response_text = response.content
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)

            travel_intent = 'ticket'
            travel_intent_confidence = 0.5
            if 'hotel' in response_text:
                travel_intent = 'hotel'

            if "置信度:" in response_text or "travel_intent_confidence:" in response_text.lower():
                try:
                    if "置信度:" in response_text:
                        score = response_text.split("置信度:")[-1].split("\n")[0]
                    else:
                        score = response_text.lower().split("travel_intent_confidence:")[-1].split("\n")[0]
                    travel_intent_confidence = float(score.strip())
                except:
                    travel_intent_confidence = 0.7 if travel_intent == "travel" else 0.5

            logger.info(f"[意图识别成功]==>类型为：{travel_intent}  置信度为：{travel_intent_confidence}")
            return AgentResponse(
                success=True,
                content={
                    'travel_intent': travel_intent,
                    'travel_intent_confidence': travel_intent_confidence,
                },
                metadata={'user_input': user_input}
            )
        except Exception as e:
            logger.error(e)
