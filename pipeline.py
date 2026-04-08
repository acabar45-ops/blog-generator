# ================================================================
#  7-에이전트 파이프라인 실행 엔진 (통합 리팩토링)
#  - Phase 0~6, 병렬/순차 실행
#  - QA 루프 (Phase 5 → Phase 6 → 재검사)
#  - FORMAT_RULE은 inject_format_rule=True 에이전트에만 적용
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


def _client():
    return anthropic.Anthropic(api_key=CLAUDE_API_KEY)


def _call_agent(agent_id: str, user_prompt: str, retries: int = 3) -> str:
    """단일 에이전트 Claude API 호출 (inject_format_rule에 따라 FORMAT_RULE 선택 주입)"""
    agent = get_pipeline_agent(agent_id)
    if not agent:
        raise ValueError(f"Unknown agent: {agent_id}")

    system_prompt = agent["system_prompt"]
    if agent.get("inject_format_rule", False):
        system_prompt = f"{system_prompt}\n\n{FORMAT_RULE}"

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
    return f"[주제] {topic_title}\n[플랫폼] {platform}\n[회사 정보]\n{company_info}"


def run_pipeline(
    topic_title: str,
    company_id: str = "houseman",
    platform: str = "naver",
    status_callback=None,
) -> dict:
    """
    7-에이전트 파이프라인 실행

    Returns:
        {
            "blog": str,           # 최종 블로그 본문
            "metadata": str,       # 메타데이터 (seo_converter 출력에서 추출)
            "image_prompts": str,  # 이미지 프롬프트
            "qa_score": int,       # QA 점수
            "qa_report": str,      # QA 보고서
            "agent_outputs": dict, # 모든 에이전트 산출물
        }
    """

    def notify(msg):
        if status_callback:
            status_callback(msg)

    base_context = _build_context(topic_title, company_id, platform)
    outputs = {}

    # ── PHASE 0: 전략 설계 ──
    notify("🎯 Phase 0: 전략 설계...")
    agent = get_pipeline_agent("strategist")
    notify(f"  {agent['icon']} **{agent['name']}** 실행 중...")
    outputs["strategist"] = _call_agent("strategist", base_context)
    notify(f"  ✅ {agent['name']} 완료")

    # ── PHASE 1: 글쓰기 ──
    notify("✍️ Phase 1: 글쓰기...")
    writer_context = (
        f"{base_context}\n\n"
        f"[크리에이티브 브리프]\n{outputs['strategist']}"
    )
    agent = get_pipeline_agent("writer")
    notify(f"  {agent['icon']} **{agent['name']}** 실행 중...")
    outputs["writer"] = _call_agent("writer", writer_context)
    notify(f"  ✅ {agent['name']} 완료")

    # ── PHASE 2: 편집 ──
    notify("⚗️ Phase 2: 편집...")
    editor_context = (
        f"{base_context}\n\n"
        f"[크리에이티브 브리프]\n{outputs['strategist']}\n\n"
        f"[현재 본문 — 이 글을 편집하세요]\n{outputs['writer']}"
    )
    agent = get_pipeline_agent("editor")
    notify(f"  {agent['icon']} **{agent['name']}** 실행 중...")
    outputs["editor"] = _call_agent("editor", editor_context)
    notify(f"  ✅ {agent['name']} 완료")

    edited_text = outputs["editor"]

    # ── PHASE 3: 이미지 + SEO전환 (병렬) ──
    notify("🎬📊 Phase 3: 이미지 + SEO전환 (병렬)...")

    img_context = (
        f"{base_context}\n\n{IMAGE_COMMON_RULE}\n\n"
        f"[본문]\n{edited_text}"
    )
    seo_context = (
        f"{base_context}\n\n"
        f"[크리에이티브 브리프]\n{outputs['strategist']}\n\n"
        f"[키워드 전략]\n{outputs['strategist']}\n\n"
        f"[본문]\n{edited_text}"
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        agent_img = get_pipeline_agent("image_director")
        agent_seo = get_pipeline_agent("seo_converter")
        notify(f"  {agent_img['icon']} **{agent_img['name']}** 실행 중...")
        notify(f"  {agent_seo['icon']} **{agent_seo['name']}** 실행 중...")

        img_fut = pool.submit(_call_agent, "image_director", img_context)
        seo_fut = pool.submit(_call_agent, "seo_converter", seo_context)

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
    outputs["assembler"] = _call_agent("assembler", assemble_context)
    assembled_blog = outputs["assembler"]
    notify(f"  ✅ {agent['name']} 완료")

    # ── PHASE 5: 품질 감사 ──
    notify("🏅 Phase 5: 품질 감사...")
    agent = get_pipeline_agent("qa_auditor")
    notify(f"  {agent['icon']} **{agent['name']}** 실행 중...")
    outputs["qa_auditor"] = _call_agent("qa_auditor", f"[완성된 블로그]\n{assembled_blog}")
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
        outputs["reviser"] = _call_agent("reviser", revision_prompt)
        assembled_blog = outputs["reviser"]
        notify(f"  ✅ {agent['name']} 완료")

        # 재검사
        notify("  🏅 품질 재검사 중...")
        outputs["qa_auditor"] = _call_agent("qa_auditor", f"[완성된 블로그]\n{assembled_blog}")
        qa_score = _parse_qa_score(outputs["qa_auditor"])
        notify(f"  🏅 재검사 점수: **{qa_score}/80** {'✅ PASS' if qa_score >= PIPELINE_QA_THRESHOLD else '❌ FAIL'}")

    if qa_score < PIPELINE_QA_THRESHOLD:
        notify(f"  ⚠️ QA {qa_score}/80 — 최대 수정 횟수 도달, 현재 버전으로 진행")

    notify(f"✅ 파이프라인 완료 (7 에이전트, QA: {qa_score}/80)")

    return {
        "blog": assembled_blog,
        "metadata": outputs.get("seo_converter", ""),
        "image_prompts": outputs.get("image_director", ""),
        "qa_score": qa_score,
        "qa_report": outputs.get("qa_auditor", ""),
        "agent_outputs": outputs,
    }
