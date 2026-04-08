import anthropic
from config import CLAUDE_API_KEY, CLAUDE_MODEL
from company_manager import get_company_info_prompt

# 회사 정보는 이제 company_manager에서 동적으로 가져옵니다
COMPANY_INFO = ""  # 하위 호환용, 실제로는 company_id 기반으로 동작

# ── 에이전트 균형 규칙 (모든 프롬프트에 공통) ──
AGENT_BALANCE_RULE = """
[에이전트 협업 핵심 규칙]
- 선택된 에이전트들은 처음부터 "함께" 글을 씁니다. 검토/수정이 아닌 공동 집필입니다.
- 최우선 원칙: 독자가 읽었을 때 "사람이 정성껏 쓴 글"이라고 느껴야 합니다.
- 스토리텔링·공감 관점을 글의 뼈대로 삼고, 나머지 에이전트의 전문성을 그 위에 입히세요.
- 데이터·SEO·전환 요소는 중요하지만, 이야기의 흐름을 끊지 않는 선에서 자연스럽게 녹이세요.
- 각 에이전트의 핵심 저서/콘텐츠의 개념을 실제로 적용하면서 글을 쓰세요.
- 에이전트 이름이나 저서를 직접 언급하지 마세요. 개념과 기법만 자연스럽게 융합하세요.
- 결과물은 하나의 매끄러운 글이어야 합니다. 에이전트별로 나뉘면 안 됩니다.
"""

# ── 이미지 공통 규칙 ──
IMAGE_COMMON_RULE = """
[🚨 Google Imagen 3 — 반드시 숙지 후 프롬프트 작성]

━━ A. Google 정책상 절대 금지 (이걸 넣으면 이미지 생성 자체가 실패함) ━━
1. 실존 인물 (유명인, 정치인, 연예인 등 이름이나 외모 특정)
2. 아동/미성년자 등장
3. 폭력, 고어, 무기 사용 장면
4. 성적/선정적 콘텐츠
5. 혐오/차별적 표현
6. 특정 인종+성별 조합 명시 (예: "Korean man", "Korean woman" → 대신 "person", "figure" 사용)
7. 얼굴 클로즈업, portrait, headshot (→ 대신 "seen from behind", "silhouette" 사용)
8. 특정 브랜드 로고 재현

━━ B. 하우스맨 추가 금지 (우리 블로그 품질 규칙) ━━
1. ❌ 외국 풍경/건물 절대 금지 → 반드시 한국(서울) 배경으로 묘사
2. ❌ 외국인 등장 금지 → 사람 필요 시 "person in Korean office setting, seen from behind" 형태
3. ❌ 큰 글씨/텍스트/간판 노출 금지 → 프롬프트에 "no signage, no readable text, no letters, no logos" 반드시 포함
4. ✅ 멀리서 흐릿하게 보이는 배경 텍스트는 허용 → "blurred distant background signs" OK
5. ✅ 사람은 뒷모습·실루엣·먼 거리로만 등장 가능 → "seen from behind, silhouette, distant figure"

━━ C. 프롬프트 작성법 (반드시 준수) ━━
- 영어로 작성 (Imagen은 영어 프롬프트가 가장 정확)
- "Korean" 단어는 장소/건물에만 사용, 사람에게 사용 금지
- 사람 묘사: "a person seen from behind", "distant silhouette of a worker" 등
- 금지어 미포함 확인 후 프롬프트 확정

━━ D. 프롬프트 구체성 필수 체크리스트 (모든 프롬프트에 반드시 포함) ━━
프롬프트가 추상적이면 Imagen이 엉뚱한 이미지를 만듭니다. 아래 5가지를 반드시 포함하세요:
1. 장소/배경: 구체적으로 (예: "Seoul commercial building lobby", "Korean apartment hallway")
2. 카메라 앵글/구도: (예: "wide angle shot", "eye-level view", "overhead view", "close-up detail")
3. 조명/시간대: (예: "soft natural daylight", "warm indoor lighting", "morning light through window")
4. 핵심 피사체: 가장 중요한 오브젝트 1~2개를 구체적으로 (예: "clipboard with inspection checklist on wooden desk")
5. 분위기/톤: (예: "clean and professional", "warm and inviting", "realistic documentary style")

[나쁜 예] "A building management scene" → 너무 추상적, Imagen이 아무거나 만듦
[좋은 예] "Wide angle photo of a Seoul commercial building lobby, soft natural daylight from glass entrance, a person in work uniform seen from behind inspecting fire extinguisher on wall, clean professional atmosphere, no text no signage no logos"

━━ E. 프롬프트 마무리 규칙 ━━
- 모든 프롬프트 끝에 반드시 추가: "no text, no signage, no readable signs, no logos, no letters"
- 한국 배경 프롬프트에는 반드시 "Seoul, South Korea" 포함
"""

