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
    client = get_client()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    path = f"{uuid4().hex}.{ext}"
    client.storage.from_(SUPABASE_BUCKET).upload(
        path, file_bytes, {"content-type": f"image/{ext}", "upsert": "true"}
    )
    return path


def get_image_url(storage_path: str) -> str:
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


def update_ocr_result(ocr_id: str, raw_text: str, formulas: list | None = None) -> dict:
    client = get_client()
    result = client.table("ocr_results").update({
        "raw_text": raw_text,
        "formulas": formulas or [],
    }).eq("id", ocr_id).execute()
    return result.data[0] if result.data else {}


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


def delete_knowledge_point(kp_id: int) -> bool:
    client = get_client()
    result = client.table("knowledge_graph").delete().eq("id", kp_id).eq("user_id", MVP_USER_ID).execute()
    return len(result.data) > 0


def add_knowledge_point(name: str) -> dict:
    client = get_client()
    result = client.table("knowledge_graph").insert({
        "user_id": MVP_USER_ID,
        "knowledge_point": name,
        "mastery_score": 0,
        "error_count": 0,
    }).execute()
    return result.data[0]


def rename_knowledge_point(kp_id: int, new_name: str) -> dict:
    client = get_client()
    result = client.table("knowledge_graph").update({
        "knowledge_point": new_name,
    }).eq("id", kp_id).eq("user_id", MVP_USER_ID).execute()
    return result.data[0] if result.data else {}


def get_analysis_by_knowledge_point(knowledge_point: str, limit: int = 5) -> list[dict]:
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
