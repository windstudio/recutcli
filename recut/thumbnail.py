"""Thumbnail generation for social media videos."""

import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from recut.config import get_thumbnail_config, get_platform_config
from recut.downloader import get_ffmpeg_path


# === Constants ===
GRADIENT_TOP_COLOR = (60, 70, 90)  # 蓝灰色
GRADIENT_BOTTOM_COLOR = (0, 0, 0)  # 黑色

# Font error message
FONT_ERROR_MSG = (
    "No Chinese font found. Please install a Chinese font or set THUMBNAIL_FONT environment variable. "
    "Recommended: Download 站酷小薇体 from https://www.zcool.com.cn/special/zcoolfonts/"
)


def _load_font(font_path: Path | str | None, font_size: int) -> ImageFont.FreeTypeFont:
    """Load font from path or config.

    Args:
        font_path: Path to font file (optional, uses config if not provided)
        font_size: Font size in pixels

    Returns:
        Loaded font object

    Raises:
        RuntimeError: If no font is available or loading fails
    """
    config = get_thumbnail_config()

    if font_path:
        font_path = Path(font_path)
    elif config.font_path:
        font_path = Path(config.font_path)
    else:
        raise RuntimeError(FONT_ERROR_MSG)

    try:
        return ImageFont.truetype(str(font_path), font_size)
    except OSError as e:
        raise RuntimeError(f"Failed to load font {font_path}: {e}")


