<p align="center">
  <h1 align="center">🎬 Video Summarizer</h1>
  <p align="center">输入 B站 / 抖音链接 → 自动提取字幕 → AI 总结内容</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue">
  <img src="https://img.shields.io/badge/license-MIT-green">
  <img src="https://img.shields.io/badge/DeepSeek-GLM--Qwen--Ollama-orange">
</p>

---

## ✨ 功能介绍

| 功能 | 说明 |
|------|------|
| 🎬 **B站视频** | 有字幕的直接 API 提取（免费），无字幕的自动语音识别 |
| 🎵 **抖音视频** | 自动下载音频 → Whisper 语音识别转文字 |
| 🤖 **AI 总结** | 支持 DeepSeek V4 / GLM / Qwen 云端 API，以及 Ollama 本地模型 |
| 🏠 **本地免费** | 搭配 Ollama 使用，完全离线，0 成本 |
| 💾 **自动保存** | 每次总结可保存为 Markdown 文件，方便日后翻阅 |

---

## 🚀 快速开始

### 1️⃣ 安装

任选一种方式：

```bash
# 方式一：一键安装（推荐）
bash <(curl -s https://raw.githubusercontent.com/lyrumu/video-summarizer/main/install.sh)

# 方式二：pip 安装
pip install video-summarizer

# 方式三：源码运行
git clone https://github.com/lyrumu/video-summarizer.git
cd video-summarizer
pip install -r requirements.txt
```

### 2️⃣ 启动

安装完成后，在终端输入：

```bash
video-summarizer
```

看到这行输出就说明启动成功了：
```
🚀 启动 Web UI...
  http://127.0.0.1:8020
```

> ⚠ 请保持终端窗口开着，不要关闭。想停止服务按 `Ctrl+C`。

### 3️⃣ 打开浏览器

在浏览器地址栏输入：

```
http://127.0.0.1:8020
```

---

## 📖 使用教程

### 第一步：启动服务

在终端运行 `video-summarizer`，然后打开浏览器访问 **http://127.0.0.1:8020**

你会看到这样的界面：

```
┌─────────────────────────────────────────────────┐
│  🎬 Video Summarizer                            │
│  输入视频链接，AI 自动提取字幕并总结内容          │
│                                                  │
│  ┌─────────────────────────────────────┐ ┌────┐ │
│  │ 粘贴 B站 / 抖音链接...              │ │开始│ │
│  └─────────────────────────────────────┘ └────┘ │
│  🎬 bilibili.com/video/BV1GJ411x7kP             │
└─────────────────────────────────────────────────┘
```

### 第二步：配置 AI 模型

点击顶部导航栏的 **配置**，进入 `/config` 页面。

#### 选项 A：用云端 API（推荐新手）

