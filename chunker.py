"""
Splits a source video into fixed-length chunks using ffmpeg (stream copy
where possible for speed, but we re-encode here because downstream steps
need frame-accurate cuts and consistent keyframes for the crop/caption pass).
"""
import json
import math
import os
import subprocess

import config


def get_duration_sec(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def plan_chunks(duration: float, clip_len: float, overlap: float):
    """
    Returns a list of (start, end) tuples in seconds.
    Full-length chunks are always kept; only a short trailing chunk
    (the last one, if truncated by the end of the video) is dropped
    when it's shorter than config.MIN_LAST_CLIP_SEC.
    """
    chunks = []
    step = clip_len - overlap
    if step <= 0:
        raise ValueError("CLIP_OVERLAP_SEC must be smaller than CLIP_LENGTH_SEC")

    start = 0.0
    while start < duration:
        end = min(start + clip_len, duration)
        is_full_length = (end - start) >= (clip_len - 1e-6)
        is_trailing_chunk = end >= duration - 1e-6
        if is_full_length or not is_trailing_chunk or (end - start) >= config.MIN_LAST_CLIP_SEC:
            chunks.append((start, end))
        start += step
    return chunks


def extract_chunk(source_path: str, start: float, end: float, out_path: str):
    """
    Cuts [start, end) from source_path into out_path.
    Re-encodes so every chunk starts on a clean keyframe (avoids the
    'first second is frozen/black' artifact you get from stream-copy cuts).
    """
    duration = end - start
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-i", source_path,
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", config.VIDEO_PRESET, "-crf", str(config.VIDEO_CRF),
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        out_path,
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)


def split_into_chunks(source_path: str, work_dir: str) -> list:
    """
    Returns list of dicts: {path, start, end, index}
    """
    duration = get_duration_sec(source_path)
    chunk_plan = plan_chunks(duration, config.CLIP_LENGTH_SEC, config.CLIP_OVERLAP_SEC)

    if not chunk_plan:
        raise RuntimeError(
            f"Source is only {duration:.1f}s long and produced zero usable chunks "
            f"at CLIP_LENGTH_SEC={config.CLIP_LENGTH_SEC}s. Try a shorter --clip-length."
        )

    chunks_dir = os.path.join(work_dir, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    results = []
    total = len(chunk_plan)
    for i, (start, end) in enumerate(chunk_plan, start=1):
        out_path = os.path.join(chunks_dir, f"chunk_{i:03d}.mp4")
        print(f"[chunk] {i}/{total}  {start:.1f}s -> {end:.1f}s")
        extract_chunk(source_path, start, end, out_path)
        results.append({"path": out_path, "start": start, "end": end, "index": i})

    return results
