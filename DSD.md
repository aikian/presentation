# Design Specification Document (DSD)
# 웹캠 기반 실시간 발표 분석 프로그램

| 항목 | 내용 |
|------|------|
| 종합설계 제목 | 웹캠 기반 실시간 발표 분석 프로그램 |
| 지도교수 | 서영석 |
| 팀장 | 안동규 |
| 팀원 | 김민서, 이보현, 이혜정, 전채현 |
| 주제 분류 | Data, AI |
| 작성일 |  |
| 버전 |  |

---

## 요약문

// 이 문서가 무엇인지 2~3줄 요약
// "PresentAI 각 모듈을 블록 레벨로 분해하여 기능·인터페이스·알고리즘을 정의한다" 방향으로

---

## 목차

1. [서론](#1-서론)
   - 1.1 [개요](#11-개요)
   - 1.2 [범위](#12-범위)
   - 1.3 [용어 정의](#13-용어-정의)
   - 1.4 [설계 제한사항](#14-설계-제한사항)
   - 1.5 [Specification](#15-specification)
2. [시스템 아키텍처](#2-시스템-아키텍처)
   - 2.1 [전체 시스템 구성도](#21-전체-시스템-구성도)
   - 2.2 [계층별 역할 정의](#22-계층별-역할-정의)
   - 2.3 [데이터 흐름 개요](#23-데이터-흐름-개요)
3. [모듈별 DSD](#3-모듈별-dsd)
   - 3.1 [회원 관리 모듈](#31-회원-관리-모듈)
   - 3.2 [발표 환경 설정 모듈](#32-발표-환경-설정-모듈)
   - 3.3 [영상 분석 모듈 (MediaPipe WASM)](#33-영상-분석-모듈-mediapipe-wasm)
   - 3.4 [영상 녹화 및 캡처 모듈](#34-영상-녹화-및-캡처-모듈)
   - 3.5 [AI 코칭 모듈 (Gemini API)](#35-ai-코칭-모듈-gemini-api)
   - 3.6 [슬라이드 관리 모듈](#36-슬라이드-관리-모듈)
   - 3.7 [점수화 알고리즘 모듈](#37-점수화-알고리즘-모듈)
   - 3.8 [PDF 보고서 생성 모듈](#38-pdf-보고서-생성-모듈)
4. [데이터베이스 설계](#4-데이터베이스-설계)
   - 4.1 [ER 다이어그램](#41-er-다이어그램)
   - 4.2 [테이블 스키마](#42-테이블-스키마)
   - 4.3 [Supabase Storage 구조](#43-supabase-storage-구조)
5. [API 명세](#5-api-명세)
   - 5.1 [인증 API](#51-인증-api)
   - 5.2 [발표 세션 API](#52-발표-세션-api)
   - 5.3 [분석 결과 API](#53-분석-결과-api)
   - 5.4 [보고서 API](#54-보고서-api)
6. [프론트엔드 설계](#6-프론트엔드-설계)
   - 6.1 [페이지 구성 및 라우팅](#61-페이지-구성-및-라우팅)
   - 6.2 [상태 관리 설계](#62-상태-관리-설계)
   - 6.3 [주요 컴포넌트 명세](#63-주요-컴포넌트-명세)
7. [테스트 계획](#7-테스트-계획)
   - 7.1 [단위 테스트](#71-단위-테스트)
   - 7.2 [통합 테스트](#72-통합-테스트)
   - 7.3 [성능 기준](#73-성능-기준)
8. [참고 문헌](#8-참고-문헌)

---

## 그림 목차

// 문서 완성 후 채울 것 (그림 번호 / 제목 / 페이지)

---

## 표 목차

// 문서 완성 후 채울 것 (표 번호 / 제목 / 페이지)

---

## 1. 서론

### 1.1 개요

// 프로젝트 한 줄 소개 + 이 문서의 목적 (모듈 분해 기준 문서임을 명시)
// DRD Executive Summary 압축 버전, 2~3문장이면 충분

### 1.2 범위

// 이 문서가 다루는 것 vs 다루지 않는 것을 표로 구분
// 제외 예시: 음성 분석(7월 이후), 모바일 앱, 관리자 페이지

| 포함 | 제외 |
|------|------|
|  |  |

### 1.3 용어 정의

// 본문에 나오는 기술 약어·신조어 정리 — 독자(교수, 팀원)가 모를 만한 것 위주
// 예: Landmark, WASM, EAR, Head Pose, MediaRecorder API, JWT

| 용어 | 정의 |
|------|------|
|  |  |

### 1.4 설계 제한사항

// DRD 2.4 제한조건을 설계 결정과 연결해서 재서술
// 단순 나열 X → "이 제한 때문에 이렇게 설계했다" 형식으로
// 예: 웹캠 깊이 정보 없음 → 전후 흔들림 감지 제외
//     Railway CPU 제한 → Whisper 7월 이후로 연기

### 1.5 Specification

// DRD 2.5 Specification 표 그대로 붙여넣거나 참조 표기로 처리
// "상세 기능 명세는 DRD 2.5를 따른다" 한 줄도 OK

---

## 2. 시스템 아키텍처

### 2.1 전체 시스템 구성도

// ★ 그림 필수 ★
// 클라이언트(Browser) / 백엔드(Railway) / DB(Supabase) 3계층 박스로 구성
// 각 계층 안에 핵심 모듈 이름, 계층 간 통신 방식 화살표로 표기 (HTTPS REST, WASM 등)
// draw.io 또는 Lucidchart 사용 권장

### 2.2 계층별 역할 정의

// 계층 / 담당자 / 기술 스택 / 배포 환경 표로 정리

| 계층 | 담당 | 기술 스택 | 배포 |
|------|------|----------|------|
|  |  |  |  |

### 2.3 데이터 흐름 개요

// ★ 그림 필수 ★
// 웹캠 → MediaPipe → 분석 엔진 → 캡처/버퍼 → 발표 종료 → 백엔드 → Gemini+PDF → Storage → 다운로드
// 화살표마다 데이터 형태 표기 (랜드마크 좌표 / JSON / Base64 이미지 등)

---

## 3. 모듈별 DSD

// 각 모듈은 아래 4가지 항목을 공통으로 채운다
// ① 기능 설명 ② 블록 다이어그램 ③ 입출력 파라미터 ④ 알고리즘

---

### 3.1 회원 관리 모듈

#### 기능 설명

회원 관리 모듈은 사용자 계정의 생성(회원가입), 인증(로그인), 세션 종료(로그아웃) 및 발표 분석 히스토리 조회 기능을 제공한다. 사용자는 안전하게 계정을 관리하고, JWT 기반 인증을 통해 보호된 서비스에 접근할 수 있다.
JWT 방식 채택 이유: 서버 상태를 유지하지 않는 Stateless 구조로 확장성과 보안성이 뛰어나기 때문.

#### 블록 다이어그램
<img width="351" height="145" alt="image" src="https://github.com/user-attachments/assets/1d05e5fc-7069-4392-bedf-6f20a6f1f624" />


// 흐름: 회원가입·로그인 Handler → UserService → JWTService → Supabase(users 테이블)

#### 입출력 파라미터

// 엔드포인트별 입력 / 출력 / 에러 케이스를 표로 정리
// 대상: /auth/signup, /auth/login, /auth/logout, /users/history

| 엔드포인트          | 입력                    | 출력           | 프론트 처리          |
| --------------      | ---------------------   | ------------   | --------------- |
| /auth/signup        | email, password, name   | user           | 성공/실패 메시지 UI    |
| /auth/login         | email, password         | token, user    | 로그인 성공 → 페이지 이동 |
| /auth/logout        | Authorization header    | success        | 상태 초기화          |
| /users/history      | page, size              | history list   | 리스트 렌더링 + 정렬    |


#### 알고리즘

// 비밀번호 해싱 방식 (bcrypt, salt rounds 몇으로 할지)

알고리즘: bcrypt

salt rounds: 12

// JWT payload 구조 (필드명, 만료 시간)
{
  "sub": "user_id",
  
  "email": "user@example.com",
  
  "name": "사용자이름",
  
  "iat": 1717000000,
  
  "exp": 1717086400,
  
  "type": "access"
  
}

exp: 24시간

type: access / refresh 구분

// 토큰 검증 흐름 간략히

클라이언트 요청 (Authorization: Bearer token)
        ↓
JWTService.verifyToken()
        ↓
유효 → 요청 처리
무효 → 401 Unauthorized

---

### 3.2 발표 환경 설정 모듈

#### 기능 설명

// 파일 업로드 → 슬라이드 변환 → Storage 저장 흐름 + 목표 시간 설정 + 웹캠 사전 점검 요약

#### 블록 다이어그램

// 그림 권장
// 흐름: 파일 업로드 → 확장자 분기(PPT/PDF) → 변환(python-pptx / pdf2image) → Storage 저장

#### 입출력 파라미터

// /slides/upload, convert_ppt(), convert_pdf() 각각 입출력을 표로

| 함수 | 입력 | 출력 |
|------|------|------|
|  |  |  |

#### 알고리즘

// 1. 확장자 확인 후 분기
// 2. PPT: python-pptx로 파싱 → PIL 이미지 렌더링
// 3. PDF: pdf2image convert_from_bytes(), DPI 설정값 명시
// 4. Storage 업로드 경로 규칙 — slides/{session_id}/slide_{n}.png

---

### 3.3 영상 분석 모듈 (MediaPipe WASM)

#### 기능 설명

// Hand / Face / Pose 3개 모델 동시 구동 개요
// Web Worker 분리 이유: 메인 스레드 블로킹 방지
// VIDEO 모드 채택 이유: LIVE_STREAM 모드 callback hang 버그 회피

#### 블록 다이어그램

// ★ 그림 필수 ★
// Web Worker 박스 안에 3개 모델 병렬 구조로 표현
// 흐름: 웹캠 VideoFrame → 각 모델 → 지표 계산 엔진 → postMessage → React 메인 스레드

#### 입출력 파라미터

// 분석 지표 17개 전체를 표로 정리
// 표 형식: 번호 / 지표명 / 사용 모델 / 계산 방법 요약 / 단위

| # | 지표명 | 사용 모델 | 계산 방법 | 단위 |
|---|--------|---------|---------|------|
|  |  |  |  |  |

// 아래 두 데이터 구조도 정의할 것
// FrameData: 매 프레임 수집 데이터 (timestamp, 각 지표 raw 값)
// SessionSummary: 발표 종료 시 집계 데이터 (평균·비율·타임스탬프 목록 등)

#### 알고리즘

// 모델 초기화 순서 및 detect_for_video() 호출 루프 방식
// 제스처 판별 조건 — 손가락 굽힘 판정 공식, 10프레임 락, 쿨다운 처리
// 시선 분석 — Head Pose 추정 방법, 정면 응시 판정 조건 (yaw ±15°, pitch ±10°), EAR 공식
// 자세 분석 — 어깨 기울기 공식, 상체 흔들림 계산 (이동평균 표준편차)

---

### 3.4 영상 녹화 및 캡처 모듈

#### 기능 설명

// MediaRecorder API로 전 구간 녹화 + Canvas API로 문제 순간 캡처
// 발표 종료 후 캡처 이미지 Storage 업로드, 원본 영상 삭제 정책 명시

#### 블록 다이어그램

// ★ 그림 필수 ★
// 웹캠 스트림을 두 갈래로 분기: MediaRecorder(녹화) / Canvas(캡처)
// 캡처 트리거 판단 → drawImage() → JPEG 저장 → captureBuffer 누적
// 발표 종료 → stop() → Blob 수집 → Storage 업로드 → 원본 메모리 해제

#### 입출력 파라미터

// 캡처 트리거 임계값 표로 정리
// 표 형식: 지표 / 트리거 조건 / 쿨다운 시간

| 지표 | 트리거 조건 | 쿨다운 |
|------|-----------|--------|
|  |  |  |

#### 알고리즘

// MediaRecorder 초기화 옵션 (mimeType, 비트레이트 등)
// JPEG 압축 품질 설정값
// 발표 종료 처리 순서: stop → Blob 수집 → 이미지 업로드 → 영상 메모리 해제

---

### 3.5 AI 코칭 모듈 (Gemini API)

#### 기능 설명

// 발표 중 호출 없이 종료 후 1회 일괄 호출 방식 채택 이유 (API 호출 제한 고려)
// SessionSummary + 캡처 이미지 → Gemini → 코칭 텍스트 생성 흐름 한 단락

#### 블록 다이어그램

// 그림 권장
// 흐름: 입력(SessionSummary + 캡처 URL) → 프롬프트 빌더 → Gemini API → 응답 파싱 → CoachingResult[]

#### 입출력 파라미터

// CoachingRequest / CoachingResult 데이터 구조 정의
// CoachingResult 필드 예시: category / captureUrl / issue / coaching / improvement

#### 알고리즘

// 프롬프트 구성 방식: System Instruction / 수치 JSON / 이미지 / 출력 포맷 지시 파트별로
// 이미지 전달 방식 결정 (Signed URL vs Base64) + 최대 이미지 수 제한 이유
// API 실패 시 폴백 처리 방식 (재시도 or 규칙 기반 텍스트)

---

### 3.6 슬라이드 관리 모듈

#### 기능 설명

// Storage에서 슬라이드 이미지 로드 → 렌더링 → 제스처 이벤트 수신 → 전환 + 타임스탬프 기록

#### 블록 다이어그램

// 흐름: 슬라이드 이미지 배열 → SlideViewer → 제스처 이벤트 수신 → 인덱스 업데이트 + SlideLog 기록

#### 입출력 파라미터

// initSlides() / nextSlide() / prevSlide() / getSlideTimings() 각 입출력 표
// SlideLog 데이터 구조 정의: slideIndex / enterTime / exitTime / duration

| 함수 | 입력 | 출력 |
|------|------|------|
|  |  |  |

#### 알고리즘

// 슬라이드 전환 시 performance.now()로 타임스탬프 기록
// SlideLog 배열 누적 방식

---

### 3.7 점수화 알고리즘 모듈

#### 기능 설명

// SessionSummary + SlideLog → 카테고리 4개 점수(0~100) + 종합 점수 산출
// 담당: 이보현 / 가중치 근거는 DRD 참고문헌 인용

#### 블록 다이어그램

// 흐름: 입력 데이터 → 시선/자세/제스처/시간 점수 각각 계산 → 가중 합산 → ScoreResult 출력

#### 카테고리 및 가중치

// 표: 카테고리 / 포함 지표 목록 / 가중치

| 카테고리 | 포함 지표 | 가중치 |
|----------|---------|--------|
|  |  |  |

#### 알고리즘

// 카테고리별 점수 계산 공식을 의사코드로 기술
// 정면 응시율 → 점수 변환 방식
// 슬라이드 시간 오차율 → 점수 변환 방식
// 종합 점수 공식: Σ(카테고리 점수 × 가중치)

---

### 3.8 PDF 보고서 생성 모듈

#### 기능 설명
PDF 보고서 생성 모듈은 분석 결과 데이터를 기반으로 시각화된 리포트를 생성하고, 프론트엔드에서는 이를 미리보기 및 다운로드 기능으로 제공한다. 사용자는 리포트를 확인하고 파일로 저장할 수 있다.
// 입력: ScoreResult + CoachingResult[] + SlideLog[]
// 출력: PDF → Supabase Storage 저장 → 다운로드 URL 반환
// 사용 라이브러리: ReportLab (레이아웃) + Matplotlib (그래프)

#### 블록 다이어그램
입력 데이터
(ScoreResult, CoachingResult[], SlideLog[])
        ↓
Matplotlib (차트 생성)
        ↓
ReportLab (PDF 생성)
        ↓
Supabase Storage (업로드)
        ↓
다운로드 URL 반환

// ★ 그림 필수 ★ — PDF 페이지 레이아웃 스케치
// 1페이지: 표지 (점수 요약 + 레이더 차트)
┌──────────────────────────────┐
│ 발표 분석 리포트              │
│                              │
│ 점수 요약 (숫자)              │
│                              │
│      [레이더 차트]            │
│                              │
└──────────────────────────────┘
// 2페이지: 카테고리별 바 차트 + 슬라이드별 시간 그래프
┌──────────────────────────────┐
│ 카테고리별 점수 (바 차트)      │
│                              │
│ 슬라이드별 시간 그래프         │
│                              │
└──────────────────────────────┘
// 3페이지~: 코칭 섹션 반복 (좌: 캡처 이미지 / 우: 코칭 텍스트, 2단 레이아웃)
┌───────────────┬───────────────┐
│  캡처 이미지   │   코칭 텍스트  │
│               │               │
│               │               │
└───────────────┴───────────────┘
// 실제 여백·비율 비례하게 표현하면 구현할 때 훨씬 편함

#### 입출력 파라미터

// 표: 페이지 번호 / 포함 내용 / 사용 라이브러리
| 페이지 | 내용                | 라이브러리                 |
| ---    | -------------       | ---------------------      |
| 1      | 표지 + 레이더 차트   | ReportLab, Matplotlib      |
| 2      | 바 차트 + 시간 그래프 | ReportLab, Matplotlib      |
| 3~N    | 코칭 반복            | ReportLab                  |

#### 알고리즘

// 1. Matplotlib으로 레이더 차트 / 바 차트 / 시간 그래프 PNG 생성
// 2. ReportLab Frame 2개로 2단 레이아웃 구현 (LEFT_FRAME: 이미지, RIGHT_FRAME: 텍스트)
// 3. CoachingResult 수만큼 페이지 반복 추가
// 4. PDF BytesIO 버퍼 → Supabase Storage 업로드

---

## 4. 데이터베이스 설계

### 4.1 ER 다이어그램

// ★ 그림 필수 ★
// 엔티티: users / sessions / analysis_results / reports
// 관계: users 1:N sessions / sessions 1:1 analysis_results / sessions 1:1 reports
// PK, FK, 주요 속성 표기 / draw.io 또는 dbdiagram.io 사용 권장

### 4.2 테이블 스키마

// 각 테이블마다 컬럼명 / 타입 / 제약조건(PK·FK·NOT NULL 등) / 설명 표로 작성

#### users

| 컬럼명 | 타입 | 제약 | 설명 |
|--------|------|------|------|
|  |  |  |  |

#### sessions

| 컬럼명 | 타입 | 제약 | 설명 |
|--------|------|------|------|
|  |  |  |  |

#### analysis_results

| 컬럼명 | 타입 | 제약 | 설명 |
|--------|------|------|------|
|  |  |  |  |

#### reports

| 컬럼명 | 타입 | 제약 | 설명 |
|--------|------|------|------|
|  |  |  |  |

### 4.3 Supabase Storage 구조

// 버킷 구조와 파일 경로 규칙을 트리 형식으로 표현
// RLS 정책 한 줄 요약 포함 — 본인 소유 파일만 접근, 공개 URL 미사용 등

---

## 5. API 명세

// 공통 사항 먼저 명시:
// Base URL / 인증 헤더 형식 / 공통 에러 코드 (400·401·403·404·500)

### 5.1 인증 API

// /auth/signup, /auth/login, /auth/logout
// 가능하면 각 엔드포인트 Request Body / Response Body 예시도 추가

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
|  |  |  |  |

### 5.2 발표 세션 API

// /sessions CRUD + /sessions/{id}/slides 업로드

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
|  |  |  |  |

### 5.3 분석 결과 API

// /sessions/{id}/analysis 저장·조회 + /sessions/{id}/captures 업로드

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
|  |  |  |  |

### 5.4 보고서 API

// POST /sessions/{id}/report → Gemini 호출 + PDF 생성 (처리 시간 김)
// 비동기 처리 방식 사용할지 (polling 방식 등) 결정해서 명시

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
|  |  |  |  |

---

## 6. 프론트엔드 설계

### 6.1 페이지 구성 및 라우팅

// 그림 권장 — 페이지 트리 또는 플로우차트
// 각 경로에 Protected 여부 + 이동 트리거 표기 (로그인 성공, 발표 종료 등)
Landing (/)
   ↓ 로그인
Login (/login)
   ↓ 성공
Dashboard (/dashboard) [Protected]
   ├─ Practice (/practice)
   ├─ Analyze (/analyze)
   ├─ Report (/report)
   ├─ History (/history)
   └─ Profile (/profile)

| 경로         | 페이지명    | 인증 필요 |
| ----------   | -------     | ----- |
| /            | Landing     | X     |
| /login       | 로그인      | X      |
| /dashboard   | 대시보드    | O      |
| /practice    | 발표 연습   | O      |
| /analyze     | 분석        | O     |
| /report      | 보고서      | O      |
| /history     | 히스토리    | O      |

### 6.2 상태 관리 설계

// Context API 4개(Auth / Session / Analysis / Report) 각각의 주요 상태 필드와 역할을 표로

| Context  | 주요 상태 필드                             | 역할           |
| -------- | -----------------------------------------  | ---------       |
| Auth     | user, token, isAuthenticated               | 로그인 상태 관리 |
| Session  | sessionId, isRecording, elapsedTime        | 발표 세션 관리   |
| Analysis | scoreResult, coachingList, slideLogs       | 분석 결과 저장   |
| Report   | reportUrl, isGenerating                    | PDF 상태 관리    |


### 6.3 주요 컴포넌트 명세

// 핵심 컴포넌트 위주로 표 작성
// WebcamAnalyzer / SlideViewer / GestureOverlay / TimerBar / ReportViewer / CoachingCard / RadarChart

| 컴포넌트           | 위치         | 역할         | 주요 Props    |
| --------------    | ----------    | -------       | ----------- |
| WebcamAnalyzer    | /practice     | 영상 분석      | isRecording |
| SlideViewer       | /practice     | 슬라이드 표시  | slides      |
| GestureOverlay    | /practice     | 제스처 표시    | landmarks   |
| TimerBar          | /practice     | 시간 표시      | elapsedTime |
| ReportViewer      | /report       | PDF 표시       | url         |
| CoachingCard      | /analyze      | 코칭 내용      | text        |
| RadarChart        | /dashboard    | 점수 시각화     | data        |


---

## 7. 테스트 계획

### 7.1 단위 테스트

// 모듈별 핵심 로직 테스트 항목과 합격 기준
// 최소 포함: 제스처 정확도 / 점수 경계값 / JWT 검증 / PDF 생성 확인

| 모듈 | 테스트 항목 | 도구 | 합격 기준 |
|------|-----------|------|---------|
|  |  |  |  |

### 7.2 통합 테스트

// 주요 사용자 시나리오 단위로 작성
// 최소 포함: 전체 발표 플로우 (시작~보고서 다운로드) / 제스처 슬라이드 전환 10회 / Gemini 응답 확인

| 시나리오 | 절차 | 합격 기준 |
|---------|------|---------|
|  |  |  |

### 7.3 성능 기준

// 수치로 명확하게 작성
// 최소 포함: MediaPipe 프레임레이트(목표 fps) / 슬라이드 렌더링 시간 / 보고서 생성 시간 / API 응답 시간

| 항목 | 목표 기준 |
|------|---------|
|  |  |

---

## 8. 참고 문헌

// DRD 참고문헌 3편 + 사용 라이브러리 공식 문서
// MediaPipe / Gemini API / FastAPI / Supabase / ReportLab / React / MDN MediaRecorder API

1.
2.
3.
