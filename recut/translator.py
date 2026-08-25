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


# TTS engine character rate coefficients (chars per second)
# Based on testing: edge is baseline at 3.5 chars/sec
# minimax speaks faster, needs more characters for same duration
TTS_CHAR_RATES = {
    "edge": 3.5,
    "minimax": 4.5,  # ~29% faster than edge
    "coqui": 3.5,    # similar to edge
}


def get_metadata_generation_prompt(
    duration: int,
    english_title: str | None,
    chs_title: str | None = None,
    tts_engine: str | None = None
) -> str:
    """Generate prompt for metadata generation.

    Args:
        duration: Target video duration in seconds
        english_title: Optional English title to translate/refine
        chs_title: Optional Chinese title to use directly
        tts_engine: TTS engine name for character rate adjustment

    Returns:
        Prompt string for LLM
    """
    # Get character rate for the TTS engine
    char_rate = TTS_CHAR_RATES.get(tts_engine, TTS_CHAR_RATES["edge"])
    target_chars = int(duration * char_rate)
    tolerance = max(3, int(target_chars * 0.05))  # At least 3 chars tolerance
    min_chars = target_chars - tolerance
    max_chars = target_chars + tolerance

    # Get current month and season for seasonal tag
    now = datetime.now()
    current_month = f"{now.month}月"
    season = _get_season(now.month)

    # Title instruction based on available titles
    if chs_title and chs_title.strip():
        title_instruction = f"中文标题：{chs_title}\n请直接使用此中文标题，无需翻译或修改。"
    elif english_title:
        title_instruction = f"英文标题：{english_title}\n请将此英文标题翻译并润色为吸引眼球的中文标题。"
    else:
        title_instruction = "请根据口播文案提炼吸引眼球的中文标题。"

    return f"""你是一位专业的短视频文案创作者。请将以下英文内容翻译成中文，并生成完整的短视频元数据。

{title_instruction}

口播文案要求：
1. 采用"3秒钩子+中间内容+最后总结"的结构
2. 口语化，适合短视频节奏
3. 【硬性约束】总字数必须严格控制在{min_chars}-{max_chars}字之间，目标{target_chars}字。超出此范围的输出将被拒绝。
4. 3秒钩子吸睛、抓人，自带好奇、利益、反差、痛点其中一种
5. 按照自然的语义停顿分行，每行一个小句或短语
6. 英文内容为语音识别结果，其中的品牌或型号可能不准确，如有中文/英文标题且其中包含品牌或型号，请以中文/英文标题中的品牌和型号为准

标题要求：
- 简洁有力，不超过15个字

标签要求：
5个标签，包括：
- 产品名称或核心品类词（如有品牌则用“品牌+品类”格式），例如“Keychron无线键盘”
- 1个与主题完全一致且为平台高频搜索词的核心精准标签，例如“轻薄无线键盘”
- 2个覆盖细分人群与使用场景的中热度长尾标签，例如“程序员键盘推荐”、“办公桌面好物”
- 1个和当前月份或季节（当前是{current_month}，{season}）、或者和即将到来的节日相关的时效性标签，例如“春日数码焕新”

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


def _count_chars(text: str) -> int:
    """Count Chinese characters in text, excluding whitespace and punctuation.

    Args:
        text: Text to count

    Returns:
        Character count
    """
    # Remove whitespace and newlines
    text = text.replace(" ", "").replace("\n", "")
    return len(text)


def _get_revision_prompt(
    transcript: str,
    min_chars: int,
    max_chars: int,
    target_chars: int,
    action: str
) -> str:
    """Generate prompt for transcript revision.

    Args:
        transcript: Current transcript text
        min_chars: Minimum allowed characters
        max_chars: Maximum allowed characters
        target_chars: Target character count
        action: "compress" or "expand"

    Returns:
        Prompt string for LLM
    """
    if action == "compress":
        instruction = f"以下口播文案字数过多，请压缩到{min_chars}-{max_chars}字（目标{target_chars}字）。保留核心信息和吸引力，删除冗余内容。"
    else:
        instruction = f"以下口播文案字数不足，请扩充到{min_chars}-{max_chars}字（目标{target_chars}字）。增加细节和描述，保持口语化风格。"

    return f"""{instruction}

严格要求：
- 最终字数必须在{min_chars}-{max_chars}字之间
- 保持"3秒钩子+中间内容+最后总结"的结构
- 保持口语化、适合短视频节奏
- 按照自然的语义停顿分行，每行一个小句

原口播文案：
{transcript}

