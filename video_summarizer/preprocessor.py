"""
文本预处理 — 在传给 LLM 之前清理和压缩字幕文本。

目的：减少 token 消耗，提高总结质量。
"""

import re


class TextPreprocessor:
    """字幕文本预处理器"""

    # 常见语气词、填充词
    FILLER_WORDS = {
        "嗯", "呃", "啊", "哦", "呐", "嘛", "咯",
        "那个", "这个", "就是", "然后", "反正", "其实",
        "就是说", "这样的话", "那么", "所以说",
    }

    # 重复标点
    REPEATED_PUNCT = re.compile(r"([。！？，、；：])\1+")

    @classmethod
    def clean(cls, text: str) -> str:
        """清理字幕文本"""
        text = cls._remove_timestamps(text)
        text = cls._remove_repeated_punctuation(text)
        text = cls._merge_short_lines(text)
        text = cls._remove_filler_words(text)
        text = cls._normalize_whitespace(text)
        return text.strip()

    @classmethod
    def _remove_timestamps(cls, text: str) -> str:
        """移除时间戳（如果有）"""
        # B站字幕JSON没有时间戳，但以防万一
        return re.sub(r"\[\d{1,2}:\d{2}(?:\.\d{2,})?(?:-->|,)\s*\d{1,2}:\d{2}(?:\.\d{2,})?\]",
                      "", text)

    @classmethod
    def _remove_repeated_punctuation(cls, text: str) -> str:
        """去重标点符号（如"！！！" → "！"）"""
        return cls.REPEATED_PUNCT.sub(r"\1", text)

    @classmethod
    def _merge_short_lines(cls, text: str) -> str:
        """合并短行（字幕分段导致的碎片）"""
        lines = text.split("\n")
        merged = []
        buffer = ""
        for line in lines:
            line = line.strip()
            if not line:
                if buffer:
                    merged.append(buffer)
                    buffer = ""
                continue
            # 如果当前行太短且不以句号结尾，合并到上一行
            if buffer and (len(line) < 15 or not line[-1] in "。！？.!?"):
                buffer += line
            else:
                if buffer:
                    merged.append(buffer)
                buffer = line
        if buffer:
            merged.append(buffer)
        return "\n".join(merged)

    @classmethod
    def _remove_filler_words(cls, text: str) -> str:
        """移除语气词和填充词"""
        for word in sorted(cls.FILLER_WORDS, key=len, reverse=True):
            # 中文语流中常见模式：开头/结尾/逗号后
            patterns = [
                rf"^{re.escape(word)}\s*,?\s*",     # 句首: "嗯，"
                rf"\s*{re.escape(word)}\s*$",         # 句尾
                rf"，\s*{re.escape(word)}\s*，",       # 句中: "，嗯，"
                rf"，\s*{re.escape(word)}\s",          # "，嗯 "
            ]
            for p in patterns:
                text = re.sub(p, "", text)
        return text

    @classmethod
    def _normalize_whitespace(cls, text: str) -> str:
        """规范化空白字符"""
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n", "\n", text)
        return text.strip()

    @classmethod
    def segment(cls, text: str, max_chars: int = 3000) -> list[str]:
        """
        将长文本分段，适合 LLM 分块处理。
        max_chars: 每段最大字符数
        """
        if len(text) <= max_chars:
            return [text]

        segments = []
        current = []
        current_len = 0

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if current_len + len(line) > max_chars and current:
                segments.append("\n".join(current))
                current = [line]
                current_len = len(line)
            else:
                current.append(line)
                current_len += len(line)

        if current:
            segments.append("\n".join(current))

        return segments

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """估算 token 数（中英文混合近似）"""
        # 中文约 1.5-2 token/字，英文约 1 token/3-4 字符
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 1.5 + other_chars / 3.5)
