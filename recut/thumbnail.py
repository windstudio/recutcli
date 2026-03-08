"""Thumbnail generation for social media videos."""

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from recut.config import get_thumbnail_config, get_platform_config
from recut.downloader import get_ffmpeg_path


def extract_first_frame(video_path: Path, output_path: Path) -> Path:
    """Extract the first frame from a video file.

    Args:
        video_path: Path to video file
        output_path: Path to save the frame image

    Returns:
        Path to the extracted frame

    Raises:
        RuntimeError: If extraction fails
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        get_ffmpeg_path(),
        "-i", str(video_path),
        "-vf", "select=eq(n\\,0)",  # Select first frame
        "-vframes", "1",
        "-y",  # Overwrite
        str(output_path)
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to extract first frame: {e.stderr.decode()}")


def create_gradient_mask(size: tuple[int, int], direction: str = "bottom") -> Image.Image:
    """Create a gradient mask image.

    Args:
        size: (width, height) of the mask
        direction: Direction of gradient ("bottom", "top", "left", "right")

    Returns:
        RGBA gradient mask image
    """
    width, height = size
    mask = Image.new("RGBA", size, (0, 0, 0, 0))
    pixels = mask.load()

    for y in range(height):
        for x in range(width):
            if direction == "bottom":
                # Gradient from transparent at top to dark at bottom
                alpha = int(200 * (y / height))
                pixels[x, y] = (0, 0, 0, alpha)
            elif direction == "top":
                alpha = int(200 * (1 - y / height))
                pixels[x, y] = (0, 0, 0, alpha)
            elif direction == "right":
                alpha = int(200 * (x / width))
                pixels[x, y] = (0, 0, 0, alpha)
            elif direction == "left":
                alpha = int(200 * (1 - x / width))
                pixels[x, y] = (0, 0, 0, alpha)

    return mask


def draw_text_with_shadow(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int] = (255, 255, 255, 255),
    shadow_color: tuple[int, int, int, int] = (0, 0, 0, 180),
    shadow_offset: int = 3,
    shadow_blur: int = 2
) -> None:
    """Draw text with shadow effect.

    Args:
        draw: PIL ImageDraw object
        position: (x, y) position for text
        text: Text to draw
        font: Font to use
        fill: Text color (RGBA)
        shadow_color: Shadow color (RGBA)
        shadow_offset: Shadow offset in pixels
        shadow_blur: Shadow blur radius
    """
    x, y = position

    # Draw shadow layer
    for offset_x in range(-shadow_blur, shadow_blur + 1):
        for offset_y in range(-shadow_blur, shadow_blur + 1):
            if offset_x * offset_x + offset_y * offset_y <= shadow_blur * shadow_blur:
                alpha = shadow_color[3] // (shadow_blur * shadow_blur + 1)
                shadow_with_alpha = (*shadow_color[:3], alpha)
                draw.text((x + shadow_offset + offset_x, y + shadow_offset + offset_y), text, font=font, fill=shadow_with_alpha)

    # Draw main text
    draw.text(position, text, font=font, fill=fill)


def draw_text_with_stroke(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int] = (255, 255, 255, 255),
    stroke_color: tuple[int, int, int, int] = (0, 0, 0, 255),
    stroke_width: int = 3
) -> None:
    """Draw text with stroke/outline effect.

    Args:
        draw: PIL ImageDraw object
        position: (x, y) position for text
        text: Text to draw
        font: Font to use
        fill: Text color (RGBA)
        stroke_color: Stroke color (RGBA)
        stroke_width: Stroke width in pixels
    """
    x, y = position

    # Draw stroke by drawing text in 8 directions
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)

    # Draw main text
    draw.text(position, text, font=font, fill=fill)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrap text to fit within max_width.

    Args:
        text: Text to wrap
        font: Font to use for measuring
        max_width: Maximum width in pixels

    Returns:
        List of text lines
    """
    lines = []
    current_line = ""

    for char in text:
        test_line = current_line + char
        bbox = font.getbbox(test_line)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char

    if current_line:
        lines.append(current_line)

    return lines if lines else [text]