def _save_as_jpeg(img: Image.Image, output_path: Path, quality: int = 95) -> None:
    """Save RGBA image as JPEG (converts to RGB first).

    Args:
        img: PIL Image (should be RGBA mode)
        output_path: Path to save the image
        quality: JPEG quality (1-100)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if img.mode == "RGBA":
        rgb_img = Image.new("RGB", img.size, (0, 0, 0))
        rgb_img.paste(img, mask=img.split()[3])
        img = rgb_img

    img.save(output_path, "JPEG", quality=quality)


def _create_gradient_image(
    size: tuple[int, int],
    top_color: tuple[int, int, int] = GRADIENT_TOP_COLOR,
    bottom_color: tuple[int, int, int] = GRADIENT_BOTTOM_COLOR
) -> Image.Image:
    """Create a vertical gradient image efficiently.

    Uses PIL's resize method for better performance than pixel-by-pixel drawing.

    Args:
        size: (width, height) of the output image
        top_color: RGB color at the top
        bottom_color: RGB color at the bottom

    Returns:
        RGBA gradient image
    """
    width, height = size

    # Create a small gradient (1 pixel wide, full height) and resize horizontally
    # This is much faster than drawing line by line
    gradient = Image.new("RGBA", (1, height))
    pixels = gradient.load()

    for y in range(height):
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        pixels[0, y] = (r, g, b, 255)

    # Resize to full width
    return gradient.resize((width, height), Image.Resampling.BILINEAR)


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

    # 先按 \n 分割
    paragraphs = text.split('\n')

    for paragraph in paragraphs:
        if not paragraph:
            continue
        current_line = ""

        for char in paragraph:
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
    video_path: Path | None = None,
    title: str = "",
    output_path: Path | None = None,
    platform: str = "tiktok",
    font_path: str | Path | None = None,
    image_path: Path | None = None
) -> Path:
    """Generate a thumbnail image for a video.

    The thumbnail is in vertical format (9:16 aspect ratio) for social media platforms.
    For horizontal video frames, applies blur background to fill the vertical canvas.

    Args:
        video_path: Path to video file (optional if image_path is provided)
        title: Chinese title for the thumbnail
        output_path: Path to save the thumbnail
        platform: Platform name for sizing (tiktok, instagram, reels)
        font_path: Path to Chinese font file (optional, auto-detected if not provided)
        image_path: Path to main image for slanted poster generation (optional)

    Returns:
        Path to the generated thumbnail

    Raises:
        RuntimeError: If thumbnail generation fails
    """
    output_path = Path(output_path) if output_path else None
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # If image_path is provided, generate slanted poster
    if image_path:
        return generate_slanted_poster(
            main_image_path=Path(image_path),
            title=title,
            output_path=output_path,
            platform=platform,
            font_path=font_path
        )

    # Original logic: generate from video first frame
    if not video_path:
        raise RuntimeError("Either video_path or image_path must be provided")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get configuration
    config = get_thumbnail_config()
    platform_config = get_platform_config(platform)

    # Load font using helper function
    font_title = _load_font(font_path, config.font_size_title)

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

            # Target dimensions (full vertical video size)
            target_width = platform_config.width
            target_height = platform_config.height

            img_ratio = img.width / img.height
            target_ratio = target_width / target_height

            if img_ratio > target_ratio:
                # Image is wider than target (horizontal video)
                # Scale image to fit height, then add blurred background for sides
                img_resized = img.resize(
                    (int(target_height * img_ratio), target_height),
                    Image.Resampling.LANCZOS
                )

                # Create blurred background from a cropped portion
                background = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                background = background.filter(ImageFilter.GaussianBlur(radius=30))

                # Paste resized image in center
                paste_x = (target_width - img_resized.width) // 2
                background.paste(img_resized, (paste_x, 0), img_resized if img_resized.mode == "RGBA" else None)
                img = background
            else:
                # Image is taller than target (vertical video)
                # Center crop to fit
                new_width = img.width
                new_height = int(new_width / target_ratio)
                if new_height > img.height:
                    new_height = img.height
                    new_width = int(new_height * target_ratio)
                left = (img.width - new_width) // 2
                top = (img.height - new_height) // 2
                img = img.crop((left, top, left + new_width, top + new_height))
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            # Add gradient overlay at bottom
            gradient = create_gradient_mask((target_width, target_height), direction="bottom")
            img = Image.alpha_composite(img, gradient)

            # Create drawing context
            draw = ImageDraw.Draw(img)

            # Wrap and draw title
            margin = 40
            max_text_width = target_width - 2 * margin
            lines = wrap_text(title, font_title, max_text_width)

            # Calculate total text height
            line_height = config.font_size_title + 10
            total_height = len(lines) * line_height

            # Position text at bottom but higher up to avoid UI overlays
            # Leave more space from bottom (20% of height instead of just margin)
            text_y = target_height - total_height - int(target_height * 0.2)

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

            # Save using helper function
            _save_as_jpeg(img, output_path)

    finally:
        # Clean up temp file
        if temp_frame.exists():
            temp_frame.unlink()

    return output_path


def create_slanted_mask(size: tuple[int, int], angle: float = -5.0) -> Image.Image:
    """Create a slanted polygon mask for image cropping.

    Args:
        size: (width, height) of the mask
        angle: Slant angle in degrees (negative = left side slants down)

    Returns:
        RGBA mask image with slanted polygon
    """
    width, height = size
    # 斜边角度是相对于水平线的，所以 offset = width * tan(angle)
    offset = int(math.tan(abs(angle) * math.pi / 180) * width)

    # Create points for the polygon (for -5°, left side slants down)
    # Points must be in clockwise order for PIL polygon fill
    if angle < 0:
        points = [
            (width, 0),               # 右上
            (width, height - offset), # 右下
            (0, height),              # 左下
            (0, offset),              # 左上
        ]
    else:
        points = [
            (width, offset),          # 右上
            (width, height),          # 右下
            (0, height - offset),     # 左下
            (0, 0),                   # 左上
        ]

    # Create mask with polygon
    mask = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(mask)
    draw.polygon(points, fill=(255, 255, 255, 255))

    return mask


def generate_slanted_poster(
    main_image_path: Path,
    title: str,
    output_path: Path,
    platform: str = "tiktok",
    canvas_width: int | None = None,
    canvas_height: int | None = None,
    angle: float = -5.0,
    font_path: Path | None = None,
    font_size: int | None = None
) -> Path:
    """Generate a slanted poster thumbnail with main image and title.

    Args:
        main_image_path: Path to the main image (product photo)
        title: Chinese title for the poster
        output_path: Path to save the poster
        platform: Platform name for sizing
        canvas_width: Canvas width (default from platform config)
        canvas_height: Canvas height (default from platform config)
        angle: Slant angle in degrees (default -5°)
        font_path: Path to Chinese font file
        font_size: Font size for title

    Returns:
        Path to the generated poster
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get platform dimensions
    platform_config = get_platform_config(platform)
    canvas_width = canvas_width or platform_config.width
    canvas_height = canvas_height or platform_config.height

    # Get font configuration and load font using helper
    config = get_thumbnail_config()
    font_size = font_size or config.font_size_title
    font = _load_font(font_path, font_size)

    # Load main image and scale to canvas width
    with Image.open(main_image_path) as main_img:
        if main_img.mode != "RGBA":
            main_img = main_img.convert("RGBA")

        # Scale image to fit canvas width while maintaining aspect ratio
        # Image width should match canvas width for full coverage
        if main_img.width != canvas_width:
            scale_ratio = canvas_width / main_img.width
            new_height = int(main_img.height * scale_ratio)
            main_img = main_img.resize((canvas_width, new_height), Image.Resampling.LANCZOS)

        # Create gradient background using optimized helper function
        canvas = _create_gradient_image((canvas_width, canvas_height))

        # Create slanted mask for main image
        main_mask = create_slanted_mask((main_img.width, main_img.height), angle)

        # Apply mask to main image
        main_img_masked = Image.new("RGBA", main_img.size, (0, 0, 0, 0))
        main_img_masked.paste(main_img, (0, 0), main_mask)

        # Calculate paste position (画面上部20%位置)
        paste_x = (canvas_width - main_img.width) // 2
        paste_y = int(canvas_height * 0.2)

        # Paste main image onto canvas
        canvas.paste(main_img_masked, (paste_x, paste_y), main_img_masked)

        # Wrap text and calculate dimensions
        margin = 60
        max_text_width = canvas_width - 2 * margin
        lines = wrap_text(title, font, max_text_width)

        line_height = font_size + 20
        total_text_height = len(lines) * line_height

        # Create title layer
        # 扩大高度以容纳斜切后的文字（竖直方向斜切）
        skew_k = math.tan(abs(angle) * math.pi / 180)  # 斜切系数（正值）
        extra_height = int(canvas_width * skew_k)  # 斜切后需要额外高度
        title_layer_width = canvas_width + 100
        title_layer_height = total_text_height + extra_height + 50
        title_layer = Image.new("RGBA", (title_layer_width, title_layer_height), (0, 0, 0, 0))

        # Draw title text
        draw = ImageDraw.Draw(title_layer)
        text_y = extra_height // 2 + 10  # 留出空间给斜切
        for line in lines:
            bbox = font.getbbox(line)
            text_width = bbox[2] - bbox[0]
            text_x = (title_layer_width - text_width) // 2

            # Draw white text with black stroke
            draw.text(
                (text_x, text_y),
                line,
                font=font,
                fill=(255, 255, 255, 255),
                stroke_width=5,
                stroke_fill=(0, 0, 0)
            )
            text_y += line_height

        # Apply skew transform (竖直方向斜切，左低右高)
        # AFFINE matrix: (a, b, c, d, e, f) where:
        # x' = a*x + b*y + c
        # y' = d*x + e*y + f
        # 左低右高：左边y增大（向下），右边y不变
        # y' = skew_k * (x - width) + y = skew_k * x + y - skew_k * width
        title_skewed = title_layer.transform(
            (title_layer_width, title_layer_height),
            Image.AFFINE,
            (1, 0, 0, skew_k, 1, -skew_k * title_layer_width),
            Image.BICUBIC
        )

        # Apply slanted mask to skewed title
        title_mask = create_slanted_mask(title_skewed.size, angle)
        title_layer_masked = Image.new("RGBA", title_skewed.size, (0, 0, 0, 0))
        title_layer_masked.paste(title_skewed, (0, 0), title_mask)

        # Position title layer below main image (主图下方，稍微重叠)
        # 使用 canvas_width 计算居中位置，而不是 title_layer_masked.width
        title_x = (canvas_width - title_layer_width) // 2
        title_y = paste_y + main_img_masked.height - int(main_img_masked.height * 0.15)  # 上移进入主图区域

        # Paste title layer onto canvas
        canvas.paste(title_layer_masked, (title_x, title_y), title_layer_masked)

        # Save using helper function
        _save_as_jpeg(canvas, output_path)

    return output_path
