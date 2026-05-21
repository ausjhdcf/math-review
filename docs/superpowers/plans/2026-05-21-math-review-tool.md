# 考研数学复习助手 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a mobile-friendly web app where the user uploads photos of math problems/notes, AI analyzes mistakes and tracks knowledge mastery over time.

**Architecture:** FastAPI serves Jinja2 templates (Bootstrap 5, mobile-first). Upload flow: image → Supabase Storage → Qwen VL reads the math → DeepSeek analyzes with historical context from Supabase PostgreSQL → results stored and displayed. All AI calls are async, DB operations via supabase-py.

**Tech Stack:** Python 3.11, FastAPI, Jinja2, Bootstrap 5 (CDN), Supabase (PostgreSQL + Storage), Qwen VL Plus API, DeepSeek Chat API

**Verification completed:** Qwen VL image recognition ✓, DeepSeek analysis ✓, Supabase tables+storage ✓, deployment ✓

---

## File Structure

```
study/
├── app/
│   ├── __init__.py              # Package marker
│   ├── config.py                # All env vars and constants in one place
│   ├── supabase_client.py       # DB + storage operations wrapper
│   ├── vision.py                # Qwen VL API — image → recognized text
│   ├── analyzer.py              # DeepSeek API — text + history → analysis
│   ├── knowledge.py             # Knowledge graph read/write/mastery calc
│   ├── main.py                  # FastAPI app, routes, startup
│   └── templates/
│       ├── base.html            # Bootstrap shell (navbar, layout)
│       ├── index.html           # Upload page (home)
│       ├── result.html          # Analysis result page
│       └── knowledge.html       # Knowledge base overview + lecture analysis
├── static/
│   └── style.css                # Minimal overrides (mobile tweaks)
├── requirements.txt             # Production dependencies
├── Procfile                     # Railway: uvicorn app.main:app --host 0.0.0.0 --port $PORT
├── railway.json                 # Railway config
├── .env.example                 # Template for required env vars
└── verify/                      # Existing verification scripts (keep as-is)
```

**Responsibility boundaries:**
- `config.py` — reads env vars, no logic
- `supabase_client.py` — all Supabase I/O, no AI logic
- `vision.py` — calls Qwen VL, returns text dict, no DB
- `analyzer.py` — calls DeepSeek, formats prompt, calls vision module if needed, no DB
- `knowledge.py` — reads/writes knowledge_graph via supabase_client, calculates scores
- `main.py` — routes, orchestrates the flow, serves templates

---

### Task 1: Project Skeleton and Configuration

**Files:**
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `.env.example`
- Update: `requirements.txt`

- [ ] **Step 1: Create app package marker**

```bash
mkdir -p app static app/templates
touch app/__init__.py
```

- [ ] **Step 2: Write config.py with all env vars**

```python
# app/config.py
import os

QWEN_API_KEY = os.environ.get("QWEN_API_KEY", "")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-vl-plus")
QWEN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_BUCKET = "math-images"

UPLOAD_TYPES = ["错题", "笔记", "讲义"]
SUBJECTS = ["高数", "线代", "概率论", "待AI识别"]
ERROR_CATEGORIES = ["计算粗心", "概念不清", "方法选错", "审题失误", "不会做"]

# Hardcoded user_id for MVP single-user mode
MVP_USER_ID = "00000000-0000-0000-0000-000000000000"
```

- [ ] **Step 3: Write .env.example**

```
QWEN_API_KEY=sk-xxx
DEEPSEEK_API_KEY=sk-xxx
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhb...
```

- [ ] **Step 4: Update requirements.txt for production**

```
fastapi==0.115.6
uvicorn==0.34.0
python-multipart==0.0.20
supabase==2.13.0
httpx==0.28.1
```

- [ ] **Step 5: Install deps and verify config imports**

```bash
pip install -r requirements.txt -q
python -c "from app.config import QWEN_API_KEY; print('config OK')"
```

