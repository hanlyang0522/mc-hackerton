전체 워크플로우

INPUT
회사명 / 직무명 / 질문[] / 글자수[]

↓

[알고리즘] 직무 분석
DART API → 기업 공시 데이터
Tavily 3-angle → 최근성과 / 비전·철학 / 직무·현직자
LLM 요약 1회 → 회사 컨텍스트 블록

↓ (직무 분석 결과가 인풋으로 들어감)

[알고리즘] 소재 선택
질문 키워드 추출
직무 분석에서 나온 역량 키워드 반영
materials.json 기반 가중치 스코어링
전체 질문 일괄 처리 → Set으로 중복 방지

↓

[알고리즘] 글 구조 선택
공통 구조는 모든 질문에 무조건 적용
질문별 keyword 매칭 → 유형 분류
유형 매칭 성공 → 공통 구조 + 유형별 특화 구조 → LLM에 전달
유형 매칭 실패 → 공통 구조만 → LLM에 전달

↓

[LLM] 큰틀 작성
System: writing-rules + CV + activities
User: 회사 컨텍스트 + 소재 데이터 + 글 구조
→ 구조/내용/핵심 팩트 중심으로 작성

↓

사용자 확인 (방향 맞는지 체크)

↓

[LLM] 초안 작성
큰틀 기반으로 표현에 집중
Humanizing instructions 적용
글자수 지시 포함

↓

[알고리즘] QC
글자수 검증 (공백 포함 카운팅)
금지 표현 검사 (keyword includes)
→ 실패 시 LLM 재조정 1회

↓

OUTPUT
완성 자소서 + 검증 리포트
4. 알고리즘 1: 직무 분석
DART API

기업 공시 데이터 (사업보고서, 재무 등)
비상장사/스타트업은 DART 없음 → Tavily로 자동 폴백
Tavily 3-angle 검색


쿼리1: [회사명] 최근 1년 신규 서비스 런칭 수주 MOU 성과
       → 최근 성과, 현재 잘 되는 이유

쿼리2: [회사명] CEO 신년사 경영 철학 비전 인재상 핵심가치
       → 회사 DNA, 원하는 인재

쿼리3: [회사명] [직무명] 직무 현직자 인터뷰 기술블로그 조직문화
       → 실제 직무 내용, 요구 역량
LLM 요약 (1회 호출)


출력 형태:
- 최근 성과 & 시장 위치
- 핵심 가치 & 인재상
- 직무 관련 요구 역량 키워드 (소재 선택 알고리즘 인풋으로 전달)
- 자소서 첫 문장에 쓸 수 있는 구체적 사실 1~2개
5. 알고리즘 2: 소재 선택
materials.json 구조


{
  "id": "petbuddy_troubleshooting",
  "display": "클라우드 기반 앱 서비스 팀 프로젝트 트러블슈팅",
  "activity_key": "petbuddy",
  "capabilities": ["클라우드/인프라", "문제해결력", "AI/ML"],
  "question_types": ["문제해결형", "직무적합성형"],
  "keywords": ["트러블슈팅", "AWS", "아키텍처", "보안", "단계적 해결"],
  "industries": ["IT", "AI", "클라우드", "금융IT"],
  "priority": 1
}
스코어링 공식


score =
  질문 키워드 매칭 × 3
  + 직무분석 역량 키워드 매칭 × 3
  + 질문 유형 매칭 × 2
  + capability 매칭 × 2
  + priority × 1
중복 방지


질문 전체를 배열로 받아 순차 처리
used = new Set()
각 질문마다 최고점 소재 선택
→ used에 이미 있으면 다음 순위 소재 선택
→ used에 추가 후 다음 질문으로
소재 DB
activities.md의 각 항목을 JSON으로 구조화
소재 선택 후 해당 activity_key로 상세 데이터 조회해서 LLM에 전달

6. 알고리즘 3: 글 구조 선택
공통 구조 (모든 질문에 무조건 적용)


