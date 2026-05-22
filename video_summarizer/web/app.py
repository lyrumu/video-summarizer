"""
Web UI — FastAPI 后端。
提供 REST API + 页面路由，供浏览器访问。
"""

import json
import os
import sys
from pathlib import Path

# 确保 src 在路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from video_summarizer.engine import VideoSummarizer
from video_summarizer.url_utils import is_valid_video_url
from video_summarizer.config import load_config, save_config, AppConfig, LLMConfig


app = FastAPI(title="Video Summarizer", version="0.1.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.cache_size = 0  # 兼容性：禁用 Jinja2 缓存

# 全局引擎实例（懒加载）
_engine = None


def get_engine() -> VideoSummarizer:
    global _engine
    if _engine is None:
        _engine = VideoSummarizer()
    return _engine


# ============ 页面路由 ============


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    config = load_config()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"config": config},
    )


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    config = load_config()
    return templates.TemplateResponse(
        request,
        "config.html",
        {"config": config},
    )


@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request):
    """系统状态页 — 展示所有文件路径和配置"""
    return templates.TemplateResponse(
        request,
        "status.html",
        {},
    )


# ============ API 路由 ============


@app.post("/api/summarize")
async def api_summarize(request: Request):
    """异步提交总结任务"""
    data = await request.json()
    raw_input = data.get("url", "").strip()
    
    # 从用户输入中提取 URL（处理抖音分享文本等混合内容）
    from video_summarizer.url_utils import extract_urls
    urls = extract_urls(raw_input)
    url = urls[0] if urls else raw_input
    
    provider = data.get("provider")
    model = data.get("model")

    if not url:
        return JSONResponse({"error": "请输入视频链接"}, status_code=400)

    if not is_valid_video_url(url):
        return JSONResponse({"error": "不支持的链接，目前支持 B站 和 抖音"}, status_code=400)

    try:
        engine = get_engine()
        result = engine.process(url, use_cache=True, provider=provider, model=model)

        # 序列化为 JSON 兼容格式
        serialized = {
            "url": result.get("url", url),
            "platform": result.get("platform", "UNKNOWN"),
            "error": result.get("error"),
            "subtitle": None,
            "summary": None,
        }

        sub = result.get("subtitle")
        if sub:
            serialized["subtitle"] = {
                "title": sub.get("title", ""),
                "duration": sub.get("duration", 0),
                "source": str(sub.get("source", "NONE")),
                "segments_count": sub.get("segments_count", 0),
                "text_length": sub.get("text_length", 0),
                "estimated_tokens": sub.get("estimated_tokens", 0),
                "error": sub.get("error"),
            }

        sm = result.get("summary")
        if sm:
            serialized["summary"] = {
                "summary": sm.summary,
                "bullet_points": sm.bullet_points,
                "key_topics": sm.key_topics,
                "model_used": sm.model_used,
                "token_count": sm.token_count,
                "cost_estimate": sm.cost_estimate,
                "error": sm.error,
            }

        return JSONResponse(serialized)
    except Exception as e:
        return JSONResponse({"error": f"处理失败: {str(e)}"}, status_code=500)


@app.get("/api/config")
async def api_get_config():
    """获取配置"""
    config = load_config()
    return JSONResponse({
        "provider": config.llm.provider,
        "model": config.llm.model,
        "api_key": config.llm.api_key,      # 返回实际 Key，让前端填入输入框
        "api_base": config.llm.api_base,
        "has_api_key": bool(config.llm.api_key),
        "api_keys": config.llm.api_keys or {},  # 所有提供商的 Key，供切换时使用
        "web_port": config.web_port,
    })

@app.post("/api/config")
async def api_save_config(request: Request):
    """保存配置"""
    data = await request.json()
    config = load_config()

    if "provider" in data:
        config.llm.provider = data["provider"]
    if "api_key" in data:
        config.llm.api_key = data["api_key"]
    if "model" in data:
        config.llm.model = data["model"]
    if "api_base" in data:
        config.llm.api_base = data["api_base"]

    save_config(config)
    return JSONResponse({"status": "ok"})


@app.post("/api/clear-key")
async def api_clear_key():
    """一键清除所有提供商的 API Key"""
    config = load_config()
    config.llm.api_key = ""
    # 清除所有提供商的 Key
    if config.llm.api_keys:
        for k in config.llm.api_keys:
            config.llm.api_keys[k] = ""
    else:
        config.llm.api_keys = {}
    save_config(config)
    return JSONResponse({"status": "ok", "message": "所有 API Key 已清除"})


@app.post("/api/clear-cache")
async def api_clear_cache():
    """清空缓存"""
    from video_summarizer.cache import Cache
    from video_summarizer.config import CONFIG_DIR

    cache = Cache(str(CONFIG_DIR / "cache"))
    cache.clear()
    return JSONResponse({"status": "ok", "message": "缓存已清空"})


