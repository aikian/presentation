# 분석 결과 공유 스키마 (v0.1)

발표 1회 분석 = `analysis_results` 레코드 1개. 분석 결과 JSON 전체를 `analysis_results.details` (jsonb) 컬럼에 저장한다.
전체 필드 사전은 협업 계획서 참고: https://claude.ai/code/artifact/a2496648-d191-4fe9-be27-a248aa32fc68

## sample_analysis.json 사용법

`sample_analysis.json`은 **모든 필드가 그럴듯한 가짜 값으로 채워진 20초짜리 발표 1건**이다.
각자 자기 기능은 이 파일을 입력으로 개발·테스트하면 다른 사람 모듈이 완성되길 기다릴 필요가 없다.

- 블록 간 숫자가 서로 맞아떨어지게 만들었다 (예: `silences[]`의 9.5~12.0 구간 → `silence_total_sec: 2.5` → `silence_ratio: 0.13`). 집계 코드 검증용으로 써도 된다.
- `null` 예시 포함: `video_timeline`의 `sec: 8.0` 항목(얼굴 미검출 → gaze/expression null, confidence 0.0), `audio.timeline`의 무음 구간(spm/pitch_hz null), `scores.voice/expression`(미구현 항목).

## 필드 주인

| 블록 | 주인 |
|---|---|
| `meta` | 기존 코드 |
| `video_timeline[].gaze / .expression` | 이보현 |
| `video_timeline[].posture / .gesture` | 김민서 |
| `audio.*` | 안동규 |
| `summary` (gaze·smile·tension) | 이보현 |
| `summary` (posture·gesture) | 김민서 |
| `scores` (산식·가중치) | 김민서 |
| `habits[]` | 김민서 |
| `artifacts` | 생성하는 사람 각자 |

자기 필드만 쓰고, 남의 블록은 읽기 전용. 쓸 때는 기존 JSON을 읽어 자기 블록만 갱신한다.

## 공통 규약 (전 필드 적용)

- **시간**: 모든 시각(`sec`, `start`, `end`)은 영상 시작 = 0초 기준 float 초 (소수 1자리). 리스트는 시간 오름차순.
- **없는 값 = `null`**: 측정 실패·미구현·해당 없음은 전부 `null`. `0`은 "측정된 0"이므로 절대 혼용 금지. 읽는 쪽은 null 방어 필수.
- **숫자 범위**: 비율(`*_ratio`) 0.0–1.0 · 타임라인 내부 `score` 0.0–1.0 · `scores` 블록 점수 0–100 정수 · `confidence` 0.0–1.0.
- **신뢰도 필터**: `confidence < 0.5` 프레임은 집계(`summary`·습관 탐지)에서 제외.
- **표기**: 키는 `snake_case`, UTF-8, enum 값은 소문자 영문.
- **생성 파일**: base64 인라인 금지, Storage 경로(`storage://sessions/{session_id}/파일명`).
- **실험 필드**: 회의 전 임시 필드는 자기 블록 안에 `x_` 접두사로 (예: `x_test_metric`) — 회의에서 승격 또는 삭제.

## 변경 규칙

- 필드 추가·의미 변경은 팀 회의에서 결정하고 `schema_version`을 올린다 (0.1 → 0.2).
- 자기 필드 내부 구조는 주인이 자유롭게 바꾸되, 남이 읽는 필드를 바꿀 땐 미리 공지.
- `weights_version`이 다른 세션끼리는 총점 비교 금지 — 개별 지표(`summary`)로 비교.
