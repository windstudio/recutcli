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

## License

MIT
