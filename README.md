# Cover Letter Data Pipeline

지원 기업 기준으로 자소서 작성에 필요한 데이터를 자동 수집해 `./db`에 JSON으로 저장합니다.

## 수집 데이터

| 항목 | 출처 | 설명 |
|---|---|---|
| **DART 3개년** | 한국거래소 OpenDART | 최근 사업보고서에서 "사업의 내용" 섹션 (사업개요, 주요제품·서비스, 연구개발활동) |
| **최신 뉴스** | Tavily (우선) / 뉴스 API / MCP | 기업의 최근 1-2년 동향, 신사업, 경영 이슈 |
| **인재상** | Tavily + Gemini | Tavily 검색 + Gemini LLM으로 인재상·핵심가치 요약·구조화 |
| **직무 분석** | Gemini (선택) | 지원 직무명 기반 DART+뉴스+인재상 종합 분석 |

## 설치

```bash
conda create -n cl-pipeline python=3.11
conda activate cl-pipeline
pip install -r requirements.txt
```

## 필수 설정 (`.env`)

```bash
# 필수
DART_API_KEY=<OpenDART API 키>
TAVILY_API_KEY=<Tavily API 키>
GEMINI_API_KEY=<Google Gemini API 키>

# 선택 (뉴스 API 폴백)
NEWS_API_ENDPOINT=https://openapi.naver.com/v1/search/news.json
NEWS_API_CLIENT_ID=<네이버 검색 API Client ID>
NEWS_API_CLIENT_SECRET=<네이버 검색 API Secret>

# 선택 (MCP 폴백)
MCP_NEWS_ENDPOINT=<MCP 서버 뉉스 엔드포인트>
MCP_NEWS_AUTH_TOKEN=<MCP 인증 토큰>
```

## 실행

### 기본 실행 (인재상까지)
```bash
python -m src.main "삼성전자"
```

### 직무 분석 포함
```bash
python -m src.main "삼성전자" --job "반도체 공정 엔지니어"
```

### 저장소 경로 커스터마이징
```bash
python -m src.main "삼성전자" --db-dir "./custom_db" --job "직무명"
```

## 출력 파일

### Raw 데이터
- `db/raw/dart/{company}.json` - DART 원본 (연도별 사업내용)
- `db/raw/news/{company}.json` - 뉴스 원본 (20개 기사)
- `db/raw/talent/{company}.json` - 인재상 검색 원본 스니펫

### Processed 결과
- `db/processed/{company}.json` - 통합 결과파일
  ```json
  {
    "company": "기업명",
    "dart_items": [
      { "year": 2025, "business_content": "...", ... },
      { "year": 2024, "business_content": "...", ... },
      { "year": 2023, "business_content": "...", ... }
    ],
    "news_items": [ ... ],
    "talent_profile": {
      "talent_description": "...",
      "core_values": ["...", "...", ...],
      "source_snippets": [...]
    },
    "errors": []
  }
  ```

- `db/processed/gemini/{company}_{job}.json` - 직무별 분석 (--job 사용 시만 생성)
  ```json
  {
    "company": "...",
    "job_title": "...",
    "business_summary": "...",
    "job_relevant_points": [...],
    "recent_issues": [...],
    "talent_alignment": [...],
    "keywords_for_cover_letter": [...]
  }
  ```

## 코드 구조

