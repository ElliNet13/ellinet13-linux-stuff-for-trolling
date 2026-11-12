#!/usr/bin/env python3

import argparse
import hashlib
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================

DEFAULT_VIDEO_URL = "https://zipline.ellinet13.com/u/h800Hq.mp4"

BASE_DIR = Path(
    os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")
) / "ElliNet13FullscreenVideoPlayer"

VIDEO_CACHE_DIR = BASE_DIR / "Videos"
MPV_INPUT_CONF = BASE_DIR / "mpv-input.conf"

MPV_PROCESS: subprocess.Popen | None = None
IS_EXITING = False


# ==========================================
# ERRORS
# ==========================================

def fail(stage: str, message: str) -> None:
    print(
        f"ElliNet13 Fullscreen Video Player - Error\n"
        f"Stage: {stage}\n\n{message}",
        file=sys.stderr,
    )
    raise SystemExit(1)


# ==========================================
# ARGUMENT PARSING
# ==========================================

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ElliNet13 Fullscreen Video Player"
    )

    parser.add_argument(
        "url",
        nargs="?",
        default=DEFAULT_VIDEO_URL,
        help="Video URL to play",
    )

    parser.add_argument(
        "--no-escape",
        action="store_true",
        help="Disable Escape as an exit key (use Ctrl+Alt+C instead)",
    )

    return parser.parse_args()


# ==========================================
# DEPENDENCIES
# ==========================================

def check_dependencies() -> None:
    for dependency in ("mpv", "curl"):
        if shutil.which(dependency) is None:
            fail(
                "Dependency verification",
                f"{dependency} is not installed.\n"
                "Install using: sudo apt install mpv curl",
            )


# ==========================================
# DIRECTORIES
# ==========================================

def initialize_directories() -> None:
    try:
        VIDEO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        fail("Directory initialization", str(error))


# ==========================================
# GENERATE CACHE KEY
# ==========================================

def get_url_hash(url: str) -> str:
    return hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()


# ==========================================
# DOWNLOAD VIDEO
# ==========================================

def download_video(url: str, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size > 0:
        print("Using cached video.")
        return

    print("Downloading video...")
    print(url)

    temporary_file = destination.with_suffix(".part")

    try:
        temporary_file.unlink(missing_ok=True)

        result = subprocess.run(
            [
                "curl",
                "--fail",
                "--location",
                "--show-error",
                "--progress-bar",
                "--retry",
                "3",
                "--output",
                str(temporary_file),
                url,
            ],
            check=False,
        )

        if result.returncode != 0:
            fail("Video download", "Could not download video.")

        if not temporary_file.exists() or temporary_file.stat().st_size == 0:
            fail("Video download", "Downloaded file is empty.")

        temporary_file.replace(destination)

    except OSError as error:
        fail("Video download", str(error))

    finally:
        temporary_file.unlink(missing_ok=True)


# ==========================================
# GENERATE MPV INPUT CONFIG
# ==========================================

def generate_mpv_config(no_escape: bool) -> None:
    if no_escape:
        config = """
Ctrl+Alt+c quit
Alt+F4 ignore
"""
    else:
        config = """
ESC quit
Alt+F4 ignore
"""

    try:
        MPV_INPUT_CONF.write_text(
            config.strip() + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        fail("MPV configuration", str(error))


# ==========================================
# CLEANUP
# ==========================================

def cleanup() -> None:
    global MPV_PROCESS, IS_EXITING

    if IS_EXITING:
        return

    IS_EXITING = True

    if MPV_PROCESS is None:
        return

    if MPV_PROCESS.poll() is None:
        try:
            os.killpg(MPV_PROCESS.pid, signal.SIGTERM)
            MPV_PROCESS.wait(timeout=5)

        except subprocess.TimeoutExpired:
            try:
                os.killpg(MPV_PROCESS.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

            MPV_PROCESS.wait()

        except ProcessLookupError:
            pass

    MPV_PROCESS = None


# ==========================================
# SIGNAL HANDLING
# ==========================================

def handle_signal(signum: int, frame: object) -> None:
    cleanup()
    raise SystemExit(128 + signum)


# ==========================================
# START MPV
# ==========================================

def start_mpv(video_path: Path) -> None:
    global MPV_PROCESS

    command = [
        "mpv",
        "--no-terminal",
        "--no-config",
        "--force-window=yes",
        "--fullscreen=yes",
        "--ontop=yes",
        "--loop-file=no",
        "--keep-open=no",
        "--idle=no",
        "--no-osc",
        "--no-osd-bar",
        "--no-border",
        "--no-input-default-bindings",
        "--input-vo-keyboard=yes",
        f"--input-conf={MPV_INPUT_CONF}",
        "--title=ElliNet13FullscreenVideoPlayer",
        str(video_path),
    ]

    print("Starting fullscreen video player...")

    try:
        MPV_PROCESS = subprocess.Popen(
            command,
            start_new_session=True,
        )
    except OSError as error:
        fail("MPV launch", str(error))

    try:
        MPV_PROCESS.wait()
    except KeyboardInterrupt:
        cleanup()
        raise SystemExit(130)
    finally:
        MPV_PROCESS = None


# ==========================================
# MAIN
# ==========================================

def main() -> None:
    args = parse_arguments()

    check_dependencies()
    initialize_directories()

    url_hash = get_url_hash(args.url)
    video_path = VIDEO_CACHE_DIR / f"{url_hash}.media"

    download_video(args.url, video_path)
    generate_mpv_config(args.no_escape)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        start_mpv(video_path)
    finally:
        cleanup()


# ==========================================
# ENTRY POINT
# ==========================================

if __name__ == "__main__":
    main()
