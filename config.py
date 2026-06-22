"""
Central config for the auto-clipper. Tweak these instead of hunting
through the other files.
"""

# ---- Output video ----
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920          # 9:16 vertical
OUTPUT_FPS = 30
VIDEO_CRF = 20                 # lower = higher quality, bigger file (18-23 is sane)
VIDEO_PRESET = "veryfast"      # ffmpeg x264 preset

# ---- Chunking ----
CLIP_LENGTH_SEC = 45           # length of each output clip
CLIP_OVERLAP_SEC = 0           # set >0 if you want overlapping clips
MIN_LAST_CLIP_SEC = 10         # drop a trailing clip shorter than this

# ---- Face tracking / crop ----
FACE_TRACK_MODE = "active_speaker"  # "smooth_pan" (old behavior) or "active_speaker" (hard cuts)
FACE_DETECT_EVERY_N_FRAMES = 5     # re-run detector every N frames (dynamic tracking)
FACE_SMOOTHING_ALPHA = 0.15        # 0-1, lower = smoother/slower pan, higher = snappier (smooth_pan mode only)
FACE_CASCADE_SCALE_FACTOR = 1.1
FACE_CASCADE_MIN_NEIGHBORS = 5
FACE_MIN_SIZE = (60, 60)
NO_FACE_FALLBACK = "center"        # "center" or "last_known"

# ---- Active speaker detection (FACE_TRACK_MODE = "active_speaker") ----
SPEAKER_REEVAL_INTERVAL_SEC = 2.5   # how often to re-decide who's talking and (maybe) hard-cut
SPEAKER_SAMPLE_EVERY_N_FRAMES = 3   # frame stride used when measuring mouth motion within a window
MOUTH_CASCADE_MIN_NEIGHBORS = 15    # smile cascade is noisy; needs a high threshold to behave as a mouth detector
MOUTH_REGION_Y_START_RATIO = 0.55   # mouth search area = lower part of the face box (0=top of face, 1=bottom)
MIN_FACES_FOR_SPEAKER_DETECTION = 2 # below this, just track the single face directly (no point comparing mouths)
SWITCH_CONFIDENCE_MARGIN = 1.3      # leading candidate's motion score must beat 2nd place by this ratio to trigger a cut (avoids flicker on close calls)

# ---- Captions ----
WHISPER_MODEL_SIZE = "base"        # tiny/base/small/medium - bigger = more accurate, slower
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"      # fast on CPU
CAPTION_MAX_WORDS_PER_CHUNK = 3    # "pop-on" group size (1-3 reads best)
CAPTION_FONT = "DejaVu Sans"    # must be a font ffmpeg/fontconfig can find (Bold applied via ASS Bold=1 style flag)
CAPTION_FONT_SIZE = 64
CAPTION_FONT_COLOR = "white"
CAPTION_OUTLINE_COLOR = "black"
CAPTION_OUTLINE_WIDTH = 4
CAPTION_POSITION_Y_RATIO = 0.72    # 0=top, 1=bottom of frame
CAPTION_HIGHLIGHT_COLOR = "&H00D7FF"  # ASS BGR hex - gold, used for active word emphasis (optional)

# ---- Paths ----
WORK_DIR = "work"              # scratch space (downloads, intermediate files)
OUTPUT_DIR = "clips_output"    # final clips land here