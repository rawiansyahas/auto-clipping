"""
Handles getting a source video onto disk, whether it's already local
or needs to be downloaded from YouTube/Twitch/etc via yt-dlp.
"""
import os
import re
import subprocess
import sys

import config


def is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s.strip(), re.IGNORECASE))


def download_video(url: str, work_dir: str) -> str:
    """
    Downloads a video with yt-dlp, merged to a single mp4.
    Returns the local file path.
    """
    os.makedirs(work_dir, exist_ok=True)
    out_template = os.path.join(work_dir, "source.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
        "--merge-output-format", "mp4",
        "-o", out_template,
        "--no-playlist",
        url,
    ]
    print(f"[download] fetching {url} ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
        raise RuntimeError(
            f"yt-dlp failed (exit {result.returncode}). "
            f"Check the URL is reachable and the site is supported."
        )

    expected = os.path.join(work_dir, "source.mp4")
    if not os.path.exists(expected):
        # yt-dlp may have kept a different extension if mp4 mux failed
        candidates = [f for f in os.listdir(work_dir) if f.startswith("source.")]
        if not candidates:
            raise RuntimeError("Download finished but no output file was found.")
        expected = os.path.join(work_dir, candidates[0])

    print(f"[download] saved to {expected}")
    return expected


def resolve_source(source: str, work_dir: str) -> str:
    """
    source can be a local path or a URL. Returns a local file path
    ready for processing.
    """
    if is_url(source):
        return download_video(source, work_dir)

    if not os.path.exists(source):
        raise FileNotFoundError(f"Local file not found: {source}")
    return os.path.abspath(source)
