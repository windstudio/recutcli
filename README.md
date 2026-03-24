# Recut

Auto-clip Kickstarter videos into short social media videos with Chinese dubbing.

## Installation

```bash
pip install -e .
```

Requires ffmpeg to be installed:
- Windows: `winget install ffmpeg`
- macOS: `brew install ffmpeg`
- Linux: `apt install ffmpeg`

## Usage

```bash
recut https://kickstarter.com/projects/xxx -o output.mp4
```

### Options

| Option | Description |
|--------|-------------|
| `-o, --output` | Output video file path (auto-generated from URL if not specified) |
| `--platform` | Target platform: tiktok, instagram, reels (default: tiktok) |
| `--duration` | Video duration in seconds (default: 30) |
| `--scene-threshold` | Scene change sensitivity (default: 0.3) |
| `--video-url` | Direct video URL (mp4, avi, m3u8, etc.) - bypass Kickstarter scraping |
| `--chs-title` | Chinese title - skip LLM title generation |
| `--title` | English title from video page (optional, used for generating Chinese title) |
| `--image` | Main image URL or path for thumbnail generation |
| `--tts-engine` | TTS engine: edge, coqui, minimax (default: edge) |
| `--pause-on-chs-script` | Pause after generating Chinese script for user review |
| `--resume` | Resume from checkpoint (directory or .md file path) |

### Examples

Basic usage:
```bash
recut https://kickstarter.com/projects/xxx -o output.mp4
```

With custom Chinese title and cover image:
```bash
recut https://kickstarter.com/projects/xxx -o output.mp4 \
  --chs-title "无狠活黑科技\n无狠活，不尬吹，只讲真东西" \
  --image "https://example.com/product.jpg"
```

With direct video URL:
```bash
recut https://kickstarter.com/projects/xxx -o output.mp4 \
  --video-url "https://example.com/video.mp4"
```

### Modes

Recut supports two workflow modes:

**Automatic Mode** (default): Runs end-to-end without interruption. Best for batch processing.

**Semi-Automatic Mode**: Pauses after generating the Chinese script for user review. Use `--pause-on-chs-script` to enable:

```bash
recut https://kickstarter.com/projects/xxx -o output.mp4 --pause-on-chs-script
```

This pauses before TTS generation, allowing you to:
1. Review and edit the generated Chinese script in `output/output.md`
2. Edit scene selections in `output/output_scenes.json`
3. Resume when ready: `recut --resume output/` or `recut --resume output/output.md`

### Resume Workflow

When resuming from a paused checkpoint:

```bash
# First run - pauses after script generation
recut https://kickstarter.com/projects/xxx -o output.mp4 --pause-on-chs-script

# Edit the script and scenes as needed
# output/output.md          - Chinese script (title, transcript, tags)
# output/output_scenes.json - Scene timestamps with motion scores (score_change_count)

# Resume processing
recut --resume output/
```

The `score_change_count` in scenes.json represents motion intensity (×100). Higher values indicate more dynamic content. You can manually adjust scene selections by editing this file.

You can also resume from the .md file directly:

```bash
recut --resume output/output.md
```

### Output Structure

Running `recut https://kickstarter.com/projects/xxx/sample-project -o sample.mp4` generates:

```
output/
├── sample.mp4          # Final video with Chinese dubbing and subtitles
├── sample.md           # Chinese script with title, transcript, tags, and source URL
└── sample/             # Intermediate files
    ├── sample_metadata.json  # Checkpoint metadata for resume
    ├── sample_scenes.json    # Scene timestamps for video cutting
    ├── sample_script.md   # English transcript
    ├── sample_dubbing.wav # TTS-generated Chinese audio
    ├── sample_nodub.mp4   # Short video without dubbing
    ├── sample.srt         # Subtitle file
    ├── sample_raw.mp4     # Original downloaded video
    └── sample_thumb.jpg   # Thumbnail with Chinese title
```

### Video Features

- **Smart Fragment Selection**: Uses motion detection to select the most dynamic video segments. Fragments with higher motion intensity are prioritized, ensuring the final video captures the most engaging content.
- **Thumbnail Intro**: The first 0.5 seconds show a thumbnail with the Chinese title before the video content
- **Slanted Poster Thumbnail**: Thumbnails feature a slanted image mask, gradient background, and skewed title text
- **Logo Overlay**: If configured, a logo is displayed in the top-left corner throughout the video
- **Subtitles**: Chinese subtitles are delayed 0.5s to avoid showing during thumbnail display

