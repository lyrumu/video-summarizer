"""
音频下载工具 — 从视频链接中提取音频流。
使用 yt-dlp 下载仅音频，不下载视频画面，节省磁盘和带宽。

流程:
  1. yt-dlp 提取最佳音频流
  2. 下载为 .mp3/.wav
  3. 返回音频文件路径（处理完后调用者负责清理）
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional

import yt_dlp


AUDIO_DIR = Path.home() / ".vidsum" / "audio_cache"


class AudioDownloader:
    """视频音频下载器"""

    def __init__(self, keep_files: bool = False):
        """
        keep_files: 如果为 True，音频文件保留在 AUDIO_DIR 中
                    如果为 False（默认），用完后自动删除
        """
        self.keep_files = keep_files
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    def download(self, url: str, output_format: str = "mp3") -> Optional[str]:
        """
        下载视频的音频流。
        返回音频文件的绝对路径，失败返回 None。
        """
        output_template = str(AUDIO_DIR / "%(id)s.%(ext)s")

        ydl_opts = {
            # 只下载最佳音频流
            "format": "bestaudio/best",
            # 指定 ffmpeg 位置（自动下载缓存）
            "ffmpeg_location": str(Path.home() / ".vidsum" / "bin"),
            # 音频转码
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": output_format,
                "preferredquality": "128",
            }],
            "outtmpl": output_template,
            # 不下载视频缩略图等
            "writethumbnail": False,
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_id = info.get("id", "unknown")
                audio_path = AUDIO_DIR / f"{video_id}.{output_format}"

                if audio_path.exists():
                    return str(audio_path.resolve())

                # yt-dlp 可能添加了其他后缀
                for f in AUDIO_DIR.glob(f"{video_id}.*"):
                    if f.suffix in (".mp3", ".wav", ".m4a", ".ogg"):
                        return str(f.resolve())

                return None

        except Exception as e:
            return None

    def get_video_title(self, url: str) -> str:
        """获取视频标题（不下载）"""
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get("title", "未知标题")
        except Exception:
            return "未知标题"

    def get_video_duration(self, url: str) -> float:
        """获取视频时长（秒，不下载）"""
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get("duration", 0)
        except Exception:
            return 0

    def cleanup(self, audio_path: str):
        """删除临时音频文件"""
        if not self.keep_files and audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass

    def cleanup_all(self):
        """清空所有缓存的音频文件"""
        if AUDIO_DIR.exists():
            shutil.rmtree(str(AUDIO_DIR))
            AUDIO_DIR.mkdir(parents=True, exist_ok=True)
