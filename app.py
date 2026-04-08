import os
import streamlit as st

# ── 페이지 설정 (반드시 최상단 1회) ──
st.set_page_config(
    page_title="블로그 자동화",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 회사 선택 ──
def _select_company():
    """두 회사 중 하나를 선택하는 화면"""
    if st.session_state.get("current_company"):
        return True

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("<div style='text-align:center; padding: 60px 0 30px 0;'><h1>🏢 블로그 자동화</h1></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🏢 하우스맨", use_container_width=True, key="btn_houseman"):
                st.session_state["current_company"] = "houseman"
                st.rerun()
        with c2:
            if st.button("🧹 청소매뉴얼", use_container_width=True, key="btn_cleanmanual"):
                st.session_state["current_company"] = "cleanmanual"
                st.rerun()
    return False

if not _select_company():
    st.stop()

from storage import load_blogs, save_blog
from company_manager import load_company, get_or_create_default_company
import generator as gen
import pipeline
import gemini_client
from config import CLAUDE_API_KEY

CATEGORY_COLORS = {
    "실무팁": "#4A90D9",
    "도입사례": "#27AE60",
    "트렌드": "#0071e3",
    "자동화": "#8E44AD",
}

# ── 페이지 설정은 최상단에서 완료 ──

# ── 스타일 ──
st.markdown("""
<style>
/* 사이드바·위젯만 13px (블로그 미리보기에 영향 없도록) */
section[data-testid="stSidebar"] { font-size: 13px; }
section[data-testid="stSidebar"] * { font-size: inherit; }
section[data-testid="stSidebar"] { width: 304px !important; }
section[data-testid="stSidebar"] .stButton button {
    font-size: 11px !important; padding: 8px 9px 8px 4.8em !important;
    text-align: left !important; white-space: normal !important;
    word-break: keep-all; line-height: 1.5;
    min-height: 48px !important;
    display: block !important;
    overflow: hidden;
    text-indent: -4.0em;
    justify-content: flex-start !important; align-items: flex-start !important;
}
section[data-testid="stSidebar"] .stButton button p,
section[data-testid="stSidebar"] .stButton button span,
section[data-testid="stSidebar"] .stButton button div {
    text-align: left !important; justify-content: flex-start !important;
}
section[data-testid="stSidebar"] .stRadio label { font-size: 11px !important; padding: 2px 5px !important; }
.badge { display: inline-block; padding: 1px 6px; border-radius: 8px;
         font-size: 10px; font-weight: bold; color: white; margin-left: 4px; vertical-align: middle; }
.badge-실무팁 { background: #0071e3; } .badge-도입사례 { background: #34c759; }
.badge-트렌드 { background: #5856d6; } .badge-자동화 { background: #af52de; }
.advisor-box { background: #1a1a2e; border-left: 3px solid #0071e3; border-radius: 6px;
               padding: 12px 14px; margin: 8px 0; color: #f0f0f0; font-size: 12px;
               white-space: pre-wrap; line-height: 1.5; }
.status-done { color: #27AE60; font-weight: bold; font-size: 11px; }
.status-wait { color: #888; font-size: 11px; }
.stDataFrame { font-size: 11px !important; }
.stTabs [data-baseweb="tab"] { font-size: 12px !important; padding: 6px 12px !important; }
[data-testid="stMetric"] label { font-size: 11px !important; }
[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 18px !important; }
/* 이미지 풀스크린 뷰어 — 닫기 버튼 강화 */
[data-testid="StyledFullScreenButton"] {
    opacity: 1 !important; visibility: visible !important;
}
div[data-testid="stImageFullScreen"] button[aria-label="Close"],
div[data-testid="stImageFullScreen"] button[kind="minimal"],
div[data-baseweb="modal"] button[aria-label="Close"] {
    width: 48px !important; height: 48px !important;
    background: rgba(0, 113, 227, 0.9) !important;
    border-radius: 50% !important; border: none !important;
    color: #fff !important; font-size: 24px !important;
    top: 16px !important; right: 16px !important;
    position: fixed !important; z-index: 999999 !important;
    cursor: pointer !important;
}
div[data-testid="stImageFullScreen"] button[aria-label="Close"]:hover,
div[data-baseweb="modal"] button[aria-label="Close"]:hover {
    background: rgba(0, 113, 227, 1) !important;
    transform: scale(1.1);
}
</style>
""", unsafe_allow_html=True)

# ── 기본 회사 초기화 ──
get_or_create_default_company()

# ── Session State 초기화 ──
defaults = {
    "page": "main",
    "selected_id": None,
    "search": "",
    "custom_topic": "",
    "current_company": "houseman",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── 현재 회사 데이터 로드 ──
def get_current_company():
    try:
        return load_company(st.session_state.current_company)
    except FileNotFoundError:
        st.session_state.current_company = "houseman"
        return get_or_create_default_company()

def get_topics():
    base = get_current_company().get("topics", [])
    ai = st.session_state.get("ai_topics", [])
    return base + ai

if "blogs" not in st.session_state:
    st.session_state.blogs = load_blogs(st.session_state.current_company)

# ── 헬퍼 함수 ──
def get_blog(topic_id):
    return st.session_state.blogs.get(str(topic_id), {})

def is_done(topic_id):
    b = get_blog(topic_id)
    return bool(b.get("final") or b.get("wordpress"))

def done_count():
    return sum(1 for t in get_topics() if is_done(t["id"]))

def update_blog(topic_id, **kwargs):
    current = get_blog(topic_id).copy()
    current.update(kwargs)
    st.session_state.blogs[str(topic_id)] = current
    save_blog(topic_id, current, st.session_state.current_company)

def check_api_key():
    if not CLAUDE_API_KEY:
        st.error("API 키가 설정되지 않았습니다. secrets.toml을 확인하세요.")
        return False
    return True

def get_generated_image_paths(topic_id, platform):
    """생성된 이미지 파일 경로 목록 반환"""
    import glob
    images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "images")
    pattern = os.path.join(images_dir, f"topic_{topic_id:03d}_{platform}_img_*.png")
    paths = sorted(glob.glob(pattern))
    return paths

def _parse_image_layouts(image_plan):
    """이미지 계획에서 각 이미지의 레이아웃 정보 추출"""
    import re as _re
    layouts = []
    blocks = _re.split(r"(?=📷\s*이미지)", image_plan)
    layout_pattern = _re.compile(r"레이아웃\s*[:：]\s*(\S+)")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        match = layout_pattern.search(block)
        if match:
            layouts.append(match.group(1).strip().lower())
        else:
            layouts.append("full")  # 기본값
    return layouts

# ── Apple 미학 CSS (블로그 미리보기 전용 — apple.com/kr 실측 기반) ──
APPLE_BLOG_CSS = """
<style>
  .apple-blog { font-family: -apple-system, 'Apple SD Gothic Neo', 'Pretendard', 'Noto Sans KR', sans-serif;
    max-width: 680px; margin: 0 auto; padding: 32px 20px; line-height: 1.7;
    color: #1d1d1f; font-size: 17px; letter-spacing: -0.022em;
    -webkit-font-smoothing: antialiased; }
  .apple-blog h1 { font-size: 44px; font-weight: 700; margin: 56px 0 20px; color: #1d1d1f;
    letter-spacing: -0.03em; line-height: 1.15; }
  .apple-blog h2 { font-size: 32px; font-weight: 600; margin: 64px 0 16px; color: #1d1d1f;
    letter-spacing: -0.02em; line-height: 1.25; }
  .apple-blog h3 { font-size: 24px; font-weight: 600; margin: 40px 0 12px; color: #1d1d1f;
    letter-spacing: -0.01em; line-height: 1.3; }
  .apple-blog p { margin: 18px 0; color: #1d1d1f; font-size: 17px; line-height: 1.7; }
  .apple-blog li { margin: 10px 0 10px 24px; color: #1d1d1f; font-size: 17px; line-height: 1.7; }
  .apple-blog strong { color: #1d1d1f; font-weight: 600; }
  .apple-blog blockquote { border-left: 3px solid #0071e3; margin: 32px 0; padding: 12px 24px;
    color: #6e6e73; font-size: 16px; line-height: 1.6;
    background: #f5f5f7; border-radius: 0 8px 8px 0; }
  .apple-blog hr { border: none; border-top: 1px solid #d2d2d7; margin: 48px 0; }
  .apple-blog img { border-radius: 12px; display: block; margin: 32px auto;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
  .apple-blog a { color: #0071e3; text-decoration: none; }
  .apple-blog a:hover { text-decoration: underline; }
</style>
"""

def _md_to_preview_html(text):
    """마크다운 → 인라인 스타일 HTML (Streamlit 미리보기 전용)"""
    import re as _re
    # Apple.com 실측 기반 인라인 스타일 (APPLE_BLOG_CSS와 동일 수치)
    S_H1 = 'style="font-size:44px !important;font-weight:700 !important;margin:56px 0 20px !important;color:#1d1d1f;letter-spacing:-0.03em;line-height:1.15 !important;"'
    S_H2 = 'style="font-size:32px !important;font-weight:600 !important;margin:64px 0 16px !important;color:#1d1d1f;letter-spacing:-0.02em;line-height:1.25 !important;"'
    S_H3 = 'style="font-size:24px !important;font-weight:600 !important;margin:40px 0 12px !important;color:#1d1d1f;letter-spacing:-0.01em;line-height:1.3 !important;"'
    S_P  = 'style="font-size:17px !important;margin:18px 0;color:#1d1d1f;line-height:1.7;"'
    S_LI = 'style="font-size:17px !important;margin:10px 0 10px 24px;color:#1d1d1f;line-height:1.7;"'
    S_BQ = 'style="border-left:3px solid #0071e3;margin:32px 0;padding:12px 24px;color:#6e6e73;font-size:16px;line-height:1.6;background:#f5f5f7;border-radius:0 8px 8px 0;"'
    S_HR = 'style="border:none;border-top:1px solid #d2d2d7;margin:48px 0;"'
    S_B  = 'style="font-weight:600 !important;color:#1d1d1f;"'

    def bold(t):
        return _re.sub(r'\*\*(.+?)\*\*', rf'<strong {S_B}>\1</strong>', t)

    lines = text.split("\n")
    html_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            html_lines.append(f'<div {S_H3}>{bold(stripped[4:])}</div>')
        elif stripped.startswith("## "):
            html_lines.append(f'<div {S_H2}>{bold(stripped[3:])}</div>')
        elif stripped.startswith("# "):
            html_lines.append(f'<div {S_H1}>{bold(stripped[2:])}</div>')
        elif stripped.startswith("> "):
            bq_p = 'style="font-size:16px !important;margin:0;color:#6e6e73;line-height:1.6;"'
            html_lines.append(f'<div {S_BQ}><div {bq_p}>{bold(stripped[2:])}</div></div>')
        elif stripped == "---":
            html_lines.append(f'<hr {S_HR}>')
        elif stripped.startswith("- "):
            html_lines.append(f'<div {S_LI}>• {bold(stripped[2:])}</div>')
        elif stripped == "":
            html_lines.append('<div style="height:18px;"></div>')
        else:
            html_lines.append(f'<div {S_P}>{bold(stripped)}</div>')
    return "\n".join(html_lines)

def render_blog_preview(blog_content):
    """블로그 마크다운을 인라인 스타일 HTML로 미리보기"""
    body = _md_to_preview_html(blog_content)
    wrapper = f'<div style="font-family:-apple-system,Apple SD Gothic Neo,Pretendard,Noto Sans KR,sans-serif;max-width:680px;margin:0 auto;padding:32px 20px;-webkit-font-smoothing:antialiased;letter-spacing:-0.022em;">{body}</div>'
    st.html(wrapper)

def render_blog_with_images(blog_content, image_plan, image_paths, platform="naver"):
    """소제목(##) 바로 아래에 이미지를 배치. 워드프레스는 레이아웃 반영."""
    import re as _re
    if not image_paths or not image_plan:
        render_blog_preview(blog_content)
        return

    lines = blog_content.split("\n")
    layouts = _parse_image_layouts(image_plan)

    # 소제목 위치 찾기
    heading_indices = []
    for li, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("##"):
            heading_indices.append(li)

    # 소제목에 이미지 매핑
    img_map = {}
    for i, img_path in enumerate(image_paths):
        layout = layouts[i] if i < len(layouts) else "full"
        if i < len(heading_indices):
            idx = heading_indices[i]
        else:
            spacing = len(lines) // (len(image_paths) + 1)
            idx = min(spacing * (i + 1), len(lines) - 1)
        if idx not in img_map:
            img_map[idx] = []
        img_map[idx].append((img_path, layout))

    # 렌더링
    content_buffer = []
    for li, line in enumerate(lines):
        content_buffer.append(line)
        if li in img_map:
            render_blog_preview("\n".join(content_buffer))
            content_buffer = []
            for img_path, layout in img_map[li]:
                # 이미지는 이미 680px로 리사이즈됨 → 가운데 정렬만 처리
                import base64 as _b64
                try:
                    with open(img_path, "rb") as _f:
                        _img_data = _b64.b64encode(_f.read()).decode()
                    _ext = img_path.rsplit(".", 1)[-1]
                    _mime = f"image/{'jpeg' if _ext == 'jpg' else _ext}"
                    st.html(f'<div style="text-align:center;margin:16px 0;"><img src="data:{_mime};base64,{_img_data}" style="max-width:85%;border-radius:8px;"></div>')
                except Exception:
                    st.image(img_path)

    if content_buffer:
        render_blog_preview("\n".join(content_buffer))

def build_html_with_images(blog_content, image_plan, image_paths, platform="naver", title="블로그"):
    """블로그 글 + 이미지를 base64 임베드한 단일 HTML 파일 생성"""
    import base64
    import re as _re

    # 이미지를 base64로 변환
    def img_to_base64(path):
        try:
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/png;base64,{data}"
        except Exception:
            return ""

    # 마크다운 → HTML 간단 변환
    def md_to_html(text):
        lines = text.split("\n")
        html_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("### "):
                html_lines.append(f"<h3>{stripped[4:]}</h3>")
            elif stripped.startswith("## "):
                html_lines.append(f"<h2>{stripped[3:]}</h2>")
            elif stripped.startswith("# "):
                html_lines.append(f"<h1>{stripped[2:]}</h1>")
            elif stripped.startswith("> "):
                quote_text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped[2:])
                html_lines.append(f"<blockquote><p>{quote_text}</p></blockquote>")
            elif stripped == "---":
                html_lines.append("<hr>")
            elif stripped.startswith("- "):
                item_text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped[2:])
                html_lines.append(f"<li>{item_text}</li>")
            elif stripped == "":
                html_lines.append("<br>")
            else:
                stripped = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
                html_lines.append(f"<p>{stripped}</p>")
        return "\n".join(html_lines)

    # 소제목 위치에 이미지 삽입
    lines = blog_content.split("\n")
    heading_indices = [i for i, l in enumerate(lines) if l.strip().startswith("##")]

    # 레이아웃 파싱
    layouts = _parse_image_layouts(image_plan) if image_plan else []

    # 이미지 매핑
    img_map = {}
    for i, img_path in enumerate(image_paths):
        layout = layouts[i] if i < len(layouts) else "full"
        if i < len(heading_indices):
            idx = heading_indices[i]
        else:
            spacing = len(lines) // (len(image_paths) + 1)
            idx = min(spacing * (i + 1), len(lines) - 1)
        if idx not in img_map:
            img_map[idx] = []
        img_map[idx].append((img_path, layout))

    # HTML 조립
    body_parts = []
    for li, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("### "):
            body_parts.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("## "):
            body_parts.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("# "):
            body_parts.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("> "):
            quote_text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped[2:])
            body_parts.append(f"<blockquote><p>{quote_text}</p></blockquote>")
        elif stripped == "---":
            body_parts.append("<hr>")
        elif stripped.startswith("- "):
            item_text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped[2:])
            body_parts.append(f"<li>{item_text}</li>")
        elif stripped == "":
            body_parts.append("<br>")
        else:
            stripped = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
            body_parts.append(f"<p>{stripped}</p>")

        # 이미지 삽입
        if li in img_map:
            for img_path, layout in img_map[li]:
                b64 = img_to_base64(img_path)
                if not b64:
                    continue
                if platform == "naver" or layout == "full":
                    w = "85%"
                elif layout == "large":
                    w = "85%"
                elif layout == "medium":
                    w = "65%"
                elif layout in ("side-left", "side-right"):
                    w = "45%"
                    fl = "left" if layout == "side-left" else "right"
                    body_parts.append(f'<img src="{b64}" style="width:{w}; float:{fl}; margin:12px 20px 12px 0; border-radius:12px;">')
                    continue
                else:
                    w = "100%"
                body_parts.append(f'<div style="text-align:center; margin:32px 0;"><img src="{b64}" style="width:{w}; max-width:680px; border-radius:12px;"></div>')

    body_html = "\n".join(body_parts)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, 'Apple SD Gothic Neo', 'Pretendard', 'Noto Sans KR', sans-serif;
         max-width: 680px; margin: 0 auto; padding: 40px 24px; line-height: 1.7;
         color: #1d1d1f; background: #fff; font-size: 17px; letter-spacing: -0.022em;
         -webkit-font-smoothing: antialiased; }}
  h1 {{ font-size: 44px; font-weight: 700; margin: 56px 0 20px; color: #1d1d1f;
       letter-spacing: -0.03em; line-height: 1.15; }}
  h2 {{ font-size: 32px; font-weight: 600; margin: 64px 0 16px; color: #1d1d1f;
       letter-spacing: -0.02em; line-height: 1.25; }}
  h3 {{ font-size: 24px; font-weight: 600; margin: 40px 0 12px; color: #1d1d1f;
       letter-spacing: -0.01em; line-height: 1.3; }}
  p {{ margin: 18px 0; color: #1d1d1f; font-size: 17px; line-height: 1.7; }}
  li {{ margin: 10px 0 10px 24px; color: #1d1d1f; font-size: 17px; line-height: 1.7; }}
  strong {{ color: #1d1d1f; font-weight: 600; }}
  blockquote {{ border-left: 3px solid #0071e3; margin: 32px 0; padding: 12px 24px;
               color: #6e6e73; font-style: normal; font-size: 16px; line-height: 1.6;
               background: #f5f5f7; border-radius: 0 8px 8px 0; }}
  hr {{ border: none; border-top: 1px solid #d2d2d7; margin: 48px 0; }}
  img {{ border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
  a {{ color: #0071e3; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  @media (max-width: 600px) {{
    body {{ padding: 24px 16px; font-size: 16px; }}
    img {{ width: 100% !important; }}
    h1 {{ font-size: 32px; margin: 40px 0 16px; }}
    h2 {{ font-size: 26px; margin: 48px 0 12px; }}
  }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""
    return html


# ── 사이드바 ──
with st.sidebar:
    company_data = get_current_company()
    st.markdown(f"#### 🏢 {company_data.get('name', '블로그')}")
    st.caption(company_data.get("website", ""))

    # API 키
    with st.expander("🔑 API 상태", expanded=False):
        if CLAUDE_API_KEY:
            st.success("✓ Claude 설정됨", icon="✅")
        else:
            st.error("❌ Claude API 키 미설정 (secrets.toml)")
        import gemini_client
        if gemini_client.check_api_key():
            st.success("✓ Gemini 설정됨", icon="✅")
        else:
            st.warning("Gemini API 키 미설정")

    st.divider()

    # 검색 + 필터
    TOPICS = get_topics()
    TOTAL = len(TOPICS)

    st.session_state.search = st.text_input(
        "검색", value=st.session_state.search,
        placeholder="🔍 주제 검색...", label_visibility="collapsed",
    )

    dc = done_count()
    st.caption(f"완료 {dc}/{TOTAL}")
    st.divider()

    # ── AI 주제 생성 ──
    gen_topic_btn = st.button("💡 새 주제", use_container_width=True)

    if gen_topic_btn:
        if not check_api_key():
            st.stop()
        with st.spinner("💡 주제발굴사가 새 주제를 찾고 있습니다..."):
            existing_titles = [t["title"] for t in TOPICS]
            result = pipeline.generate_topic(st.session_state.current_company, existing_titles)
            if result:
                new_id = max([t["id"] for t in TOPICS], default=0) + 1
                result["id"] = new_id
                result["source"] = "ai"
                # 회사 JSON에 영구 저장
                from company_manager import load_company, save_company
                company = load_company(st.session_state.current_company)
                company.setdefault("topics", []).append(result)
                save_company(st.session_state.current_company, company)
                st.rerun()
            else:
                st.error("주제 생성에 실패했습니다. 다시 시도해주세요.")

    # 주제 목록 다시 로드 (방금 추가했을 수 있으므로)
    import random
    TOPICS = get_topics()

    # 미작성/작성완료 분리
    undone_naver = [t for t in TOPICS if t.get("platform") == "naver" and not is_done(t["id"])]
    undone_wp = [t for t in TOPICS if t.get("platform") == "wordpress" and not is_done(t["id"])]
    done_topics = [t for t in TOPICS if is_done(t["id"])]

    def _delete_topic(topic_id):
        """미작성 주제를 회사 JSON에서 삭제"""
        from company_manager import load_company, save_company
        company = load_company(st.session_state.current_company)
        company["topics"] = [t for t in company.get("topics", []) if t["id"] != topic_id]
        save_company(st.session_state.current_company, company)

    # Apple 스타일 삭제 버튼: 존재하되 주장하지 않는 연한 회색 ×
    st.markdown("""<style>
    button[kind="secondary"][data-testid="stBaseButton-secondary"]:has(> div > p:only-child) {
        all: unset;
    }
    .del-btn button {
        background: none !important; border: none !important; box-shadow: none !important;
        color: #d2d2d7 !important; font-size: 13px !important; padding: 0 !important;
        min-height: 0 !important; height: auto !important; line-height: 1 !important;
        cursor: pointer !important; opacity: 0.5 !important; transition: opacity 0.2s !important;
    }
    .del-btn button:hover { opacity: 1 !important; color: #6e6e73 !important; }
    </style>""", unsafe_allow_html=True)

    topic_container = st.container(height=520)
    with topic_container:
        # ── 미작성 주제 (삭제 가능) ──
        if undone_naver:
            st.caption(f"📝 네이버 미작성 ({len(undone_naver)}개)")
            for t in undone_naver[:10]:
                col_topic, col_del = st.columns([14, 1])
                with col_topic:
                    is_sel = st.session_state.selected_id == t["id"]
                    ai_badge = " 💡" if t.get("source") == "ai" else ""
                    label = f'⬜ {t["title"]}{ai_badge}'
                    if st.button(label, key=f"topic_{t['id']}", use_container_width=True,
                                 type="primary" if is_sel else "secondary"):
                        st.session_state.selected_id = t["id"]
                        st.rerun()
                with col_del:
                    with st.container():
                        if st.button("×", key=f"del_{t['id']}"):
                            _delete_topic(t["id"])
                            st.rerun()

        if undone_wp:
            st.divider()
            st.caption(f"🌐 워드프레스 미작성 ({len(undone_wp)}개)")
            for t in undone_wp[:10]:
                col_topic, col_del = st.columns([14, 1])
                with col_topic:
                    is_sel = st.session_state.selected_id == t["id"]
                    ai_badge = " 💡" if t.get("source") == "ai" else ""
                    label = f'⬜ {t["title"]}{ai_badge}'
                    if st.button(label, key=f"topic_{t['id']}", use_container_width=True,
                                 type="primary" if is_sel else "secondary"):
                        st.session_state.selected_id = t["id"]
                        st.rerun()
                with col_del:
                    with st.container():
                        if st.button("×", key=f"del_{t['id']}"):
                            _delete_topic(t["id"])
                            st.rerun()

        # ── 작성 완료 (삭제 불가, 영구 보관) ──
        if done_topics:
            st.divider()
            st.caption(f"✅ 작성 완료 · 영구 보관 ({len(done_topics)}개)")
            for t in done_topics:
                platform_icon = "📝" if t.get("platform") == "naver" else "🌐"
                is_sel = st.session_state.selected_id == t["id"]
                label = f'✅ {platform_icon} {t["title"]}'
                if st.button(label, key=f"done_{t['id']}", use_container_width=True,
                             type="primary" if is_sel else "secondary"):
                    st.session_state.selected_id = t["id"]
                    st.rerun()



# ═══════════════════════════════════════════════
#  메인 페이지
# ═══════════════════════════════════════════════
TOPICS = get_topics()
TOTAL = len(TOPICS)

if st.session_state.selected_id is None:
    company_data = get_current_company()
    st.markdown(f"#### 🏢 {company_data.get('name', '')} 블로그 자동화")

    # ── 커스텀 주제 ──
    st.markdown("##### ✏️ 커스텀 주제")
    custom_col1, custom_col2, custom_col3 = st.columns([4, 1.5, 1])
    with custom_col1:
        st.session_state.custom_topic = st.text_input(
            "커스텀", placeholder="원하는 주제를 직접 입력하세요", label_visibility="collapsed",
        )
    with custom_col2:
        custom_platform = st.selectbox(
            "플랫폼", ["📝 네이버", "🌐 워드프레스"],
            label_visibility="collapsed",
        )
    with custom_col3:
        custom_go = st.button("작성", type="primary", use_container_width=True)

    st.caption("💡 일반 주제는 플랫폼이 자동 지정되어 있습니다. 커스텀 주제만 플랫폼을 선택하세요.")

    st.divider()


    # 메트릭
    naver_topics = [t for t in TOPICS if t.get("platform") == "naver"]
    wp_topics = [t for t in TOPICS if t.get("platform") == "wordpress"]
    naver_done = sum(1 for t in naver_topics if is_done(t["id"]))
    wp_done = sum(1 for t in wp_topics if is_done(t["id"]))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📝 네이버", f"{naver_done}/{len(naver_topics)}")
    c2.metric("🌐 워드프레스", f"{wp_done}/{len(wp_topics)}")
    c3.metric("전체 완료", f"{done_count()}/{TOTAL}")
    c4.metric("완료율", f"{int(done_count() / TOTAL * 100) if TOTAL > 0 else 0}%")

    # 커스텀 주제 실행
    if custom_go and st.session_state.custom_topic.strip():
        if not check_api_key():
            st.stop()
        sel_platform = "naver" if "네이버" in custom_platform else "wordpress"
        sel_label = "네이버" if sel_platform == "naver" else "워드프레스"
        import time as _time
        with st.status(f"커스텀 주제 작성 중 ({sel_label})...", expanded=True) as s:
            _t0 = _time.time()
            topic_title = st.session_state.custom_topic.strip()
            results = {}
            cid = st.session_state.current_company
            st.write(f"🍎 파이프라인 — {sel_label} 생성 중...")
            r = pipeline.run_pipeline(topic_title, cid, sel_platform, status_callback=lambda msg: st.write(msg))
            results[sel_platform] = r["blog"]
            elapsed = _time.time() - _t0
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            time_str = f"{minutes}분 {seconds}초" if minutes > 0 else f"{seconds}초"
            s.update(label=f"✅ 커스텀 주제 완료! · {time_str}", state="complete")

        if results.get("naver"):
            st.markdown("##### 📝 네이버 블로그")
            render_blog_preview(results["naver"])
            with st.expander("📋 복사"):
                st.code(results["naver"], language=None)
        if results.get("wordpress"):
            st.markdown("##### 🌐 워드프레스")
            render_blog_preview(results["wordpress"])
            with st.expander("📋 복사"):
                st.code(results["wordpress"], language=None)

    st.stop()

# ═══════════════════════════════════════════════
#  주제 선택됨
# ═══════════════════════════════════════════════
topic = next((t for t in TOPICS if t["id"] == st.session_state.selected_id), None)
if not topic:
    st.error("주제를 찾을 수 없습니다.")
    st.stop()

blog = get_blog(topic["id"])
cid = st.session_state.current_company

st.markdown(
    f'#### {topic["title"]} '
    f'<span class="badge badge-{topic["category"]}">{topic["category"]}</span>',
    unsafe_allow_html=True,
)
st.caption("✅ 완료" if is_done(topic["id"]) else "⬜ 미생성")

# ── 글 생성/재생성 ──
topic_platform = topic.get("platform", "naver")
platform_label = "📝 네이버 블로그" if topic_platform == "naver" else "🌐 워드프레스"
is_already_done = blog.get("final") or blog.get("wordpress")

if not is_already_done:
    st.info(f"아직 생성되지 않은 주제입니다. ({platform_label} 전용)")
    gen_label = f"✨ {platform_label} 생성"
else:
    gen_label = f"🔄 {platform_label} 재생성"

do_gen = st.button(gen_label, type="primary", use_container_width=True, key=f"gen_blog_{topic['id']}")

if do_gen:
    if not check_api_key():
        st.stop()
    import time as _time
    with st.status(f"🍎 파이프라인 — {platform_label} {'재' if is_already_done else ''}생성 중...", expanded=True) as s:
        _t0 = _time.time()
        result = pipeline.run_pipeline(
            topic["title"], cid, topic_platform,
            status_callback=lambda msg: st.write(msg)
        )
        blog_text = result["blog"]
        footer = gen.generate_blog_footer(blog_text, cid)
        blog_text = blog_text + "\n" + footer
        qa_score = result.get("qa_score", 0)
        img_prompts = result.get("image_prompts", "")
        if topic_platform == "naver":
            blog_data = dict(naver=blog_text, final=blog_text,
                             agents=["pipeline_7"], qa_score=qa_score)
            if img_prompts:
                blog_data["naver_images"] = img_prompts
        else:
            blog_data = dict(wordpress=blog_text,
                             agents=["pipeline_7"], qa_score=qa_score)
            if img_prompts:
                blog_data["wp_images"] = img_prompts
        update_blog(topic["id"], **blog_data)
        elapsed = _time.time() - _t0
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        time_str = f"{minutes}분 {seconds}초" if minutes > 0 else f"{seconds}초"
        s.update(label=f"✅ 파이프라인 완료! QA {qa_score}/80 · {time_str}", state="complete")
    blog = get_blog(topic["id"])
    is_already_done = True

if not is_already_done:
    st.stop()

# ── 생성 완료: 해당 플랫폼만 표시 ──
if topic_platform == "naver":
    blog_content = blog.get("final")
    blog_key = "final"
    img_key = "naver_images"
    platform_for_img = "naver"
else:
    blog_content = blog.get("wordpress")
    blog_key = "wordpress"
    img_key = "wp_images"
    platform_for_img = "wordpress"

if blog_content:
    used_agents = blog.get("agents", [])
    if used_agents:
        names = []
        for aid in used_agents:
            if aid in ("pipeline_7", "pipeline_23"):
                names.append("🍎파이프라인")
        st.caption(f"참여 에이전트: {' · '.join(names)}")

    # 이미지가 있으면 글 사이사이에 이미지 삽입, 없으면 글만
    naver_img_paths = get_generated_image_paths(topic["id"], "naver")
    if naver_img_paths and blog.get("naver_images"):
        st.markdown("###### 📖 글 + 이미지 미리보기")
        render_blog_with_images(blog["final"], blog["naver_images"], naver_img_paths)
    else:
        render_blog_preview(blog["final"])

    with st.expander("📋 텍스트만 복사"):
        st.code(blog["final"], language=None)

    # ── HTML 다운로드 버튼 ──
    naver_dl_paths = get_generated_image_paths(topic["id"], "naver")
    html_data = build_html_with_images(
        blog["final"],
        blog.get("naver_images", ""),
        naver_dl_paths,
        platform="naver",
        title=topic["title"],
    )
    st.download_button(
        label="📥 HTML 다운로드 (이미지 포함)",
        data=html_data.encode("utf-8"),
        file_name=f"naver_{topic['id']:03d}_{topic['title'][:20]}.html",
        mime="text/html",
        use_container_width=True,
        key="dl_naver_html",
    )

    st.divider()

    # ── 방향성 전환 (코멘트 수정) — 이미지보다 위 ──
    st.markdown("###### 🔀 방향성 전환")
    comment = st.text_area("방향성 전환", placeholder="글의 방향, 톤, 강조점 등 수정 요청을 입력하세요",
                           height=60, label_visibility="collapsed", key="comment_naver")
    if st.button("✏️ 방향성 전환 적용", use_container_width=True, type="primary", key="apply_naver"):
        if not comment.strip():
            st.warning("수정 요청을 입력해주세요.")
        elif check_api_key():
            with st.spinner("방향성 전환 중..."):
                revised = gen.revise_with_comment(blog["final"], comment, "naver")
            update_blog(topic["id"], final=revised)
            st.rerun()

    st.divider()

    # ── 이미지 배치 ──
    st.markdown("###### 📷 이미지 배치")

    if blog.get("naver_images"):
        with st.expander("📋 이미지 배치 계획 보기", expanded=not bool(naver_img_paths)):
            st.markdown(blog["naver_images"])

        if naver_img_paths:
            st.success(f"✅ 이미지 {len(naver_img_paths)}장 생성 완료")

            # ZIP 다운로드 버튼
            import zipfile, io
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for img_path in naver_img_paths:
                    from pathlib import Path as _P
                    zf.write(img_path, _P(img_path).name)
            zip_buf.seek(0)
            st.download_button(
                "📥 전체 이미지 다운로드 (ZIP)",
                data=zip_buf.getvalue(),
                file_name=f"topic_{topic['id']:03d}_naver_images.zip",
                mime="application/zip",
                use_container_width=True,
            )

            naver_prompts = gemini_client.parse_image_prompts(blog["naver_images"])
            for img_i, img_path in enumerate(naver_img_paths):
                col_img, col_btn = st.columns([4, 1])
                with col_img:
                    st.image(img_path, caption=f"이미지 {img_i+1}", width=385)
                with col_btn:
                    st.write("")
                    st.write("")
                    if st.button("🔄", key=f"regen_naver_img_{img_i}", help=f"이미지 {img_i+1} 다시 만들기"):
                        if not gemini_client.is_authenticated():
                            st.warning("Gemini API 키 필요")
                        elif img_i < len(naver_prompts):
                            with st.spinner(f"이미지 {img_i+1} 재생성 중..."):
                                result = gemini_client.regenerate_single_image(
                                    naver_prompts[img_i], topic["id"], "naver", img_i + 1)
                            if result["success"]:
                                st.success("✅ 재생성 완료!")
                            else:
                                st.error(f"실패: {result['error']}")
                            st.rerun()
                        else:
                            st.warning("프롬프트를 찾을 수 없습니다.")

            if st.button("🔄 전체 이미지 재생성", use_container_width=True, key="gen_all_img_naver"):
                if not gemini_client.is_authenticated():
                    st.warning("Gemini API 키가 필요합니다.")
                else:
                    with st.spinner("전체 이미지 재생성 중..."):
                        results = gemini_client.generate_blog_images(blog["naver_images"], topic["id"], "naver")
                    ok = sum(1 for r in results if r["success"])
                    if ok:
                        st.success(f"✅ {ok}장 재생성 완료")
                    st.rerun()
        else:
            if st.button("🖼️ AI 이미지 생성", use_container_width=True, type="primary", key="gen_img_naver"):
                if not gemini_client.is_authenticated():
                    st.warning("Gemini API 키가 필요합니다.")
                else:
                    with st.status("🖼️ AI가 이미지를 생성하고 있습니다...", expanded=True) as img_s:
                        st.write("🏢 현장콘텐츠 자문위원 + 💡 크리에이티브 자문위원의 콘텐츠 합의 기반...")
                        st.write("🎨 아트디렉션 자문위원의 프롬프트로 이미지 생성 중...")
                        results = gemini_client.generate_blog_images(blog["naver_images"], topic["id"], "naver")
                        img_s.update(label="✅ 이미지 생성 완료!", state="complete")
                    ok = sum(1 for r in results if r["success"])
                    fail = sum(1 for r in results if not r["success"])
                    if ok:
                        st.success(f"✅ {ok}장 생성 완료")
                    if fail:
                        for r in results:
                            if not r["success"]:
                                st.error(f"실패: {r['error']}")
                    st.rerun()

        if st.button("🔄 이미지 계획 재생성", use_container_width=True, key="regen_img_naver"):
            if check_api_key():
                with st.status("🎬 네이버 이미지 팀 재협업...", expanded=True) as s:
                    st.markdown("""<div class="collab-step"><div class="step-label">STEP 1</div>
                    <div class="step-desc">🏢 현장콘텐츠 자문위원 + 💡 크리에이티브 자문위원 콘텐츠 회의 중...</div>
                    <div class="collab-progress"><div class="bar"></div></div></div>""", unsafe_allow_html=True)
                    agent_prompts = ""
                    def naver_regen_cb(msg):
                        st.write(msg)
                    img_plan = gen.generate_image_plan(blog["final"], "naver", agent_prompts, cid, status_callback=naver_regen_cb)
                    update_blog(topic["id"], naver_images=img_plan)
                    s.update(label="✅ 이미지 배치 계획 완료!", state="complete")
                st.rerun()
    else:
        if st.button("📷 이미지 배치 계획 생성", use_container_width=True, type="primary", key="img_plan_naver"):
            if check_api_key():
                with st.status("🎬 네이버 이미지 팀 협업 시작...", expanded=True) as s:
                    st.markdown("""<div class="collab-step"><div class="step-label">STEP 1 · 콘텐츠 회의</div>
                    <div class="step-desc">🏢 현장콘텐츠 자문위원 + 💡 크리에이티브 자문위원이 소제목별 이미지를 논의합니다</div>
                    <div class="collab-progress"><div class="bar"></div></div></div>""", unsafe_allow_html=True)
                    agent_prompts = ""
                    def naver_cb(msg):
                        st.write(msg)
                    img_plan = gen.generate_image_plan(blog["final"], "naver", agent_prompts, cid, status_callback=naver_cb)
                    update_blog(topic["id"], naver_images=img_plan)
                    s.update(label="✅ 이미지 배치 계획 완료!", state="complete")
                st.rerun()
else:
    st.info(f"{platform_label} 글이 없습니다. 위에서 생성해주세요.")