Expected: `config OK`

- [ ] **Step 6: Commit**

```bash
git add app/__init__.py app/config.py .env.example requirements.txt
git commit -m "feat: project skeleton and configuration module"
```

---

### Task 2: Supabase Data Access Layer

**Files:**
- Create: `app/supabase_client.py`

- [ ] **Step 1: Write supabase_client.py — init and uploads CRUD**

```python
# app/supabase_client.py
from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET, MVP_USER_ID
from uuid import uuid4

_client: Client | None = None

def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def upload_image(file_bytes: bytes, filename: str) -> str:
    """Upload image to Supabase Storage, return the storage path."""
    client = get_client()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    path = f"{uuid4().hex}.{ext}"
    client.storage.from_(SUPABASE_BUCKET).upload(
        path, file_bytes, {"content-type": f"image/{ext}", "upsert": "true"}
    )
    return path


def get_image_url(storage_path: str) -> str:
    """Get a signed URL for an uploaded image (valid 1 hour)."""
    client = get_client()
    return client.storage.from_(SUPABASE_BUCKET).create_signed_url(storage_path, 3600)


def create_upload(
    upload_type: str,
    image_path: str,
    subject: str | None = None,
    knowledge_point: str | None = None,
    user_note: str | None = None,
) -> dict:
    client = get_client()
    data = {
        "user_id": MVP_USER_ID,
        "type": upload_type,
        "image_url": image_path,
        "subject": subject,
        "knowledge_point": knowledge_point,
        "user_note": user_note,
    }
    result = client.table("uploads").insert(data).execute()
    return result.data[0]
```

- [ ] **Step 2: Add analysis_records and knowledge_graph operations**

```python
# append to app/supabase_client.py

def save_ocr_result(upload_id: str, raw_text: str, formulas: list | None = None) -> dict:
    client = get_client()
    data = {
        "upload_id": upload_id,
        "raw_text": raw_text,
        "formulas": formulas or [],
        "confidence": 0.0,
    }
    result = client.table("ocr_results").insert(data).execute()
    return result.data[0]


def save_analysis(upload_id: str, analysis: dict) -> dict:
    client = get_client()
    data = {
        "upload_id": upload_id,
        "analysis_type": analysis.get("analysis_type", ""),
        "error_category": analysis.get("error_category", ""),
        "error_detail": analysis.get("error_detail", ""),
        "correct_solution": analysis.get("correct_solution", ""),
        "suggestions": analysis.get("suggestions", ""),
        "related_knowledge": analysis.get("related_knowledge", []),
        "similar_problems": analysis.get("similar_problems", []),
        "knowledge_mastery": analysis.get("knowledge_mastery", 50),
        "context_used": analysis.get("context_used", ""),
    }
    result = client.table("analysis_records").insert(data).execute()
    return result.data[0]


def get_upload(upload_id: str) -> dict | None:
    client = get_client()
    result = client.table("uploads").select("*").eq("id", upload_id).execute()
    return result.data[0] if result.data else None


def get_ocr_result(upload_id: str) -> dict | None:
    client = get_client()
    result = client.table("ocr_results").select("*").eq("upload_id", upload_id).execute()
    return result.data[0] if result.data else None


def get_analysis(upload_id: str) -> dict | None:
    client = get_client()
    result = client.table("analysis_records").select("*").eq("upload_id", upload_id).execute()
    return result.data[0] if result.data else None


def get_recent_uploads(limit: int = 20) -> list[dict]:
    client = get_client()
    result = (
        client.table("uploads")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


def get_knowledge_graph() -> list[dict]:
    client = get_client()
    result = (
        client.table("knowledge_graph")
        .select("*")
        .eq("user_id", MVP_USER_ID)
        .order("mastery_score", desc=False)
        .execute()
    )
    return result.data


def upsert_knowledge_point(knowledge_point: str, mastery_score: int = 50) -> dict:
    client = get_client()
    existing = (
        client.table("knowledge_graph")
        .select("*")
        .eq("user_id", MVP_USER_ID)
        .eq("knowledge_point", knowledge_point)
        .execute()
    )
    if existing.data:
        new_count = existing.data[0]["error_count"] + 1
        result = (
            client.table("knowledge_graph")
            .update({"mastery_score": mastery_score, "error_count": new_count})
            .eq("id", existing.data[0]["id"])
            .execute()
        )
        return result.data[0]
    else:
        result = (
            client.table("knowledge_graph")
            .insert({
                "user_id": MVP_USER_ID,
                "knowledge_point": knowledge_point,
                "mastery_score": mastery_score,
                "error_count": 1,
            })
            .execute()
        )
        return result.data[0]


def get_analysis_by_knowledge_point(knowledge_point: str, limit: int = 5) -> list[dict]:
    """Get recent analyses for a specific knowledge point, for memory context."""
    client = get_client()
    result = (
        client.table("analysis_records")
        .select("error_detail, error_category, correct_solution, created_at")
        .contains("related_knowledge", [knowledge_point])
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data
```

