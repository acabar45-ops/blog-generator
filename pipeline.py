# ================================================================
#  7-에이전트 파이프라인 실행 엔진 (통합 리팩토링)
#  - Phase 0~6, 병렬/순차 실행
#  - QA 루프 (Phase 5 → Phase 6 → 재검사)
#  - 플랫폼별(네이버/워드프레스) 규칙 자동 주입
# ================================================================

import time
import re
import concurrent.futures
import anthropic
from config import (
    CLAUDE_API_KEY, CLAUDE_MODEL,
    PIPELINE_QA_THRESHOLD, PIPELINE_MAX_REVISION_ROUNDS,
)
from agents import PIPELINE_AGENTS, PIPELINE_PHASES, get_pipeline_agent
from company_manager import get_company_info_prompt
from generator import FORMAT_RULE, IMAGE_COMMON_RULE


# ================================================================
#  플랫폼별 에이전트 규칙
# ================================================================

PLATFORM_RULES = {
    "naver": {
        "strategist": (
            "[네이버 블로그 전략 규칙]\n"
            "- 분량: 1,800~2,400자 (자연스러운 흐름 우선)\n"
            "- 구조: 자유로운 흐름, H2 소제목 3~5개. H3 불필요\n"
            "- 검색 최적화: 체류시간 증가, 공감·저장 유도가 핵심\n"
            "- 키워드: 자연 삽입 2~4회 (맥락이 횟수보다 중요)\n"
            "- 도입: 구체적 장면, 질문, 에피소드로 시작 (결론 먼저 X)\n"
            "- FAQ 섹션: 불필요\n"
            "- 독자: 네이버에서 검색하는 40~60대 건물주"
        ),
        "writer": (
            "[네이버 블로그 작성 규칙]\n"
            "- 분량: 1,800~2,400자\n"
            "- 톤: 옆집 형/누나가 커피 한잔 하며 얘기해주는 느낌. 편한 대화체\n"
            "- 도입: 구체적 장면 묘사, 질문, 에피소드로 시작\n"
            "- 구조: H2(##) 소제목 + 자유 본문. H3 사용하지 마세요\n"
            "- FAQ: 포함하지 마세요\n"
            "- 사례: \"~한 건물이 있었는데\" 스토리형으로 풀기\n"
            "- 마무리: 독자에게 힘을 주는 한 마디로 끝\n"
            "- 금지: 결론 먼저 제시, 딱딱한 보고서 톤"
        ),
        "editor": (
            "[네이버 블로그 편집 규칙]\n"
            "- 문장 길이: 25~35자 목표\n"
            "- 어미: ~합니다/~입니다 70% + ~죠/~세요 30% (편한 느낌)\n"
            "- 인용구(>): 건물주 말투 활용 (\"전화만 안 왔으면 좋겠어요\")\n"
            "- 이모지: H2 소제목에 1개씩 허용\n"
            "- 전체 톤이 '사람 냄새 나는 글'이어야 함"
        ),
        "image_director": (
            "[네이버 블로그 이미지 규칙]\n"
            "- 스타일: 현장감·스마트폰 촬영 느낌·리얼리즘\n"
            "- 종류: 현장사진, Before/After, 작업 스냅샷, 점검 장면\n"
            "- 수량: 4~6장 (체류시간 확보가 중요)\n"
            "- 톤: 따뜻하고 친근한 색감, 자연광 위주\n"
            "- 네이버 이미지 스타일 참고:\n"
            "  1. 현실 현장 사진 (realistic, natural lighting)\n"
            "  2. 스마트폰 촬영 느낌 (slightly grainy, natural colors)\n"
            "  3. Before/After 비교형\n"
            "  4. 문제 상황 강조형 (wall damage, water leak, close-up)\n"
            "  5. 작업 중 현장 스냅샷\n"
            "  6. 점검 도구/서류 장면\n"
            "  7. 한국 건물 전경\n"
            "  8. 생활 공간 장면 (복도, 계단, 주차장)\n"
            "  9. 디테일 클로즈업\n"
            "  10. 건물 관리 도구/장비"
        ),
        "seo_converter": (
            "[네이버 블로그 SEO/전환 규칙]\n"
            "- SEO 목표: 체류시간 증가, 공감·저장 유도, 자연스러운 문의 발생\n"
            "- 키워드: 자연 삽입 2~4회, 맥락이 횟수보다 중요\n"
            "- 메타데이터: 태그 5~8개만 (메타 디스크립션/OG/슬러그 불필요)\n"
            "- CTA: 소프트하게. \"필요하시면 참고만 하셔도 됩니다\" 형태\n"
            "  → 강요/긴급성 절대 금지\n"
            "  → 중간 CTA 1줄 (부드러운 제안)\n"
            "  → 마무리 CTA 1~2줄 (카카오톡 안내)\n"
            "- FAQ: 포함하지 마세요\n"
            "- 내부 링크: 불필요\n"
            "- AI 검색 인용 패턴: 불필요"
        ),
        "assembler": (
            "[네이버 블로그 조립 규칙]\n"
            "- 전체 톤: 편하고 친근하게, '사람이 쓴 글' 느낌\n"
            "- CTA는 글 흐름에 자연스럽게 녹이기\n"
            "- 푸터: 슬로건 + 회사 정보 (간결하게)"
        ),
    },

    "wordpress": {
        "strategist": (
            "[워드프레스 SEO 전략 규칙]\n"
            "- 분량: 2,200~2,800자\n"
            "- 구조: H1 제목 → H2 섹션(4~6개) → H3 세부 항목. 계층 필수\n"
            "- 검색 최적화: E-E-A-T (경험·전문성·권위·신뢰) 확보가 핵심\n"
            "- 키워드: 밀도 타겟 5~8회 + LSI(관련) 키워드 3~5개\n"
            "- 도입: 결론을 먼저 제시 → 상세 전개\n"
            "- FAQ 섹션: 필수 포함 (3~5개 Q&A)\n"
            "- 독자: 구글에서 검색하는 건물주·투자자·관리 담당자\n"
            "- AI 검색 인용: \"X는 Y입니다\" 형태의 명확한 정의 문장 포함"
        ),
        "writer": (
            "[워드프레스 SEO 작성 규칙]\n"
            "- 분량: 2,200~2,800자\n"
            "- 톤: 전문적이되 딱딱하지 않은. 신뢰감 있는 에디터 톤\n"
            "- 도입: 결론 먼저 → 문제 정의 → 상세 설명\n"
            "- 구조: H1(#) 제목 → H2(##) 섹션 → H3(###) 세부 항목\n"
            "- FAQ: 글 하단에 필수 포함 (## FAQ 또는 ## 자주 묻는 질문)\n"
            "  → 3~5개 Q&A, 구조화 데이터에 적합한 형태\n"
            "- 사례: 데이터 기반, 전후 비교 수치 포함\n"
            "- 내부 링크: 관련 주제 2개 이상 자연스럽게 언급\n"
            "- 마무리: 핵심 요약 + 행동 유도\n"
            "- 금지: 장면 묘사로 시작, 과도한 감성, FAQ 누락"
        ),
        "editor": (
            "[워드프레스 편집 규칙]\n"
            "- 문장 길이: 35~45자 허용 (네이버보다 길어도 OK)\n"
            "- 어미: ~합니다/~입니다 85% + ~죠 15% (전문적 톤 유지)\n"
            "- 인용구(>): 전문가 의견, 데이터 인용에 사용\n"
            "- 이모지: H2에만, 최소한으로 (없어도 OK)\n"
            "- H1/H2/H3 위계가 정확한지 확인\n"
            "- FAQ 섹션이 있는지 확인 — 없으면 추가 지시"
        ),
        "image_director": (
            "[워드프레스 이미지 규칙]\n"
            "- 스타일: 미니멀·전문적·정보 전달 중심\n"
            "- 종류: 인포그래픽, 비교 차트, 구조 다이어그램, 프로세스 플로우\n"
            "- 수량: 2~4장 (정보 밀도 중심, 장식적 이미지 최소화)\n"
            "- 톤: 깨끗하고 전문적인 색감, 화이트 배경 선호\n"
            "- 워드프레스 이미지 스타일 참고:\n"
            "  1. 미니멀 인포그래픽 (clean layout, white background)\n"
            "  2. 구조 다이어그램 (flow diagram, arrows)\n"
            "  3. 데이터 그래프 (bar chart, clean visualization)\n"
            "  4. 비교 표 스타일 (comparison grid)\n"
            "  5. 체크리스트 시각화 (simple icons)\n"
            "  6. 단계별 프로세스 (numbered steps)\n"
            "  7. 사례 카드 스타일 (case study card, clean UI)\n"
            "  8. 시스템 구조도 (technical illustration)"
        ),
        "seo_converter": (
            "[워드프레스 SEO/전환 규칙]\n"
            "- SEO 목표: 검색 상위 노출, E-E-A-T 확보, 유입→문의 전환\n"
            "- 키워드: 제목+H2+본문에 5~8회. 키워드 밀도 1.5~2.5% 타겟\n"
            "- 메타데이터: 전부 작성\n"
            "  → 페이지 타이틀: 40자 이내 (키워드 + 차별점)\n"
            "  → 메타 디스크립션: 150자 이내 (키워드 + CTA)\n"
            "  → OG 타이틀/디스크립션: 소셜 공유용\n"
            "  → 슬러그: 영문 URL 경로\n"
            "  → 태그: 5~8개\n"
            "- CTA: 3단계 구조\n"
            "  → 1단계: 공감 마무리 (\"관리의 시작은 현실을 아는 것입니다\")\n"
            "  → 2단계: 신뢰 한 줄 (\"100개+ 건물 관리 경험\")\n"
            "  → 3단계: 행동 유도 (카카오톡 상담 안내)\n"
            "- FAQ: 본문에 FAQ가 있는지 확인. 없으면 3~5개 추가\n"
            "- 내부 링크: 관련 글 2개 이상 링크 제안\n"
            "- AI 검색 인용: \"X는 Y입니다\" 형태의 정의 문장 2~3개 확인"
        ),
        "assembler": (
            "[워드프레스 조립 규칙]\n"
            "- H1/H2/H3 계층 구조 정확하게 유지\n"
            "- FAQ 섹션이 글 하단에 있는지 확인\n"
            "- 메타 디스크립션을 글 맨 하단에 별도 표기\n"
            "- CTA는 3단계 구조로 자연스럽게 삽입\n"
            "- 푸터: 슬로건 + 회사 정보"
        ),
    },
}


