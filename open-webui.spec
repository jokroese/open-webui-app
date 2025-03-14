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
import os
import sys

# Mode selection
BUILD_MODE = os.environ.get("BUILD_MODE", "dev").lower()

if BUILD_MODE not in ("dev", "prod"):
    raise ValueError(f"Unknown BUILD_MODE: {BUILD_MODE}")

print(f"[INFO] Building in {BUILD_MODE.upper()} mode")

# Mode-dependent options
DEBUG = BUILD_MODE == "dev"
NOARCHIVE = BUILD_MODE == "dev"
OPTIMIZE = 0 if DEBUG else 2
CONSOLE = DEBUG
# STRIP = not DEBUG
UPX = not DEBUG
BOOTLOADER_IGNORE_SIGNALS = not DEBUG


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
    "scipy.special._cdflib",
    "importlib_resources.trees",
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

# Platform-specific dependencies
PLATFORM_SPECIFICS = {
    "darwin": {
        "excludes": [],
        "notes": "macOS-specific dependencies go here",
    },
    "win32": {
        "excludes": ["user32", "msvcrt"],
        "notes": "Windows-specific exclusions",
    },
    "linux": {
        "excludes": ["libc", "libnvidia-ml"],
        "notes": "Linux-specific exclusions",
    },
}


def gather_exclusions(current_platform):
    """
    Return a list of all excludes not applicable to the current platform.
    """
    all_excludes = []
    for plat, details in PLATFORM_SPECIFICS.items():
        if plat != current_platform:
            all_excludes.extend(details.get("excludes", []))
    return all_excludes


current_platform = sys.platform
if current_platform.startswith("linux"):
    current_platform = "linux"

if current_platform not in PLATFORM_SPECIFICS:
    raise RuntimeError(f"Unsupported platform: {current_platform}")

print(f"[INFO] Building for platform: {current_platform}")

excludes = gather_exclusions(current_platform)

print(f"[INFO] Excluding these platform-specific modules: {excludes}")

a = Analysis(
    ["backend/start_open_webui.py"],
    pathex=["backend"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=NOARCHIVE,
    optimize=OPTIMIZE,
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
    bootloader_ignore_signals=BOOTLOADER_IGNORE_SIGNALS,
    strip=False,
    upx=UPX,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

print(
    f"""
[BUILD SUMMARY]
Mode: {BUILD_MODE.upper()}
Platform: {current_platform}
DEBUG: {DEBUG}
OPTIMIZE: {OPTIMIZE}
NOARCHIVE: {NOARCHIVE}
UPX: {UPX}
CONSOLE: {CONSOLE}
"""
)
