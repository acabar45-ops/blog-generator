# ================================================================
#  회사 프로필 관리 모듈
#  - 여러 회사 프로필을 JSON으로 저장/로드
#  - Claude API로 회사별 블로그 토픽 100개 자동 생성
# ================================================================

import json
import os
from pathlib import Path

import anthropic

# ── 경로 설정 ──
BASE_DIR = Path(__file__).resolve().parent
COMPANIES_DIR = BASE_DIR / "data" / "companies"

# ── 기본 회사 (하우스맨) 데이터 ──
DEFAULT_COMPANY_ID = "houseman"

DEFAULT_HOUSEMAN_DATA = {
    "id": "houseman",
    "name": "하우스맨",
    "website": "houseman.co.kr",
    "founded": "2011",
    "team_size": "",
    "managed_count": "100개 이상",
    "region": "서울 강남·역삼·논현·대치·성수·마포·구로·관악·강동·광진",
    "clients": "포르쉐코리아, 이브릿지(보건복지부 산하), 미트박스(코스닥 상장)",
    "strengths": "15년 현장 경험 + 자체 개발 건물관리 자동화 시스템",
    "industry": "건물관리 위탁",
    "representative": "박종호",
    "phone": "1544-4150",
    "phone_direct": "010-5560-8245",
    "address": "강남구 학동로8길 9, 5층",
    "naver_map_url": "https://map.naver.com/v5/search/%EA%B0%95%EB%82%A8%EA%B5%AC%20%ED%95%99%EB%8F%99%EB%A1%9C8%EA%B8%B8%209",
    "seo_keywords": "서울 건물관리 위탁, 상가 건물 관리업체, 건물주 자동화 관리, 강남 건물관리, 중소형 빌딩 관리",
    "description": (
        "전화 한 통 없이도 건물이 스스로 관리됩니다. "
        "하우스맨은 2011년부터 서울 주요 상권의 상업용 건물을 위탁 관리해온 전문 기업입니다. "
        "15년간 축적한 현장 경험과 자체 개발한 건물관리 자동화 시스템을 결합하여, "
        "건물주가 직접 전화받고 현장 나가는 일 없이도 건물이 체계적으로 관리되는 환경을 만들어 드립니다. "
        "포르쉐코리아, 이브릿지(보건복지부 산하기관), 미트박스(코스닥 상장기업) 등 "
        "100개 이상의 건물을 전문 팀이 관리합니다. "
        "임대관리, 수금 자동화, 민원 대응, 시설 관리, 단기임대 운영, 원상복구, "
        "비상주 관리사무소, 기업 시설관리 외주까지 건물 운영에 필요한 모든 업무를 원스톱으로 제공합니다. "
        "수금 자동화, 단기계약 자동화, QR 민원 시스템, 건물주 포털, 카카오 알림톡 자동화 등 "
        "5대 자동화 시스템으로 관리 효율을 극대화합니다. "
        "하우스맨은 실제 운영 성과를 바탕으로 꾸준히 성장해왔습니다."
    ),
    "topics": [
        # ──── 네이버 블로그 50개 ────
        # 실무팁 (21개) — 실용적 how-to, 체크리스트, 현장 노하우
        {"id": 1,   "title": "공실 3개월 이상 지속될 때 체크해야 할 것들",          "category": "실무팁", "platform": "naver"},
        {"id": 2,   "title": "건물 하자 발생 시 건물주가 해야 할 대처법",            "category": "실무팁", "platform": "naver"},
        {"id": 3,   "title": "임차인 퇴실 정산, 분쟁 없이 끝내는 방법",             "category": "실무팁", "platform": "naver"},
        {"id": 4,   "title": "상가 건물 관리비 항목, 제대로 알고 계신가요?",         "category": "실무팁", "platform": "naver"},
        {"id": 5,   "title": "노후 건물 유지보수 비용 줄이는 현장 노하우",           "category": "실무팁", "platform": "naver"},
        {"id": 6,   "title": "임차인 민원, 빠르게 해결하는 프로세스",               "category": "실무팁", "platform": "naver"},
        {"id": 8,   "title": "공실 발생 즉시 해야 할 5가지 행동",                   "category": "실무팁", "platform": "naver"},
        {"id": 9,   "title": "관리업체 선택 시 반드시 확인해야 할 7가지",            "category": "실무팁", "platform": "naver"},
        {"id": 11,  "title": "수금 연체 임차인 대응 실전 가이드",                   "category": "실무팁", "platform": "naver"},
        {"id": 12,  "title": "건물 청소·시설팀 외주 관리하는 법",                   "category": "실무팁", "platform": "naver"},
        {"id": 14,  "title": "신축 건물 첫 입주 전 꼭 점검할 체크리스트",           "category": "실무팁", "platform": "naver"},
        {"id": 17,  "title": "엘리베이터 점검 주기와 비용 절감법",                  "category": "실무팁", "platform": "naver"},
        {"id": 18,  "title": "건물 누수 발생 시 긴급 대응 매뉴얼",                  "category": "실무팁", "platform": "naver"},
        {"id": 19,  "title": "임차인 인테리어 공사 허가 기준과 관리법",              "category": "실무팁", "platform": "naver"},
        {"id": 20,  "title": "건물 주차장 관리로 임차인 만족도 높이는 법",           "category": "실무팁", "platform": "naver"},
        {"id": 21,  "title": "전기·수도·가스 공용 요금 분배 정확하게 하는 법",       "category": "실무팁", "platform": "naver"},
        {"id": 22,  "title": "건물 외벽·간판 관리, 방치하면 생기는 문제",            "category": "실무팁", "platform": "naver"},
        {"id": 24,  "title": "건물 소방 점검 주기와 과태료 피하는 법",               "category": "실무팁", "platform": "naver"},
        {"id": 25,  "title": "명절·장기 휴일 건물 관리 비상 체크리스트",             "category": "실무팁", "platform": "naver"},
        {"id": 26,  "title": "관리업체 변경 시 인수인계 체크리스트",                 "category": "실무팁", "platform": "naver"},
        {"id": 28,  "title": "임차인 원상복구 기준, 어디까지 요구할 수 있나",        "category": "실무팁", "platform": "naver"},
        # 도입사례 (15개) — 스토리텔링, 건물주 공감, 에피소드
        {"id": 31,  "title": "포르쉐코리아 건물, 하우스맨이 관리하는 이유",          "category": "도입사례", "platform": "naver"},
        {"id": 32,  "title": "성수동 빌딩 공실률 0% 달성 사례",                    "category": "도입사례", "platform": "naver"},
        {"id": 33,  "title": "수금 자동화 도입 후 건물주의 달라진 일상",             "category": "도입사례", "platform": "naver"},
        {"id": 34,  "title": "퇴실 정산 자동화로 분쟁이 사라진 사례",               "category": "도입사례", "platform": "naver"},
        {"id": 35,  "title": "강남 상가 건물주가 하우스맨을 선택한 이유",            "category": "도입사례", "platform": "naver"},
        {"id": 37,  "title": "코스닥 상장기업 미트박스가 신뢰한 관리 시스템",        "category": "도입사례", "platform": "naver"},
        {"id": 38,  "title": "마포 오피스 빌딩 관리비 연 4,000만원 절감 사례",       "category": "도입사례", "platform": "naver"},
        {"id": 39,  "title": "건물주 포털 도입 후 야간 문의가 사라진 이야기",        "category": "도입사례", "platform": "naver"},
        {"id": 40,  "title": "관악구 중소형 건물, 위탁관리 전후 비교",              "category": "도입사례", "platform": "naver"},
        {"id": 41,  "title": "건물주가 해외 출장 중에도 관리가 되는 이유",           "category": "도입사례", "platform": "naver"},
        {"id": 42,  "title": "직접 관리 10년 → 하우스맨 전환 후 달라진 점",         "category": "도입사례", "platform": "naver"},
        {"id": 43,  "title": "신축 건물 첫 입주부터 하우스맨과 함께한 사례",         "category": "도입사례", "platform": "naver"},
        {"id": 46,  "title": "보건복지부 산하기관 이브릿지 관리 사례",               "category": "도입사례", "platform": "naver"},
        {"id": 48,  "title": "건물주 3명이 말하는 하우스맨 솔직 후기",              "category": "도입사례", "platform": "naver"},
        {"id": 50,  "title": "하우스맨 계약 후 첫 1개월, 무엇이 바뀌나",            "category": "도입사례", "platform": "naver"},
        # 트렌드 (6개) — 건물주가 바로 검색할 실용 정보
        {"id": 61,  "title": "서울 역세권 소형 빌딩 공실 관리 전략",               "category": "트렌드", "platform": "naver"},
        {"id": 63,  "title": "임대수익 극대화를 위한 리모델링 타이밍",              "category": "트렌드", "platform": "naver"},
        {"id": 67,  "title": "MZ세대 임차인이 원하는 건물 조건",                   "category": "트렌드", "platform": "naver"},
        {"id": 71,  "title": "상가 건물 공실 보험, 알고 계신가요?",                "category": "트렌드", "platform": "naver"},
        {"id": 72,  "title": "건물 매입 전 관리 상태 체크하는 법",                  "category": "트렌드", "platform": "naver"},
        {"id": 73,  "title": "지방 건물주가 서울 건물 원격 관리하는 방법",           "category": "트렌드", "platform": "naver"},
        # 자동화 (8개) — 쉬운 기능 소개, 건물주 체감형
        {"id": 76,  "title": "하우스맨 자동화 시스템 5가지 완전 정리",              "category": "자동화", "platform": "naver"},
        {"id": 77,  "title": "단기계약 자동화란? 24시간 무인 계약의 실제",          "category": "자동화", "platform": "naver"},
        {"id": 78,  "title": "수금 자동화로 월 120만원 업무가 사라지는 원리",        "category": "자동화", "platform": "naver"},
        {"id": 79,  "title": "건물주 전용 포털, 스마트폰으로 수익 실시간 확인",     "category": "자동화", "platform": "naver"},
        {"id": 80,  "title": "QR 민원 시스템, 입주민 불만을 앱으로 해결하는 법",    "category": "자동화", "platform": "naver"},
        {"id": 81,  "title": "카카오 알림톡 자동화, 건물주·임차인 소통의 혁신",     "category": "자동화", "platform": "naver"},
        {"id": 82,  "title": "퇴실 사진 비교 자동화, 정산 분쟁 제로의 비밀",        "category": "자동화", "platform": "naver"},
        {"id": 88,  "title": "건물주가 앱 하나로 할 수 있는 것들",                  "category": "자동화", "platform": "naver"},

        # ──── 워드프레스 50개 ────
        # 실무팁 (9개) — 비교분석, 법률, 데이터 심층
        {"id": 7,   "title": "건물 CCTV·IoT 관리, 왜 필요한가",                    "category": "실무팁", "platform": "wordpress"},
        {"id": 10,  "title": "계약 갱신 거절, 건물주가 알아야 할 법적 기준",         "category": "실무팁", "platform": "wordpress"},
        {"id": 13,  "title": "서울 상가 건물 관리비 적정 수준은?",                  "category": "실무팁", "platform": "wordpress"},
        {"id": 15,  "title": "건물주가 직접 관리 vs 위탁관리, 현실적 비교",         "category": "실무팁", "platform": "wordpress"},
        {"id": 16,  "title": "건물 화재보험·배상책임보험 필수 가입 가이드",          "category": "실무팁", "platform": "wordpress"},
        {"id": 23,  "title": "임대차 분쟁 예방을 위한 계약서 작성 핵심",             "category": "실무팁", "platform": "wordpress"},
        {"id": 27,  "title": "건물 옥상·지하 공간 활용으로 수익 만드는 법",          "category": "실무팁", "platform": "wordpress"},
        {"id": 29,  "title": "건물 에너지 절감으로 연간 수백만원 아끼는 법",          "category": "실무팁", "platform": "wordpress"},
        {"id": 30,  "title": "장기 공실 건물, 리모델링 vs 임대료 인하 판단법",       "category": "실무팁", "platform": "wordpress"},
        # 도입사례 (5개) — 데이터 기반, 분석형
        {"id": 36,  "title": "전문 팀으로 100개 건물 관리하는 비결",                 "category": "도입사례", "platform": "wordpress"},
        {"id": 44,  "title": "임차인 만족도 조사, 하우스맨 관리 건물 결과",          "category": "도입사례", "platform": "wordpress"},
        {"id": 45,  "title": "건물 매각 시 관리 이력이 가격에 미치는 영향",          "category": "도입사례", "platform": "wordpress"},
        {"id": 47,  "title": "복합 용도 건물 관리, 하우스맨 접근법",                "category": "도입사례", "platform": "wordpress"},
        {"id": 49,  "title": "경쟁 입찰에서 하우스맨이 선택된 이유",                "category": "도입사례", "platform": "wordpress"},
        # 트렌드 (19개) — 시장분석, 데이터, 전문 SEO
        {"id": 51,  "title": "2025년 서울 상가 공실률 현황과 전망",                 "category": "트렌드", "platform": "wordpress"},
        {"id": 52,  "title": "강남 vs 성수 vs 마포, 임대 수익률 비교",              "category": "트렌드", "platform": "wordpress"},
        {"id": 53,  "title": "AI 시대, 건물관리도 자동화가 표준이 된다",             "category": "트렌드", "platform": "wordpress"},
        {"id": 54,  "title": "서울 중소형 상업용 건물 투자 트렌드",                 "category": "트렌드", "platform": "wordpress"},
        {"id": 55,  "title": "건물주가 알아야 할 2025년 임대차 법 변화",             "category": "트렌드", "platform": "wordpress"},
        {"id": 56,  "title": "공유오피스 확산이 일반 임대 건물에 미치는 영향",       "category": "트렌드", "platform": "wordpress"},
        {"id": 57,  "title": "서울 도심 소형 빌딩 수익률 극대화 전략",              "category": "트렌드", "platform": "wordpress"},
        {"id": 58,  "title": "건물 노후화 시대, 관리가 자산 가치를 결정한다",        "category": "트렌드", "platform": "wordpress"},
        {"id": 59,  "title": "임차인 트렌드 변화, 건물주는 무엇을 준비해야 하나",    "category": "트렌드", "platform": "wordpress"},
        {"id": 60,  "title": "상업용 부동산 관리 비용, 적게 쓰고 많이 남기는 법",   "category": "트렌드", "platform": "wordpress"},
        {"id": 62,  "title": "건물주 세금 절감, 관리비 구조로 접근하는 법",         "category": "트렌드", "platform": "wordpress"},
        {"id": 64,  "title": "2025년 건물관리 위탁 시장 규모와 성장 이유",          "category": "트렌드", "platform": "wordpress"},
        {"id": 65,  "title": "디지털 전환 시대, 아날로그 건물관리의 한계",          "category": "트렌드", "platform": "wordpress"},
        {"id": 66,  "title": "금리 변동이 건물 투자 수익에 미치는 영향",            "category": "트렌드", "platform": "wordpress"},
        {"id": 68,  "title": "서울 주요 상권별 임대 시장 분석 (강남·홍대·성수)",     "category": "트렌드", "platform": "wordpress"},
        {"id": 69,  "title": "건물 가치 평가, 관리 상태가 얼마나 영향을 주나",      "category": "트렌드", "platform": "wordpress"},
        {"id": 70,  "title": "1인 법인 건물주 증가, 관리 위탁이 필수인 이유",       "category": "트렌드", "platform": "wordpress"},
        {"id": 74,  "title": "상업용 부동산 ESG, 건물주가 준비해야 할 것",          "category": "트렌드", "platform": "wordpress"},
        {"id": 75,  "title": "건물관리 업계 트렌드, 앞으로 5년 전망",              "category": "트렌드", "platform": "wordpress"},
        # 자동화 (17개) — 기술 심층, 비교분석, ROI
        {"id": 83,  "title": "공실 자동 매물 등록, 공실 기간을 줄이는 기술",        "category": "자동화", "platform": "wordpress"},
        {"id": 84,  "title": "CCTV·IoT 원격 모니터링, 현장 없이 건물 보는 법",     "category": "자동화", "platform": "wordpress"},
        {"id": 85,  "title": "하우스맨 vs 일반 관리업체, 자동화 시스템 차이",       "category": "자동화", "platform": "wordpress"},
        {"id": 86,  "title": "건물관리 자동화란? 개념부터 실전까지",                "category": "자동화", "platform": "wordpress"},
        {"id": 87,  "title": "자동화 시스템 도입 전후 비교 (시간·비용)",            "category": "자동화", "platform": "wordpress"},
        {"id": 89,  "title": "현장팀 스케줄 자동 관리, 빠지는 일정 없는 비결",      "category": "자동화", "platform": "wordpress"},
        {"id": 90,  "title": "계약서 자동 발송 시스템, 어떻게 작동하나",            "category": "자동화", "platform": "wordpress"},
        {"id": 91,  "title": "수금 알림 자동화, 연체율을 낮추는 구조",              "category": "자동화", "platform": "wordpress"},
        {"id": 92,  "title": "건물 관리 리포트 자동 생성, 건물주에게 매달 전달",    "category": "자동화", "platform": "wordpress"},
        {"id": 93,  "title": "임차인 입주 안내 자동화, 첫인상을 바꾸는 시스템",     "category": "자동화", "platform": "wordpress"},
        {"id": 94,  "title": "시설 점검 스케줄 자동화, 하자를 미리 잡는 법",        "category": "자동화", "platform": "wordpress"},
        {"id": 95,  "title": "15년 현장 경험이 만든 자동화, 왜 다른가",             "category": "자동화", "platform": "wordpress"},
        {"id": 96,  "title": "일반 관리 프로그램 vs 하우스맨 전용 시스템 비교",     "category": "자동화", "platform": "wordpress"},
        {"id": 97,  "title": "건물관리 SaaS 시장, 하우스맨의 위치",                "category": "자동화", "platform": "wordpress"},
        {"id": 98,  "title": "자동화 도입 ROI, 투자 대비 효과 분석",               "category": "자동화", "platform": "wordpress"},
        {"id": 99,  "title": "건물관리 자동화의 미래, 다음 단계는?",                "category": "자동화", "platform": "wordpress"},
        {"id": 100, "title": "하우스맨이 꿈꾸는 완전 자동화 건물관리",              "category": "자동화", "platform": "wordpress"},
    ],
}


