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

- `--platform {tiktok,instagram,reels}` - Target platform (default: tiktok)
- `--duration SECONDS` - Video duration (default: 30)
- `--scene-threshold 0.3` - Scene change sensitivity (default: 0.3)
- `--m3u8-url URL` - Direct m3u8 URL (bypass Kickstarter scraping)
- `--tts-engine {edge,coqui,piper}` - TTS engine for Chinese dubbing (default: edge)
- `--title TITLE` - English title from video page (optional, used for generating Chinese title)

### Output Files

Running `recut -o sample/Keytron.mp4` generates:

| File | Description |
|------|-------------|
| `Keytron.mp4` | Clipped short video |
| `Keytron_final.mp4` | Final video with Chinese dubbing, subtitles, thumbnail intro, and logo overlay |
| `Keytron_raw.mp4` | Original downloaded video |
| `Keytron_dubbing.wav` | TTS-generated Chinese audio |
| `Keytron_chs.md` | Chinese script with title and tags |
| `Keytron_script.md` | English transcript |
| `Keytron.srt` | Subtitle file |
| `Keytron_thumb.jpg` | Thumbnail image with Chinese title |

### Video Features

- **Thumbnail Intro**: The first 0.5 seconds show a thumbnail with the Chinese title before the video content
- **Logo Overlay**: If configured, a logo is displayed in the top-left corner throughout the video
- **Subtitles**: Chinese subtitles are delayed 0.5s to avoid showing during thumbnail display

### Bypassing Cloudflare

If Kickstarter blocks direct requests (403 error), use a browser to get the m3u8 URL:

1. Open the Kickstarter page in your browser
2. Open developer tools (F12) → Network tab
3. Filter for `m3u8` and copy the URL
4. Run with `--m3u8-url`:

```bash
recut https://kickstarter.com/projects/xxx -o output.mp4 --m3u8-url "https://v2.kickstarter.com/..."
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
THUMBNAIL_LOGO_PATH=images/logo.png
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
- **piper** - Offline TTS using ONNX models

### Thumbnail Configuration

Configure thumbnail generation with these environment variables:

```env
# Chinese font for title display (required for thumbnails)
THUMBNAIL_FONT=/path/to/font.ttf

# Optional: Logo to overlay throughout video (top-left corner)
THUMBNAIL_LOGO_PATH=images/logo.png

# Optional: Title font size (default: 72)
THUMBNAIL_FONT_SIZE_TITLE=72
```

**Font Setup**: Download a Chinese font (e.g., 站酷高端黑 from zcool.com.cn) and set `THUMBNAIL_FONT` to its path. Without a font configured, thumbnails will not be generated.

**Logo**: When `THUMBNAIL_LOGO_PATH` is set, the logo image will be overlaid on the entire video (not on the thumbnail image itself, to avoid overlap).

## License

MIT
