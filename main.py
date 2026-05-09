import asyncio
from pathlib import Path
from mcp_project.utils.logger import get_logger
from mcp_project.workflow.graph import Workflow
import tracemalloc
tracemalloc.start()

logger = get_logger(__name__)
def print_banner():
    """打印欢迎横幅"""
    banner = """
══════════════════════════════════════════════════════════
        多智能体内容生成系统
        基于 LangGraph + FastMCP 构建
══════════════════════════════════════════════════════════
    """
    print(banner)

async def interactive_mode():
    """交互模式"""
    print_banner()
    print("\n💡 提示: 输入 'quit' 或 'exit' 退出程序\n")

    workflow = Workflow()
    async with workflow:
        while True:
            try:
                # 在线程池中运行阻塞的 input()
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: input("\n👤 请输入您的需求: ").strip()
                )

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', '退出']:
                    print("\n👋 再见！")
                    break

                # 异步运行工作流
                result = await workflow.run(user_input)

                # 打印结果
                print_result(result)

            except KeyboardInterrupt:
                print("\n\n程序被中断，再见！")
                break
            except Exception as e:
                logger.error(f"发生错误: {str(e)}")
                print(f"\n错误: {str(e)}")


async def main():
    """主函数"""
    # 确保日志目录存在
    Path("logs").mkdir(exist_ok=True)
    # 异步调用交互模式
    await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())


#
# from fastapi import FastAPI
# from fastapi.responses import StreamingResponse
# from sse_starlette.sse import EventSourceResponse
# from mcp_project.workflow.graph import Workflow
# import asyncio
# import json
#
# app = FastAPI()
# workflow = None
#
# @app.on_event("startup")
# async def startup():
#     global workflow
#     workflow = Workflow()
#     await workflow.__aenter__()
#
# @app.on_event("shutdown")
# async def shutdown():
#     await workflow.__aexit__(None, None, None)
#
# @app.get("/chat/stream")
# async def chat_stream(user_input: str):
#     async def event_generator():
#         # 执行工作流
#         final_state = await workflow.run(user_input)
#         output = final_state["final_output"]
#         # 模拟流式输出：按字输出，每次 yield 一个字符
#         for ch in output:
#             yield {"event": "message", "data": json.dumps({"chunk": ch}, ensure_ascii=False)}
#             await asyncio.sleep(0.02)   # 模拟打字效果
#         yield {"event": "done", "data": ""}
#     return EventSourceResponse(event_generator())
#
# @app.get("/health")
# async def health():
#     return {"status": "ok"}
#
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)