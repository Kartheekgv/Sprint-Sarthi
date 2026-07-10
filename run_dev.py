"""
Sprint Sarthi one-command developer runner.

Works from Windows Git Bash, Windows PowerShell/CMD, Linux, and macOS.
It creates the virtual environment, installs backend packages, prepares env files,
ingests the knowledge base, then starts FastAPI and React/Vite together.

Windows Git Bash command:
    bash run-dev-gitbash.sh

On Windows, if npm is missing, this runner tries to install Node.js LTS using
winget automatically, then continues with npm install and app startup.
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, Optional

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
VENV_DIR = ROOT_DIR / ".venv"


def log(message: str) -> None:
    print(f"[sprint-sarthi] {message}", flush=True)


def run(command: Iterable[str], cwd: Path = ROOT_DIR, env: Optional[dict] = None, check: bool = True) -> int:
    command_list = [str(item) for item in command]
    log("Running: " + " ".join(command_list))
    completed = subprocess.run(command_list, cwd=str(cwd), env=env)
    if check and completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed.returncode


def find_system_python() -> list[str]:
    # Prefer the Python that is currently executing this runner.
    if sys.executable:
        return [sys.executable]

    for candidate in ("python", "python3"):
        path = shutil.which(candidate)
        if path:
            return [path]

    py_launcher = shutil.which("py")
    if py_launcher:
        return [py_launcher, "-3"]

    raise SystemExit("Python was not found. Install Python 3.10+ and try again.")


def venv_python_path() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def create_venv() -> Path:
    py_path = venv_python_path()
    if py_path.exists():
        log(f"Using existing virtual environment: {VENV_DIR}")
        return py_path

    log("Creating virtual environment...")
    run([*find_system_python(), "-m", "venv", str(VENV_DIR)])

    py_path = venv_python_path()
    if not py_path.exists():
        raise SystemExit(f"Virtual environment was created, but Python was not found at: {py_path}")
    return py_path


def copy_if_missing(source: Path, target: Path) -> None:
    if target.exists():
        return
    if source.exists():
        shutil.copyfile(source, target)
        log(f"Created {target.relative_to(ROOT_DIR)} from {source.relative_to(ROOT_DIR)}")


def prepend_path(directory: Path) -> None:
    if not directory.exists():
        return
    directory_text = str(directory)
    existing = os.environ.get("PATH", "")
    parts = existing.split(os.pathsep) if existing else []
    if directory_text not in parts:
        os.environ["PATH"] = directory_text + os.pathsep + existing
        log(f"Added to PATH for this run: {directory_text}")


def find_from_windows_common_paths(exe_names: list[str]) -> Optional[str]:
    if os.name != "nt":
        return None

    candidate_dirs: list[Path] = []
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(env_name)
        if base:
            candidate_dirs.append(Path(base) / "nodejs")

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidate_dirs.extend(
            [
                Path(local_app_data) / "Programs" / "nodejs",
                Path(local_app_data) / "Microsoft" / "WindowsApps",
            ]
        )

    for directory in candidate_dirs:
        for exe_name in exe_names:
            candidate = directory / exe_name
            if candidate.exists():
                prepend_path(directory)
                return str(candidate)
    return None


def find_winget() -> Optional[str]:
    for name in ("winget", "winget.exe"):
        found = shutil.which(name)
        if found:
            return found

    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidate = Path(local_app_data) / "Microsoft" / "WindowsApps" / "winget.exe"
            if candidate.exists():
                return str(candidate)
    return None


def find_npm() -> Optional[str]:
    # Git Bash usually resolves npm.cmd correctly after Node.js is installed.
    for name in ("npm", "npm.cmd", "npm.exe"):
        found = shutil.which(name)
        if found:
            return found
    return find_from_windows_common_paths(["npm.cmd", "npm.exe", "npm"])


def ensure_npm(auto_install_node: bool) -> str:
    npm = find_npm()
    if npm:
        log(f"Using npm: {npm}")
        return npm

    if os.name == "nt" and auto_install_node:
        log("npm was not found. Trying to install Node.js LTS automatically using winget...")
        winget = find_winget()
        if not winget:
            raise SystemExit(
                "npm was not found and winget was not found.\n"
                "Install Node.js LTS manually, then reopen Git Bash and run: bash run-dev-gitbash.sh"
            )

        result = run(
            [
                winget,
                "install",
                "--id",
                "OpenJS.NodeJS.LTS",
                "-e",
                "--accept-source-agreements",
                "--accept-package-agreements",
            ],
            check=False,
        )

        if result != 0:
            raise SystemExit(
                "Automatic Node.js installation failed.\n"
                "Install Node.js LTS manually, then reopen Git Bash and run: bash run-dev-gitbash.sh\n"
                "You can still run only the backend with: bash run-dev-gitbash.sh --backend-only"
            )

        # The current terminal may not receive the new PATH automatically.
        # Search common installation directories and add Node.js to PATH for this process.
        time.sleep(2)
        npm = find_npm()
        if npm:
            log(f"Node.js installation completed. Using npm: {npm}")
            return npm

        raise SystemExit(
            "Node.js was installed, but npm was not visible in this Git Bash session.\n"
            "Close Git Bash, open it again inside the project folder, and run: bash run-dev-gitbash.sh"
        )

    raise SystemExit(
        "npm was not found. Install Node.js LTS, then reopen the terminal and run this command again.\n"
        "You can still run only the backend with: bash run-dev-gitbash.sh --backend-only"
    )


def install_backend_dependencies(py_path: Path, skip_install: bool) -> None:
    if skip_install:
        log("Skipping backend dependency installation.")
        return

    run([str(py_path), "-m", "pip", "install", "--upgrade", "pip"])

    requirements = ROOT_DIR / "requirements.txt"
    lite_requirements = ROOT_DIR / "requirements-lite.txt"

    result = run([str(py_path), "-m", "pip", "install", "-r", str(requirements)], check=False)
    if result == 0:
        return

    if lite_requirements.exists():
        log("Full requirements installation failed. Trying lightweight demo requirements.")
        log("The app will still run because RAG has a local JSON fallback when ChromaDB is unavailable.")
        run([str(py_path), "-m", "pip", "install", "-r", str(lite_requirements)])
    else:
        raise SystemExit(result)


def install_frontend_dependencies(skip_install: bool, auto_install_node: bool) -> None:
    if skip_install:
        log("Skipping frontend dependency installation.")
        return

    npm = ensure_npm(auto_install_node)

    package_json = FRONTEND_DIR / "package.json"
    if not package_json.exists():
        raise SystemExit(f"Frontend package.json not found at {package_json}")

    # npm install is safe to run again and keeps this command simple for demo users.
    run([npm, "install"], cwd=FRONTEND_DIR)


def ingest_knowledge_base(py_path: Path, no_ingest: bool) -> None:
    if no_ingest:
        log("Skipping knowledge base ingestion.")
        return

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR)
    run([str(py_path), "-m", "rag.ingest"], env=env)


def start_process(command: list[str], cwd: Path, env: dict) -> subprocess.Popen:
    log("Starting: " + " ".join(command))
    return subprocess.Popen(command, cwd=str(cwd), env=env)


def terminate_process(process: Optional[subprocess.Popen], name: str) -> None:
    if process is None or process.poll() is not None:
        return
    log(f"Stopping {name}...")
    try:
        process.terminate()
        process.wait(timeout=8)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def start_apps(py_path: Path, backend_only: bool, frontend_only: bool, auto_install_node: bool) -> None:
    npm: Optional[str] = None
    if not backend_only:
        npm = ensure_npm(auto_install_node)

    backend_process: Optional[subprocess.Popen] = None
    frontend_process: Optional[subprocess.Popen] = None

    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = str(ROOT_DIR)
    backend_env.setdefault("AI_PROVIDER", "mock")
    backend_env.setdefault("JIRA_MOCK_MODE", "true")

    frontend_env = os.environ.copy()
    frontend_env.setdefault("VITE_API_BASE_URL", "http://127.0.0.1:8000")

    try:
        if not frontend_only:
            backend_process = start_process(
                [
                    str(py_path),
                    "-m",
                    "uvicorn",
                    "backend.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                cwd=ROOT_DIR,
                env=backend_env,
            )

        if not backend_only:
            if not npm:
                raise SystemExit("npm was not found. Install Node.js, then run this command again.")
            frontend_process = start_process([npm, "run", "dev"], cwd=FRONTEND_DIR, env=frontend_env)

        log("Backend API:  http://127.0.0.1:8000/docs")
        log("Frontend UI:  http://localhost:5173")
        log("Press Ctrl+C to stop both servers.")

        while True:
            if backend_process and backend_process.poll() is not None:
                raise SystemExit(backend_process.returncode or 0)
            if frontend_process and frontend_process.poll() is not None:
                raise SystemExit(frontend_process.returncode or 0)
            time.sleep(1)

    except KeyboardInterrupt:
        log("Ctrl+C received.")
    finally:
        terminate_process(frontend_process, "frontend")
        terminate_process(backend_process, "backend")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Sprint Sarthi with one command.")
    parser.add_argument("--setup-only", action="store_true", help="Install dependencies and prepare files, then exit.")
    parser.add_argument("--skip-install", action="store_true", help="Skip pip install and npm install.")
    parser.add_argument("--no-ingest", action="store_true", help="Skip RAG knowledge base ingestion.")
    parser.add_argument("--skip-ingest", dest="no_ingest", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--backend-only", action="store_true", help="Start only FastAPI backend.")
    parser.add_argument("--frontend-only", action="store_true", help="Start only React frontend.")
    parser.add_argument(
        "--no-auto-install-node",
        action="store_true",
        help="Do not try to install Node.js automatically on Windows when npm is missing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.backend_only and args.frontend_only:
        raise SystemExit("Use either --backend-only or --frontend-only, not both.")

    auto_install_node = not args.no_auto_install_node

    log(f"Project root: {ROOT_DIR}")

    py_path = create_venv()

    copy_if_missing(ROOT_DIR / ".env.example", ROOT_DIR / ".env")
    copy_if_missing(FRONTEND_DIR / ".env.example", FRONTEND_DIR / ".env")

    if not args.frontend_only:
        install_backend_dependencies(py_path, args.skip_install)
        ingest_knowledge_base(py_path, args.no_ingest)

    if not args.backend_only:
        install_frontend_dependencies(args.skip_install, auto_install_node)

    if args.setup_only:
        log("Setup completed. Start the app with: python run_dev.py --skip-install")
        return

    start_apps(
        py_path,
        backend_only=args.backend_only,
        frontend_only=args.frontend_only,
        auto_install_node=auto_install_node,
    )


if __name__ == "__main__":
    # Make Ctrl+C behavior predictable on Windows.
    try:
        signal.signal(signal.SIGINT, signal.default_int_handler)
    except Exception:
        pass
    main()
