# vidsum 开发工作流

## 1. 日常开发（WSL）

```bash
# 进入项目
cd ~/hmpro/tools/video-summarizer

# 改代码...

# 重建包
python3 -m build --sdist

# 本地重装
pip install dist/vidsum-0.2.0.tar.gz --force-reinstall
```

## 2. 本地测试

### 快速功能验证（推荐）
```bash
vidsum --url <B站链接> --model deepseek
# 单条命令走完下载→提取→总结全流程，直接在终端出结果
```

### Web UI 测试
```bash
# WSL 下必须加 --host 0.0.0.0
vidsum --host 0.0.0.0
# Windows 浏览器访问 http://172.30.30.3:8000
```

### 检查 ffmpeg 自动下载
```bash
# 先确认系统没有 ffmpeg
which ffmpeg && echo "存在" || echo "不存在"

# 如果有，临时屏蔽
PATH=/usr/bin python3 -m video_summarizer --host 0.0.0.0
```

### 检查 Whisper 模型
```bash
# 启动后用 --url 传一个无字幕视频，看是否自动下载 base 模型
vidsum --url <抖音链接> --model deepseek
```

## 3. 发布流程

### 版本号管理
```bash
# 只有重大变更才改版本号（小修小补不升版，覆盖安装即可）
# 改 pyproject.toml 里的 version
vim pyproject.toml # version = "0.2.0" → "0.2.1"
# 然后按i 进入编辑模式 编辑好后
# 按Esc退回到普通模式
# 然后输入 :wq (保存并推出) 最后按Enter即可

```

### 提交 GitHub
```bash
# 看看改了什么
git status
git diff
# git diff后可能会进入less分页文档 按enter看完diff差异 最后按q退出即可

# 提交
git add -A
git commit -m "v0.2.1: 简短描述改动"
git push origin master

# 打 tag（触发生成 EXE 的 GitHub Actions）
git tag v0.2.1
git push origin v0.2.1
```

### 发布 PyPI（自动）

GitHub Actions 已配好 `PYPI_API_TOKEN`。**推送 tag 即自动发布**，无需手动操作。

```bash
# 只需推送 tag，剩下的交给 Actions
git tag v0.2.1
git push origin v0.2.1
```

触发 `publish.yml`，自动：
1. `python -m build` 构建
2. `twine upload dist/*` 推送到 PyPI

## 4. Windows 测试

发布完成后在 Windows 终端：

```cmd
:: 安装或更新
pip install vidsum --upgrade

:: 可以直接在 CMD 里测试
vidsum --url <B站链接> --model deepseek

:: 或者启动 Web UI
vidsum

:: 浏览器自动打开 http://127.0.0.1:8000
```

## 5. 完整循环（一张图）

```
┌───────────────────┐
│  WSL 改代码        │
│  python3 -m build │
│  pip install ...   │
│  vidsum --url 测试  │
└───────┬───────────┘
        │ git add + commit + push + tag
        ▼
┌───────────────────┐
│  GitHub Actions   │
│  └─ 自动构建 EXE  │
│  └─ 自动发 PyPI   │
└───────┬───────────┘
        │ pip install --upgrade
        ▼
┌───────────────────┐
│  Windows 测试      │
│  vidsum --url 验证  │
└───────────────────┘
```

## 6. 常用命令速查

| 场景 | 命令 |
|------|------|
| 重建包 | `python3 -m build --sdist` |
| 重装本地 | `pip install dist/*.tar.gz --force-reinstall` |
| 本地测试 | `vidsum --url <链接> --model deepseek` |
| Web UI | `vidsum --host 0.0.0.0` |
| 提交代码 | `git add -A && git commit -m "xxx" && git push` |
| 打 tag | `git tag v0.x.x && git push origin v0.x.x` |
| 打 tag 触发发布 | `git tag v0.x.x && git push origin v0.x.x` ⏎ GitHub Actions 自动发 PyPI + EXE |
| Windows 更新 | `pip install vidsum --upgrade` |

---

**规则：**
- 小修小补不升版本号，`--force-reinstall` 覆盖安装测试
- 只有 **代码改动已确认** 且 **本地测试通过** 才走发布流程
- 每次发布前 build + 本地测试必须走一遍，不在 WSL 验证通过就不发
