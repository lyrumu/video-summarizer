"""
启动检查模块 — 全部启动日志、状态输出、console UX 统一由本模块管理。

原则：
  - 不做全局网络检测（误判太多）
  - Whisper 模型不在此处下载（首次转录时自动触发）
  - 所有启动阶段 print 都在这里，不散落在 main/app 中
"""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional


# ── 工具函数 ──────────────────────────────────────────────


def _is_wsl() -> bool:
    """检测是否在 WSL 环境中"""
    return os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop")


# ── 1. ffmpeg 检测（基础版，含本地路径 + 系统 PATH）────


def check_ffmpeg() -> tuple[bool, str]:
    """
    检测 ffmpeg 是否可用。

    检测顺序（Windows 用户常把 ffmpeg.exe 放项目目录）：
      1. 当前目录 ./ffmpeg.exe (Windows) / ./ffmpeg (Linux/macOS)
      2. ./bin/ffmpeg.exe / ./bin/ffmpeg
      3. 系统 PATH 中的 ffmpeg

    返回: (是否可用, 描述信息)
    """
    candidates = []

    if sys.platform == "win32":
        candidates.append(Path.cwd() / "ffmpeg.exe")
        candidates.append(Path.cwd() / "bin" / "ffmpeg.exe")
    else:
        candidates.append(Path.cwd() / "ffmpeg")
        candidates.append(Path.cwd() / "bin" / "ffmpeg")

    path_ffmpeg = shutil.which("ffmpeg")
    if path_ffmpeg:
        candidates.append(Path(path_ffmpeg))

    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            path_str = str(candidate.resolve())
            try:
                result = subprocess.run(
                    [str(candidate), "-version"],
                    capture_output=True, text=True, timeout=5
                )
                version_line = result.stdout.split("\n")[0] if result.stdout else ""
                return True, f"{path_str}  ({version_line})"
            except Exception:
                return True, path_str

    return False, "未找到 ffmpeg（Whisper 语音识别需要）"


def _download_progress(percent: Optional[int], message: str):
    """ffmpeg 下载进度显示。"""
    if percent is not None and percent < 100:
        # 进度条 20 格，\r 原地刷新
        filled = percent // 5
        bar = "█" * filled + "░" * (20 - filled)
        print(f"\r  ⏳ 正在自动下载 ffmpeg... {bar} {percent}%", end="", flush=True)
    elif percent == 100:
        print(f"\r  ⏳ 正在自动下载 ffmpeg... {'█' * 20} 100%")
    else:
        # 解压/重试等状态，换新行
        print(f"  ⏳ {message}...")


def check_ffmpeg_with_download() -> tuple[bool, str]:
    """
    检测 ffmpeg + 自动下载回退。

    检测顺序:
      1. 当前目录 ./ffmpeg(.exe)
      2. ./bin/ffmpeg(.exe)
      3. 系统 PATH
      4. ~/.vidsum/bin/ffmpeg(.exe)  ← 自动下载缓存
      5. 自动下载到 ~/.vidsum/bin/   ← 全自动

    返回: (是否可用, 描述信息)
    """
    # 1-3: 本地路径 + 系统 PATH
    ok, msg = check_ffmpeg()
    if ok:
        return True, msg

    # 4-5: 缓存 → 自动下载
    from video_summarizer.ffmpeg_downloader import ensure_ffmpeg, check_cached_ffmpeg

    # 先查缓存
    cached_ok, cached_msg = check_cached_ffmpeg()
    if cached_ok:
        return True, cached_msg

    # 自动下载（包含进度显示）
    print(f"\r  ⏳ 未检测到系统 ffmpeg，正在自动下载...", end="", flush=True)
    print()
    download_ok, download_msg = ensure_ffmpeg(progress_callback=_download_progress)
    if download_ok:
        return True, download_msg

    return False, "未找到 ffmpeg，自动下载失败。请手动安装: https://ffmpeg.org/download.html"


# ── 2. Whisper 模型检查（轻量）────────────────────────────


