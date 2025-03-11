#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path
import base64
import uvicorn


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
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)

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
    uvicorn.run(app, host=host, port=port, forwarded_allow_ips='*')


if __name__ == "__main__":
    main()
