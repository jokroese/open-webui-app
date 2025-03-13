# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.building.build_main import Analysis, PYZ, EXE
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    collect_dynamic_libs,
    collect_all,
)
from pathlib import Path
import site

DEBUG = True

# Get the first site-packages directory (should be the current venv)
site_packages_path = next(
    (Path(p) for p in site.getsitepackages() if Path(p).exists()), None
)

if not site_packages_path:
    raise RuntimeError("Couldn't locate the site-packages directory!")

print(f"[DEBUG] Using site-packages from: {site_packages_path}")


# Use collect_all for tricky packages
black_datas, black_binaries, black_hiddenimports = collect_all("black")
blib2to3_datas, blib2to3_binaries, blib2to3_hiddenimports = collect_all("blib2to3")
tiktoken_datas, tiktoken_binaries, tiktoken_hiddenimports = collect_all("tiktoken")

hiddenimports = black_hiddenimports + blib2to3_hiddenimports + tiktoken_hiddenimports
datas = black_datas + blib2to3_datas + tiktoken_datas
binaries = black_binaries + blib2to3_binaries + tiktoken_binaries

# Manual collection for well-behaved packages
packages = [
    {"name": "chromadb", "submodules": True, "datas": True, "binaries": False},
    {"name": "passlib", "submodules": True, "datas": False, "binaries": False},
    {"name": "pydantic", "submodules": True, "datas": True, "binaries": True},
    {"name": "charset_normalizer", "submodules": True, "datas": True, "binaries": True},
    {"name": "pathspec", "submodules": True, "datas": True, "binaries": False},
    {"name": "peewee", "submodules": True, "datas": False, "binaries": False},
]

for pkg in packages:
    name = pkg["name"]
    if pkg.get("submodules"):
        hiddenimports += collect_submodules(name)
    if pkg.get("datas"):
        datas += collect_data_files(name)
    if pkg.get("binaries"):
        binaries += collect_dynamic_libs(name)

# Special hiddenimports
hiddenimports += [
    "chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2",
    "chromadb.execution.executor.local",
    "chromadb.segment.impl.manager",
    "chromadb.segment.impl.manager.local",
    "chromadb.api.segment",
    "chromadb.api.client",
    "chromadb.api.shared_system_client",
    "unittest",
    "encodings.idna",
    "encodings.cp1250",
    "ftfy.bad_codecs.sloppy",
    "encodings.aliases",
]

# Special data
datas += [
    ("CHANGELOG.md", "open_webui"),
    ("backend/open_webui/internal/migrations", "open_webui/internal/migrations"),
    ("backend/open_webui/migrations", "open_webui/migrations"),
    ("build", "build"),
    ("backend/open_webui/static", "open_webui/static"),
]

# Explicitly include tiktoken_ext directory
tiktoken_ext_dir = site_packages_path / "tiktoken_ext"
if tiktoken_ext_dir.exists():
    print(f"[DEBUG] Found tiktoken_ext dir: {tiktoken_ext_dir}")
    datas.append((str(tiktoken_ext_dir), "tiktoken_ext"))
else:
    raise RuntimeError("Couldn't find tiktoken_ext directory!")

# Explicitly include _black_version module
black_version_file = site_packages_path / "_black_version.py"
if black_version_file.exists():
    print(f"[DEBUG] Found _black_version.py: {black_version_file}")
    datas.append((str(black_version_file), "."))
else:
    raise RuntimeError("Couldn't find _black_version.py!")

# Special binaries
mypyc_shared_objects = [
    (str(path), ".") for path in site_packages_path.rglob("*__mypyc*.so")
]

binaries += mypyc_shared_objects


a = Analysis(
    ["backend/start_open_webui.py"],
    pathex=["backend"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="open-webui",
    debug=DEBUG,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
