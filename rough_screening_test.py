# # 酒店粗筛测试
#
# from DrissionPage import ChromiumOptions
# from DrissionPage import ChromiumPage
# import time
# import re
# from mcp_project.utils.llm_utils import LLMFactory
#
# llm = LLMFactory.intention_recognize()
#
#
# def get_hotels(start_date, end_date, destination: str, room_num: str, adult_num, children_num):
#     co = ChromiumOptions()
#     co.set_browser_path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
#     dp = ChromiumPage(addr_or_opts=co)
#     try:
#         # 1.由于日期真的很难根据元素去找，所以构造url直接填好
#         url = (f'https://hotels.ctrip.com/hotels/list'
#                f'?countryId=1&city=3&provinceId=0'
#                f'&checkin={start_date}&checkout={end_date}'
#                f'&optionId=3&optionType=City&directSearch=0'
#                f'&display=%E5%A4%A9%E6%B4%A5&crn={room_num}'
#                f'&adult={adult_num}&children={children_num}&searchBoxArg=t'
#                f'&travelPurpose=0&ctm_ref=ix_sb_dl'
#                f'&domestic=1&&v2_mod=95&v2_version=E')
#         # 2.打开网页
#         dp.get(url)
#         # 3.启动监听
#         dp.listen.start('fetchHotelList')
#         # 4.清除原本城市，重新输入所需要的城市
#         dp.ele('#destinationInput').click().input(destination, clear=True)
#         dp.wait.ele_displayed('.city-list-item', timeout=5)
#         dp.ele(f'text={destination}', timeout=3).click()
#         # 5.点击“搜索”，刷新一下页面
#         dp.ele('text=搜索').click()
#         time.sleep(2)
#         # 6.选择“好评优先”，才会出现‘fetchHotelList’这个请求头
#         dp.ele('text=欢迎度排序').click()
#         dp.ele('text=好评优先').click()
#         # 7.循环以获取更多数据
#         page = 1
#         results = []
#         while True:
#             print(f'正在抓取第{page}页...')
#
#             res = dp.listen.wait(timeout=15)
#             if res:
#                 data = res.response.body
#                 hotels = data['data']['hotelList']
#
#                 for i in hotels:
#                     first_room = i.get('roomInfo', [])[0]
#                     advantage_tags = first_room.get('roomTags', {}).get('advantageTags', [])
#                     dict_data = {
#                         '酒店名称': i.get('hotelInfo', {}).get('nameInfo', {}).get('name', ''),
#                         "星级": i.get('hotelInfo', {}).get('hotelStar', {}).get('star', ''),
#                         # "hotelStar": {"star": 5...返回值为int
#                         "评分": i.get('hotelInfo', {}).get('commentInfo', {}).get('commentScore', ''),
#                         "酒店地址": i.get('hotelInfo', {}).get('positionInfo', {}).get('address', ''),
#                         # 注意：这里面有纬度，是不是可以结合百度地图查纬度？
#                         "临近资源": i.get('hotelInfo', {}).get('positionInfo', {}).get('positionDesc', ''),
#                         "房型": first_room.get('summary', {}).get('saleRoomName', ''),
#                         "价格": first_room.get('priceInfo', {}).get('price', ''),
#                         "床型": first_room.get('bedInfo', {}).get('contentList', []),
#                         "优势": advantage_tags[0].get('tagTitle', '') if advantage_tags else '',
#                     }
#                     results.append(dict_data)
#                 page += 1
#                 dp.scroll.to_bottom()
#                 dp.scroll.to_bottom()
#                 if page > 5:
#                     print('[执行工具完成]==>酒店搜索完成')
#                     break
#             else:
#                 print('监听失败')
#                 break
#         return results
#     except Exception as e:
#         print(e)
#         return []
#
#
# def rough_screening(user_input, current_time):
#     user_prompt = f"""
#         你是一个高效率的旅游行程解析助手。你的任务是从用户的非结构化输入中提取关键的酒店预订信息。
#         当前日期：{current_time}
#         用户输入：{user_input}
#
#         # 要求：
#         请分析用户的输入，推断并提取以下字段：
#         1. 入住日期 (check_in): 格式为 YYYY-MM-DD。
#         2. 退房日期 (check_out): 格式为 YYYY-MM-DD。
#         3. 城市 (city): 酒店所在的城市。
#         4. 酒店级别 (star_rating): 用户要求的星级或档次，若未提及，默认为“不限”。
#         5. 房间数 (room_num): 用户提到的房间数，默认为1。
#         6. 成人数 (adults): 用户提到的人数，默认为1。
#         7. 儿童数 (children): 默认为 0。
#         8. 特殊要求(breakfast): 用户要求含早餐填"是"，若未提及，默认为“不限”。
#         9. 评分下限 (score_min): 用户提到的酒店的最低评分，若未提及，默认为“不限”。
#         10. 价格下限 (price_min): 默认0
#         11. 价格上限(price_max): 用户提到的最高价格，若未提及，默认为“不限”。
#
#         # 输出格式：
#         start_date: [入住日期]
#         end_date: [退房日期]
#         city: [城市]
#         star_rating: [星级]
#         room_num: [房间数量]
#         adults: [成人数]
#         children: [儿童数]
#         breakfast: [是/不限]
#         score_min: [数字/不限]
#         price_min: [数字]
#         price_max: [数字/不限]
#     """
#     user_preference = llm.invoke(prompt=user_prompt).content
#     print("提取出来的酒店要求:", user_preference)
#     print("===========================================")
#     start_date = re.search(r'start_date:\s*([^\n]+)', user_preference).group(1).strip()
#     print("正则提取的日期1：", start_date)
#     end_date = re.search(r'end_date:\s*([^\n]+)', user_preference).group(1).strip()
#     print("end_date:", end_date)
#     departure = re.search(r'city:\s*([^\n]+)', user_preference).group(1).strip()
#     room_num = re.search(r'room_num:\s*([^\n]+)', user_preference).group(1).strip()
#     adults = re.search(r'adults:\s*([^\n]+)', user_preference).group(1).strip()
#     children = re.search(r'children:\s*([^\n]+)', user_preference).group(1).strip()
#
#     star_rating = re.search(r'star_rating:\s*([^\n]+)', user_preference).group(1).strip()
#     score_min = re.search(r'score_min:\s*([^\n]+)', user_preference).group(1).strip()
#     price_max = re.search(r'price_max:\s*([^\n]+)', user_preference).group(1).strip()
#     breakfast = re.search(r'breakfast:\s*([^\n]+)', user_preference).group(1).strip()
#
#     dict_list = get_hotels(start_date, end_date, departure, room_num, adults, children)
#     print("第一个元素===>", dict_list[0])
#     print("第2个元素===>", dict_list[1])
#
#     rough_screening_hotels = []
#     for i in dict_list:
#         # 如果用户提到星级但是酒店的星级不是用户所要求的，跳过不保留
#         if star_rating != "不限" and i.get('星级', '') != star_rating:
#             continue
#         # 用户提到最低评分但是酒店评分小于这个最低评分的，淘汰
#         if score_min != '不限' and i.get('评分', '') < score_min:
#             continue
#         if price_max != "不限" and float(i.get('价格', 0)) > float(price_max):
#             continue
#         if breakfast == "是" and "包早餐" not in i.get('优势', ''):
#             continue
#         rough_screening_hotels.append(i)
#     # 7.保留最符合条件的10个酒店信息，如果用户要求不够详细，就计算酒店平均分，获得前20个价格合理、评分高、星级高的酒店
#     if len(rough_screening_hotels) > 10:
#         for hotel in rough_screening_hotels:
#             score = float(hotel.get('评分', 0))
#             price = float(hotel.get('价格', 9999))
#             star = float(hotel.get('星级', 0))
#             hotel['总分'] = score * 10 + (2000 - price) / 100 + star * 5
#         rough_screening_hotels.sort(key=lambda x: x['总分'], reverse=True)
#         final_hotels = rough_screening_hotels[:10]
#     else:
#         final_hotels = rough_screening_hotels
#
#     print(final_hotels)
#
#
# if __name__ == '__main__':
#     user_input = "查询天津的酒店，一个成年人住，5月10号到5月12日，需要早餐，评分要在4.8以上，价格不高于500块钱一晚"
#     current_time = '2026-05-07'
#     rough_screening(user_input, current_time)
#
# """
# 打印台内容：
# 提取出来的酒店要求: start_date: 2026-05-10
# end_date: 2026-05-12
# city: 天津
# star_rating: 不限
# room_num: 1
# adults: 1
# children: 0
# breakfast: 是
# score_min: 4.8
# price_min: 0
# price_max: 500
# ===========================================
# 正则提取的日期1： 2026-05-10
# end_date: 2026-05-12
# 正在抓取第1页...
# 正在抓取第2页...
# 正在抓取第3页...
# 正在抓取第4页...
# 正在抓取第5页...
# [执行工具完成]==>酒店搜索完成
# 第一个元素===> {'酒店名称': '麗枫酒店(天津小白楼地铁站五大道文化旅游区店)', '星级': 3, '评分': '4.8', '酒店地址': '解放北路168号', '临近资源': '近五大道 · 滨江道商圈', '房型': '雅致大床房（智能客控+手机投屏）', '价格': 236, '床型': ['1张1.8米大床'], '优势': '免费取消'}
# 第2个元素===> {'酒店名称': '天津海河悦榕庄', '星级': 5, '评分': '4.8', '酒店地址': '海河东路34号', '临近资源': '近天津之眼摩天轮 · 天津古文化街旅游区', '房型': '至尊家庭客房丨超大圆形浴缸', '价格': 818, '床型': ['1张特大床 及 1张单人床'], '优势': '免费取消'}
# [{'酒店名称': '天津站希尔顿欢朋酒店', '星级': 4, '评分': '4.8', '酒店地址': '光复道街道海河东路78号茂业大厦1层', '临近资源': '近天津站 · 津湾广场', '房型': '高级大床房', '价格': 469, '床型': ['1张1.8米大床'], '优势': '包早餐'}, {'酒店名称': '天津河东希尔顿欢朋酒店', '星级': 4, '评分': '4.8', '酒店地址': '津滨大道63号', '临近资源': '近天津河东万达广场 · 泰昌路地铁站', '房型': '舒适大床房（舒达床垫+智能投屏电视+智能客控）', '价格': 413, '床型': ['1张1.8米大床'], '优势': '包早餐'}, {'酒店名称': '天津生态城希尔顿欢朋酒店', '星级': 4, '评分': '4.8', '酒店地址': '生态城安正路666号', '临近资源': '近中新生态城地铁站 · 国家海洋博物馆', '房型': '舒适大床房', '价格': 337, '床型': ['1张1.8米大床'], '优势': '包早餐'}, {'酒店名称': '天津北辰希尔顿欢朋酒店', '星级': 4, '评分': '4.8', '酒店地址': '辰昌路1260号', '临近资源': '刘园商圈 · 近瑞景新苑地铁站', '房型': '舒适双床房', '价格': 389, '床型': ['2张1.2米单人床'], '优势': '包早餐'}, {'酒店名称': '天津奥体中心解放南路希尔顿欢朋酒店', '星级': 4, '评分': '4.8', '酒店地址': '解放南路447号', '临近资源': '近土城地铁站 · 九号温泉生活馆', '房型': '舒适大床房（舒达床垫+投屏+彼得罗夫洗沐）', '价格': 339, '床型': ['1张1.8米大床'], '优势': '包早餐'}, {'酒店名称': '天津武清希尔顿欢朋酒店', '星级': 4, '评分': '4.8', '酒店地址': '开发区创业总部基地B42号楼', '临近资源': '近天津武清福源万达广场 · 麒麟商业中心', '房型': '舒适大床房', '价格': 404, '床型': ['1张1.8米大床'], '优势': '包早餐'}]
#
# 进程已结束，退出代码为 0
#
# """