- 첫 문장: 구체적 사실/인사이트로 시작. 추상적 포부 금지
- 중간: 내 경험을 근거로, 구체적 상황
- 마지막: 기여 방향 또는 배운 점
- 소재 하나만 중점
- activities에 없는 내용 지어내지 말 것
- 고유명사(프로젝트명 등) 그대로 쓰지 말 것
질문별 구조 (question-types.json)


지원동기형
  흐름: 직무-역량 연결 → 경험 근거 → 기여 방향
  핵심: "너네 회사 이런 곳" 아닌 "이 직무에 이런 역량 필요 → 나는 있다" 흐름
  주의: 첫 문단을 기업 설명으로 시작하지 말 것

직무적합성형
  흐름: 직무 핵심 키워드 2~3개 → 키워드별 경험 매핑 → 기여로 마무리
  핵심: "왜 나인가"를 경험으로 증명
  주의: 단순 나열 금지

문제해결형
  흐름: 상황(구체적 문제) → 판단(왜 그 선택) → 행동(실행) → 결과(변화) → 직무 연결
  핵심: 결과보다 판단 이유가 중요
  주의: 첫 문장 추상적 포부 금지

가치관형
  흐름: 핵심 가치 하나 → 형성된 계기(경험) → 실제 행동 사례 → 현재의 나
  핵심: 연대기 나열 금지. 하나의 가치에서 출발
  주의: "직무에 필요한 역량"으로 마무리하지 말 것

팀워크형
  흐름: 구체적 상황 → 내 판단 → 선택한 행동과 이유 → 팀 전체 결과
  핵심: 장단점 솔직하게 함께 서술
  주의: 나만 잘했다는 식 금지

시사형
  흐름: 현상(구체적 수치/사례) → 본질 분석 → 해결 방향 → 직무 연결
  핵심: 표면적 이슈 아닌 본질로 파고들 것
  주의: 정리된 보고서 느낌 금지
매칭 로직


공통 구조는 항상 포함 (모든 경우)
keyword 매칭 성공 → 공통 구조 + 해당 유형 특화 구조 → LLM 큰틀 작성에 전달
keyword 매칭 실패 → 공통 구조만 → LLM 큰틀 작성에 전달
7. LLM 레이어
System Prompt (고정)

① writing-rules.md 전체
   - 질문 유형별 흐름
   - 금지 표현 목록
   - 문체 원칙
   - 소재 매핑 테이블

② CV.md + activities.md 전체
   - LLM이 "나"를 완전히 이해한 상태

③ 역할 지시
   - activities에 없는 내용 지어내지 말 것
   - 고유명사(PetBuddy 등) 자소서에 직접 쓰지 말 것
   - 공백 포함 글자수 기준 적용
큰틀 작성 LLM 호출

User Prompt 구성:
  [회사 컨텍스트 블록] (직무 분석 결과)
  [질문별]
    질문: "..."
    유형: 문제해결형
    구조: 상황 → 판단 → 행동 → 결과 → 직무연결
    구조 핵심: 판단 이유가 중요
    소재: [activity_key에서 가져온 상세 데이터]

출력:
  질문별 STAR 구조 큰틀
  (내용/구조 중심, 글자수 미적용)
초안 작성 LLM 호출

User Prompt 구성:
  큰틀 내용
  글자수: N자 (공백 포함)
  Humanizing 지시:
    - 긴 문장과 짧은 문장 교차
    - "또한" "결론적으로" "그 결과" 같은 접속사 금지
    - 솔직한 감정 표현 삽입 ("당황했다" "식은땀이 났다")
    - 두괄식/미괄식 혼용

출력:
  완성형 자소서 문단
8. QC 레이어

글자수 검증
→ 공백 포함 직접 카운팅
→ 허용 범위: 목표 글자수 ±100자
→ 실패 시 "N자에 맞춰 조정" LLM 재조정 1회