def generate_thumbnail(
    video_path: Path,
    title: str,
    output_path: Path,
    platform: str = "tiktok",
    font_path: str | Path | None = None,
    brand: str | None = None
) -> Path:
    """Generate a thumbnail image for a video.

    Args:
        video_path: Path to video file
        title: Chinese title for the thumbnail
        output_path: Path to save the thumbnail
        platform: Platform name for sizing (tiktok, instagram, reels)
        font_path: Path to Chinese font file (optional, auto-detected if not provided)
        brand: Optional brand name to display

    Returns:
        Path to the generated thumbnail

    Raises:
        RuntimeError: If thumbnail generation fails
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get configuration
    config = get_thumbnail_config()
    platform_config = get_platform_config(platform)

    # Determine font
    if font_path:
        font_path = Path(font_path)
    elif config.font_path:
        font_path = Path(config.font_path)
    else:
        raise RuntimeError(
            "No Chinese font found. Please install a Chinese font or set THUMBNAIL_FONT environment variable. "
            "Recommended: Download 站酷高端黑 from https://www.zcool.com.cn/special/zcoolfonts/"
        )

    # Extract first frame
    temp_frame = output_path.with_suffix(".temp_frame.jpg")
    try:
        extract_first_frame(video_path, temp_frame)
    except RuntimeError:
        raise RuntimeError("Failed to extract first frame from video")

    try:
        # Load and resize image
        with Image.open(temp_frame) as img:
            # Convert to RGBA
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # Resize to platform dimensions (cover fit)
            target_width = platform_config.width
            target_height = int(platform_config.height * 0.6)  # Use 60% height for thumbnail

            # Calculate crop dimensions (center crop)
            img_ratio = img.width / img.height
            target_ratio = target_width / target_height

            if img_ratio > target_ratio:
                # Image is wider, crop sides
                new_height = img.height
                new_width = int(new_height * target_ratio)
                left = (img.width - new_width) // 2
                top = 0
            else:
                # Image is taller, crop top/bottom
                new_width = img.width
                new_height = int(new_width / target_ratio)
                left = 0
                top = (img.height - new_height) // 2

            img = img.crop((left, top, left + new_width, top + new_height))
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            # Add gradient overlay at bottom
            gradient = create_gradient_mask((target_width, target_height), direction="bottom")
            img = Image.alpha_composite(img, gradient)

            # Load fonts
            try:
                font_title = ImageFont.truetype(str(font_path), config.font_size_title)
                font_brand = ImageFont.truetype(str(font_path), config.font_size_subtitle)
            except OSError as e:
                raise RuntimeError(f"Failed to load font {font_path}: {e}")

            # Create drawing context
            draw = ImageDraw.Draw(img)

            # Wrap and draw title
            margin = 40
            max_text_width = target_width - 2 * margin
            lines = wrap_text(title, font_title, max_text_width)

            # Calculate total text height
            line_height = config.font_size_title + 10
            total_height = len(lines) * line_height

            # Position text at bottom with margin
            text_y = target_height - total_height - margin

            for line in lines:
                # Center the text
                bbox = font_title.getbbox(line)
                text_width = bbox[2] - bbox[0]
                text_x = (target_width - text_width) // 2

                # Draw text with stroke for better visibility
                draw_text_with_stroke(
                    draw,
                    (text_x, text_y),
                    line,
                    font_title,
                    fill=(255, 255, 255, 255),
                    stroke_color=(0, 0, 0, 200),
                    stroke_width=3
                )
                text_y += line_height

            # Draw brand if provided
            if brand:
                brand_y = margin // 2
                bbox = font_brand.getbbox(brand)
                brand_width = bbox[2] - bbox[0]
                brand_x = (target_width - brand_width) // 2
                draw_text_with_stroke(
                    draw,
                    (brand_x, brand_y),
                    brand,
                    font_brand,
                    fill=(255, 255, 255, 230),
                    stroke_color=(0, 0, 0, 180),
                    stroke_width=2
                )

            # Convert to RGB and save
            img_rgb = Image.new("RGB", img.size, (0, 0, 0))
            img_rgb.paste(img, mask=img.split()[3])
            img_rgb.save(output_path, "JPEG", quality=95)

    finally:
        # Clean up temp file
        if temp_frame.exists():
            temp_frame.unlink()

    return output_path