def check_whisper_model(model_size: str = "base") -> tuple[bool, str, int]:
    """
    轻量检查 Whisper 模型状态。

    ⚠️  启动阶段不做深度文件检查：
      - 不同平台缓存路径不同（faster-whisper / huggingface / ctranslate2）
      - 模型名随版本变化
      - 真正的下载与存在检查交由首次转录时处理

    **只检查 faster-whisper 是否可 import**。
    返回: (是否可 import, 描述信息, 模型大小参考 MB)
    """
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False, "faster-whisper 未安装", 0

    model_sizes = {
        "tiny": 75, "base": 142, "small": 466, "medium": 1468, "large-v3": 3149,
    }
    approx = model_sizes.get(model_size, 0)
    size_hint = f"(约 {approx}MB)" if approx else ""

    # 检查是否有模型缓存目录（快速判断是否下载过）
    cache_dir = Path.home() / ".cache" / "faster-whisper"
    if (cache_dir / model_size).exists():
        return True, f"已缓存 {size_hint}", approx
    return False, f"未下载 {size_hint}（首次转录时自动下载）", approx


# ── 3. 自动选端口 ─────────────────────────────────────────


def find_available_port(start: int = 8000, end: int = 8020) -> int:
    """
    找第一个可用端口。

    范围: 8000-8020（符合 Web 服务认知习惯）
    超出范围则让 OS 分配（必能找到一个端口）。
    """
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    # 保底：系统分配
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ── 4. 等端口 + 自动打开浏览器 ──────────────────────────


def wait_for_port(host: str, port: int, timeout: int = 10) -> bool:
    """
    等待端口就绪（确保服务已启动再打开浏览器）。
    每 0.5 秒重试一次，超时返回 False。

    host=0.0.0.0 时实际检测 127.0.0.1（0.0.0.0 是 bind 地址，不可 connect）。
    """
    check_host = "127.0.0.1" if host == "0.0.0.0" else host
    for _ in range(timeout * 2):
        time.sleep(0.5)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.settimeout(1)
                s.connect((check_host, port))
                return True
            except (socket.timeout, ConnectionRefusedError, OSError):
                continue
    return False


def should_open_browser() -> bool:
    """
    是否应该自动打开浏览器。

    环境变量 BROWSER=0 可禁用（Headless/SSH/服务器场景）。
    """
    return os.environ.get("BROWSER", "1") != "0"


def open_browser(host: str, port: int, url: str) -> None:
    """
    自动打开浏览器。

    先等端口就绪（避免页面打不开），再开浏览器。
    WSL → 调 cmd.exe 开 Windows 浏览器
    普通 → webbrowser
    失败 → 只打印警告，不影响服务启动
    """
    if not should_open_browser():
        print_check(3, 3, "打开浏览器", "已跳过 (BROWSER=0)", ok=True)
        return

    # 等端口就绪（最多 10 秒）
    ready = wait_for_port(host, port)
    if not ready:
        print_check(3, 3, "打开浏览器",
                     f"⚠️  服务未就绪，请手动访问 {url}",
                     ok=False)
        return

    opened = False

    if _is_wsl():
        # WSL：优先调 Windows 浏览器
        for cmd in ["cmd.exe", "/mnt/c/Windows/System32/cmd.exe"]:
            if shutil.which(cmd) or Path(cmd).exists():
                try:
                    subprocess.run(
                        [cmd, "/c", "start", url],
                        capture_output=True, timeout=5,
                        shell=(cmd == "cmd.exe")
                    )
                    opened = True
                    break
                except Exception:
                    continue

    if not opened:
        try:
            import webbrowser
            webbrowser.open(url)
            opened = True
        except Exception:
            pass

    if opened:
        print_check(3, 3, "打开浏览器", "✅ 已自动打开", ok=True)
    else:
        print_check(3, 3, "打开浏览器",
                     "⚠️  自动打开失败，请手动访问下方地址",
                     ok=False)


# ── 5. Console UX ────────────────────────────────────────


def print_header():
    """打印启动头部"""
    print()
    print("  🎬 Video Summarizer")
    print()


def print_check(step: int, total: int, label: str, status: str, ok: bool = True):
    """
    打印检查项结果。

    输出格式:
      [1/3] 🔍 检测系统依赖....... ✅ /usr/bin/ffmpeg
      [2/3] 📥 检查 Whisper 模型.. ⚠️  未下载（首次转录时自动下载）
    """
    icon = "✅" if ok else "⚠️ "
    line = f"  [{step}/{total}] {label}"
    padding = max(1, 36 - len(line))
    print(f"{line}{'.' * padding} {icon} {status}")


def print_startup_result(host: str, port: int):
    """打印启动成功信息"""
    print()
    print(f"  ───────────────────────────────")
    print(f"  🎬 Video Summarizer Web UI")
    print(f"  http://{host}:{port}")
    print(f"  ───────────────────────────────")
    print()
    print(f"  按 Ctrl+C 停止服务")
    print()
