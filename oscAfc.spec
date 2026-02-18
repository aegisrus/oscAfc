# -*- mode: python ; coding: utf-8 -*-
# oscAfc: SeeOSC + расчёт АЧХ. Точка входа — main.py

import os
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files
block_cipher = None
SPECPATH = os.path.dirname(os.path.abspath(SPEC))

def enhanced_collect(pkg_name):
    """Собирает datas, binaries и hiddenimports для пакета."""
    datas, binaries, hiddenimports = collect_all(pkg_name)
    hiddenimports += collect_submodules(pkg_name)
    return datas, binaries, hiddenimports

# scipy для ach_calculator (uniform_filter1d)
scipy_datas, scipy_binaries, scipy_hiddenimports = enhanced_collect('scipy')
# numpy для всех модулей
numpy_datas, numpy_binaries, numpy_hiddenimports = enhanced_collect('numpy')
# numba — все подмодули (включая old_scalars, old_models, old_builtins и др.)
numba_hiddenimports = collect_submodules('numba')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        ('./Aegis_osc.pyd', '.'),
        ('C:/Windows/System32/mfc140.dll', '.'),
        ('C:/Windows/System32/msvcp140.dll', '.'),
        ('C:/Windows/System32/vccorlib140.dll', '.'),
        *scipy_binaries,
        *numpy_binaries
    ],
    datas=[
        *scipy_datas,
        *numpy_datas,
    ],
    hiddenimports=[
        *scipy_hiddenimports,
        *numpy_hiddenimports,
        'scipy.ndimage',
        *numba_hiddenimports,
        'pyqtgraph',
        'pyqtgraph.exporters',
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

def remove_duplicates(lst):
    return list(dict.fromkeys(lst))

a.datas = remove_duplicates(a.datas)
a.binaries = remove_duplicates(a.binaries)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AmplFreqChar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AmplFreqChar',
)
