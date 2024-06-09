# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['..\\cardiacmap\\app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('C:\\Users\\Chris\\miniconda3\\envs\\cardiacmap\\Lib\\site-packages\\dash_extensions', 'dash_extensions'),
        ('C:\\Users\\Chris\\miniconda3\\envs\\cardiacmap\\Lib\\site-packages\\dash', 'dash'),
        ('C:\\Users\\Chris\\miniconda3\\envs\\cardiacmap\\Lib\\site-packages\\dash_bootstrap_components', 'dash_bootstrap_components'),
        ('C:\\Users\\Chris\\miniconda3\\envs\\cardiacmap\\Lib\\site-packages\\dash_core_components', 'dash_core_components'),
        ('C:\\Users\\Chris\\miniconda3\\envs\\cardiacmap\\Lib\\site-packages\\dash_core_components', 'dash_core_components'),
        ('C:\\Users\\Chris\\miniconda3\\envs\\cardiacmap\\Lib\\site-packages\\dash_player', 'dash_player'),
        ('C:\\Users\\Chris\\miniconda3\\envs\\cardiacmap\\Lib\\site-packages\\cv2', 'cv2'),
        ('C:\\Users\\Chris\\miniconda3\\envs\\cardiacmap\\Lib\\site-packages\\ffmpeg', 'ffmpeg'),
        ('..\\cardiacmap\\assets', 'assets'),

    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='app',
)