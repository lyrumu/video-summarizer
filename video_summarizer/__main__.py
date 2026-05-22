#!/usr/bin/env python3
"""
video-summarizer — 视频内容总结工具

用法:
  video-summarizer               # 启动 Web UI（默认）
  video-summarizer --cli         # 启动命令行界面
  video-summarizer --url <链接>   # 单次处理
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
            "  video-summarizer --output-dir ~/Desktop/summaries  # 指定保存目录\n"
        ),
    )
    parser.add_argument("--cli", action="store_true", help="使用命令行界面")
    parser.add_argument("--web", action="store_true", help="使用 Web 界面（默认）")
    parser.add_argument("--url", type=str, help="视频链接（单次处理模式）")
    parser.add_argument("--model", type=str, default=None, help="指定模型提供商")
    parser.add_argument("--port", type=int, default=8020, help="Web 端口（默认 8020）")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Web 主机地址（Windows 访问需要设 0.0.0.0）")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="历史记录保存目录（默认 ~/.video-summarizer/history）")

    args = parser.parse_args()

    # 设置保存目录
    if args.output_dir:
        from video_summarizer.config import CONFIG_DIR
        history_dir = Path(args.output_dir).expanduser().resolve()
        history_dir.mkdir(parents=True, exist_ok=True)
        # 覆写全局配置中的 history_dir
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
        print(f"\n🤖 总结 ({summary.model_used if hasattr(summary, 'model_used') else '?'}):")
        if hasattr(summary, 'summary'):
            print(summary.summary)
            if hasattr(summary, 'cost_estimate') and summary.cost_estimate > 0:
                print(f"\n💰 费用: ¥{summary.cost_estimate:.4f}")
        else:
            print(summary.get('summary', ''))
        return

    # CLI 模式
    if args.cli:
        from video_summarizer.cli import main as cli_main
        cli_main()
        return

    # Web UI 模式（默认）
    from video_summarizer.web.app import run
    print("🚀 启动 Web UI...")
    run(host=args.host, port=args.port, no_browser=args.no_browser)


if __name__ == "__main__":
    main()
