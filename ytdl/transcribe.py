#!/usr/bin/env python3
"""
Japanese audio transcription with speaker diarization.

Uses faster-whisper (large-v3) for ASR and pyannote-audio for speaker diarization.
Outputs sub.json (Remotion-compatible) and speaker-labeled SRT.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path


def seconds_to_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def extract_audio(input_path: str, duration: float | None = None) -> str:
    """Extract 16kHz mono WAV from video/audio file using ffmpeg."""
    if not shutil.which("ffmpeg"):
        print("Error: ffmpeg not found. Install with: brew install ffmpeg")
        sys.exit(1)

    wav_path = tempfile.mktemp(suffix=".wav")
    cmd = ["ffmpeg", "-y", "-i", input_path, "-vn",
           "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1"]
    if duration:
        cmd.extend(["-t", str(duration)])
    cmd.append(wav_path)

    print(f"[1/4] Extracting audio from {input_path}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg error: {result.stderr}")
        sys.exit(1)
    print(f"  -> Audio extracted to temp WAV ({wav_path})")
    return wav_path


def run_diarization(audio_path: str, hf_token: str, num_speakers: int, device: str):
    """Run speaker diarization using pyannote-audio."""
    import torch
    from pyannote.audio import Pipeline

    print(f"[2/4] Running speaker diarization (num_speakers={num_speakers}, device={device})...")

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=hf_token,
    )

    if device == "mps" and torch.backends.mps.is_available():
        pipeline.to(torch.device("mps"))
        print("  -> Using MPS (Apple Silicon GPU)")
    else:
        if device == "mps":
            print("  -> MPS not available, falling back to CPU")
        pipeline.to(torch.device("cpu"))

    result = pipeline(audio_path, num_speakers=num_speakers)

    # pyannote 4.x returns DiarizeOutput; extract the Annotation object
    if hasattr(result, "speaker_diarization"):
        diarization = result.speaker_diarization
    else:
        diarization = result

    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "start": round(turn.start, 2),
            "end": round(turn.end, 2),
            "speaker": speaker,
        })

    print(f"  -> Found {len(segments)} diarization segments")

    # Free memory
    del pipeline
    if device == "mps" and torch.backends.mps.is_available():
        torch.mps.empty_cache()
    import gc
    gc.collect()

    return segments


def run_transcription(audio_path: str, model_size: str, language: str):
    """Run transcription using faster-whisper."""
    from faster_whisper import WhisperModel

    print(f"[3/4] Transcribing with faster-whisper ({model_size}, language={language})...")

    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    segments_gen, info = model.transcribe(
        audio_path,
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        word_timestamps=True,
    )

    segments = []
    for seg in segments_gen:
        segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
            "words": [
                {"start": round(w.start, 2), "end": round(w.end, 2), "word": w.word}
                for w in (seg.words or [])
            ],
        })

    print(f"  -> Transcribed {len(segments)} segments")

    del model
    import gc
    gc.collect()

    return segments


def merge_segments(diar_segments, whisper_segments, speaker_names: list[str]):
    """Assign each whisper segment to the speaker with most temporal overlap."""
    print("[4/4] Merging diarization + transcription...")

    # Get unique speaker labels from diarization, sorted for consistent mapping
    diar_labels = sorted(set(seg["speaker"] for seg in diar_segments))

    # Map diarization labels to user-provided names
    label_map = {}
    for i, label in enumerate(diar_labels):
        if i < len(speaker_names):
            label_map[label] = speaker_names[i]
        else:
            label_map[label] = f"speaker_{i}"

    print(f"  -> Speaker mapping: {label_map}")

    speakers_data = defaultdict(list)

    for wseg in whisper_segments:
        if not wseg["text"]:
            continue

        ws, we = wseg["start"], wseg["end"]
        overlap_per_speaker = defaultdict(float)

        for dseg in diar_segments:
            ds, de = dseg["start"], dseg["end"]
            overlap = max(0, min(we, de) - max(ws, ds))
            if overlap > 0:
                overlap_per_speaker[dseg["speaker"]] += overlap

        if overlap_per_speaker:
            best_label = max(overlap_per_speaker, key=overlap_per_speaker.get)
            speaker_name = label_map.get(best_label, best_label)
        else:
            # Fallback: assign to first speaker
            speaker_name = speaker_names[0] if speaker_names else "unknown"

        speakers_data[speaker_name].append({
            "start": ws,
            "end": we,
            "text": wseg["text"],
        })

    # Ensure all speaker names appear in output (even if empty)
    for name in speaker_names:
        if name not in speakers_data:
            speakers_data[name] = []

    total = sum(len(v) for v in speakers_data.values())
    for name, segs in speakers_data.items():
        print(f"  -> {name}: {len(segs)} segments")
    print(f"  -> Total: {total} segments")

    return dict(speakers_data)


def get_audio_duration(audio_path: str) -> float:
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", audio_path],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def write_sub_json(speakers_data: dict, duration: float, output_path: str):
    """Write sub.json in Remotion-compatible format."""
    data = {
        "duration": int(duration),
        "speakers": speakers_data,
        "annotations": [],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  -> Wrote {output_path}")


def write_srt(speakers_data: dict, output_path: str):
    """Write SRT with [speaker_name] prefixes."""
    # Flatten and sort all segments by start time
    all_segments = []
    for speaker, segs in speakers_data.items():
        for seg in segs:
            all_segments.append({**seg, "speaker": speaker})
    all_segments.sort(key=lambda x: x["start"])

    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(all_segments, 1):
            start = seconds_to_srt_time(seg["start"])
            end = seconds_to_srt_time(seg["end"])
            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"[{seg['speaker']}] {seg['text']}\n")
            f.write("\n")
    print(f"  -> Wrote {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Japanese audio transcription with speaker diarization"
    )
    parser.add_argument("input", help="Path to video or audio file")
    parser.add_argument("--speakers", nargs="+", default=["speaker_0", "speaker_1"],
                        help="Speaker names in order (default: speaker_0 speaker_1)")
    parser.add_argument("--num-speakers", type=int, default=2,
                        help="Expected number of speakers (default: 2)")
    parser.add_argument("--language", default="ja",
                        help="Whisper language code (default: ja)")
    parser.add_argument("--model", default="large-v3",
                        help="Whisper model size (default: large-v3)")
    parser.add_argument("--hf-token", default=None,
                        help="HuggingFace token (or set HF_TOKEN env var)")
    parser.add_argument("--device", default="mps",
                        help="Torch device for pyannote (default: mps)")
    parser.add_argument("--output-dir", default="./output",
                        help="Output directory (default: ./output)")
    parser.add_argument("--duration", type=float, default=None,
                        help="Only process first N seconds")

    args = parser.parse_args()

    # Validate input
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    # Resolve HF token
    hf_token = args.hf_token or os.environ.get("HF_TOKEN")
    if not hf_token:
        print("Error: HuggingFace token required.")
        print("  Set HF_TOKEN env var or pass --hf-token")
        print("  Get token at: https://huggingface.co/settings/tokens")
        print("  Accept licenses at:")
        print("    https://huggingface.co/pyannote/speaker-diarization-3.1")
        print("    https://huggingface.co/pyannote/segmentation-3.0")
        sys.exit(1)

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    wav_path = None
    try:
        # Stage 1: Extract audio
        wav_path = extract_audio(args.input, args.duration)

        # Get duration
        duration = args.duration or get_audio_duration(wav_path)

        # Stage 2: Speaker diarization
        diar_segments = run_diarization(wav_path, hf_token, args.num_speakers, args.device)

        # Stage 3: Transcription
        whisper_segments = run_transcription(wav_path, args.model, args.language)

        # Stage 4: Merge
        speakers_data = merge_segments(diar_segments, whisper_segments, args.speakers)

        # Stage 5: Output
        print("\nWriting output files...")
        json_path = os.path.join(args.output_dir, "sub.json")
        srt_path = os.path.join(args.output_dir, "transcription.srt")
        write_sub_json(speakers_data, duration, json_path)
        write_srt(speakers_data, srt_path)

        print("\nDone!")

    finally:
        # Cleanup temp WAV
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)


if __name__ == "__main__":
    main()
