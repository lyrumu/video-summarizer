"""
faster-whisper 语音识别引擎。
支持 CPU 和 GPU，自动检测可用设备。
模型首次运行时会自动下载，后续缓存到 ~/.cache/faster-whisper/。
"""

import os
from pathlib import Path
from typing import Optional

from .base import ASREngine, ASRRegistry
from ..models import SubtitleResult, SubtitleSegment, SubtitleSource, VideoPlatform


class WhisperEngine(ASREngine):
    """faster-whisper 语音识别"""

    # 各模型大小（磁盘占用）
    MODEL_SIZES = {
        "tiny":    "~75MB   (最快，精度最低)",
        "base":    "~142MB  (推荐，平衡速度和精度)",
        "small":   "~466MB",
        "medium":  "~1.5GB  (较慢，精度高)",
        "large":   "~3.1GB  (最慢，精度最高)",
    }

    def __init__(self, model_size: str = "base", device: str = "auto",
                 compute_type: str = "auto"):
        """
        model_size: tiny/base/small/medium/large-v3
        device: auto/cpu/cuda
        compute_type: auto/float16/int8
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _lazy_load(self):
        """延迟加载模型（只在首次调用时下载）"""
        if self._model is not None:
            return

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError(
                "faster-whisper 未安装。请运行: pip install faster-whisper\n"
                "如果安装失败，也可以用 'openai-whisper' 替换。"
            )

        print(f"  ⏳ 正在初始化 Whisper 模型 ({self.model_size})，首次运行可能需要下载")
        print(f"     请耐心等待...\n")

        # 压制 Windows 上 huggingface_hub 的 symlink 警告
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

        # 自动检测设备
        device = self.device
        compute_type = self.compute_type

        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                # torch 未安装（Windows 用户常见），默认 CPU
                device = "cpu"

        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"

        # 尝试加载模型，如果 HuggingFace 被墙则自动回退到国内镜像
        self._model = self._load_model_with_fallback(
            self.model_size, device, compute_type,
        )

    def _load_model_with_fallback(self, model_size: str,
                                   device: str,
                                   compute_type: str) -> "WhisperModel":
        """加载 Whisper 模型，国内用户自动回退到 hf-mirror.com"""
        # 先设环境变量再 import，确保 huggingface_hub 读到正确端点
        for attempt, endpoint in enumerate([None, "https://hf-mirror.com"]):
            if endpoint is not None:
                os.environ["HF_ENDPOINT"] = endpoint
                if attempt == 1:
                    print(f"  ⏳ 默认源下载失败，正在尝试国内镜像 hf-mirror.com...")

            from faster_whisper import WhisperModel

            try:
                return WhisperModel(
                    model_size,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=4,
                    num_workers=2,
                )
            except Exception as e:
                err_str = str(e)
                is_network_error = any(k in err_str for k in [
                    "ConnectTimeout", "ConnectionError", "Timeout",
                    "cannot connect", "WinError 10060",
                ])
                if is_network_error and attempt == 0:
                    # 网络问题 + 还没试过镜像 → 继续重试
                    continue
                # 其他错误或镜像也失败 → 抛出去
                hint = ("\n💡 提示: 如果在中国大陆，可设置 HuggingFace 镜像:\n"
                        "   set HF_ENDPOINT=https://hf-mirror.com\n"
                        "   或重启程序时带上: set HF_ENDPOINT=https://hf-mirror.com && vidsum")
                if is_network_error:
                    raise RuntimeError(f"模型下载失败（网络连接超时）{hint}") from e
                raise

    def supported_formats(self) -> list[str]:
        return [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".wma"]

    def transcribe(self, audio_path: str,
                   language: Optional[str] = "zh") -> SubtitleResult:
        """转写音频为字幕"""
        self._lazy_load()

        path = Path(audio_path)
        if not path.exists():
            return SubtitleResult(
                platform=VideoPlatform.UNKNOWN,
                source=SubtitleSource.AI_ASR,
                title="",
                duration=0,
                segments=[],
                error=f"音频文件不存在: {audio_path}",
            )

        try:
            segments_gen, info = self._model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True,            # 过滤静音段
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    threshold=0.5,
                ),
            )

            segments = []
            for i, seg in enumerate(segments_gen):
                segments.append(SubtitleSegment(
                    index=i + 1,
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                ))

            if not segments:
                return SubtitleResult(
                    platform=VideoPlatform.UNKNOWN,
                    source=SubtitleSource.AI_ASR,
                    title="",
                    duration=info.duration if info else 0,
                    segments=[],
                    error="语音识别未能提取到文本（音频可能无声或语种不匹配）",
                )

            # 检测语言
            detected_lang = info.language if info else language or "zh"

            return SubtitleResult(
                platform=VideoPlatform.UNKNOWN,
                source=SubtitleSource.AI_ASR,
                title="",
                duration=info.duration if info else 0,
                segments=segments,
            )

        except Exception as e:
            return SubtitleResult(
                platform=VideoPlatform.UNKNOWN,
                source=SubtitleSource.AI_ASR,
                title="",
                duration=0,
                segments=[],
                error=f"Whisper 识别失败: {e}",
            )

    @property
    def model_info(self) -> str:
        """返回模型信息"""
        return f"faster-whisper/{self.model_size} ({self.MODEL_SIZES.get(self.model_size, '?')})"


# 注册
ASRRegistry.register("whisper", WhisperEngine)
