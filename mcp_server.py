import datetime
import re
from typing import List, Dict, Any
import fastmcp
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from mcp.server.sse import SseServerTransport

from mcp_project.utils.logger import get_logger
from DrissionPage import ChromiumOptions
from DrissionPage import ChromiumPage
from urllib.parse import quote
import time
import json
import httpx
logger = get_logger(__name__)
from mcp_project.rag.database import DatabaseManager
from mcp_project.rag.vector_store import VectorStore
from mcp_project.rag.final_retrieve import FinalRetrieval
from mcp_project.rag.rag_system import RagSystem
from mcp_project.config.settings import settings
# from mcp_project.mcp.tool_registry import MCP

mcp = fastmcp.MCP()

# 初始化 RAG 系统
db_manager = DatabaseManager()
vector_store = VectorStore()
retriever = FinalRetrieval(db_manager=db_manager)
rag_system = RagSystem(settings, db_manager, vector_store, retriever)

# ============================Tool================================
# 获取当前日期，返回值例如：2026-04-27
@mcp.tool()
def get_current_time():
    return datetime.datetime.now().date()


# RAG 检索工具
@mcp.tool()
async def rag_retrieve(question: str, document_ids: str = None, session_id: str = None) -> str:
    """
    RAG 检索工具：基于文档内容回答用户问题

    Args:
        question: 用户问题
        document_ids: 文档ID列表，用逗号分隔，例如 "1,2,3"
        session_id: 会话ID，可选

    Returns:
        回答内容
    """
    try:
        # 解析文档ID
        doc_ids = None
        if document_ids:
            doc_ids = [int(id.strip()) for id in document_ids.split(',') if id.strip()]

        # 生成会话ID
        if not session_id:
            session_id = rag_system.generate_session_id()

        # 调用 RAG 系统
        answer, retrieved_docs = rag_system.rag_chat(question, doc_ids, session_id)

        return answer
    except Exception as e:
        logger.error(f"RAG 检索工具错误: {e}")
        return f"处理问题时出现错误: {str(e)}"


# 注册到工具注册器
# MCP.register_tool("rag_retrieve", rag_retrieve)


