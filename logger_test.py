from mcp_project.utils.logger import get_logger
import os

def test_singleton():
    l1 = get_logger("SameName")
    l2 = get_logger("SameName")

    print(f"两个 Logger 是否为同一对象: {l1 is l2}")  # 应该输出 True

    # 观察控制台，每条日志应该只出现一次
    l1.info("测试重复性：如果这行出现了两次，说明测试失败： Handler 重复添加。")

def test_logging():
    # 1. 获取 logger 实例
    log = get_logger("TestModule")

    # 2. 打印不同级别的日志
    log.debug("这条应该是青色的 - 调试细节")
    log.info("这条应该是绿色的 - 运行正常")
    log.warning("这条应该是黄色的 - 潜在问题")
    log.error("这条应该是红色的 - 发生错误")

    # 3. 验证文件是否生成
    from mcp_project.config.settings import settings
    if os.path.exists(settings.LOG_FILE_PATH):
        print(f"\nTest OK! 测试成功！日志文件已生成在: {settings.LOG_FILE_PATH}")
    else:
        print("\nTest Error! 测试失败：未找到日志文件。")

if __name__ == "__main__":
    test_logging()
    test_singleton()
