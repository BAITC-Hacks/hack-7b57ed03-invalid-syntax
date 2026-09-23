"""One-command launcher for the Aqylman hackathon MVP."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import socket
import sqlite3
import sys
import threading
import time
import urllib.request
import webbrowser

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "BACKEND"
RUNTIME_DIR = ROOT_DIR / "runtime"
HOST = "127.0.0.1"
PORT = 8000
APP_URL = f"http://{HOST}:{PORT}/"


class LaunchError(RuntimeError):
    pass


class ProcessLock:
    """Cross-platform, non-destructive single-instance lock."""

    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def __enter__(self):
        self.handle = self.path.open("a+b")
        if self.path.stat().st_size == 0:
            self.handle.write(b"0")
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            self.handle.close()
            raise LaunchError("Приложение уже запущено. Откройте http://127.0.0.1:8000/") from exc
        return self

    def __exit__(self, *_):
        if self.handle is None:
            return
        try:
            self.handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle, fcntl.LOCK_UN)
        finally:
            self.handle.close()


def _port_available() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((HOST, PORT))
            return True
        except OSError:
            return False


def check_environment() -> None:
    print("[CHECK] Проверка backend", flush=True)
    if sys.version_info < (3, 10):
        raise LaunchError("Требуется Python 3.10 или новее.")
    required_files = (
        BACKEND_DIR / "requirements.txt",
        BACKEND_DIR / "app" / "main.py",
        BACKEND_DIR / "app" / "web" / "index.html",
    )
    for path in required_files:
        if not path.is_file():
            raise LaunchError(f"Не найден обязательный файл: {path}")
    missing = [
        package for package in ("fastapi", "uvicorn", "sqlalchemy", "pydantic_settings", "docx", "reportlab", "openai")
        if importlib.util.find_spec(package) is None
    ]
    if missing:
        raise LaunchError(
            "Не установлены Python-зависимости: " + ", ".join(missing) + "\n"
            f'Выполните: "{sys.executable}" -m pip install -r "{BACKEND_DIR / "requirements.txt"}"'
        )
    try:
        with sqlite3.connect(":memory:") as connection:
            connection.execute("select 1")
    except sqlite3.Error as exc:
        raise LaunchError("SQLite недоступен в текущем Python.") from exc
    for folder in (RUNTIME_DIR, BACKEND_DIR / "uploads", BACKEND_DIR / "exports"):
        folder.mkdir(parents=True, exist_ok=True)
        marker = folder / ".write-test"
        try:
            marker.write_text("ok", encoding="utf-8")
            marker.unlink()
        except OSError as exc:
            raise LaunchError(f"Нет доступа на запись: {folder}") from exc
    if not _port_available():
        raise LaunchError(f"Порт {PORT} уже занят. Возможно, Aqylman уже запущен: {APP_URL}")


def _announce_when_ready(mode: str) -> None:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            with opener.open(APP_URL + "health", timeout=1.2) as response:
                if response.status == 200:
                    label = "REAL AI" if mode == "openai" else ("LOCAL AI" if mode == "local" else "DEMO MODE")
                    print(
                        "[READY] Приложение работает\n"
                        f"Режим:   {label}\n"
                        f"Интерфейс: {APP_URL}\n"
                        f"Swagger:   {APP_URL}docs\n\n"
                        "Ctrl+C — остановить приложение",
                        flush=True,
                    )
                    if os.environ.get("ALEM_NO_BROWSER") != "1":
                        webbrowser.open(APP_URL)
                    return
        except OSError:
            time.sleep(0.25)
    print(f"[WARNING] Сервер запущен, но проверка {APP_URL} не завершилась вовремя.", file=sys.stderr)


def main() -> int:
    print("[START] Запуск Aqylman MVP", flush=True)
    RUNTIME_DIR.mkdir(exist_ok=True)
    with ProcessLock(RUNTIME_DIR / "alem.lock"):
        check_environment()
        sys.path.insert(0, str(BACKEND_DIR))
        os.chdir(BACKEND_DIR)

        import uvicorn
        from app.core.config import settings
        from app.main import app

        if settings.ai_mode == "demo":
            print("[WARNING] OPENAI_API_KEY не настроен. Используется DEMO MODE.", flush=True)
        print("[BACKEND] Запуск FastAPI...", flush=True)
        threading.Thread(
            target=_announce_when_ready,
            args=(settings.ai_mode,),
            name="browser-opener",
            daemon=True,
        ).start()
        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    print("[STOP] Aqylman остановлен", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[STOP] Остановлено пользователем", file=sys.stderr)
        raise SystemExit(130)
    except LaunchError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
