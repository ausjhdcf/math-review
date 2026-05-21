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
    get_recent_uploads,
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
    # 1. Read and upload image to Supabase Storage
    image_bytes = await file.read()
    storage_path = upload_image(image_bytes, file.filename or "upload.jpg")

    # 2. Qwen VL recognition
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