# 携程车票检索工具
@mcp.tool()
def c_trip_ticket_search(start_date, departure, destination) -> List[Dict[str, Any]]:
    logger.info(f"[开始车票检索]==>出发日期为{start_date}，从{departure} 到 {destination}")

    co = ChromiumOptions()
    co.set_browser_path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    dp = ChromiumPage(addr_or_opts=co)

    try:
        # 1. 准备参数
        departure_ = quote(departure)
        destination_ = quote(destination)
        start_date_ = start_date

        # 2. 构造url
        url = f"https://trains.ctrip.com/webapp/train/list?ticketType=0&dStation={departure_}&aStation={destination_}&dDate={start_date_}&rDate=&trainsType=&hubCityName=&highSpeedOnly=0"

        # 3. 启动监听
        dp.listen.start('GetBookingByStationV3')

        # 4. 直接访问构造好的目标页面
        print(f"正在访问: {url}")
        dp.get(url)

        dp.ele('text=搜索').click()

        # 5. 等待数据包
        print("正在等待数据包返回...")
        res = dp.listen.wait(timeout=15)

        if res:
            # res 如果不是 False，它就是一个 DataPacket 对象
            print(">>> 成功截获数据包！")
            print(f"URL: {res.url}")

            if 'ResponseBody' in res.response.body:
                trains = res.response.body['ResponseBody'].get('TrainInfoList', [])
                print(f"共{len(trains)}趟车次信息")
                if trains:
                    results = []
                    for i in trains:
                        num = i.get('TrainNumber')
                        d_station = i.get('DepartStation')
                        a_station = i.get('ArriveStation')
                        d_time = i.get('DepartTime')
                        a_time = i.get('ArriveTime')
                        runtime = i.get('RunTime') # int

                        train_type = "unknown"
                        seats = {}
                        if num and len(num) > 0:
                            first_char = num[0]
                            if first_char in ["G", "C"]:
                                train_type = "high_speed"
                            elif first_char in ["Z", "T", "K"]:
                                train_type = "normal"
                            elif first_char == "D":
                                train_type = "d_series_train"
                            else:
                                continue
                        if train_type == "high_speed":
                            seats = {
                                "商务座": "--",
                                "一等座": "--",
                                "二等座": "--",
                                "无座": "--",
                            }
                        elif train_type == "normal":
                            seats = {
                                "硬座": "--",
                                "硬卧上铺": "--",
                                "硬卧中铺": "--",
                                "硬卧下铺": "--",
                                "软卧上铺": "--",
                                "软卧下铺": "--",
                                "无座": "--",
                            }
                        elif train_type == "d_series_train":
                            seats = {
                                "二等座": "--",
                                "一等座": "--",
                                "二等卧": "--",
                                "一等卧": "--",
                                "无座": "--"
                            }
                        for j in i.get('SeatList', []):
                            seat_name = j.get('SeatName')
                            inventory = j.get('SeatInventory')
                            other_seats = j.get('OtherSeatInfoList', [])
                            if other_seats:
                                for sub_seat in other_seats:
                                    sub_seat_name = sub_seat.get('SeatName')
                                    price = sub_seat.get('Price', 0)
                                    if inventory > 20:
                                        status = f"票量充足，价格{price}"
                                    elif inventory > 0:
                                        status = f"仅剩{inventory}，价格{price}"
                                    else:
                                        status = "无票"
                                        # 根据不同列车类型判断
                                    if train_type == "high_speed":
                                        if sub_seat_name in ["商务座", "一等座", "二等座", "无座"]:
                                            seats[sub_seat_name] = status
                                    elif train_type == "normal":
                                        # 普通列车的铺位：硬卧上铺、硬卧中铺、硬卧下铺、软卧上铺、软卧下铺
                                        if sub_seat_name in ["硬座", "硬卧上铺", "硬卧中铺", "硬卧下铺", "软卧上铺",
                                                             "软卧下铺", "无座"]:
                                            seats[sub_seat_name] = status
                                    elif train_type == "d_series_train":
                                        if sub_seat_name in ["二等座", "一等座", "二等卧", "一等卧", "无座"]:
                                            seats[sub_seat_name] = status
                            else:
                                # 无铺位信息（硬座、无座、二等座、一等座等）
                                price = j.get('ShowSeatPrice', 0)

                                if inventory > 20:
                                    status = f"票量充足，价格{price}"
                                elif inventory > 0:
                                    status = f"仅剩{inventory}，价格{price}"
                                else:
                                    status = "无票"

                                # 根据不同列车类型判断
                                if train_type == "high_speed":
                                    if seat_name in ["商务座", "一等座", "二等座", "无座"]:
                                        seats[seat_name] = status
                                elif train_type == "normal":
                                    if seat_name in ["硬座", "硬卧", "软卧", "无座"]:
                                        # 兜底
                                        seats[seat_name] = status
                                elif train_type == "d_series_train":
                                    if seat_name in ["二等座", "一等座", "二等卧", "一等卧", "无座"]:
                                        seats[seat_name] = status
                        results.append({
                            '车次': num,
                            '类型': "高铁" if train_type == "high_speed" else "普通列车" if train_type == "normal" else "动车",
                            "出发站": d_station,
                            "到达站": a_station,
                            "出发时间": d_time,
                            "到达时间": a_time,
                            "耗时": runtime,
                            **seats
                        })
                    return results
                else:
                    return []
            else:
                return []
        else:
            logger.error("监听失败：在 15 秒内未发现目标请求包。")
            return []
    except Exception as e:
        logger.error(f"[车票检索工具出错]==>{e}")
        return []
    finally:
        dp.quit()

