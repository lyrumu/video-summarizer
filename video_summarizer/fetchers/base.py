"""
Fetcher 抽象基类 — 所有视频平台提取器都要实现这个接口。
新增平台只需新建一个文件，实现 Fetcher，然后注册。
"""

from abc import ABC, abstractmethod
from typing import Optional
from ..models import SubtitleResult, VideoPlatform


class Fetcher(ABC):
    """视频字幕提取器基类"""

    @classmethod
    @abstractmethod
    def platform(cls) -> VideoPlatform:
        """返回对应的平台枚举"""
        ...

    @classmethod
    @abstractmethod
    def can_handle(cls, url: str) -> bool:
        """判断是否能处理该 URL"""
        ...

    @abstractmethod
    def fetch_subtitle(self, url: str) -> SubtitleResult:
        """
        提取视频字幕。
        返回 SubtitleResult，包含字幕片段和视频元信息。
        内部应处理：URL 解析 → 获取字幕 → 解析为 SubtitleSegment 列表。
        """
        ...

    @abstractmethod
    def get_video_info(self, url: str) -> Optional[dict]:
        """获取视频基本信息（标题、时长等），不下载内容"""
        ...


class FetcherRegistry:
    """提取器注册表 — 用来自动发现和路由"""

    _fetchers: dict[VideoPlatform, type[Fetcher]] = {}

    @classmethod
    def register(cls, fetcher_class: type[Fetcher]):
        """注册一个提取器"""
        platform = fetcher_class.platform()
        cls._fetchers[platform] = fetcher_class

    @classmethod
    def resolve(cls, url: str) -> type[Fetcher]:
        """根据 URL 自动匹配对应的提取器"""
        for fetcher_class in cls._fetchers.values():
            if fetcher_class.can_handle(url):
                return fetcher_class
        raise ValueError(f"不支持的链接: {url}")

    @classmethod
    def list_platforms(cls) -> list[str]:
        """列出所有已注册的平台名称"""
        return [p.name for p in cls._fetchers.keys()]

    @classmethod
    def create(cls, url: str) -> Fetcher:
        """根据 URL 创建对应的提取器实例"""
        fetcher_class = cls.resolve(url)
        return fetcher_class()