# ── 네이버 이미지 스타일 10가지 ──
NAVER_IMAGE_STYLES = """
[네이버 블로그용 이미지 스타일 — 현장감/신뢰/체류시간]
1. 현실 현장 사진: realistic photo, Korean building exterior, natural lighting, Seoul
2. 스마트폰 촬영 느낌: smartphone photo, slightly grainy, natural colors, Korean building interior
3. Before/After 비교형: before and after comparison, same angle, clear contrast, renovation
4. 문제 상황 강조형: problem scene, wall damage, mold, water leak, realistic texture, close-up
5. 작업 중 현장 스냅샷: repair tools on floor, paint buckets, work in progress, person seen from behind
6. 점검 도구/서류 장면: clipboard on desk, inspection documents, tools arranged, Korean office
7. 한국 건물 전경: Korean commercial building, Seoul urban street, realistic photo
8. 생활 공간 장면: hallway, staircase, parking lot, Korean building interior
9. 디테일 클로즈업: close-up detail, wall crack, pipe texture, high detail macro
10. 건물 관리 도구/장비: maintenance tools, equipment, cleaning supplies, Korean setting
"""

# ── 워드프레스 이미지 스타일 10가지 ──
WP_IMAGE_STYLES = """
[워드프레스용 이미지 스타일 — 정보/구조/전문성]
1. 미니멀 인포그래픽: minimal infographic, clean layout, simple design, white background
2. 구조 다이어그램: flow diagram, structured layout, arrows, minimal style
3. 데이터 그래프: bar chart, line graph, clean data visualization, minimal
4. 비교 표 스타일: comparison table, clean grid, minimal UI design
5. 체크리스트 시각화: checklist visual, simple icons, minimal layout
6. 아이콘 설명형: minimal icons, flat design, clean composition
7. 사례 카드 스타일: case study card, clean UI, minimal box layout
8. 단계별 프로세스: step by step diagram, numbered steps, clean arrows
9. 시스템 구조도: system diagram, building structure, technical illustration
10. 통계 시각화: data visualization, charts, clean analytics style
"""


def _client():
    key = CLAUDE_API_KEY
    if not key or len(key) < 10:
        print(f"[generator] WARNING: API key is empty or too short: '{key[:5] if key else 'NONE'}...'")
    else:
        print(f"[generator] Using API key: {key[:15]}...{key[-4:]}")
    return anthropic.Anthropic(api_key=key)


import time as _time

