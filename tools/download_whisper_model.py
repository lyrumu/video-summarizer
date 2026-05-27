"""
手动下载 Whisper base 模型到缓存目录。
在 Windows 上运行: python download_whisper_model.py
"""
import os, sys
from pathlib import Path

CACHE = Path.home() / ".cache" / "faster-whisper" / "base"
if CACHE.exists():
    print(f"✅ 模型已存在: {CACHE}")
    sys.exit(0)

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from faster_whisper import WhisperModel

print("正在从 hf-mirror.com 下载 Whisper base 模型...")
model = WhisperModel("base", device="cpu", compute_type="int8")
print(f"✅ 下载完成: {CACHE}")