def _client():
    return anthropic.Anthropic(api_key=CLAUDE_API_KEY)


def _call_agent(agent_id: str, user_prompt: str, platform: str = "naver", retries: int = 3) -> str:
    """단일 에이전트 Claude API 호출 (FORMAT_RULE + 플랫폼 규칙 주입)"""
    agent = get_pipeline_agent(agent_id)
    if not agent:
        raise ValueError(f"Unknown agent: {agent_id}")

    system_prompt = agent["system_prompt"]

    # FORMAT_RULE 주입 (포맷 규칙이 필요한 에이전트만)
    if agent.get("inject_format_rule", False):
        system_prompt = f"{system_prompt}\n\n{FORMAT_RULE}"

    # 플랫폼별 규칙 주입
    platform_rules = PLATFORM_RULES.get(platform, {})
    agent_rule = platform_rules.get(agent_id, "")
    if agent_rule:
        system_prompt = f"{system_prompt}\n\n{agent_rule}"

    max_tokens = agent.get("max_tokens", 4000)

    for attempt in range(retries):
        try:
            msg = _client().messages.create(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return msg.content[0].text
        except Exception as e:
            if "529" in str(e) or "overloaded" in str(e).lower():
                wait = 10 * (attempt + 1)
                time.sleep(wait)
            else:
                raise
    raise Exception(f"Agent '{agent_id}' API 호출 실패 (서버 과부하)")


def _parse_qa_score(qa_result: str) -> int:
    """품질감사 결과에서 총점 추출"""
    match = re.search(r'총점[:\s]*(\d+)', qa_result)
    if match:
        return int(match.group(1))
    match = re.search(r'(\d+)\s*/\s*80', qa_result)
    if match:
        return int(match.group(1))
    return 0


def _build_context(topic_title: str, company_id: str, platform: str) -> str:
    """모든 에이전트에 전달할 기본 컨텍스트"""
    company_info = get_company_info_prompt(company_id)
    platform_label = "네이버 블로그" if platform == "naver" else "워드프레스 (구글 SEO)"
    return f"[주제] {topic_title}\n[플랫폼] {platform_label}\n[회사 정보]\n{company_info}"


def run_pipeline(
    topic_title: str,
    company_id: str = "houseman",
    platform: str = "naver",
    status_callback=None,
) -> dict:
    """
    7-에이전트 파이프라인 실행 (플랫폼별 규칙 자동 적용)
    """

    def notify(msg):
        if status_callback:
            status_callback(msg)

    platform_label = "네이버" if platform == "naver" else "워드프레스"
    base_context = _build_context(topic_title, company_id, platform)
    outputs = {}

    # ── PHASE 0: 전략 설계 ──
    notify(f"🎯 Phase 0: 전략 설계 ({platform_label})...")
    agent = get_pipeline_agent("strategist")
    notify(f"  {agent['icon']} **{agent['name']}** 실행 중...")
    outputs["strategist"] = _call_agent("strategist", base_context, platform)
    notify(f"  ✅ {agent['name']} 완료")

    # ── PHASE 1: 글쓰기 ──
    notify(f"✍️ Phase 1: 글쓰기 ({platform_label})...")
    writer_context = (
        f"{base_context}\n\n"
        f"[크리에이티브 브리프]\n{outputs['strategist']}"
    )
    agent = get_pipeline_agent("writer")
    notify(f"  {agent['icon']} **{agent['name']}** 실행 중...")
    outputs["writer"] = _call_agent("writer", writer_context, platform)
    notify(f"  ✅ {agent['name']} 완료")

    # ── PHASE 2: 편집 ──
    notify(f"⚗️ Phase 2: 편집 ({platform_label})...")
    editor_context = (
        f"{base_context}\n\n"
        f"[크리에이티브 브리프]\n{outputs['strategist']}\n\n"
        f"[현재 본문 — 이 글을 편집하세요]\n{outputs['writer']}"
    )
    agent = get_pipeline_agent("editor")
    notify(f"  {agent['icon']} **{agent['name']}** 실행 중...")
    outputs["editor"] = _call_agent("editor", editor_context, platform)
    notify(f"  ✅ {agent['name']} 완료")

    edited_text = outputs["editor"]

    # ── PHASE 3: 이미지 + SEO전환 (병렬) ──
    notify(f"🎬📊 Phase 3: 이미지 + SEO전환 (병렬, {platform_label})...")

    img_context = (
        f"{base_context}\n\n{IMAGE_COMMON_RULE}\n\n"
        f"[본문]\n{edited_text}"
    )
    seo_context = (
        f"{base_context}\n\n"
        f"[크리에이티브 브리프]\n{outputs['strategist']}\n\n"
        f"[본문]\n{edited_text}"
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        agent_img = get_pipeline_agent("image_director")
        agent_seo = get_pipeline_agent("seo_converter")
        notify(f"  {agent_img['icon']} **{agent_img['name']}** 실행 중...")
        notify(f"  {agent_seo['icon']} **{agent_seo['name']}** 실행 중...")

        img_fut = pool.submit(_call_agent, "image_director", img_context, platform)
        seo_fut = pool.submit(_call_agent, "seo_converter", seo_context, platform)

        outputs["image_director"] = img_fut.result()
        notify(f"  ✅ {agent_img['name']} 완료")
        outputs["seo_converter"] = seo_fut.result()
        notify(f"  ✅ {agent_seo['name']} 완료")

    # ── PHASE 4: 최종 조립 ──
    notify("🔨 Phase 4: 최종 조립...")
    assemble_context = (
        f"{base_context}\n\n"
        f"[편집된 본문]\n{edited_text}\n\n"
        f"[SEO + CTA + 메타데이터 + 푸터 슬로건]\n{outputs['seo_converter']}"
    )
    agent = get_pipeline_agent("assembler")
    notify(f"  {agent['icon']} **{agent['name']}** 실행 중...")
    outputs["assembler"] = _call_agent("assembler", assemble_context, platform)
    assembled_blog = outputs["assembler"]
    notify(f"  ✅ {agent['name']} 완료")

    # ── PHASE 5: 품질 감사 ──
    notify("🏅 Phase 5: 품질 감사...")
    agent = get_pipeline_agent("qa_auditor")
    notify(f"  {agent['icon']} **{agent['name']}** 실행 중...")
    outputs["qa_auditor"] = _call_agent("qa_auditor", f"[완성된 블로그]\n{assembled_blog}", platform)
    qa_score = _parse_qa_score(outputs["qa_auditor"])
    notify(f"  ✅ {agent['name']} 완료")
    notify(f"  🏅 QA 점수: **{qa_score}/80** {'✅ PASS' if qa_score >= PIPELINE_QA_THRESHOLD else '❌ FAIL'}")

    # ── PHASE 6: 조건부 수정 (QA 실패 시) ──
    revision_round = 0
    while qa_score < PIPELINE_QA_THRESHOLD and revision_round < PIPELINE_MAX_REVISION_ROUNDS:
        revision_round += 1
        notify(f"🔬 Phase 6: 수정 (라운드 {revision_round}/{PIPELINE_MAX_REVISION_ROUNDS})...")

        agent = get_pipeline_agent("reviser")
        notify(f"  {agent['icon']} **{agent['name']}** 실행 중...")
        revision_prompt = (
            f"[현재 블로그]\n{assembled_blog}\n\n"
            f"[QA 감사 결과 — 이 문제점만 정확히 수정하세요]\n{outputs['qa_auditor']}"
        )
        outputs["reviser"] = _call_agent("reviser", revision_prompt, platform)
        assembled_blog = outputs["reviser"]
        notify(f"  ✅ {agent['name']} 완료")

        notify("  🏅 품질 재검사 중...")
        outputs["qa_auditor"] = _call_agent("qa_auditor", f"[완성된 블로그]\n{assembled_blog}", platform)
        qa_score = _parse_qa_score(outputs["qa_auditor"])
        notify(f"  🏅 재검사 점수: **{qa_score}/80** {'✅ PASS' if qa_score >= PIPELINE_QA_THRESHOLD else '❌ FAIL'}")

    if qa_score < PIPELINE_QA_THRESHOLD:
        notify(f"  ⚠️ QA {qa_score}/80 — 최대 수정 횟수 도달, 현재 버전으로 진행")

    notify(f"✅ 파이프라인 완료 ({platform_label}, 7 에이전트, QA: {qa_score}/80)")

    return {
        "blog": assembled_blog,
        "metadata": outputs.get("seo_converter", ""),
        "image_prompts": outputs.get("image_director", ""),
        "qa_score": qa_score,
        "qa_report": outputs.get("qa_auditor", ""),
        "agent_outputs": outputs,
    }