def _call_claude(prompt: str, max_tokens: int = 4000, retries: int = 3) -> str:
    """Claude API 호출 + 529 Overloaded 자동 재시도"""
    for attempt in range(retries):
        try:
            msg = _client().messages.create(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except Exception as e:
            if "529" in str(e) or "overloaded" in str(e).lower():
                wait = 10 * (attempt + 1)
                print(f"[Claude] 서버 과부하, {wait}초 후 재시도 ({attempt+1}/{retries})...")
                _time.sleep(wait)
            else:
                raise
    raise Exception("Claude API 서버가 계속 과부하 상태입니다. 잠시 후 다시 시도해주세요.")


# ══════════════════════════════════════════════════════════════════
#  네이버 블로그 생성 (에이전트와 함께 작성)
# ══════════════════════════════════════════════════════════════════
def generate_naver_blog(topic_title: str, agent_prompts: str = "", company_id: str = "houseman") -> str:
    COMPANY_INFO = get_company_info_prompt(company_id)
    agent_section = ""
    if agent_prompts.strip():
        agent_section = f"""
{AGENT_BALANCE_RULE}

[참여 에이전트들의 관점 — 이들의 전문성을 균형 있게 융합하여 함께 글을 쓰세요]
{agent_prompts}
"""

    prompt = f"""당신은 하우스맨(houseman.co.kr)의 블로그를 쓰는 경험 많은 에디터입니다. 건물 관리 현장을 직접 다녀본 경험을 바탕으로, 건물주가 "아, 이 사람 진짜 아는 사람이네"라고 느끼게 쓰세요.
{COMPANY_INFO}
{agent_section}

아래 주제로 네이버 블로그 글을 작성해주세요.

주제: {topic_title}

[네이버 블로그 최적화 전문가 역할 — 항상 적용]
목표: 체류시간 증가 / 끝까지 읽게 만들기 / 공감·저장 유도 / 자연스러운 문의 발생

[작성 규칙]
- 분량: 1,800~2,400자 (자연스러운 흐름 우선, 억지로 늘리거나 줄이지 않기)
- 톤: 옆집 형/누나가 커피 한잔 하며 얘기해주는 느낌. 전문성은 유지하되 딱딱하지 않게.
- 독자: 서울 건물주 (임대수익 관리에 관심 있는 40~60대)
- 도입은 구체적 장면이나 상황 묘사로 시작 (예: "지난주 강남 7층 빌딩 옥상에서 물이 새고 있었습니다")
- 중간에 실제 사례나 에피소드 하나는 반드시 포함 (현장감 있게)
- 문단 길이는 리듬감 있게 변화를 주기 (짧은 한 줄 → 3줄 설명 → 짧은 한 줄)
- 소제목: 자연스럽게 사용, 궁금증을 유발하는 형태
- 키워드: 자연스럽게 녹이기 (횟수보다 맥락이 중요)
- ⚠️ 줄바꿈 (가장 중요한 규칙):
  → 한 문장은 최대 40자 이내. 40자가 넘으면 반드시 끊어 줄바꿈하세요.
  → 한 문단은 2~3줄 이내. 그 이상 길어지면 빈 줄로 문단을 나누세요.
  → 네이버 블로그는 모바일에서 읽힙니다. 긴 문장은 읽기 힘듭니다.
  → 좋은 예: "관리비는 크게 두 가지 방식이 있어요.\n하나는 고정 관리비.\n다른 하나는 실비 정산 방식입니다."
  → 나쁜 예: "서울 상업용 건물, 특히 강남이나 성수처럼 임대 수요가 높은 지역일수록 건물 관리 이력이 있는 곳과 없는 곳의 임차인 신뢰도 차이는 생각보다 큽니다."
  → 쉼표(,)가 2개 이상 들어가는 문장은 무조건 끊으세요.

[글의 온도]
- 정보만 나열하지 말고, "왜 이게 중요한지" 독자의 상황에 빗대어 설명
- 가끔 질문을 던지세요 ("혹시 이런 경험 있으신가요?")
- 완벽한 해답보다 솔직한 조언 느낌으로 ("솔직히 말씀드리면...")
- 글 끝은 독자에게 힘을 주는 한 마디로 마무리

[금지]
- 광고 느낌 문장
- 색깔 글씨
- 이모지 남발
- 긴 문단

[CTA]
- 강요하지 말 것
- "필요하시면 참고만 하셔도 됩니다" 형태

[중요] 본문에 이미지 자리를 표시하지 마세요. 글 본문만 작성하세요.
이미지는 글 완성 후 별도로 배치합니다.

Markdown 형식 (## 소제목, **굵게**, - 목록 사용)"""

    return _call_claude(prompt, max_tokens=4000)


# ══════════════════════════════════════════════════════════════════
#  워드프레스 생성 (에이전트와 함께 작성)
# ══════════════════════════════════════════════════════════════════
def generate_wordpress_blog(base_content: str, topic_title: str, agent_prompts: str = "", company_id: str = "houseman") -> str:
    COMPANY_INFO = get_company_info_prompt(company_id)
    agent_section = ""
    if agent_prompts.strip():
        agent_section = f"""
{AGENT_BALANCE_RULE}

[참여 에이전트들의 관점 — 이들의 전문성을 균형 있게 융합하여 함께 글을 쓰세요]
{agent_prompts}
"""

    prompt = f"""당신은 구글 SEO를 잘 아는 건물관리 전문 에디터입니다. 검색 최적화 구조를 따르되, 읽는 사람이 "이건 AI가 쓴 글이 아니라 진짜 사람이 쓴 글"이라고 느끼게 하세요.
{COMPANY_INFO}
{agent_section}

아래 내용을 참고하여 워드프레스 SEO 최적화 글을 작성해주세요.

주제: {topic_title}

--- 참고 내용 ---
{base_content}
---

[워드프레스 SEO 전문가 역할 — 항상 적용]
목표: 검색 상위 노출 / 검색 의도 완벽 충족 / 전문성(E-E-A-T) 확보 / 유입→문의 전환
핵심 철학: "검색되면서도 읽히는 글 — SEO 구조 안에서 사람의 목소리를 유지"

[작성 규칙]
- 분량: 2,200~2,800자 (자연스러운 흐름 우선)
- 결론을 먼저 제시
- 문제 정의 후 상세 설명
- 실제 사례 포함 (구체적 장면·에피소드로)
- 비교 및 선택 기준 제공
- 전문적이되 딱딱하지 않은 어조
- 광고 느낌 최소화
- ⚠️ 줄바꿈 (가장 중요한 규칙):
  → 한 문장은 최대 40자 이내. 40자가 넘으면 반드시 끊어 줄바꿈하세요.
  → 한 문단은 2~3줄 이내. 그 이상 길어지면 빈 줄로 문단을 나누세요.
  → 네이버 블로그는 모바일에서 읽힙니다. 긴 문장은 읽기 힘듭니다.
  → 좋은 예: "관리비는 크게 두 가지 방식이 있어요.\n하나는 고정 관리비.\n다른 하나는 실비 정산 방식입니다."
  → 나쁜 예: "서울 상업용 건물, 특히 강남이나 성수처럼 임대 수요가 높은 지역일수록 건물 관리 이력이 있는 곳과 없는 곳의 임차인 신뢰도 차이는 생각보다 큽니다."
  → 쉼표(,)가 2개 이상 들어가는 문장은 무조건 끊으세요.

[글의 온도]
- 정보만 나열하지 말고, "왜 이게 중요한지" 독자의 상황에 빗대어 설명
- 가끔 질문을 던지세요 ("혹시 이런 경험 있으신가요?")
- 완벽한 해답보다 솔직한 조언 느낌으로 ("솔직히 말씀드리면...")
- 문단 길이에 리듬감 주기 (짧은 한 줄 → 3줄 설명 → 짧은 한 줄)

[글 구조]
제목 → 요약(결론 먼저) → 본문(H2/H3) → 사례 → 해결 → 결과 → 결론 → CTA → FAQ

[제목]
- 핵심 키워드 1개 이상 + '서울'·'건물관리'·'위탁' 중 1개 이상
- 40자 이내

[SEO 규칙]
- 제목에 키워드 포함
- H2/H3 구조 필수
- 내부 링크 2개 이상
- 키워드 5~8회 자연 삽입
- FAQ 반드시 포함

[AI 검색 최적화]
- 핵심 개념을 명확하게 정의하는 문장을 본문 초반에 자연스럽게 포함
- 구체적 수치가 있으면 문장 안에 녹이기 (별도 나열이 아닌 맥락 속 언급)
- 비교 구문은 독자가 실제 판단할 때 도움되는 형태로 작성

[CTA]
- 정보 제공 후 자연스럽게 유도
- 직접적인 문의 유도 가능
- 3단계: 공감 마무리 → 신뢰 한 줄 → 행동 유도 (카카오톡 상담)

[글 맨 하단]
> 메타 디스크립션 (150자): [핵심 키워드] + [하우스맨 차별점] + [행동 유도]

[중요] 본문에 이미지 자리를 표시하지 마세요. 글 본문만 작성하세요.
이미지는 글 완성 후 별도로 배치합니다.

Markdown 형식 (H1=#, H2=##, H3=###)"""

    return _call_claude(prompt, max_tokens=6000)


# ══════════════════════════════════════════════════════════════════
#  이미지 3인 협업:
#  1단계 콘텐츠 회의: 현장콘텐츠 자문위원 + 크리에이티브 자문위원 (뭘 찍을지)
#  2단계 비주얼 실행: 아트디렉션 자문위원 (어떻게 찍을지 + 프롬프트)
# ══════════════════════════════════════════════════════════════════

def _step1_naver_content_meeting(blog_content: str) -> str:
    """1단계 (네이버): 현장콘텐츠 자문위원 + 크리에이티브 자문위원이 소제목별 이미지 방향 결정"""

    prompt = f"""지금부터 두 명의 전문가가 블로그 이미지 콘텐츠 회의를 합니다.

👤 현장콘텐츠 자문위원
- 부동산 플랫폼에서 수년간 건물/부동산 콘텐츠를 제작해온 현장 콘텐츠 전문가
- 한국 건물주가 어떤 사진에 반응하는지, 어떤 현장 사진이 신뢰감을 주는지 정확히 앎
- 한국 상업용 건물, 관리실, 복도, 주차장, 옥상 등 실제 현장의 시각적 특징을 꿰뚫고 있음

👤 크리에이티브 자문위원
- 광고·마케팅 크리에이티브를 총괄하는 전문가
- 한국 소비자 심리를 꿰뚫는 감각, "이 사진 한 장이면 클릭한다" 판단력
- 건물 사진뿐 아니라 감성/마케팅적 사진 선택 능력 (스트레스 장면, 여유 장면, 자동화 느낌 등)
- 40~60대 한국인이 감정적으로 반응하는 이미지를 정확히 앎

플랫폼: 네이버 블로그 (40~60대 서울 건물주 대상, 체류시간·공감·신뢰 중요)

{IMAGE_COMMON_RULE}

--- 블로그 글 ---
{blog_content}
---

[회의 진행]
두 사람이 글의 소제목(##)을 하나씩 보면서 치열하게 토론합니다:
- 현장콘텐츠 자문위원: 이 소제목에 어떤 현장 사진이 적합한지 제안
- 크리에이티브 자문위원: 마케팅/감성 관점에서 동의 또는 더 나은 대안 제시
- 두 사람은 때로 의견이 충돌합니다. 한쪽이 이기기도 하고, 양보하기도 합니다.
- 두 사람이 합의하여 각 소제목의 최종 이미지 방향 결정
- 이미지 수 제한 없음 — 필요한 만큼 자유롭게
- 모든 소제목에 이미지가 필요한 건 아님. 효과적인 곳에만 배치

[출력 형식 — 반드시 이 형식으로]

📋 콘텐츠 회의 결과

각 이미지:
---
📷 이미지 N
소제목: (해당 소제목 원문 그대로 인용)
현장콘텐츠 자문위원 의견: (이 소제목에 왜 이 장면인지, 현장 관점 1~2줄)
크리에이티브 자문위원 의견: (마케팅/감성 관점에서 동의, 반박, 대안 중 하나 — 이유와 함께 1~2줄)
승패: (누구의 의견이 더 반영되었는지 — "현장콘텐츠 자문위원 WIN" / "크리에이티브 자문위원 WIN" / "절충안" 중 택1 + 한 줄 이유)
최종 합의: (어떤 장면으로 갈지 구체적으로 — 장소, 상황, 분위기, 시각적 포인트)
이미지 유형: (현장사진 / 감성사진 / 개념사진 중 택1)
---

이 형식으로 이미지가 필요한 모든 소제목에 대해 출력하세요."""

    return _call_claude(prompt, max_tokens=4000)


def _step1_wp_info_meeting(blog_content: str) -> str:
    """1단계 (워드프레스): 정보시각화 자문위원 + 미디어디자인 자문위원이 소제목별 정보 시각화 방향 결정"""

    prompt = f"""지금부터 두 명의 전문가가 워드프레스 블로그 이미지 콘텐츠 회의를 합니다.

👤 정보시각화 자문위원
- 데이터 시각화, 인포그래픽, 다이어그램 설계의 권위자
- "좋은 정보 디자인은 데이터를 말하게 한다" — 불필요한 장식 제거, 정보 밀도 극대화
- 비교 표, 프로세스 다이어그램, 데이터 차트 등 정보 전달형 비주얼 설계

👤 미디어디자인 자문위원
- 한국 미디어/디자인 산업에 정통한 전문가
- 한국 시장에서 정보가 어떤 비주얼로 전달되어야 설득력이 있는지 정확히 앎
- 글로벌 디자인 트렌드와 한국 비즈니스 맥락의 교차점을 파악
- "정보는 아름다워야 읽힌다" — 한국 독자가 신뢰하는 정보 디자인 감각

플랫폼: 워드프레스 (구글 SEO, 전문성·E-E-A-T·정보성 중요, HTML 레이아웃 자유)

{IMAGE_COMMON_RULE}

--- 블로그 글 ---
{blog_content}
---

[회의 진행]
두 사람이 글의 소제목(##)을 하나씩 보면서 치열하게 토론합니다:
- 정보시각화 자문위원: 이 소제목의 핵심 정보를 어떤 형태로 시각화하면 효과적인지 제안
- 미디어디자인 자문위원: 한국 비즈니스 맥락에서 어떤 비주얼이 신뢰감과 전문성을 주는지 의견 추가
- 두 사람은 때로 의견이 충돌합니다. 학술적 관점과 실무적 관점이 부딪힐 수 있습니다.
- 두 사람이 합의하여 각 소제목의 최종 이미지 방향 결정
- 이미지 수 제한 없음 — 필요한 만큼 자유롭게
- 워드프레스는 레이아웃이 자유로우므로 사이즈/배치도 고려

[출력 형식 — 반드시 이 형식으로]

📋 정보 시각화 회의 결과

각 이미지:
---
📷 이미지 N
소제목: (해당 소제목 원문 그대로 인용)
정보시각화 자문위원 의견: (이 정보를 어떤 형태로 시각화하면 효과적인지, 정보 디자인 관점 1~2줄)
미디어디자인 자문위원 의견: (한국 비즈니스/미디어 관점에서 동의, 반박, 대안 중 하나 — 이유와 함께 1~2줄)
승패: (누구의 의견이 더 반영되었는지 — "정보시각화 자문위원 WIN" / "미디어디자인 자문위원 WIN" / "절충안" 중 택1 + 한 줄 이유)
최종 합의: (어떤 시각물로 갈지 구체적으로 — 형태, 구조, 핵심 데이터, 비주얼 포인트)
이미지 유형: (인포그래픽 / 다이어그램 / 데이터차트 / 비교표 / 프로세스도식 / 개념도 중 택1)
---

이 형식으로 이미지가 필요한 모든 소제목에 대해 출력하세요."""

    return _call_claude(prompt, max_tokens=4000)


def _step2_art_direction_naver(blog_content: str, content_plan: str) -> str:
    """2단계 (네이버): 아트디렉션 자문위원 — 현장/감성 이미지를 미니멀하게 프롬프트 작성"""

    prompt = f"""당신은 아트디렉션 자문위원입니다. 미니멀하고 통일된 비주얼 톤을 설계하는 전문가.

현장콘텐츠 자문위원과 크리에이티브 자문위원이 콘텐츠 회의를 끝냈습니다.
각 소제목에 어떤 장면이 필요한지 합의했습니다. 당신은 이걸 받아서:
1. 전체 비주얼 톤을 통일합니다
2. 각 이미지의 스타일을 선택합니다
3. Gemini 이미지 생성용 영문 프롬프트를 작성합니다
4. 불필요한 요소를 제거하고 미니멀하게 정리합니다

--- 콘텐츠 회의 결과 ---
{content_plan}
---

{IMAGE_COMMON_RULE}

{NAVER_IMAGE_STYLES}

레이아웃: 네이버: 모든 이미지 동일 크기, 소제목 바로 아래 순서대로 배치

[출력 형식 — 반드시 이 형식으로]

🎨 아트디렉션 자문위원의 아트 디렉션
- 톤 기준: (전체 이미지 톤 1~2줄)
- 총 이미지 수: (확정)

각 이미지:
---
📷 이미지 1
소제목: (원문 그대로)
스타일: (번호와 이름)
레이아웃: (full / large / medium / side-left / side-right / pair)
이미지 설명: (콘텐츠팀 합의 기반 + 아트디렉션 자문위원이 다듬은 최종 장면)
Gemini 프롬프트: (영문 프롬프트 — 아래 필수사항 모두 포함)
  → 필수 포함: 장소/배경 + 카메라 앵글 + 조명 + 핵심 피사체 + 분위기
  → 필수 포함: "Seoul, South Korea" (한국 배경일 때)
  → 필수 끝맺음: "no text, no signage, no readable signs, no logos, no letters"
---

⚠️ 중요: 프롬프트가 1줄짜리 추상적 문장이면 안 됩니다. 반드시 3줄 이상의 구체적 묘사로 작성하세요.
이 형식으로 모든 이미지를 출력하세요."""

    return _call_claude(prompt, max_tokens=4000)


def _step2_art_direction_wordpress(blog_content: str, info_plan: str) -> str:
    """2단계 (워드프레스): 아트디렉션 자문위원 — 정보 시각화를 미니멀하게 프롬프트 작성 + 레이아웃 선택"""

    prompt = f"""당신은 아트디렉션 자문위원입니다. 미니멀하고 통일된 비주얼 톤을 설계하는 전문가.

정보시각화 자문위원과 미디어디자인 자문위원이 정보 시각화 회의를 끝냈습니다.
각 소제목에 어떤 형태의 정보 시각물이 필요한지 합의했습니다. 당신은 이걸 받아서:
1. 전체 비주얼 톤을 통일합니다 — 깨끗하고 미니멀한 정보 디자인
2. 각 이미지의 스타일을 선택합니다
3. Gemini 이미지 생성용 영문 프롬프트를 작성합니다
4. 워드프레스 HTML 레이아웃에 맞는 사이즈/배치를 결정합니다
5. 불필요한 장식을 제거하고 정보 밀도를 높입니다

--- 정보 시각화 회의 결과 ---
{info_plan}
---

{IMAGE_COMMON_RULE}

{WP_IMAGE_STYLES}

레이아웃: 워드프레스: 각 이미지마다 레이아웃 선택
- full: 본문 폭 100% (임팩트 있는 메인 인포그래픽)
- large: 본문 폭 80% 중앙 (일반 다이어그램)
- medium: 본문 폭 60% 중앙 (보조 차트)
- side-left: 좌측 40% + 텍스트 감싸기
- side-right: 우측 40% + 텍스트 감싸기
- pair: 2장 나란히 50%씩 (비교/대조용)

[출력 형식 — 반드시 이 형식으로]

🎨 아트디렉션 자문위원의 아트 디렉션
- 톤 기준: (전체 이미지 톤 1~2줄 — 정보 디자인 중심)
- 총 이미지 수: (확정)

각 이미지:
---
📷 이미지 1
소제목: (원문 그대로)
스타일: (번호와 이름)
레이아웃: (full / large / medium / side-left / side-right / pair)
이미지 설명: (정보팀 합의 기반 + 아트디렉션 자문위원이 다듬은 최종 시각물)
Gemini 프롬프트: (영문 프롬프트 — 아래 필수사항 모두 포함)
  → 필수 포함: 장소/배경 + 카메라 앵글 + 조명 + 핵심 피사체 + 분위기
  → 필수 포함: "Seoul, South Korea" (한국 배경일 때)
  → 필수 끝맺음: "no text, no signage, no readable signs, no logos, no letters"
---

⚠️ 중요: 프롬프트가 1줄짜리 추상적 문장이면 안 됩니다. 반드시 3줄 이상의 구체적 묘사로 작성하세요.
이 형식으로 모든 이미지를 출력하세요."""

    return _call_claude(prompt, max_tokens=4000)


def _parse_debate_summary(step1_result: str, platform: str = "naver") -> dict:
    """1단계 결과에서 토론 하이라이트 + 승패를 추출"""
    import re
    blocks = re.split(r"(?=📷\s*이미지)", step1_result)
    image_blocks = [b for b in blocks if b.strip() and "📷" in b]
    total_images = len(image_blocks)

    # 의견 추출
    opinions_a = re.findall(r"(?:현장콘텐츠 자문위원|정보시각화 자문위원)\s*의견\s*[:：]\s*(.+?)(?:\n|$)", step1_result)
    opinions_b = re.findall(r"(?:크리에이티브 자문위원|미디어디자인 자문위원)\s*의견\s*[:：]\s*(.+?)(?:\n|$)", step1_result)
    agreements = re.findall(r"최종 합의\s*[:：]\s*(.+?)(?:\n|$)", step1_result)

    # 승패 추출
    verdicts = re.findall(r"승패\s*[:：]\s*(.+?)(?:\n|$)", step1_result)
    wins_a = 0
    wins_b = 0
    draws = 0
    for v in verdicts:
        vl = v.lower()
        if "현장콘텐츠 자문위원" in vl or "정보시각화 자문위원" in vl:
            if "win" in vl.lower():
                wins_a += 1
        elif "크리에이티브 자문위원" in vl or "미디어디자인 자문위원" in vl:
            if "win" in vl.lower():
                wins_b += 1
        elif "절충" in vl:
            draws += 1

    if platform == "naver":
        name_a, name_b = "현장콘텐츠 자문위원", "크리에이티브 자문위원"
    else:
        name_a, name_b = "정보시각화 자문위원", "미디어디자인 자문위원"

    return {
        "total": total_images,
        "opinions_a": opinions_a[:3],
        "opinions_b": opinions_b[:3],
        "agreements": agreements[:3],
        "verdicts": verdicts[:5],
        "wins_a": wins_a,
        "wins_b": wins_b,
        "draws": draws,
        "name_a": name_a,
        "name_b": name_b,
    }


def generate_image_plan(blog_content: str, platform: str, agent_prompts: str = "", company_id: str = "houseman", status_callback=None) -> str:
    """플랫폼별 이미지 협업 — 실시간 토론 스토리 콜백 포함"""

    cb = status_callback or (lambda x: None)

    if platform == "naver":
        # ── 네이버: 현장감 + 감성 마케팅 팀 ──

        # 팀원 입장
        cb("━━━ 🎬 STEP 1: 콘텐츠 회의실 ━━━")
        cb("")
        cb("🏢 **현장콘텐츠 자문위원** 입장")
        cb("  └ 부동산 현장 콘텐츠 10년+ · 한국 건물주 반응 데이터 전문가")
        cb("  └ _\"한국 건물주가 진짜 클릭하는 사진이 뭔지, 저보다 잘 아는 사람 없습니다\"_")
        cb("")
        cb("💡 **크리에이티브 자문위원** 입장")
        cb("  └ 광고·마케팅 크리에이티브 총괄 전문가")
        cb("  └ _\"좋은 사진은 설명이 필요 없어요. 한 장으로 마음을 잡아야 합니다\"_")
        cb("")
        cb("🔥 두 사람이 소제목을 하나씩 펼치며 토론을 시작합니다...")
        cb("")

        # API 호출 (실제 토론)
        content_plan = _step1_naver_content_meeting(blog_content)

        # 토론 결과 파싱 & 하이라이트
        debate = _parse_debate_summary(content_plan, "naver")
        cb(f"━━━ 📋 1단계 토론 결과: 이미지 **{debate['total']}장** 합의 ━━━")
        cb("")

        # 승패 스코어보드
        cb(f"🏆 **스코어보드**: 🏢 현장콘텐츠 자문위원 {debate['wins_a']}승 vs 💡 크리에이티브 자문위원 {debate['wins_b']}승 / 절충 {debate['draws']}건")
        cb("")

        # 토론 하이라이트 재현 — 승패 포함
        if debate["opinions_a"] and debate["opinions_b"]:
            cb("💬 **토론 하이라이트**")
            reactions = [
                ("_(자리에서 일어나며)_", "_(느긋하게 미소 지으며)_"),
                ("_(사진을 꺼내 보이며)_", "_(고개를 갸웃하며)_"),
                ("_(확신에 차서)_", "_(잠시 고민 후)_"),
            ]
            for i, (oa, ob) in enumerate(zip(debate["opinions_a"], debate["opinions_b"])):
                ra, rb = reactions[i] if i < len(reactions) else ("", "")
                cb(f"  🏢 현장콘텐츠 자문위원 {ra}: \"{oa[:60]}\"")
                cb(f"  💡 크리에이티브 자문위원 {rb}: \"{ob[:60]}\"")
                if i < len(debate["verdicts"]):
                    v = debate["verdicts"][i]
                    if "현장콘텐츠 자문위원" in v and "WIN" in v.upper():
                        cb(f"  🥊 → **현장콘텐츠 자문위원 WIN!** {v[v.find('—')+1:].strip() if '—' in v else ''}")
                    elif "크리에이티브 자문위원" in v and "WIN" in v.upper():
                        cb(f"  🥊 → **크리에이티브 자문위원 WIN!** {v[v.find('—')+1:].strip() if '—' in v else ''}")
                    else:
                        cb(f"  🤝 → **절충안** 채택 — 서로 양보하여 합의")
                if i < len(debate["agreements"]):
                    cb(f"  📌 합의: {debate['agreements'][i][:55]}...")
                cb("")

        # 아트디렉션 자문위원 등장
        cb("━━━ 🎬 STEP 2: 아트 디렉션 ━━━")
        cb("")
        cb("🎨 **아트디렉션 자문위원** 입장")
        cb("  └ 미니멀하고 통일된 비주얼 톤을 설계하는 전문가")
        cb("  └ _\"Simplicity is the ultimate sophistication.\"_")
        cb("")
        cb(f"📨 콘텐츠팀이 합의한 {debate['total']}장의 이미지 브리프를 전달받았습니다")
        cb("🎨 아트디렉션 자문위원: _\"불필요한 건 전부 덜어내겠습니다. 하나의 톤으로 통일합니다.\"_")
        cb("⏳ 비주얼 톤 통일 + 프롬프트 작성 중...")
        cb("")

        final_plan = _step2_art_direction_naver(blog_content, content_plan)

        cb("✅ 아트디렉션 자문위원의 아트 디렉션 완료!")

    else:
        # ── 워드프레스: 정보 시각화 + 한국 미디어 디자인 팀 ──

        cb("━━━ 🎬 STEP 1: 정보 시각화 회의실 ━━━")
        cb("")
        cb("📊 **정보시각화 자문위원** 입장")
        cb("  └ 데이터 시각화·인포그래픽·다이어그램 설계 전문가")
        cb("  └ _\"모든 데이터에는 이야기가 있습니다. 장식이 아니라 정보를 보여주세요.\"_")
        cb("")
        cb("📐 **미디어디자인 자문위원** 입장")
        cb("  └ 한국 미디어/디자인 산업 전문가")
        cb("  └ _\"한국 시장에서 정보는 신뢰의 옷을 입어야 합니다\"_")
        cb("")
        cb("🔍 두 사람이 소제목의 핵심 데이터를 분석하며 시각화 방향을 논의합니다...")
        cb("")

        info_plan = _step1_wp_info_meeting(blog_content)

        debate = _parse_debate_summary(info_plan, "wordpress")
        cb(f"━━━ 📋 1단계 토론 결과: 시각물 **{debate['total']}개** 합의 ━━━")
        cb("")

        # 승패 스코어보드
        cb(f"🏆 **스코어보드**: 📊 정보시각화 자문위원 {debate['wins_a']}승 vs 📐 미디어디자인 자문위원 {debate['wins_b']}승 / 절충 {debate['draws']}건")
        cb("")

        if debate["opinions_a"] and debate["opinions_b"]:
            cb("💬 **토론 하이라이트**")
            reactions = [
                ("_(칠판에 다이어그램을 그리며)_", "_(태블릿을 보여주며)_"),
                ("_(데이터를 짚으며)_", "_(한국 사례를 꺼내며)_"),
                ("_(단호하게)_", "_(웃으며 양보하며)_"),
            ]
            for i, (oa, ob) in enumerate(zip(debate["opinions_a"], debate["opinions_b"])):
                ra, rb = reactions[i] if i < len(reactions) else ("", "")
                cb(f"  📊 정보시각화 자문위원 {ra}: \"{oa[:60]}\"")
                cb(f"  📐 미디어디자인 자문위원 {rb}: \"{ob[:60]}\"")
                if i < len(debate["verdicts"]):
                    v = debate["verdicts"][i]
                    if "정보시각화 자문위원" in v and "WIN" in v.upper():
                        cb(f"  🥊 → **정보시각화 자문위원 WIN!** {v[v.find('—')+1:].strip() if '—' in v else ''}")
                    elif "미디어디자인 자문위원" in v and "WIN" in v.upper():
                        cb(f"  🥊 → **미디어디자인 자문위원 WIN!** {v[v.find('—')+1:].strip() if '—' in v else ''}")
                    else:
                        cb(f"  🤝 → **절충안** 채택 — 학술과 실무의 균형")
                if i < len(debate["agreements"]):
                    cb(f"  📌 합의: {debate['agreements'][i][:55]}...")
                cb("")

        cb("━━━ 🎬 STEP 2: 미니멀 실행 ━━━")
        cb("")
        cb("🎨 **아트디렉션 자문위원** 입장")
        cb("  └ 미니멀하고 통일된 비주얼 톤을 설계하는 전문가")
        cb("  └ _\"Less, but better. 정보 디자인도 미니멀하게.\"_")
        cb("")
        cb(f"📨 정보팀이 설계한 {debate['total']}개의 시각물 브리프를 전달받았습니다")
        cb("🎨 아트디렉션 자문위원: _\"데이터를 아름답게 만들겠습니다. 미니멀하게.\"_")
        cb("⏳ 비주얼 톤 통일 + 레이아웃 선택 + 프롬프트 작성 중...")
        cb("")

        final_plan = _step2_art_direction_wordpress(blog_content, info_plan)

        cb("✅ 아트디렉션 자문위원의 아트 디렉션 완료!")

    return final_plan


# ══════════════════════════════════════════════════════════════════
#  코멘트 반영 수정
# ══════════════════════════════════════════════════════════════════
def revise_with_comment(blog_content: str, comment: str, platform: str = "naver") -> str:
    if platform == "naver":
        length_rule = "2,000~2,200자"
    else:
        length_rule = "2,500자 내외"

    prompt = f"""아래 블로그를 사용자 요청에 맞게 수정해주세요.

--- 현재 블로그 ---
{blog_content}
---

수정 요청: {comment}

[요구사항]
- 요청 내용을 충분히 반영하여 수정
- 기존 톤앤매너와 분량({length_rule}) 유지
- Markdown 형식 유지
- 이미지 자리를 표시하지 마세요"""

    return _call_claude(prompt, max_tokens=6000)
