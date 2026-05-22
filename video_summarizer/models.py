"""共享数据模型 — 整个项目的核心类型定义"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum, auto
from datetime import datetime


class VideoPlatform(Enum):
    """支持的视频平台"""
    BILIBILI = auto()
    DOUYIN = auto()
    UNKNOWN = auto()


class SubtitleSource(Enum):
    """字幕来源"""
    CC = auto()       # B站 CC 字幕（内置）
    XML = auto()      # B站 XML 字幕
    AI_ASR = auto()   # AI 语音识别生成
    NONE = auto()     # 无字幕


@dataclass
class SubtitleSegment:
    """单条字幕片段"""
    index: int
    start: float           # 开始时间（秒）
    end: float             # 结束时间（秒）
    text: str


@dataclass
class SubtitleResult:
    """字幕提取结果"""
    platform: VideoPlatform
    source: SubtitleSource
    title: str                     # 视频标题
    duration: float                # 视频时长（秒）
    segments: list[SubtitleSegment]
    raw_text: str = ""             # 纯文本（合并后）
    error: Optional[str] = None
    video_url: str = ""

    def __post_init__(self):
        if not self.raw_text:
            self.raw_text = "\n".join(s.text for s in self.segments)


@dataclass
class SummaryResult:
    """总结结果"""
    summary: str
    bullet_points: list[str] = field(default_factory=list)
    key_topics: list[str] = field(default_factory=list)
    model_used: str = ""
    token_count: int = 0
    cost_estimate: float = 0.0       # 预估费用（元）
    error: Optional[str] = None


@dataclass
class VideoInfo:
    """视频基本信息"""
    platform: VideoPlatform
    url: str
    title: str
    duration: float
    has_subtitle: bool = False
    subtitle_source: SubtitleSource = SubtitleSource.NONE
