# ================================================================
#  하우스맨 블로그 자동화 — 설정 파일
#  로컬: .streamlit/secrets.toml 에서 읽음
#  배포: Streamlit Cloud > Settings > Secrets 에서 설정
# ================================================================
import streamlit as st

# ── Claude API ──
CLAUDE_API_KEY = st.secrets.get("CLAUDE_API_KEY", "")
CLAUDE_MODEL = st.secrets.get("CLAUDE_MODEL", "claude-sonnet-4-6")

# ── Vertex AI (Imagen 3) ──
VERTEX_PROJECT_ID = st.secrets.get("VERTEX_PROJECT_ID", "")
VERTEX_LOCATION = st.secrets.get("VERTEX_LOCATION", "us-central1")
CLIENT_SECRET_FILE = "client_secret.json"

# ── 앱 비밀번호 ──
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")

# ── Gemini (gemini_client.py 용) ──
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
