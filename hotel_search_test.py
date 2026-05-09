# =======================================================================
# from DrissionPage import ChromiumPage, ChromiumOptions
# import time
#
# co = ChromiumOptions()
# edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
# co.set_browser_path(edge_path)
#
# dp = ChromiumPage(addr_or_opts=co)
#
# start_date = '2025-05-08'
# end_date = '2025-05-09'
# room_num = '1'
# adult_num = '1'
# children_num = '0'
#
# url = (f'https://hotels.ctrip.com/hotels/list'
#        f'?countryId=1&city=3&provinceId=0'
#        f'&checkin={start_date}&checkout={end_date}'
#        f'&optionId=3&optionType=City&directSearch=0'
#        f'&display=%E5%A4%A9%E6%B4%A5&crn={room_num}'
#        f'&adult={adult_num}&children={children_num}&searchBoxArg=t'
#        f'&travelPurpose=0&ctm_ref=ix_sb_dl'
#        f'&domestic=1&&v2_mod=95&v2_version=E')
#
# # 1. 先打开带参数的URL
# dp.get(url)
#
# # 2. 页面加载完后再启动监听
# dp.listen.start('fetchHotelList')
#
# # 3. 修改城市
# dp.ele('#destinationInput').click().input('北京', clear=True)
#
# # 4. 关键：等待下拉建议出现，并点击匹配项
# # 而不是直接点搜索按钮
# dp.wait.ele_displayed('.city-list-item', timeout=5)
# # 或者用更通用的选择器，例如弹窗容器
# # dp.wait.ele_displayed('.autocomplete-dropdown', timeout=5)
#
# # 4. 点击弹窗中完全匹配“北京”的那个选项
# # 尝试用文本定位，点击城市名
# beijing_option = dp.ele('text=北京', timeout=3)
# # 如果 text=北京 匹配不到（可能元素结构特殊），试试 @text():北京
# # beijing_option = dp.ele('@text():北京', timeout=3)
#
# if beijing_option:
#     beijing_option.click()
#     print('已选择北京')
# else:
#     print('未找到北京的选项')
#
# # 5. 点击搜索
# dp.ele('text=搜索').click()
#
# time.sleep(2)
#
# dp.ele('text=欢迎度排序').click()
# dp.ele('text=好评优先').click()
#
#
#
# # 6. 等待数据
# res = dp.listen.wait(timeout=15)
# if res:
#     print('成功！！！！！！！！！')
#     data = res.response.body
#     print(f"{len(data['data']['hotelList'])}")
#     print(str(data)[:300])
# else:
#     # 调试信息
#     print('监听失败，尝试检查实际监听到的请求...')
#     # 可以打印所有监听到的请求名称来调试
#     print('当前监听到的请求:', dp.listen.steps)
# ==============================================================================
# dp.listen.start('fetchHotelList')
# dp.ele('text=欢迎度排序').click()
# dp.ele('text=好评优先').click()
# page = 1
# while True:
#     try:
#         resp = dp.listen.wait(timeout=5)
#         json_data = resp.response.body
#         hotelList = json_data['data']['hotelList']
#         for i in hotelList:
#             dict_data = {
#                 "酒店名称": i['hotelInfo']['nameInfo']['name'],
#                 "价格": i['hotelInfo']['priceInfo']['price'],
#                 "床类型": i['hotelInfo']['bedInfo']['bed'],
#             }
#         page+=1
#         dp.scroll.to_bottom()
#         dp.scroll.to_bottom()
#         if page == 10:
#             print("爬取完毕")
#             break
#
#     except Exception as e:
#         print(e)
#         print('爬取出错')

