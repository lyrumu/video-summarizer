"""ASR (语音识别) 抽象接口"""

from abc import ABC, abstractmethod
from typing import Optional
from ..models import SubtitleResult, SubtitleSegment


class ASREngine(ABC):
    """语音识别引擎基类"""

    @abstractmethod
    def transcribe(self, audio_path: str, language: Optional[str] = "zh") -> SubtitleResult:
        """
        将音频文件转写为字幕。
        audio_path: 音频文件路径
        language: 语言代码，默认中文
        返回 SubtitleResult（source=AI_ASR）
        """
        ...

    @abstractmethod
    def supported_formats(self) -> list[str]:
        """支持的音频格式列表"""
        ...


class ASRRegistry:
    """ASR 引擎注册表"""

    _engines: dict[str, type[ASREngine]] = {}

    @classmethod
    def register(cls, name: str, engine_class: type[ASREngine]):
        cls._engines[name] = engine_class

    @classmethod
    def create(cls, name: str = "whisper") -> ASREngine:
        if name not in cls._engines:
            raise ValueError(f"不支持的 ASR 引擎: {name}，可用: {list(cls._engines.keys())}")
        return cls._engines[name]()

    @classmethod
    def list_engines(cls) -> list[str]:
        return list(cls._engines.keys())
