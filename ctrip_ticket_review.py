from mcp_project.agents.base import BaseAgent
from mcp_project.utils.logger import get_logger
from typing import List, Dict
import json
from mcp_project.workflow.state import AgentResponse
from pydantic import BaseModel
logger = get_logger(__name__)

class TravelReviewResult(BaseModel):
    score: int                    # 总分 0-100
    passed: bool                  # 是否通过
    reason: str = ""              # 不通过时：一句话说明原因；通过时：空字符串
    suggestions: List[str]        # 不通过时：具体修改建议；通过时：空列表

class TicketReview(BaseAgent):
    def __init__(self, mcp_tools, mcp_adapter):
        super().__init__(mcp_tools, mcp_adapter, 'ticket_review')# 去llm-utils写这个llm并在base里做映射
        self.check_tool = self.get_tool('validate_infos')
        logger.info('[初始化]==>车票审查agent初始化完成')

    async def ticket_review(self, tickets_info: List[Dict], user_preference: str, ticket_summary: str):
        try:
            logger.info("[执行工具]==>车票审查工具执行中...")
            if not ticket_summary:
                return AgentResponse(
                    success=False,
                    content='',
                    error='车票总结为空，无法审查'
                )

            # 第一步：规则校验
            if self.check_tool:
                validated_result = await self.check_tool.coroutine(
                    user_preference=user_preference,
                    summary=ticket_summary,
                    original_infos=tickets_info,
                    criteria=["数据一致", "要素齐全", "需求匹配"]
                )
                if isinstance(validated_result, str):
                    validated_result = json.loads(validated_result)

                pass_rate = validated_result.get("pass_rate", 0)
                logger.info(f"车票规则校验完成，通过率: {pass_rate:.1%}")

                # 通过率低于 50% 直接打回，不浪费 LLM Token
                if pass_rate < 0.5:
                    logger.warning(f"[车票规则校验失败]==>通过率仅 {pass_rate:.1%}")
                    return AgentResponse(
                        success=False,
                        content=ticket_summary,
                        metadata={
                            "status": "rejected",
                            "feedback": {
                                "reason": "基础校验未通过",
                                "suggestions": [
                                    "请确保总结包含综合推荐、对比表格和最终建议",
                                    "请检查表格中引用的价格和车次是否与原始数据一致",
                                    "请确认推荐覆盖了用户的核心需求"
                                ],
                                "校验详情": validated_result,
                            },
                            "retry_required": True,
                        }
                    )

            # 第二步：获取 Resource 审核标准
            resource_review_criteria = self.mcp_adapter.get_resource("reviewStandards://travel-recommendation")

            # 第三步：构建最终 Prompt（基础 Prompt + Resource）
            prompt = self.mcp_adapter.get_prompt(
                'get_review_tickets',
                arguments={
                    "tickets_info": json.dumps(tickets_info, ensure_ascii=False),
                    "user_preference": user_preference,
                    "ticket_summary": ticket_summary,
                }
            )
            final_prompt = f"""
                {prompt}
    
                ## 详细审核标准
                {resource_review_criteria}
            """

            # 第四步：LLM 结构化输出
            structured_llm = self.llm.llm.with_structured_output(TravelReviewResult)
            review_result_obj = await structured_llm.ainvoke(final_prompt)
            review_result = review_result_obj.model_dump()

            score = review_result.get("score", 0)
            passed = score >= 70

            if passed:
                logger.info(f"[审查通过]==>得分: {score}分")
                return AgentResponse(
                    success=True,
                    content=ticket_summary,
                    metadata={
                        "status": "approved",
                        "score": score,
                    }
                )
            else:
                logger.info(f"[审查不通过]==>得分: {score}分")
                return AgentResponse(
                    success=False,
                    content=ticket_summary,
                    metadata={
                        "status": "rejected",
                        "score": score,
                        "feedback": {
                            "reason": review_result.get("reason", ""),
                            "suggestions": review_result.get("suggestions", []),
                        },
                        "retry_required": True,
                    }
                )

        except Exception as e:
            logger.error(f"[车票审查工具执行失败] {e}")
            return AgentResponse(
                success=False,
                error=str(e),
                content='',
                metadata={"status": "error", "retry_required": False}
            )