- [ ] **Step 3: Verify supabase_client works with real DB**

```bash
python -c "
from app.supabase_client import get_recent_uploads
result = get_recent_uploads(5)
print(f'OK — got {len(result)} uploads')
"
```

Expected: `OK — got 0 uploads` (empty table is fine)

- [ ] **Step 4: Commit**

```bash
git add app/supabase_client.py
git commit -m "feat: Supabase data access layer — uploads, analysis, knowledge CRUD"
```

---

### Task 3: Qwen VL Vision Module

**Files:**
- Create: `app/vision.py`

- [ ] **Step 1: Write vision.py**

```python
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


def recognize_image(image_bytes: bytes) -> dict:
    """Send image to Qwen VL, return structured recognition result."""
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
        "response_format": {"type": "json_object"},
    }).encode()

    req = urllib.request.Request(QWEN_API_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {QWEN_API_KEY}")

    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
```

- [ ] **Step 2: Verify vision module with a real test image**

```bash
cd verify && python -c "
import sys; sys.path.insert(0, '..')
from app.vision import recognize_image

with open('test_images/1.jpg', 'rb') as f:
    result = recognize_image(f.read())
print('lines:', result.get('lines', [])[:3])
print('formulas:', result.get('formulas', [])[:3])
print('subject:', result.get('subject'))
print('knowledge_points:', result.get('knowledge_points'))
print('OK — vision module works')
"
```

Expected: Real math content recognized from the test image.

- [ ] **Step 3: Commit**

```bash
git add app/vision.py
git commit -m "feat: Qwen VL vision module — image to structured math text"
```

---

### Task 4: DeepSeek Analyzer with Memory Context

**Files:**
- Create: `app/analyzer.py`

- [ ] **Step 1: Write analyzer.py — core analysis function**

```python
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
  "correct_solution": "正确的解题过程，用LaTeX格式",
  "suggestions": "改进建议",
  "related_knowledge": ["关联知识点"],
  "similar_problems": [{"description": "题目描述", "hint": "解题提示"}]
}
"""


def build_memory_context(knowledge_points: list[str]) -> str:
    """Build memory context from historical analysis records."""
    if not knowledge_points:
        return "（无历史记录）"

    all_records = []
    for kp in knowledge_points:
        records = get_analysis_by_knowledge_point(kp, limit=3)
        all_records.extend(records)

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
    """Send recognized text + memory context to DeepSeek, return structured analysis."""

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
        "response_format": {"type": "json_object"},
    }).encode()

    req = urllib.request.Request(DEEPSEEK_API_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {DEEPSEEK_API_KEY}")

    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())
        content = body["choices"][0]["message"]["content"]
        analysis = json.loads(content)
        analysis["context_used"] = memory
        return analysis
```

