import re
from typing import Any, Dict, List
from mcp_project.utils.logger import get_logger
logger = get_logger(__name__)
from mcp_project.agents.base import BaseAgent
from mcp_project.workflow.state import AgentResponse
class TicketSearch(BaseAgent):
    def __init__(self, mcp_tools, mcp_adapter):
        super().__init__(mcp_tools, mcp_adapter, 'ticket_searcher')
        self.get_current_time = self.get_tool('get_current_time')
        self.ticket_search_tool = self.get_tool('c_trip_ticket_search')
        logger.info("[初始化]==>车票搜索agent初始化完成")

    def check_time_limit(self, ticket_time: str, user_limit: str) -> bool:
        if user_limit == '不限' or not ticket_time:
            return True
        hour = int(ticket_time.split(':')[0])

        # 第一种情况：
        if user_limit == "上午":
            return 0 <= hour < 12
        if user_limit == "下午":
            return 12 <= hour < 18
        if user_limit == "晚上":
            return 18 <= hour < 24

        # 第二种情况
        if user_limit.startswith("时间点："):
            user_time = re.search(r'时间点:(\d{1,2})点', user_limit)
            if user_time:
                target_hour = int(user_time.group(1))
                return target_hour-1 <= hour <= target_hour+1
            return True

        # 第三种情况
        if user_limit.startswith("最晚:"):
            match = re.search(r'最晚:(\d{1,2})点', user_limit)
            if match:
                limit_hour = int(match.group(1))
                return hour < limit_hour  # 匹配这个数字之前的时间点
            return True
        # 第四种情况
        if user_limit.startswith("最早:"):
            match = re.search(r'最早:(\d{1,2})点', user_limit)
            if match:
                limit_hour = int(match.group(1))
                return hour >= limit_hour  # 匹配这个数字及之后的时间点
            return True
        return True

    async def ticket_search(self, user_input: str):
        try:
            logger.info('[车票检索中...]')
            # 1.获取当前时间
            current_time = await self.get_current_time.coroutine()
            # 2.构建提示词，调用llm，从用户输入中获取 出发日期，出发地和目的地
            prompt = self.mcp_adapter.get_prompt(
                'extract_ticket_info_prompt',
                arguments={
                    "current_time": current_time,
                    "user_input": user_input,
                }
            )
            response = await self.llm.ainvoke(prompt)
            start_date = re.search(r'start_date:\s*(.+)', response).group(1)
            departure = re.search(r'departure:\s*(.+)', response).group(1)
            destination = re.search(r'destination:\s*(.+)', response).group(1)

            # 3.拿着大模型返回的车票信息，调用检索工具
            searched_tickets: List[Dict[str, Any]] = await self.ticket_search_tool.coroutine(start_date, departure, destination)# type: ignore

            run_time_str = re.search(r'run_time:\s*([^\n]+)', response).group(1).strip()# str
            run_time = int(run_time_str) if run_time_str != "不限" else "不限"
            s_time = re.search(r's_time:\s*([^\n]+)', response).group(1).strip()
            e_time = re.search(r'e_time:\s*([^\n]+)', response).group(1).strip()
            price_min = re.search(r'price_min:\s*([^\n]+)', response).group(1).strip()
            price_max = re.search(r'price_max:\s*([^\n]+)', response).group(1).strip()
            seat = re.search(r'seat:\s*([^\n]+)', response).group(1).strip()
            d_station = re.search(r'd_station:\s*([^\n]+)', response).group(1).strip()
            a_station = re.search(r'a_station:\s*([^\n]+)', response).group(1).strip()
            train_type = re.search(r'type:\s*([^\n]+)', response).group(1).strip()
            rough_screening_tickets = []
            for ticket in searched_tickets:
                # 耗时限制，用户提到时限并且列车的耗时高于用户要求时，舍弃
                if run_time != "不限" and ticket.get('耗时', '') > run_time:
                    continue
                # 出发时间偏好
                if s_time != "不限":
                    depart_time = ticket.get('出发时间', '')
                    if not self.check_time_limit(depart_time, s_time):
                        continue
                # 到达时间偏好
                if e_time != "不限":
                    arrive_time = ticket.get('到达时间', '')
                    if not self.check_time_limit(arrive_time, e_time):
                        continue
                # 价格区间
                min_price = 0
                if price_min != "0"  or price_max != "不限":
                    # 获取所有有票且价格不为空的座位价格
                    available_prices = []
                    seat_fields = ["商务座", "一等座", "二等座", "硬座", "硬卧上铺", "硬卧中铺", "硬卧下铺", "无座"]
                    # 只遍历座位字段
                    for seat_name in seat_fields:
                        seat_status = ticket.get(seat_name, '')
                        if seat_status and seat_status != "--" and "无票" not in seat_status:
                            price_match = re.search(r'价格(\d+(?:\.\d+)?)', seat_status)
                            if price_match:
                                available_prices.append(float(price_match.group(1)))
                    if available_prices:
                        min_price = min(available_prices)
                        if price_min != "0" and min_price < float(price_min):
                            continue
                        if price_max != "不限" and min_price > float(price_max):
                            continue
                    else:
                        continue  # 没有有效价格
                ticket['min_price'] = min_price

                # 座位等级
                if seat != "不限":
                    seat_status = ticket.get(seat, '')
                    if not seat_status or seat_status == "--" or "无票" in seat_status:
                        continue
                # 出发车站
                if d_station != "不限" and d_station not in ticket.get('出发站', ''):
                    continue
                # 到达车站
                if a_station != "不限" and a_station not in ticket.get('到达站', ''):
                    continue
                # 车的类型
                if train_type != "不限":
                    train_type_ = ticket.get('类型', '')
                    if train_type == "高铁" and train_type_ != "高铁":
                        continue
                    if train_type == "普通火车" and train_type_ != "普通列车":
                        continue
                    if train_type == "动车" and train_type_ != "动车":
                        continue
                rough_screening_tickets.append(ticket)

            # 6. 取前5条最优车票，价格越低越好，耗时越短越好
            if len(rough_screening_tickets) > 5:
                for ticket in rough_screening_tickets:
                    price = float(ticket.get('min_price', 9999))
                    time_minutes =  ticket.get('耗时', '99999分')
                    ticket['总分'] = (2000 - price) / 50 - time_minutes / 10
                rough_screening_tickets.sort(key=lambda x: x['总分'], reverse=True)
                final_tickets = rough_screening_tickets[:5]
            else:
                final_tickets = rough_screening_tickets
            return AgentResponse(
                success=True,
                content=final_tickets,
                metadata={
                    'user_preference': response,
                }
            )
        except Exception as e:
            logger.error('[车票检索失败]')
            return AgentResponse(
                success=False,
                error=str(e),
                content=[]
            )