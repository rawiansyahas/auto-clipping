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
FACE_DETECT_EVERY_N_FRAMES = 5     # re-run detector every N frames (dynamic tracking)
FACE_SMOOTHING_ALPHA = 0.15        # 0-1, lower = smoother/slower pan, higher = snappier
FACE_CASCADE_SCALE_FACTOR = 1.1
FACE_CASCADE_MIN_NEIGHBORS = 5
FACE_MIN_SIZE = (60, 60)
NO_FACE_FALLBACK = "center"        # "center" or "last_known"

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
WORK_DIR = "clipping"              # scratch space (downloads, intermediate files)
OUTPUT_DIR = "clips_output"    # final clips land here
