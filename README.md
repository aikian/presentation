# AI Presentation Coach

웹캠으로 발표를 녹화하면 시선, 자세, 표정, 제스처, 음성을 분석해서 점수와 코칭을 돌려주는 발표 연습 서비스입니다.
영남대학교 컴퓨터공학과 종합설계 과목에서 2026년 1년 동안 개발했습니다.

## 주요 기능

- 발표 모드: 슬라이드(PDF, PPT, PPTX)를 띄우고 웹캠으로 녹화합니다. 손동작으로 슬라이드를 넘길 수 있습니다.
- 영상 분석: MediaPipe로 시선 이탈, 자세 기울기, 표정(미소, 긴장), 제스처를 프레임 단위로 측정합니다. 시선은 9분할 히트맵으로 보여줍니다.
- 음성 분석: Whisper로 받아쓰기를 하고 필러워드, 말속도, 침묵 구간, 피치를 계산합니다.
- 점수화: AHP로 정한 가중치로 항목별 점수와 종합 점수를 냅니다. 측정이 불가능한 항목은 0점이 아니라 결측으로 처리합니다.
- 시간축 분석과 습관 탐지: 영상 전체를 시간 순으로 보여주고 반복되는 나쁜 습관을 찾아냅니다.
- AI 코칭: Gemini가 분석 수치를 근거로 개선 코멘트를 작성합니다. PDF 보고서로 내려받을 수 있습니다.
- 롤모델 비교: 유명 연사 영상에서 뽑은 기준값과 내 발표를 비교합니다.
- 청중 집중도 추정: 음성 특징으로 청중이 집중했을 구간을 추정하고, 설문 데이터로 가중치를 보정합니다.
- 발표 이력과 성장 분석: 지난 발표 결과를 모아 점수 변화를 그래프로 보여줍니다.
- 게시판: 발표 영상을 올리고 서로 피드백을 남깁니다.

## 팀원과 역할

| 이름 | 담당 |
|---|---|
| 안동규 (팀장) | 음성 분석, 롤모델 벤치마킹, 배포와 통합 |
| 이혜정 | 음성 특징 추출(피치, 음량, 정적 구간), 청중 집중도 추정, 설문 데이터 분석 |
| 이보현 | 표정 분석, 시선 히트맵, DRD/DSD 문서, 발표 자료 디자인 |
| 김민서 | 시간축 확장, 습관 탐지, AHP 가중치 산출 |
| 전채현 | 발표 이력, 성장 분석, 게시판, 화면 전면 개편 |

모듈마다 담당자가 한 명씩 있습니다. 1학기에는 사람별 프로토타입 브랜치(Prototype_이름)에서, 2학기부터는 기능별 브랜치(feature/, fix/, docs/)에서 작업한 뒤 PR로 main에 합쳤습니다. 커밋 내역은 GitHub의 Insights > Contributors 또는 각 PR에서 확인할 수 있습니다.

## 기술 스택

- 프론트엔드: React 19, Vite, React Router, Recharts
- 백엔드: FastAPI, Python 3.11
- 분석: MediaPipe, OpenCV, faster-whisper, librosa, pandas, scipy
- AI 코칭: Google Gemini API
- 데이터베이스와 스토리지: Supabase (PostgreSQL, Storage)
- 보고서: ReportLab, matplotlib
- 배포: Docker (backend, frontend 각각 Dockerfile 포함)

## 폴더 구조

```
backend/
  app/routers/      API 엔드포인트 (analysis, auth, history, slides, board, audience)
  app/services/     분석 로직 (video_analyzer, audio_analyzer, score_calculator 등)
  app/core/         설정, DB 연결, 인증
  app/middleware/   JWT 인증 미들웨어
  tests/            핵심 지표 계산과 DB 재시도 단위 테스트
frontend/
  src/pages/        화면 (발표 모드, 영상 분석, 결과, 이력, 성장, 게시판, 집중도)
  src/components/   화면 구성 요소
supabase/schema.sql 테이블과 RLS 정의
docs/               분석 결과 스키마, AHP 가중치 근거, 테스트 기록
images/             ER 다이어그램
reference_data/     롤모델 연사 목록과 기준값(speakers.json), 수집·전처리 스크립트 (영상 원본은 용량 때문에 포함하지 않음)
DRD.md, DSD.md      요구사항 정의서, 설계 명세서
```

## 실행 방법

미리 설치할 것: Python 3.11, Node.js 22, ffmpeg(음성 분석), LibreOffice(PPT를 이미지로 변환할 때만 필요)

백엔드

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 값을 채운다
uvicorn app.main:app --reload
```

프론트엔드

```bash
cd frontend
npm install
cp .env.example .env   # 로컬 백엔드면 그대로 두고, 배포 서버면 그 주소 뒤에 /api 를 붙인다
npm run dev
```

브라우저에서 http://localhost:5173 으로 접속합니다. 백엔드는 8000번 포트에서 뜹니다.

필요한 외부 서비스는 Supabase 프로젝트와 Gemini API 키입니다. 테이블은 `supabase/schema.sql`을 Supabase SQL Editor에서 실행하면 만들어집니다. 게시판 영상 저장용으로 Storage 버킷 `presentation-videos`를 하나 만들어 둡니다.

## 문서

- [DRD.md](DRD.md) 요구사항 정의서
- [DSD.md](DSD.md) 설계 명세서
- [docs/schema/README.md](docs/schema/README.md) 분석 결과 JSON 스키마
- [docs/AHP 가중치 산출 근거.md](docs/AHP%20가중치%20산출%20근거.md) 점수 가중치 산출 과정
- [docs/2026-10-19-release-followup.md](docs/2026-10-19-release-followup.md) 상호 테스트 결과와 후속 작업
