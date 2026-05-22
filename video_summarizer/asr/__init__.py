"""
语音识别模块接口。
默认实现为 faster-whisper，可替换为其他 ASR 引擎。
"""

# 自动导入所有 ASR 引擎，触发注册
from . import whisper_engine
