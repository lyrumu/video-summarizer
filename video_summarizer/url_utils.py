"""
URL 平台检测工具函数
"""

import re
from .models import VideoPlatform
from .fetchers.base import FetcherRegistry


def detect_platform(url: str) -> VideoPlatform:
    """检测 URL 对应的视频平台"""
    try:
        fetcher_class = FetcherRegistry.resolve(url)
        return fetcher_class.platform()
    except ValueError:
        return VideoPlatform.UNKNOWN


def is_valid_video_url(url: str) -> bool:
    """判断是否是一个支持的视频链接"""
    return detect_platform(url) != VideoPlatform.UNKNOWN


def extract_urls(text: str) -> list[str]:
    """从文本中提取所有链接"""
    pattern = r"https?://[^\s,，。；;'\"<>()（）【】\[\]{}]+"
    return re.findall(pattern, text)
