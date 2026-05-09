from mcp_project.agents.base import BaseAgent
from mcp_project.utils.logger import get_logger
from typing import List, Dict
import json
from mcp_project.workflow.state import AgentResponse

logger = get_logger(__name__)


class TicketSummary(BaseAgent):
    def __init__(self, mcp_tools, mcp_adapter):
        super().__init__(mcp_tools, mcp_adapter, 'ticket_summary')  # 去llm-utils写这个llm并在base里做映射
        logger.info('[初始化]==>车票总结agent初始化完成')

    async def ticket_summary(self, tickets_info: List[Dict], user_preference: str, feedback: List[str] = None) -> AgentResponse:
        try:
            logger.info("[执行工具]==>车票总结工具执行中...")
            if not tickets_info:
                logger.error("车票检索列表为空，无法总结")
                return AgentResponse(
                    success=False,
                    content='',
                    error='车票检索列表为空，无法总结'
                )
            prompt = self.mcp_adapter.get_prompt(
                'get_summary_tickets',
                arguments={
                    'tickets_info': json.dumps(tickets_info),
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
            logger.error("[车票总结工具执行失败]")
            return AgentResponse(
                success=False,
                error=str(e),
                content=''
            )
