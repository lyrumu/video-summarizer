"""
统一的 LLM 调用客户端。
DeepSeek / GLM / Qwen / Ollama 都兼容 OpenAI API 格式，所以用同一套代码。
"""

import re
from typing import Optional
from openai import OpenAI

from .base import Summarizer, SummarizerRegistry
from ..models import SummaryResult
from ..config import LLMConfig


class OpenAIClient(Summarizer):
    """
    通用 OpenAI 兼容客户端。
    适用于 DeepSeek / GLM / Qwen / Ollama 等。
    """

    def __init__(self, config: LLMConfig = None, **kwargs):
        self._config = config or LLMConfig()
        # 允许 kwargs 覆盖 config
        for k, v in kwargs.items():
            if hasattr(self._config, k) and v:
                setattr(self._config, k, v)

        self._client = OpenAI(
            api_key=self._config.api_key or "not-needed",
            base_url=self._config.api_base,
        )

    @property
    def model_name(self) -> str:
        return self._config.model

    @property
    def cost_per_1k_tokens(self) -> float:
        """返回每千 token 成本（元），近似值"""
        pricing = {
            "deepseek-v4-flash": 0.002,          # DeepSeek V4 Flash: ¥1/1M in, ¥2/1M out ≈ ¥0.002/1K avg
            "deepseek-v4-pro": 0.006,            # DeepSeek V4 Pro: ¥3/1M in, ¥6/1M out
            "deepseek-chat": 0.001,            # DeepSeek V3: ¥1/1M tokens= ¥0.001/1K
            "deepseek-reasoner": 0.004,       # DeepSeek R1: ¥4/1M tokens
            "glm-4-flash": 0.0001,            # GLM Flash: ¥0.1/1M tokens
            "glm-4-plus": 0.005,              # GLM Plus: ¥5/1M tokens
            "qwen-turbo": 0.0003,             # Qwen Turbo: ¥0.3/1M tokens
            "qwen-plus": 0.0008,               # Qwen Plus: ¥0.8/1M tokens
            # Ollama 本地模型（全部免费）
            "qwen2.5:7b": 0.0,
            "qwen2.5:14b": 0.0,
            "qwen2.5:32b": 0.0,
            "deepseek-r1:7b": 0.0,
            "deepseek-r1:8b": 0.0,
            "deepseek-r1:14b": 0.0,
            "deepseek-r1:32b": 0.0,
            "deepseek-coder:6.7b": 0.0,
            "llama3.2:3b": 0.0,
            "llama3.2:7b": 0.0,
            "llama3.1:8b": 0.0,
        }
        return pricing.get(self._config.model, 0.001)

    def summarize(self, text: str, max_length: Optional[str] = None) -> SummaryResult:
        """调用 LLM 总结文本"""
        sys_prompt = "你是一个专业的视频内容总结助手。请根据提供的视频字幕，生成清晰、有条理的总结。"
        user_prompt = self._build_prompt(text, max_length)

        try:
            resp = self._client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
            )

            content = resp.choices[0].message.content or ""

            # 估算 token 和费用
            input_tokens = resp.usage.prompt_tokens if resp.usage else 0
            output_tokens = resp.usage.completion_tokens if resp.usage else 0
            total_tokens = input_tokens + output_tokens
            cost = (total_tokens / 1000) * self.cost_per_1k_tokens

            # 解析结构化的总结（尝试提取要点）
            bullets = self._extract_bullets(content)
            topics = self._extract_topics(content)

            return SummaryResult(
                summary=content,
                bullet_points=bullets,
                key_topics=topics,
                model_used=self._config.model,
                token_count=total_tokens,
                cost_estimate=round(cost, 4),
            )

        except Exception as e:
            return SummaryResult(
                summary="",
                error=f"LLM 调用失败: {e}",
                model_used=self._config.model,
            )

    def _build_prompt(self, text: str, max_length: Optional[str] = None) -> str:
        """构建总结提示词"""
        length_hint = ""
        if max_length:
            length_hint = f"\n请将总结控制在{max_length}以内。"

        return (
            f"以下是视频的字幕文本，请用中文总结：{length_hint}\n\n"
            f"要求（严格遵守）：\n"
            f"1. 先用 **总体概括：** 开头，写 2-3 句话\n"
            f"2. 然后用 **核心要点：** 开头，每条用 - 开头\n"
            f"3. 然后用 **关键词：** 开头，逗号分隔，最多 5 个\n"
            f"4. 输出完关键词后立即停止，不要额外输出任何内容\n\n"
            f"--- 字幕开始 ---\n{text}\n--- 字幕结束 ---"
        )

    def _extract_bullets(self, text: str) -> list[str]:
        """从总结中提取要点列表"""
        bullets = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* ") or line.startswith("• "):
                bullets.append(line.lstrip("- *• "))
            elif line.startswith("-") and len(line) > 2:
                bullets.append(line[1:].strip())
        return bullets

    def _extract_topics(self, text: str) -> list[str]:
        """从总结中提取关键词"""
        topics = []
        in_keywords = False
        for line in text.split("\n"):
            line = line.strip().lower()
            if any(k in line for k in ["关键词", "主题", "关键字", "话题", "标签"]):
                in_keywords = True
                continue
            if in_keywords and line:
                # 清理行内标点分割的关键词
                parts = re.split(r"[、，,；; \t]+", line)
                for p in parts:
                    p = p.strip("「」【】()（）[]·：:、，, ")
                    if p and len(p) > 1:
                        topics.append(p)
        return topics[:10]  # 最多 10 个


# 注册各平台
SummarizerRegistry.register("deepseek", OpenAIClient)
SummarizerRegistry.register("glm", OpenAIClient)
SummarizerRegistry.register("qwen", OpenAIClient)
SummarizerRegistry.register("ollama", OpenAIClient)
