#!/usr/bin/env python3
"""
Auto-clipper pipeline:

  source (local file or URL)
    -> chunk into fixed-length segments
    -> for each chunk:
         - track face movement (dynamic)
         - render 9:16 crop following the face
         - transcribe audio (word-level timestamps)
         - burn in TikTok-style pop-on captions
    -> final clips land in clips_output/

Usage:
    python3 main.py <local_path_or_url> [--no-captions] [--no-facetrack]

Example:
    python3 main.py my_podcast.mp4
    python3 main.py https://youtube.com/watch?v=XXXXXXXX
"""
import argparse
import os
import shutil
import sys
import time

import config
import source_input
import chunker
import face_tracker
import crop_render
import transcribe
import captions
import ffmpeg_utils


def process_chunk(chunk, work_dir, output_dir, do_facetrack: bool, do_captions: bool):
    idx = chunk["index"]
    chunk_path = chunk["path"]
    tag = f"{idx:03d}"

    print(f"\n=== Clip {tag} ({chunk['start']:.1f}s - {chunk['end']:.1f}s) ===")

    # 1. Face tracking (or skip -> center crop default in crop_render)
    if do_facetrack:
        print(f"[clip {tag}] tracking face movement...")
        tracking = face_tracker.track_faces(chunk_path)
    else:
        # build a trivial "always center" tracking dict
        import cv2
        cap = cv2.VideoCapture(chunk_path)
        fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or config.OUTPUT_FPS
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        center = (fw / 2, fh / 2)
        tracking = {
            "keyframes": [(i, *center) for i in range(total)],
            "frame_w": fw, "frame_h": fh, "fps": fps,
            "total_frames": total, "found_any_face": False,
        }

    # 2. Render vertical crop
    vertical_path = os.path.join(work_dir, f"vertical_{tag}.mp4")
    print(f"[clip {tag}] rendering 9:16 crop...")
    crop_render.render_vertical_clip(chunk_path, tracking, vertical_path, work_dir, tag)

    final_path = os.path.join(output_dir, f"clip_{tag}.mp4")

    # 3. Captions
    if do_captions:
        print(f"[clip {tag}] extracting audio for transcription...")
        wav_path = os.path.join(work_dir, f"audio_{tag}.wav")
        ffmpeg_utils.extract_audio(chunk_path, wav_path)

        print(f"[clip {tag}] transcribing...")
        words = transcribe.transcribe_words(wav_path)
        print(f"[clip {tag}] {len(words)} words transcribed")

        ass_path = os.path.join(work_dir, f"captions_{tag}.ass")
        ass_path = captions.build_caption_ass(
            words, ass_path, config.OUTPUT_WIDTH, config.OUTPUT_HEIGHT
        )

        if ass_path:
            print(f"[clip {tag}] burning in captions...")
            ffmpeg_utils.burn_captions(
                vertical_path, ass_path, final_path, config.VIDEO_CRF, config.VIDEO_PRESET
            )
        else:
            print(f"[clip {tag}] no speech detected, skipping captions")
            shutil.copy(vertical_path, final_path)
    else:
        shutil.copy(vertical_path, final_path)

    print(f"[clip {tag}] done -> {final_path}")
    return final_path


def main():
    parser = argparse.ArgumentParser(description="Auto-clip long videos into vertical shorts.")
    parser.add_argument("source", help="Local video path or a URL (YouTube/Twitch/etc.)")
    parser.add_argument("--no-captions", action="store_true", help="Skip transcription/captions")
    parser.add_argument("--no-facetrack", action="store_true", help="Use static center crop instead of face tracking")
    parser.add_argument("--clip-length", type=int, default=None, help=f"Clip length in seconds (default {config.CLIP_LENGTH_SEC})")
    parser.add_argument("--work-dir", default=config.WORK_DIR)
    parser.add_argument("--output-dir", default=config.OUTPUT_DIR)
    args = parser.parse_args()

    if args.clip_length:
        config.CLIP_LENGTH_SEC = args.clip_length

    work_dir = args.work_dir
    output_dir = args.output_dir
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    t0 = time.time()

    print(f"[1/3] Resolving source: {args.source}")
    local_path = source_input.resolve_source(args.source, work_dir)

    print(f"[2/3] Splitting into {config.CLIP_LENGTH_SEC}s chunks...")
    chunks = chunker.split_into_chunks(local_path, work_dir)
    print(f"      -> {len(chunks)} chunk(s) planned")

    print(f"[3/3] Processing chunks (facetrack={not args.no_facetrack}, captions={not args.no_captions})")
    final_clips = []
    for chunk in chunks:
        try:
            final_clips.append(
                process_chunk(
                    chunk, work_dir, output_dir,
                    do_facetrack=not args.no_facetrack,
                    do_captions=not args.no_captions,
                )
            )
        except Exception as e:
            print(f"[ERROR] clip {chunk['index']} failed: {e}", file=sys.stderr)
            continue

    elapsed = time.time() - t0
    print(f"\nDone. {len(final_clips)}/{len(chunks)} clips written to '{output_dir}/' in {elapsed:.1f}s")
    for p in final_clips:
        print(f"  - {p}")


if __name__ == "__main__":
    main()
