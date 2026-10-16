#!/usr/bin/env python3
"""
scripts/extract_intro_frames.py
Extracts cropped 4:3 frames and synchronized audio from assets/Street Fighters.mov.
Usage:
    .venv/bin/python scripts/extract_intro_frames.py [--end-frame 1477|1756] [--force]
"""

import os
import sys
import json
import argparse
import time
import wave
import cv2
import numpy as np

DEFAULT_VIDEO = "assets/Street Fighters.mov"
DEFAULT_OUT_DIR = "assets/intro_frames"
DEFAULT_AUDIO_OUT = "assets/audio/intro_cutscene.wav"

START_FRAME = 892
BASE_END_FRAME = 1477     # Base punch + skyscraper pan + fade (586 frames)
LOGO_END_FRAME = 1756     # Full cutscene including logo drop (865 frames)

CROP_Y1, CROP_Y2 = 112, 2055
CROP_X1, CROP_X2 = 431, 3024
TARGET_WIDTH, TARGET_HEIGHT = 960, 720
JPEG_QUALITY = 85
VIDEO_FPS = 55.763519


def check_cache_complete(out_dir: str, expected_frames: int) -> bool:
    manifest_path = os.path.join(out_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return False
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        if manifest.get("total_frames") != expected_frames:
            return False
        for i in range(expected_frames):
            frame_file = os.path.join(out_dir, f"frame_{i:04d}.jpg")
            if not os.path.exists(frame_file) or os.path.getsize(frame_file) == 0:
                return False
        return True
    except Exception:
        return False


def extract_frames(video_path: str, out_dir: str, start_frame: int, end_frame: int, force: bool = False):
    total_frames = end_frame - start_frame + 1
    os.makedirs(out_dir, exist_ok=True)

    if not force and check_cache_complete(out_dir, total_frames):
        print(f"[CACHE HIT] Frame cache already complete ({total_frames} frames in {out_dir}).")
        return

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    print(f"Extracting {total_frames} frames ({start_frame}..{end_frame}) to {out_dir} at {TARGET_WIDTH}x{TARGET_HEIGHT}...")

    t0 = time.time()
    for idx in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            print(f"Warning: Video stream ended early at frame {start_frame + idx}")
            total_frames = idx
            break

        crop = frame[CROP_Y1:CROP_Y2, CROP_X1:CROP_X2]
        resized = cv2.resize(crop, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_AREA)
        out_path = os.path.join(out_dir, f"frame_{idx:04d}.jpg")
        cv2.imwrite(out_path, resized, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])

        if idx > 0 and idx % 100 == 0:
            print(f"  Progress: {idx}/{total_frames} frames ({(time.time()-t0)/idx*1000:.1f} ms/frame)...")

    cap.release()
    elapsed = time.time() - t0
    print(f"Frame extraction complete: {total_frames} frames in {elapsed:.2f}s ({total_frames/elapsed:.1f} FPS).")

    # Write self-describing manifest
    manifest = {
        "source_video": video_path,
        "start_frame": start_frame,
        "end_frame": start_frame + total_frames - 1,
        "total_frames": total_frames,
        "playback_fps": 60.0,
        "native_video_fps": VIDEO_FPS,
        "resolution": [TARGET_WIDTH, TARGET_HEIGHT],
        "crop_region": {"y1": CROP_Y1, "y2": CROP_Y2, "x1": CROP_X1, "x2": CROP_X2},
        "file_pattern": "frame_%04d.jpg",
        "format": "jpg",
        "quality": JPEG_QUALITY
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Saved manifest to {os.path.join(out_dir, 'manifest.json')}")


def extract_audio(video_path: str, audio_out: str, start_frame: int, end_frame: int):
    scratch_wav = "scratch/street_fighters_audio.wav"
    if not os.path.exists(scratch_wav):
        print(f"Audio source {scratch_wav} not found; skipping audio extraction.")
        return

    os.makedirs(os.path.dirname(audio_out), exist_ok=True)
    rate = 48000
    with open(scratch_wav, "rb") as f:
        f.seek(4096)
        raw = f.read()

    total_samples = len(raw) // (2 * 2) # 2 bytes per sample, 2 channels
    samples = np.frombuffer(raw[:total_samples * 4], dtype=np.int16).reshape(-1, 2)
    s_start = int((start_frame / VIDEO_FPS) * rate)
    s_end = int((end_frame / VIDEO_FPS) * rate)
    chunk = samples[s_start:s_end]

    with wave.open(audio_out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(chunk.tobytes())
    print(f"Extracted cutscene audio to {audio_out} ({len(chunk)/rate:.2f}s).")


def main():
    parser = argparse.ArgumentParser(description="Street Fighter II Intro Cutscene Extractor")
    parser.add_argument("--video", default=DEFAULT_VIDEO, help="Path to Street Fighters.mov")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Destination directory for frames")
    parser.add_argument("--start-frame", type=int, default=START_FRAME, help="Start frame index")
    parser.add_argument("--end-frame", type=int, default=LOGO_END_FRAME, help="End frame index (1477 or 1756)")
    parser.add_argument("--audio-out", default=DEFAULT_AUDIO_OUT, help="Path for output audio WAV")
    parser.add_argument("--force", action="store_true", help="Force re-extraction even if cache exists")
    args = parser.parse_args()

    extract_frames(args.video, args.out_dir, args.start_frame, args.end_frame, force=args.force)
    extract_audio(args.video, args.audio_out, args.start_frame, args.end_frame)


if __name__ == "__main__":
    main()
