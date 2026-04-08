"""
Gemini (나노바나나) API 연동 — 이미지 생성
"""
import requests
import base64
import json
from pathlib import Path
from config import GEMINI_API_KEY

# 이미지 저장 폴더
IMAGE_DIR = Path(__file__).parent / "data" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def generate_image(prompt: str, filename: str = "image") -> dict:
    """
    Gemini API로 이미지 생성

    Args:
        prompt: 이미지 생성 프롬프트 (영문)
        filename: 저장할 파일명 (확장자 제외)

    Returns:
        {"success": True, "path": "저장경로", "prompt": "사용된 프롬프트"}
        또는
        {"success": False, "error": "에러메시지"}
    """
    if not GEMINI_API_KEY or not GEMINI_API_KEY.strip():
        return {"success": False, "error": "Gemini API 키가 설정되지 않았습니다."}

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"

        headers = {"Content-Type": "application/json"}

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"Generate a realistic image based on this description. Do NOT include any text or watermarks in the image.\n\nDescription: {prompt}"
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"]
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            return {"success": False, "error": f"API 오류 ({response.status_code}): {response.text[:200]}"}

        result = response.json()

        # 이미지 데이터 추출
        candidates = result.get("candidates", [])
        if not candidates:
            return {"success": False, "error": "이미지 생성 결과가 없습니다."}

        parts = candidates[0].get("content", {}).get("parts", [])

        for part in parts:
            if "inlineData" in part:
                image_data = part["inlineData"]["data"]
                mime_type = part["inlineData"].get("mimeType", "image/png")

                # 확장자 결정
                ext = "png"
                if "jpeg" in mime_type or "jpg" in mime_type:
                    ext = "jpg"
                elif "webp" in mime_type:
                    ext = "webp"

                # 파일 저장
                save_path = IMAGE_DIR / f"{filename}.{ext}"
                with open(save_path, "wb") as f:
                    f.write(base64.b64decode(image_data))

                return {
                    "success": True,
                    "path": str(save_path),
                    "prompt": prompt,
                    "mime_type": mime_type,
                }

        return {"success": False, "error": "이미지 데이터를 찾을 수 없습니다."}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "API 요청 시간 초과 (60초)"}
    except Exception as e:
        return {"success": False, "error": f"오류 발생: {str(e)}"}


def generate_blog_images(image_plan: str, topic_id: int, platform: str) -> list:
    """
    이미지 계획서를 파싱하여 각 이미지를 Gemini로 생성

    Args:
        image_plan: generate_image_plan()의 결과 텍스트
        topic_id: 주제 번호
        platform: "naver" 또는 "wordpress"

    Returns:
        [{"index": 1, "prompt": "...", "path": "...", "success": True}, ...]
    """
    results = []

    # 이미지 계획에서 Gemini 프롬프트 추출
    lines = image_plan.split("\n")
    current_index = 0
    current_prompt = ""

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("📷 이미지"):
            # 새 이미지 시작
            try:
                num = stripped.split("이미지")[1].strip()
                current_index = int(num)
            except (ValueError, IndexError):
                current_index += 1

        elif stripped.lower().startswith("gemini 프롬프트:") or stripped.lower().startswith("gemini프롬프트:"):
            current_prompt = stripped.split(":", 1)[1].strip()

            if current_prompt:
                filename = f"topic_{topic_id:03d}_{platform}_img_{current_index:02d}"
                result = generate_image(current_prompt, filename)
                result["index"] = current_index
                result["prompt_used"] = current_prompt
                results.append(result)

    return results


def check_api_key() -> bool:
    """Gemini API 키 유효성 간단 체크"""
    if not GEMINI_API_KEY or not GEMINI_API_KEY.strip():
        return False
    return True


def is_authenticated() -> bool:
    """Gemini는 API 키만 있으면 인증 완료"""
    return check_api_key()


def parse_image_prompts(image_plan: str) -> list:
    """이미지 계획에서 각 이미지의 프롬프트를 추출하여 리스트로 반환"""
    import re
    prompts = []
    blocks = re.split(r"(?=(?:#+ *)?(?:\*\*)?📷)", image_plan)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        match = re.search(
            r"(?:Gemini|Imagen)\s*프롬프트\s*(?:\*\*)?\s*[:：]\s*(?:\*\*)?\s*\n\s*```[^\n]*\n([\s\S]*?)```",
            block, re.IGNORECASE
        )
        if match:
            prompt_text = ' '.join(match.group(1).strip().split())
            if prompt_text:
                prompts.append(prompt_text)
                continue
        match = re.search(
            r"(?:Gemini|Imagen)\s*프롬프트\s*(?:\*\*)?\s*[:：]\s*(?:\*\*)?\s*(.+)",
            block, re.IGNORECASE
        )
        if match:
            prompt_text = match.group(1).strip().strip('`').strip()
            if prompt_text:
                prompts.append(prompt_text)
    return prompts


def regenerate_single_image(prompt: str, topic_id: int, platform: str, image_index: int) -> dict:
    """특정 이미지 1장만 재생성"""
    filename = f"topic_{topic_id:03d}_{platform}_img_{image_index:02d}"
    return generate_image(prompt, filename)