@app.get("/api/models/{provider}")
async def api_models(provider: str):
    """获取某个提供商支持的模型列表"""
    models = {
        "deepseek": [
            {"id": "deepseek-v4-flash", "name": "DeepSeek V4 Flash", "cost": "¥1/1M tokens"},
            {"id": "deepseek-v4-pro", "name": "DeepSeek V4 Pro", "cost": "¥3/1M tokens"},
            {"id": "deepseek-chat", "name": "DeepSeek V3", "cost": "¥1/1M tokens"},
            {"id": "deepseek-reasoner", "name": "DeepSeek R1", "cost": "¥4/1M tokens"},
        ],
        "glm": [
            {"id": "glm-4-flash", "name": "GLM-4-Flash (免费)", "cost": "免费"},
            {"id": "glm-4-plus", "name": "GLM-4-Plus", "cost": "¥5/1M tokens"},
        ],
        "qwen": [
            {"id": "qwen-turbo", "name": "Qwen Turbo", "cost": "¥0.3/1M tokens"},
            {"id": "qwen-plus", "name": "Qwen Plus", "cost": "¥0.8/1M tokens"},
            {"id": "qwen-max", "name": "Qwen Max", "cost": "¥2/1M tokens"},
        ],
        "ollama": [
            {"id": "deepseek-r1:7b", "name": "DeepSeek R1 7B (本地)", "cost": "免费"},
            {"id": "deepseek-r1:8b", "name": "DeepSeek R1 8B (本地)", "cost": "免费"},
            {"id": "deepseek-r1:14b", "name": "DeepSeek R1 14B (本地)", "cost": "免费"},
            {"id": "deepseek-r1:32b", "name": "DeepSeek R1 32B (本地)", "cost": "免费"},
            {"id": "deepseek-coder:6.7b", "name": "DeepSeek Coder 6.7B (本地)", "cost": "免费"},
            {"id": "qwen2.5:7b", "name": "Qwen 2.5 7B (本地)", "cost": "免费"},
            {"id": "qwen2.5:14b", "name": "Qwen 2.5 14B (本地)", "cost": "免费"},
            {"id": "qwen2.5:32b", "name": "Qwen 2.5 32B (本地)", "cost": "免费"},
            {"id": "llama3.2:3b", "name": "LLaMA 3.2 3B (本地)", "cost": "免费"},
            {"id": "llama3.2:7b", "name": "LLaMA 3.2 7B (本地)", "cost": "免费"},
            {"id": "llama3.1:8b", "name": "LLaMA 3.1 8B (本地)", "cost": "免费"},
        ],
    }
    return JSONResponse(models.get(provider, []))


