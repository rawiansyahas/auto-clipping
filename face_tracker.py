"""
Dynamic face tracking for smart vertical cropping.

Strategy:
- Run Haar cascade face detection every N frames (cheap, no GPU needed).
- Between detections, hold the last known position.
- Smooth the crop center with an exponential moving average so the pan
  looks deliberate instead of jittery.
- If no face is ever found, fall back to a static center crop.

Output: a list of (frame_index, crop_center_x, crop_center_y) keyframes
that crop_and_render.py interpolates between.
"""
import cv2

import config


def _load_cascade():
    path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(path)
    if cascade.empty():
        raise RuntimeError(f"Could not load face cascade from {path}")
    return cascade


def _detect_largest_face(cascade, gray_frame):
    faces = cascade.detectMultiScale(
        gray_frame,
        scaleFactor=config.FACE_CASCADE_SCALE_FACTOR,
        minNeighbors=config.FACE_CASCADE_MIN_NEIGHBORS,
        minSize=config.FACE_MIN_SIZE,
    )
    if len(faces) == 0:
        return None
    # pick the largest face (most likely the main speaker)
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return (x + w / 2, y + h / 2)  # center point


def track_faces(video_path: str):
    """
    Returns:
        keyframes: list of (frame_idx, center_x, center_y) in source pixel coords
        frame_w, frame_h: source dimensions
        fps: source fps
        found_any_face: bool
    """
    cascade = _load_cascade()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video for face tracking: {video_path}")

    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or config.OUTPUT_FPS
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    last_center = (frame_w / 2, frame_h / 2)  # default: dead center
    smoothed_center = last_center
    found_any_face = False
    keyframes = []

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % config.FACE_DETECT_EVERY_N_FRAMES == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected = _detect_largest_face(cascade, gray)
            if detected is not None:
                last_center = detected
                found_any_face = True
            elif config.NO_FACE_FALLBACK == "center":
                last_center = (frame_w / 2, frame_h / 2)
            # else "last_known": keep previous last_center as-is

        # exponential smoothing toward the current target
        a = config.FACE_SMOOTHING_ALPHA
        smoothed_center = (
            smoothed_center[0] + a * (last_center[0] - smoothed_center[0]),
            smoothed_center[1] + a * (last_center[1] - smoothed_center[1]),
        )

        keyframes.append((frame_idx, smoothed_center[0], smoothed_center[1]))
        frame_idx += 1

    cap.release()

    if not found_any_face:
        print(f"[face-track] no faces detected in {video_path}, using center crop")

    return {
        "keyframes": keyframes,
        "frame_w": frame_w,
        "frame_h": frame_h,
        "fps": fps,
        "total_frames": total_frames,
        "found_any_face": found_any_face,
    }
