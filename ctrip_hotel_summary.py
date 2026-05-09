# hotel-search agent获取到了符合条件的酒店们，这个agent要做的是 整合信息，给用户
# 一条总结建议，并列举出符合条件的前三四个酒店信息做对比
from mcp_project.agents.base import BaseAgent
from mcp_project.utils.logger import get_logger
from typing import List, Dict
import json
from mcp_project.workflow.state import AgentResponse
logger = get_logger(__name__)

class HotelSummary(BaseAgent):
    def __init__(self, mcp_tools, mcp_adapter):
        super().__init__(mcp_tools, mcp_adapter, 'hotel_summary')# 去llm-utils写这个llm并在base里做映射
        logger.info('[初始化]==>酒店总结agent初始化完成')
# 需传入用户对酒店的要求，避免重复search中的步骤，直接在search时将用户偏好一同封装进agent response中的metadata中，然后state取出来流转用
    async def hotel_summary(self, hotels_info: List[Dict], user_preference: str, feedback: List[str] = None) -> AgentResponse:
        try:
            logger.info("[执行工具]==>酒店总结...")
            if not hotels_info:
                logger.error("酒店检索列表为空，无法总结")
                return AgentResponse(
                    success=False,
                    content='',
                    error='酒店检索列表为空，无法总结'
                )
            prompt = self.mcp_adapter.get_prompt(
                'get_summary_hotels',
                arguments={
                    'hotels_info': json.dumps(hotels_info),
                    'user_preference': user_preference
                }
            )
            if feedback:
                logger.info('[重试模式]==>根据审核建议重新生成...')
                feedback_str = "\n".join(f"- {item}" for item in feedback)
                prompt += f"""
                   ## 你之前生成的总结未通过审核，以下是修正要求:
                   {feedback_str}

                   要求：逐条对照上述建议，重新进行针对性的总结和推荐。
                   """
            response = await self.llm.ainvoke(prompt)
            return AgentResponse(
                success=True,
                content=response,
                metadata={
                    "user_preference": user_preference,
                    "is_retry": feedback is not None,
                }
            )
        except Exception as e:
            logger.error("[酒店总结工具执行失败]")
            return AgentResponse(
                success=False,
                error=str(e),
                content=''
            )