1. 选择提供商（如 **DeepSeek**）
2. 输入你的 **API Key**
   - DeepSeek: 在 [platform.deepseek.com](https://platform.deepseek.com) 注册获取
   - GLM: 在 [open.bigmodel.cn](https://open.bigmodel.cn) 注册获取
   - Qwen: 在 [dashscope.aliyuncs.com](https://dashscope.aliyuncs.com) 注册获取
3. 选择模型（默认 `deepseek-v4-flash`，或点 **🔄 刷新** 实时拉取最新列表）
4. 点 **保存配置**

#### 选项 B：用本地模型（完全免费）

需要先安装 Ollama：

```bash
# 安装 Ollama（Linux/Mac）
curl -fsSL https://ollama.com/install.sh | sh

# 下载一个模型（任选一个）
ollama pull deepseek-r1:8b      # 推理强，约5GB
ollama pull qwen2.5:7b          # 均衡，约4GB
ollama pull llama3.2:3b         # 轻量，约2GB
```

然后回到配置页，选 **Ollama（本地免费）** → 选择你下载的模型 → 保存（不需要 API Key）。

> **Windows 用户注意**：Ollama 安装在 Windows 上时，WSL 可以通过 `localhost:11434` 自动访问，配置页无需修改。

### 第三步：总结视频

1. 回到 **首页**
2. 在输入框粘贴视频链接，例如：
   ```
   https://www.bilibili.com/video/BV1GJ411x7kP
   ```
3. 点击 **开始总结**
4. 等待处理完成（首次运行会自动下载 Whisper 语音模型，约 150MB）

### 第四步：查看结果

处理完成后你会看到：

```
┌─────────────────────────────────────────────────┐
│  📄 视频信息                                      │
│  平台: BILIBILI  │  时长: 1分21秒                  │
│  字幕来源: 语音识别  │  文本: 515字                 │
├─────────────────────────────────────────────────┤
│  🤖 AI 总结                                      │
│                                                  │
│  DeepSeek R1 8B 自动识别了视频内容并生成了          │
│  下面这份总结...                                   │
│                                                  │
│  📋 要点：                                        │
│  • ...                                           │
│  • ...                                           │
│                                                  │
│  🏷 关键词: AI绘画, GPT Image2, ChatGPT           │
│                                                  │
│  [💾 保存记录]  [📄 查看完整回复]                   │
└─────────────────────────────────────────────────┘
```

- **💾 保存记录** — 保存为 `.md` 文件到 `~/.video-summarizer/history/`
- **📄 查看完整回复** — 展开查看 AI 的原始输出

### 第五步：管理历史记录

所有保存的记录在 `~/.video-summarizer/history/` 目录下，按日期命名：

```
~/.video-summarizer/history/
├── 20260521_092016_测试视频.md
├── 20260521_102030_ChatGPT教程.md
└── ...
```

你也可以通过命令行指定保存位置：

```bash
video-summarizer --output-dir ~/Desktop/summaries
```

---

## 🖥 命令行模式

不想开浏览器的话，可以直接在终端处理：

```bash
# 单次处理
video-summarizer --url "https://www.bilibili.com/video/BVxxx"

# 指定模型
video-summarizer --url "https://www.douyin.com/video/xxx" --model ollama

# 指定保存目录
video-summarizer --output-dir ~/Desktop/summaries --url "https://..."
```

---

## ⚙️ 配置详解

| 配置项 | 路径 | 说明 |
|--------|------|------|
| API Key | `/config` 页面 | 云端模型的密钥 |
| 模型选择 | `/config` 页面 | 当前支持 DeepSeek / GLM / Qwen / Ollama |
| 实时刷新 | `/config` 页面 🔄 按钮 | 从厂商 API 拉取最新模型列表 |
| 自定义模型 | `/config` 页面 | 支持手动输入任意模型名 |
| 缓存管理 | `/config` 页面 | 清空已处理的视频缓存 |
| 保存目录 | `--output-dir` 参数 | 指定历史记录保存位置 |

### 各模型费用参考

| 提供商 | 模型 | 输入价格 | 输出价格 |
|--------|------|---------|---------|
| DeepSeek | V4 Flash | ¥1/百万 tokens | ¥2/百万 tokens |
| DeepSeek | V4 Pro | ¥3/百万 tokens | ¥6/百万 tokens |
| GLM | 4-Flash | 免费额度 | 免费额度 |
| Qwen | Turbo | ¥0.3/百万 tokens | ¥0.6/百万 tokens |
| Ollama | 所有模型 | **免费** | **免费** |

---

## ❓ 常见问题

**Q: 第一次运行很慢？**
A: 首次会下载 Whisper 语音识别模型（~150MB），后续秒开。

**Q: 提示模型找不到？**
A: 去配置页点 **🔄 刷新** 从 API 拉取最新列表，或选 **✏️ 自定义模型名** 手动输入。

**Q: 能处理多长的视频？**
A: 不限长度。B站有字幕的直接 API 提取，无字幕的会自动分段语音识别。

**Q: 要不要 GPU？**
A: 推荐有 GPU，但不是必须。Whisper 在 CPU 上也能跑（慢一些），Ollama 也一样。

**Q: 历史记录存在哪？**
A: 默认 `~/.video-summarizer/history/`，可通过 `--output-dir` 改成桌面等位置。

---

## 🏗 项目结构

```
video-summarizer/
├── video_summarizer/       # 核心代码
│   ├── engine.py           # 主编排器（协调各模块）
│   ├── fetchers/           # 平台提取器（可插拔）
│   │   ├── bilibili.py     # B站字幕提取
│   │   └── douyin.py       # 抖音音频提取
│   ├── asr/                # 语音识别（Whisper）
│   ├── summarizer/         # AI 总结层
│   └── web/                # Web UI 界面
├── install.sh              # 一键安装脚本
└── pyproject.toml          # Python 包配置
```

## 🔌 扩展开发

添加新平台只需一个文件 + 一行注册：

```python
# video_summarizer/fetchers/my_platform.py
from .base import Fetcher, FetcherRegistry

class MyFetcher(Fetcher):
    @classmethod
    def can_handle(cls, url): return "my-site.com" in url
    def fetch_subtitle(self, url): ...

FetcherRegistry.register(MyFetcher)
```

## 📜 License

MIT