# 携程酒店查询工具
@mcp.tool()
def c_trip_hotel_search(start_date, end_date, destination: str, room_num: str, adult_num, children_num) -> List[Dict[str, Any]]:
    """
    这个工具是去检索 符合日期和人数和地区要求的酒店，
    得再去写一个resource？还是prompt，传入这些符合要求的酒店（带着周边设施和价格），
    再让大模型去筛选符合最终要求的酒店
    """
    co = ChromiumOptions()
    co.set_browser_path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    dp = ChromiumPage(addr_or_opts=co)
    try:
        # 1.由于日期真的很难根据元素去找，所以构造url直接填好
        url = (f'https://hotels.ctrip.com/hotels/list'
              f'?countryId=1&city=3&provinceId=0'
              f'&checkin={start_date}&checkout={end_date}'
              f'&optionId=3&optionType=City&directSearch=0'
              f'&display=%E5%A4%A9%E6%B4%A5&crn={room_num}'
              f'&adult={adult_num}&children={children_num}&searchBoxArg=t'
              f'&travelPurpose=0&ctm_ref=ix_sb_dl'
              f'&domestic=1&&v2_mod=95&v2_version=E')
        # 2.打开网页
        dp.get(url)
        # 3.启动监听
        dp.listen.start('fetchHotelList')
        # 4.清除原本城市，重新输入所需要的城市
        dp.ele('#destinationInput').click().input(destination, clear=True)
        dp.wait.ele_displayed('.city-list-item', timeout=5)
        dp.ele(f'text={destination}', timeout=3).click()
        # 5.点击“搜索”，刷新一下页面
        dp.ele('text=搜索').click()
        time.sleep(2)
        # 6.选择“好评优先”，才会出现‘fetchHotelList’这个请求头
        dp.ele('text=欢迎度排序').click()
        dp.ele('text=好评优先').click()
        # 7.循环以获取更多数据
        page = 1
        results = []
        while True:
            print(f'正在抓取第{page}页...')

            res = dp.listen.wait(timeout=15)
            if res:
                data = res.response.body
                hotels = data['data']['hotelList']

                for i in hotels:
                    first_room = i.get('roomInfo', [])[0]
                    advantage_tags = first_room.get('roomTags', {}).get('advantageTags', [])
                    dict_data = {
                        '酒店名称': i.get('hotelInfo', {}).get('nameInfo', {}).get('name', ''),
                        "星级": i.get('hotelInfo', {}).get('hotelStar', {}).get('star', ''), # "hotelStar": {"star": 5...返回值为int
                        "评分": i.get('hotelInfo', {}).get('commentInfo', {}).get('commentScore', ''),
                        "酒店地址": i.get('hotelInfo', {}).get('positionInfo', {}).get('address', ''),# 注意：这里面有纬度，是不是可以结合百度地图查纬度？
                        "临近资源": i.get('hotelInfo', {}).get('positionInfo', {}).get('positionDesc', ''),
                        "房型": first_room.get('summary', {}).get('saleRoomName', ''),
                        "价格": first_room.get('priceInfo', {}).get('price', ''),
                        "床型": first_room.get('bedInfo', {}).get('contentList', []),
                        "优势": advantage_tags[0].get('tagTitle', '') if advantage_tags else '',
                    }
                    results.append(dict_data)
                page += 1
                dp.scroll.to_bottom()
                dp.scroll.to_bottom()
                if page > 10:
                    logger.info('[执行工具完成]==>酒店搜索完成')
                    break
            else:
                logger.error('监听失败')
                break
        return results
    except Exception as e:
        logger.error(e)
        return []

