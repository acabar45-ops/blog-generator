import json
import shutil
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
BLOGS_DIR = DATA_DIR / "blogs"
LEGACY_FILE = DATA_DIR / "blogs.json"
DEFAULT_COMPANY = "houseman"


def _get_company_file(company_id: str) -> Path:
    """회사별 블로그 JSON 파일 경로를 반환합니다."""
    return BLOGS_DIR / f"{company_id}_blogs.json"


def _migrate_legacy_if_needed():
    """기존 data/blogs.json이 있으면 houseman 데이터로 마이그레이션합니다."""
    if LEGACY_FILE.exists():
        BLOGS_DIR.mkdir(parents=True, exist_ok=True)
        dest = _get_company_file(DEFAULT_COMPANY)
        if not dest.exists():
            shutil.move(str(LEGACY_FILE), str(dest))
        else:
            # 이미 마이그레이션된 경우, 레거시 파일 삭제
            LEGACY_FILE.unlink()


def load_blogs(company_id: str = DEFAULT_COMPANY) -> dict:
    """특정 회사의 저장된 전체 블로그 데이터를 불러옵니다."""
    _migrate_legacy_if_needed()
    BLOGS_DIR.mkdir(parents=True, exist_ok=True)
    company_file = _get_company_file(company_id)
    if not company_file.exists():
        return {}
    with open(company_file, encoding="utf-8") as f:
        return json.load(f)


def save_blog(topic_id: int, data: dict, company_id: str = DEFAULT_COMPANY):
    """특정 회사의 특정 주제 블로그 데이터를 저장합니다."""
    _migrate_legacy_if_needed()
    blogs = load_blogs(company_id)
    blogs[str(topic_id)] = data
    BLOGS_DIR.mkdir(parents=True, exist_ok=True)
    company_file = _get_company_file(company_id)
    with open(company_file, "w", encoding="utf-8") as f:
        json.dump(blogs, f, ensure_ascii=False, indent=2)
