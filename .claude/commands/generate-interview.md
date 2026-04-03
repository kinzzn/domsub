Generate a split-screen interview video with Japanese transcription and speaker diarization.

## Full Pipeline Steps

You are operating in the `domsub` project — a Remotion-based split-screen interview video generator.

### Prerequisites
- ffmpeg installed (`brew install ffmpeg`)
- yt-dlp installed (`brew install yt-dlp`)
- HuggingFace token with access to pyannote models (set as `HF_TOKEN` env var or pass `--hf-token`)
- Python venv at `ytdl/.venv` with dependencies installed

If the venv doesn't exist yet, set it up:
```bash
cd ytdl
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 1: Download video (if needed)
```bash
cd ytdl
yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" \
  --merge-output-format mp4 -o "%(title)s.%(ext)s" "YOUTUBE_URL"
```

### Step 2: Run transcription + speaker diarization
```bash
cd ytdl
source .venv/bin/activate
python transcribe.py INPUT.mp4 --speakers SPEAKER1 SPEAKER2 --hf-token HF_TOKEN
```

Options:
- `--duration N` — only process first N seconds (for quick testing)
- `--num-speakers N` — expected number of speakers (default: 2)
- `--model large-v3` — whisper model size
- `--language ja` — language code

Output goes to `ytdl/output/sub.json` and `ytdl/output/transcription.srt`.

**Important**: Check `output/transcription.srt` to verify speaker assignment is correct. If speakers are swapped (e.g., host labeled as guest), either:
- Re-run with `--speakers` names in reversed order, OR
- Swap the speaker keys in `output/sub.json` using a script

### Step 3: Prepare project files
```bash
# Backup existing sub.json
cp sub.json sub.json.bak

# Copy new transcription to project root
cp ytdl/output/sub.json sub.json

# Extract full audio for Remotion
ffmpeg -y -i ytdl/INPUT.mp4 -vn -acodec libmp3lame -b:a 192k public/audio.mp3
```

If only rendering a portion, add `-t SECONDS` to the ffmpeg command and edit `sub.json` duration field accordingly.

### Step 4: Ensure speaker avatars exist
Each speaker needs an avatar image at `public/SPEAKERNAME.jpeg`. Check that files exist:
```bash
ls public/*.jpeg
```

### Step 5: Render the video
```bash
npm run render
```
Output: `output.mp4` (1080x1080, h264, 30fps)

### Step 6: Preview (optional)
```bash
open output.mp4          # macOS
npm run studio           # Remotion Studio in browser for interactive preview
```

### Rollback
If the result is bad, restore the previous version:
```bash
cp sub.json.bak sub.json
```

### Notes
- `sub.json` format: `{ duration, speakers: { name: [{start, end, text}] }, annotations: [] }`
- Speaker diarization quality depends on audio clarity and voice distinctiveness
- The `ytdl/` folder is gitignored — all intermediate files stay there
- For long videos (30+ min), full transcription takes ~15 minutes on Apple Silicon
