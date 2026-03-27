# AI Cover Letter Generator

지원 기업의 정보를 크롤링한 후, 직무에 맞는 맞춤형 자소서를 자동으로 생성합니다.

## 구성

### 1단계: 기업 정보 크롤링

지원 기업 기준으로 다음 데이터를 수집해 `./db/raw`에 JSON으로 저장합니다.

- **DART 사업보고서**: 최근 3개년의 `사업의 내용` (DART 공시 시스템)
- **뉴스**: 최근 뉴스 이슈/사업 동향 (Tavily 검색 API 우선, Naver News API, MCP 폴백)
- **기업 인재상**: Tavily 검색으로 수집한 채용 공고 및 인재상/핵심 가치

### 2단계: 자소서 생성

Gemini API를 통해 수집된 기업 정보를 분석하고, 해당 직무에 맞는 자격 요건 및 강조 포인트를 추출합니다. 
이후 소재 선택 알고리즘과 글 구조 선택 알고리즘을 적용해 최종 자소서를 생성합니다.

## 설치

```bash
conda create -n cl-pipeline python=3.11
conda activate cl-pipeline
pip install -r requirements.txt
cp .env.example .env
```

## 필수 설정

`.env` 파일에 다음을 설정합니다:

| 변수 | 설명 | 필수 |
|---|---|---|
| `DART_API_KEY` | OpenDART API 키 (dart_fss) | ✅ |
| `TAVILY_API_KEY` | Tavily 검색 API 키 (기업 정보/뉴스 검색) | ✅ |
| `GEMINI_API_KEY` | Google Gemini API 키 (기업 분석 및 자소서 생성) | ✅ |
| `REVIEWER_API_URL` | reviewer HTTP 서버 주소. 설정 시 생성된 자소서 초안 평가 실행 | ❌ |
| `NEWS_API_CLIENT_ID`, `NEWS_API_CLIENT_SECRET` | Naver News API (Tavily 실패 시 폴백) | ❌ |
| `MCP_NEWS_ENDPOINT` | MCP 뉴스 서버 (마지막 폴백) | ❌ |

## 실행

### 기업 정보만 수집
```bash
python -m src.main "SK하이닉스"
```

### 기업 정보 + 자소서 생성 (직무 지정)
```bash
python -m src.main "SK하이닉스" --job "반도체 공정 엔지니어"
```

### 자소서 생성 + reviewer 평가
```bash
python -m src.reviewer_agent_server

# 다른 터미널에서
export REVIEWER_API_URL=http://127.0.0.1:8000/agent/reviewer
python -m src.generate "SK하이닉스" "반도체 공정 엔지니어" "지원 동기를 서술하시오" --max-length 1000
```

`REVIEWER_API_URL`이 설정되어 있으면 reviewer는 생성된 초안을 평가합니다. 설정되어 있지 않으면 reviewer 단계는 자동으로 건너뜁니다.

## 출력

### 수집된 기업 정보
- `db/raw/dart/<company>.json` - 최근 3개년 사업보고서
- `db/raw/news/<company>.json` - 최근 뉴스 (20개)
- `db/raw/talent/<company>.json` - 기업 인재상 및 핵심 가치
- `db/processed/<company>.json` - 통합 기업 정보

### 생성된 자소서
- `db/processed/gemini/<company>_<job>.json` - Gemini 분석 결과 (직무 관련 요점, 최근 이슈, 인재상 적합도 등)
- `db/processed/review/<company>_<job>_<hash>.json` - reviewer 평가 결과

## 코드 구조

```
src/
├── main.py                          # CLI 진입점 (회사, --job 인자 처리)
├── crawling/
│   ├── pipeline/
│   │   ├── cover_letter.py          # 오케스트레이션: DART→뉴스→인재상→Gemini
│   │   └── gemini_extractor.py      # Gemini API로 직무 관련 정보 추출
│   ├── collectors/
│   │   ├── dart.py                  # DART 사업보고서 수집 (최근 3년)
│   │   ├── news.py                  # 뉴스 수집 (Tavily→API→MCP 폴백)
│   │   └── talent.py                # 기업 인재상 수집 (Tavily + Gemini)
│   └── core/
│       ├── config.py                # .env 로딩 및 설정 관리
│       ├── models.py                # 데이터 클래스
│       ├── storage.py               # JSON 저장
│       └── utils.py                 # HTTP/문자열 유틸
├── material_selection/              # 자소서 소재 선택 알고리즘
├── pipeline/                        # 자소서 생성 및 reviewer 연동
└── structure_selection/             # 자소서 글 구조 선택 알고리즘
```

### 크롤링 알고리즘