금지 표현 검사
→ includes() 기반
→ 금지어: 다양한, 확보하다, 도모하다, 발휘하다,
         열심히, 최선을 다해, 노력했습니다,
         첫째/둘째, 또한, 결론적으로, 그 결과
→ 발견 시 해당 표현 포함 문장만 LLM 수정 요청
9. 데이터 구조
materials.json - 소재 메타데이터


[
  {
    "id": "construction_intern",
    "display": "공공기관 정보화지원실 현장실습",
    "activity_key": "construction_intern",
    "capabilities": ["금융IT 실무", "조직 적응력", "백엔드/DB"],
    "question_types": ["지원동기형", "직무적합성형", "팀워크형"],
    "keywords": ["실무", "Java", "DB", "공공기관", "금융", "운영", "조직"],
    "industries": ["금융IT", "공공기관", "SI"],
    "priority": 1
  },
  {
    "id": "petbuddy_troubleshooting",
    "display": "클라우드 기반 앱 서비스 팀 프로젝트 트러블슈팅",
    "activity_key": "petbuddy",
    "capabilities": ["클라우드/인프라", "문제해결력", "AI/ML"],
    "question_types": ["문제해결형", "직무적합성형"],
    "keywords": ["트러블슈팅", "AWS", "아키텍처", "보안", "단계적", "인증서"],
    "industries": ["IT", "AI", "클라우드", "금융IT"],
    "priority": 1
  },
  {
    "id": "storygpt",
    "display": "생성형 AI 웹서비스 기획·개발",
    "activity_key": "storygpt",
    "capabilities": ["기획력/UX", "문제해결력", "AI/ML"],
    "question_types": ["문제해결형", "직무적합성형", "가치관형"],
    "keywords": ["프롬프트", "UX", "사용자", "실험", "반복", "기획"],
    "industries": ["IT", "AI", "콘텐츠", "핀테크"],
    "priority": 2
  },
  {
    "id": "rag_chatbot",
    "display": "법률 도메인 특화 AI 챗봇 개발",
    "activity_key": "rag_chatbot",
    "capabilities": ["AI/ML", "문제해결력", "백엔드/DB"],
    "question_types": ["직무적합성형", "문제해결형"],
    "keywords": ["RAG", "데이터", "파이프라인", "전처리", "LangChain"],
    "industries": ["IT", "AI", "금융IT", "법률"],
    "priority": 2
  },
  {
    "id": "aws_education",
    "display": "AWS 주관 AI 전문 교육과정",
    "activity_key": "aws_education",
    "capabilities": ["AI/ML", "클라우드/인프라"],
    "question_types": ["지원동기형", "직무적합성형"],
    "keywords": ["AWS", "AI", "클라우드", "교육", "실습"],
    "industries": ["IT", "AI", "클라우드"],
    "priority": 2
  },
  {
    "id": "homeserver",
    "display": "개인 홈서버 구축 및 LLM 로컬 운영",
    "activity_key": "homeserver",
    "capabilities": ["클라우드/인프라", "AI/ML"],
    "question_types": ["직무적합성형", "가치관형"],
    "keywords": ["서버", "운영", "Docker", "LLM", "Nginx", "네트워크"],
    "industries": ["IT", "AI", "클라우드"],
    "priority": 3
  },
  {
    "id": "ssafy",
    "display": "삼성전자 주관 소프트웨어 교육과정",
    "activity_key": "ssafy",
    "capabilities": ["임베디드/IoT"],
    "question_types": ["지원동기형", "직무적합성형"],
    "keywords": ["임베디드", "C", "Linux", "ARM", "IoT", "하드웨어"],
    "industries": ["반도체", "제조", "IT"],
    "priority": 2
  },
  {
    "id": "cg_research",
    "display": "컴퓨터 그래픽스 연구실 학부연구생",
    "activity_key": "cg_research",
    "capabilities": ["연구·논문"],
    "question_types": ["가치관형", "직무적합성형"],
    "keywords": ["연구", "논문", "시뮬레이션", "문제의식", "학술"],
    "industries": ["IT", "AI", "연구기관"],
    "priority": 3
  }
]
question-types.json - 유형별 구조


