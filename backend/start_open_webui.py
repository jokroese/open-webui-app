#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path
import base64
import uvicorn
import platform
import multiprocessing


def setup_data_dir():
    """Determine and set DATA_DIR if not already set."""
    custom_data_dir = os.environ.get("DATA_DIR")

    if custom_data_dir:
        data_dir = Path(custom_data_dir)
    else:
        system = platform.system()
        if system == "Darwin":  # macOS
            base_dir = Path.home() / "Library" / "Application Support"
        elif system == "Windows":
            base_dir = Path(os.getenv("APPDATA", Path.home()))
        else:  # Linux and others
            base_dir = Path.home() / ".local" / "share"

        data_dir = base_dir / "open-webui"

    # Set and ensure the directory exists
    os.environ["DATA_DIR"] = str(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"[DEBUG] DATA_DIR is set to: {data_dir}")

    return data_dir


def generate_secret_key(key_file):
    """Generate or load a secret key."""
    if not key_file.exists():
        print("Generating WEBUI_SECRET_KEY")
        secret = base64.b64encode(os.urandom(12)).decode("utf-8")
        key_file.write_text(secret)
    else:
        print(f"Loading WEBUI_SECRET_KEY from {key_file}")
    return key_file.read_text().strip()


def main():
    multiprocessing.freeze_support()

    setup_data_dir()

    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)

    # detect frozen
    import sys

    if getattr(sys, "frozen", False):
        frontend_build_dir = Path(sys._MEIPASS) / "build"
    else:
        frontend_build_dir = Path(
            os.getenv("FRONTEND_BUILD_DIR", script_dir.parent / "build")
        ).resolve()

    os.environ["FRONTEND_BUILD_DIR"] = str(frontend_build_dir)

    print(f"[DEBUG] FRONTEND_BUILD_DIR is set to: {frontend_build_dir}")

    # Default values
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    key_file = script_dir / ".webui_secret_key"

    # Handle WEBUI_SECRET_KEY if not set
    webui_secret_key = os.environ.get("WEBUI_SECRET_KEY") or generate_secret_key(
        key_file
    )

    # Export WEBUI_SECRET_KEY for child processes
    os.environ["WEBUI_SECRET_KEY"] = webui_secret_key

    # Optional: handle ollama / CUDA (left out for simplicity)
    if os.environ.get("USE_OLLAMA_DOCKER", "").lower() == "true":
        print("USE_OLLAMA is true. Starting ollama serve...")
        subprocess.Popen(["ollama", "serve"])

    if os.environ.get("USE_CUDA_DOCKER", "").lower() == "true":
        print("CUDA enabled. Updating LD_LIBRARY_PATH...")
        ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
        cuda_paths = [
            "/usr/local/lib/python3.11/site-packages/torch/lib",
            "/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib",
        ]
        os.environ["LD_LIBRARY_PATH"] = f"{ld_library_path}:{':'.join(cuda_paths)}"

    # Optional: HuggingFace SPACE_ID logic
    if os.environ.get("SPACE_ID"):
        print("Configuring for HuggingFace Space deployment (simplified)")
        # Add your specific logic here if needed.

    # Start Uvicorn
    print(f"Starting Open WebUI on {host}:{port}...")
    from open_webui.main import app

    uvicorn.run(app, host=host, port=port, forwarded_allow_ips="*", workers=1, reload=False)


if __name__ == "__main__":
    main()