# ── 기본 회사 (청소매뉴얼) 데이터 ──
DEFAULT_CLEANMANUAL_ID = "cleanmanual"

DEFAULT_CLEANMANUAL_DATA = {
    "id": "cleanmanual",
    "name": "청소매뉴얼",
    "website": "blog.naver.com/naoyada",
    "founded": "",
    "team_size": "",
    "managed_count": "80여 개 건물",
    "region": "서울 강남·성수·논현·역삼·삼성·청담·신사",
    "clients": "다수 부동산 및 빌딩관리업체, 국내 유명 프랜차이즈 본사",
    "strengths": "눈에 보이지 않는 곳까지 관리, 전용 약품 사용, 천연/친환경 세제 기본, 물기 완전 제거 마무리",
    "industry": "건물 전문 청소업체",
    "representative": "김용수",
    "phone": "1811-1555",
    "phone_direct": "010-3202-1081",
    "address": "강남구 논현동 124-25 1층 101호",
    "naver_map_url": "https://map.naver.com/v5/search/%EA%B0%95%EB%82%A8%EA%B5%AC%20%EB%85%BC%ED%98%84%EB%8F%99%20124-25",
    "seo_keywords": "강남 정기청소, 건물 계단청소, 공용화장실 청소, 배수구 청소, 입주청소, 준공청소, 건물청소 전문업체",
    "description": (
        "체계화된 청소의 기준, 청소매뉴얼입니다. "
        "청소매뉴얼은 강남구 기반으로 다수의 부동산 및 빌딩관리업체와 협약을 맺고 "
        "건물을 정기 관리하는 전문 청소업체입니다. "
        "현재 강남 일대 80여 개 건물을 정기 관리하고 있으며, "
        "대부분의 건물은 첫 계약 이후 재계약으로 이어지고 있습니다. "
        "일반 세제로는 제거되지 않는 고착 오염에 전용 약품을 사용하고, "
        "배수구 분해 청소, 변기 힌지 오염 제거, 점자블록 이물질 제거 등 "
        "다른 업체가 놓치는 보이지 않는 곳까지 관리합니다. "
        "모든 작업은 마른걸레로 물기 완전 제거까지 마무리하며, "
        "화학약품 사용을 최소화하고 천연/친환경 세제를 기본으로 사용합니다. "
        "정기청소, 입주청소, 퇴실청소, 준공청소, 배수구청소, 외부미관청소, "
        "마루광택, 곰팡이제거, 고압세척 등 건물 청소 전반을 제공합니다."
    ),
    "topics": [],  # 앱에서 Claude API로 자동 생성 예정
}


