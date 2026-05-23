# app/main.py
from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import UPLOAD_TYPES, SUBJECTS, SUPABASE_BUCKET, SUPABASE_URL
from app.supabase_client import (
    upload_image, get_image_url, create_upload,
    save_ocr_result, update_ocr_result, save_analysis,
    get_upload, get_ocr_result, get_analysis,
    get_recent_uploads,
    delete_knowledge_point, add_knowledge_point, rename_knowledge_point,
)
from app.vision import recognize_image
from app.analyzer import analyze
from app.knowledge import update_mastery_after_error, get_mastery_summary


def segment_ocr_text(text: str, formulas: list[str]) -> list[dict]:
    """Split OCR text into alternating text/formula blocks."""
    blocks = []
    if not text and not formulas:
        return [{"type": "text", "content": ""}]
    if formulas:
        remaining = text
        for f in formulas:
            idx = remaining.find(f.strip())
            if idx > 0:
                pre = remaining[:idx].strip()
                if pre:
                    blocks.append({"type": "text", "content": pre})
                blocks.append({"type": "formula", "content": f.strip()})
                remaining = remaining[idx + len(f):]
            elif idx == 0:
                blocks.append({"type": "formula", "content": f.strip()})
                remaining = remaining[len(f):]
        if remaining.strip():
            blocks.append({"type": "text", "content": remaining.strip()})
    else:
        blocks.append({"type": "text", "content": text.strip()})
    return blocks if blocks else [{"type": "text", "content": text or ""}]


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
    image_bytes = await file.read()
    storage_path = upload_image(image_bytes, file.filename or "upload.jpg")

    try:
        vision_result = recognize_image(image_bytes)
    except Exception:
        vision_result = {
            "lines": [],
            "formulas": [],
            "subject": subject if subject != "待AI识别" else "未知",
            "knowledge_points": [],
            "question_type": upload_type if upload_type != "待AI识别" else "错题",
            "is_error_question": False,
            "student_work": "",
        }

    final_type = upload_type if upload_type != "待AI识别" else vision_result.get("question_type", "错题")
    final_subject = subject if subject != "待AI识别" else vision_result.get("subject", "高数")
    knowledge_points = vision_result.get("knowledge_points", [])
    recognized_text = "\n".join(vision_result.get("lines", []))

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

    return RedirectResponse(url=f"/edit/{upload_record['id']}", status_code=303)


@app.get("/edit/{upload_id}", response_class=HTMLResponse)
async def edit_page(request: Request, upload_id: str):
    upload = get_upload(upload_id)
    if not upload:
        return HTMLResponse("未找到该记录", status_code=404)

    ocr = get_ocr_result(upload_id)

    try:
        image_url = get_image_url(upload["image_url"])
    except Exception:
        image_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{upload['image_url']}"

    raw_text = ocr.get("raw_text", "") if ocr else ""
    formulas = ocr.get("formulas", []) if ocr else []
    blocks = segment_ocr_text(raw_text, formulas)

    return templates.TemplateResponse("edit.html", {
        "request": request,
        "upload": upload,
        "ocr": ocr or {},
        "image_url": image_url,
        "blocks": blocks,
    })


@app.post("/api/analyze/{upload_id}")
async def run_analysis(upload_id: str, request: Request):
    upload = get_upload(upload_id)
    if not upload:
        return JSONResponse({"error": "未找到该记录"}, status_code=404)

    body = await request.json()
    corrected_text = body.get("corrected_text", "")
    knowledge_points = body.get("knowledge_points", [])

    ocr = get_ocr_result(upload_id)
    if ocr:
        update_ocr_result(ocr["id"], corrected_text, body.get("formulas", []))

    analysis_result = analyze(
        recognized_text=corrected_text,
        knowledge_points=knowledge_points or [],
        upload_type=upload.get("type", "错题"),
        student_work="",
    )

    save_analysis(upload_id=upload_id, analysis=analysis_result)

    if upload.get("type") == "错题" and knowledge_points:
        update_mastery_after_error(knowledge_points)

    return JSONResponse({"success": True, "redirect": f"/result/{upload_id}"})


@app.get("/result/{upload_id}", response_class=HTMLResponse)
async def result_page(request: Request, upload_id: str):
    upload = get_upload(upload_id)
    if not upload:
        return HTMLResponse("未找到该记录", status_code=404)

    ocr = get_ocr_result(upload_id)
    analysis = get_analysis(upload_id)

    try:
        image_url = get_image_url(upload["image_url"])
    except Exception:
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
    knowledge = get_mastery_summary()
    uploads = get_recent_uploads(limit=30)
    return templates.TemplateResponse("knowledge.html", {
        "request": request,
        "knowledge": knowledge,
        "uploads": uploads,
    })


# --- Knowledge CRUD API ---

@app.delete("/api/knowledge/{kp_id}")
async def api_delete_knowledge(kp_id: int):
    ok = delete_knowledge_point(kp_id)
    return JSONResponse({"success": ok})


@app.post("/api/knowledge")
async def api_add_knowledge(request: Request):
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        return JSONResponse({"error": "名称不能为空"}, status_code=400)
    record = add_knowledge_point(name)
    return JSONResponse({"success": True, "record": record})


@app.put("/api/knowledge/{kp_id}")
async def api_rename_knowledge(kp_id: int, request: Request):
    body = await request.json()
    new_name = body.get("name", "").strip()
    if not new_name:
        return JSONResponse({"error": "名称不能为空"}, status_code=400)
    record = rename_knowledge_point(kp_id, new_name)
    return JSONResponse({"success": True, "record": record})
