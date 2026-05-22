"""
视频总结主流程 — 协调各个模块。

处理管线:
  视频链接 → 尝试 API 字幕 → 无字幕则 ASR → 预处理 → AI 总结
"""

from typing import Optional

from .models import SubtitleResult, SummaryResult, SubtitleSource, VideoPlatform
from .fetchers.base import FetcherRegistry
from .asr.base import ASRRegistry
from .summarizer.base import SummarizerRegistry
from .preprocessor import TextPreprocessor
from .cache import Cache
from .config import load_config, AppConfig
from .audio import AudioDownloader

# 导入具体实现触发注册表注册
from . import fetchers  # noqa: F401 — 注册 B站/抖音等平台提取器
from . import asr       # noqa: F401 — 注册 Whisper 等 ASR 引擎
from . import summarizer  # noqa: F401 — 注册 DeepSeek/GLM/Qwen/Ollama 等总结器


class VideoSummarizer:
    """
    视频总结引擎 — 完整的处理管线。
    输入链接 → 提取字幕 → 预处理 → AI 总结 → 输出结果。
    """

    def __init__(self, config: AppConfig = None):
        self.config = config or load_config()
        self.cache = Cache(self.config.cache_dir) if self.config.cache_enabled else None
        self.audio = AudioDownloader(keep_files=False)
        self._asr_engine = None

    @property
    def asr(self):
        """延迟加载 ASR 引擎"""
        if self._asr_engine is None:
            self._asr_engine = ASRRegistry.create("whisper")
        return self._asr_engine

    def process(self, url: str, use_cache: bool = True,
                provider: str = None, model: str = None,
                max_length: str = None) -> dict:
        """
        处理一个视频链接，返回完整结果。
        """
        result = {
            "url": url,
            "platform": self._detect_platform_name(url),
            "subtitle": None,
            "summary": None,
            "error": None,
        }

        # Step 1: 获取字幕（API 优先，无字幕则 ASR 兜底）
        subtitle = self._get_subtitle(url, use_cache)
        result["subtitle"] = {
            "title": subtitle.title,
            "duration": subtitle.duration,
            "source": subtitle.source.name,
            "segments_count": len(subtitle.segments),
            "text_length": len(subtitle.raw_text),
            "estimated_tokens": TextPreprocessor.estimate_tokens(subtitle.raw_text),
            "error": subtitle.error,
        }

        if subtitle.error:
            result["error"] = subtitle.error
            return result

        if not subtitle.segments:
            result["error"] = "未能提取到任何字幕内容"
            return result

        # Step 2: 预处理文本
        cleaned_text = TextPreprocessor.clean(subtitle.raw_text)
        if not cleaned_text.strip():
            result["error"] = "预处理后文本为空"
            return result

        # Step 3: AI 总结
        summary = self._summarize(cleaned_text, provider, model, max_length)
        result["summary"] = summary

        return result

    def _get_subtitle(self, url: str, use_cache: bool = True) -> SubtitleResult:
        """获取字幕 — API 优先 → ASR 兜底，带缓存"""
        # 尝试从缓存读取
        if use_cache and self.cache and self.cache.exists(url):
            cached = self.cache.get(url)
            if cached and cached.segments:
                return cached

        # Step 1: 尝试通过平台 API 提取字幕
        subtitle = self._fetch_via_api(url)

        # Step 2: 如果 API 没有字幕 → ASR 兜底
        if not subtitle.segments or subtitle.source == SubtitleSource.NONE:
            asr_result = self._fetch_via_asr(url)
            if asr_result and asr_result.segments:
                # 保留 API 获取到的标题信息
                if subtitle.title:
                    asr_result.title = subtitle.title
                subtitle = asr_result

        # 写入缓存
        if use_cache and self.cache and subtitle.segments:
            self.cache.set(url, subtitle)

        return subtitle

    def _fetch_via_api(self, url: str) -> SubtitleResult:
        """通过平台 API 提取字幕"""
        try:
            fetcher = FetcherRegistry.create(url)
            return fetcher.fetch_subtitle(url)
        except ValueError as e:
            return SubtitleResult(
                platform=self._detect_platform(url),
                source=SubtitleSource.NONE,
                title="",
                duration=0,
                segments=[],
                error=str(e),
                video_url=url,
            )

    def _fetch_via_asr(self, url: str) -> Optional[SubtitleResult]:
        """通过语音识别获取字幕（下载音频 → ASR）"""
        try:
            # 先获取视频标题（用于返回）
            title = self.audio.get_video_title(url)
            duration = self.audio.get_video_duration(url)

            # 下载音频
            audio_path = self.audio.download(url)
            if not audio_path:
                return SubtitleResult(
                    platform=self._detect_platform(url),
                    source=SubtitleSource.AI_ASR,
                    title=title,
                    duration=duration,
                    segments=[],
                    error="音频下载失败",
                    video_url=url,
                )

            # 语音识别
            result = self.asr.transcribe(audio_path)

            # 补充元信息
            result.title = title
            if not result.duration:
                result.duration = duration
            result.video_url = url

            # 清理音频文件
            self.audio.cleanup(audio_path)

            return result

        except Exception as e:
            return SubtitleResult(
                platform=self._detect_platform(url),
                source=SubtitleSource.AI_ASR,
                title="",
                duration=0,
                segments=[],
                error=f"语音识别失败: {e}",
                video_url=url,
            )

    def _summarize(self, text: str, provider: str = None,
                   model: str = None, max_length: str = None) -> SummaryResult:
        """调用 LLM 总结（每次都新建配置，不修改引擎默认值）"""
        import copy
        cfg = copy.deepcopy(self.config.llm)
        if provider:
            cfg.provider = provider
        if model:
            cfg.model = model

        try:
            summarizer = SummarizerRegistry.create(cfg.provider, config=cfg)
            return summarizer.summarize(text, max_length)
        except (ValueError, Exception) as e:
            return SummaryResult(
                summary="",
                error=f"总结失败: {e}",
            )

    @staticmethod
    def _detect_platform(url: str) -> VideoPlatform:
        """检测平台"""
        try:
            return FetcherRegistry.resolve(url).platform()
        except ValueError:
            return VideoPlatform.UNKNOWN

    @staticmethod
    def _detect_platform_name(url: str) -> str:
        return VideoSummarizer._detect_platform(url).name
