"""
Small ffmpeg helpers: pull audio out for transcription, and burn an
.ass subtitle file onto a video (hardcoded captions).
"""
import subprocess


def extract_audio(video_path: str, out_wav_path: str):
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        out_wav_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr[-2000:])
        raise RuntimeError(f"Audio extraction failed for {video_path}")


def burn_captions(video_path: str, ass_path: str, out_path: str, crf: int, preset: str):
    # ffmpeg's ass filter needs the path escaped for filter syntax
    escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"ass={escaped_ass}",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-c:a", "copy",
        "-movflags", "+faststart",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr[-3000:])
        raise RuntimeError(f"Caption burn-in failed for {video_path}")