@app.post("/api/test-connection")
async def api_test_connection(request: Request):
    """真正测试 API 连接 — 发一条简单消息看能不能返回"""
    from openai import OpenAI

    data = await request.json()
    provider = data.get("provider", "")
    api_key = data.get("api_key", "")
    api_base = data.get("api_base", "")
    model = data.get("model", "")

    if not api_key:
        return JSONResponse({"success": False, "error": "缺少 API Key"})

    try:
        client = OpenAI(api_key=api_key, base_url=api_base, timeout=10)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "回复'OK'表示连接测试通过"}],
            max_tokens=10,
        )
        reply = resp.choices[0].message.content or ""
        return JSONResponse({
            "success": True,
            "model": resp.model if hasattr(resp, 'model') else model,
            "response": reply[:50],
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.post("/api/models/live/{provider}")
async def api_models_live(provider: str, request: Request):
    """从提供商 API 实时拉取模型列表（调用 /v1/models）"""
    from video_summarizer.config import AppConfig, LLMConfig

    data = await request.json()
    api_key = data.get("api_key", "")

    # 获取对应 provider 的 API base
    defaults = {
        "deepseek": "https://api.deepseek.com",
        "glm": "https://open.bigmodel.cn/api/paas/v4",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
    base_url = defaults.get(provider, "http://localhost:11434/v1")

    if not api_key and provider != "ollama":
        return JSONResponse({"error": "缺少 API Key", "models": []})

    try:
        import httpx
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{base_url}/models", headers=headers)
            if resp.status_code != 200:
                return JSONResponse({
                    "error": f"API 返回 {resp.status_code}",
                    "models": [],
                })
            body = resp.json()
            raw_models = body.get("data", body.get("models", []))
            models = []
            for m in raw_models:
                mid = m.get("id", m.get("name", ""))
                if mid:
                    models.append({"id": mid, "name": mid})
            if not models:
                return JSONResponse({"error": "API 未返回模型列表", "models": []})
            return JSONResponse({"models": models})
    except Exception as e:
        return JSONResponse({"error": str(e), "models": []})


@app.post("/api/save")
async def api_save(request: Request):
    """保存当前记录为 .md 文件"""
    from datetime import datetime
    from video_summarizer.config import HISTORY_DIR

    data = await request.json()
    url = data.get("url", "").strip()
    sub = data.get("subtitle", {}) or {}
    summary = data.get("summary", {}) or {}

    if not url:
        return JSONResponse({"error": "缺少 url"}, status_code=400)

    title = sub.get("title", "未知视频") or "未知视频"

    # 构建 Markdown
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:60]
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_title}.md"

    history_dir = HISTORY_DIR
    history_dir.mkdir(parents=True, exist_ok=True)
    filepath = history_dir / filename

    md = f"""# 🎬 视频总结

> **时间**: {timestamp}
> **平台**: {data.get('platform', '?')}
> **链接**: [{url}]({url})
> **模型**: {summary.get('model_used', '?')}

## 视频信息

- **标题**: {title}
- **时长**: {sub.get('duration', 0):.0f}秒
- **字幕来源**: {sub.get('source', '?')}
- **文本长度**: {sub.get('text_length', 0)}字
- **估算 Token**: ~{sub.get('estimated_tokens', 0)}

## AI 总结

{summary.get('summary', '（无总结）')}

"""
    bullets = summary.get("bullet_points", []) or []
    if bullets:
        md += "### 要点\n\n"
        for b in bullets:
            md += f"- {b}\n"
        md += "\n"

    topics = summary.get("key_topics", []) or []
    if topics:
        md += f"**关键词**: {'、'.join(topics)}\n\n"

    token_count = summary.get("token_count", 0)
    cost = summary.get("cost_estimate", 0)
    if token_count:
        md += f"---\n*Token: {token_count} | 费用: ¥{cost:.4f}*"

    filepath.write_text(md, encoding="utf-8")
    return JSONResponse({"status": "ok", "path": str(filepath), "filename": filename})


@app.get("/api/status")
async def api_status():
    """系统状态 — 让用户看到所有文件路径和配置"""
    import os
    from video_summarizer.config import CONFIG_DIR, CONFIG_FILE, HISTORY_DIR
    from video_summarizer.cache import Cache

    config = load_config()
    cache_dir = CONFIG_DIR / "cache"

    # 计算缓存大小
    cache_size = 0
    if cache_dir.exists():
        for f in cache_dir.glob("*.json"):
            cache_size += f.stat().st_size

    return JSONResponse({
        "version": "0.2.0",
        "config_file": str(CONFIG_FILE),
        "config_exists": CONFIG_FILE.exists(),
        "cache_dir": str(cache_dir),
        "cache_files": len(list(cache_dir.glob("*.json"))) if cache_dir.exists() else 0,
        "cache_size_bytes": cache_size,
        "history_dir": str(HISTORY_DIR),
        "history_files": len(list(HISTORY_DIR.glob("*.md"))) if HISTORY_DIR.exists() else 0,
        "provider": config.llm.provider,
        "model": config.llm.model,
        "has_api_key": bool(config.llm.api_key),
        "api_base": config.llm.api_base,
    })


@app.post("/api/shutdown")
async def api_shutdown():
    """停止 Web 服务"""
    import os
    import signal
    # 延迟一点返回，让前端收到响应再退出
    import threading
    def _kill():
        import time
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGINT)
    threading.Thread(target=_kill, daemon=True).start()
    return JSONResponse({"status": "ok", "message": "服务正在停止..."})


# ============ 启动 ============


def run(host: str = "0.0.0.0", port: int = 8020, no_browser: bool = False):
    """启动 Web 服务"""
    import os, socket
    config = load_config()

    # 检测 WSL IP（用于告知用户 Windows 浏览器访问地址）
    wsl_ip = "?"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        wsl_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    print(f"\n  🎬 Video Summarizer Web UI")
    print(f"  ─────────────────────────")
    # 显示 WSL 内访问地址
    print(f"  WSL 内地址:  http://127.0.0.1:{port}")
    if wsl_ip != "?":
        print(f"  Windows 访问: http://{wsl_ip}:{port}")
    print(f"  ─────────────────────────")
    # 检测代理环境
    http_proxy = os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")
    if http_proxy:
        print(f"  ⚠  检测到系统代理: {http_proxy}")
        print(f"  ⚠  请在代理软件中设置绕过 localhost,127.*,172.*")
    print(f"  ─────────────────────────")
    print(f"  在 Windows 浏览器里打开上面的「Windows 访问」地址")
    print(f"  按 Ctrl+C 停止服务\n")

    uvicorn.run(app, host=host, port=port, log_level="warning")
