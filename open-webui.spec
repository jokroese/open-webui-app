# -*- mode: python ; coding: utf-8 -*-

from build import build_config
from PyInstaller.building.build_main import Analysis, PYZ, EXE

config = build_config()

a = Analysis(
    ["backend/start_open_webui.py"],
    pathex=["backend"],
    binaries=config["binaries"],
    datas=config["datas"],
    hiddenimports=config["hiddenimports"],
    excludes=config["excludes"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    noarchive=config["NOARCHIVE"],
    optimize=config["OPTIMIZE"],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="open-webui",
    debug=config["DEBUG"],
    bootloader_ignore_signals=config["BOOTLOADER_IGNORE_SIGNALS"],
    strip=False,
    upx=config["UPX"],
    upx_exclude=[],
    runtime_tmpdir=None,
    console=config["CONSOLE"],
)
