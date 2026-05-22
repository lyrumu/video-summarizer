"""
视频文本缓存 — 避免重复下载和处理同一视频。
使用 URL 做 key，缓存字幕文本。
"""

import hashlib
import json
from pathlib import Path
from typing import Optional
from .models import SubtitleResult
from .config import CONFIG_DIR


class Cache:
    """简单文件缓存"""

    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir or CONFIG_DIR / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, url: str) -> Optional[SubtitleResult]:
        """从缓存中读取"""
        path = self._path(self._key(url))
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            # 字符串转回枚举
            from .models import VideoPlatform, SubtitleSource
            if isinstance(data.get("platform"), str):
                data["platform"] = VideoPlatform[data["platform"]]
            if isinstance(data.get("source"), str):
                data["source"] = SubtitleSource[data["source"]]
            # segments 的字典也要转回 SubtitleSegment
            if data.get("segments"):
                from .models import SubtitleSegment
                data["segments"] = [SubtitleSegment(**s) for s in data["segments"]]
            return SubtitleResult(**data)
        except Exception:
            return None

    def set(self, url: str, result: SubtitleResult):
        """写入缓存"""
        path = self._path(self._key(url))
        data = {
            "platform": result.platform.name,
            "source": result.source.name,
            "title": result.title,
            "duration": result.duration,
            "segments": [{"index": s.index, "start": s.start, "end": s.end, "text": s.text}
                         for s in result.segments],
            "raw_text": result.raw_text,
            "error": result.error,
            "video_url": result.video_url,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def clear(self):
        """清空缓存"""
        for f in self.cache_dir.glob("*.json"):
            f.unlink()

    def exists(self, url: str) -> bool:
        """检查是否已缓存"""
        return self._path(self._key(url)).exists()
