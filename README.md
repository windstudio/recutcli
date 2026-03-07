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
| `Keytron_final.mp4` | Final video with Chinese dubbing and subtitles |
| `Keytron_raw.mp4` | Original downloaded video |
| `Keytron_dubbing.wav` | TTS-generated Chinese audio |
| `Keytron_chs.md` | Chinese script |
| `Keytron_script.md` | English transcript |
| `Keytron.srt` | Subtitle file |

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
LLM_API_KEY=your_api_key_here
LLM_API_URL=https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1
LLM_MODEL=glm-5
TTS_ENGINE=edge
TTS_VOICE=zh-CN-XiaoxiaoNeural
WHISPER_MODEL=small
```

### LLM Configuration

The tool supports any OpenAI-compatible API:

- **LLM_API_KEY** - Your API key (required)
- **LLM_API_URL** - API endpoint URL (default: Yuanjing API)
- **LLM_MODEL** - Model name (default: glm-5)

> **Note:** For backward compatibility, `YUANJING_API_KEY` is still supported.

### TTS Engines

- **edge** (default) - Microsoft Edge TTS, high quality Chinese voice
- **coqui** - Open-source TTS (requires Python 3.9-3.11)
- **piper** - Offline TTS using ONNX models

## License

MIT
