"""One entry point: isolated dependencies, local API, native window, cleanup."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
FRONT = ROOT / 'FRONT'
BACK = ROOT / 'BACKEND'
DATA = FRONT / '.desktop-data'


def python_in(folder):
    return folder / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def ensure_environment(folder, requirements, imports):
    python = python_in(folder)
    if not python.exists():
        print(f'Подготовка Python: {folder.name}', flush=True)
        subprocess.run([sys.executable, '-m', 'venv', str(folder)], check=True)
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = folder / '.requirements-hash'
    probe = subprocess.run([str(python), '-c', imports], capture_output=True)
    if probe.returncode or not marker.exists() or marker.read_text() != fingerprint:
        print('Установка зависимостей. Интернет нужен только для первого запуска.', flush=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(requirements)], check=True)
        marker.write_text(fingerprint)
    return python


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main():
    if sys.version_info < (3, 10):
        raise RuntimeError('Нужен Python 3.10 или новее.')
    DATA.mkdir(exist_ok=True)
    with (DATA / 'desktop.lock').open('a+') as lock:
        # Hold the lock for the application's entire life; never reuse arbitrary ports/PIDs.
        if os.name != 'nt':
            import fcntl
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print('Приложение уже запущено. Найдите окно ALEM PROTOCOL.', flush=True)
                return
        front_python = ensure_environment(FRONT / '.desktop-env', FRONT / 'python' / 'requirements.txt',
                                           'import importlib.metadata as m; assert m.version("PySide6")=="6.8.3"; import httpx')
        back_python = ensure_environment(BACK / '.venv', BACK / 'requirements.txt', 'import fastapi, sqlalchemy, reportlab, docx')
        port = free_port()
        url = f'http://127.0.0.1:{port}'
        api_process = gui_process = None
        with (DATA / 'backend.log').open('ab') as backend_log, (DATA / 'desktop.log').open('ab') as desktop_log:
            try:
                api_process = subprocess.Popen([str(back_python), '-m', 'uvicorn', 'app.main:app',
                                                '--host', '127.0.0.1', '--port', str(port)],
                                               cwd=BACK, stdout=backend_log, stderr=backend_log)
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                for _ in range(100):
                    if api_process.poll() is not None:
                        raise RuntimeError(f'Backend не запустился. Журнал: {DATA / "backend.log"}')
                    try:
                        with opener.open(url + '/health', timeout=.8) as response:
                            health = json.load(response)
                        if health.get('status') == 'ok' and 'mock_mode' in health:
                            break
                    except (OSError, ValueError):
                        time.sleep(.2)
                else:
                    raise RuntimeError('Backend не ответил за 30 секунд.')
                print('Открываю окно ALEM PROTOCOL. Закройте окно приложения для завершения.', flush=True)
                gui_process = subprocess.Popen([str(front_python), str(FRONT / 'python' / 'desktop.py'), '--api', url],
                                               cwd=ROOT, stdout=desktop_log, stderr=desktop_log)
                result = gui_process.wait()
                if result:
                    raise RuntimeError(f'Окно не удалось запустить. Журнал: {DATA / "desktop.log"}')
            finally:
                stop(gui_process)
                stop(api_process)


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        print(f'\nОшибка запуска: {exc}', file=sys.stderr, flush=True)
        raise SystemExit(1)
