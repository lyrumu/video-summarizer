"""
可插拔的视频平台提取器。
每个平台实现 Fetcher 子类，通过 FetcherRegistry 注册。
"""

# 自动导入所有提取器，触发注册
from . import bilibili
from . import douyin