### Bypassing Cloudflare

If Kickstarter blocks direct requests (403 error), use a browser to get the video URL:

1. Open the Kickstarter page in your browser
2. Open developer tools (F12) → Network tab
3. Filter for `m3u8` or `mp4` and copy the URL
4. Run with `--video-url`:

```bash
recut https://kickstarter.com/projects/xxx -o output.mp4 \
  --video-url "https://v2.kickstarter.com/..."
```

## Configuration

Create a `.env` file in the project directory:

```env
# LLM Configuration (required)
LLM_API_KEY=your_api_key_here
LLM_API_URL=https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1
LLM_MODEL=glm-5

# TTS Configuration (optional)
TTS_ENGINE=edge
TTS_VOICE=zh-CN-XiaoxiaoNeural
WHISPER_MODEL=small

# Thumbnail Configuration (optional)
THUMBNAIL_FONT=/path/to/chinese-font.ttf
THUMBNAIL_LOGO_PATH=material/logo.png
THUMBNAIL_FONT_SIZE_TITLE=72
```

### LLM Configuration

The tool supports any OpenAI-compatible API:

- **LLM_API_KEY** - Your API key (required)
- **LLM_API_URL** - API endpoint URL (default: Yuanjing API)
- **LLM_MODEL** - Model name (default: glm-5)

### TTS Engines

- **edge** (default) - Microsoft Edge TTS, high quality Chinese voice
- **coqui** - Open-source TTS (requires Python 3.9-3.11)
- **minimax** - MiniMax cloud TTS API, high quality Chinese voice

Each TTS engine has a different speaking speed. The tool automatically adjusts the Chinese script length to match the target duration:

| Engine | Character Rate | Target chars for 30s video |
|--------|---------------|----------------------------|
| edge | 3.5 chars/sec | ~105 chars |
| minimax | 4.5 chars/sec | ~135 chars |
| coqui | 3.5 chars/sec | ~105 chars |

Additionally, if the dubbing duration is shorter than the target, the tool automatically selects more video fragments to ensure the final video meets the target duration.

### MiniMax Configuration

To use MiniMax TTS, set these environment variables:

```env
MINIMAX_API_KEY=your-api-key
MINIMAX_API_URL=https://api.minimaxi.com/v1/t2a_v2
MINIMAX_VOICE_ID=moss_audio_ce44fc67-7ce3-11f0-8de5-96e35d26fb85
```

Get your API key from [MiniMax Platform](https://platform.minimaxi.com).

**Note**: MiniMax TTS uses volume level 2.0 (default is 1.0) for better audio output.

### Thumbnail Configuration

Configure thumbnail generation with these environment variables:

```env
# Chinese font for title display (auto-detected if not set)
THUMBNAIL_FONT=/path/to/font.ttf

# Optional: Default fonts to search (comma-separated, auto-detection)
THUMBNAIL_DEFAULT_FONTS=ZCOOLGaoDuanHei-Regular.ttf,NotoSansSC-Bold.ttf

# Optional: Font sizes
THUMBNAIL_FONT_SIZE_TITLE=72
THUMBNAIL_FONT_SIZE_SUBTITLE=14

# Optional: Logo to overlay throughout video (top-left corner, 70% opacity)
THUMBNAIL_LOGO_PATH=material/logo.png

# Optional: Outro video to append at the end
THUMBNAIL_OUTRO_PATH=material/outro.mp4
```

**Font Setup**: The tool auto-detects Chinese fonts (站酷高端黑, Noto Sans SC, Source Han Sans, SimHei, etc.). For custom fonts, set `THUMBNAIL_FONT` to the font file path.

**Logo**: When `THUMBNAIL_LOGO_PATH` is set, the logo image will be overlaid on the entire video (not on the thumbnail image itself, to avoid overlap).

**Outro Video**: When `THUMBNAIL_OUTRO_PATH` is set and the file exists, the outro video will be appended to the final video. The outro keeps its original audio. No subtitles or logo overlay are applied to the outro.

## License

MIT
