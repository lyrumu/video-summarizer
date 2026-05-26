"""
ffmpeg_downloader — 自动下载、缓存、校验 ffmpeg/ffprobe。

跨平台支持 Windows / macOS / Linux，启动时检测不到系统 ffmpeg 时
自动下载到 ~/.vidsum/bin/ 并加入进程 PATH。

下载源（全部指向最新稳定版）：
  Windows:  gyan.dev (release essentials, .7z)
  macOS:    evermeet.cx (universal binary, .zip)
  Linux:    johnvansickle.com (static builds, .tar.xz)

设计原则：
  - 下载失败不阻塞主程序（ffmpeg 是增强功能）
  - 缓存校验通过后才认为安装完成
  - 临时文件下载完成后再 rename，防半下载损坏
"""

import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

# ── 常量 ──────────────────────────────────────────────────

CACHE_DIR = Path.home() / ".vidsum" / "bin"
VERSION_FILE = CACHE_DIR / "version.json"
DOWNLOAD_TIMEOUT = 120
RETRY_COUNT = 1

# ── 平台探测 ──────────────────────────────────────────────


def _get_download_config() -> Optional[dict]:
    """根据当前操作系统和 CPU 架构返回下载配置。"""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        return {
            "url": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.7z",
            "archive_type": "7z",
            "binary_names": ["ffmpeg.exe", "ffprobe.exe"],
            "archive_prefix": "ffmpeg-release-essentials",
        }

    if system == "darwin":
        return {
            "type": "macos",
            "archive_type": "zip",
            "binary_names": ["ffmpeg", "ffprobe"],
            "urls": {
                "ffmpeg": "https://evermeet.cx/ffmpeg/ffmpeg.zip",
                "ffprobe": "https://evermeet.cx/ffmpeg/ffprobe.zip",
            },
        }

    if system == "linux":
        if machine in ("x86_64", "amd64"):
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        elif machine in ("aarch64", "arm64"):
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"
        else:
            return None
        return {
            "url": url,
            "archive_type": "tar.xz",
            "binary_names": ["ffmpeg", "ffprobe"],
        }

    return None


# ── 路径 API ──────────────────────────────────────────────


def get_cache_dir() -> Path:
    return CACHE_DIR


def get_ffmpeg_path() -> Path:
    return CACHE_DIR / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")


def get_ffprobe_path() -> Path:
    return CACHE_DIR / ("ffprobe.exe" if sys.platform == "win32" else "ffprobe")


def add_to_path():
    """将缓存目录加入当前进程 PATH（不修改用户 shell 配置）。"""
    cache_str = str(CACHE_DIR.resolve())
    parts = os.environ.get("PATH", "").split(os.pathsep)
    if cache_str not in parts:
        os.environ["PATH"] = os.pathsep.join([cache_str] + parts)


# ── 检测 ──────────────────────────────────────────────────


def check_system_ffmpeg() -> tuple[bool, str]:
    """检查系统 PATH 中是否有 ffmpeg。"""
    path = shutil.which("ffmpeg")
    if not path:
        return False, ""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5,
        )
        version = result.stdout.split("\n")[0] if result.stdout else ""
        return True, version
    except Exception:
        return True, path


