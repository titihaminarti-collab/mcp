from typing import Any, Dict, List
from mcp_project.agents.base import BaseAgent
from mcp_project.utils.logger import get_logger
import re

from mcp_project.workflow.state import AgentResponse

logger = get_logger(__name__)

class HotelSearch(BaseAgent):
    def __init__(self, mcp_tools, mcp_adapter):
        super().__init__(mcp_tools, mcp_adapter, 'hotel_searcher')
        self.get_current_time = self.get_tool('get_current_time')
        self.hotel_searcher = self.get_tool('c_trip_hotel_search')
        logger.info('[初始化]==>酒店搜索agent初始化完成')

    async def hotel_search(self, user_input: str):
        try:
            logger.info("[执行agent]==>酒店搜索中...")
            # 1.得到当前日期 ,返回值例如：2026-04-27
            current_time =  await self.get_current_time.coroutine()
            # 2.先把用户输入放入提示词，调用llm先生成一个酒店信息，然后去调用爬虫工具，返回符合要求的酒店
            prompt = self.mcp_adapter.get_prompt(
                'extract_hotel_info_prompt',
                arguments={
                    "current_time": current_time,
                    "user_input": user_input
                }
            )
            # 3.得到用户酒店要求字符串
            response = await self.llm.ainvoke(prompt) # 这里得到的直接就是content的字符串
            # 4.正则匹配每个用户要求的酒店条件
            start_date = re.search(r'start_date:\s*([^\n]+)', response).group(1).strip()
            end_date = re.search(r'end_date:\s*([^\n]+)', response).group(1).strip()
            departure = re.search(r'city:\s*([^\n]+)', response).group(1).strip()
            room_num = re.search(r'room_num:\s*([^\n]+)', response).group(1).strip()
            adults = re.search(r'adults:\s*([^\n]+)', response).group(1).strip()
            children = re.search(r'children:\s*([^\n]+)', response).group(1).strip()

            star_rating_str = re.search(r'star_rating:\s*([^\n]+)', response).group(1).strip() #str
            star_rating = int(star_rating_str) if star_rating_str != "不限" else "不限"
            score_min_str = re.search(r'score_min:\s*([^\n]+)', response).group(1).strip()
            score_min = float(score_min_str) if score_min_str != "不限" else "不限"
            price_max_str = re.search(r'price_max:\s*([^\n]+)', response).group(1).strip()
            price_max = float(price_max_str) if price_max_str != "不限" else "不限"
            breakfast = re.search(r'breakfast:\s*([^\n]+)', response).group(1).strip()
            # 5.调用查询工具，获得所有满足条件的酒店列表
            searched_hotels: List[Dict[str, Any]] = await self.hotel_searcher.coroutine(start_date, end_date, departure, room_num, adults, children) #type: ignore
            # 6.根据星级、评分、价格、有无早餐进行粗筛
            rough_screening_hotels = []
            for i in searched_hotels:
                # 如果用户提到星级但是酒店的星级不是用户所要求的，跳过不保留
                if star_rating != "不限" and i.get('星级', '') != star_rating:
                    continue
                # 用户提到最低评分但是酒店评分小于这个最低评分的，淘汰
                if score_min != '不限' and float(i.get('评分', '')) < score_min:
                    continue
                if price_max != "不限" and float(i.get('价格', 0)) > price_max:
                    continue
                if breakfast == "是" and "包早餐" not in i.get('优势', ''):
                    continue
                rough_screening_hotels.append(i)
            # 7.保留最符合条件的10个酒店信息，如果用户要求不够详细，就计算酒店平均分，获得前20个价格合理、评分高、星级高的酒店
            if len(rough_screening_hotels) > 10:
                for hotel in rough_screening_hotels:
                    score = float(hotel.get('评分', 0))
                    price = float(hotel.get('价格', 9999))
                    star = hotel.get('星级', 0)
                    hotel['总分'] = score * 10 + (2000 - price) / 100 + star * 5
                rough_screening_hotels.sort(key=lambda x: x['总分'], reverse=True)
                final_hotels = rough_screening_hotels[:10]
            else:
                final_hotels = rough_screening_hotels
            return AgentResponse(
                success=True,
                content=final_hotels,
                metadata={
                    'user_preference': response,
                }
            )

        except Exception as e:
            logger.error(e)
            return AgentResponse(
                success=False,
                content=[],
                error=str(e),
            )
