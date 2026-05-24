<p align="center">
  <h1 align="center">🎬 Video Summarizer</h1>
  <p align="center">粘贴视频链接 → 自动提取字幕 → AI 总结内容<br>支持 B站 / 抖音，支持 DeepSeek / GLM / Qwen / 本地 Ollama</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue">
  <img src="https://img.shields.io/badge/pip%20install-ffmpeg%20required-orange">
  <img src="https://img.shields.io/badge/license-MIT-green">
</p>

---

## 📸 效果预览

![demo](https://raw.githubusercontent.com/lyrumu/video-summarizer/main/screenshots/demo.gif)

> 还没截图？先跑起来看看。上面是效果示意，具体界面以实际为准。

---

## 🚀 一键安装

### 前置条件

需要 **Python 3.10+** 和 **pip**。验证方法：

```bash
python3 --version
pip --version
```

### 安装

```bash
pip install vidsum
```

### 启动

```bash
vidsum
```

终端会显示：

```
  🎬 Video Summarizer

  [1/3] 🔍 检测系统依赖.......... ✅ /usr/bin/ffmpeg
  [2/3] 📥 检查 Whisper 模型..... ✅ 已缓存

  ───────────────────────────────
  🎬 Video Summarizer Web UI
  http://127.0.0.1:8000
  ───────────────────────────────

  按 Ctrl+C 停止服务
```

浏览器会自动打开。如果没有，手动访问上面的地址。

> 终端输出中带有 `INFO:` 前缀的信息是 uvicorn 的正常日志，不是报错。

---

## 🔊 ffmpeg 安装（必须）

Whisper 语音识别需要 ffmpeg 来提取音频。

### Windows

**方式一：winget（推荐）**
```cmd
winget install "FFmpeg (Essentials Build)"
```

**方式二：手动下载**
1. 下载 https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
2. 解压到 `C:\ffmpeg`
3. 把 `C:\ffmpeg\bin` 添加到系统 PATH
4. 验证：打开新终端运行 `ffmpeg -version`

**方式三：放项目目录**
把 `ffmpeg.exe` 放到 `vidsum` 命令的运行目录下即可，程序会自动找到。

### macOS

```bash
brew install ffmpeg
```

### Linux

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# CentOS/RHEL
sudo dnf install ffmpeg
```

---

## 🤖 Whisper 模型

首次使用语音识别（无字幕视频）时，程序会自动下载 Whisper 模型。

```
  ⏳ 正在初始化 Whisper 模型 (small)，首次运行可能需要下载
     请耐心等待...
```

- 模型大小：`small`（约 500MB）—— 平衡速度和精度
- 缓存位置：`~/.cache/faster-whisper/`
- 只需下载一次，后续自动使用缓存

> 如果网络不好，可以手动下载模型文件放到缓存目录。具体参考 [faster-whisper 文档](https://github.com/SYSTRAN/faster-whisper)。

---

## 🖥 Windows 使用

### 直接使用（127.0.0.1）

安装 ffmpeg 后直接运行即可：

```bash
vidsum
```

浏览器访问 `http://127.0.0.1:8000`（端口自动分配，以实际显示为准）。

### WSL 中使用

WSL 默认 `127.0.0.1` 从 Windows 浏览器无法直接访问，需要：

```bash
vidsum --host 0.0.0.0
```

然后 Windows 浏览器访问终端上显示的那个 IP 地址。

---

## 🔧 高级选项

### 指定端口

```bash
vidsum --port 8888
```

不指定则自动分配（8000-8020 中找可用端口）。

> 如果指定端口被占用，程序会报错提示，不会偷偷换端口。

### 禁止自动打开浏览器

```bash
BROWSER=0 vidsum
```

适合无桌面环境的服务器、SSH 连接等场景。

### 其他参数

```bash
vidsum --help
```

| 参数 | 说明 |
|------|------|
| `--port PORT` | 指定端口（默认自动分配） |
| `--host HOST` | 指定主机地址（WSL 需 `--host 0.0.0.0`） |
| `--no-browser` | 不自动打开浏览器 |
| `--cli` | 命令行交互模式 |
| `--url URL` | 单次处理模式 |
| `--model NAME` | 指定模型提供商 |
| `--output-dir DIR` | 历史记录保存目录 |

---

## 🔌 配置文件位置

所有数据存储在用户目录下，互不干扰：

| 内容 | 位置 |
|------|------|
| 配置文件（API Key 等） | `~/.video-summarizer/config.json` |
| 历史记录（保存的 .md） | `~/.video-summarizer/history/` |
| 字幕缓存 | `~/.video-summarizer/cache/` |
| 音频缓存 | `~/.video-summarizer/audio_cache/` |
| Whisper 模型 | `~/.cache/faster-whisper/` |

---

## 🗑 卸载

### 卸载包

```bash
pip uninstall vidsum
```

### 清理配置和缓存（可选）

```bash
# 删除配置和数据
rm -rf ~/.video-summarizer

# 删除 Whisper 模型缓存
rm -rf ~/.cache/faster-whisper
```

---

## ❓ 常见问题

**Q: 第一次运行很慢？**
A: 首次会下载 Whisper 语音识别模型（约 500MB），后续秒开。

**Q: 端口 8000 用不了？**
A: 程序会自动找可用端口，不用管。如果指定了被占用的端口，会报错并提示换一个。

**Q: 提示 "未找到 ffmpeg"？**
A: 参考上方 ffmpeg 安装章节。Windows 用户也可以把 `ffmpeg.exe` 放到运行目录。

**Q: 输出很多 `INFO:` 日志正常吗？**
A: 正常，那是 uvicorn 的访问日志，不是报错。

**Q: 能处理多长的视频？**
A: 不限长度。B站有字幕的直接 API 提取，无字幕的会自动分段语音识别。

**Q: 要 GPU 吗？**
A: 推荐但不需要。Whisper 在 CPU 上也能跑（慢一些）。

**Q: 历史记录存在哪？**
A: `~/.video-summarizer/history/`，可通过 `--output-dir` 指定其他位置。

**Q: 怎么换模型？**
A: 打开配置页面，选提供商 → 输 API Key → 保存。Ollama 用户选 Ollama 即可，不需要 Key。

---

## 🏗 项目结构

```
video-summarizer/
├── video_summarizer/       # 核心代码
│   ├── engine.py           # 主编排器
│   ├── startup.py          # 启动检测 + 自动端口 + 开浏览器
│   ├── fetchers/           # 平台提取器（可插拔）
│   │   ├── bilibili.py     # B站字幕
│   │   └── douyin.py       # 抖音
│   ├── asr/                # 语音识别
│   │   └── whisper_engine.py
│   ├── summarizer/         # AI 总结
│   └── web/                # Web UI
├── pyproject.toml          # 包配置
└── README.md
```

## 🔌 扩展开发

添加新平台只需一个文件 + 一行注册：

```python
from .base import Fetcher, FetcherRegistry

class MyFetcher(Fetcher):
    @classmethod
    def can_handle(cls, url): return "my-site.com" in url
    def fetch_subtitle(self, url): ...

FetcherRegistry.register(MyFetcher)
```

## 📜 License

MIT
