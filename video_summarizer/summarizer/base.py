"""
LLM 总结层抽象接口。
所有模型（云端/本地）都实现同一个接口，方便切换。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from ..models import SummaryResult


class Summarizer(ABC):
    """总结器基类 — 一个 LLM 就是一个 Summarizer"""

    @abstractmethod
    def summarize(self, text: str, max_length: Optional[str] = None) -> SummaryResult:
        """
        总结文本内容。
        text: 字幕全文
        max_length: 可选的输出长度约束（如"200字"、"3句话"）
        """
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """当前使用的模型名称"""
        ...

    @property
    @abstractmethod
    def cost_per_1k_tokens(self) -> float:
        """每千 token 成本（元），本地模型返回 0"""
        ...


class SummarizerRegistry:
    """总结器注册表"""

    _summarizers: dict[str, type[Summarizer]] = {}

    @classmethod
    def register(cls, name: str, summarizer_class: type[Summarizer]):
        cls._summarizers[name] = summarizer_class

    @classmethod
    def create(cls, name: str, **kwargs) -> Summarizer:
        if name not in cls._summarizers:
            raise ValueError(f"不支持的总结器: {name}，可用: {list(cls._summarizers.keys())}")
        return cls._summarizers[name](**kwargs)

    @classmethod
    def list_summarizers(cls) -> list[str]:
        return list(cls._summarizers.keys())
