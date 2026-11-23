"""Set up and run the Windows portfolio demo in the foreground."""

import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time
import venv


ROOT = Path(__file__).resolve().parent
ADDRESS = "127.0.0.1:8001"


def serve_demo() -> None:
    import django
    from django.core.management import call_command, execute_from_command_line

    django.setup()
    call_command("migrate", interactive=False, verbosity=0)
    seeded = Path(os.environ["LMM_DATA_DIR"]) / ".demo-seeded"
    if not seeded.exists():
        call_command("seed_demo")
        seeded.touch()

    print(f"Open http://{ADDRESS}/ in your browser.", flush=True)
    print("Press Ctrl+C to stop the demo.", flush=True)
    execute_from_command_line(["manage.py", "runserver", ADDRESS, "--noreload"])


def main() -> int:
    demo_home = Path(os.environ["LOCALAPPDATA"]) / "LocalMediaFileManager"
    demo_venv = demo_home / "venv"
    python = demo_venv / "Scripts" / "python.exe"
    if not python.is_file():
        print("Creating the demo environment...", flush=True)
        venv.create(demo_venv, with_pip=True)

    requirements = (ROOT / "requirements.txt").read_bytes()
    installed = demo_venv / "demo-requirements.txt"
    if not installed.is_file() or installed.read_bytes() != requirements:
        print("Installing the demo dependencies...", flush=True)
        subprocess.run(
            [str(python), "-m", "pip", "--disable-pip-version-check", "install", "-r", "requirements.txt"],
            cwd=ROOT,
            check=True,
        )
        installed.write_bytes(requirements)

    env = os.environ.copy()
    env.update(
        DJANGO_SETTINGS_MODULE="fanart_manager.settings",
        DJANGO_SECRET_KEY=secrets.token_urlsafe(48),
        DJANGO_DEBUG="1",
        LMM_DATA_DIR=str(demo_home / "demo"),
        PYTHONDONTWRITEBYTECODE="1",
    )

    # The launcher owns shutdown. A separate process group keeps the server
    # from receiving the same Windows Ctrl+C while the launcher cleans up.
    with subprocess.Popen(
        [str(python), "-u", __file__, "--serve"],
        cwd=ROOT,
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    ) as server:
        try:
            while server.poll() is None:
                time.sleep(0.2)
            return server.returncode
        except KeyboardInterrupt:
            server.send_signal(signal.CTRL_BREAK_EVENT)
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            print("\nDemo stopped.", flush=True)
            return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--serve"]:
        signal.signal(signal.SIGBREAK, signal.default_int_handler)
        serve_demo()
    else:
        try:
            raise SystemExit(main())
        except KeyboardInterrupt:
            raise SystemExit(0)
        except (OSError, subprocess.CalledProcessError) as error:
            print(f"Could not start the demo: {error}", file=sys.stderr)
            raise SystemExit(1)
