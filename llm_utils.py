from langchain_openai import ChatOpenAI

from ..config.settings import settings
from mcp_project.utils.logger import get_logger
from typing import Optional, List
from langchain_core.messages import BaseMessage
logger = get_logger(__name__)

class LLMClient:
    def __init__(self, provider: str="openai", temperature: float = 0.7, max_tokens: Optional[int] = None):
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        if self.provider == "openai":
            self.model = settings.QWEN_MODEL
            self.llm = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL,
            )
            logger.info(f'[模型初始化完成]==>模型为{self.model}')

    def invoke(self, prompt: str):
        try:
            logger.debug(f"[同步调用模型{self.model}...]")
            response = self.llm.invoke(prompt)
            content = response.content
            logger.debug(f"[模型回答完成]==>回答长度为{len(content)}")
            return content

        except Exception as e:
            logger.error(f"[同步调用模型回答失败]==>{e}")
            raise

    async def ainvoke(self, prompt: str):
        try:
            logger.debug(f"[异步调用模型{self.model}...]")
            response = await self.llm.ainvoke(prompt)
            content = response.content
            logger.debug(f"[模型回答完成]==>回答长度为{len(content)}")
            return content

        except Exception as e:
            logger.error(f"[异步调用模型回答失败]==>{e}")
            raise

    def stream(self, messages: List[BaseMessage], **kwargs):
        try:
            logger.debug(f"[流式调用模型{self.model}...]")
            for chunk in self.llm.stream(messages, **kwargs):
                if hasattr(chunk, "content"):
                    yield chunk
        except Exception as e:
            logger.error(f"[流式调用失败]==>{e}")

# ====================================================
# 下面的llm工厂参数可变，
# 我偷懒用了同样的temperature和max-tokens，这样是不对的，要根据实际情况做调整
# ====================================================

class LLMFactory:
    @staticmethod
    def intention_recognize():
        return LLMClient(
            provider="openai",
            temperature=0.3,
            max_tokens=500,
        )
    #
    # @staticmethod
    # def travel_intention_recognize():
    #     return LLMClient(
    #         provider="openai",
    #         temperature=0.5,
    #         max_tokens=30,
    #     )

    @staticmethod
    def c_trip_ticket_search():
        return LLMClient(
            provider="openai",
            temperature=0.1,
            max_tokens=500,
        )

    @staticmethod
    def c_trip_hotel_search():
        return LLMClient(
            provider="openai",
            temperature=0.1,
            max_tokens=500,
        )
    @staticmethod
    def retrieve():
        return LLMClient(
            provider="openai",
            temperature=0.7,
            max_tokens=10,
        )
    @staticmethod
    def chat():
        return LLMClient(
            provider="openai",
            temperature=0.7,
            max_tokens=10,
        )
    @staticmethod
    def review():
        return LLMClient(
            provider="openai",
            temperature=0.7,
            max_tokens=10,
        )

    @staticmethod
    def summary_hotels():
        return LLMClient(
            provider="openai",
            temperature=0.7,
            max_tokens=4000,
        )

    @staticmethod
    def summary_tickets():
        return LLMClient(
            provider="openai",
            temperature=0.7,
            max_tokens=4000,
        )
    @staticmethod
    def rag_agent():
        return LLMClient(
            provider="openai",
            temperature=0.1,
            max_tokens=2000,
            # api_key=settings.QWEN_API_KEY,
            # base_url=settings.QWEN_BASE_URL
        )