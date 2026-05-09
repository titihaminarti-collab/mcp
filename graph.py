# 图的编排
# 1.初始化与mcp——adapter的连接
# 2.初始化工具
# 3.构建工作流
# 4.节点、路由函数们
from typing import Literal
from mcp_project.mcp.mcp_adapter import get_adapter
from mcp_project.config.settings import settings
from contextlib import AsyncExitStack
from mcp_project.utils.logger import get_logger
from mcp_project.agents.intention import Intent
from mcp_project.agents.baidu_map_agent import BaiduMapAgent

# from mcp_project.utils.db import get_or_create_session, save_history

from mcp_project.agents.travel_intention import TravelIntention
from mcp_project.agents.ctrip_ticket_search import TicketSearch
from mcp_project.agents.ctrip_hotel_search import HotelSearch
from mcp_project.agents.ctrip_ticket_summary import TicketSummary
from mcp_project.agents.ctrip_hotel_summary import HotelSummary
from mcp_project.agents.ctrip_ticket_review import TicketReview
from mcp_project.agents.ctrip_hotel_review import HotelReview
# from ..agents.rag_agent import RAGAgent

from langgraph.graph import StateGraph, END
# from langsmith import traceable

from mcp_project.workflow.state import WorkflowState
from mcp_project.utils.llm_utils import LLMFactory
logger = get_logger(__name__)
class Workflow:
    def __init__(self):
        self.settings = settings
        self.mcp_adapter = get_adapter(self.settings.MCP_SERVER_URL)
        self._exit_stack = AsyncExitStack()
        self.normal_chat_llm = LLMFactory.chat()

    async def __aenter__(self):
        try:
            logger.info('初始化与mcp连接')
            await self._exit_stack.enter_async_context(self.mcp_adapter)
            self.mcp_tools = await self.mcp_adapter.get_langchain_tools() #去写转换函数


            self.intent_recognize = Intent(self.mcp_tools, self.mcp_adapter)
            self.travel_intention = TravelIntention(self.mcp_tools, self.mcp_adapter)
            self.ticket_search = TicketSearch(self.mcp_tools, self.mcp_adapter)
            self.hotel_search = HotelSearch(self.mcp_tools, self.mcp_adapter)
            self.ticket_summary = TicketSummary(self.mcp_tools, self.mcp_adapter)
            self.hotel_summary = HotelSummary(self.mcp_tools, self.mcp_adapter)
            self.ticket_review = TicketReview(self.mcp_tools, self.mcp_adapter)
            # self.hotel_review = HotelReview(self.mcp_tools, self.mcp_adapter)
            self.hotel_review = HotelReview(self.mcp_tools, self.mcp_adapter)
            #=============================================
            #self.rag_agent = RAGAgent(self.mcp_tools, self.mcp_adapter)
            self.rag_agent=None
            #==============================================
            self.baidu_map_agent=BaiduMapAgent(self.mcp_tools, self.mcp_adapter)
            self.graph = self.graph_build()

        except Exception as e:
            logger.error(e)
            raise

    def graph_build(self):
        workflow = StateGraph(WorkflowState)

        workflow.add_node("intent_recognize", self.intent_recognize_node)# 直接全都写成异步的
        workflow.add_node("retrieve", self.retrieve_node)
        workflow.add_node("travel_intention", self.travel_intention_node)
        workflow.add_node("c_trip_ticket_search", self.c_trip_ticket_search_node)
        workflow.add_node("c_trip_hotel_search", self.c_trip_hotel_search_node)
        workflow.add_node("c_trip_ticket_summary", self.c_trip_ticket_summary_node)
        workflow.add_node("c_trip_hotel_summary", self.c_trip_hotel_summary_node)
        workflow.add_node("c_trip_ticket_review", self.c_trip_ticket_review_node)
        workflow.add_node("c_trip_hotel_review", self.c_trip_hotel_review_node)
        workflow.add_node("rag", self.rag_node)
        workflow.add_node("normal_chat", self.normal_chat_node)       # 直接从工厂导入闲聊llm
        workflow.add_node("baidu_map", self.baidu_map_node)

        workflow.set_entry_point('intent_recognize')

        workflow.add_conditional_edges(
            'intent_recognize',
            self._route_by_intention,
            {
                'chat': 'normal_chat',
                'rag': 'rag',
                'travel': 'travel_intention',
            }
        )

        # 闲聊
        workflow.add_edge('normal_chat', END)
        # rag...

        # 旅行
        workflow.add_conditional_edges(
            'travel_intention',
            self._travel_route_by_intention,
            {
                'ticket': 'c_trip_ticket_search',
                'hotel': 'c_trip_hotel_search',
                'baidu': 'baidu_map'
            }
        )
        # 车票
        workflow.add_edge('c_trip_ticket_search', 'c_trip_ticket_summary')
        workflow.add_edge('c_trip_ticket_summary', 'c_trip_ticket_review')
        workflow.add_conditional_edges(
            'c_trip_ticket_review',
            self._route_after_review,
            {
                'pass': END,
                'retry': 'c_trip_ticket_summary',
            }
        )
        # 酒店
        workflow.add_edge('c_trip_hotel_search', 'c_trip_hotel_summary')
        workflow.add_edge('c_trip_hotel_summary', 'c_trip_hotel_review')
        workflow.add_conditional_edges(
            'c_trip_hotel_review',
            self._route_after_review,
            {
                'pass': END,
                'retry': 'c_trip_hotel_summary',
            }
        )
        # 百度地图
        workflow.add_edge("baidu_map", END)

        return workflow.compile()

    async def baidu_map_node(self, state: WorkflowState) -> WorkflowState:
        logger.info("进入百度地图节点")
        if "execution_path" not in state:
            state["execution_path"] = []
        response = await self.baidu_map_agent.process(state["user_input"])
        if response.success:
            state["final_output"] = response.content
        else:
            state["final_output"] = f"地图服务出错: {response.error}"
        state["execution_path"].append("baidu_map")
        return state

    async def intent_recognize_node(self, state:WorkflowState):
        logger.info('=' * 50)
        logger.info("[执行节点]==>第一次意图识别")
        response = await self.intent_recognize.intent(state['user_input']) # 此函数须传用户输入，在state中写这个参数
        if response.success:
            result = response.content
            # 更新状态,state中要写这两个参数
            state['intention'] = result['intent']
            state['intention_confidence'] = result['confidence']
            logger.info(f'[第一次意图识别成功]==>{result['intent']}, confidence: {result["confidence"]}')
        else:
            state['intention'] = 'chat' #默认为闲聊
            state['intention_confidence'] = 0.5
            logger.info("[第一次意图识别失败]==>默认为闲聊")
        state['execution_path'].append('intent_recognize')
        return state

    async def normal_chat_node(self, state: WorkflowState):
        logger.info('=' * 50)
        logger.info('[执行节点]==>普通对话')
        response = await self.normal_chat_llm.ainvoke(
            '你是一个友好的AI助手,请温柔回应用户' + state['user_input']
        )
        # 更新状态
        state['final_output'] = response
        state['execution_path'].append('normal_chat')
        return state

    async def retrieve_node(self, state:WorkflowState):
        pass

    # 第二次意图识别
    async def travel_intention_node(self, state: WorkflowState):
        logger.info('=' * 50)
        logger.info("[执行节点]==>第二次意图识别")
        response = await self.travel_intention.travel_intention(state['user_input']) # 此函数须传用户输入，在state中写这个参数
        if response.success:
            result = response.content
            # 更新状态,state中要写这两个参数
            state['travel_intent'] = result['intent']
            state['travel_intent_confidence'] = result['confidence']
            logger.info(f'[第二次意图识别成功]==>{result['travel_intent']}, confidence: {result["travel_intent_confidence"]}')
        else:
            state['travel_intent'] = 'ticket' #默认为车票，可以再改 改成百度会不会好一点
            state['travel_intent_confidence'] = 0.5
            logger.info("[第二次意图识别失败]==>默认为车票")
        state['execution_path'].append('travel_intent_recognize')
        return state

    async def c_trip_ticket_search_node(self, state:WorkflowState):
        logger.info('=' * 50)
        logger.info("[执行节点]==>携程车票检索")
        try:
            response = await self.ticket_search.ticket_search(state['user_input'])
            if response.success:
                state['searched_tickets'] = response.content
                state['user_preference'] = response.metadata['user_preference']
            else:
                state['error_msg'] = f"车票检索失败：{response.error}"
                state['final_output'] = f"车票检索失败：{response.error}"
                logger.error(state['error_msg'])
        except Exception as e:
            error_msg = f"车票搜索节点异常: {str(e)}"
            state["error_msg"] = error_msg
            state["final_output"] = error_msg
            logger.error(error_msg)
        state['execution_path'].append('c_trip_ticket_search')
        return state

    async def c_trip_hotel_search_node(self, state:WorkflowState):
        logger.info('=' * 50)
        logger.info("[执行节点]==>携程酒店检索")
        try:
            response = await self.hotel_search.hotel_search(state['user_input'])
            if response.success:
                state['searched_hotels'] = response.content
                state['user_preference'] = response.metadata['user_preference']
            else:
                state['error_msg'] = f"酒店检索失败：{response.error}"
                state['final_output'] = f"酒店检索失败：{response.error}"
                logger.error(state['error_msg'])
        except Exception as e:
            error_msg = f"酒店搜索节点异常: {str(e)}"
            state["error_msg"] = error_msg
            state["final_output"] = error_msg
            logger.error(error_msg)
        state['execution_path'].append('c_trip_hotel_search')
        return state

    async def c_trip_ticket_summary_node(self, state:WorkflowState):
        logger.info('=' * 50)
        logger.info('[执行节点]==>携程车票总结')
        try:
            response = await self.ticket_summary.ticket_summary(state['searched_tickets'] ,state['user_preference'])
            if response.success:
                state['summary_tickets'] = response.content
            else:
                state['error_msg'] = f"车票总结失败：{response.error}"
                state['final_output'] = f"车票总结失败：{response.error}"
                logger.error(state['error_msg'])
        except Exception as e:
            error_msg = f"车票总结节点异常: {str(e)}"
            state["error_msg"] = error_msg
            state["final_output"] = error_msg
            logger.error(error_msg)
        state['execution_path'].append('c_trip_ticket_summary')
        return state

    async def c_trip_hotel_summary_node(self, state: WorkflowState):
        logger.info('=' * 50)
        logger.info('[执行节点]==>携程酒店总结')
        try:
            response = await self.hotel_summary.hotel_summary(state['searched_hotels'], state['user_preference'])
            if response.success:
                state['summary_hotels'] = response.content
            else:
                state['error_msg'] = f"酒店总结失败：{response.error}"
                state['final_output'] = f"酒店总结失败：{response.error}"
                logger.error(state['error_msg'])
        except Exception as e:
            error_msg = f"酒店总结节点异常: {str(e)}"
            state["error_msg"] = error_msg
            state["final_output"] = error_msg
            logger.error(error_msg)
        state['execution_path'].append('c_trip_hotel_summary')
        return state

    async def c_trip_ticket_review_node(self, state: WorkflowState):
        logger.info('=' * 50)
        logger.info('[执行节点]==>携程车票审查')
        try:
            state['needs_retry'] = False
            state['review_pass'] = False
            response = await self.ticket_review.ticket_review(state['searched_tickets'], state['user_preference'], state['summary_tickets'])
            if response.success:
                state['reviewed_tickets'] = response.content
                state['review_pass'] = True
                state['final_output'] = response.content
                logger.info('[节点执行成功]==>车票审查通过')
            else:
                # 审查不通过
                state['review_pass'] = False
                state['ticket_retry_count'] = state.get('ticket_retry_count', 0) + 1

                if state['ticket_retry_count'] <= 2:
                    # 打回重试：把修改建议传给 Summary Agent
                    feedback = response.metadata.get("feedback", {}) if response.data else {}
                    logger.warning(
                        f"[车票审查不通过]==>第{state['ticket_retry_count']}次重试，"
                        f"原因：{feedback.get('reason', '未知')}"
                    )
                    # 重新调用 Summary Agent
                    retry_result = await self.ticket_summary.ticket_summary(
                        tickets_info=state['searched_tickets'],
                        user_preference=state['user_preference'],
                        feedback=feedback.get('suggestions', []),  # 传入修改建议
                    )
                    state['summary_tickets'] = retry_result.content
                    state['needs_retry'] = True  # 标记需要重新进入审查节点
                else:
                    # 重试次数用尽
                    logger.warning('[车票审查重试次数用尽]==>返回当前结果并标注')
                    state['reviewed_tickets'] = response.content
                    state['final_output'] = (
                            state['summary_tickets'] +
                            "\n\n审核未完全通过，以下问题未能修复：\n" +
                            response.data.get("feedback", {}).get("reason", "未知")
                    )
        except Exception as e:
            error_msg = f"车票审查节点异常: {str(e)}"
            state["error_msg"] = error_msg
            state["final_output"] = error_msg
            logger.error(error_msg)
        state['execution_path'].append('c_trip_ticket_review')
        return state

    async def c_trip_hotel_review_node(self, state: WorkflowState):
        logger.info('=' * 50)
        logger.info('[执行节点]==>携程酒店审查')
        try:
            state['needs_retry'] = False
            state['review_pass'] = False
            response = await self.hotel_review.hotel_review(state['searched_hotels'],state['user_preference'], state['summary_hotels'])
            if response.success:
                state['reviewed_hotels'] = response.content
                state['review_pass'] = True
                state['final_output'] = response.content
                logger.info('[节点执行成功]==>酒店审查通过')
            else:
                # 审查不通过
                state['review_pass'] = False
                state['hotel_retry_count'] = state.get('hotel_retry_count', 0) + 1

                if state['hotel_retry_count'] <= 2:
                    # 打回重试：把修改建议传给 Summary Agent
                    feedback = response.metadata.get("feedback", {}) if response.data else {}
                    logger.warning(
                        f"[酒店审查不通过]==>第{state['hotel_retry_count']}次重试，"
                        f"原因：{feedback.get('reason', '未知')}"
                    )
                    # 重新调用 Summary Agent
                    retry_result = await self.hotel_summary.hotel_summary(
                        hotels_info=state['searched_hotels'],
                        user_preference=state['user_preference'],
                        feedback=feedback.get('suggestions', []),  # 传入修改建议
                    )
                    state['summary_hotels'] = retry_result.content
                    state['needs_retry'] = True  # 标记需要重新进入审查节点
                else:
                    # 重试次数用尽
                    logger.warning('[酒店审查重试次数用尽]==>返回当前结果并标注')
                    state['reviewed_hotels'] = response.content
                    state['final_output'] = (
                            state['summary_hotels'] +
                            "\n\n审核未完全通过，以下问题未能修复：\n" +
                            response.data.get("feedback", {}).get("reason", "未知")
                    )
        except Exception as e:
            error_msg = f"酒店审查节点异常: {str(e)}"
            state["error_msg"] = error_msg
            state["final_output"] = error_msg
            logger.error(error_msg)
        state['execution_path'].append('c_trip_hotel_review')
        return state

    def _route_by_intention(self, state: WorkflowState) -> Literal["chat", "travel", "rag"]:
        """第一次意图路由（同步）"""
        intent = state.get("intention", "chat")
        logger.info(f"[第一次路由决策]==> {intent}")
        return intent

    def _travel_route_by_intention(self, state: WorkflowState) -> Literal["ticket", "hotel", "baidu"]:
        """第二次旅行意图细分"""
        intent = state.get("travel_intent", "ticket")
        logger.info(f"[第二次旅行意图决策]==> {intent}")
        return intent

    def _route_after_review(self, state: WorkflowState):
        """是否重写"""
        if state.get('needs_retry'):
            state['needs_retry'] = False
            return 'retry'
        return 'pass'

    async def rag_node(self, state:WorkflowState):
        logger.info('=' * 50)
        logger.info('[执行节点]==>RAG 文档问答')
        try:
            response = await self.rag_agent.run(state['user_input'])
            if response.success:
                state['final_output'] = response.content
            else:
                state['error_msg'] = f"RAG 问答失败：{response.error}"
                state['final_output'] = f"RAG 问答失败：{response.error}"
                logger.error(state['error_msg'])
        except Exception as e:
            error_msg = f"RAG 节点异常: {str(e)}"
            state["error_msg"] = error_msg
            state["final_output"] = error_msg
            logger.error(error_msg)
        state['execution_path'].append('rag')
        return state

    async def review_node(self, state:WorkflowState):
        pass

    # async def travel_intention_node(self, state: WorkflowState):
    #     user_input = state.get('user_input', '').lower()
    #
    #     if any(kw in user_input for kw in ['导航', '路线', '地图', '怎么去', '驾车', '公交']):
    #         state['sub_intent'] = 'baidu'
    #     elif any(kw in user_input for kw in ['酒店', '住宿', '宾馆']):
    #         state['sub_intent'] = 'hotel'
    #     else:
    #         state['sub_intent'] = 'ticket'  # 默认车票
    #
    #     state['execution_path'].append('travel_intention')
    #     return state

    async def run(self, user_input: str, session_id: str = "default"):
        """执行整个工作流，并添加 LangSmith 追踪"""
        logger.info('=' * 50)
        logger.info(f"Starting workflow run for session: {session_id}")
        logger.info('=' * 50)
        initial_state: WorkflowState = {
            "user_input": user_input,
            "user_preference": '',
            "intention": "chat",
            "intention_confidence": 0.0,
            "travel_intent": 'ticket',
            "travel_intent_confidence": 0.0,
            "sub_intent": '',
            "sub_intent_confidence": 0.0,
            "execution_path": [],
            "history": [],
            "final_output": "",
            "searched_tickets": [],
            "searched_hotels": [],
            "summary_tickets": "",
            "summary_hotels": "",
            "reviewed_tickets": "",
            "reviewed_hotels": "",
            "review_pass": False,
            "needs_retry": False,
            "ticket_retry_count": 0,
            "hotel_retry_count": 0,
            "error_msg": '',
        }
        try:
            final_state = await self.graph.ainvoke(initial_state)

            logger.info("=" * 50)
            logger.info("工作流执行完成")
            logger.info(f"执行路径: {' -> '.join(final_state['execution_path'])}")
            logger.info("=" * 50)
            return final_state
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            initial_state["error_msg"] = str(e)
            initial_state["final_output"] = f"执行失败: {str(e)}"
            return initial_state

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._exit_stack.aclose()
        logger.info("工作流连接已关闭")