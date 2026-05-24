#!/usr/bin/env python3
"""
video-summarizer — 视频内容总结工具

用法:
  video-summarizer               # 启动 Web UI（默认）
  video-summarizer --cli         # 启动命令行界面
  video-summarizer --url <链接>   # 单次处理

环境变量:
  BROWSER=0       禁止自动打开浏览器（Headless/SSH 场景）
"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="🎬 Video Summarizer — 视频内容总结工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  video-summarizer                           # 启动 Web UI\n"
            "  video-summarizer --cli                     # 启动命令行界面\n"
            "  video-summarizer --url <链接>              # 单次处理\n"
            "  video-summarizer --url <链接> --model ollama  # 使用本地模型\n"
            "  video-summarizer --port 8888               # 指定端口\n"
            "  BROWSER=0 video-summarizer                 # 不自动打开浏览器\n"
        ),
    )
    parser.add_argument("--cli", action="store_true", help="使用命令行界面")
    parser.add_argument("--web", action="store_true", help="使用 Web 界面（默认）")
    parser.add_argument("--url", type=str, help="视频链接（单次处理模式）")
    parser.add_argument("--model", type=str, default=None, help="指定模型提供商")
    parser.add_argument("--port", type=int, default=None,
                        help="Web 端口（默认自动分配 8000-8020 中可用端口）")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="Web 主机地址（WSL/局域网需要 0.0.0.0）")
    parser.add_argument("--no-browser", action="store_true",
                        help="不自动打开浏览器（也可用环境变量 BROWSER=0）")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="历史记录保存目录（默认 ~/.video-summarizer/history）")

    args = parser.parse_args()

    # 设置保存目录
    if args.output_dir:
        from video_summarizer.config import CONFIG_DIR
        history_dir = Path(args.output_dir).expanduser().resolve()
        history_dir.mkdir(parents=True, exist_ok=True)
        import video_summarizer.config as cfg
        cfg.HISTORY_DIR = history_dir

    # 单次处理模式
    if args.url:
        from video_summarizer.engine import VideoSummarizer
        from video_summarizer.url_utils import is_valid_video_url

        if not is_valid_video_url(args.url):
            print("❌ 不支持的链接，目前支持 B站 和 抖音")
            sys.exit(1)

        engine = VideoSummarizer()
        result = engine.process(args.url, provider=args.model)

        if result.get("error"):
            print(f"❌ {result['error']}")
            sys.exit(1)

        sub = result.get("subtitle", {})
        summary = result.get("summary", {})

        print(f"\n📄 视频: {sub.get('title', '?')}")
        print(f"   时长: {sub.get('duration', 0)}秒")
        print(f"   字幕: {sub.get('source', '?')} ({sub.get('segments_count', 0)}条)")
        print(f"   Token: ~{sub.get('estimated_tokens', 0)}")
        print(f"\n🤖 总结:")
        s = summary.get('summary', '')
        if isinstance(s, str):
            print(s)
        else:
            print(str(s))
        if summary.get('cost_estimate', 0) > 0:
            print(f"\n💰 费用: ¥{summary['cost_estimate']:.4f}")
        return

    # CLI 交互模式
    if args.cli:
        from video_summarizer.cli import main as cli_main
        cli_main()
        return

    # ── Web UI 模式（默认） ──────────────────────────────
    from video_summarizer.startup import (
        print_header,
        print_check,
        print_startup_result,
        check_ffmpeg,
        check_whisper_model,
        find_available_port,
        open_browser,
        should_open_browser,
    )

    print_header()

    # [1/3] 检测 ffmpeg
    ffmpeg_ok, ffmpeg_msg = check_ffmpeg()
    print_check(1, 3, "检测系统依赖", ffmpeg_msg, ok=ffmpeg_ok)

    # [2/3] 检查 Whisper 模型
    whisper_ok, whisper_msg, _ = check_whisper_model()
    print_check(2, 3, "检查 Whisper 模型", whisper_msg, ok=whisper_ok)

    # 选择端口：指定端口 → 自动
    import socket as _socket
    if args.port:
        # 用户指定端口：被占则报错，不 fallback
        port = args.port
        with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as _s:
            try:
                _s.bind((args.host, port))
            except OSError:
                print(f"\n  ❌ 端口 {port} 已被占用，请换一个端口")
                print(f"     尝试: video-summarizer --port <其他端口>")
                print(f"     或:   video-summarizer（让程序自动选端口）")
                print()
                sys.exit(1)
    else:
        port = find_available_port()

    # 禁用浏览器
    if args.no_browser:
        import os
        os.environ["BROWSER"] = "0"

    # 打印启动信息
    print_startup_result(args.host, port)

    # 构造浏览器地址
    if args.host == "127.0.0.1":
        browser_url = f"http://127.0.0.1:{port}"
    else:
        browser_url = f"http://{args.host}:{port}"

    # 后台线程：等端口就绪 → 打开浏览器（不阻塞启动）
    import threading as _threading
    _browser_thread = _threading.Thread(
        target=open_browser,
        args=(args.host, port, browser_url),
        name="browser-opener",
        daemon=True,
    )
    _browser_thread.start()

    # 启动服务
    from video_summarizer.web.app import run
    run(host=args.host, port=port)


if __name__ == "__main__":
    main()