请直接输出修改后的口播文案，不要输出其他内容："""


def translate_and_generate_metadata(
    english_text: str,
    api_key: str,
    base_url: str,
    model: str,
    duration: int = 30,
    english_title: str | None = None,
    chs_title: str | None = None,
    tts_engine: str | None = None,
    max_retries: int = 3
) -> dict:
    """Translate English text and generate Chinese metadata (title, transcript, tags).

    Args:
        english_text: English transcript text
        api_key: LLM API key
        base_url: API base URL
        model: Model name
        duration: Target video duration in seconds (default 30)
        english_title: Optional English title to translate/refine
        chs_title: Optional Chinese title to override LLM-generated title
        tts_engine: TTS engine name for character rate adjustment
        max_retries: Maximum number of retries for character count adjustment (default 3)

    Returns:
        dict with keys: title (str), transcript (str), tags (list[str])

    Raises:
        RuntimeError: If generation fails
    """
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    # Calculate target character count
    char_rate = TTS_CHAR_RATES.get(tts_engine, TTS_CHAR_RATES["edge"])
    target_chars = int(duration * char_rate)
    tolerance = max(3, int(target_chars * 0.05))
    min_chars = target_chars - tolerance
    max_chars = target_chars + tolerance

    try:
        prompt = get_metadata_generation_prompt(duration, english_title, chs_title, tts_engine)
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
        result = parse_metadata_response(content)

        # Validate and adjust transcript character count
        char_count = _count_chars(result["transcript"])
        retry_count = 0

        while (char_count < min_chars or char_count > max_chars) and retry_count < max_retries:
            action = "compress" if char_count > max_chars else "expand"
            print(f"Transcript has {char_count} chars (target: {min_chars}-{max_chars}), {action}ing... (attempt {retry_count + 1}/{max_retries})")

            revision_prompt = _get_revision_prompt(
                result["transcript"],
                min_chars,
                max_chars,
                target_chars,
                action
            )
            revision_response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": revision_prompt}]
            )
            revised_transcript = revision_response.choices[0].message.content
            if revised_transcript:
                result["transcript"] = revised_transcript.strip()
                char_count = _count_chars(result["transcript"])

            retry_count += 1

        # Final status
        if char_count < min_chars or char_count > max_chars:
            print(f"Warning: Could not achieve target character count after {max_retries} retries. Final count: {char_count} chars")
        else:
            print(f"Transcript character count: {char_count} (target: {min_chars}-{max_chars})")

        # Override title if chs_title is provided (exclude whitespace-only strings)
        if chs_title and chs_title.strip():
            result["title"] = chs_title

        return result
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Metadata generation failed: {e}") from e


def save_chinese_script(output_path: str | Path, metadata: dict, source_url: str | None = None) -> None:
    """Save Chinese script with metadata to markdown file.

    Args:
        output_path: Path to save the markdown file
        metadata: dict with keys: title, transcript, tags
        source_url: Optional source URL to include in the file

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

    if source_url:
        content += f"\n# Source URL\n{source_url}\n"

    path.write_text(content, encoding="utf-8")


def parse_chinese_script(path: Path) -> dict:
    """Parse user-edited Chinese script markdown file.

    Args:
        path: Path to the markdown file

    Returns:
        dict with keys: title, transcript, tags, source_url (optional)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If required sections are missing
    """
    if not path.exists():
        raise FileNotFoundError(f"Chinese script file not found: {path}")

    content = path.read_text(encoding="utf-8")
    result: dict = {"title": "", "transcript": "", "tags": [], "source_url": None}

    # Parse sections by headers
    lines = content.split("\n")
    current_section = None
    section_content: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            # Save previous section content
            if current_section and section_content:
                _set_section_content(result, current_section, section_content)
            # Start new section
            current_section = stripped[2:].lower()
            section_content = []
        elif current_section:
            section_content.append(line)

    # Save last section
    if current_section and section_content:
        _set_section_content(result, current_section, section_content)

    # Validate required fields
    if not result["title"]:
        raise ValueError("Chinese script missing 'Title' section")
    if not result["transcript"]:
        raise ValueError("Chinese script missing 'Transcript' section")

    return result


def _set_section_content(result: dict, section: str, content: list[str]) -> None:
    """Set section content in result dict.

    Args:
        result: Result dictionary to update
        section: Section name (lowercase)
        content: List of content lines
    """
    text = "\n".join(content).strip()

    if section == "title":
        result["title"] = text
    elif section == "transcript":
        result["transcript"] = text
    elif section == "tags":
        # Parse tags: extract from #tag format or comma-separated
        tags = []
        for part in text.split():
            if part.startswith("#"):
                tags.append(part[1:])  # Remove # prefix
            else:
                # Handle comma-separated format
                for tag in part.split(","):
                    tag = tag.strip()
                    if tag:
                        tags.append(tag)
        result["tags"] = tags
    elif section in ("source url", "source_url", "source"):
        result["source_url"] = text if text else None
