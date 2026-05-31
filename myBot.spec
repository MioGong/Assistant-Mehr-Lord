# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['myBot.py'],
    pathex=[],
    binaries=[],
    datas=[('auto_replies.json', '.'), ('banned_words.json', '.'), ('birthdays.json', '.'), ('cookies.txt', '.'), ('moderation.json', '.'), ('questions.txt', '.'), ('tasks.json', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='myBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
