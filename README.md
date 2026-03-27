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