# 审查工具
@mcp.tool()
def validate_infos(user_preference: str, summary: str, original_infos: List[Dict], criteria: List[str]):
    # criteria=["数据一致", "要素齐全", "需求匹配"]
    results = {
        "validations": [],
        "all_passed": True,
        "pass_rate": 0.0,
    }
    for criterion in criteria:
        validation = {"criterion": criterion, "passed": True, "message": ""}

        if "数据一致" in criterion:
            # 先判断是酒店还是车票（根据字段名自动识别）
            if "车次" in str(original_infos[0]) if original_infos else False:
                # ========== 车票模式 ==========
                # 1. 从原始数据建立 {车次: {座位类型: 价格}} 映射
                original_map = {}
                for item in original_infos:
                    train_num = item.get("车次", "")
                    if not train_num:
                        continue
                    original_map[train_num] = {}
                    for key, value in item.items():
                        # key 是座位类型（硬座、二等座等），value 是 "票量充足，价格580元"
                        if key in ("车次", "出发站", "到达站", "出发时间", "到达时间", "耗时"):
                            continue
                        if isinstance(value, str):
                            price_match = re.search(r'价格(\d+)元', value)
                            if price_match:
                                original_map[train_num][key] = price_match.group(1)

                # 2. 从总结表格提取 车次-座位等级-价格
                #    表格格式：| 排名 | 车次 | 出发站 | 到达站 | 出发时间 | 到达时间 | 耗时 | 座位等级 | 价格 | 推荐理由 |
                #    车次是第2列，座位等级是第8列，价格是第9列
                table_rows = re.findall(
                    r'\|[^|]*\|([^|]*)\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|([^|]*)\|([^|]*)\|[^|]*\|',
                    summary
                )

                mismatches = []
                for train_num, seat_type, price in table_rows:
                    train_num = train_num.strip()
                    seat_type = seat_type.strip()
                    price_str = re.search(r'(\d+)', price.strip())
                    price_num = price_str.group(1) if price_str else ""

                    if train_num in original_map:
                        if seat_type in original_map[train_num]:
                            if original_map[train_num][seat_type] != price_num:
                                mismatches.append(
                                    f"{train_num} {seat_type}: 总结{price_num}元, 原始{original_map[train_num][seat_type]}元"
                                )
                        else:
                            mismatches.append(f"{train_num}: 总结提到{seat_type}，原始数据中无此座位类型")
                    else:
                        mismatches.append(f"{train_num}: 在原始数据中未找到")

                passed = len(mismatches) == 0
                validation["passed"] = passed
                validation["message"] = f"数据一致性: {'✓' if passed else '✗ ' + '; '.join(mismatches[:3])}"
            else:
                # 1. 从原始数据建立 {酒店名: 价格} 映射
                original_map = {}
                for item in original_infos:
                    name = item.get("酒店名称", "")
                    price = str(item.get("价格", ""))
                    if name and price:
                        original_map[name] = price

                # 2. 从总结的表格行中提取 酒店名-价格 对
                #    表格格式：| 1 | 酒店名 | 5星 | 4.8 | 860元 | 含早 | 理由 |
                #    酒店名是第2列，价格是第5列
                table_rows = re.findall(r'\|[^|]*\|([^|]*)\|[^|]*\|[^|]*\|([^|]*)\|[^|]*\|', summary)
                # table_rows 是 [(酒店名, 价格), ...]

                mismatches = []
                for name, price in table_rows:
                    name = name.strip()
                    price = price.strip()  # "860元"
                    price_num = re.search(r'(\d+)', price)  # 提取数字
                    price_str = price_num.group(1) if price_num else price

                    if name in original_map:
                        if original_map[name] != price_str:
                            mismatches.append(f"{name}: 总结写{price_str}元, 原始数据为{original_map[name]}元")
                    else:
                        mismatches.append(f"{name}: 在原始数据中未找到")

                passed = len(mismatches) == 0
                validation["passed"] = passed
                validation["message"] = f"数据一致性: {'✓' if passed else '✗ ' + '; '.join(mismatches[:3])}"
        elif "要素齐全" in criterion:
            # 逻辑修正：不再强匹配文字，改用结构特征
            has_table = "|" in summary and summary.count("|") > 10
            has_recommendation = any(word in summary for word in ["推荐", "首选", "建议", "选择"])
            passed = has_table and has_recommendation
            validation["passed"] = passed
            validation["message"] = f"要素齐全: {'✓ 表格与综合推荐要素具备' if passed else '✗ 缺少对比表格或综合推荐'}"

        elif "需求匹配" in criterion:
            # 从 preference 中提取非空关键词进行覆盖率检查
            pref_values = []
            for line in user_preference.split("\n"):
                if ":" in line:
                    val = line.split(":")[-1].strip()
                    if val and "不限" not in val:
                        pref_values.append(val)

            matches = [v for v in pref_values if v in summary]
            # 只要覆盖了 50% 的硬性需求即认为通过基础校验
            passed = len(matches) >= len(pref_values) * 0.5 if pref_values else True
            validation["passed"] = passed
            validation["message"] = f"需求匹配: 覆盖了 {len(matches)}/{len(pref_values)} 个用户核心偏好"

        results["validations"].append(validation)

    results["all_passed"] = all(v["passed"] for v in results["validations"])
    results["pass_rate"] = sum(1 for v in results["validations"] if v["passed"]) / len(results["validations"])
    return results

