# recut/translator.py
"""Translation and content refinement using GLM-5 API."""

from openai import OpenAI


TRANSLATION_PROMPT = """你是一位专业的短视频文案创作者。请将以下英文内容翻译成中文，并提炼成一段25秒的短视频口播文案。

要求：
1. 采用"3秒钩子+中间内容+最后总结"的结构
2. 语言口语化，适合短视频节奏
3. 总字数控制在70-90字（约25秒语速）
4. 只输出最终的口播文案，不要输出任何解释、分析或结构说明

英文内容：
{english_text}"""


def translate_and_refine(
    english_text: str,
    api_key: str,
    base_url: str = "https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1",
    model: str = "glm-5"
) -> str:
    """Translate English text and refine into 25-second Chinese script.

    Args:
        english_text: English transcript text
        api_key: Yuanjing API key
        base_url: API base URL
        model: Model name

    Returns:
        Chinese script text (about 25 seconds, with hook-body-summary structure)

    Raises:
        RuntimeError: If translation fails
    """
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": TRANSLATION_PROMPT.format(english_text=english_text)
                }
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Translation failed: {e}")