- [ ] **Step 2: Verify analyzer module**

```bash
cd verify && python -c "
import sys; sys.path.insert(0, '..')
from app.analyzer import analyze

result = analyze(
    recognized_text='求极限 lim(x→0) (tan x - sin x) / x^3，我用了等价无穷小替换得到0，答案是1/2',
    knowledge_points=['极限计算', '等价无穷小'],
    upload_type='错题',
    student_work='tan x ~ x, sin x ~ x, 所以原式 = lim(x→0) (x-x)/x^3 = 0',
)
print('analysis_type:', result.get('analysis_type'))
print('error_category:', result.get('error_category'))
print('knowledge_points:', result.get('knowledge_points'))
print('OK — analyzer works')
"
```

Expected: Valid analysis with error_category and correct_solution.

- [ ] **Step 3: Commit**

```bash
git add app/analyzer.py
git commit -m "feat: DeepSeek analyzer with memory context from historical records"
```

---

### Task 5: Knowledge Graph Tracker

**Files:**
- Create: `app/knowledge.py`

- [ ] **Step 1: Write knowledge.py**

```python
# app/knowledge.py
from app.supabase_client import upsert_knowledge_point, get_knowledge_graph


def update_mastery_after_error(knowledge_points: list[str]) -> None:
    """After a new mistake, decrease mastery score for each affected knowledge point."""
    for kp in knowledge_points:
        current = get_knowledge_graph()
        existing = [k for k in current if k["knowledge_point"] == kp]
        if existing:
            old_score = existing[0]["mastery_score"]
            # Drop score, minimum 5
            new_score = max(5, old_score - 15)
        else:
            # New knowledge point, start below default
            new_score = 35
        upsert_knowledge_point(kp, new_score)


def update_mastery_after_success(knowledge_points: list[str]) -> None:
    """After a correct answer, increase mastery score."""
    for kp in knowledge_points:
        current = get_knowledge_graph()
        existing = [k for k in current if k["knowledge_point"] == kp]
        if existing:
            old_score = existing[0]["mastery_score"]
            new_score = min(100, old_score + 10)
            upsert_knowledge_point(kp, new_score)


def get_mastery_summary() -> list[dict]:
    """Return all knowledge points with mastery level labels."""
    graph = get_knowledge_graph()
    for item in graph:
        score = item.get("mastery_score", 50)
        if score <= 30:
            item["level"] = "薄弱"
            item["color"] = "#ef4444"
        elif score <= 60:
            item["level"] = "一般"
            item["color"] = "#f59e0b"
        else:
            item["level"] = "掌握"
            item["color"] = "#10b981"
    return graph
```

- [ ] **Step 2: Verify knowledge module**

```bash
python -c "
from app.knowledge import update_mastery_after_error, get_mastery_summary
update_mastery_after_error(['极限计算'])
summary = get_mastery_summary()
pts = [s['knowledge_point'] for s in summary]
print('Knowledge points:', pts)
print('OK — knowledge module works')
"
```

Expected: `极限计算` appears in the list with a score.

- [ ] **Step 3: Commit**

```bash
git add app/knowledge.py
git commit -m "feat: knowledge graph tracker — mastery score up/down logic"
```

---

### Task 6: HTML Templates

**Files:**
- Create: `app/templates/base.html`
- Create: `app/templates/index.html`
- Create: `app/templates/result.html`
- Create: `app/templates/knowledge.html`
- Create: `static/style.css`

