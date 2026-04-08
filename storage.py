"""
블로그 데이터 저장소 — Supabase 기반
- blog_topics: 주제 CRUD
- blog_posts: 글 저장/조회
- blog_images: 이미지 메타 + Storage 업로드
- JSON 폴백: Supabase 연결 실패 시 기존 JSON 파일 사용
"""
import json
import os
from pathlib import Path

# ── JSON 폴백 경로 ──
DATA_DIR = Path(__file__).parent / "data"
BLOGS_DIR = DATA_DIR / "blogs"
IMAGES_DIR = DATA_DIR / "images"

# ── Supabase 클라이언트 ──
_supabase = None


def _get_supabase():
    """Supabase 클라이언트 싱글톤"""
    global _supabase
    if _supabase is not None:
        return _supabase
    try:
        from config import SUPABASE_URL, SUPABASE_KEY
        if SUPABASE_URL and SUPABASE_KEY:
            from supabase import create_client
            _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            return _supabase
    except Exception:
        pass
    return None


def _use_supabase() -> bool:
    """Supabase 사용 가능 여부"""
    return _get_supabase() is not None


# ================================================================
#  주제 (blog_topics)
# ================================================================

def load_topics(company_id: str = "houseman") -> list:
    """주제 목록 조회 (삭제되지 않은 것만)"""
    sb = _get_supabase()
    if sb:
        try:
            res = sb.table("blog_topics") \
                .select("*") \
                .eq("company_id", company_id) \
                .eq("is_deleted", False) \
                .order("id") \
                .execute()
            return res.data or []
        except Exception:
            pass
    # JSON 폴백
    return _json_load_topics(company_id)


def save_topic(company_id: str, topic: dict) -> dict:
    """주제 1개 저장 (INSERT). 반환: 저장된 row"""
    sb = _get_supabase()
    if sb:
        try:
            row = {
                "company_id": company_id,
                "title": topic["title"],
                "category": topic.get("category", "실무팁"),
                "platform": topic.get("platform", "naver"),
                "source": topic.get("source", "manual"),
            }
            res = sb.table("blog_topics").insert(row).execute()
            return res.data[0] if res.data else topic
        except Exception:
            pass
    # JSON 폴백
    return _json_save_topic(company_id, topic)


def delete_topic(company_id: str, topic_id: int):
    """주제 소프트 삭제"""
    sb = _get_supabase()
    if sb:
        try:
            sb.table("blog_topics") \
                .update({"is_deleted": True}) \
                .eq("id", topic_id) \
                .eq("company_id", company_id) \
                .execute()
            return
        except Exception:
            pass
    # JSON 폴백
    _json_delete_topic(company_id, topic_id)


# ================================================================
#  글 (blog_posts)
# ================================================================

def load_blogs(company_id: str = "houseman") -> dict:
    """전체 블로그 데이터 {topic_id_str: {content, image_prompts, ...}}"""
    sb = _get_supabase()
    if sb:
        try:
            res = sb.table("blog_posts") \
                .select("*") \
                .eq("company_id", company_id) \
                .execute()
            blogs = {}
            for row in (res.data or []):
                tid = str(row["topic_id"])
                blogs[tid] = {
                    "post_id": row["id"],
                    "final": row["content"] if row["platform"] == "naver" else None,
                    "wordpress": row["content"] if row["platform"] == "wordpress" else None,
                    "naver_images": row["image_prompts"] if row["platform"] == "naver" else None,
                    "wp_images": row["image_prompts"] if row["platform"] == "wordpress" else None,
                    "qa_score": row.get("qa_score", 0),
                    "agents": row.get("agents", []),
                }
                # None 제거
                blogs[tid] = {k: v for k, v in blogs[tid].items() if v is not None}
            return blogs
        except Exception:
            pass
    # JSON 폴백
    return _json_load_blogs(company_id)


def save_blog(topic_id: int, data: dict, company_id: str = "houseman"):
    """블로그 글 저장 (UPSERT)"""
    sb = _get_supabase()
    if sb:
        try:
            platform = "wordpress" if data.get("wordpress") else "naver"
            content = data.get("wordpress") or data.get("final") or data.get("naver") or ""
            img_key = "wp_images" if platform == "wordpress" else "naver_images"

            # 기존 post 확인
            existing = sb.table("blog_posts") \
                .select("id") \
                .eq("topic_id", topic_id) \
                .eq("company_id", company_id) \
                .execute()

            row = {
                "topic_id": topic_id,
                "company_id": company_id,
                "platform": platform,
                "content": content,
                "image_prompts": data.get(img_key, ""),
                "metadata": data.get("metadata", ""),
                "qa_score": data.get("qa_score", 0),
                "qa_report": data.get("qa_report", ""),
                "agents": data.get("agents", []),
            }

            if existing.data:
                sb.table("blog_posts") \
                    .update(row) \
                    .eq("id", existing.data[0]["id"]) \
                    .execute()
            else:
                sb.table("blog_posts").insert(row).execute()
            return
        except Exception:
            pass
    # JSON 폴백
    _json_save_blog(topic_id, data, company_id)


# ================================================================
#  이미지 Storage
# ================================================================

def upload_image(topic_id: int, platform: str, image_index: int, file_path: str) -> str:
    """이미지를 Supabase Storage에 업로드. 반환: public URL"""
    sb = _get_supabase()
    if sb:
        try:
            storage_path = f"{platform}/topic_{topic_id:03d}_img_{image_index:02d}.png"
            with open(file_path, "rb") as f:
                # 기존 파일 삭제 후 업로드
                sb.storage.from_("blog-images").remove([storage_path])
                sb.storage.from_("blog-images").upload(storage_path, f.read(), {"content-type": "image/png"})
            url = sb.storage.from_("blog-images").get_public_url(storage_path)
            return url
        except Exception:
            pass
    return file_path  # 폴백: 로컬 경로 반환


def get_image_url(topic_id: int, platform: str, image_index: int) -> str:
    """이미지 public URL 반환"""
    sb = _get_supabase()
    if sb:
        try:
            storage_path = f"{platform}/topic_{topic_id:03d}_img_{image_index:02d}.png"
            return sb.storage.from_("blog-images").get_public_url(storage_path)
        except Exception:
            pass
    # 폴백: 로컬 경로
    local = IMAGES_DIR / f"topic_{topic_id:03d}_{platform}_img_{image_index:02d}.png"
    return str(local) if local.exists() else ""


# ================================================================
#  JSON 폴백 함수들 (기존 로직 유지)
# ================================================================

def _json_company_path(company_id):
    return DATA_DIR / "companies" / f"{company_id}.json"


def _json_load_topics(company_id):
    path = _json_company_path(company_id)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("topics", [])
    return []


def _json_save_topic(company_id, topic):
    path = _json_company_path(company_id)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"topics": []}
    data.setdefault("topics", []).append(topic)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return topic


def _json_delete_topic(company_id, topic_id):
    path = _json_company_path(company_id)
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["topics"] = [t for t in data.get("topics", []) if t.get("id") != topic_id]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _json_load_blogs(company_id):
    BLOGS_DIR.mkdir(parents=True, exist_ok=True)
    path = BLOGS_DIR / f"{company_id}_blogs.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _json_save_blog(topic_id, data, company_id):
    BLOGS_DIR.mkdir(parents=True, exist_ok=True)
    blogs = _json_load_blogs(company_id)
    current = blogs.get(str(topic_id), {})
    current.update(data)
    blogs[str(topic_id)] = current
    path = BLOGS_DIR / f"{company_id}_blogs.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(blogs, f, ensure_ascii=False, indent=2)
