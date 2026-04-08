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

from agents import AGENTS, CUSTOM_AGENT, NAVER_HIDDEN, WP_HIDDEN, NAVER_AGENTS, WP_AGENTS, recommend_agents
from storage import load_blogs, save_blog
from company_manager import (
    list_companies, load_company, save_company, delete_company,
    get_or_create_default_company, generate_topics_for_company,
)
import generator as gen
import imagen_client
from config import CLAUDE_API_KEY

CATEGORY_COLORS = {
    "실무팁": "#4A90D9",
    "도입사례": "#27AE60",
    "트렌드": "#E67E22",
    "자동화": "#8E44AD",
}

# ── 페이지 설정은 최상단에서 완료 ──

# ── 스타일 ──
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 13px !important; }
h1 { font-size: 1.4rem !important; }
h2 { font-size: 1.2rem !important; }
h3 { font-size: 1.05rem !important; }
h4 { font-size: 0.95rem !important; }
p, li, span, div { font-size: 13px; }
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
.badge-실무팁 { background: #4A90D9; } .badge-도입사례 { background: #27AE60; }
.badge-트렌드 { background: #E67E22; } .badge-자동화 { background: #8E44AD; }
.advisor-box { background: #1a1a2e; border-left: 3px solid #E67E22; border-radius: 6px;
               padding: 12px 14px; margin: 8px 0; color: #f0f0f0; font-size: 12px;
               white-space: pre-wrap; line-height: 1.5; }
.agent-card { background: #1e1e2e; border: 1px solid #333; border-radius: 8px;
              padding: 8px 10px; text-align: center; min-height: 100px;
              display: flex; flex-direction: column; justify-content: center; transition: all 0.2s; }
.agent-card:hover { border-color: #E67E22; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(230,126,34,0.15); }
.agent-card .field { font-size: 10px; color: #aaa; margin-bottom: 2px; }
.agent-card .name { font-size: 12px; font-weight: bold; color: #fff; }
.agent-card .icon { font-size: 16px; margin-bottom: 2px; }
.agent-card .superpower { font-size: 9px; color: #E67E22; margin-top: 3px; line-height: 1.3; }
/* 이미지 팀 협업 애니메이션 */
@keyframes fadeInUp { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
@keyframes slideRight { from { width: 0; } to { width: 100%; } }
.collab-card { background: #1a1a2e; border: 1px solid #333; border-radius: 10px;
               padding: 14px; text-align: center; animation: fadeInUp 0.5s ease-out; }
.collab-card .collab-icon { font-size: 28px; margin-bottom: 4px; }
.collab-card .collab-name { font-size: 13px; font-weight: bold; color: #fff; }
.collab-card .collab-role { font-size: 10px; color: #aaa; margin-top: 2px; }
.collab-card .collab-career { font-size: 9px; color: #888; margin-top: 4px; line-height: 1.3; }
.collab-arrow { text-align: center; font-size: 24px; color: #E67E22; animation: pulse 1.5s infinite; padding-top: 20px; }
.collab-step { background: linear-gradient(135deg, #1a1a2e, #2a1a3e); border: 1px solid #444;
               border-radius: 8px; padding: 10px 14px; margin: 6px 0; }
.collab-step .step-label { font-size: 10px; color: #E67E22; font-weight: bold; letter-spacing: 1px; }
.collab-step .step-desc { font-size: 11px; color: #ccc; margin-top: 3px; }
.collab-progress { height: 3px; background: #333; border-radius: 2px; margin-top: 6px; overflow: hidden; }
.collab-progress .bar { height: 100%; background: linear-gradient(90deg, #E67E22, #F39C12); animation: slideRight 2s ease-out; }
.img-placeholder { background: #1a1a2e; border: 1px dashed #555; border-radius: 6px;
                   padding: 10px 12px; margin: 8px 0; font-size: 11px; color: #ccc; line-height: 1.4; }
.status-done { color: #27AE60; font-weight: bold; font-size: 11px; }
.status-wait { color: #888; font-size: 11px; }
.stDataFrame { font-size: 11px !important; }
.stTabs [data-baseweb="tab"] { font-size: 12px !important; padding: 6px 12px !important; }
[data-testid="stMetric"] label { font-size: 11px !important; }
[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 18px !important; }
.platform-box { background: #1e1e2e; border: 1px solid #444; border-radius: 8px;
                padding: 10px 14px; margin: 4px 0; font-size: 12px; }
/* 이미지 풀스크린 뷰어 — 닫기 버튼 강화 */
[data-testid="StyledFullScreenButton"] {
    opacity: 1 !important; visibility: visible !important;
}
div[data-testid="stImageFullScreen"] button[aria-label="Close"],
div[data-testid="stImageFullScreen"] button[kind="minimal"],
div[data-baseweb="modal"] button[aria-label="Close"] {
    width: 48px !important; height: 48px !important;
    background: rgba(230, 126, 34, 0.9) !important;
    border-radius: 50% !important; border: none !important;
    color: #fff !important; font-size: 24px !important;
    top: 16px !important; right: 16px !important;
    position: fixed !important; z-index: 999999 !important;
    cursor: pointer !important;
}
div[data-testid="stImageFullScreen"] button[aria-label="Close"]:hover,
div[data-baseweb="modal"] button[aria-label="Close"]:hover {
    background: rgba(230, 126, 34, 1) !important;
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
    "category_filter": "전체",
    "bulk_running": False,
    "api_key": CLAUDE_API_KEY,
    "platform_naver": True,
    "platform_wp": False,
    "selected_agents": [],
    "custom_agent_prompt": "",
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
    return get_current_company().get("topics", [])

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

def filtered_topics():
    result = get_topics()
    if st.session_state.category_filter != "전체":
        result = [t for t in result if t["category"] == st.session_state.category_filter]
    if st.session_state.search.strip():
        kw = st.session_state.search.strip().lower()
        result = [t for t in result if kw in t["title"].lower()]
    return result

def update_blog(topic_id, **kwargs):
    current = get_blog(topic_id).copy()
    current.update(kwargs)
    st.session_state.blogs[str(topic_id)] = current
    save_blog(topic_id, current, st.session_state.current_company)

def check_api_key():
    key = st.session_state.api_key.strip()
    if not key:
        st.error("API 키가 설정되지 않았습니다.")
        return False
    gen.CLAUDE_API_KEY = key
    return True

def _auto_recommend_agents(topic_title: str):
    """토픽 선택 시 플랫폼에 맞는 에이전트 2명을 자동 추천"""
    platform = "naver" if st.session_state.get("platform_naver") else "wordpress"
    try:
        recs = recommend_agents(topic_title, platform, CLAUDE_API_KEY)
        st.session_state.selected_agents = recs
    except Exception:
        pass  # 실패 시 기존 선택 유지


def get_selected_agent_prompts():
    """선택된 에이전트 + 플랫폼 필수 에이전트의 프롬프트를 합쳐서 반환"""
    # 숨겨진 필수 에이전트 자동 추가
    all_ids = list(st.session_state.selected_agents)
    if st.session_state.get("platform_naver"):
        for hid in NAVER_HIDDEN:
            if hid not in all_ids:
                all_ids.insert(0, hid)
    if st.session_state.get("platform_wp"):
        for hid in WP_HIDDEN:
            if hid not in all_ids:
                all_ids.insert(0, hid)

    prompts = []
    for agent_id in all_ids:
        if agent_id == "custom":
            if st.session_state.custom_agent_prompt.strip():
                prompts.append(f"[커스텀 에이전트]\n{st.session_state.custom_agent_prompt}")
        else:
            agent = next((a for a in AGENTS if a["id"] == agent_id), None)
            if agent:
                prompts.append(f"[{agent['field']} — {agent['name']}]\n{agent['prompt']}")
    return "\n\n".join(prompts)

def _collab_render(msg):
    """이미지 팀 협업 콜백 — 토론 스토리를 스타일리시하게 렌더링"""
    if not msg or not msg.strip():
        return
    m = msg.strip()
    # 구분선
    if m.startswith("━━━"):
        st.markdown(f'<div style="background:linear-gradient(90deg,#E67E22,#F39C12); padding:6px 14px; border-radius:6px; margin:10px 0 6px; font-size:12px; font-weight:bold; color:#fff;">{m.replace("━━━","").strip()}</div>', unsafe_allow_html=True)
    # 사람 입장
    elif m.startswith(("🏢 **", "💡 **", "🎨 **", "📊 **", "📐 **")):
        st.markdown(f'<div style="font-size:13px; font-weight:bold; margin-top:6px;">{m}</div>', unsafe_allow_html=True)
    # 커리어 / 인용
    elif m.startswith("  └"):
        text = m[3:].strip()
        if text.startswith("_") and text.endswith("_"):
            # 인용문
            st.markdown(f'<div style="font-size:11px; color:#E67E22; font-style:italic; margin-left:20px; margin-bottom:4px;">💬 {text[1:-1]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:10px; color:#999; margin-left:20px;">{text}</div>', unsafe_allow_html=True)
    # 토론 하이라이트 제목
    elif m.startswith("💬 **토론"):
        st.markdown(f'<div style="font-size:12px; font-weight:bold; margin-top:8px; color:#F39C12;">💬 토론 하이라이트</div>', unsafe_allow_html=True)
    # 토론 발언
    elif m.startswith("  🏢") or m.startswith("  💡") or m.startswith("  📊") or m.startswith("  📐") or m.startswith("  🎨"):
        st.markdown(f'<div style="font-size:11px; margin-left:16px; margin-bottom:2px; color:#ddd; line-height:1.5;">{m.strip()}</div>', unsafe_allow_html=True)
    # 합의
    elif m.startswith("  🤝"):
        st.markdown(f'<div style="font-size:11px; margin-left:16px; padding:3px 8px; background:#1a2e1a; border-left:2px solid #27AE60; border-radius:4px; color:#27AE60; margin-bottom:4px;">{m.strip()}</div>', unsafe_allow_html=True)
    # 승패 결과
    elif m.startswith("  🥊"):
        st.markdown(f'<div style="font-size:11px; margin-left:16px; padding:4px 10px; background:#2e1a1a; border-left:3px solid #E74C3C; border-radius:4px; color:#FF6B6B; margin-bottom:4px; font-weight:bold;">{m.strip()}</div>', unsafe_allow_html=True)
    # 합의 결과
    elif m.startswith("  📌"):
        st.markdown(f'<div style="font-size:10px; margin-left:16px; padding:2px 8px; background:#1a1a2e; border-left:2px solid #4A90D9; border-radius:4px; color:#7EB5E5; margin-bottom:6px;">{m.strip()}</div>', unsafe_allow_html=True)
    # 스코어보드
    elif m.startswith("🏆"):
        st.markdown(f'<div style="font-size:13px; padding:8px 14px; background:linear-gradient(135deg,#2e1a00,#1a1a2e); border:1px solid #E67E22; border-radius:8px; text-align:center; margin:6px 0;">{m}</div>', unsafe_allow_html=True)
    # 완료
    elif m.startswith("✅"):
        st.markdown(f'<div style="font-size:12px; font-weight:bold; color:#27AE60; margin-top:6px;">{m}</div>', unsafe_allow_html=True)
    # 일반 진행 메시지
    else:
        st.write(m)

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

def render_blog_with_images(blog_content, image_plan, image_paths, platform="naver"):
    """소제목(##) 바로 아래에 이미지를 배치. 워드프레스는 레이아웃 반영."""
    import re as _re
    if not image_paths or not image_plan:
        st.markdown(blog_content)
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
            st.markdown("\n".join(content_buffer))
            content_buffer = []
            for img_path, layout in img_map[li]:
                if platform == "naver" or layout == "full":
                    st.image(img_path, width=550)
                elif layout == "large":
                    st.image(img_path, width=480)
                elif layout == "medium":
                    col_l, col_c, col_r = st.columns([1, 3, 1])
                    with col_c:
                        st.image(img_path, width=380)
                elif layout == "side-left":
                    col_img, col_txt = st.columns([2, 3])
                    with col_img:
                        st.image(img_path, width=280)
                elif layout == "side-right":
                    col_txt, col_img = st.columns([3, 2])
                    with col_img:
                        st.image(img_path, width=280)
                elif layout == "pair":
                    # pair는 다음 이미지와 나란히 (여기서는 단독 처리)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.image(img_path, width=270)
                else:
                    st.image(img_path, width=550)

    if content_buffer:
        st.markdown("\n".join(content_buffer))

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
            elif stripped.startswith("- "):
                html_lines.append(f"<li>{stripped[2:]}</li>")
            elif stripped == "":
                html_lines.append("<br>")
            else:
                # 볼드 처리
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
        elif stripped.startswith("- "):
            body_parts.append(f"<li>{stripped[2:]}</li>")
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
                    w = "100%"
                elif layout == "large":
                    w = "85%"
                elif layout == "medium":
                    w = "65%"
                elif layout in ("side-left", "side-right"):
                    w = "45%"
                    fl = "left" if layout == "side-left" else "right"
                    body_parts.append(f'<img src="{b64}" style="width:{w}; float:{fl}; margin:10px; border-radius:8px;">')
                    continue
                else:
                    w = "100%"
                body_parts.append(f'<div style="text-align:center; margin:16px 0;"><img src="{b64}" style="width:{w}; max-width:700px; border-radius:8px;"></div>')

    body_html = "\n".join(body_parts)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: 'Pretendard', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
         max-width: 720px; margin: 0 auto; padding: 24px; line-height: 1.8;
         color: #222; background: #fff; font-size: 16px; }}
  h1 {{ font-size: 24px; font-weight: 700; margin: 32px 0 16px; color: #111; }}
  h2 {{ font-size: 20px; font-weight: 600; margin: 28px 0 12px; color: #222;
       border-bottom: 2px solid #E67E22; padding-bottom: 6px; }}
  h3 {{ font-size: 17px; font-weight: 600; margin: 20px 0 8px; color: #333; }}
  p {{ margin: 6px 0; }}
  li {{ margin: 4px 0 4px 20px; }}
  strong {{ color: #E67E22; }}
  img {{ box-shadow: 0 2px 12px rgba(0,0,0,0.1); }}
  @media (max-width: 600px) {{
    body {{ padding: 12px; font-size: 14px; }}
    img {{ width: 100% !important; }}
  }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""
    return html


def switch_company(company_id):
    st.session_state.current_company = company_id
    st.session_state.blogs = load_blogs(company_id)
    st.session_state.selected_id = None
    st.session_state.page = "main"

# ── 사이드바 ──
with st.sidebar:
    company_data = get_current_company()
    st.markdown(f"#### 🏢 {company_data.get('name', '블로그')}")
    st.caption(company_data.get("website", ""))

    # 회사 전환
    with st.expander("⚙️ 회사 설정", expanded=False):
        companies = list_companies()

        # 회사 선택
        if companies:
            selected_company = st.selectbox(
                "회사 선택", companies,
                index=companies.index(st.session_state.current_company) if st.session_state.current_company in companies else 0,
                label_visibility="collapsed",
            )
            if selected_company != st.session_state.current_company:
                switch_company(selected_company)
                st.rerun()

        # 회사 관리 버튼
        c1, c2 = st.columns(2)
        with c1:
            if st.button("➕ 새 회사", use_container_width=True):
                st.session_state.page = "company_new"
                st.rerun()
        with c2:
            if st.button("✏️ 편집", use_container_width=True):
                st.session_state.page = "company_edit"
                st.rerun()

    # API 키
    with st.expander("🔑 API 키", expanded=not bool(st.session_state.api_key.strip())):
        api_input = st.text_input(
            "Claude API 키", value=st.session_state.api_key,
            type="password", placeholder="sk-ant-api03-...",
            label_visibility="collapsed",
        )
        if api_input != st.session_state.api_key:
            st.session_state.api_key = api_input
            gen.CLAUDE_API_KEY = api_input
            st.rerun()
        if st.session_state.api_key.strip():
            st.success("✓ Claude 설정됨", icon="✅")

        st.caption("─ Gemini (이미지) ─")
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
    cat = st.radio(
        "카테고리",
        ["전체", "실무팁", "도입사례", "트렌드", "자동화"],
        horizontal=True, label_visibility="collapsed",
    )
    st.session_state.category_filter = cat

    dc = done_count()
    st.caption(f"완료 {dc} / {TOTAL}개")
    st.divider()

    # 주제 목록
    topic_container = st.container(height=450)
    with topic_container:
        for t in filtered_topics():
            status = "✅" if is_done(t["id"]) else "⬜"
            label = f'{status} {t["id"]:03d}. {t["title"]}'
            is_sel = st.session_state.selected_id == t["id"]
            if st.button(label, key=f"topic_{t['id']}", use_container_width=True,
                         type="primary" if is_sel else "secondary"):
                st.session_state.selected_id = t["id"]
                _auto_recommend_agents(t["title"])
                st.session_state.page = "main"
                st.rerun()

    st.divider()

    # 전체 진행
    if TOTAL > 0:
        st.progress(dc / TOTAL, text=f"진행: {dc}/{TOTAL}")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.session_state.bulk_running:
            if st.button("⏹ 중지", use_container_width=True):
                st.session_state.bulk_running = False
                st.rerun()
        else:
            if st.button("🔄 전체생성", use_container_width=True, type="primary"):
                if check_api_key():
                    st.session_state.bulk_running = True
                    st.rerun()
    with col_b:
        if st.button("📊 전체보기", use_container_width=True):
            st.session_state.page = "all_view"
            st.rerun()

# ═══════════════════════════════════════════════
#  회사 신규 등록 페이지
# ═══════════════════════════════════════════════
if st.session_state.page == "company_new":
    st.markdown("#### ➕ 새 회사 등록")

    col_l, col_r = st.columns(2)
    with col_l:
        new_id = st.text_input("회사 ID (영문, 공백 없이)", placeholder="예: mycompany")
        new_name = st.text_input("회사명", placeholder="예: 마이컴퍼니")
        new_website = st.text_input("웹사이트", placeholder="예: mycompany.co.kr")
    with col_r:
        new_industry = st.text_input("업종/분야", placeholder="예: 인테리어, 법률, 마케팅")
        new_region = st.text_input("서비스 지역", placeholder="예: 서울 전체")
        new_seo = st.text_input("SEO 키워드 (3개)", placeholder="예: 서울 인테리어, 사무실 리모델링")
    new_founded = st.text_input("설립연도", placeholder="예: 2020")

    st.divider()
    st.markdown("##### 📝 회사 상세 정보")
    st.caption("회사에 대한 모든 정보를 자유롭게 써주세요. 많이 쓸수록 AI가 더 좋은 글을 씁니다.")
    new_desc = st.text_area(
        "회사 소개",
        placeholder="예시) 자유롭게 작성:\n\n우리 회사는 2015년에 설립된 인테리어 전문 업체입니다.\n팀 규모는 20명이고 서울 강남 지역을 중심으로 활동합니다.\n주요 고객사는 OO, OO이며...\n핵심 강점은...\n최근 성과는...",
        height=250,
        label_visibility="collapsed",
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 저장 + 주제 자동 생성", type="primary", use_container_width=True):
            if not new_id.strip() or not new_name.strip():
                st.warning("회사 ID와 회사명은 필수입니다.")
            elif not check_api_key():
                st.stop()
            else:
                company_data = {
                    "id": new_id.strip(),
                    "name": new_name.strip(),
                    "website": new_website.strip(),
                    "founded": new_founded.strip(),
                    "region": new_region.strip(),
                    "industry": new_industry.strip(),
                    "seo_keywords": new_seo.strip(),
                    "description": new_desc.strip(),
                    "topics": [],
                }
                with st.status("회사 등록 + 주제 100개 생성 중...", expanded=True) as s:
                    st.write("Claude가 회사에 맞는 100가지 주제를 생성합니다...")
                    try:
                        topics = generate_topics_for_company(company_data, st.session_state.api_key)
                        company_data["topics"] = topics
                        st.write(f"✅ {len(topics)}개 주제 생성 완료!")
                    except Exception as e:
                        st.error(f"주제 생성 실패: {e}")
                        company_data["topics"] = []
                    save_company(new_id.strip(), company_data)
                    s.update(label="✅ 회사 등록 완료!", state="complete")
                switch_company(new_id.strip())
                st.rerun()
    with c2:
        if st.button("← 취소", use_container_width=True):
            st.session_state.page = "main"
            st.rerun()
    st.stop()

# ═══════════════════════════════════════════════
#  회사 편집 페이지
# ═══════════════════════════════════════════════
elif st.session_state.page == "company_edit":
    cd = get_current_company()
    st.markdown(f"#### ✏️ 회사 편집: {cd.get('name', '')}")

    # 기본 정보 (간단히)
    col_l, col_r = st.columns(2)
    with col_l:
        ed_name = st.text_input("회사명", value=cd.get("name", ""))
        ed_website = st.text_input("웹사이트", value=cd.get("website", ""))
        ed_industry = st.text_input("업종/분야", value=cd.get("industry", ""))
    with col_r:
        ed_region = st.text_input("서비스 지역", value=cd.get("region", ""))
        ed_seo = st.text_input("SEO 키워드", value=cd.get("seo_keywords", ""))
        ed_founded = st.text_input("설립연도", value=cd.get("founded", ""))

    st.divider()

    # 회사 정보 자연어 영역
    st.markdown("##### 📝 회사 상세 정보")
    st.caption("자유롭게 작성하세요. 여기에 쓴 내용이 블로그 생성 시 AI에게 전달됩니다. 내용을 계속 추가하면 AI가 더 정확한 글을 씁니다.")

    # 기존 description + extra_info 합쳐서 보여주기
    existing_desc = cd.get("description", "")
    existing_extra = cd.get("extra_info", "")
    if existing_extra and existing_extra not in existing_desc:
        combined_text = existing_desc + "\n\n" + existing_extra if existing_desc else existing_extra
    else:
        combined_text = existing_desc

    ed_desc = st.text_area(
        "회사 소개 (자연어)",
        value=combined_text,
        height=300,
        placeholder="""예시) 자유롭게 쭉 써주세요:

하우스맨은 2011년부터 서울 주요 상권의 상업용 건물을 위탁 관리해온 전문 기업입니다.
15년간 축적한 현장 경험과 자체 개발한 건물관리 자동화 시스템을 결합하여...

팀 규모는 8명이고, 50개 이상의 건물을 관리하고 있습니다.
주요 고객사는 포르쉐코리아, 이브릿지, 미트박스 등입니다.

핵심 강점:
- 수금 자동화 시스템
- QR 민원 접수
- 카카오 알림톡 자동화
- 건물주 전용 포털

최근에 새로운 서비스를 추가했습니다...
경쟁사 대비 차별점은...
고객 후기나 성과 데이터도 여기에 추가하세요.""",
        label_visibility="collapsed",
    )

    st.divider()

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("💾 저장", type="primary", use_container_width=True):
            cd.update({
                "name": ed_name, "website": ed_website, "founded": ed_founded,
                "region": ed_region, "industry": ed_industry,
                "seo_keywords": ed_seo, "description": ed_desc,
            })
            save_company(st.session_state.current_company, cd)
            st.success("저장 완료!")
            st.rerun()
    with c2:
        if st.button("🔄 주제 재생성", use_container_width=True):
            if not check_api_key():
                st.stop()
            with st.status("주제 100개 재생성 중...", expanded=True):
                try:
                    topics = generate_topics_for_company(cd, st.session_state.api_key)
                    cd["topics"] = topics
                    save_company(st.session_state.current_company, cd)
                    st.success(f"{len(topics)}개 주제 재생성 완료!")
                except Exception as e:
                    st.error(f"실패: {e}")
            st.rerun()
    with c3:
        if st.button("← 돌아가기", use_container_width=True):
            st.session_state.page = "main"
            st.rerun()

    # 현재 주제 목록
    st.divider()
    with st.expander(f"📋 현재 주제 ({len(cd.get('topics', []))}개)", expanded=False):
        for t in cd.get("topics", []):
            st.caption(f"{t['id']:03d}. [{t['category']}] {t['title']}")

    # 회사 삭제
    if st.session_state.current_company != "houseman":
        st.divider()
        if st.button("🗑️ 이 회사 삭제", use_container_width=True):
            delete_company(st.session_state.current_company)
            switch_company("houseman")
            st.rerun()

    st.stop()

# ═══════════════════════════════════════════════
#  전체 만들기 자동 처리
# ═══════════════════════════════════════════════
if st.session_state.bulk_running:
    TOPICS = get_topics()
    next_topic = next((t for t in TOPICS if not is_done(t["id"])), None)
    if next_topic:
        with st.status(f"⏳ [{next_topic['id']:03d}] {next_topic['title']}", expanded=True) as s:
            st.write("네이버 블로그 작성 중...")
            agent_prompts = get_selected_agent_prompts()
            naver = gen.generate_naver_blog(next_topic["title"], agent_prompts, st.session_state.current_company)
            update_blog(next_topic["id"],
                        naver=naver, final=naver, wordpress="",
                        agents=st.session_state.selected_agents)
            s.update(label=f"✅ {next_topic['title']}", state="complete")
        st.rerun()
    else:
        st.session_state.bulk_running = False
        st.success(f"🎉 전체 {len(TOPICS)}개 블로그 생성 완료!")
        st.rerun()

# ═══════════════════════════════════════════════
#  전체 보기 페이지
# ═══════════════════════════════════════════════
elif st.session_state.page == "all_view":
    TOPICS = get_topics()
    TOTAL = len(TOPICS)
    st.markdown("#### 📊 전체 블로그 현황")
    st.caption(f"완료 {done_count()}개 / 미완료 {TOTAL - done_count()}개")

    filter_view = st.radio("", ["전체", "완료만", "미완료만"], horizontal=True, label_visibility="collapsed")

    for t in TOPICS:
        done = is_done(t["id"])
        if filter_view == "완료만" and not done:
            continue
        if filter_view == "미완료만" and done:
            continue
        c1, c2, c3, c4 = st.columns([0.5, 7, 1.5, 1.5])
        c1.caption(f"{t['id']:03d}")
        c2.caption(t["title"])
        c3.markdown(f'<span class="badge badge-{t["category"]}">{t["category"]}</span>', unsafe_allow_html=True)
        if done:
            if c4.button("보기", key=f"v_{t['id']}", use_container_width=True):
                st.session_state.selected_id = t["id"]
                _auto_recommend_agents(t["title"])
                st.session_state.page = "main"
                st.rerun()
        else:
            if c4.button("생성", key=f"g_{t['id']}", use_container_width=True):
                st.session_state.selected_id = t["id"]
                _auto_recommend_agents(t["title"])
                st.session_state.page = "main"
                st.rerun()

    st.divider()
    if st.button("← 돌아가기"):
        st.session_state.page = "main"
        st.rerun()

# ═══════════════════════════════════════════════
#  메인 페이지
# ═══════════════════════════════════════════════
else:
    TOPICS = get_topics()
    TOTAL = len(TOPICS)

    if st.session_state.selected_id is None:
        company_data = get_current_company()
        st.markdown(f"#### 🏢 {company_data.get('name', '')} 블로그 자동화")

        # ── 커스텀 주제 ──
        st.markdown("##### ✏️ 커스텀 주제")
        custom_col1, custom_col2 = st.columns([5, 1])
        with custom_col1:
            st.session_state.custom_topic = st.text_input(
                "커스텀", placeholder="원하는 주제를 직접 입력하세요", label_visibility="collapsed",
            )
        with custom_col2:
            custom_go = st.button("작성", type="primary", use_container_width=True)

        st.divider()

        # ── STEP 1: 플랫폼 선택 ──
        st.markdown("##### 📌 STEP 1. 플랫폼 선택")
        p1, p2 = st.columns(2)
        with p1:
            st.session_state.platform_naver = st.checkbox(
                "📝 네이버 블로그", value=st.session_state.platform_naver,
                help="2,000~2,200자 / 현장감·체류시간·공감")
        with p2:
            st.session_state.platform_wp = st.checkbox(
                "🌐 워드프레스", value=st.session_state.platform_wp,
                help="2,500자 내외 / 구글SEO·E-E-A-T·FAQ")

        st.divider()

        # ── STEP 2: 에이전트 선택 ──
        st.markdown("##### 📌 STEP 2. 에이전트 선택 (복수)")
        naver_on = st.session_state.get("platform_naver", False)
        wp_on = st.session_state.get("platform_wp", False)

        # 플랫폼별 숨겨진 필수 에이전트 결정
        hidden_ids = set()
        visible_agent_ids = set()
        if naver_on:
            hidden_ids.update(NAVER_HIDDEN)
            visible_agent_ids.update(NAVER_AGENTS)
        if wp_on:
            hidden_ids.update(WP_HIDDEN)
            visible_agent_ids.update(WP_AGENTS)
        # 둘 다 안 선택이면 전체 표시
        if not naver_on and not wp_on:
            visible_agent_ids = {a["id"] for a in AGENTS}

        st.caption("자문위원을 선택하세요")

        # UI에 표시할 에이전트 필터링 (숨겨진 것 제외)
        visible_agents = [a for a in AGENTS if a["id"] in visible_agent_ids and a["id"] not in hidden_ids]

        cols_per_row = 6
        num_agents = len(visible_agents)
        num_rows = (num_agents + cols_per_row - 1) // cols_per_row
        rows = []
        for _ in range(num_rows):
            rows.extend(st.columns(cols_per_row))
        current_agents = list(st.session_state.selected_agents)

        for i, agent in enumerate(visible_agents):
            with rows[i]:
                sp = agent.get('superpower', '')
                st.markdown(f"""<div class="agent-card">
                    <div class="icon">{agent['icon']}</div>
                    <div class="field">{agent['field']}</div>
                    <div class="name">{agent['name']}</div>
                    <div class="superpower">⚡ {sp}</div>
                </div>""", unsafe_allow_html=True)
                checked = st.checkbox(
                    f"{agent['name']}", value=agent["id"] in current_agents,
                    key=f"agent_{agent['id']}", label_visibility="collapsed",
                )
                if checked and agent["id"] not in current_agents:
                    current_agents.append(agent["id"])
                elif not checked and agent["id"] in current_agents:
                    current_agents.remove(agent["id"])

        custom_agent_on = st.checkbox("✏️ 커스텀 에이전트", value="custom" in current_agents)
        if custom_agent_on:
            if "custom" not in current_agents:
                current_agents.append("custom")
            st.session_state.custom_agent_prompt = st.text_area(
                "커스텀 프롬프트", value=st.session_state.custom_agent_prompt,
                placeholder="예) 20대 여성 건물주 시각으로", height=60, label_visibility="collapsed",
            )
        elif "custom" in current_agents:
            current_agents.remove("custom")

        st.session_state.selected_agents = current_agents

        if current_agents:
            names = []
            for aid in current_agents:
                if aid == "custom":
                    names.append("커스텀")
                else:
                    a = next((x for x in AGENTS if x["id"] == aid), None)
                    if a:
                        names.append(a["name"])
            st.caption(f"선택됨: {len(names)}명 — {' + '.join(names)}")

            # 선택된 에이전트 상세 정보
            with st.expander("📋 참여 에이전트 상세", expanded=False):
                for aid in current_agents:
                    if aid == "custom":
                        continue
                    a = next((x for x in AGENTS if x["id"] == aid), None)
                    if a:
                        st.markdown(f"""<div style="background:#1a1a2e; border-left:3px solid #E67E22; border-radius:6px; padding:8px 12px; margin:4px 0; font-size:11px;">
                        <b>{a['icon']} {a['name']}</b> · {a['field']}<br>
                        <span style="color:#E67E22;">⚡ {a.get('superpower','')}</span><br>
                        <span style="color:#999;">{a.get('bio','')}</span>
                        </div>""", unsafe_allow_html=True)
        else:
            st.caption("선택됨: 0명")

        st.divider()

        # 메트릭
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("전체 주제", f"{TOTAL}개")
        c2.metric("완료", f"{done_count()}개")
        c3.metric("미완료", f"{TOTAL - done_count()}개")
        c4.metric("완료율", f"{int(done_count() / TOTAL * 100) if TOTAL > 0 else 0}%")

        # 커스텀 주제 실행
        if custom_go and st.session_state.custom_topic.strip():
            if not check_api_key():
                st.stop()
            if not st.session_state.platform_naver and not st.session_state.platform_wp:
                st.warning("플랫폼을 최소 1개 선택해주세요.")
                st.stop()
            with st.status("커스텀 주제 작성 중...", expanded=True) as s:
                agent_prompts = get_selected_agent_prompts()
                topic_title = st.session_state.custom_topic.strip()
                results = {}
                if st.session_state.platform_naver:
                    st.write("📝 네이버 블로그 작성 중...")
                    results["naver"] = gen.generate_naver_blog(topic_title, agent_prompts, st.session_state.current_company)
                if st.session_state.platform_wp:
                    st.write("🌐 워드프레스 작성 중...")
                    base = results.get("naver", topic_title)
                    results["wordpress"] = gen.generate_wordpress_blog(base, topic_title, agent_prompts, st.session_state.current_company)
                s.update(label="✅ 커스텀 주제 완료!", state="complete")

            if results.get("naver"):
                st.markdown("##### 📝 네이버 블로그")
                st.markdown(results["naver"])
                with st.expander("📋 복사"):
                    st.code(results["naver"], language=None)
            if results.get("wordpress"):
                st.markdown("##### 🌐 워드프레스")
                st.markdown(results["wordpress"])
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
        f'#### {topic["id"]:03d}. {topic["title"]} '
        f'<span class="badge badge-{topic["category"]}">{topic["category"]}</span>',
        unsafe_allow_html=True,
    )
    st.caption("✅ 완료" if is_done(topic["id"]) else "⬜ 미생성")

    # ── 에이전트 선택 (주제 상세 페이지에서도 항상 표시) ──
    with st.expander("🤖 에이전트 선택", expanded=not is_done(topic["id"])):
        naver_on2 = st.session_state.get("platform_naver", False)
        wp_on2 = st.session_state.get("platform_wp", False)

        hidden_ids2 = set()
        visible_ids2 = set()
        if naver_on2:
            hidden_ids2.update(NAVER_HIDDEN)
            visible_ids2.update(NAVER_AGENTS)
        if wp_on2:
            hidden_ids2.update(WP_HIDDEN)
            visible_ids2.update(WP_AGENTS)
        if not naver_on2 and not wp_on2:
            visible_ids2 = {a["id"] for a in AGENTS}

        # 에이전트는 토픽 선택 시 자동 추천됨

        visible_agents2 = [a for a in AGENTS if a["id"] in visible_ids2 and a["id"] not in hidden_ids2]

        cols_per_row = 6
        num_agents = len(visible_agents2)
        num_rows = (num_agents + cols_per_row - 1) // cols_per_row
        rows = []
        for _ in range(num_rows):
            rows.extend(st.columns(cols_per_row))
        current_agents = list(st.session_state.selected_agents)

        for i, agent in enumerate(visible_agents2):
            with rows[i]:
                sp = agent.get('superpower', '')
                st.markdown(f"""<div class="agent-card">
                    <div class="icon">{agent['icon']}</div>
                    <div class="field">{agent['field']}</div>
                    <div class="name">{agent['name']}</div>
                    <div class="superpower">⚡ {sp}</div>
                </div>""", unsafe_allow_html=True)
                checked = st.checkbox(
                    f"{agent['name']}", value=agent["id"] in current_agents,
                    key=f"dagent_{agent['id']}", label_visibility="collapsed",
                )
                if checked and agent["id"] not in current_agents:
                    current_agents.append(agent["id"])
                elif not checked and agent["id"] in current_agents:
                        current_agents.remove(agent["id"])

        custom_agent_on = st.checkbox("✏️ 커스텀 에이전트", value="custom" in current_agents, key="dcustom_agent")
        if custom_agent_on:
            if "custom" not in current_agents:
                current_agents.append("custom")
            st.session_state.custom_agent_prompt = st.text_area(
                "커스텀 프롬프트", value=st.session_state.custom_agent_prompt,
                placeholder="예) 20대 여성 건물주 시각으로", height=60, label_visibility="collapsed", key="dcustom_prompt",
            )
        elif "custom" in current_agents:
            current_agents.remove("custom")

        st.session_state.selected_agents = current_agents

        if current_agents:
            names = []
            for aid in current_agents:
                if aid == "custom":
                    names.append("커스텀")
                else:
                    a = next((x for x in AGENTS if x["id"] == aid), None)
                    if a:
                        names.append(a["name"])
            st.caption(f"선택됨: {len(names)}명 — {' + '.join(names)}")

    # ── 미생성: 둘 다 없을 때 ──
    if not blog.get("final") and not blog.get("wordpress"):
        st.info("아직 생성되지 않은 주제입니다.")
        gen_col1, gen_col2 = st.columns(2)
        with gen_col1:
            do_naver = st.button("📝 네이버 생성", type="primary", use_container_width=True)
        with gen_col2:
            do_wp = st.button("🌐 워드프레스 생성", use_container_width=True)

        if do_naver:
            if not check_api_key():
                st.stop()
            with st.status("📝 네이버 블로그 생성 중...", expanded=True) as s:
                agent_prompts = get_selected_agent_prompts()
                # 에이전트 활동 상태 표시
                sel_names = []
                for aid in st.session_state.selected_agents:
                    a = next((x for x in AGENTS if x["id"] == aid), None)
                    if a:
                        sel_names.append(f"{a['icon']} {a['name']}")
                if sel_names:
                    st.write(f"🤝 **에이전트 협업 시작**: {' + '.join(sel_names)}")
                    st.write("📋 각 에이전트가 자신의 전문 분야 관점을 제시하고 있습니다...")
                    st.write("✍️ 모든 관점을 균형 있게 융합하여 하나의 글로 통합 중...")
                else:
                    st.write("✍️ 블로그 글을 작성하고 있습니다...")
                naver = gen.generate_naver_blog(topic["title"], agent_prompts, cid)
                update_blog(topic["id"], naver=naver, final=naver, agents=st.session_state.selected_agents)
                s.update(label="✅ 네이버 블로그 생성 완료!", state="complete")
            st.rerun()

        if do_wp:
            if not check_api_key():
                st.stop()
            with st.status("🌐 워드프레스 생성 중...", expanded=True) as s:
                agent_prompts = get_selected_agent_prompts()
                sel_names = []
                for aid in st.session_state.selected_agents:
                    a = next((x for x in AGENTS if x["id"] == aid), None)
                    if a:
                        sel_names.append(f"{a['icon']} {a['name']}")
                if sel_names:
                    st.write(f"🤝 **에이전트 협업 시작**: {' + '.join(sel_names)}")
                    st.write("🔍 SEO 구조 설계 + E-E-A-T 전문성 확보 중...")
                    st.write("📊 각 에이전트가 구글 검색 최적화 관점을 융합하고 있습니다...")
                else:
                    st.write("🔍 SEO 최적화 글을 작성하고 있습니다...")
                wp = gen.generate_wordpress_blog(topic["title"], topic["title"], agent_prompts, cid)
                update_blog(topic["id"], wordpress=wp, final=wp, agents=st.session_state.selected_agents)
                s.update(label="✅ 워드프레스 생성 완료!", state="complete")
            st.rerun()
        st.stop()

    # ── 생성 완료: 탭 ──
    tab_naver, tab_wp = st.tabs(["📝 네이버", "🌐 워드프레스"])

    # ── 네이버 탭 ──
    with tab_naver:
        if blog.get("final"):
            used_agents = blog.get("agents", [])
            if used_agents:
                names = []
                for aid in used_agents:
                    if aid == "custom":
                        names.append("✏️커스텀")
                    else:
                        a = next((x for x in AGENTS if x["id"] == aid), None)
                        if a:
                            names.append(f"{a['icon']}{a['name']}")
                st.caption(f"참여 에이전트: {' · '.join(names)}")

            # 이미지가 있으면 글 사이사이에 이미지 삽입, 없으면 글만
            naver_img_paths = get_generated_image_paths(topic["id"], "naver")
            if naver_img_paths and blog.get("naver_images"):
                st.markdown("###### 📖 글 + 이미지 미리보기")
                render_blog_with_images(blog["final"], blog["naver_images"], naver_img_paths)
            else:
                st.markdown(blog["final"])

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

            # 이미지 팀 소개
            with st.expander("🎬 네이버 이미지 팀 소개", expanded=False):
                tc1, tc2, tc3 = st.columns(3)
                with tc1:
                    st.markdown("""<div class="collab-card">
                        <div class="collab-icon">🏢</div>
                        <div class="collab-name">현장콘텐츠 자문위원</div>
                        <div class="collab-role">콘텐츠 기획</div>
                        <div class="collab-career">부동산 현장 콘텐츠 제작 10년+<br>한국 건물주 시각 반응 데이터 전문가<br>상업용 건물 현장 촬영 디렉팅</div>
                    </div>""", unsafe_allow_html=True)
                with tc2:
                    st.markdown("""<div class="collab-card">
                        <div class="collab-icon">💡</div>
                        <div class="collab-name">크리에이티브 자문위원</div>
                        <div class="collab-role">크리에이티브 디렉터</div>
                        <div class="collab-career">광고·마케팅 크리에이티브 총괄 전문가<br>한국 소비자 심리를 꿰뚫는 감각<br>40~60대 한국인 감성 마케팅 전문</div>
                    </div>""", unsafe_allow_html=True)
                with tc3:
                    st.markdown("""<div class="collab-card">
                        <div class="collab-icon">🎨</div>
                        <div class="collab-name">아트디렉션 자문위원</div>
                        <div class="collab-role">아트 디렉터</div>
                        <div class="collab-career">미니멀하고 통일된 비주얼 톤 설계 전문가<br>전체 이미지 톤 통일 및 프롬프트 작성<br>미니멀리즘 비주얼 톤 통일의 마에스트로</div>
                    </div>""", unsafe_allow_html=True)
                st.markdown("""<div class="collab-step">
                    <div class="step-label">STEP 1 · 콘텐츠 회의</div>
                    <div class="step-desc">🏢 현장콘텐츠 자문위원이 현장 사진을 제안 → 💡 크리에이티브 자문위원이 감성/마케팅 관점으로 보완 → 소제목별 이미지 합의</div>
                </div>
                <div class="collab-step">
                    <div class="step-label">STEP 2 · 비주얼 실행</div>
                    <div class="step-desc">🎨 아트디렉션 자문위원이 합의 결과를 받아 → 전체 톤 통일 → 미니멀 프롬프트 작성 → Imagen 3 생성</div>
                </div>""", unsafe_allow_html=True)

            if blog.get("naver_images"):
                with st.expander("📋 이미지 배치 계획 보기", expanded=not bool(naver_img_paths)):
                    st.markdown(blog["naver_images"])

                if naver_img_paths:
                    st.success(f"✅ 이미지 {len(naver_img_paths)}장 생성 완료")
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
                    if st.button("🖼️ Imagen 3 이미지 생성", use_container_width=True, type="primary", key="gen_img_naver"):
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
                            agent_prompts = get_selected_agent_prompts()
                            def naver_regen_cb(msg):
                                _collab_render(msg)
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
                            agent_prompts = get_selected_agent_prompts()
                            def naver_cb(msg):
                                _collab_render(msg)
                            img_plan = gen.generate_image_plan(blog["final"], "naver", agent_prompts, cid, status_callback=naver_cb)
                            update_blog(topic["id"], naver_images=img_plan)
                            s.update(label="✅ 이미지 배치 계획 완료!", state="complete")
                        st.rerun()
        else:
            st.info("네이버 버전이 없습니다. 생성해주세요.")

    # ── 워드프레스 탭 ──
    with tab_wp:
        if blog.get("wordpress"):
            used_agents = blog.get("agents", [])
            if used_agents:
                names = []
                for aid in used_agents:
                    if aid == "custom":
                        names.append("✏️커스텀")
                    else:
                        a = next((x for x in AGENTS if x["id"] == aid), None)
                        if a:
                            names.append(f"{a['icon']}{a['name']}")
                st.caption(f"참여 에이전트: {' · '.join(names)}")

            # 이미지가 있으면 글 사이사이에 이미지 삽입
            wp_img_paths = get_generated_image_paths(topic["id"], "wordpress")
            if wp_img_paths and blog.get("wp_images"):
                st.markdown("###### 📖 글 + 이미지 미리보기")
                render_blog_with_images(blog["wordpress"], blog["wp_images"], wp_img_paths, platform="wordpress")
            else:
                st.markdown(blog["wordpress"])

            with st.expander("📋 텍스트만 복사"):
                st.code(blog["wordpress"], language=None)

            # ── HTML 다운로드 버튼 ──
            wp_dl_paths = get_generated_image_paths(topic["id"], "wordpress")
            wp_html_data = build_html_with_images(
                blog["wordpress"],
                blog.get("wp_images", ""),
                wp_dl_paths,
                platform="wordpress",
                title=topic["title"],
            )
            st.download_button(
                label="📥 HTML 다운로드 (이미지 포함)",
                data=wp_html_data.encode("utf-8"),
                file_name=f"wordpress_{topic['id']:03d}_{topic['title'][:20]}.html",
                mime="text/html",
                use_container_width=True,
                key="dl_wp_html",
            )

            st.divider()

            # ── 방향성 전환 (코멘트 수정) — 이미지보다 위 ──
            st.markdown("###### 🔀 방향성 전환")
            comment_wp = st.text_area("방향성 전환", placeholder="글의 방향, 톤, SEO 키워드 등 수정 요청을 입력하세요",
                                      height=60, label_visibility="collapsed", key="comment_wp")
            if st.button("✏️ 방향성 전환 적용", use_container_width=True, type="primary", key="apply_wp"):
                if not comment_wp.strip():
                    st.warning("수정 요청을 입력해주세요.")
                elif check_api_key():
                    with st.spinner("방향성 전환 중..."):
                        revised = gen.revise_with_comment(blog["wordpress"], comment_wp, "wordpress")
                    update_blog(topic["id"], wordpress=revised)
                    st.rerun()

            st.divider()

            # ── 이미지 배치 ──
            st.markdown("###### 📷 이미지 배치")

            # 워드프레스 이미지 팀 소개 (네이버와 다른 팀!)
            with st.expander("🎬 워드프레스 이미지 팀 소개", expanded=False):
                tc1, tc2, tc3 = st.columns(3)
                with tc1:
                    st.markdown("""<div class="collab-card">
                        <div class="collab-icon">📊</div>
                        <div class="collab-name">정보시각화 자문위원</div>
                        <div class="collab-role">정보 시각화 설계</div>
                        <div class="collab-career">데이터 시각화·인포그래픽·다이어그램 설계 전문가<br>불필요한 장식 제거, 정보 밀도 극대화<br>데이터→시각물 변환의 권위자</div>
                    </div>""", unsafe_allow_html=True)
                with tc2:
                    st.markdown("""<div class="collab-card">
                        <div class="collab-icon">📐</div>
                        <div class="collab-name">미디어디자인 자문위원</div>
                        <div class="collab-role">한국 미디어 디자인</div>
                        <div class="collab-career">한국 미디어/디자인 산업 전문가<br>글로벌 트렌드와 한국 비즈니스 맥락의 교차점 파악<br>한국 비즈니스 정보 디자인의 핵심 인물</div>
                    </div>""", unsafe_allow_html=True)
                with tc3:
                    st.markdown("""<div class="collab-card">
                        <div class="collab-icon">🎨</div>
                        <div class="collab-name">아트디렉션 자문위원</div>
                        <div class="collab-role">미니멀 실행</div>
                        <div class="collab-career">미니멀하고 통일된 비주얼 톤 설계 전문가<br>전체 이미지 톤 통일 및 프롬프트 작성<br>미니멀리즘 비주얼 톤 통일의 마에스트로</div>
                    </div>""", unsafe_allow_html=True)
                st.markdown("""<div class="collab-step">
                    <div class="step-label">STEP 1 · 정보 시각화 회의</div>
                    <div class="step-desc">📊 정보시각화 자문위원이 데이터 시각화 방향을 설계 → 📐 미디어디자인 자문위원이 한국 비즈니스 맥락으로 조율 → 소제목별 정보 시각물 합의</div>
                </div>
                <div class="collab-step">
                    <div class="step-label">STEP 2 · 미니멀 실행</div>
                    <div class="step-desc">🎨 아트디렉션 자문위원이 합의 결과를 받아 → 미니멀 스타일 톤 통일 → 레이아웃 선택 → 미니멀 프롬프트 작성</div>
                </div>""", unsafe_allow_html=True)

            if blog.get("wp_images"):
                with st.expander("📋 이미지 배치 계획 보기", expanded=not bool(wp_img_paths)):
                    st.markdown(blog["wp_images"])

                if wp_img_paths:
                    st.success(f"✅ 이미지 {len(wp_img_paths)}장 생성 완료")
                    wp_prompts = gemini_client.parse_image_prompts(blog["wp_images"])
                    for img_i, img_path in enumerate(wp_img_paths):
                        col_img, col_btn = st.columns([4, 1])
                        with col_img:
                            st.image(img_path, caption=f"이미지 {img_i+1}", width=385)
                        with col_btn:
                            st.write("")
                            st.write("")
                            if st.button("🔄", key=f"regen_wp_img_{img_i}", help=f"이미지 {img_i+1} 다시 만들기"):
                                if not gemini_client.is_authenticated():
                                    st.warning("Gemini API 키 필요")
                                elif img_i < len(wp_prompts):
                                    with st.spinner(f"이미지 {img_i+1} 재생성 중..."):
                                        result = gemini_client.regenerate_single_image(
                                            wp_prompts[img_i], topic["id"], "wordpress", img_i + 1)
                                    if result["success"]:
                                        st.success("✅ 재생성 완료!")
                                    else:
                                        st.error(f"실패: {result['error']}")
                                    st.rerun()
                                else:
                                    st.warning("프롬프트를 찾을 수 없습니다.")

                    if st.button("🔄 전체 이미지 재생성", use_container_width=True, key="gen_all_img_wp"):
                        if not gemini_client.is_authenticated():
                            st.warning("Gemini API 키가 필요합니다.")
                        else:
                            with st.spinner("전체 이미지 재생성 중..."):
                                results = gemini_client.generate_blog_images(blog["wp_images"], topic["id"], "wordpress")
                            ok = sum(1 for r in results if r["success"])
                            if ok:
                                st.success(f"✅ {ok}장 재생성 완료")
                            st.rerun()
                else:
                    if st.button("🖼️ Imagen 3 이미지 생성", use_container_width=True, type="primary", key="gen_img_wp"):
                        if not gemini_client.is_authenticated():
                            st.warning("Gemini API 키가 필요합니다.")
                        else:
                            with st.status("🖼️ AI가 이미지를 생성하고 있습니다...", expanded=True) as img_s:
                                st.write("📊 정보시각화 자문위원 + 📐 미디어디자인 자문위원의 정보 시각화 합의 기반...")
                                st.write("🎨 아트디렉션 자문위원의 미니멀 프롬프트로 이미지 생성 중...")
                                results = gemini_client.generate_blog_images(blog["wp_images"], topic["id"], "wordpress")
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

                if st.button("🔄 이미지 계획 재생성", use_container_width=True, key="regen_img_wp"):
                    if check_api_key():
                        with st.status("🎬 워드프레스 이미지 팀 재협업...", expanded=True) as s:
                            st.markdown("""<div class="collab-step"><div class="step-label">STEP 1</div>
                            <div class="step-desc">📊 정보시각화 자문위원 + 📐 미디어디자인 자문위원 정보 시각화 회의 중...</div>
                            <div class="collab-progress"><div class="bar"></div></div></div>""", unsafe_allow_html=True)
                            agent_prompts = get_selected_agent_prompts()
                            def wp_regen_cb(msg):
                                _collab_render(msg)
                            img_plan = gen.generate_image_plan(blog["wordpress"], "wordpress", agent_prompts, cid, status_callback=wp_regen_cb)
                            update_blog(topic["id"], wp_images=img_plan)
                            s.update(label="✅ 이미지 배치 계획 완료!", state="complete")
                        st.rerun()
            else:
                if st.button("📷 이미지 배치 계획 생성", use_container_width=True, type="primary", key="img_plan_wp"):
                    if check_api_key():
                        with st.status("🎬 워드프레스 이미지 팀 협업 시작...", expanded=True) as s:
                            st.markdown("""<div class="collab-step"><div class="step-label">STEP 1 · 정보 시각화 회의</div>
                            <div class="step-desc">📊 정보시각화 자문위원 + 📐 미디어디자인 자문위원이 소제목별 정보 시각물을 논의합니다</div>
                            <div class="collab-progress"><div class="bar"></div></div></div>""", unsafe_allow_html=True)
                            agent_prompts = get_selected_agent_prompts()
                            def wp_cb(msg):
                                _collab_render(msg)
                            img_plan = gen.generate_image_plan(blog["wordpress"], "wordpress", agent_prompts, cid, status_callback=wp_cb)
                            update_blog(topic["id"], wp_images=img_plan)
                            s.update(label="✅ 이미지 배치 계획 완료!", state="complete")
                        st.rerun()
        else:
            st.info("워드프레스 버전이 아직 없습니다.")
            st.caption("네이버 최종본 기반으로 2,500자 내외 SEO 구조로 변환됩니다.")
            if st.button("🌐 워드프레스 버전 만들기", type="primary", use_container_width=True):
                if check_api_key():
                    with st.spinner("워드프레스 생성 중..."):
                        agent_prompts = get_selected_agent_prompts()
                        wp = gen.generate_wordpress_blog(blog["final"], topic["title"], agent_prompts, cid)
                        update_blog(topic["id"], wordpress=wp)
                    st.rerun()
