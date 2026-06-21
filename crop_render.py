"""
Renders the 9:16 vertical video by applying a per-frame crop window
computed from face_tracker keyframes.

Approach: build an ffmpeg `sendcmd` script that updates the crop filter's
x/y position on (almost) every frame, matching the smoothed face-center
track. This gives a real pan, not just a static crop.
"""
import os
import subprocess

import config


def _compute_crop_window(frame_w, frame_h, out_w, out_h):
    """
    Given source dims and target aspect (9:16), compute the crop box
    size (crop_w, crop_h) that we'll slide around within the source frame.
    """
    target_aspect = out_w / out_h  # e.g. 1080/1920
    src_aspect = frame_w / frame_h

    if src_aspect > target_aspect:
        # source is wider than target -> crop width, keep full height
        crop_h = frame_h
        crop_w = int(round(crop_h * target_aspect))
    else:
        # source is taller/narrower -> crop height, keep full width
        crop_w = frame_w
        crop_h = int(round(crop_w / target_aspect))

    crop_w = min(crop_w, frame_w)
    crop_h = min(crop_h, frame_h)
    return crop_w, crop_h


def _build_sendcmd_script(keyframes, frame_w, frame_h, crop_w, crop_h, fps, path):
    """
    Writes an ffmpeg sendcmd file that moves the crop x/y over time to
    follow the tracked face center, clamped so the crop never leaves
    the source frame.
    """
    half_w, half_h = crop_w / 2, crop_h / 2
    lines = []
    # Throttle commands to ~6/sec; smoothing already happened per-frame in
    # face_tracker, so this keeps the script small without looking stepped.
    stride = max(1, int(round(fps / 6)))

    for frame_idx, cx, cy in keyframes[::stride]:
        t = frame_idx / fps
        x = cx - half_w
        y = cy - half_h
        x = max(0, min(x, frame_w - crop_w))
        y = max(0, min(y, frame_h - crop_h))
        lines.append(
            f"{t:.3f} crop x '{x:.1f}', crop y '{y:.1f}';"
        )

    with open(path, "w") as f:
        f.write("\n".join(lines))


def render_vertical_clip(chunk_path: str, tracking: dict, out_path: str, work_dir: str, tag: str):
    """
    Produces a 9:16 vertical version of chunk_path using the face
    tracking data, scaled to config.OUTPUT_WIDTH x OUTPUT_HEIGHT.
    """
    frame_w, frame_h = tracking["frame_w"], tracking["frame_h"]
    fps = tracking["fps"]
    crop_w, crop_h = _compute_crop_window(frame_w, frame_h, config.OUTPUT_WIDTH, config.OUTPUT_HEIGHT)

    sendcmd_path = os.path.join(work_dir, f"sendcmd_{tag}.txt")
    _build_sendcmd_script(tracking["keyframes"], frame_w, frame_h, crop_w, crop_h, fps, sendcmd_path)

    # initial crop position centered, sendcmd will override x/y over time
    init_x = max(0, (frame_w - crop_w) // 2)
    init_y = max(0, (frame_h - crop_h) // 2)

    filter_complex = (
        f"crop=w={crop_w}:h={crop_h}:x={init_x}:y={init_y},"
        f"sendcmd=f={sendcmd_path},"
        f"scale={config.OUTPUT_WIDTH}:{config.OUTPUT_HEIGHT}:flags=lanczos"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", chunk_path,
        "-filter_complex", filter_complex,
        "-r", str(config.OUTPUT_FPS),
        "-c:v", "libx264", "-preset", config.VIDEO_PRESET, "-crf", str(config.VIDEO_CRF),
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr[-3000:])
        raise RuntimeError(f"ffmpeg crop/render failed for {chunk_path}")
