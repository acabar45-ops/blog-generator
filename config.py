# ================================================================
#  하우스맨 블로그 자동화 — 설정 파일
#  로컬: .streamlit/secrets.toml 에서 읽음
#  배포: Streamlit Cloud > Settings > Secrets 에서 설정
# ================================================================
import streamlit as st

# ── Claude API ──
CLAUDE_API_KEY = st.secrets["CLAUDE_API_KEY"] if "CLAUDE_API_KEY" in st.secrets else ""
CLAUDE_MODEL = st.secrets["CLAUDE_MODEL"] if "CLAUDE_MODEL" in st.secrets else "claude-sonnet-4-6"

# ── Vertex AI (Imagen 3) ──
VERTEX_PROJECT_ID = st.secrets["VERTEX_PROJECT_ID"] if "VERTEX_PROJECT_ID" in st.secrets else ""
VERTEX_LOCATION = st.secrets["VERTEX_LOCATION"] if "VERTEX_LOCATION" in st.secrets else "us-central1"
CLIENT_SECRET_FILE = "client_secret.json"

# ── 앱 비밀번호 ──
APP_PASSWORD = st.secrets["APP_PASSWORD"] if "APP_PASSWORD" in st.secrets else ""

# ── Gemini (gemini_client.py 용) ──
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else ""
