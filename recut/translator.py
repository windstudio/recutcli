# recut/translator.py
"""Translation and content refinement using GLM-5 API."""

from openai import OpenAI


def get_translation_prompt(duration: int) -> str:
    """Generate translation prompt for the specified duration.

    Args:
        duration: Target video duration in seconds

    Returns:
        Translation prompt string
    """
    # Approximate word count: ~3.5-4 Chinese characters per second for natural speech
    min_chars = int(duration * 3.2)
    max_chars = int(duration * 4.0)

    return f"""你是一位专业的短视频文案创作者。请将以下英文内容翻译成中文，并提炼成一段{duration}秒的短视频口播文案。

要求：
1. 采用"3秒钩子+中间内容+最后总结"的结构
2. 语言口语化，适合短视频节奏
3. 总字数控制在{min_chars}-{max_chars}字（约{duration}秒语速，确保填满整个视频时长）
4. 只输出最终的口播文案，不要输出任何解释、分析或结构说明
5. 按照自然的语义停顿分行，每行一个小句或短语（约10-18字），方便后续生成字幕

输出格式示例：
第一句钩子文案
第二句内容
第三句内容
第四句内容
第五句内容
最后一句总结

英文内容：
{{english_text}}"""


def get_metadata_generation_prompt(duration: int, english_title: str | None) -> str:
    """Generate prompt for metadata generation.

    Args:
        duration: Target video duration in seconds
        english_title: Optional English title to translate/refine

    Returns:
        Prompt string for LLM
    """
    min_chars = int(duration * 3.2)
    max_chars = int(duration * 4.0)

    title_instruction = (
        f"英文标题：{english_title}\n请将此英文标题翻译并润色为一个简洁、有吸引力的中文标题。"
        if english_title
        else "请根据口播文案提炼一个简洁、有吸引力的中文标题。"
    )

    return f"""你是一位专业的短视频文案创作者。请将以下英文内容翻译成中文，并生成完整的短视频元数据。

{title_instruction}

要求：
1. 口播文案采用"3秒钩子+中间内容+最后总结"的结构
2. 语言口语化，适合短视频节奏
3. 口播文案总字数控制在{min_chars}-{max_chars}字（约{duration}秒语速）
4. 标题要求：简洁有吸引力，不超过15个字
5. 标签要求：8个左右，涵盖产品类别、产品名称、品牌名称、其他关键词
6. 按照自然的语义停顿分行，每行一个小句或短语

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
    base_url: str = "https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1",
    model: str = "glm-5",
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


def translate_and_refine(
    english_text: str,
    api_key: str,
    base_url: str = "https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1",
    model: str = "glm-5",
    duration: int = 30
) -> str:
    """Translate English text and refine into Chinese script.

    Args:
        english_text: English transcript text
        api_key: Yuanjing API key
        base_url: API base URL
        model: Model name
        duration: Target video duration in seconds (default 30)

    Returns:
        Chinese script text (about specified duration, with hook-body-summary structure)

    Raises:
        RuntimeError: If translation fails
    """
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    try:
        prompt = get_translation_prompt(duration)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt.format(english_text=english_text)
                }
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Translation failed: {e}")


def save_chinese_script(output_path, metadata: dict) -> None:
    """Save Chinese script with metadata to markdown file.

    Args:
        output_path: Path to save the markdown file
        metadata: dict with keys: title, transcript, tags
    """
    from pathlib import Path

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
