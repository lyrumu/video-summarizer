"""
抖音视频信息提取器。
抖音没有公开的字幕 API，所以只提取元信息（标题、时长），
实际的语音识别由编排层调用 ASR 引擎完成。

注意：
- 支持标准链接: https://www.douyin.com/video/764106...
- 支持精选页: https://www.douyin.com/jingxuan?modal_id=764106...
  自动提取 modal_id 转为标准链接格式
- 部分抖音视频需要登录才能访问，用户会看到详细的操作指引
"""

import re
from typing import Optional
from urllib.parse import urlparse, parse_qs

import yt_dlp

from .base import Fetcher, FetcherRegistry
from ..models import SubtitleResult, SubtitleSegment, SubtitleSource, VideoPlatform


class DouyinFetcher(Fetcher):
    """抖音提取器 — 只提取视频元信息，字幕由 ASR 提供"""

    @classmethod
    def platform(cls) -> VideoPlatform:
        return VideoPlatform.DOUYIN

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """判断是否是抖音链接"""
        patterns = [
            r"douyin\.com",
            r"iesdouyin\.com",
            r"v\.douyin\.com",
            r"t\.\w+/",               # 抖音短链接
        ]
        return any(re.search(p, url, re.I) for p in patterns)

    @classmethod
    def _normalize_url(cls, url: str) -> str:
        """
        将各种抖音链接格式统一为标准 video/ID 格式。
        - jingxuan?modal_id=XXX → /video/XXX
        - 其他格式保持原样
        """
        parsed = urlparse(url)
        if "jingxuan" in parsed.path:
            params = parse_qs(parsed.query)
            modal_id = params.get("modal_id", [None])[0]
            if modal_id:
                return f"https://www.douyin.com/video/{modal_id}"
        return url

    def get_video_info(self, url: str) -> Optional[dict]:
        """获取视频基本信息（不下载）"""
        url = self._normalize_url(url)
        try:
            with yt_dlp.YoutubeDL({
                "quiet": True,
                "no_warnings": True,
            }) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "title": info.get("title", "未知标题"),
                    "duration": info.get("duration", 0),
                    "uploader": info.get("uploader", ""),
                    "description": info.get("description", ""),
                }
        except Exception as e:
            err_str = str(e)
            if "cookies" in err_str.lower() or "Fresh cookies" in err_str:
                return {"error": "需要 cookies", "detail": err_str}
            return None

    def fetch_subtitle(self, url: str) -> SubtitleResult:
        """
        抖音不支持直接获取字幕。
        返回带视频元信息的空结果，由编排层触发 ASR。
        """
        url = self._normalize_url(url)
        info = self.get_video_info(url)

        if info is None:
            return SubtitleResult(
                platform=VideoPlatform.DOUYIN,
                source=SubtitleSource.NONE,
                title="",
                duration=0,
                segments=[],
                error="无法获取该抖音视频信息。常见原因和解决方法：\n\n"
                      "① 链接不对 → 在抖音 App 打开视频 → 点「分享」→「复制链接」→ 把新链接粘贴过来\n"
                      "② 视频需要登录才能看 → 按下面的步骤操作\n"
                      "③ 视频已删除或被屏蔽 → 试试其他视频\n\n"
                      "如果链接是对的，用电脑浏览器打开 douyin.com → 扫码登录 → "
                      "找到这个视频 → 复制地址栏网址 → 重新粘贴进来。",
                video_url=url,
            )

        if info.get("error") == "需要 cookies":
            return SubtitleResult(
                platform=VideoPlatform.DOUYIN,
                source=SubtitleSource.NONE,
                title="",
                duration=0,
                segments=[],
                error="抖音视频需要登录才能查看。请按以下步骤操作：\n\n"
                      "第一步：在电脑上用 Chrome 浏览器打开 douyin.com\n"
                      "第二步：点右上角「扫码登录」，用抖音 App 扫一下\n"
                      "第三步：登录后，搜索或找到你想总结的那个视频并打开\n"
                      "第四步：复制浏览器地址栏的完整链接（以 https://www.douyin.com/video/ 开头）\n"
                      "第五步：把新链接粘贴到这里重新提交\n\n"
                      "如果还是不行，先把视频保存到手机相册，告诉我文件名，我试试用其他方式处理。",
                video_url=url,
            )

        return SubtitleResult(
            platform=VideoPlatform.DOUYIN,
            source=SubtitleSource.NONE,
            title=info["title"],
            duration=info["duration"],
            segments=[],
            error="抖音无公开字幕，需要语音识别",
            video_url=url,
        )


# 注册
FetcherRegistry.register(DouyinFetcher)