def check_cached_ffmpeg() -> tuple[bool, str]:
    """检查 ~/.vidsum/bin/ 中是否有可用的 ffmpeg。"""
    ffmpeg = get_ffmpeg_path()
    ffprobe = get_ffprobe_path()
    if not ffmpeg.exists() or not ffprobe.exists():
        return False, ""

    try:
        result = subprocess.run(
            [str(ffmpeg), "-version"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            raise RuntimeError("non-zero exit")
        version = result.stdout.split("\n")[0] if result.stdout else ""
        return True, f"{ffmpeg} ({version})"
    except Exception:
        # 缓存损坏 -> 清理
        ffmpeg.unlink(missing_ok=True)
        ffprobe.unlink(missing_ok=True)
        return False, ""


# ── 下载 ──────────────────────────────────────────────────


def _download_file(url: str, dest: Path, progress_callback: Optional[Callable] = None) -> bool:
    """下载文件到目标路径，支持进度反馈。"""
    import ssl
    import urllib.request

    _report(progress_callback, 0, "正在连接...")

    ctx = ssl.create_default_context()
    tmp = dest.with_suffix(".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1 + RETRY_COUNT):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "vidsum/0.2.0",
            })
            with urllib.request.urlopen(req, context=ctx, timeout=DOWNLOAD_TIMEOUT) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 8192

                with open(tmp, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = min(int(downloaded * 100 / total), 99)
                            _report(progress_callback, pct, f"下载中... ({_fmt_size(downloaded)}/{_fmt_size(total)})")
                        else:
                            _report(progress_callback, None, f"下载中... ({_fmt_size(downloaded)})")

            _report(progress_callback, 100, "下载完成")
            tmp.rename(dest)
            return True

        except Exception as e:
            tmp.unlink(missing_ok=True)
            if attempt < RETRY_COUNT:
                _report(progress_callback, 0, f"下载失败，正在重试... ({e})")
                time.sleep(1)
                continue
            raise

    return False


def _fmt_size(n_bytes: int) -> str:
    """格式化文件大小（如 '12.5MB'）。"""
    mb = n_bytes / (1024 * 1024)
    if mb < 1:
        return f"{n_bytes / 1024:.1f}KB"
    return f"{mb:.1f}MB"


def _report(callback: Optional[Callable], percent: Optional[int], message: str):
    """安全调用进度回调。"""
    if callback:
        try:
            callback(percent, message)
        except Exception:
            pass


# ── 解压 ──────────────────────────────────────────────────


def _extract_windows(archive_path: Path, dest_dir: Path, config: dict) -> bool:
    """从 .7z 中提取 ffmpeg.exe / ffprobe.exe。"""
    import py7zr

    dest_dir.mkdir(parents=True, exist_ok=True)
    prefix = config["archive_prefix"]

    with py7zr.SevenZipFile(archive_path, mode="r") as sz:
        targets = [f"{prefix}/bin/{name}" for name in config["binary_names"]]
        sz.extract(path=dest_dir, targets=targets)

    # 从子目录移到缓存根目录
    for name in config["binary_names"]:
        src = dest_dir / prefix / "bin" / name
        if src.exists():
            shutil.move(str(src), str(dest_dir / name))

    # 清理临时目录
    tmp_sub = dest_dir / prefix
    if tmp_sub.exists():
        shutil.rmtree(str(tmp_sub))

    return True


def _extract_macos_zip(archive_path: Path, dest_dir: Path, binary_name: str) -> bool:
    """从 .zip 中提取单个二进制（macOS evermeet.cx 格式）。"""
    import zipfile

    dest_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename).name
            if name == binary_name:
                zf.extract(info, dest_dir)
                # 可能解压到子目录，移出来
                extracted = dest_dir / info.filename
                final = dest_dir / binary_name
                if extracted != final:
                    if final.exists():
                        final.unlink()
                    shutil.move(str(extracted), str(final))
                return True
    return False


def _extract_linux(archive_path: Path, dest_dir: Path, config: dict) -> bool:
    """从 tar.xz 中提取 ffmpeg / ffprobe。"""
    import tarfile

    dest_dir.mkdir(parents=True, exist_ok=True)

    # 先扫描目录结构
    top_dirs = set()

    with tarfile.open(archive_path, "r:xz") as tf:
        members = tf.getmembers()
        for m in members:
            if "/" in m.name:
                top_dirs.add(m.name.split("/")[0])

        for m in members:
            if m.isfile():
                name = Path(m.name).name
                if name in config["binary_names"]:
                    tf.extract(m, dest_dir)
                    src = dest_dir / m.name
                    dst = dest_dir / name
                    if src != dst:
                        if dst.exists():
                            dst.unlink()
                        shutil.move(str(src), str(dst))

    # 清理残留目录
    for td in top_dirs:
        td_path = dest_dir / td
        if td_path.exists() and td_path.is_dir():
            shutil.rmtree(str(td_path))

    return True


def _set_executable(path: Path):
    """设置可执行权限（Linux/macOS）。"""
    if sys.platform != "win32":
        st = path.stat()
        path.chmod(st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _verify_ffmpeg(ffmpeg_path: Path) -> Optional[str]:
    """校验 ffmpeg 可运行，返回版本字符串。"""
    try:
        result = subprocess.run(
            [str(ffmpeg_path), "-version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.split("\n")[0]
        return None
    except Exception:
        return None


# ── 核心入口 ──────────────────────────────────────────────


def ensure_ffmpeg(progress_callback: Optional[Callable] = None) -> tuple[bool, str]:
    """
    确保 ffmpeg 可用 — 检测 → 缓存 → 自动下载。

    优先级:
      1. 系统 PATH 中的 ffmpeg
      2. ~/.vidsum/bin/ 中的缓存 ffmpeg
      3. 自动下载到 ~/.vidsum/bin/

    progress_callback(percent, message)
      percent: 0-100 或 None（未知大小）, 解压期间为 None

    返回: (是否成功, 描述信息)
    """
    # 1. 系统 PATH
    system_ok, system_msg = check_system_ffmpeg()
    if system_ok:
        return True, system_msg

    # 2. 缓存
    cached_ok, cached_msg = check_cached_ffmpeg()
    if cached_ok:
        add_to_path()
        return True, cached_msg

    # 3. 自动下载
    config = _get_download_config()
    if config is None:
        return False, f"不支持的平台: {platform.system()} {platform.machine()}"

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    binary_names = config["binary_names"]

    try:
        if config["archive_type"] == "7z":
            # Windows
            archive_path = CACHE_DIR / "ffmpeg.7z"
            _download_file(config["url"], archive_path, progress_callback)
            _report(progress_callback, None, "正在解压 (7z)...")
            _extract_windows(archive_path, CACHE_DIR, config)
            archive_path.unlink(missing_ok=True)

        elif config["archive_type"] == "zip":
            # macOS
            urls = config["urls"]
            for binary_name in urls:
                archive_ext = "zip"
                archive_path = CACHE_DIR / f"{binary_name}.{archive_ext}"
                _download_file(urls[binary_name], archive_path, progress_callback)
                _report(progress_callback, None, f"正在解压 {binary_name}...")
                if not _extract_macos_zip(archive_path, CACHE_DIR, binary_name):
                    archive_path.unlink(missing_ok=True)
                    return False, f"从 {binary_name}.zip 中提取失败"
                archive_path.unlink(missing_ok=True)

        elif config["archive_type"] == "tar.xz":
            # Linux
            archive_path = CACHE_DIR / "ffmpeg.tar.xz"
            _download_file(config["url"], archive_path, progress_callback)
            _report(progress_callback, None, "正在解压 (tar.xz)...")
            _extract_linux(archive_path, CACHE_DIR, config)
            archive_path.unlink(missing_ok=True)

        # 设置可执行权限
        for name in binary_names:
            bin_path = CACHE_DIR / name
            if bin_path.exists():
                _set_executable(bin_path)

        # 校验
        ffmpeg_path = get_ffmpeg_path()
        version = _verify_ffmpeg(ffmpeg_path)
        if not version:
            for name in binary_names:
                (CACHE_DIR / name).unlink(missing_ok=True)
            return False, "ffmpeg 校验失败，已清理缓存"

        # 写入元数据
        try:
            VERSION_FILE.write_text(json.dumps({
                "ffmpeg_version": version,
                "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "platform": f"{platform.system()} {platform.machine()}",
            }, indent=2) + "\n")
        except Exception:
            pass

        add_to_path()

        msg = f"{ffmpeg_path} ({version})"
        return True, msg

    except Exception as e:
        # 清理残留
        for name in binary_names:
            (CACHE_DIR / name).unlink(missing_ok=True)
        (CACHE_DIR / "ffmpeg.7z").unlink(missing_ok=True)
        (CACHE_DIR / "ffmpeg.tar.xz").unlink(missing_ok=True)
        (CACHE_DIR / "ffmpeg.zip").unlink(missing_ok=True)
        (CACHE_DIR / "ffprobe.zip").unlink(missing_ok=True)
        return False, f"自动下载失败: {e}"
