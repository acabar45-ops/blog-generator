"""
Vertex AI Imagen 3 image generation client.
OAuth2 authentication with client secret JSON file.
Replaces the old gemini_client.py.
"""

import os
import re
import json
import sys
import warnings

# Windows cp949 인코딩 에러 방지
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(errors='replace')
except (OSError, AttributeError):
    pass

# Suppress deprecation warnings from vertexai
warnings.filterwarnings("ignore", category=DeprecationWarning, module="vertexai")
warnings.filterwarnings("ignore", category=UserWarning, module="vertexai")

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

# ── Configuration ──────────────────────────────────────────────
PROJECT_ID = "project-278f381d-5cc2-42f8-84a"
LOCATION = "us-central1"
MODEL_NAME = "imagen-3.0-generate-001"
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
IMAGES_DIR = os.path.join(BASE_DIR, "data", "images")

# ── Module-level state ─────────────────────────────────────────
_credentials = None
_authenticated = False


def _try_auto_auth() -> bool:
    """앱 시작 시 token.json이 있으면 자동으로 인증 시도"""
    global _credentials, _authenticated
    if _authenticated:
        return True
    if not os.path.exists(TOKEN_FILE):
        return False
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        if creds and creds.valid:
            vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=creds)
            _credentials = creds
            _authenticated = True
            print("[Imagen] Auto-authenticated from token.json")
            return True
    except Exception as e:
        print(f"[Imagen] Auto-auth failed: {e}")
    return False


# 모듈 로드 시 자동 인증 시도
_try_auto_auth()


def authenticate() -> bool:
    """
    Handle OAuth2 authentication flow.
    - If token.json exists and is valid, use cached credentials.
    - If expired but refreshable, refresh silently.
    - Otherwise, open browser for interactive login.
    - Initialize vertexai with the resulting credentials.
    Returns True on success, False on failure.
    """
    global _credentials, _authenticated

    try:
        creds = None

        # 1. Try loading cached token
        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            except Exception:
                creds = None

        # 2. Refresh or re-authenticate
        if creds and creds.valid:
            pass  # cached token is still good
        elif creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if creds is None:
            # Full interactive flow
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"[Imagen] ERROR: client_secret.json not found at {CLIENT_SECRET_FILE}")
                return False

            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # 3. Cache the token for next time
        try:
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        except Exception as e:
            print(f"[Imagen] WARNING: Could not save token.json: {e}")

        # 4. Initialize Vertex AI
        vertexai.init(
            project=PROJECT_ID,
            location=LOCATION,
            credentials=creds,
        )

        _credentials = creds
        _authenticated = True
        print("[Imagen] Authentication successful.")
        return True

    except Exception as e:
        print(f"[Imagen] Authentication failed: {e}")
        _authenticated = False
        return False


def is_authenticated() -> bool:
    """Check if already authenticated in this session."""
    return _authenticated and _credentials is not None


def generate_image(prompt: str, filename: str) -> dict:
    """
    Generate a single image using Imagen 3 and save it as PNG.

    Args:
        prompt:   Text prompt for image generation.
        filename: Base filename (without extension).

    Returns:
        {"success": True, "path": "<saved path>", "prompt": "<prompt used>"}
        or {"success": False, "error": "<message>"}
    """
    if not is_authenticated():
        return {"success": False, "error": "Not authenticated. Call authenticate() first."}

    try:
        # Ensure output directory exists
        os.makedirs(IMAGES_DIR, exist_ok=True)

        # 프롬프트는 에이전트가 이미 Google 정책을 숙지하고 작성했으므로 그대로 사용
        # negative_prompt로 최소한의 안전장치만 추가
        negative_prompt = "text, letters, signage, logo, readable sign, close-up face, foreign scenery"

        print(f"[Imagen] Prompt: {prompt[:120]}...")

        model = ImageGenerationModel.from_pretrained(MODEL_NAME)

        response = model.generate_images(
            prompt=prompt,
            negative_prompt=negative_prompt,
            number_of_images=1,
            aspect_ratio="4:3",
        )

        if not response.images:
            return {"success": False, "error": "Imagen returned no images."}

        # Save the first (only) image
        save_path = os.path.join(IMAGES_DIR, f"{filename}.png")
        response.images[0].save(save_path)

        print(f"[Imagen] Saved: {save_path}")
        return {"success": True, "path": save_path, "prompt": prompt}

    except Exception as e:
        error_msg = str(e)
        print(f"[Imagen] Image generation failed: {error_msg}")
        return {"success": False, "error": error_msg}