#### 1. DART 사업보고서 수집
- corp_code 조회 후 최근 3개년 신고서 검색
- DART 섹션 필터링으로 "사업의 개요", "주요 제품" 등 추출
- "사업의 개요" 중복 제거 (최신년만 유지)

#### 2. 뉴스 수집
| 우선순위 | 제공자 | 특징 |
|---|---|---|
| 1순위 | Tavily | 고급 검색 (최대 20개) |
| 2순위 | Naver News API | 국내 뉴스 (ID/PW 필수) |
| 3순위 | MCP NewsProvider | 폴백 |

#### 3. 기업 인재상 수집
1. Tavily 검색: `"{company} 인재상 핵심가치 채용문화"` 쿼리
2. Gemini로 정리: talent_description + core_values 리스트 생성

#### 4. Gemini 직무 분석
입력: 회사명, 직무명, DART 내용, 뉴스, 인재상  
출력: 직무 관련 요점 8개, 최근 이슈 5개, 인재상 적합도 5개, 키워드 10개

---

## 소재 선택 알고리즘 (`src/material_selection/`)

질문 리스트와 직무분석 결과(역량 키워드)를 받아 각 질문에 최적 소재를 배정한다.

### 스코어링

| 항목 | 대상 | 가중치 |
|---|---|---|
| 질문 키워드 매칭 | question ↔ material.keywords | ×3 |
| 역량-capabilities 매칭 | competency_keywords ↔ material.capabilities | ×3 |
| 질문 유형 매칭 | question_type ↔ material.question_types | ×2 |
| 역량-keywords 매칭 | competency_keywords ↔ material.keywords | ×2 |
| 우선순위 | material.priority (1→3점, 2→2점, 3→1점) | ×1 |

### 중복 방지

질문을 순차 처리하며 `used = set()`으로 이미 배정된 소재를 제외한다. 질문 수가 소재 수(12개)를 초과하면 최고점 소재를 재사용한다.

### 전처리

질문에서 동사 어미("기술하시오", "서술하십시오" 등)와 접두사("문항1.", "[지원동기]" 등)를 제거한 후 매칭한다.

```python
from src.material_selection import MaterialSelector

ms = MaterialSelector()
results = ms.select_all(
    questions=["당사에 지원한 동기를 서술하시오"],
    competency_keywords=["AI/ML", "클라우드"],
    question_types=["지원동기형"],
)
```

### 파일 구조

- `models.py`: `AllocationResult` 데이터 클래스
- `scorer.py`: 단일 소재 점수 계산
- `selector.py`: 전체 질문 순회 및 중복 방지 로직

---

## 글 구조 선택 알고리즘 (`src/structure_selection/`)

질문 문자열을 분석해 6개 유형 중 매칭되는 글 구조를 반환한다.

### 유형 분류

| 유형 | 매칭 키워드 예시 |
|---|---|
| 지원동기형 | 지원 동기, 지원한 이유, 왜 당사 |
| 직무적합성형 | 역량, 강점, 차별점, 직무 역량 |
| 문제해결형 | 극복, 어려움, 실패, 도전, 문제, 해결 |
| 가치관형 | 성장, 가치관, 자기소개, 어떤 사람 |
| 팀워크형 | 팀, 협업, 갈등, 설득, 함께 |
| 시사형 | 시사, 전망, 트렌드, 업계 |

### 반환 구조

- **매칭 성공**: 공통 구조 + 유형별 특화 구조 (flow, core, caution)
- **매칭 실패**: 공통 구조만

```python
from src.structure_selection import StructureSelector

ss = StructureSelector()
result = ss.select("본인이 경험한 가장 어려운 문제와 해결 과정을 기술하시오")
# result.question_type = "문제해결형"
# result.flow = ["1. 구체적인 문제 상황 설정...", ...]
# result.common_rules = ["첫 문장: 구체적 사실로 시작...", ...]
```

### 파일 구조

- `models.py`: `StructureResult` 데이터 클래스
- `matcher.py`: 질문 전처리 + 유형 키워드 매칭
- `selector.py`: 공통/특화 구조 조립

---

## 기준 데이터 (`src/data/`)

| 파일 | 용도 |
|---|---|
| `materials.json` | 소재 12개 메타데이터 + activity_detail (LLM user prompt용) |
| `question_types.json` | 공통 구조 규칙 + 6개 유형별 키워드/흐름/핵심/주의사항 |
| `banned_words.json` | 금지 표현 18개 |
| `CV.json` | 지원자 이력 (소재 선택 알고리즘 참고용) |
| `prompts/system_prompt.md` | LLM 시스템 프롬프트 (작성 규칙만, CV 미포함) |
