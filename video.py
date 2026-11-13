#!/usr/bin/env python3
import argparse
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request

DEFAULT_VIDEO_URL = "https://zipline.ellinet13.com/u/h800Hq.mp4"

def fail(stage, message):
    print(f"[ERROR] Stage: {stage}\n{message}", file=sys.stderr)
    sys.exit(1)

def get_url_hash(url):
    return hashlib.sha256(url.encode('utf-8')).hexdigest()

def download_file(url, dest_path):
    try:
        print(f"Downloading video from: {url}")
        urllib.request.urlretrieve(url, dest_path)
    except Exception as e:
        fail("Video download", str(e))

def main():
    parser = argparse.ArgumentParser(description="ElliNet13 Fullscreen Video Player for Linux")
    parser.add_argument(
        "url", 
        nargs="?", 
        default=DEFAULT_VIDEO_URL, 
        help="URL of the video to play"
    )
    parser.add_argument(
        "--no-escape", 
        action="store_true", 
        help="Disable exiting via the Escape key"
    )
    args = parser.parse_args()

    # 1. Verify MPV is installed
    mpv_path = shutil.which("mpv")
    if not mpv_path:
        fail(
            "MPV verification", 
            "mpv is not installed or not found in PATH.\n"
            "Install it via your package manager, e.g.:\n"
            "  - Ubuntu/Debian: sudo apt install mpv\n"
            "  - Fedora/RHEL:   sudo dnf install mpv\n"
            "  - Arch Linux:    sudo pacman -S mpv"
        )

    # 2. Setup Cache Directories
    base_dir = pathlib.Path.home() / ".cache" / "ElliNet13FullscreenVideoPlayer"
    video_cache_dir = base_dir / "videos"
    video_cache_dir.mkdir(parents=True, exist_ok=True)

    # 3. Generate Caching Path via SHA-256 Hash
    url_hash = get_url_hash(args.url)
    video_path = video_cache_dir / f"{url_hash}.mp4"

    # 4. Download Video if Missing or Corrupted
    if not video_path.exists() or video_path.stat().st_size < 1024:
        if video_path.exists():
            video_path.unlink()
        download_file(args.url, video_path)
        if not video_path.exists() or video_path.stat().st_size < 1024:
            fail("Video validation", "Downloaded video file is invalid or too small.")

    # 5. Build MPV Arguments
    mpv_args = [
        mpv_path,
        "--no-terminal",
        "--no-config",
        "--fullscreen",
        "--ontop",
        "--loop-file=no",
        "--keep-open=no",
        "--idle=no",
        "--no-osc",
        "--no-border",
        "--title=ElliNet13FullscreenVideoPlayer",
        str(video_path)
    ]

    # Handle --no-escape by creating a temporary mpv input config that ignores ESC
    temp_input_file = None
    if args.no_escape:
        fd, temp_input_path = tempfile.mkstemp(prefix="mpv_input_", suffix=".conf")
        os.close(fd)
        with open(temp_input_path, "w") as f:
            f.write("ESC ignore\n")
        temp_input_file = pathlib.Path(temp_input_path)
        mpv_args.extend(["--input-conf", str(temp_input_file)])

    # 6. Run MPV
    try:
        print("Launching player...")
        subprocess.run(mpv_args, check=True)
    except subprocess.CalledProcessError as e:
        fail("MPV execution", f"mpv exited with error code {e.returncode}")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Cleanup temporary config if created
        if temp_input_file and temp_input_file.exists():
            temp_input_file.unlink()

if __name__ == "__main__":
    main()
