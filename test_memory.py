import asyncio
from mcp_project.workflow.graph import Workflow

async def test():
    workflow = Workflow()
    async with workflow:
        session_id = "test_user_001"
        # 第一轮
        res1 = await workflow.run("从天安门到鸟巢的路线", session_id)
        print("第一轮输出:", res1["final_output"])
        # 第二轮：询问“那距离多远？”（需要模型记住上文）
        res2 = await workflow.run("那距离多远？", session_id)
        print("第二轮输出:", res2["final_output"])