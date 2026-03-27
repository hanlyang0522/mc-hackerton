# Cover Letter Data Pipeline

지원 기업 기준으로 다음 데이터를 수집해 `./db`에 JSON으로 저장합니다.

- DART 최근 3개년 사업보고서의 `사업의 내용`
- 최근 뉴스 이슈/사업 동향 (API 우선, MCP 폴백)
- 기업 인재상/핵심가치

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 필수 설정

- `.env` 에 `DART_API_KEY` 설정
- 뉴스 API 사용 시 `NEWS_API_CLIENT_ID`, `NEWS_API_CLIENT_SECRET` 설정
- MCP 폴백 사용 시 `MCP_NEWS_ENDPOINT` 설정

## 실행

```bash
python -m src.main "삼성전자"
```

## 출력

- raw
  - `db/raw/dart/<company>.json`
  - `db/raw/news/<company>.json`
  - `db/raw/talent/<company>.json`
- processed
  - `db/processed/<company>.json`

## 코드 구조

- `src/main.py`: CLI 진입점
- `src/crawling/pipeline`: 파이프라인 오케스트레이션
- `src/crawling/collectors`: 기능별 수집기
  - `dart.py`: 사업보고서 수집
  - `news.py`: 뉴스 수집
  - `talent.py`: 인재상/핵심가치 수집
- `src/crawling/core`: 공용 구성요소
  - `config.py`: 환경설정 로딩
  - `models.py`: 데이터 모델
  - `storage.py`: JSON 저장
  - `utils.py`: HTTP/문자열 유틸

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
