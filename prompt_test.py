import datetime
import re

from mcp_project.utils.llm_utils import LLMFactory

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

        # 输出格式：
        start_date: [出发日期]
        departure: [出发地]
        destination: [目的地]
    """
if __name__ == "__main__":
    current_time_ = str(datetime.datetime.now().date())
    u_input="查询明天从北京到天津的车票"
    prompt = extract_ticket_info_prompt(current_time_, u_input)
    llm = LLMFactory.intention_recognize()
    response = llm.invoke(prompt)
    print(response.content)
    departure_date = re.search(r'start_date:\s*(.+)', response.content).group(1)
    print("=====>", departure_date)
    departure = re.search(r'departure:\s*(.+)', response.content).group(1)
    print("=====>", departure)
    destination = re.search(r'destination:\s*(.+)', response.content).group(1)
    print("=====>", destination)