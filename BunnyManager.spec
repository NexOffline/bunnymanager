# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['soundpack_copier.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/fonts/Orbitron-Medium.ttf', 'assets/fonts'),
           ('assets/fonts/Orbitron-Bold.ttf', 'assets/fonts'),
           ('assets/fonts/OFL.txt', 'assets/fonts'),
           ('assets/images/bunny-logo.png', 'assets/images'),
           ('assets/images/BunnyManager.ico', 'assets/images')],
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
    name='BunnyManager',
    icon='assets/images/BunnyManager.ico',
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
