"""Press Run in your editor to start local MLX inference and the DASE desktop."""
from contextlib import contextmanager
from importlib.util import find_spec
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent


def stop_process(process):
    """Stop only a child we started, including one still starting up."""
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def server_ready(client, health_url):
    import httpx

    try:
        response = client.get(health_url)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except (httpx.RequestError, ValueError, AttributeError):
        return False


def wait_for_server(process, client, health_url, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("MLX server exited during startup. See its output above.")
        if server_ready(client, health_url):
            return
        time.sleep(0.5)
    raise RuntimeError("MLX server did not become ready within two minutes. See its output above.")


@contextmanager
def local_server(config):
    """Start or reuse MLX; callers own their interface, this context owns its server."""
    import httpx

    address = urlsplit(config.base_url)
    host, port = address.hostname, address.port or 80
    health_url = config.base_url.rsplit("/v1", 1)[0] + "/health"
    environment = dict(os.environ, DASE_DEFAULT_PROVIDER="Apple MLX (local)",
                       MLX_MODEL=config.model, MLX_BASE_URL=config.base_url,
                       PYTHONUNBUFFERED="1")
    server = None
    try:
        with httpx.Client(timeout=2.0, trust_env=False, follow_redirects=False) as client:
            if server_ready(client, health_url):
                print(f"Using the existing local server at {config.base_url}.", flush=True)
            else:
                try:
                    with socket.create_connection((host, port), timeout=1):
                        raise RuntimeError(
                            f"Port {port} is occupied by an unavailable or incompatible server. "
                            "Stop it or change MLX_BASE_URL in .env."
                        )
                except OSError:
                    pass
                if find_spec("mlx_lm") is None:
                    raise RuntimeError(
                        "MLX-LM is missing. Install it once with:\n"
                        f'  "{sys.executable}" -m pip install "mlx-lm==0.32.2"'
                    )
                command = [sys.executable, "-m", "mlx_lm.server", "--model", config.model,
                           "--host", host, "--port", str(port),
                           "--max-tokens", str(config.max_tokens),
                           "--temp", str(config.temperature), "--top-p", str(config.top_p),
                           "--top-k", "20", "--prompt-cache-size", "1",
                           "--prefill-step-size", "512",
                           "--chat-template-args", '{"enable_thinking":false}']
                print(f"Starting MLX: {config.model}", flush=True)
                server = subprocess.Popen(command, cwd=ROOT, env=environment)
                wait_for_server(server, client, health_url)
        yield environment
    finally:
        if server is not None:
            print("Stopping the MLX server started by this launcher.", flush=True)
            stop_process(server)


def run_local(config):
    gui = None
    with local_server(config) as environment:
        try:
            print("Opening DASE with Apple MLX selected. First inference may download/load the model.",
                  flush=True)
            gui = subprocess.Popen([sys.executable, "-m", "dase"], cwd=ROOT, env=environment)
            return gui.wait()
        finally:
            stop_process(gui)


def main():
    # Editor Play may use a global interpreter. Prefer this repo's existing .venv.
    venv = ROOT / ".venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if python.is_file() and Path(sys.prefix).resolve() != venv.resolve():
        return subprocess.call([str(python), str(Path(__file__).resolve())], cwd=ROOT)
    try:
        from dotenv import load_dotenv
        from dase.paths import ENV_PATH
        from dase.providers.mlx import MLXConfig

        load_dotenv(ENV_PATH)
        return run_local(MLXConfig.from_env())
    except KeyboardInterrupt:
        print("DASE stopped.")
        return 130
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"Could not launch DASE: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
