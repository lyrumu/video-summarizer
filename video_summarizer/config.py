"""
用户配置管理 — 支持多种 LLM 配置，持久化到 ~/.vidsum/config.json
"""

import json
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


CONFIG_DIR = Path.home() / ".vidsum"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_DIR = CONFIG_DIR / "history"  # 可被 --output-dir 覆写


@dataclass
class LLMConfig:
    """大模型配置"""
    provider: str = "ollama"       # deepseek / glm / qwen / ollama
    api_key: str = ""
    api_keys: dict = None          # 每个提供商独立的 Key，如 {"deepseek": "sk-xxx", "glm": "sk-yyy"}
    api_base: str = ""             # 为空则用默认地址
    model: str = ""                # 为空则用默认模型
    max_tokens: int = 2048
    temperature: float = 0.3

    def __post_init__(self):
        # 设置各平台默认值
        defaults = {
            "deepseek": {"api_base": "https://api.deepseek.com", "model": "deepseek-v4-flash"},
            "glm": {"api_base": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash"},
            "qwen": {"api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-turbo"},
            "ollama": {"api_base": "http://localhost:11434/v1", "model": "deepseek-r1:8b"},
        }
        if not self.api_base and self.provider in defaults:
            self.api_base = defaults[self.provider]["api_base"]
        if not self.model and self.provider in defaults:
            self.model = defaults[self.provider]["model"]
        # 从 api_keys 字典中恢复当前提供商的 Key（向后兼容）
        if isinstance(self.api_keys, dict) and self.provider in self.api_keys:
            self.api_key = self.api_keys[self.provider]


@dataclass
class AppConfig:
    """应用全局配置"""
    llm: LLMConfig = None
    cache_enabled: bool = True
    cache_dir: str = str(CONFIG_DIR / "cache")
    web_host: str = "127.0.0.1"
    web_port: int = 8020

    def __post_init__(self):
        if self.llm is None:
            self.llm = LLMConfig()


def load_config() -> AppConfig:
    """从磁盘加载配置"""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            if "llm" in data:
                data["llm"] = LLMConfig(**data["llm"])
            return AppConfig(**data)
        except Exception:
            pass
    return AppConfig()


def save_config(config: AppConfig):
    """保存配置到磁盘"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # 将当前 Key 存入 per-provider 字典
    if config.llm.api_keys is None:
        config.llm.api_keys = {}
    config.llm.api_keys[config.llm.provider] = config.llm.api_key
    data = asdict(config)
    CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