```
src/
├── main.py                                    CLI 진입점 (argparse)
├── crawling/
│   ├── __init__.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── cover_letter.py                   파이프라인 오케스트레이션 (DART → 뉴스 → 인재상 → Gemini)
│   │   └── gemini_extractor.py               Gemini API 직무분석 모듈 (talent_profile 입력)
│   ├── collectors/
│   │   ├── dart.py                           DART 사업보고서 수집기
│   │   │                                      - _filter_subsections: 최상위 섹션만 추출
│   │   │                                      - _deduplicate_overview: 최신연도만 사업개요 유지
│   │   ├── news.py                           뉴스 수집기 (3개 provider 폴백)
│   │   │                                      1. TavilyNewsProvider (기본)
│   │   │                                      2. ApiNewsProvider (네이버 뉴스 API)
│   │   │                                      3. MCPNewsProvider (MCP 서버)
│   │   └── talent.py                         인재상 수집기 (Tavily + Gemini)
│   │                                          - Tavily로 인재상 관련 스니펫 5개 검색
│   │                                          - Gemini로 요약 + 구조화
│   └── core/
│       ├── config.py                         환경설정 로딩 (.env → Settings dataclass)
│       ├── models.py                         데이터 모델
│       │                                      - DartBusinessContent
│       │                                      - NewsItem
│       │                                      - TalentProfile (talent_description, core_values)
│       │                                      - PipelineResult
│       ├── storage.py                        JSON 저장 로직
│       │                                      - save_dart()
│       │                                      - save_news()
│       │                                      - save_talent()
│       │                                      - save_gemini()
│       └── utils.py                          유틸 (HttpClient, slugify)
```

## 수집 알고리즘

### 1. DART 수집 (`DartCollector`)

1. 기업명 → corp_code 조회 (dart_fss)
2. corp_code로 3개년 사업보고서 검색
3. 각 연도별로 최고 품질 문서 선택 (점수: 문서 길이 + 섹션 명중도 - 페널티)
4. `_filter_subsections()`: 최상위 섹션만 추출
   - **분할 패턴**: `\n\d+\.\s+(?:사업의\s*개요|주요\s*제품|...)`
   - **대상 키워드**: 사업개요, 주요제품·서비스, 주요계약·연구개발
5. `_deduplicate_overview()`: 최신 연도만 사업개요 유지 (중복 제거)

**출력**: `DartBusinessContent` × 3개 (2025, 2024, 2023)

---

### 2. 뉴스 수집 (`NewsCollector`)

`NewsCollector(tavily_provider, api_provider, mcp_provider)` 순차 실행

| 단계 | Provider | 조건 |
|---|---|---|
| 1 | **TavilyNewsProvider** | API 키 있음 → 고급 검색 (최대 20건) |
| 2 | **ApiNewsProvider** | Tavily 실패 + API 설정 있음 → 네이버 검색 API |
| 3 | **MCPNewsProvider** | 1,2 모두 실패 + MCP 엔드포인트 있음 → MCP 폴백 |

**출력**: `NewsItem` × 최대 20개

---

### 3. 인재상 수집 (`TalentCollector`)

**2단계 접근**:

1. **Tavily 검색**
   - 쿼리: `"{기업} 인재상 핵심가치 채용문화"`
   - 검색 깊이: advanced
   - 결과: 스니펫 5개
   
2. **Gemini 요약**
   - 입력: 5개 스니펫
   - 프롬프트: 인재상 요약 + 핵심가치 키워드 추출 요청
   - 출력: JSON (`talent_description`, `core_values`)

**출력**: `TalentProfile` 1개
- `talent_description`: 인재상 요약 (3-5문장)
- `core_values`: 핵심가치 리스트 (최대 8개)
- `source_snippets`: 원본 검색 스니펫

---

### 4. 직무 분석 (`GeminiExtractor`) - 선택사항

**조건**: `--job "직무명"` 전달 + `GEMINI_API_KEY` 설정

**입력**:
- DART 3개년 사업내용 (앞 6000자)
- 뉴스 20개 항목 제목+요약
- **인재상** (talent_description + core_values)
- 지원 직무명

**프롬프트 구성**:
```
1. 인재상 요약 + 핵심가치
2. DART 사업보고서
3. 최신 뉴스
→ 직무 관련 핵심 포인트 추출
```

**출력**: `gemini/{company}_{job}.json`
```json
{
  "business_summary": "사업 요약",
  "job_relevant_points": ["기술/프로젝트 5-8개"],
  "recent_issues": ["최근 이슈 5개"],
  "talent_alignment": ["인재상과의 부합도 5개"],
  "keywords_for_cover_letter": ["자소서 키워드 10개"]
}
```
