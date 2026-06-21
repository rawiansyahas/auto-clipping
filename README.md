# Auto-Clipper

Turns a long video (local file or a YouTube/Twitch/etc. URL) into a batch of
vertical 9:16 short clips with face-following crop and TikTok-style burned-in
captions.

## Pipeline

```
source (file or URL)
  -> chunk into fixed-length segments
  -> for each chunk:
       - track subject position (Haar-cascade face detection + smoothing)
       - render 9:16 crop that pans to follow the subject
       - transcribe audio (word-level timestamps, faster-whisper, local/CPU)
       - burn in pop-on captions
  -> clips_output/clip_001.mp4, clip_002.mp4, ...
```

## Setup

```bash
pip install yt-dlp faster-whisper opencv-python --break-system-packages
```

You also need `ffmpeg` and `ffprobe` on PATH (most systems already have this;
`sudo apt install ffmpeg` on Ubuntu/Debian if not).

First run will download the Whisper model (~150MB for `base`) from
Hugging Face — needs internet access once, then it's cached locally.

## Usage

```bash
# Local file
python3 main.py my_podcast.mp4

# From YouTube/Twitch/etc.
python3 main.py https://youtube.com/watch?v=XXXXXXXX

# Custom clip length (seconds)
python3 main.py my_podcast.mp4 --clip-length 60

# Skip captions (faster, no Whisper needed)
python3 main.py my_podcast.mp4 --no-captions

# Static center crop instead of face-following pan
python3 main.py my_podcast.mp4 --no-facetrack
```

Output lands in `clips_output/clip_001.mp4`, `clip_002.mp4`, etc.
Intermediate files (downloads, per-chunk audio, subtitle files) go in
`work/` — safe to delete after a run, or keep for debugging.

## Tuning

Everything adjustable lives in `config.py`:

| Setting | What it does |
|---|---|
| `CLIP_LENGTH_SEC` | length of each output clip |
| `OUTPUT_WIDTH` / `OUTPUT_HEIGHT` | output resolution (default 1080x1920) |
| `FACE_DETECT_EVERY_N_FRAMES` | how often to re-run face detection (lower = more accurate, slower) |
| `FACE_SMOOTHING_ALPHA` | 0–1, how snappy vs. smooth the pan is. Lower = smoother/slower pan |
| `WHISPER_MODEL_SIZE` | `tiny`/`base`/`small`/`medium` — bigger = more accurate, slower |
| `CAPTION_MAX_WORDS_PER_CHUNK` | how many words appear per caption "pop" (1–3 reads best) |
| `CAPTION_FONT_SIZE`, `CAPTION_FONT_COLOR`, etc. | caption styling |

## How the face tracking works

Every `FACE_DETECT_EVERY_N_FRAMES` frames, it runs OpenCV's bundled Haar
cascade face detector and picks the largest detected face (assumed to be
the main speaker). Between detections it holds the last known position.
The crop center is smoothed with an exponential moving average
(`FACE_SMOOTHING_ALPHA`) so the pan looks deliberate instead of jittery,
then that path is baked into an ffmpeg `sendcmd` script that drives the
`crop` filter's x/y per-frame.

If no face is ever found in a chunk, it falls back to a static center crop
automatically — no manual intervention needed.

**Known limitation:** Haar cascades are a fast, classic, fully-offline
detector but not as robust as modern DNN-based face detectors — side
profiles, poor lighting, or small/distant faces can be missed. If you find
tracking unreliable on your footage, the swap point is `face_tracker.py`'s
`_detect_largest_face` function; an OpenCV DNN or MediaPipe-based detector
can drop in there without touching the rest of the pipeline.

## Known issues / not yet verified

- Caption burn-in (`transcribe.py` + `captions.py` + `ffmpeg_utils.burn_captions`)
  is implemented and logically sound but **has not been visually verified**
  end-to-end in development — the dev sandbox couldn't reach huggingface.co
  to download the Whisper model. Run once on a real clip and check the
  output before relying on it for a batch job.
- Face tracking quality depends entirely on Haar cascade detection quality
  on your specific footage — test on a representative sample before
  processing a large batch.

## Files

- `main.py` — CLI entry point, orchestrates the pipeline
- `config.py` — all tunable settings
- `source_input.py` — local file resolution + yt-dlp downloads
- `chunker.py` — splits source into fixed-length segments
- `face_tracker.py` — Haar-cascade face detection + smoothing
- `crop_render.py` — renders 9:16 crop following the tracked path
- `transcribe.py` — faster-whisper word-level transcription
- `captions.py` — builds ASS subtitle file (pop-on style)
- `ffmpeg_utils.py` — audio extraction + caption burn-in helpers
