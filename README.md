# Recut

Auto-clip Kickstarter videos into 25-second social media shorts.

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
- `--scene-threshold 0.3` - Scene change sensitivity (default: 0.3)
- `--m3u8-url URL` - Direct m3u8 URL (bypass Kickstarter scraping)

### Bypassing Cloudflare

If Kickstarter blocks direct requests (403 error), use a browser to get the m3u8 URL:

1. Open the Kickstarter page in your browser
2. Open developer tools (F12) → Network tab
3. Filter for `m3u8` and copy the URL
4. Run with `--m3u8-url`:

```bash
recut https://kickstarter.com/projects/xxx -o output.mp4 --m3u8-url "https://v2.kickstarter.com/..."
```

## License

MIT