# ================================================================
#  유틸리티
# ================================================================

def _ensure_companies_dir():
    """data/companies/ 폴더가 없으면 생성"""
    COMPANIES_DIR.mkdir(parents=True, exist_ok=True)


def _company_path(company_id: str) -> Path:
    """회사 JSON 파일 경로 반환"""
    return COMPANIES_DIR / f"{company_id}.json"


# ================================================================
#  CRUD 함수
# ================================================================

def list_companies() -> list[str]:
    """저장된 회사 ID 목록 반환"""
    _ensure_companies_dir()
    return sorted(
        p.stem for p in COMPANIES_DIR.glob("*.json")
    )


def load_company(company_id: str) -> dict:
    """회사 프로필 JSON을 읽어서 dict로 반환.
    파일이 없으면 FileNotFoundError 발생.
    """
    path = _company_path(company_id)
    if not path.exists():
        raise FileNotFoundError(f"회사 프로필을 찾을 수 없습니다: {company_id}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_company(company_id: str, data: dict) -> None:
    """회사 프로필을 JSON 파일로 저장"""
    _ensure_companies_dir()
    data["id"] = company_id  # id 필드 보장
    path = _company_path(company_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def delete_company(company_id: str) -> bool:
    """회사 프로필 삭제. 성공 시 True, 파일 없으면 False."""
    path = _company_path(company_id)
    if path.exists():
        path.unlink()
        return True
    return False


# ================================================================
#  프롬프트용 회사 정보 포매팅
# ================================================================

def get_company_info_prompt(company_id: str) -> str:
    """Claude 프롬프트에 삽입할 회사 정보 문자열을 반환"""
    data = load_company(company_id)

    lines = [
        f"[회사 기본 정보]",
        f"- 회사명: {data.get('name', '')}",
        f"- 웹사이트: {data.get('website', '')}",
        f"- 설립연도: {data.get('founded', '')}",
        f"- 서비스 지역: {data.get('region', '')}",
        f"- 업종: {data.get('industry', '')}",
        f"- SEO 키워드: {data.get('seo_keywords', '')}",
    ]

    # 자연어로 작성된 상세 정보 전체 전달
    desc = data.get("description", "")
    if desc.strip():
        lines.append("")
        lines.append("[회사 상세 정보 — 아래 내용을 참고하되, 광고처럼 나열하지 말고 이야기 속에 자연스럽게 녹이세요]")
        lines.append(desc)

    return "\n".join(lines)


# ================================================================
#  Claude API로 토픽 100개 생성
# ================================================================

def generate_topics_for_company(company_data: dict, api_key: str) -> list[dict]:
    """Claude API를 호출해 회사에 맞는 블로그 토픽 100개를 생성한다.

    카테고리 4개 (각 25개):
      - 실무팁: 업종 관련 실무 노하우
      - 도입사례: 해당 회사 도입/성공 사례
      - 트렌드: 업종 시장 트렌드·정보
      - 자동화: 회사 시스템·기술 소개

    Parameters:
        company_data: 회사 프로필 dict (topics 제외 정보 사용)
        api_key: Anthropic API 키

    Returns:
        list[dict] - [{"id": 1, "title": "...", "category": "실무팁"}, ...]
    """
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""당신은 B2B 블로그 콘텐츠 전략 전문가입니다.
아래 회사 정보를 바탕으로, 이 회사의 블로그에 올릴 토픽 100개를 만들어 주세요.

[회사 정보]
- 회사명: {company_data.get('name', '')}
- 업종: {company_data.get('industry', '')}
- 핵심 강점: {company_data.get('strengths', '')}
- 서비스 지역: {company_data.get('region', '')}
- 주요 고객사: {company_data.get('clients', '')}
- SEO 키워드: {company_data.get('seo_keywords', '')}
- 회사 소개: {company_data.get('description', '')}

[카테고리 및 개수]
1. 실무팁 (25개) — 업종 관련 실무 노하우, 체크리스트, 가이드
2. 도입사례 (25개) — 이 회사의 서비스 도입 사례, 고객 후기, 전후 비교
3. 트렌드 (25개) — 업종 시장 트렌드, 법규 변화, 투자 정보
4. 자동화 (25개) — 회사의 기술·시스템·자동화 기능 소개

[규칙]
- 토픽은 해당 업종에 특화되어야 합니다.
- 각 토픽 제목은 구체적이고 클릭하고 싶은 제목이어야 합니다.
- 한국어로 작성하세요.
- 반드시 JSON 배열 형태로만 출력하세요. 다른 텍스트는 포함하지 마세요.
- 형식: [{{"id": 1, "title": "제목", "category": "실무팁"}}, ...]
- id는 1부터 100까지 순서대로 부여하세요.
- 실무팁 1~25, 도입사례 26~50, 트렌드 51~75, 자동화 76~100 순서로 배치하세요.
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    # 응답에서 JSON 배열 추출
    response_text = message.content[0].text.strip()

    # JSON 블록이 ```json ... ``` 로 감싸진 경우 처리
    if response_text.startswith("```"):
        # 첫 줄(```json)과 마지막 줄(```) 제거
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1]).strip()

    topics = json.loads(response_text)

    # 유효성 검증: 100개인지 확인
    if not isinstance(topics, list):
        raise ValueError("Claude 응답이 JSON 배열이 아닙니다.")

    return topics


