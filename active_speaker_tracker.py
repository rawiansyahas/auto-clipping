"""
Active-speaker tracking: detects all faces in frame, estimates which one
is talking by measuring mouth-region motion over a re-evaluation window,
and produces a HARD-CUT crop path (no easing) that snaps to the speaker.

Strategy per window (config.SPEAKER_REEVAL_INTERVAL_SEC long):
  1. Sample several frames across the window.
  2. Detect all faces in each sampled frame (Haar face cascade).
  3. Cluster detections into stable face "slots" by position (faces don't
     teleport within a couple seconds, so simple nearest-position matching
     is enough -- no need for a full tracker/re-ID).
  4. For each face slot, crop its mouth region (lower-half of face box,
     using the bundled "smile" cascade as a coarse mouth detector) and
     measure how much that region changes frame-to-frame.
  5. The face with the most mouth motion wins the window, *if* it clearly
     beats the runner-up (config.SWITCH_CONFIDENCE_MARGIN) -- otherwise
     keep whoever was talking in the previous window, to avoid flicker on
     ambiguous/close calls.
  6. Emit one hard-cut keyframe at the start of the window: the crop jumps
     straight to the winner's position and holds there (no interpolation)
     until the next window's decision.

Output format matches the smooth-pan tracker: a flat list of
(frame_idx, center_x, center_y) keyframes that crop_render.py already
knows how to consume -- just with step changes instead of eased ones.
"""
import cv2
import numpy as np

import config


def _load_cascades():
    face_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    mouth_path = cv2.data.haarcascades + "haarcascade_smile.xml"
    face_cascade = cv2.CascadeClassifier(face_path)
    mouth_cascade = cv2.CascadeClassifier(mouth_path)
    if face_cascade.empty():
        raise RuntimeError(f"Could not load face cascade from {face_path}")
    if mouth_cascade.empty():
        raise RuntimeError(f"Could not load mouth cascade from {mouth_path}")
    return face_cascade, mouth_cascade


def _detect_faces(face_cascade, gray_frame):
    faces = face_cascade.detectMultiScale(
        gray_frame,
        scaleFactor=config.FACE_CASCADE_SCALE_FACTOR,
        minNeighbors=config.FACE_CASCADE_MIN_NEIGHBORS,
        minSize=config.FACE_MIN_SIZE,
    )
    return list(faces)  # list of (x, y, w, h)


def _mouth_region(face_box, frame_shape):
    """Lower portion of a face box, where a talking mouth would be."""
    x, y, w, h = face_box
    fh, fw = frame_shape[:2]
    my0 = y + int(h * config.MOUTH_REGION_Y_START_RATIO)
    my1 = min(y + h, fh)
    mx0 = max(x, 0)
    mx1 = min(x + w, fw)
    if my1 <= my0 or mx1 <= mx0:
        return None
    return (mx0, my0, mx1, my1)  # x0,y0,x1,y1


def _match_face_to_slots(face_box, slots, max_dist):
    """
    Finds which existing tracked "slot" (a face we've been following
    across sampled frames in this window) this detection belongs to,
    based on center-point distance. Returns the slot index or None.
    """
    x, y, w, h = face_box
    cx, cy = x + w / 2, y + h / 2
    best_idx, best_dist = None, max_dist
    for i, slot in enumerate(slots):
        sx, sy = slot["last_center"]
        dist = ((cx - sx) ** 2 + (cy - sy) ** 2) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    return best_idx


