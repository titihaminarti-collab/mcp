# # 车票搜索测试
# from DrissionPage import ChromiumOptions
# from DrissionPage import ChromiumPage
# from mcp_project.utils.llm_utils import LLMFactory
# from urllib.parse import quote
# import re
# llm = LLMFactory.intention_recognize()
#
#
# def get_tickets(start_date, departure, destination: str):
#     co = ChromiumOptions()
#     co.set_browser_path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
#     dp = ChromiumPage(addr_or_opts=co)
#
#     try:
#         # 1. 准备参数
#         departure_ = quote(departure)
#         destination_ = quote(destination)
#         start_date_ = start_date
#
#         # 2. 构造url
#         url = f"https://trains.ctrip.com/webapp/train/list?ticketType=0&dStation={departure_}&aStation={destination_}&dDate={start_date_}&rDate=&trainsType=&hubCityName=&highSpeedOnly=0"
#
#         # 3. 启动监听
#         dp.listen.start('GetBookingByStationV3')
#
#         # 4. 直接访问构造好的目标页面
#         print(f"正在访问: {url}")
#         dp.get(url)
#
#         dp.ele('text=搜索').click()
#
#         # 5. 等待数据包
#         print("正在等待数据包返回...")
#         res = dp.listen.wait(timeout=15)
#
#         if res:
#             # res 如果不是 False，它就是一个 DataPacket 对象
#             print(">>> 成功截获数据包！")
#             print(f"URL: {res.url}")
#
#             if 'ResponseBody' in res.response.body:
#                 trains = res.response.body['ResponseBody'].get('TrainInfoList', [])
#                 print(f"共{len(trains)}趟车次信息")
#                 if trains:
#                     results = []
#                     for i in trains:
#                         num = i.get('TrainNumber')
#                         d_station = i.get('DepartStation')
#                         a_station = i.get('ArriveStation')
#                         d_time = i.get('DepartTime')
#                         a_time = i.get('ArriveTime')
#                         runtime = i.get('RunTime')
#
#                         train_type = "unknown"
#                         seats = {}
#                         if num and len(num) > 0:
#                             first_char = num[0]
#                             if first_char in ["G", "C"]:
#                                 train_type = "high_speed"
#                             elif first_char in ["Z", "T", "K"]:
#                                 train_type = "normal"
#                             elif first_char == "D":
#                                 train_type = "d_series_train"
#                             else:
#                                 continue
#                         if train_type == "high_speed":
#                             seats = {
#                                 "商务座": "--",
#                                 "一等座": "--",
#                                 "二等座": "--",
#                                 "无座": "--",
#                             }
#                         elif train_type == "normal":
#                             seats = {
#                                 "硬座": "--",
#                                 "硬卧上铺": "--",
#                                 "硬卧中铺": "--",
#                                 "硬卧下铺": "--",
#                                 "软卧上铺": "--",
#                                 "软卧下铺": "--",
#                                 "无座": "--",
#                             }
#                         elif train_type == "d_series_train":
#                             seats = {
#                                 "二等座": "--",
#                                 "一等座": "--",
#                                 "二等卧": "--",
#                                 "一等卧": "--",
#                                 "无座": "--"
#                             }
#                         for j in i.get('SeatList', []):
#                             seat_name = j.get('SeatName')
#                             inventory = j.get('SeatInventory')
#                             other_seats = j.get('OtherSeatInfoList', [])
#                             if other_seats:
#                                 for sub_seat in other_seats:
#                                     sub_seat_name = sub_seat.get('SeatName')
#                                     price = sub_seat.get('Price', 0)
#                                     if inventory > 20:
#                                         status = f"票量充足，价格{price}"
#                                     elif inventory > 0:
#                                         status = f"仅剩{inventory}，价格{price}"
#                                     else:
#                                         status = "无票"
#                                         # 根据不同列车类型判断
#                                     if train_type == "high_speed":
#                                         if sub_seat_name in ["商务座", "一等座", "二等座", "无座"]:
#                                             seats[sub_seat_name] = status
#                                     elif train_type == "normal":
#                                         # 普通列车的铺位：硬卧上铺、硬卧中铺、硬卧下铺、软卧上铺、软卧下铺
#                                         if sub_seat_name in ["硬座", "硬卧上铺", "硬卧中铺", "硬卧下铺", "软卧上铺",
#                                                              "软卧下铺", "无座"]:
#                                             seats[sub_seat_name] = status
#                                     elif train_type == "d_series_train":
#                                         if sub_seat_name in ["二等座", "一等座", "二等卧", "一等卧", "无座"]:
#                                             seats[sub_seat_name] = status
#                             else:
#                                 # 无铺位信息（硬座、无座、二等座、一等座等）
#                                 price = j.get('ShowSeatPrice', 0)
#
#                                 if inventory > 20:
#                                     status = f"票量充足，价格{price}"
#                                 elif inventory > 0:
#                                     status = f"仅剩{inventory}，价格{price}"
#                                 else:
#                                     status = "无票"
#
#                                 # 根据不同列车类型判断
#                                 if train_type == "high_speed":
#                                     if seat_name in ["商务座", "一等座", "二等座", "无座"]:
#                                         seats[seat_name] = status
#                                 elif train_type == "normal":
#                                     if seat_name in ["硬座", "硬卧", "软卧", "无座"]:
#                                         # 兜底
#                                         seats[seat_name] = status
#                                 elif train_type == "d_series_train":
#                                     if seat_name in ["二等座", "一等座", "二等卧", "一等卧", "无座"]:
#                                         seats[seat_name] = status
#                         results.append({
#                             '车次': num,
#                             '类型': "高铁" if train_type == "high_speed" else "普通列车" if train_type == "normal" else "动车",
#                             "出发站": d_station,
#                             "到达站": a_station,
#                             "出发时间": d_time,
#                             "到达时间": a_time,
#                             "耗时": runtime,
#                             **seats
#                         })
#                     return results
#                 else:
#                     return []
#             else:
#                 return []
#         else:
#             print("监听失败：在 15 秒内未发现目标请求包。")
#             return []
#     except Exception as e:
#         print(f"[车票检索工具出错]==>{e}")
#         return []
#     # finally:
#     #     dp.quit()
#
# def check_time_limit(ticket_time: str, user_limit: str) -> bool:
#     if user_limit == '不限' or not ticket_time:
#         return True
#     hour = int(ticket_time.split(':')[0])
#
#     # 第一种情况：
#     if user_limit == "上午":
#         return 0 <= hour < 12
#     if user_limit == "下午":
#         return 12 <= hour < 18
#     if user_limit == "晚上":
#         return 18 <= hour < 24
#
#     # 第二种情况
#     if user_limit.startswith("时间点："):
#         user_time = re.search(r'时间点:(\d{1,2})点', user_limit)
#         if user_time:
#             target_hour = int(user_time.group(1))
#             return target_hour -1 <= hour <= target_hour +1
#         return True
#
#     # 第三种情况
#     if user_limit.startswith("最晚:"):
#         match = re.search(r'最晚:(\d{1,2})点', user_limit)
#         if match:
#             limit_hour = int(match.group(1))
#             return hour < limit_hour  # 匹配这个数字之前的时间点
#         return True
#     # 第四种情况
#     if user_limit.startswith("最早:"):
#         match = re.search(r'最早:(\d{1,2})点', user_limit)
#         if match:
#             limit_hour = int(match.group(1))
#             return hour >= limit_hour  # 匹配这个数字及之后的时间点
#         return True
#     return True
#
# def rough_screening(user_input, current_time):
#     user_prompt = f"""
#         你是一个高效率的车票信息解析助手。你的任务是从用户的非结构化输入中提取关键的车票信息。
#         当前日期：{current_time}
#         用户输入：{user_input}
#
#         # 要求：
#         请分析用户的输入，推断并提取以下字段：
#         1. start_date: 出发日期, 格式为 YYYY-MM-DD。
#         2. departure: 用户提到的出发地点
#         3. destination：用户提到的目的地点
#         4. run_time: 用户提到的路程耗时，若未提及，默认为“不限”。
#         5. s_time: 用户对出发时间的要求，输出格式：
#             - 如果是时间段（上午/下午/晚上），直接输出"上午"/"下午"/"晚上"
#             - 如果有具体时间点（如"8点"、"下午2点"），输出格式为"时间点:XX点"（如"时间点:8点"、"时间点:14点"）
#             - 如果有最晚时间限制（如"最晚下午两点前"），输出格式为"最晚:14点"
#             - 如果有最早时间限制（如"最早8点后"），输出格式为"最早:8点"
#             - 若未提及，输出"不限"
#         6. e_time: 用户对到达时间的要求，格式同 s_time。
#             示例：
#             - "下午到" → "下午"
#             - "最晚下午两点前能到达" → "最晚:14点"
#             - "中午12点左右到达" → "时间点:12点"
#         7. price_min: 最低价格，默认为0.
#         8. price_max: 用户提到的能接受的最高价格，若未提及，默认为“不限”。
#         9. seat: 用户提到的座位等级，如“一等座”、“二等座”、“商务座”、“硬卧”等，若未提及，默认为“不限”。
#         10. d_station: 用户提到的出发车站，若未提及，默认为“不限”。
#         11. a_station: 用户提到的到达车站，若未提及，默认为“不限”。
#         12. type: 用户提到的列车类型，高铁或者普通火车，若未提及，默认为“不限”。
#
#         # 输出格式：
#         start_date: [出发日期]
#         departure: [出发地]
#         destination: [目的地]
#         run_time: [耗时/不限]
#         s_time: [出发时间/不限]
#         e_time: [到达时间/不限]
#         price_min: [数字]
#         price_max: [数字/不限]
#         seat: [座位等级/不限]
#         d_station: [出发车站/不限]
#         a_station: [到达车站/不限]
#         type: # [列车类型/不限]
#     """
#     user_preference = llm.invoke(prompt=user_prompt).content
#     print("提取出来的车票要求:", user_preference)
#     print("============================================")
#     start_date = re.search(r'start_date:\s*(.+)', user_preference).group(1)
#     departure = re.search(r'departure:\s*(.+)', user_preference).group(1)
#     destination = re.search(r'destination:\s*(.+)', user_preference).group(1)
#
#     run_time_str = re.search(r'run_time:\s*([^\n]+)', user_preference).group(1).strip()  # str
#     run_time = int(run_time_str) if run_time_str != "不限" else "不限"
#     s_time = re.search(r's_time:\s*([^\n]+)', user_preference).group(1).strip()
#     e_time = re.search(r'e_time:\s*([^\n]+)', user_preference).group(1).strip()
#     price_min = re.search(r'price_min:\s*([^\n]+)', user_preference).group(1).strip()
#     price_max = re.search(r'price_max:\s*([^\n]+)', user_preference).group(1).strip()
#     seat = re.search(r'seat:\s*([^\n]+)', user_preference).group(1).strip()
#     d_station = re.search(r'd_station:\s*([^\n]+)', user_preference).group(1).strip()
#     a_station = re.search(r'a_station:\s*([^\n]+)', user_preference).group(1).strip()
#     train_type = re.search(r'type:\s*([^\n]+)', user_preference).group(1).strip()
#
#     dict_list = get_tickets(start_date, departure, destination)
#     print("第一个元素====>", dict_list[0])
#     print("第2个元素====>", dict_list[1])
#
#     rough_screening_tickets = []
#     for ticket in dict_list:
#         # 耗时限制，用户提到时限并且列车的耗时高于用户要求时，舍弃
#         if run_time != "不限" and ticket.get('耗时', '') > run_time:
#             continue
#         # 出发时间偏好
#         if s_time != "不限":
#             depart_time = ticket.get('出发时间', '')
#             if not check_time_limit(depart_time, s_time):
#                 continue
#         # 到达时间偏好
#         if e_time != "不限":
#             arrive_time = ticket.get('到达时间', '')
#             if not check_time_limit(arrive_time, e_time):
#                 continue
#         # 价格区间
#         min_price = 0
#         if price_min != "0" or price_max != "不限":
#             # 获取所有有票且价格不为空的座位价格
#             available_prices = []
#             seat_fields = ["商务座", "一等座", "二等座", "硬座", "硬卧上铺", "硬卧中铺", "硬卧下铺", "无座"]
#             # 只遍历座位字段
#             for seat_name in seat_fields:
#                 seat_status = ticket.get(seat_name, '')
#                 if seat_status and seat_status != "--" and "无票" not in seat_status:
#                     price_match = re.search(r'价格(\d+(?:\.\d+)?)', seat_status)
#                     if price_match:
#                         available_prices.append(float(price_match.group(1)))
#             if available_prices:
#                 min_price = min(available_prices)
#                 if price_min != "0" and min_price < float(price_min):
#                     continue
#                 if price_max != "不限" and min_price > float(price_max):
#                     continue
#             else:
#                 continue  # 没有有效价格
#         ticket['min_price'] = min_price
#         # 座位等级
#         if seat != "不限":
#             seat_status = ticket.get(seat, '')
#             if not seat_status or seat_status == "--" or "无票" in seat_status:
#                 continue
#         # 出发车站
#         if d_station != "不限" and d_station not in ticket.get('出发站', ''):
#             continue
#         # 到达车站
#         if a_station != "不限" and a_station not in ticket.get('到达站', ''):
#             continue
#         # 车的类型
#         if train_type != "不限":
#             train_type_ = ticket.get('类型', '')
#             if train_type == "高铁" and train_type_ != "高铁":
#                 continue
#             if train_type == "普通火车" and train_type_ != "普通列车":
#                 continue
#             if train_type == "动车" and train_type_ != "动车":
#                 continue
#         rough_screening_tickets.append(ticket)
#
#         # 6. 取前5条最优车票，价格越低越好，耗时越短越好
#     if len(rough_screening_tickets) > 5:
#         for ticket in rough_screening_tickets:
#             price = float(ticket.get('min_price', 9999))
#             time_minutes = ticket.get('耗时', '99999分')
#             ticket['总分'] = (2000 - price) / 50 - time_minutes / 10
#         rough_screening_tickets.sort(key=lambda x: x['总分'], reverse=True)
#         final_tickets = rough_screening_tickets[:5]
#     else:
#         final_tickets = rough_screening_tickets
#     print(final_tickets)
#
#
#
# if __name__ == '__main__':
#     user_input_ = "查询后天从北京到天津的车票，要下午两点之前能到，一个人，票价不高于100块钱"
#     current_time_ = '2026-05-07'
#     rough_screening(user_input_, current_time_)
# ============
# """
# 上面的返回值：
# 提取出来的车票要求: start_date: 2026-05-09
# departure: 北京
# destination: 天津
# run_time: 不限
# s_time: 不限
# e_time: 最晚:14点
# price_min: 0
# price_max: 100
# seat: 不限
# d_station: 不限
# a_station: 不限
# type: # 不限
# ============================================
# 正在访问: https://trains.ctrip.com/webapp/train/list?ticketType=0&dStation=%E5%8C%97%E4%BA%AC&aStation=%E5%A4%A9%E6%B4%A5&dDate=2026-05-09&rDate=&trainsType=&hubCityName=&highSpeedOnly=0
# 正在等待数据包返回...
# >>> 成功截获数据包！
# URL: https://m.ctrip.com/restapi/soa2/14666/json/GetBookingByStationV3?_fxpcqlniredt=09031086311652033365&x-traceID=09031086311652033365-1778163195839-6931345
# 共306趟车次信息
# 第一个元素====> {'车次': 'K7731', '类型': '普通列车', '出发站': '北京丰台', '到达站': '天津', '出发时间': '00:22', '到达时间': '02:05', '耗时': 103, '硬座': '票量充足，价格19.5', '硬卧上铺': '仅剩3，价格65.5', '硬卧中铺': '仅剩3，价格70.5', '硬卧下铺': '仅剩3，价格73.5', '软卧上铺': '--', '软卧下铺': '--', '无座': '票量充足，价格19.5'}
# 第2个元素====> {'车次': 'K2601', '类型': '普通列车', '出发站': '北京丰台', '到达站': '天津', '出发时间': '03:55', '到达时间': '05:27', '耗时': 92, '硬座': '票量充足，价格19.5', '硬卧上铺': '票量充足，价格65.5', '硬卧中铺': '票量充足，价格70.5', '硬卧下铺': '票量充足，价格73.5', '软卧上铺': '--', '软卧下铺': '--', '无座': '票量充足，价格19.5'}
# [{'车次': 'C2601', '类型': '高铁', '出发站': '亦庄', '到达站': '武清', '出发时间': '07:26', '到达时间': '07:42', '耗时': 16, '商务座': '仅剩5，价格90.0', '一等座': '票量充足，价格46.0', '二等座': '票量充足，价格27.5', '无座': '--', 'min_price': 27.5, '总分': 37.85}, {'车次': 'C2555', '类型': '高铁', '出发站': '北京南', '到达站': '武清', '出发时间': '06:37', '到达时间': '06:58', '耗时': 21, '商务座': '仅剩3，价格122.0', '一等座': '票量充足，价格62.0', '二等座': '票量充足，价格38.5', '无座': '--', 'min_price': 38.5, '总分': 37.129999999999995}, {'车次': 'C2557', '类型': '高铁', '出发站': '北京南', '到达站': '武清', '出发时间': '06:46', '到达时间': '07:07', '耗时': 21, '商务座': '仅剩3，价格122.0', '一等座': '仅剩4，价格62.0', '二等座': '票量充足，价格38.5', '无座': '--', 'min_price': 38.5, '总分': 37.129999999999995}, {'车次': 'C2559', '类型': '高铁', '出发站': '北京南', '到达站': '武清', '出发时间': '08:01', '到达时间': '08:22', '耗时': 21, '商务座': '仅剩3，价格122.0', '一等座': '仅剩20，价格62.0', '二等座': '票量充足，价格38.5', '无座': '--', 'min_price': 38.5, '总分': 37.129999999999995}, {'车次': 'C2561', '类型': '高铁', '出发站': '北京南', '到达站': '武清', '出发时间': '08:38', '到达时间': '08:59', '耗时': 21, '商务座': '仅剩5，价格122.0', '一等座': '仅剩3，价格62.0', '二等座': '票量充足，价格38.5', '无座': '--', 'min_price': 38.5, '总分': 37.129999999999995}]
#
# """
# ======================================================================
# from DrissionPage import ChromiumOptions, ChromiumPage
# from urllib.parse import quote
# import time
#
# # 配置
# co = ChromiumOptions()
# co.set_browser_path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
# dp = ChromiumPage(addr_or_opts=co)
#
# try:
#     # 1. 准备参数
#     departure = quote('北京')
#     destination = quote('天津')
#     start_date = '2026-05-10'
#
#     # 2. 【关键修正】使用单行字符串构造 URL，确保没有空格和换行
#     url = f"https://trains.ctrip.com/webapp/train/list?ticketType=0&dStation={departure}&aStation={destination}&dDate={start_date}&rDate=&trainsType=&hubCityName=&highSpeedOnly=0"
#
#     # 3. 启动监听
#     dp.listen.start('GetBookingByStationV3')
#
#     # 4. 直接访问构造好的目标页面
#     print(f"正在访问: {url}")
#     dp.get(url)
#
#     dp.ele('text=搜索').click()
#
#     # 5. 等待数据包
#     print("正在等待数据包返回...")
#     # 建议稍微多等一下，携程有时候加载较慢
#     res = dp.listen.wait(timeout=15)
#
#     if res:
#         # res 如果不是 False，它就是一个 DataPacket 对象
#         print(">>> 成功截获数据包！")
#         print(f"URL: {res.url}")
#
#         # 打印响应 JSON（如果确实截获到了数据包）
#         if res.response.body:
#             print("响应数据预览:", str(res.response.body)[:200])  # 预览前200字符
#     else:
#         print("❌ 监听失败：在 15 秒内未发现目标请求包。")
#         # 调试：打印出页面当前拦截到的所有请求名，看看问题出在哪
#         print("当前页面发出的所有请求关键字：")
#         for packet in dp.listen.steps(count=5):  # 查看最近的5个包
#             print(f" - {packet.url}")
#
# finally:
#     # 调试阶段建议不关闭浏览器，方便查看页面状态（是否卡在验证码或登录）
#     # dp.quit()
#     pass