# SoftClip - Smart Auto-Clipper

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
# Local file (active_speaker mode by default — hard cuts to whoever's talking)
python3 main.py my_podcast.mp4

# From YouTube/Twitch/etc.
python3 main.py https://youtube.com/watch?v=XXXXXXXX

# Custom clip length (seconds)
python3 main.py my_podcast.mp4 --clip-length 60

# Cap total output to N clips (stops early, doesn't waste time on the rest)
python3 main.py my_podcast.mp4 --max-clips 5

# Explicitly choose tracking mode
python3 main.py my_podcast.mp4 --track-mode active_speaker   # hard-cut to whoever's talking (default)
python3 main.py my_podcast.mp4 --track-mode smooth_pan       # smooth eased pan that follows a face

# Skip captions (faster, no Whisper needed)
python3 main.py my_podcast.mp4 --no-captions

# Static center crop, no face tracking at all
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
| `FACE_TRACK_MODE` | `"active_speaker"` (default) or `"smooth_pan"` |
| `FACE_DETECT_EVERY_N_FRAMES` | how often to re-run face detection (lower = more accurate, slower) |
| `FACE_SMOOTHING_ALPHA` | smooth_pan mode only: 0–1, lower = smoother/slower pan |
| `SPEAKER_REEVAL_INTERVAL_SEC` | active_speaker mode: how often to re-check who's talking and potentially cut (default 2.5s) |
| `SWITCH_CONFIDENCE_MARGIN` | active_speaker mode: how much clearer a winner needs to be before cutting (1.3 = 30% margin, higher = fewer cuts) |
| `WHISPER_MODEL_SIZE` | `tiny`/`base`/`small`/`medium` — bigger = more accurate, slower |
| `CAPTION_MAX_WORDS_PER_CHUNK` | how many words appear per caption "pop" (1–3 reads best) |
| `CAPTION_FONT_SIZE`, `CAPTION_FONT_COLOR`, etc. | caption styling |

## How the tracking modes work

**`active_speaker` (default):** Every `SPEAKER_REEVAL_INTERVAL_SEC` seconds, it samples several frames from that window, detects all faces, and measures how much each face's mouth region changes frame-to-frame. The face with the most mouth movement wins that window, *if* it clearly beats the runner-up by `SWITCH_CONFIDENCE_MARGIN` — otherwise the previous speaker holds to avoid flickering on ambiguous/overlapping speech. When a winner is decided, the crop snaps instantly (hard cut) to center on them and stays there for the whole window.

**`smooth_pan`:** Detects the largest face every N frames and eases the crop center toward it with exponential smoothing. Good for single-speaker content; can look floaty on multi-person footage.

Both modes fall back to static center crop if no faces are detected.

**Known limitation on detection:** Haar cascades are fast and fully offline but not as robust as modern DNN detectors — side profiles, poor lighting, or small/distant faces can be missed. If tracking is unreliable on your footage, the swap point is `face_tracker.py`'s `_detect_largest_face` and `active_speaker_tracker.py`'s `_detect_faces` — a MediaPipe or OpenCV DNN detector can drop in without touching the rest of the pipeline.

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

## Thank You

- If this tools really help you please give us a rating
- support us on https://trakteer.id/rawiansyah_andhika_s 
