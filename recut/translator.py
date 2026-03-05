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
