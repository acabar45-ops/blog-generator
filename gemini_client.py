"""
Gemini (나노바나나) API 연동 — 이미지 생성 (Imagen 4 Ultra)
"""
import re
import requests
import base64
import json
from pathlib import Path
from config import GEMINI_API_KEY

# 이미지 저장 폴더
IMAGE_DIR = Path(__file__).parent / "data" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)


VALID_RATIOS = {"16:9", "4:3", "1:1", "3:4", "9:16"}


def _detect_aspect_ratio(prompt: str) -> str:
    """프롬프트에서 종횡비 태그를 감지. 기본값 16:9."""
    # 한글: 종횡비: X:Y
    match = re.search(r'종횡비\s*[:：]\s*(\d+:\d+)', prompt)
    if match and match.group(1) in VALID_RATIOS:
        return match.group(1)
    # 영문: aspect_ratio: X:Y
    match = re.search(r'aspect.?ratio\s*[:：]\s*(\d+:\d+)', prompt, re.IGNORECASE)
    if match and match.group(1) in VALID_RATIOS:
        return match.group(1)
    return "16:9"


def _clean_ratio_tag(prompt: str) -> str:
    """프롬프트에서 종횡비 태그를 제거 (API에 전달 불필요)."""
    prompt = re.sub(r'종횡비\s*[:：]\s*\d+:\d+\s*', '', prompt)
    prompt = re.sub(r'aspect.?ratio\s*[:：]\s*\d+:\d+\s*', '', prompt, flags=re.IGNORECASE)
    return prompt.strip()


def generate_image(prompt: str, filename: str = "image", aspect_ratio: str = None) -> dict:
    """
    Gemini API로 이미지 생성 (Imagen 4 Ultra)

    Args:
        prompt: 이미지 생성 프롬프트 (영문)
        filename: 저장할 파일명 (확장자 제외)
        aspect_ratio: 종횡비 (16:9/4:3/1:1/3:4/9:16). None이면 프롬프트에서 자동 감지.

    Returns:
        {"success": True, "path": "저장경로", "prompt": "사용된 프롬프트", "aspect_ratio": "비율"}
        또는
        {"success": False, "error": "에러메시지"}
    """
    if not GEMINI_API_KEY or not GEMINI_API_KEY.strip():
        return {"success": False, "error": "Gemini API 키가 설정되지 않았습니다."}

    try:
        # 종횡비 결정: 명시적 인자 > 프롬프트 감지 > 기본값
        ratio = aspect_ratio or _detect_aspect_ratio(prompt)
        clean_prompt = _clean_ratio_tag(prompt)

        print(f"[Gemini] Generating image ({ratio}): {clean_prompt[:80]}...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-ultra-generate-001:predict?key={GEMINI_API_KEY}"

        headers = {"Content-Type": "application/json"}

        payload = {
            "instances": [
                {"prompt": clean_prompt}
            ],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": ratio
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=120)

        print(f"[Gemini] Response status: {response.status_code}")
        if response.status_code != 200:
            print(f"[Gemini] ERROR: {response.text[:500]}")
            return {"success": False, "error": f"API 오류 ({response.status_code}): {response.text[:200]}"}

        result = response.json()

        # Imagen 4 응답에서 이미지 추출
        predictions = result.get("predictions", [])
        if not predictions:
            return {"success": False, "error": "이미지 생성 결과가 없습니다."}

        image_data = predictions[0].get("bytesBase64Encoded", "")
        mime_type = predictions[0].get("mimeType", "image/png")

        if not image_data:
            return {"success": False, "error": "이미지 데이터를 찾을 수 없습니다."}

        # 확장자 결정
        ext = "png"
        if "jpeg" in mime_type or "jpg" in mime_type:
            ext = "jpg"
        elif "webp" in mime_type:
            ext = "webp"

        # 파일 저장 (10% 축소)
        from PIL import Image
        import io as _io
        raw_bytes = base64.b64decode(image_data)
        img = Image.open(_io.BytesIO(raw_bytes))
        new_w = int(img.width * 0.9)
        new_h = int(img.height * 0.9)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        save_path = IMAGE_DIR / f"{filename}.{ext}"
        img.save(save_path, quality=92)

        return {
            "success": True,
            "path": str(save_path),
            "prompt": prompt,
            "aspect_ratio": ratio,
            "mime_type": mime_type,
        }

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

    # 정교한 프롬프트 파서 사용
    prompts = parse_image_prompts(image_plan)
    print(f"[Gemini] Found {len(prompts)} prompts in image plan")

    if not prompts:
        print(f"[Gemini] WARNING: No prompts found! Plan preview: {image_plan[:300]}")
        return results

    import time
    for idx, prompt_text in enumerate(prompts, 1):
        filename = f"topic_{topic_id:03d}_{platform}_img_{idx:02d}"

        # 쿼터 초과 방지: 이미지 간 5초 대기 (첫 번째 제외)
        if idx > 1:
            print(f"[Gemini] Waiting 5s before next image...")
            time.sleep(5)

        result = generate_image(prompt_text, filename)
        result["index"] = idx
        result["prompt_used"] = prompt_text
        results.append(result)

        # 429 에러 시 30초 대기 후 재시도
        if not result["success"] and "429" in result.get("error", ""):
            print(f"[Gemini] Rate limited, waiting 30s and retrying...")
            time.sleep(30)
            result = generate_image(prompt_text, filename)
            results[-1] = result

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
