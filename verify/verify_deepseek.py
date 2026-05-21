"""
验证2：DeepSeek 分析质量
目标：确认 DeepSeek 能否对数学错题做准确的错因诊断
红线：错因归类合理、解法正确、知识点标签准确

使用方法：
  1. 先完成 OCR 验证（verify_ocr.py），拿到识别文本
  2. 设置环境变量: export DEEPSEEK_API_KEY="sk-xxx"
  3. python verify_deepseek.py
"""

import os
import json
import sys

# ============================================================
# 测试用例：模拟 3 道考研数学错题（OCR 识别后的文本形式）
# 用户可替换为自己真实错题的 OCR 结果
# ============================================================
TEST_CASES = [
    {
        "id": "test_1",
        "description": "极限计算 — 等价无穷小误用",
        "ocr_text": """
        求极限 lim(x→0) (tan x - sin x) / x^3
        我的解答：tan x ~ x, sin x ~ x，所以原式 = lim(x→0) (x - x) / x^3 = 0
        但答案是 1/2，我不知道哪里错了
        """,
        "expected_error": "等价无穷小替换条件不满足/精度不够",
    },
    {
        "id": "test_2",
        "description": "中值定理证明题",
        "ocr_text": """
        设 f(x) 在 [a,b] 上连续，在 (a,b) 内可导，f(a)=f(b)=0，
        证明：存在 ξ∈(a,b) 使得 f'(ξ) + f(ξ) = 0
        我不会做这道题
        """,
        "expected_error": "不知道如何构造辅助函数",
    },
    {
        "id": "test_3",
        "description": "二重积分换序",
        "ocr_text": """
        计算二重积分 ∫(0→1)dx ∫(x→1) e^(y^2) dy
        我直接对 y 积分积不出来
        """,
        "expected_error": "不知道交换积分次序",
    },
]

SYSTEM_PROMPT = """你是一位考研数学辅导老师，擅长分析学生的错题。

对于学生提交的每道题，请严格按以下 JSON 格式输出分析结果：

{
  "question_type": "错题 / 不会做的题 / 笔记",
  "subject": "高数 / 线代 / 概率论",
  "knowledge_points": ["知识点1", "知识点2"],
  "error_analysis": {
    "error_category": "计算粗心 / 概念不清 / 方法选错 / 审题失误 / 不会做",
    "error_step": "具体哪一步出错了",
    "root_cause": "出错的根本原因，用通俗语言解释",
    "why_wrong": "为什么这个错误会导致结果不对"
  },
  "correct_solution": "完整正确的解题过程",
  "improvement": "针对性的改进建议，包括复习方向",
  "similar_problem_hint": "推荐1-2道可以巩固的同类题型"
}

要求：
- 解题过程使用 LaTeX 数学公式（$$...$$）
- 改进建议要具体可执行，不要泛泛而谈
- 如果学生写了过程但错了，务必指出"从哪一步开始出错"以及"为什么会犯这个错"
"""


def analyze_with_deepseek(ocr_text: str, api_key: str) -> dict:
    """调用 DeepSeek API 分析错题"""
    import urllib.request
    import urllib.error

    url = "https://api.deepseek.com/v1/chat/completions"
    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请分析下面这道题：\n\n{ocr_text}"},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return json.loads(content)
    except urllib.error.HTTPError as e:
        print(f"  API 请求失败: {e.code} {e.reason}")
        print(f"  {e.read().decode()}")
        return {}
    except Exception as e:
        print(f"  请求异常: {e}")
        return {}


def evaluate_analysis(result: dict, expected_error: str) -> dict:
    """人工辅助评估分析质量（最终判断由人做）"""
    checks = {
        "has_error_category": bool(result.get("error_analysis", {}).get("error_category")),
        "has_correct_solution": bool(result.get("correct_solution")),
        "has_knowledge_points": bool(result.get("knowledge_points")),
        "has_improvement": bool(result.get("improvement")),
    }
    all_ok = all(checks.values())
    return {"checks": checks, "all_fields_present": all_ok}


def main():
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("=" * 60)
        print("  [!!] 未设置 DEEPSEEK_API_KEY")
        print("  请执行: export DEEPSEEK_API_KEY='sk-xxx'")
        print("  获取 Key: https://platform.deepseek.com/api_keys")
        print("=" * 60)
        sys.exit(1)

    print(f"DeepSeek API Key: {api_key[:8]}...{api_key[-4:]}\n")

    all_passed = True
    for case in TEST_CASES:
        print(f"--- {case['description']} ---")
        print(f"  识别文本: {case['ocr_text'][:150].strip()}...")

        result = analyze_with_deepseek(case["ocr_text"], api_key)
        if not result:
            print(f"  [!!] 分析失败\n")
            all_passed = False
            continue

        eval_result = evaluate_analysis(result, case["expected_error"])

        print(f"  学科: {result.get('subject', '?')}")
        print(f"  知识点: {result.get('knowledge_points', [])}")
        print(f"  错因分类: {result.get('error_analysis', {}).get('error_category', '?')}")
        print(f"  根本原因: {result.get('error_analysis', {}).get('root_cause', '?')[:100]}")
        print(f"  正确解法: {result.get('correct_solution', '?')[:150]}")
        print(f"  改进建议: {result.get('improvement', '?')[:100]}")

        checks = eval_result["checks"]
        for field, ok in checks.items():
            print(f"    {'[OK]' if ok else '[!!]'} {field}")

        if eval_result["all_fields_present"]:
            print(f"  [OK] 字段完整\n")
        else:
            print(f"  [!!] 缺失字段\n")
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("  [OK] DeepSeek 分析验证通过")
        print("  请人工检查输出的解法正确性和错因合理性")
    else:
        print("  [!!] 部分用例未通过，请检查输出")
    print("=" * 60)


if __name__ == "__main__":
    main()
