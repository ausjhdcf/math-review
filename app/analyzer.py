# app/analyzer.py
import json
import urllib.request
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_API_URL
from app.supabase_client import get_analysis_by_knowledge_point


ANALYSIS_SYSTEM_PROMPT = """你是一位考研数学辅导老师，擅长分析学生的错题和梳理知识体系。

对于错题，你需要：
1. 判断学生的解答是否正确，如果错误，指出具体在哪一步开始出错
2. 分类错因：计算粗心、概念不清、方法选错、审题失误、不会做（选一个）
3. 说明为什么学生容易犯这个错误
4. 给出完整正确的解题过程
5. 提供针对性的改进建议
6. 推荐1-2道可以巩固的同类题型

对于讲义，你需要：
1. 总结例题的编排逻辑（从易到难？按知识点分组？）
2. 梳理涉及的知识点及其关联关系
3. 给出基于这份讲义的复习建议

对于笔记，你需要：
1. 提取笔记中的知识点要点
2. 补充可能的遗漏

严格按照以下JSON格式输出分析结果（不要输出任何其他内容）：
{
  "analysis_type": "错题分析/讲义总结/笔记整理",
  "subject": "高数/线代/概率论",
  "knowledge_points": ["标签1", "标签2"],
  "error_category": "计算粗心/概念不清/方法选错/审题失误/不会做（讲义和笔记填空字符串）",
  "error_detail": "详细的错因分析",
  "correct_solution": "正确的解题过程，用LaTeX格式。行内公式用$...$包裹，独立公式用$$...$$包裹，不要使用\\(...\\)或\\[...\\]",
  "suggestions": "改进建议",
  "related_knowledge": ["关联知识点"],
  "similar_problems": [{"description": "题目描述", "hint": "解题提示"}]
}
"""


def build_memory_context(knowledge_points: list[str]) -> str:
    if not knowledge_points:
        return "（无历史记录）"

    all_records = []
    for kp in knowledge_points:
        # Skip empty or overly long knowledge points that could break queries
        if not kp or not kp.strip() or len(kp) > 200:
            continue
        # Skip knowledge points containing characters that would break JSON queries
        bad_chars = ['"', '\\', '\x00', '�']
        if any(c in kp for c in bad_chars):
            continue
        try:
            records = get_analysis_by_knowledge_point(kp, limit=3)
            all_records.extend(records)
        except Exception:
            # Non-critical: query failure should not block analysis
            continue

    if not all_records:
        return "（该知识点无历史错题记录）"

    parts = ["以下是该学生在此知识点及相关领域的**历史错题记录**，请参考这些信息来分析当前题目，注意对比学生的薄弱点是否有改善或有重复错误：\n"]
    for i, rec in enumerate(all_records[:8], 1):
        parts.append(f"[记录{i}] 错因: {rec.get('error_category', '?')} | {rec.get('error_detail', '')[:200]}")
    return "\n".join(parts)


def analyze(
    recognized_text: str,
    knowledge_points: list[str],
    upload_type: str,
    student_work: str = "",
) -> dict:
    memory = build_memory_context(knowledge_points)

    user_message = f"""请分析以下内容：

【类型】{upload_type}
【识别出的内容】
{recognized_text}

【学生自己的解题过程】（如果有）
{student_work if student_work else "（学生未提供解题过程）"}

【历史记忆】
{memory}"""

    payload = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
    }).encode()

    req = urllib.request.Request(DEEPSEEK_API_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {DEEPSEEK_API_KEY}")

    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())
        content = body["choices"][0]["message"]["content"]
        analysis = _extract_json(content)
        analysis["context_used"] = memory
        return analysis


def _extract_json(text: str) -> dict:
    """Extract JSON from model response, handling markdown code blocks."""
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try ```json ... ``` wrapper
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return json.loads(text[start:end].strip())
    # Try ``` ... ``` wrapper
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return json.loads(text[start:end].strip())
    # Try to find outermost { ... }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    raise ValueError(f"Could not extract JSON from: {text[:200]}")
