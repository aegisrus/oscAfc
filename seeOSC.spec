# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['seeOSC.py'],
    pathex=[],
    binaries=[('./Aegis_osc.pyd', '.')
    ,('C:/Windows/System32/mfc140.dll', '.')
    , ('C:/Windows/System32/msvcp140.dll', '.')
    , ('C:/Windows/System32/vccorlib140.dll', '.')],
    datas=[],
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
    name='seeOSC',
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
