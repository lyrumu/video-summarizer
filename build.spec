# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 — Video Summarizer
构建命令: pyinstaller build.spec
"""
import os, sys

block_cipher = None

a = Analysis(
    ['video_summarizer/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        # HTML 模板
        ('video_summarizer/web/templates/*.html', 'video_summarizer/web/templates'),
    ],
    hiddenimports=[
        # faster-whisper 及其依赖
        'ctranslate2',
        'faster_whisper',
        'faster_whisper.transcribe',
        'faster_whisper.audio',
        'faster_whisper.feature_extractor',
        'faster_whisper.tokenizer',
        'faster_whisper.utils',
        'faster_whisper.vad',
        'faster_whisper.models',
        'av',
        'numpy',
        # 各平台 fetcher/summarizer 注册
        'video_summarizer.fetchers',
        'video_summarizer.fetchers.bilibili',
        'video_summarizer.fetchers.douyin',
        'video_summarizer.summarizer',
        'video_summarizer.summarizer.llm_client',
        # ASR
        'video_summarizer.asr',
        'video_summarizer.asr.whisper_engine',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'matplotlib',
        'scipy',
        'pandas',
        'notebook',
        'jupyter',
        'ipython',
        'test',
        'unittest',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='video-summarizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # 显示控制台窗口（方便看日志）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',  # 后续加上图标
)