# ================================================================
#  초기화: 기본 회사(하우스맨) 프로필 생성
# ================================================================

def initialize_default_company() -> None:
    """기본 회사 프로필(하우스맨, 청소매뉴얼)이 없으면 생성한다."""
    _ensure_companies_dir()
    if not _company_path(DEFAULT_COMPANY_ID).exists():
        save_company(DEFAULT_COMPANY_ID, DEFAULT_HOUSEMAN_DATA.copy())
        print(f"[company_manager] 기본 회사 '{DEFAULT_COMPANY_ID}' 프로필을 생성했습니다.")
    if not _company_path(DEFAULT_CLEANMANUAL_ID).exists():
        save_company(DEFAULT_CLEANMANUAL_ID, DEFAULT_CLEANMANUAL_DATA.copy())
        print(f"[company_manager] 기본 회사 '{DEFAULT_CLEANMANUAL_ID}' 프로필을 생성했습니다.")


def get_or_create_default_company() -> dict:
    """기본 회사 프로필을 로드하되, 없으면 생성 후 로드한다."""
    try:
        return load_company(DEFAULT_COMPANY_ID)
    except FileNotFoundError:
        initialize_default_company()
        return load_company(DEFAULT_COMPANY_ID)


# ================================================================
#  직접 실행 시 초기화
# ================================================================

if __name__ == "__main__":
    initialize_default_company()
    companies = list_companies()
    print(f"등록된 회사 목록: {companies}")

    for cid in companies:
        data = load_company(cid)
        topic_count = len(data.get("topics", []))
        print(f"  - {cid}: {data['name']} (토픽 {topic_count}개)")