def _extract_prompts_from_plan(image_plan: str) -> list:
    """이미지 계획에서 프롬프트 추출 — 코드블록/한줄/볼드 등 모든 형식 지원"""
    prompts = []

    # 이미지 블록 분리: ## 📷, 📷, **📷 등 다양한 마커 지원
    blocks = re.split(r"(?=(?:#+ *)?(?:\*\*)?📷)", image_plan)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # 패턴 1: 코드블록 — **Gemini 프롬프트:**\n```\n...\n```
        match = re.search(
            r"(?:Gemini|Imagen)\s*프롬프트\s*(?:\*\*)?\s*[:：]\s*(?:\*\*)?\s*\n\s*```[^\n]*\n([\s\S]*?)```",
            block, re.IGNORECASE
        )
        if match:
            prompt_text = ' '.join(match.group(1).strip().split())
            if prompt_text:
                prompts.append(prompt_text)
                continue

        # 패턴 2: 한 줄 — Gemini 프롬프트: <내용>
        match = re.search(
            r"(?:Gemini|Imagen)\s*프롬프트\s*(?:\*\*)?\s*[:：]\s*(?:\*\*)?\s*(.+)",
            block, re.IGNORECASE
        )
        if match:
            prompt_text = match.group(1).strip().strip('`').strip()
            if prompt_text:
                prompts.append(prompt_text)

    return prompts


def generate_blog_images(image_plan: str, topic_id: int, platform: str) -> list:
    """
    Parse an image plan and generate all images described in it.

    The plan is expected to contain blocks marked with lines like:
        📷 이미지 1: <description>
        Gemini 프롬프트: <the actual prompt to use>

    Args:
        image_plan: Multi-line text describing images to generate.
        topic_id:   Numeric topic identifier.
        platform:   Platform name (e.g. "naver", "tistory").

    Returns:
        List of result dicts from generate_image().
    """
    if not is_authenticated():
        print("[Imagen] Not authenticated. Attempting authentication...")
        if not authenticate():
            return [{"success": False, "error": "Authentication failed."}]

    results = []

    prompts = _extract_prompts_from_plan(image_plan)

    import time

    image_index = 0
    for prompt_text in prompts:
        image_index += 1

        filename = f"topic_{topic_id:03d}_{platform}_img_{image_index:02d}"

        # 쿼터 초과 방지: 이미지 간 15초 대기 (첫 번째 제외)
        if image_index > 1:
            print(f"[Imagen] Waiting 15s to avoid quota limit...")
            time.sleep(15)

        print(f"[Imagen] Generating image {image_index}: {prompt_text[:80]}...")
        result = generate_image(prompt_text, filename)
        results.append(result)

        # 429 에러 시 30초 대기 후 재시도
        if not result["success"] and "429" in result.get("error", ""):
            print(f"[Imagen] Quota exceeded, waiting 30s and retrying...")
            time.sleep(30)
            result = generate_image(prompt_text, filename)
            results[-1] = result

    if not results:
        print("[Imagen] WARNING: No image prompts found in the plan.")

    return results


def parse_image_prompts(image_plan: str) -> list:
    """이미지 계획에서 각 이미지의 프롬프트를 추출하여 리스트로 반환"""
    return _extract_prompts_from_plan(image_plan)


def regenerate_single_image(prompt: str, topic_id: int, platform: str, image_index: int) -> dict:
    """특정 이미지 1장만 재생성"""
    if not is_authenticated():
        if not authenticate():
            return {"success": False, "error": "Authentication failed."}

    filename = f"topic_{topic_id:03d}_{platform}_img_{image_index:02d}"
    print(f"[Imagen] Regenerating image {image_index}: {prompt[:80]}...")
    return generate_image(prompt, filename)