def _analyze_window(cap, frame_shape, start_frame, end_frame, fps):
    """
    Samples frames in [start_frame, end_frame), tracks face slots across
    them, and returns (winner_center_xy or None, faces_found: bool).
    """
    face_cascade, mouth_cascade = _analyze_window._cascades
    stride = max(1, config.SPEAKER_SAMPLE_EVERY_N_FRAMES)
    fh, fw = frame_shape[:2]
    max_match_dist = max(fw, fh) * 0.15  # generous-ish since people move a bit

    slots = []  # each: {last_center, last_mouth_gray, motion_total, motion_samples}

    frame_idx = start_frame
    any_face_found = False

    while frame_idx < end_frame:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = _detect_faces(face_cascade, gray)

        seen_slots = set()
        for face_box in faces:
            any_face_found = True
            x, y, w, h = face_box
            cx, cy = x + w / 2, y + h / 2

            slot_idx = _match_face_to_slots(face_box, slots, max_match_dist)
            if slot_idx is None:
                slots.append({
                    "last_center": (cx, cy),
                    "last_mouth_gray": None,
                    "motion_total": 0.0,
                    "motion_samples": 0,
                })
                slot_idx = len(slots) - 1

            slot = slots[slot_idx]
            slot["last_center"] = (cx, cy)
            seen_slots.add(slot_idx)

            mouth_box = _mouth_region(face_box, frame.shape)
            if mouth_box is not None:
                mx0, my0, mx1, my1 = mouth_box
                mouth_gray = cv2.resize(gray[my0:my1, mx0:mx1], (40, 24))
                if slot["last_mouth_gray"] is not None:
                    diff = cv2.absdiff(mouth_gray, slot["last_mouth_gray"])
                    slot["motion_total"] += float(np.mean(diff))
                    slot["motion_samples"] += 1
                slot["last_mouth_gray"] = mouth_gray

        frame_idx += stride

    if not any_face_found or not slots:
        return None, any_face_found

    # pick the slot with the highest average mouth motion
    scored = []
    for slot in slots:
        if slot["motion_samples"] > 0:
            avg_motion = slot["motion_total"] / slot["motion_samples"]
            scored.append((avg_motion, slot["last_center"]))

    if not scored:
        # faces were found but mouth motion was never measured twice in a
        # row (window too short, or detection too sparse) -- fall back to
        # whichever face slot was detected first this window
        return slots[0]["last_center"], True

    scored.sort(key=lambda s: s[0], reverse=True)
    winner_motion, winner_center = scored[0]

    if len(scored) > 1:
        runner_up_motion = scored[1][0]
        if runner_up_motion > 0 and winner_motion < runner_up_motion * config.SWITCH_CONFIDENCE_MARGIN:
            # too close to call confidently this window
            return "AMBIGUOUS", True

    return winner_center, True


def track_active_speaker(video_path: str):
    """
    Returns the same shape as face_tracker.track_faces():
        keyframes: list of (frame_idx, center_x, center_y) -- HARD-STEPPED,
                   not eased. Each window holds one constant position.
        frame_w, frame_h, fps, total_frames, found_any_face
    """
    face_cascade, mouth_cascade = _load_cascades()
    _analyze_window._cascades = (face_cascade, mouth_cascade)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video for active speaker tracking: {video_path}")

    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or config.OUTPUT_FPS
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_shape = (frame_h, frame_w)

    window_frames = max(1, int(round(config.SPEAKER_REEVAL_INTERVAL_SEC * fps)))

    current_position = (frame_w / 2, frame_h / 2)  # default center
    found_any_face = False
    keyframes = []

    start_frame = 0
    while start_frame < total_frames:
        end_frame = min(start_frame + window_frames, total_frames)

        winner, faces_found = _analyze_window(cap, frame_shape, start_frame, end_frame, fps)
        if faces_found:
            found_any_face = True

        if winner == "AMBIGUOUS":
            pass  # keep current_position (avoid flicker on a close call)
        elif winner is not None:
            current_position = winner
        elif config.NO_FACE_FALLBACK == "center":
            current_position = (frame_w / 2, frame_h / 2)
        # else "last_known": keep current_position as-is

        # hard cut: emit a single flat keyframe segment for this whole window
        for frame_idx in range(start_frame, end_frame):
            keyframes.append((frame_idx, current_position[0], current_position[1]))

        start_frame = end_frame

    cap.release()

    if not found_any_face:
        print(f"[active-speaker] no faces detected in {video_path}, using center crop")

    return {
        "keyframes": keyframes,
        "frame_w": frame_w,
        "frame_h": frame_h,
        "fps": fps,
        "total_frames": total_frames,
        "found_any_face": found_any_face,
    }