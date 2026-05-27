#!/usr/bin/env python3
"""
CLI 入口 — 命令行交互界面。
先用 Rich 做终端界面，后期替换为 Web UI。
"""

import sys
from pathlib import Path

# 确保 `src` 在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent))

import rich
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

from video_summarizer.engine import VideoSummarizer
from video_summarizer.url_utils import is_valid_video_url, extract_urls
from video_summarizer.config import load_config, save_config, AppConfig, LLMConfig


console = Console()


def show_banner():
    """显示启动横幅"""
    console.print(Panel.fit(
        "[bold cyan]🎬 视频内容总结工具[/bold cyan]\n"
        "[dim]支持 B站 / 抖音 · DeepSeek / GLM / Qwen / Ollama[/dim]",
        border_style="cyan",
    ))


def input_url() -> str:
    """让用户输入视频链接"""
    while True:
        url = Prompt.ask("[bold]输入视频链接[/bold]（输入 q 退出）")
        if url.lower() in ("q", "quit", "exit"):
            return None
        url = url.strip()
        if is_valid_video_url(url):
            return url
        console.print("[red]❌ 暂不支持该链接，目前仅支持 B站 和 抖音[/red]")


def select_llm() -> str:
    """选择 LLM 提供商"""
    options = {
        "1": ("deepseek", "DeepSeek API"),
        "2": ("glm", "GLM API（智谱）"),
        "3": ("qwen", "Qwen API（通义千问）"),
        "4": ("ollama", "Ollama 本地模型（免费）"),
    }

    table = Table(title="选择 AI 模型")
    table.add_column("编号", style="cyan")
    table.add_column("提供商", style="green")
    table.add_column("说明")
    for k, (_, desc) in options.items():
        table.add_row(k, desc.split("（")[0], f"（{desc.split('（')[1]}" if "（" in desc else "")

    console.print(table)

    while True:
        choice = Prompt.ask("[bold]请选择[/bold]", choices=list(options.keys()), default="4")
        provider = options[choice][0]
        if provider != "ollama":
            api_key = Prompt.ask(
                f"[bold]输入 {provider} API Key[/bold]",
                password=True,
            )
            # 保存到配置
            config = load_config()
            config.llm.provider = provider
            config.llm.api_key = api_key
            save_config(config)
            console.print("[green]✅ API Key 已保存到 ~/.vidsum/config.json[/green]")
        return provider


def show_result(platform: str, summary: dict, subtitle: dict):
    """显示处理结果"""
    # 视频信息
    console.print(Panel.fit(
        f"[bold]平台:[/bold] {platform}\n"
        f"[bold]标题:[/bold] {subtitle.get('title', '未知')}\n"
        f"[bold]时长:[/bold] {subtitle.get('duration', 0)}秒\n"
        f"[bold]字幕来源:[/bold] {subtitle.get('source', '无')}\n"
        f"[bold]文本长度:[/bold] {subtitle.get('text_length', 0)}字\n"
        f"[bold]估算 Token:[/bold] ~{subtitle.get('estimated_tokens', 0)}",
        title="📄 视频信息",
        border_style="blue",
    ))

    # 总结
    if summary:
        s = summary
        if s.get("error"):
            console.print(f"[red]❌ 总结失败: {s['error']}[/red]")
            return

        info = f"[bold]模型:[/bold] {s.get('model_used', '?')}"
        if s.get("token_count"):
            info += f" | [bold]Token:[/bold] {s['token_count']}"
        if s.get("cost_estimate"):
            info += f" | [bold]费用:[/bold] ¥{s['cost_estimate']:.4f}"

        console.print(Panel.fit(info, border_style="yellow"))
        console.print(Markdown(s.get("summary", "")))
    else:
        console.print("[yellow]⚠ 未生成总结[/yellow]")


def main():
    """主流程"""
    show_banner()

    # 选择 LLM
    provider = select_llm()

    engine = VideoSummarizer()

    while True:
        url = input_url()
        if url is None:
            break

        console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]正在处理...", total=None)

            result = engine.process(
                url,
                use_cache=True,
                provider=provider,
            )

        progress.remove_task(task)

        if result.get("error"):
            console.print(f"[red]❌ 处理失败: {result['error']}[/red]")
        else:
            show_result(
                result.get("platform", "?"),
                result.get("summary"),
                result.get("subtitle"),
            )

        console.print()
        if not Confirm.ask("[bold]继续处理下一个视频？[/bold]", default=True):
            break

    console.print("[green]👋 再见！[/green]")


if __name__ == "__main__":
    main()
