# app/vision.py
import base64
import json
import urllib.request
from app.config import QWEN_API_KEY, QWEN_MODEL, QWEN_API_URL


VISION_SYSTEM_PROMPT = """你是一位数学教师。请仔细识别图片中的所有文字和数学公式。

严格按以下JSON格式输出：
{
  "lines": ["逐行识别出的文本，每行一个字符串"],
  "formulas": ["识别出的数学公式，用LaTeX格式，每个一行"],
  "subject": "高数/线代/概率论（根据内容判断）",
  "knowledge_points": ["涉及的知识点标签"],
  "question_type": "错题/笔记/讲义（根据图片内容判断属于哪种类型）",
  "is_error_question": true或false,
  "student_work": "如果图片中有学生自己的解题过程或答案，原样抄录在这里；如果没有就留空"
}
"""


def _extract_json(text: str) -> dict:
    """Extract JSON object from text that may contain extra content."""
    # Try direct parse first (fastest path)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block ```json ... ```
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            try:
                return json.loads(text[start:end].strip())
            except json.JSONDecodeError:
                pass

    # Try extracting anything between { and } at outermost level
    brace_depth = 0
    start_pos = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if brace_depth == 0:
                start_pos = i
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
            if brace_depth == 0 and start_pos != -1:
                try:
                    return json.loads(text[start_pos:i + 1])
                except json.JSONDecodeError:
                    pass
    raise ValueError("Could not extract valid JSON from response")


def recognize_image(image_bytes: bytes) -> dict:
    img_b64 = base64.b64encode(image_bytes).decode()

    payload = json.dumps({
        "model": QWEN_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                },
                {"type": "text", "text": VISION_SYSTEM_PROMPT},
            ],
        }],
        "max_tokens": 2000,
    }).encode()

    req = urllib.request.Request(QWEN_API_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {QWEN_API_KEY}")

    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())
        content = body["choices"][0]["message"]["content"]
        return _extract_json(content)
