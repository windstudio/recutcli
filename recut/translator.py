# recut/translator.py
"""Translation and content refinement using GLM-5 API."""

from datetime import datetime
from pathlib import Path

from openai import OpenAI


def _get_season(month: int) -> str:
    """Get season name from month number."""
    if month in (3, 4, 5):
        return "春季"
    elif month in (6, 7, 8):
        return "夏季"
    elif month in (9, 10, 11):
        return "秋季"
    else:
        return "冬季"


def get_metadata_generation_prompt(duration: int, english_title: str | None) -> str:
    """Generate prompt for metadata generation.

    Args:
        duration: Target video duration in seconds
        english_title: Optional English title to translate/refine

    Returns:
        Prompt string for LLM
    """
    # Target: ~3.5 Chinese characters per second for natural speech
    # Allow ±5% tolerance for better precision
    target_chars = int(duration * 3.5)
    tolerance = max(3, int(target_chars * 0.05))  # At least 3 chars tolerance
    min_chars = target_chars - tolerance
    max_chars = target_chars + tolerance

    # Get current month and season for seasonal tag
    now = datetime.now()
    current_month = f"{now.month}月"
    season = _get_season(now.month)

    title_instruction = (
        f"英文标题：{english_title}\n请将此英文标题翻译并润色为吸引眼球的中文标题。"
        if english_title
        else "请根据口播文案提炼吸引眼球的中文标题。"
    )

    return f"""你是一位专业的短视频文案创作者。请将以下英文内容翻译成中文，并生成完整的短视频元数据。

{title_instruction}

口播文案要求：
1. 采用"3秒钩子+中间内容+最后总结"的结构
2. 口语化，适合短视频节奏
3. 【重要】总字数精确控制在{min_chars}-{max_chars}字之间（目标{target_chars}字），这是硬性要求
4. 按照自然的语义停顿分行，每行一个小句或短语

标题要求：
- 简洁有力，不超过15个字

标签要求：
5个标签，包括：
- 产品名称或核心品类词（如有品牌则用“品牌+品类”格式），例如“Keychron无线键盘”；
- 1个与主题完全一致且为平台高频搜索词的核心精准标签，例如“轻薄无线键盘”；
- 2个覆盖细分人群与使用场景的中热度长尾标签，例如“程序员键盘推荐”、“办公桌面好物”；
- 1个和当前月份或季节（当前是{current_month}，{season}）、或者和即将到来的节日相关的时效性标签，例如“春日数码焕新”。

严格按照以下格式输出，不要输出其他内容：
---TITLE---
[中文标题]
---TRANSCRIPT---
[口播文案，每行一个小句]
---TAGS---
[标签1,标签2,标签3,...]

英文内容：
{{english_text}}"""


def parse_metadata_response(response: str) -> dict:
    """Parse LLM response into structured metadata.

    Args:
        response: Raw LLM response string

    Returns:
        dict with keys: title, transcript, tags
    """
    result = {"title": "", "transcript": "", "tags": []}

    parts = response.split("---TITLE---")
    if len(parts) < 2:
        raise ValueError("Invalid response format: missing TITLE section")
    content = parts[1]

    parts = content.split("---TRANSCRIPT---")
    if len(parts) < 2:
        raise ValueError("Invalid response format: missing TRANSCRIPT section")
    result["title"] = parts[0].strip()
    content = parts[1]

    parts = content.split("---TAGS---")
    if len(parts) < 2:
        raise ValueError("Invalid response format: missing TAGS section")
    result["transcript"] = parts[0].strip()
    tags_str = parts[1].strip()

    # Parse tags: split by comma and strip whitespace
    result["tags"] = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

    return result


def translate_and_generate_metadata(
    english_text: str,
    api_key: str,
    base_url: str,
    model: str,
    duration: int = 30,
    english_title: str | None = None
) -> dict:
    """Translate English text and generate Chinese metadata (title, transcript, tags).

    Args:
        english_text: English transcript text
        api_key: LLM API key
        base_url: API base URL
        model: Model name
        duration: Target video duration in seconds (default 30)
        english_title: Optional English title to translate/refine

    Returns:
        dict with keys: title (str), transcript (str), tags (list[str])

    Raises:
        RuntimeError: If generation fails
    """
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    try:
        prompt = get_metadata_generation_prompt(duration, english_title)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt.format(english_text=english_text)
                }
            ]
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Metadata generation failed: empty response")
        return parse_metadata_response(content)
    except Exception as e:
        raise RuntimeError(f"Metadata generation failed: {e}")


def save_chinese_script(output_path: str | Path, metadata: dict) -> None:
    """Save Chinese script with metadata to markdown file.

    Args:
        output_path: Path to save the markdown file
        metadata: dict with keys: title, transcript, tags

    Raises:
        ValueError: If metadata is missing required keys
    """
    # Validate required keys
    required_keys = ["title", "transcript", "tags"]
    missing = [k for k in required_keys if k not in metadata]
    if missing:
        raise ValueError(f"metadata missing required keys: {missing}")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Format tags as #tag1 #tag2 ...
    tags_formatted = " ".join(f"#{tag}" for tag in metadata["tags"])

    content = f"""# Title
{metadata["title"]}

# Transcript
{metadata["transcript"]}

# Tags
{tags_formatted}
"""

    path.write_text(content, encoding="utf-8")