# 百度地图
@mcp.tool()
async def search_places(query: str, region: str = "全国", city_limit: bool = True) -> str:
    """
    地点检索（POI 搜索）
    :param query: 关键词，如“加油站”
    :param region: 城市，如“北京”
    :param city_limit: 是否限制在区域内
    """
    ak = settings.BAIDU_MAP_AK
    if not ak:
        return json.dumps({"error": "百度地图 AK 未配置"})

    params = {
        "query": query,
        "region": region,
        "city_limit": city_limit,
        "output": "json",
        "ak": ak
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://api.map.baidu.com/place/v2/search", params=params)
        data = resp.json()
        if data.get("status") == 0:
            results = []
            for item in data.get("results", []):
                results.append({
                    "name": item.get("name"),
                    "address": item.get("address"),
                    "lat": item.get("location", {}).get("lat"),
                    "lng": item.get("location", {}).get("lng")
                })
            return json.dumps({"success": True, "count": len(results), "results": results}, ensure_ascii=False)
        else:
            return json.dumps({"success": False, "error": data.get("message")})

# 百度地图

@mcp.tool()
async def get_route(origin: str, destination: str, mode: str = "driving") -> str:
    """
    路线规划（支持 driving, walking, transit, riding）
    :param origin: 起点坐标 "lat,lng" 或地址文本（建议使用坐标）
    :param destination: 终点坐标
    :param mode: 出行方式 driving/walking/transit/riding
    """
    ak = settings.BAIDU_MAP_AK
    if not ak:
        return json.dumps({"error": "百度地图 AK 未配置"})

    # 简易验证是否为坐标格式（纬度,经度）
    def is_coord(s: str) -> bool:
        parts = s.split(',')
        if len(parts) != 2:
            return False
        try:
            float(parts[0]); float(parts[1])
            return True
        except:
            return False

    if not is_coord(origin) or not is_coord(destination):
        # 如果不满足坐标格式，可以提示需要先进行地理编码，这里先简单报错
        return json.dumps({"error": "起点或终点请使用坐标格式，例如 '39.9042,116.4074'。如需地址转坐标，请先调用地理编码工具。"})

    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "output": "json",
        "ak": ak
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://api.map.baidu.com/direction/v2/route", params=params)
        data = resp.json()
        if data.get("status") == 0:
            route = data["result"]["routes"][0]
            distance_km = route.get("distance", 0) / 1000
            duration_min = route.get("duration", 0) / 60
            steps = [step.get("instructions", "") for step in route.get("steps", [])[:5]]
            return json.dumps({
                "success": True,
                "distance_km": round(distance_km, 1),
                "duration_min": round(duration_min, 1),
                "steps": steps
            }, ensure_ascii=False)
        else:
            return json.dumps({"success": False, "error": data.get("message")})

# ============================Prompt================================
# 意图识别提示词
@mcp.prompt()
def get_intention_prompt(user_input: str):
    return f"""
        请分析用户输入，判断用户的意图属于以下哪一类：

        1. **chat**：普通对话，如问候、闲聊、询问助手能力等，不涉及具体信息查询或任务执行。
        2. **travel**：出行需求，明确涉及机票、火车票、酒店、景点、行程规划等旅游相关内容。
        3. **rag**：知识问答，需要基于外部知识库回答的事实性问题，如政策、定义、历史事件等。

        用户输入: {user_input}

        判断规则：
        - 出现“订票”、“酒店”、“航班”、“高铁”、“自驾”、“路线推荐”等词 → travel
        - 出现“什么是”、“为什么”、“如何理解”、“规定是什么”等知识性问题 → rag  
        - 单纯打招呼、问好、表达情绪 → chat
        - 边界模糊时，优先判断为更具体的类别（chat > travel > rag）

        格式：
        意图: [intent]
        置信度: [confidence]
    """

# 第二次意图识别提示词
@mcp.prompt()
def get_travel_intention_prompt(user_input: str):
    return f"""
        请分析用户输入，判断用户在“出行（travel）”这个大范畴下，具体的垂直意图是什么：
        
        意图分类：
        1. **ticket**：用户想要查询、购买或者咨询关于火车、高铁、列车的内容。
        2. **hotel**：用户想要找地方住、预订房间、看酒店价格或住宿推荐。
        3. **baidu**：用户想要知道怎么去某个地方、寻找路线、导航、或是自驾/公交规划。
        4. **mixed**：用户一句话里既要查票又要订房（例如：“帮我看看明天去上海的车票和外滩附近的酒店”）。

        用户输入: {user_input}

        判断规则：
        - 核心关键词包含“车、票、列车、高铁、动车、班次” → ticket
        - 核心关键词包含“住、店、房、宿、宾馆、民宿” → hotel
        - 核心关键词包含“怎么走、路线、导航、地图、走哪条路” → baidu
        - 如果同时出现上述两类或以上需求 → mixed

        输出格式：
        意图: [travel_intent]
        置信度: [travel_intent_confidence]
"""

# 车票信息提取的提示词
@mcp.prompt()
def extract_ticket_info_prompt(current_time: str, user_input: str):
    return f"""
        你是一个高效率的车票信息解析助手。你的任务是从用户的非结构化输入中提取关键的车票信息。
        当前日期：{current_time}
        用户输入：{user_input}
        
        # 要求：
        请分析用户的输入，推断并提取以下字段：
        1. start_date: 出发日期, 格式为 YYYY-MM-DD。
        2. departure: 用户提到的出发地点
        3. destination：用户提到的目的地点
        4. run_time: 用户对路程耗时的最大限制（分钟数）。只输出数字，不要带单位。若未提及则输出"不限"。示例：2小时→120，1.5小时→90，半小时→30
        5. s_time: 用户对出发时间的要求，输出格式：
            - 如果是时间段（上午/下午/晚上），直接输出"上午"/"下午"/"晚上"
            - 如果有具体时间点（如"8点"、"下午2点"），输出格式为"时间点:XX点"（如"时间点:8点"、"时间点:14点"）
            - 如果有最晚时间限制（如"最晚下午两点前"），输出格式为"最晚:14点"
            - 如果有最早时间限制（如"最早8点后"），输出格式为"最早:8点"
            - 若未提及，输出"不限"
        6. e_time: 用户对到达时间的要求，格式同 s_time。
            示例：
            - "下午到" → "下午"
            - "最晚下午两点前能到达" → "最晚:14点"
            - "中午12点左右到达" → "时间点:12点"
        7. price_min: 最低价格，默认为0.
        8. price_max: 用户提到的能接受的最高价格，若未提及，默认为“不限”。
        9. seat: 用户提到的座位等级，如“一等座”、“二等座”、“商务座”、“硬卧”等，若未提及，默认为“不限”。
        10. d_station: 用户提到的出发车站，若未提及，默认为“不限”。
        11. a_station: 用户提到的到达车站，若未提及，默认为“不限”。
        12. type: 用户提到的列车类型，高铁或者普通火车，若未提及，默认为“不限”。
        
        # 输出格式：
        start_date: [出发日期]
        departure: [出发地]
        destination: [目的地]
        run_time: [耗时/不限]
        s_time: [出发时间/不限]
        e_time: [到达时间/不限]
        price_min: [数字]
        price_max: [数字/不限]
        seat: [座位等级/不限]
        d_station: [出发车站/不限]
        a_station: [到达车站/不限]
        type: [列车类型/不限]
    """

# 酒店信息提取的提示词
@mcp.prompt()
def extract_hotel_info_prompt(current_time: str, user_input: str):
    return f"""
        你是一个高效率的旅游行程解析助手。你的任务是从用户的非结构化输入中提取关键的酒店预订信息。
        当前日期：{current_time}
        用户输入：{user_input}
        
        # 要求：
        请分析用户的输入，推断并提取以下字段：
        1. 入住日期 (check_in): 格式为 YYYY-MM-DD。
        2. 退房日期 (check_out): 格式为 YYYY-MM-DD。
        3. 城市 (city): 酒店所在的城市。
        4. 酒店级别 (star_rating): 用户要求的星级或档次，若未提及，默认为“不限”。
        5. 房间数 (room_num): 用户提到的房间数，默认为1。
        6. 成人数 (adults): 用户提到的人数，默认为1。
        7. 儿童数 (children): 默认为 0。
        8. 特殊要求(breakfast): 用户要求含早餐填"是"，若未提及，默认为“不限”。
        9. 评分下限 (score_min): 用户提到的酒店的最低评分，若未提及，默认为“不限”。
        10. 价格下限 (price_min): 默认0
        11. 价格上限(price_max): 用户提到的最高价格，若未提及，默认为“不限”。
        
        # 输出格式：
        start_date: [入住日期]
        end_date: [退房日期]
        city: [城市]
        star_rating: [星级]
        room_num: [房间数量]
        adults: [成人数]
        children: [儿童数]
        breakfast: [是/不限]
        score_min: [数字/不限]
        price_min: [数字]
        price_max: [数字/不限]
    """

@mcp.prompt()
def get_summary_hotels(hotels_info: str, user_preference: str):
    return f"""
        你是一个专业的酒店推荐顾问。根据用户的偏好，从酒店列表中推荐最符合的酒店。
        
        用户偏好：
        {user_preference}
        
        酒店列表：
        {hotels_info}
        
        要求：
        1. 根据用户偏好的各个维度（星级、价格、评分、早餐、位置等），逐一对比酒店列表中的候选酒店
        2. 综合评估后，选出最符合用户需求的 Top 3 酒店
        3. 给出推荐理由，说明每家酒店为什么适合该用户
        4. 酒店名称、价格等各字段必须严格基于给出的酒店列表取出。
        
        输出格式：
        
        ## 综合推荐
        [一句话总结首选哪家，为什么]
        
        ## Top 3 酒店对比
        
        | 排名 | 酒店名称 | 星级 | 评分 | 价格 | 早餐 | 推荐理由 |
        |------|---------|------|------|------|------|---------|
        | 1 | xxx | 5星 | 4.8 | 860 | 含早 | 价格符合预算，评分最高... |
        | 2 | xxx | 4星 | 4.6 | 720 | 不含 | 性价比突出... |
        | 3 | xxx | 5星 | 4.5 | 950 | 含早 | 位置优越... |
    """

@mcp.prompt()
def get_review_hotels(hotels_info: str, user_preference: str, hotel_summary):
    return f"""
        你是一个严格的酒店推荐审核专家。审核以下推荐结果是否符合用户需求，给出评分和改进建议。

        用户偏好：
        {user_preference}
        
        推荐结果：
        {hotel_summary}
        
        原始酒店数据（用于事实核对）：
        {hotels_info}
        
        审核标准：
        1. 数据一致性（40分）：推荐理由中引用的酒店信息（名称、价格、评分、星级、早餐、设施等）是否与原始数据完全一致
        2. 要素齐全性（25分）：是否包含综合推荐和对比表格
        3. 需求匹配度（35分）：是否覆盖用户所有硬性条件，排序是否有充分理由。
        
        通过标准：总分 >= 70
        
        输出格式（JSON）：
        {{
            "score": 总分（0-100）,
            "passed": 是否通过（true/false）,
            "reason": 不通过时写一句话说明核心问题，通过时为空字符串,
            "suggestions": 不通过时列出具体修改建议，如['建议1', '建议2']，通过时为空列表
        }}
        """


@mcp.prompt()
def get_summary_tickets(tickets_info: str, user_preference: str):
    return f"""
        你是一个专业的车票推荐顾问。根据用户的偏好，从车票列表中推荐最符合的车次。
        
        用户偏好：
        {user_preference}
        
        车票列表：
        {tickets_info}
        
        要求：
        1. 根据用户偏好的各个维度（出发时间、到达时间、耗时、价格、座位等级、车站等），逐一对比候选车次
        2. 综合评估后，选出最符合用户需求的 Top 3 车次
        3. 给出推荐理由，说明每趟车次为什么适合该用户
        
        输出格式：
        
        ## 综合推荐
        [一句话总结首选哪趟车次，为什么]
        
        ## Top 3 车次对比
        
        | 排名 | 车次 | 出发站 | 到达站 | 出发时间 | 到达时间 | 耗时 | 座位等级 | 价格 | 推荐理由 |
        |------|------|--------|--------|----------|----------|------|----------|------|---------|
        | 1 | G123 | 北京南 | 上海虹桥 | 08:00 | 12:30 | 4小时30分 | 二等座 | 580 | 出发时间合适，高铁速度快... |
        | 2 | G456 | 北京南 | 上海虹桥 | 09:00 | 13:15 | 4小时15分 | 二等座 | 610 | 耗时最短，价格略高但合理... |
        | 3 | T109 | 北京站 | 上海站 | 20:00 | 10:30 | 14小时30分 | 硬卧 | 320 | 价格最低，夕发朝至节省住宿... |
    """


@mcp.prompt()
def get_review_tickets(tickets_info: str, user_preference: str, ticket_summary):
    return f"""
        你是一个严格的车票推荐审核专家。审核以下推荐结果是否符合用户需求，给出评分和改进建议。
        
        用户偏好：
        {user_preference}
        
        推荐结果：
        {ticket_summary}
        
        原始车票数据（用于事实核对）：
        {tickets_info}
        
        审核标准：
        1. 数据一致性（40分）：推荐理由中引用的车票信息是否与原始数据完全一致。
        2. 要素齐全性（25分）：是否包含综合推荐和对比表格。
        3. 需求匹配度（35分）：推荐的车次是否覆盖用户的所有硬性条件，排序是否有充分理由，有无更优但被遗漏的车次。
        
        通过标准：总分 >= 70
        
        输出格式（JSON）：
        {{
            "score": 总分（0-100），
            "passed": 是否通过（true/false），
            "reason": 不通过时写一句话说明核心问题，通过时为空字符串,
            "suggestions": 不通过时列出具体修改建议，如['建议1', '建议2']，通过时为空列表
        }}
    """
# ============================Resource================================
@mcp.resource("reviewStandards://travel-recommendation", mime_type="text/plain")
def get_travel_review_standards() -> str:
    return """
        # 出行推荐审核标准
        
        ## 评分标准（总分100）
        
        ### 1. 数据一致性（40分）
        - **价格准确（15分）**
          - 推荐表格中的价格是否与原始数据一致
          - 有无编造或篡改价格的情况
          - 价格单位是否正确（元）
        
        - **信息真实（15分）**
          - 评分、星级、设施（早餐/健身房等）是否真实存在
          - 酒店名称/车次是否在原始数据中可查
          - 是否有幻觉生成的虚假信息
        
        - **引用完整（10分）**
          - 推荐理由中引用的关键字段是否都有据可查
          - 排名依据是否有原始数据支撑
        
        ### 2. 要素齐全性（25分）
        - **结构完整（15分）**
          - 是否包含综合推荐（开头总结段）
          - 是否包含对比表格（Top 3 或 Top 5）
        
        - **内容完整（10分）**
          - 表格是否包含所有关键列（名称、星级/车次、价格、评分/耗时、推荐理由）
          - 推荐理由是否具体，而非泛泛而谈
          - 用户关心的维度是否都有回应
        
        ### 3. 需求匹配度（35分）
        - **硬性条件满足（20分）**
          - 用户明确提出的星级、价格区间是否全部满足
          - 日期、城市、人数等基础条件是否匹配
          - 特殊要求（早餐、座位等级、车站偏好等）是否覆盖
        
        - **排序合理性（15分）**
          - 推荐排序是否有充分理由支撑
          - 是否有更优但被遗漏的选项
          - 推荐理由之间是否存在矛盾
        
        ## 通过标准
        - 总分 >= 70分：通过
        - 总分 >= 85分：优秀
        - 总分 < 70分：不通过，需重新生成
        
        ## 常见问题检查清单
        - [ ] 推荐表格中的价格与原始数据一致吗？
        - [ ] 所有引用的设施/标签真实存在吗？
        - [ ] 酒店名称/车次在原始数据中能查到吗？
        - [ ] 是否有综合推荐、对比表格两要素？
        - [ ] 用户的硬性条件（星级、预算、早餐等）全部满足了吗？
        - [ ] 排名第一的选项确实是最优吗？
        - [ ] 有没有更匹配但被遗漏的选项？
        - [ ] 推荐理由是否自相矛盾？
"""

# ============================FastAPI=================================
app = FastAPI(title='MCP Server - Personal assistant')
sse_transport = None
@app.get('/sse')
async def sse_handler(request: Request):
    global sse_transport
    sse_transport = SseServerTransport('/messages')
    async with sse_transport.connect_sse(
        request.scope,
        request.receive,
        request._send
    )as streams:
        read_stream, write_stream = streams
        await mcp.run(
            read_stream,
            write_stream,
            mcp.create_initialization_options()
        )
@app.post('/messages')
async def messages_handler(request: Request):
    global sse_transport
    if sse_transport is None:
        raise HTTPException(status_code=400, detail="no active...")
    await sse_transport.handle_post_message(
        request.scope,
        request.receive,
        request._send
    )
    return Response(content=b"", status_code=200, media_type='text/plain')

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8056)