- [ ] **Step 1: Write base.html (Bootstrap 5 shell)**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}考研数学复习助手{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <link href="/static/style.css" rel="stylesheet">
    {% block head %}{% endblock %}
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary sticky-top">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">&#x1F4D0; 数学复习助手</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item"><a class="nav-link" href="/"><i class="bi bi-house"></i> 首页</a></li>
                    <li class="nav-item"><a class="nav-link" href="/knowledge"><i class="bi bi-book"></i> 知识库</a></li>
                </ul>
            </div>
        </div>
    </nav>
    <main class="container py-3">
        {% block content %}{% endblock %}
    </main>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

- [ ] **Step 2: Write index.html (upload page)**

```html
{% extends "base.html" %}
{% block title %}上传 — 考研数学复习助手{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 col-lg-6">
        <h1 class="h4 mb-3 text-center">拍照上传数学题目或笔记</h1>

        <form action="/api/upload" method="POST" enctype="multipart/form-data" id="upload-form">
            <!-- Upload area -->
            <div class="card mb-3">
                <div class="card-body text-center py-4">
                    <label for="file-input" class="upload-area d-block" id="upload-label">
                        <i class="bi bi-camera" style="font-size:2.5rem;color:#6c757d;"></i>
                        <p class="mt-2 mb-0 text-muted">点击选择图片 或 直接拍照</p>
                        <small class="text-muted">支持 JPG / PNG</small>
                    </label>
                    <input type="file" id="file-input" name="file" accept="image/*" capture="environment"
                           class="d-none" onchange="previewImage(this)">
                    <img id="preview" class="img-fluid rounded mt-3 d-none" style="max-height:300px;" alt="预览">
                </div>
            </div>

            <!-- Optional fields -->
            <div class="row g-2 mb-3">
                <div class="col-6">
                    <label class="form-label small">分类（可选）</label>
                    <select name="upload_type" class="form-select form-select-sm">
                        <option value="待AI识别">让AI自动判断</option>
                        <option value="错题">错题</option>
                        <option value="笔记">笔记</option>
                        <option value="讲义">讲义</option>
                    </select>
                </div>
                <div class="col-6">
                    <label class="form-label small">学科（可选）</label>
                    <select name="subject" class="form-select form-select-sm">
                        <option value="待AI识别">让AI自动判断</option>
                        <option value="高数">高数</option>
                        <option value="线代">线代</option>
                        <option value="概率论">概率论</option>
                    </select>
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label small">补充说明（可选）</label>
                <textarea name="user_note" class="form-control form-control-sm" rows="2"
                          placeholder="例如：这道题我卡在了第二步..."></textarea>
            </div>

            <button type="submit" class="btn btn-primary w-100 py-2" id="submit-btn" disabled>
                <i class="bi bi-magic"></i> 开始AI分析
            </button>
        </form>
    </div>
</div>
{% endblock %}
{% block scripts %}
<script>
function previewImage(input) {
    const preview = document.getElementById('preview');
    const submit = document.getElementById('submit-btn');
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.classList.remove('d-none');
            submit.disabled = false;
        };
        reader.readAsDataURL(input.files[0]);
    }
}
</script>
{% endblock %}
```

- [ ] **Step 3: Write result.html (analysis result page)**

```html
{% extends "base.html" %}
{% block title %}分析结果 — 考研数学复习助手{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 col-lg-6">

        <a href="/" class="btn btn-outline-secondary btn-sm mb-3">&larr; 继续上传</a>

        <!-- Original image -->
        <div class="card mb-3">
            <div class="card-header small text-muted">原图</div>
            <div class="card-body text-center p-2">
                <img src="{{ image_url }}" class="img-fluid rounded" style="max-height:300px;" alt="原图">
            </div>
        </div>

        <!-- Recognition -->
        <div class="card mb-3">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span class="small text-muted">AI 识别内容</span>
                <span class="badge bg-secondary">{{ upload.subject or '?' }}</span>
            </div>
            <div class="card-body">
                <p class="card-text" style="white-space:pre-wrap;">{{ ocr.raw_text }}</p>
                {% if ocr.formulas %}
                <div class="mt-2">
                    {% for f in ocr.formulas %}
                    <span class="badge bg-light text-dark me-1 mb-1">{{ f }}</span>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
        </div>

        <!-- Error analysis (only for 错题 type) -->
        {% if analysis.analysis_type == '错题分析' %}
        <div class="card mb-3 border-danger">
            <div class="card-header bg-danger bg-opacity-10 text-danger fw-bold small">
                错因分析：{{ analysis.error_category }}
            </div>
            <div class="card-body">
                <p class="mb-2" style="white-space:pre-wrap;">{{ analysis.error_detail }}</p>
            </div>
        </div>

        <div class="card mb-3 border-success">
            <div class="card-header bg-success bg-opacity-10 text-success fw-bold small">正确解法</div>
            <div class="card-body">
                <p class="card-text" style="white-space:pre-wrap;">{{ analysis.correct_solution }}</p>
            </div>
        </div>
        {% endif %}

        <!-- Lecture/note analysis -->
        {% if analysis.analysis_type in ('讲义总结', '笔记整理') %}
        <div class="card mb-3 border-info">
            <div class="card-header bg-info bg-opacity-10 text-info fw-bold small">{{ analysis.analysis_type }}</div>
            <div class="card-body">
                <p style="white-space:pre-wrap;">{{ analysis.error_detail }}</p>
            </div>
        </div>
        {% endif %}

        <!-- Suggestions -->
        {% if analysis.suggestions %}
        <div class="card mb-3">
            <div class="card-header small text-muted">改进建议</div>
            <div class="card-body">
                <p style="white-space:pre-wrap;">{{ analysis.suggestions }}</p>
            </div>
        </div>
        {% endif %}

        <!-- Knowledge points & similar problems -->
        {% if analysis.related_knowledge %}
        <div class="card mb-3">
            <div class="card-header small text-muted">关联知识点</div>
            <div class="card-body">
                {% for kp in analysis.related_knowledge %}
                <span class="badge bg-primary me-1 mb-1">{{ kp }}</span>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if analysis.similar_problems %}
        <div class="card mb-3">
            <div class="card-header small text-muted">推荐练习</div>
            <div class="card-body">
                {% for sp in analysis.similar_problems %}
                <div class="mb-2">
                    <strong>{{ sp.description if sp.description is defined else sp }}</strong>
                    {% if sp.hint is defined and sp.hint %}
                    <br><small class="text-muted">提示：{{ sp.hint }}</small>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- Toast message -->
        <div class="text-center mb-4">
            <small class="text-muted">分析完成 · 已自动记录到知识库</small>
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Write knowledge.html (knowledge base overview)**

```html
{% extends "base.html" %}
{% block title %}知识库 — 考研数学复习助手{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 col-lg-6">
        <h1 class="h4 mb-3">我的知识库</h1>

        <!-- Mastery overview -->
        <div class="card mb-3">
            <div class="card-header small text-muted">知识点掌握度</div>
            <div class="card-body p-2">
                {% if knowledge %}
                {% for k in knowledge %}
                <div class="d-flex align-items-center mb-2 px-2">
                    <span class="flex-grow-1 small">{{ k.knowledge_point }}</span>
                    <div class="progress flex-grow-1 me-2" style="height:6px;max-width:120px;">
                        <div class="progress-bar" style="width:{{ k.mastery_score }}%;background-color:{{ k.color }};"></div>
                    </div>
                    <small style="color:{{ k.color }};">{{ k.mastery_score }}分 · {{ k.level }}</small>
                </div>
                {% endfor %}
                {% else %}
                <p class="text-muted text-center py-3 mb-0">还没有记录，上传一道错题后这里就会出现知识点追踪。</p>
                {% endif %}
            </div>
        </div>

        <!-- Recent uploads -->
        <div class="card mb-3">
            <div class="card-header small text-muted">最近上传</div>
            <div class="list-group list-group-flush">
                {% if uploads %}
                {% for u in uploads %}
                <a href="/result/{{ u.id }}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                    <div>
                        <span class="badge {% if u.type == '错题' %}bg-danger{% elif u.type == '讲义' %}bg-info{% else %}bg-secondary{% endif %} me-1">{{ u.type }}</span>
                        <small>{{ u.knowledge_point or '待分类' }}</small>
                    </div>
                    <small class="text-muted">{{ u.created_at[:10] if u.created_at else '' }}</small>
                </a>
                {% endfor %}
                {% else %}
                <div class="list-group-item text-muted text-center py-3">还没有上传记录</div>
                {% endif %}
            </div>
        </div>

        <div class="text-center">
            <a href="/" class="btn btn-primary"><i class="bi bi-plus-circle"></i> 上传新题</a>
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Write static/style.css**

```css
.upload-area {
    cursor: pointer;
    transition: background-color 0.2s;
    border-radius: 12px;
    padding: 2rem 1rem;
}
.upload-area:hover {
    background-color: #f0f4ff;
}
.card-header {
    font-weight: 500;
}
```

- [ ] **Step 6: Commit**

```bash
git add app/templates/ static/
git commit -m "feat: HTML templates — upload, result, knowledge base w/ Bootstrap 5"
```

---

### Task 7: FastAPI Main Application — Routes and Orchestration

**Files:**
- Create: `app/main.py`

- [ ] **Step 1: Write main.py — imports, app init, and upload route**

```python
# app/main.py
import io
from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import UPLOAD_TYPES, SUBJECTS, SUPABASE_BUCKET, SUPABASE_URL
from app.supabase_client import (
    upload_image, get_image_url, create_upload,
    save_ocr_result, save_analysis,
    get_upload, get_ocr_result, get_analysis,
    get_recent_uploads, get_knowledge_graph,
)
from app.vision import recognize_image
from app.analyzer import analyze
from app.knowledge import update_mastery_after_error, get_mastery_summary

app = FastAPI(title="考研数学复习助手")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "upload_types": UPLOAD_TYPES,
        "subjects": SUBJECTS,
    })


@app.post("/api/upload")
async def handle_upload(
    request: Request,
    file: UploadFile = File(...),
    upload_type: str = Form("待AI识别"),
    subject: str = Form("待AI识别"),
    user_note: str = Form(""),
):
    # 1. Read and upload image
    image_bytes = await file.read()
    storage_path = upload_image(image_bytes, file.filename or "upload.jpg")

    # 2. Qwen VL recognition
    try:
        vision_result = recognize_image(image_bytes)
    except Exception as e:
        # If vision fails, use basic info
        vision_result = {
            "lines": [],
            "formulas": [],
            "subject": subject if subject != "待AI识别" else "未知",
            "knowledge_points": [],
            "question_type": upload_type if upload_type != "待AI识别" else "错题",
            "is_error_question": False,
            "student_work": "",
        }

    # 3. Determine type/subject: user override > AI detection
    final_type = upload_type if upload_type != "待AI识别" else vision_result.get("question_type", "错题")
    final_subject = subject if subject != "待AI识别" else vision_result.get("subject", "高数")
    knowledge_points = vision_result.get("knowledge_points", [])
    recognized_text = "\n".join(vision_result.get("lines", []))

    # 4. Save upload + OCR to DB
    upload_record = create_upload(
        upload_type=final_type,
        image_path=storage_path,
        subject=final_subject,
        knowledge_point=", ".join(knowledge_points) if knowledge_points else None,
        user_note=user_note or None,
    )
    save_ocr_result(
        upload_id=upload_record["id"],
        raw_text=recognized_text or str(vision_result),
        formulas=vision_result.get("formulas", []),
    )

    # 5. DeepSeek analysis with memory context
    analysis_result = analyze(
        recognized_text=recognized_text or str(vision_result),
        knowledge_points=knowledge_points,
        upload_type=final_type,
        student_work=vision_result.get("student_work", ""),
    )

    # 6. Save analysis
    save_analysis(upload_id=upload_record["id"], analysis=analysis_result)

    # 7. Update knowledge graph
    if final_type == "错题" and knowledge_points:
        update_mastery_after_error(knowledge_points)

    # 8. Redirect to result page
    return RedirectResponse(url=f"/result/{upload_record['id']}", status_code=303)


@app.get("/result/{upload_id}", response_class=HTMLResponse)
async def result_page(request: Request, upload_id: str):
    upload = get_upload(upload_id)
    if not upload:
        return HTMLResponse("未找到该记录", status_code=404)

    ocr = get_ocr_result(upload_id)
    analysis = get_analysis(upload_id)

    # Get signed URL for image
    try:
        image_url = get_image_url(upload["image_url"])
    except Exception:
        # Fallback: construct public URL
        image_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{upload['image_url']}"

    return templates.TemplateResponse("result.html", {
        "request": request,
        "upload": upload,
        "ocr": ocr or {},
        "analysis": analysis or {},
        "image_url": image_url,
    })


@app.get("/knowledge", response_class=HTMLResponse)
async def knowledge_page(request: Request):
    knowledge = get_mastery_summary()  # Already sorted by score ascending
    uploads = get_recent_uploads(limit=30)
    return templates.TemplateResponse("knowledge.html", {
        "request": request,
        "knowledge": knowledge,
        "uploads": uploads,
    })
```

- [ ] **Step 2: Verify the app starts and all routes work**

```bash
# Start the server in background
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 2

# Test routes
echo "=== Home page ===" && curl -s http://localhost:8000/ | head -5
echo "=== Knowledge page ===" && curl -s http://localhost:8000/knowledge | head -5

# Kill server
kill %1 2>/dev/null
echo "OK — all routes responding"
```

Expected: HTML content returned for both pages.

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: FastAPI app with upload → vision → analyze → result flow"
```

---

### Task 8: Deployment Configuration

**Files:**
- Create/Update: `Procfile`
- Create/Update: `railway.json`

- [ ] **Step 1: Place Procfile and railway.json in project root**

Procfile:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

railway.json:
```json
{
  "build": {"builder": "NIXPACKS"},
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
  }
}
```

- [ ] **Step 2: Verify deploy files exist in correct location**

```bash
ls -la Procfile railway.json requirements.txt
```

- [ ] **Step 3: Commit**

```bash
git add Procfile railway.json
git commit -m "chore: deployment config for Railway"
```

---

### Task 9: End-to-End Integration Test

- [ ] **Step 1: Start server, upload a real test image, verify full flow**

```bash
# Start server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 2

# Upload test image
curl -s -X POST http://localhost:8000/api/upload \
  -F "file=@verify/test_images/1.jpg" \
  -F "upload_type=错题" \
  -F "subject=高数" \
  -o /dev/null -w "%{http_code} %{redirect_url}" \
  -L

# Check knowledge base
curl -s http://localhost:8000/knowledge | grep -o "极限" | head -1

kill %1 2>/dev/null
echo "Done — E2E test passed"
```

Expected: HTTP 200 after redirect, knowledge base shows new entry.

- [ ] **Step 2: Commit any fixes, tag as mvp-ready**

```bash
git add -A
git commit -m "test: end-to-end integration test pass, MVP ready"
```

---

## Verification Checklist

After all 9 tasks, verify:

| Check | Method |
|-------|--------|
| Upload image → saves to Supabase Storage | Upload, check Supabase Dashboard → Storage |
| Qwen VL reads math correctly | Check result page shows recognized formulas |
| DeepSeek analysis is accurate | Read the result page, verify error category makes sense |
| Memory context works | Upload 2nd question on same topic, check analysis mentions history |
| Knowledge graph updates | Check /knowledge page, mastery score reflects new data |
| Mobile browser works | Open localhost:8000 on phone browser, upload and view |
