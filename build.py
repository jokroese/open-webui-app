#!/usr/bin/env python3

import argparse
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    collect_dynamic_libs,
    collect_all,
)
import PyInstaller.__main__


# -------------------------------
# ARGPARSE
# -------------------------------


def parse_args():
    parser = argparse.ArgumentParser(description="Open WebUI PyInstaller Build Helper")
    parser.add_argument(
        "--mode",
        choices=["dev", "prod"],
        default=os.environ.get("BUILD_MODE", "dev"),
        help="Build mode (default: dev)",
    )
    parser.add_argument(
        "--platform",
        choices=["darwin", "linux", "win32"],
        help="Target platform (default: auto-detect from sys.platform)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    return parser.parse_args()


# -------------------------------
# CONFIGURATION
# -------------------------------


def detect_platform(cli_platform=None):
    if cli_platform:
        return cli_platform
    plat = sys.platform
    if plat.startswith("linux"):
        return "linux"
    return plat


def get_build_options(mode, verbose=False):
    is_dev = mode == "dev"

    if verbose:
        print(f"[INFO] Build mode: {mode.upper()}")
        print(f"[INFO] Debug: {is_dev}")

    return {
        "DEBUG": is_dev,
        "NOARCHIVE": is_dev,
        "OPTIMIZE": 0 if is_dev else 2,
        "CONSOLE": is_dev,
        "UPX": not is_dev,
        "BOOTLOADER_IGNORE_SIGNALS": not is_dev,
    }


# -------------------------------
# PLATFORM-SPECIFIC RULES
# -------------------------------

PLATFORM_SPECIFICS = {
    "darwin": {
        "excludes": [],
    },
    "win32": {
        "excludes": ["user32", "msvcrt"],
    },
    "linux": {
        "excludes": ["libc", "libnvidia-ml"],
    },
}


def gather_exclusions(target_platform, verbose=False):
    all_excludes = []
    for plat, details in PLATFORM_SPECIFICS.items():
        if plat != target_platform:
            all_excludes.extend(details.get("excludes", []))
    if verbose:
        print(f"[INFO] Excludes for platform {target_platform}: {all_excludes}")
    return all_excludes


# -------------------------------
# COLLECT PACKAGES / DATA
# -------------------------------


def get_site_packages_path(verbose=False):
    site_packages = next(
        (Path(p) for p in sys.path if "site-packages" in p and Path(p).exists()), None
    )
    if not site_packages:
        raise RuntimeError("Couldn't locate site-packages directory!")
    if verbose:
        print(f"[DEBUG] site-packages path: {site_packages}")
    return site_packages


def collect_dependencies(verbose=False):
    binaries = []
    datas = []
    hiddenimports = []

    site_packages_path = get_site_packages_path(verbose)

    tricky_packages = ["black", "blib2to3", "tiktoken"]
    for package in tricky_packages:
        d, b, h = collect_all(package)
        datas += d
        binaries += b
        hiddenimports += h
        if verbose:
            print(
                f"[DEBUG] Collected {package}: {len(d)} datas, {len(b)} binaries, {len(h)} hidden imports"
            )

    # Manual collections
    packages = [
        {"name": "chromadb", "submodules": True, "datas": True, "binaries": False},
        {"name": "passlib", "submodules": True, "datas": False, "binaries": False},
        {"name": "pydantic", "submodules": True, "datas": True, "binaries": True},
        {
            "name": "charset_normalizer",
            "submodules": True,
            "datas": True,
            "binaries": True,
        },
        {"name": "pathspec", "submodules": True, "datas": True, "binaries": False},
        {"name": "peewee", "submodules": True, "datas": False, "binaries": False},
    ]

    for pkg in packages:
        name = pkg["name"]
        if pkg.get("submodules"):
            hi = collect_submodules(name)
            hiddenimports += hi
            if verbose:
                print(f"[DEBUG] Collected submodules for {name}: {len(hi)}")
        if pkg.get("datas"):
            d = collect_data_files(name)
            datas += d
            if verbose:
                print(f"[DEBUG] Collected data files for {name}: {len(d)}")
        if pkg.get("binaries"):
            b = collect_dynamic_libs(name)
            binaries += b
            if verbose:
                print(f"[DEBUG] Collected binaries for {name}: {len(b)}")

    # Special hidden imports
    special_hidden = [
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
    hiddenimports += special_hidden
    if verbose:
        print(f"[DEBUG] Added special hiddenimports: {special_hidden}")

    # Special data files
    special_datas = [
        ("CHANGELOG.md", "open_webui"),
        ("backend/open_webui/internal/migrations", "open_webui/internal/migrations"),
        ("backend/open_webui/migrations", "open_webui/migrations"),
        ("build", "build"),
        ("backend/open_webui/static", "open_webui/static"),
    ]
    datas += special_datas
    if verbose:
        print(f"[DEBUG] Added special datas: {special_datas}")

    # tiktoken_ext dir
    tiktoken_ext_dir = site_packages_path / "tiktoken_ext"
    if tiktoken_ext_dir.exists():
        datas.append((str(tiktoken_ext_dir), "tiktoken_ext"))
        if verbose:
            print(f"[DEBUG] Found and added tiktoken_ext: {tiktoken_ext_dir}")
    else:
        raise RuntimeError("Couldn't find tiktoken_ext directory!")

    # _black_version.py
    black_version_file = site_packages_path / "_black_version.py"
    if black_version_file.exists():
        datas.append((str(black_version_file), "."))
        if verbose:
            print(f"[DEBUG] Found and added _black_version.py: {black_version_file}")
    else:
        raise RuntimeError("Couldn't find _black_version.py!")

    # __mypyc__.so files
    mypyc_objects = list(site_packages_path.rglob("*__mypyc*.so"))
    binaries += [(str(path), ".") for path in mypyc_objects]
    if verbose:
        print(f"[DEBUG] Found and added mypyc shared objects: {len(mypyc_objects)}")

    return binaries, datas, hiddenimports


# -------------------------------
# EXPORT CONFIGS
# -------------------------------


def build_config(mode=None, target_platform=None, verbose=False):
    if mode is None:
        mode = os.environ.get("BUILD_MODE", "dev")

    if target_platform is None:
        target_platform = detect_platform()

    binaries, datas, hiddenimports = collect_dependencies(verbose=verbose)
    excludes = gather_exclusions(target_platform, verbose=verbose)
    build_options = get_build_options(mode, verbose=verbose)

    if verbose:
        print(
            f"""
[BUILD CONFIG]
Mode: {mode.upper()}
Platform: {target_platform}
Excludes: {excludes}
Binaries: {len(binaries)} files
Datas: {len(datas)} files
Hidden Imports: {len(hiddenimports)} items
Options:
    DEBUG: {build_options["DEBUG"]}
    OPTIMIZE: {build_options["OPTIMIZE"]}
    NOARCHIVE: {build_options["NOARCHIVE"]}
    UPX: {build_options["UPX"]}
"""
        )

    return {
        "binaries": binaries,
        "datas": datas,
        "hiddenimports": hiddenimports,
        "excludes": excludes,
        **build_options,
    }


# -------------------------------
# ENTRY POINT
# -------------------------------

if __name__ == "__main__":
    args = parse_args()
    target_platform = detect_platform(args.platform)

    config = build_config(
        mode=args.mode, target_platform=target_platform, verbose=args.verbose
    )

    pyinstaller_args = [
        "open-webui.spec",
        "--clean",
        "--distpath",
        "dist",
        "--workpath",
        "_pyi_build",
    ]

    if args.verbose:
        pyinstaller_args.append("--log-level=DEBUG")

    PyInstaller.__main__.run(pyinstaller_args)
