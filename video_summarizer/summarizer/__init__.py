"""
AI 总结层。
支持 DeepSeek / GLM / Qwen 云端 API，以及 Ollama 本地模型。
"""

# 自动导入所有总结器，触发注册
from . import llm_client
