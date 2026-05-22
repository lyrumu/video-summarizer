"""
B站视频字幕提取器。
通过 B站 API 直接获取 CC 字幕，无需下载视频。

API 流程:
  1. 解析 BV/AV 号
  2. 获取视频元信息（标题、时长、字幕列表）
  3. 下载字幕 JSON → 解析为 SubtitleSegment
"""

import re
import json
import time
from typing import Optional
from urllib.parse import urlparse, parse_qs

import requests

from .base import Fetcher, FetcherRegistry
from ..models import SubtitleResult, SubtitleSegment, SubtitleSource, VideoPlatform


# B站 API 基础地址
API_BASE = "https://api.bilibili.com"

# 请求头 — 模拟浏览器
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
}


class BilibiliFetcher(Fetcher):
    """B站字幕提取器"""

    @classmethod
    def platform(cls) -> VideoPlatform:
        return VideoPlatform.BILIBILI

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """判断是否是 B站 链接"""
        patterns = [
            r"bilibili\.com/video/(BV\w+)",
            r"bilibili\.com/video/av(\d+)",
            r"b23\.tv/\w+",           # 短链接
        ]
        return any(re.search(p, url, re.I) for p in patterns)

    def _extract_bvid(self, url: str) -> Optional[str]:
        """从 URL 中提取 BV 号或 AV 号并转为 BV"""
        # BV 号
        m = re.search(r"bilibili\.com/video/(BV\w+)", url, re.I)
        if m:
            return m.group(1)

        # AV 号 → 需要转 BV
        m = re.search(r"bilibili\.com/video/av(\d+)", url, re.I)
        if m:
            return self._av_to_bv(int(m.group(1)))

        # 短链接 → 重定向解析
        m = re.search(r"b23\.tv/(\w+)", url, re.I)
        if m:
            try:
                resp = requests.head(f"https://b23.tv/{m.group(1)}",
                                     headers=HEADERS, allow_redirects=True, timeout=10)
                return self._extract_bvid(resp.url)
            except Exception:
                return None

        return None

    def _av_to_bv(self, av: int) -> str:
        """AV 号转 BV 号（通过 API 查询）"""
        try:
            resp = requests.get(
                f"{API_BASE}/x/web-interface/view",
                params={"aid": av},
                headers=HEADERS,
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 0:
                return data["data"]["bvid"]
        except Exception:
            pass
        return f"av{av}"

    def get_video_info(self, url: str) -> Optional[dict]:
        """获取视频基本信息"""
        bvid = self._extract_bvid(url)
        if not bvid:
            return None

        try:
            resp = requests.get(
                f"{API_BASE}/x/web-interface/view",
                params={"bvid": bvid},
                headers=HEADERS,
                timeout=10,
            )
            data = resp.json()
            if data.get("code") != 0:
                return None

            info = data["data"]
            return {
                "title": info.get("title", ""),
                "duration": info.get("duration", 0),  # 秒
                "bvid": info.get("bvid", bvid),
                "aid": info.get("aid", 0),
                "desc": info.get("desc", ""),
                "owner": info.get("owner", {}).get("name", ""),
            }
        except Exception as e:
            return None

    def fetch_subtitle(self, url: str) -> SubtitleResult:
        """提取B站字幕"""
        bvid = self._extract_bvid(url)
        if not bvid:
            return SubtitleResult(
                platform=VideoPlatform.BILIBILI,
                source=SubtitleSource.NONE,
                title="",
                duration=0,
                segments=[],
                error=f"无法解析链接: {url}",
                video_url=url,
            )

        # 获取视频信息
        info = self.get_video_info(url)
        if not info:
            return SubtitleResult(
                platform=VideoPlatform.BILIBILI,
                source=SubtitleSource.NONE,
                title="",
                duration=0,
                segments=[],
                error="无法获取视频信息",
                video_url=url,
            )

        title = info["title"]
        duration = info["duration"]
        aid = info["aid"]

        # 获取字幕列表
        try:
            resp = requests.get(
                f"{API_BASE}/x/web-interface/view",
                params={"bvid": bvid},
                headers=HEADERS,
                timeout=10,
            )
            data = resp.json()
        except Exception as e:
            return SubtitleResult(
                platform=VideoPlatform.BILIBILI,
                source=SubtitleSource.NONE,
                title=title,
                duration=duration,
                segments=[],
                error=f"API 请求失败: {e}",
                video_url=url,
            )

        if data.get("code") != 0:
            return SubtitleResult(
                platform=VideoPlatform.BILIBILI,
                source=SubtitleSource.NONE,
                title=title,
                duration=duration,
                segments=[],
                error=f"API 返回错误: {data.get('message', '未知')}",
                video_url=url,
            )

        # 解析字幕
        subtitle_info = data.get("data", {}).get("subtitle", {})
        subtitles = subtitle_info.get("subtitles", [])

        if not subtitles:
            return SubtitleResult(
                platform=VideoPlatform.BILIBILI,
                source=SubtitleSource.NONE,
                title=title,
                duration=duration,
                segments=[],
                error="该视频没有可用字幕",
                video_url=url,
            )

        # 优先选择中文字幕
        selected = None
        for sub in subtitles:
            lang = sub.get("lan_doc", "")
            if "中" in lang or "zh" in sub.get("language", "").lower():
                selected = sub
                break
        if not selected:
            selected = subtitles[0]

        subtitle_url = selected.get("subtitle_url", "")
        if not subtitle_url:
            return SubtitleResult(
                platform=VideoPlatform.BILIBILI,
                source=SubtitleSource.NONE,
                title=title,
                duration=duration,
                segments=[],
                error="字幕 URL 为空",
                video_url=url,
            )

        # B站字幕 URL 可能是相对路径
        if subtitle_url.startswith("//"):
            subtitle_url = "https:" + subtitle_url
        elif subtitle_url.startswith("/"):
            subtitle_url = "https://api.bilibili.com" + subtitle_url

        # 下载字幕 JSON
        try:
            sub_resp = requests.get(subtitle_url, headers=HEADERS, timeout=10)
            sub_data = sub_resp.json()
        except Exception as e:
            return SubtitleResult(
                platform=VideoPlatform.BILIBILI,
                source=SubtitleSource.CC,
                title=title,
                duration=duration,
                segments=[],
                error=f"字幕下载失败: {e}",
                video_url=url,
            )

        # 解析字幕片段
        # B站字幕格式: body = [{"from": 0, "to": 2.5, "content": "..."}, ...]
        segments = []
        for i, item in enumerate(sub_data.get("body", [])):
            segments.append(SubtitleSegment(
                index=i + 1,
                start=item.get("from", 0),
                end=item.get("to", 0),
                text=item.get("content", "").strip(),
            ))

        if not segments:
            return SubtitleResult(
                platform=VideoPlatform.BILIBILI,
                source=SubtitleSource.CC,
                title=title,
                duration=duration,
                segments=[],
                error="字幕内容为空",
                video_url=url,
            )

        return SubtitleResult(
            platform=VideoPlatform.BILIBILI,
            source=SubtitleSource.CC,
            title=title,
            duration=duration,
            segments=segments,
            video_url=url,
        )


# 注册到全局注册表
FetcherRegistry.register(BilibiliFetcher)
