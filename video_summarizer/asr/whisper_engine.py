"""
faster-whisper 语音识别引擎。
支持 CPU 和 GPU，自动检测可用设备。
模型首次运行时会自动下载（~1-2GB），后续缓存到 ~/.cache/whisper/。
"""

from pathlib import Path
from typing import Optional

from .base import ASREngine, ASRRegistry
from ..models import SubtitleResult, SubtitleSegment, SubtitleSource, VideoPlatform


class WhisperEngine(ASREngine):
    """faster-whisper 语音识别"""

    # 各模型大小（磁盘占用）
    MODEL_SIZES = {
        "tiny":    "~150MB  (最快，精度最低)",
        "base":    "~300MB",
        "small":   "~500MB  (推荐，平衡速度和精度)",
        "medium":  "~1.5GB  (较慢，精度高)",
        "large":   "~3GB    (最慢，精度最高)",
    }

    def __init__(self, model_size: str = "small", device: str = "auto",
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

        # 自动检测设备
        device = self.device
        compute_type = self.compute_type

        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"

        self._model = WhisperModel(
            self.model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=4,
            num_workers=2,
        )

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