[
  {
    "type": "지원동기형",
    "keywords": ["지원한 이유", "지원 동기", "선택한 이유", "지원하게 된", "왜 당사"],
    "flow": ["직무-역량 연결", "경험 근거", "기여 방향"],
    "core": "이 직무에 이런 역량 필요 → 나는 있다 흐름",
    "caution": "첫 문단을 기업 설명으로 시작하지 말 것. 너네 회사 어떻더라 식 금지"
  },
  {
    "type": "직무적합성형",
    "keywords": ["역량", "강점", "차별점", "직무 경험", "기술"],
    "flow": ["직무 핵심 키워드 2~3개 파악", "키워드별 경험 매핑", "기여로 마무리"],
    "core": "왜 나인가를 경험으로 증명",
    "caution": "단순 나열 금지. 강점 자체로 바로 시작, 직무강점 첫 문장 금지"
  },
  {
    "type": "문제해결형",
    "keywords": ["극복", "어려움", "실패", "도전", "문제", "힘들었던", "위기"],
    "flow": ["상황(구체적 문제)", "판단(왜 그 선택)", "행동(실행)", "결과(변화)", "직무 연결"],
    "core": "결과보다 판단 이유가 중요",
    "caution": "첫 문장 추상적 포부 금지"
  },
  {
    "type": "가치관형",
    "keywords": ["성장", "가치관", "삶의 철학", "나를 표현", "자기소개", "어떤 사람"],
    "flow": ["핵심 가치 하나", "형성된 계기(경험)", "실제 행동 사례", "현재의 나"],
    "core": "연대기 나열 금지. 하나의 가치에서 출발",
    "caution": "직무에 필요한 역량으로 마무리하지 말 것"
  },
  {
    "type": "팀워크형",
    "keywords": ["팀", "협업", "갈등", "설득", "함께", "동료"],
    "flow": ["구체적 상황", "내 판단", "선택한 행동과 이유", "팀 전체 결과"],
    "core": "장단점 솔직하게 함께 서술",
    "caution": "나만 잘했다는 식 금지"
  },
  {
    "type": "시사형",
    "keywords": ["시사", "전망", "트렌드", "업계", "이슈", "사회"],
    "flow": ["현상(구체적 수치/사례)", "본질 분석", "해결 방향", "직무 연결"],
    "core": "표면적 이슈 아닌 본질로 파고들 것",
    "caution": "정리된 보고서 느낌 금지. 고뇌가 묻어나야 함"
  }
]
banned-words.json


[
  "다양한", "확보하다", "도모하다", "발휘하다",
  "열심히 하겠습니다", "최선을 다해", "노력했습니다",
  "첫째", "둘째", "첫 번째", "두 번째",
  "또한", "결론적으로", "그 결과", "이를 통해",
  "누구보다 뛰어난", "꿈을 이루고 싶습니다"
]
10. API 엔드포인트

POST /api/v2/research
  Input:  company, position
  Output: 회사 컨텍스트 블록

POST /api/v2/allocate
  Input:  questions[], company, position, researchResult
  Output: 질문별 { type, structure, material, activityDetail }

POST /api/v2/outline
  Input:  questions[], allocateResult, researchResult
  Output: 질문별 큰틀

POST /api/v2/draft
  Input:  question, outline, maxLength
  Output: 초안

POST /api/v2/qc
  Input:  text, maxLength
  Output: { passed, charCount, bannedWordsFound, adjusted }
11. 사용자 피드백 루프

큰틀 확인 후:
  "소재 바꿔줘"    → allocate 재실행 (해당 질문만)
  "방향 틀었어"   → outline 재실행 (direction 추가)

초안 확인 후:
  "표현 다듬어줘" → draft 재실행 (direction 추가)
  "더 자연스럽게" → draft 재실행 (humanize 강화)
  "글자수 안 맞아" → qc 재실행