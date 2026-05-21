# app/knowledge.py
from app.supabase_client import upsert_knowledge_point, get_knowledge_graph


def update_mastery_after_error(knowledge_points: list[str]) -> None:
    """After a new mistake, decrease mastery score for each affected knowledge point."""
    for kp in knowledge_points:
        current = get_knowledge_graph()
        existing = [k for k in current if k["knowledge_point"] == kp]
        if existing:
            old_score = existing[0]["mastery_score"]
            new_score = max(5, old_score - 15)
        else:
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
    """Return all knowledge points with mastery level labels and colors."""
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
