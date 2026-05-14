# Design Specification Document (DSD)
# 웹캠 기반 실시간 발표 분석 프로그램

| 항목 | 내용 |
|------|------|
| 종합설계 제목 | 웹캠 기반 실시간 발표 분석 프로그램 |
| 지도교수 | 서영석 |
| 팀장 | 안동규 |
| 팀원 | 김민서, 이보현, 이혜정, 전채현 |
| 주제 분류 | Data, AI |
| 작성일 | 2026년 5월 7일 |
| 버전 | 0.1 DSD 초안 |

---

## 요약문

본 문서는 웹캠 기반 실시간 발표 분석 프로그램의 설계 명세서로, DRD에서 정의한 요구사항을 시스템 계층, 모듈, 데이터 흐름, 입출력 인터페이스, 핵심 알고리즘 단위로 구체화한다.
특히 클라이언트에서 실행되는 MediaPipe WASM 분석 구조와 발표 종료 후 Gemini API를 활용한 AI 코칭 생성 흐름을 명확히 정의하여 구현 단계의 기준 문서로 사용한다.

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

// 점검 메모: DRD 내용과 표현이 어긋나지 않는지, 제외 범위(음성 분석·모바일·관리자 페이지)가 팀 방향과 맞는지 확인한다.
// 용어 정의가 교수님도 이해 가능한 수준인지, 설계 제한사항이 "제한 → 설계 반영" 구조로 자연스러운지 점검한다.

### 1.1 개요

본 프로젝트는 노트북 웹캠만으로 발표자의 시선, 자세, 제스처를 실시간 분석하고, 발표 종료 후 문제 순간 캡처 이미지와 AI 코칭 텍스트가 포함된 PDF 보고서를 생성하는 PC용 웹 애플리케이션이다.
본 DSD는 DRD의 요구사항을 실제 구현 가능한 설계 단위로 분해하여 각 모듈의 책임, 입출력 데이터, 내부 알고리즘, 외부 시스템 연동 방식을 정의한다.
문서의 설계 기준은 1차 프로토타입 제출 범위에 맞추며, 음성 분석처럼 일정상 후순위인 기능은 확장 항목으로 분리한다.

### 1.2 범위

| 포함 | 제외 |
|------|------|
| PC 웹 브라우저 기반 발표 분석 웹 애플리케이션 설계 | 모바일 앱 및 태블릿 전용 UI |
| React 클라이언트, FastAPI 백엔드, Supabase DB/Storage 3계층 구조 | 관리자 페이지, 기관 관리 콘솔 |
| MediaPipe WASM 기반 시선·자세·제스처 분석 구조 | 음성 분석 및 Whisper 기반 전사 기능(7월 이후 고도화) |
| 발표 슬라이드 제어, 영상 녹화, 문제 순간 캡처 연동 방식 | 다중 발표자 동시 분석, 실시간 협업 발표 |
| Gemini API 기반 발표 종료 후 AI 코칭 생성 방식 | 발표 중 실시간 AI 호출 및 실시간 음성 코칭 |
| PDF 보고서 생성을 위한 분석 결과 전달 구조 | 상용 결제, 구독, 라이선스 관리 기능 |

### 1.3 용어 정의

| 용어 | 정의 |
|------|------|
| Landmark | MediaPipe 모델이 얼굴, 손, 몸의 주요 지점을 정규화 좌표로 추출한 값이다. |
| WASM(WebAssembly) | 브라우저에서 네이티브에 가까운 속도로 모델 추론 코드를 실행하기 위한 바이너리 실행 형식이다. |
| MediaPipe Tasks | Google MediaPipe에서 제공하는 Face Landmarker, Hand Landmarker, Pose Landmarker 등 고수준 비전 추론 API 묶음이다. |
| Web Worker | 브라우저 메인 스레드와 분리된 백그라운드 스레드로, 영상 분석 작업이 UI 렌더링을 막지 않도록 사용한다. |
| VIDEO 모드 | MediaPipe 모델 호출 시 프레임과 타임스탬프를 직접 전달하는 동영상 처리 모드이다. |
| Head Pose | 얼굴 랜드마크를 기반으로 발표자의 머리 방향을 yaw, pitch, roll 각도로 추정한 값이다. |
| EAR(Eye Aspect Ratio) | 눈 주변 랜드마크 간 거리 비율로 눈 깜빡임 또는 눈 감김을 판단하는 지표이다. |
| FrameData | 매 프레임에서 추출한 분석 원시값과 이벤트를 담는 클라이언트 내부 데이터 구조이다. |
| SessionSummary | 발표 종료 시 FrameData를 집계하여 평균, 비율, 문제 타임스탬프, 캡처 목록으로 정리한 데이터 구조이다. |
| Signed URL | Supabase Storage의 비공개 파일에 제한된 시간 동안 접근할 수 있도록 발급하는 임시 URL이다. |
| Gemini API | 분석 수치와 캡처 이미지를 입력으로 받아 발표 코칭 텍스트를 생성하는 생성형 AI API이다. |

### 1.4 설계 제한사항

DRD의 현실적 제한조건은 다음 설계 결정에 반영한다. 제한사항은 단순히 기능을 줄이는 기준이 아니라, 프로토타입 단계에서 안정적으로 동작하는 범위를 정하는 기준으로 사용한다.

| 제한사항 | 설계 반영 |
|----------|-----------|
| 노트북 웹캠은 720p, 30fps, 고정 앵글, 깊이 정보 없음 | 3D 공간 분석이 아닌 2D 랜드마크 기반 상반신 분석으로 제한하고, 전후 방향 흔들림은 평가 항목에서 제외한다. |
| 조명과 카메라 위치에 따라 인식률 저하 가능 | 발표 시작 전 웹캠·조명 점검 단계를 두고, 모델 confidence가 낮은 프레임은 집계에서 제외한다. |
| MediaPipe 3개 모델 동시 구동 시 브라우저 부하 발생 가능 | Face, Hand, Pose 추론을 Web Worker에서 실행하고, 필요 시 분석 프레임레이트를 15~20fps로 제한한다. |
| Railway 백엔드 CPU 자원 제한 | 실시간 영상 추론은 클라이언트에서 수행하고, 백엔드는 세션 저장, Gemini 호출, PDF 생성처럼 발표 종료 후 처리에 집중한다. |
| Gemini API 호출 제한 및 응답 지연 | 발표 중에는 API를 호출하지 않고, 발표 종료 후 SessionSummary와 선별된 캡처 이미지를 묶어 1회 일괄 호출한다. |
| 개인정보 보호 필요 | 원본 녹화 영상은 보고서 생성 후 삭제하고, 보고서에는 문제 순간 캡처 이미지와 집계값만 저장한다. |
| 다중 사용자 동시 세션 미지원 | 1인 1세션 구조로 설계하고, 세션 데이터는 user_id 기준으로 분리한다. |
| 음성 분석은 7월 이후 고도화 항목 | 1차 DSD의 핵심 데이터 구조에는 음성 전사·필러워드 분석을 포함하지 않는다. |

### 1.5 Specification

상세 기능 명세는 DRD 2.5 Specification을 기준으로 하며, 본 DSD에서는 이를 구현 관점의 모듈 책임으로 재구성한다.

| 분야 | DSD 설계 대응 |
|------|---------------|
| 사용자 관리 | JWT 기반 인증, 사용자별 발표 세션 및 보고서 조회 구조 |
| 발표 실행 | PPT/PDF 업로드, 목표 발표 시간 설정, 슬라이드 이미지 로딩 구조 |
| 영상 분석 | MediaPipe Face/Hand/Pose 모델을 Web Worker에서 실행하고 FrameData로 집계 |
| 영상 녹화 및 캡처 | MediaRecorder와 Canvas 캡처를 분석 이벤트와 연결 |
| AI 피드백 | SessionSummary와 캡처 이미지를 Gemini API 입력으로 변환 |
| 보고서 생성 | ScoreResult, CoachingResult, SlideLog를 PDF 생성 모듈로 전달 |
| 시스템 환경 | React, FastAPI, Supabase, Vercel, Railway 기반 3계층 배포 구조 |

---

## 2. 시스템 아키텍처

// 점검 메모: Mermaid 다이어그램을 최종본에서 draw.io 그림으로 바꿀지, 담당자/역할 표가 실제 팀 분담과 맞는지 확인한다.
// 영상 원본을 서버로 보내지 않는 구조와 Supabase·Railway·Vercel 사용 전제가 팀 결정과 일치하는지 점검한다.

### 2.1 전체 시스템 구성도

그림 1은 1차 프로토타입 기준 전체 시스템 구성도 초안이다. 실제 제출 문서에서는 동일 구조를 draw.io 또는 Lucidchart 그림으로 변환한다.

```mermaid
flowchart LR
    subgraph Client["Client: Browser / React"]
        Webcam["Webcam Stream"]
        SlideViewer["SlideViewer"]
        GestureWorker["GestureWorker<br/>Hand Landmarker 전용<br/>(발표 중 실시간)"]
        Recorder["MediaRecorder<br/>녹화 Blob"]
        VideoAnalyzer["VideoAnalyzer<br/>Face + Pose + Hand<br/>(발표 후 오프라인)"]
        Analysis["Analysis Engine<br/>FrameData / SessionSummary"]
        UI["React UI + Context"]
    end

    subgraph Backend["Backend: FastAPI / Railway"]
        API["REST API Router"]
        SessionSvc["Session Service"]
        ReportSvc["Report Service"]
        GeminiSvc["Gemini Client"]
        PdfSvc["PDF Generator"]
    end

    subgraph Supabase["Supabase"]
        DB["PostgreSQL"]
        Storage["Storage"]
    end

    Webcam --> GestureWorker
    Webcam --> Recorder
    GestureWorker -- "슬라이드 제어 이벤트" --> SlideViewer
    GestureWorker --> UI
    Recorder -- "녹화 Blob URL<br/>(분석하기 버튼 클릭)" --> VideoAnalyzer
    VideoAnalyzer --> Analysis
    Analysis --> UI
    SlideViewer --> UI
    UI -- "HTTPS REST / JSON" --> API
    API --> SessionSvc
    API --> ReportSvc
    SessionSvc -- "CRUD" --> DB
    SessionSvc -- "slide/capture upload" --> Storage
    ReportSvc --> GeminiSvc
    ReportSvc --> PdfSvc
    GeminiSvc -- "CoachingResult JSON" --> ReportSvc
    PdfSvc -- "report.pdf" --> Storage
    ReportSvc -- "report metadata" --> DB
```

발표 중에는 GestureWorker(Hand Landmarker 전용)만 실시간으로 실행하여 슬라이드 제어에 사용하고, 나머지 Face·Pose·Hand 분석 지표는 발표 종료 후 "분석하기" 버튼 클릭 시 VideoAnalyzer가 녹화 영상을 입력받아 처리한다. 영상 프레임 원본은 서버에 전송하지 않으며, 서버로 전송되는 데이터는 발표 종료 후의 집계 JSON, 캡처 이미지, 슬라이드 로그, 보고서 생성 요청으로 제한한다.

### 2.2 계층별 역할 정의

| 계층 | 담당 | 기술 스택 | 배포 |
|------|------|----------|------|
| 클라이언트 UI | 전채현, 안동규(분석 연동) | React, Context API, WebRTC getUserMedia, Canvas API | Vercel |
| 영상 분석 Worker | 안동규 | MediaPipe Tasks Vision, WASM, Web Worker, requestVideoFrameCallback | 브라우저 내 실행 |
| 백엔드 API | 김민서, 이혜정 | FastAPI, Pydantic, JWT, Supabase SDK | Railway |
| AI 코칭 처리 | 안동규 | Gemini API, 프롬프트 빌더, JSON 응답 파서 | Railway 백엔드 내부 |
| 보고서 생성 | 전채현, 김민서 | ReportLab, Matplotlib, BytesIO | Railway 백엔드 내부 |
| 데이터베이스 | 이혜정 | Supabase PostgreSQL, Row Level Security | Supabase |
| 파일 저장소 | 이혜정 | Supabase Storage, Signed URL, 비공개 버킷 | Supabase |

### 2.3 데이터 흐름 개요

그림 2는 발표 시작부터 보고서 다운로드까지의 핵심 데이터 흐름이다. 흐름은 발표 중 1단계와 발표 후 2단계로 분리된다.

**1단계: 발표 중**

```mermaid
flowchart TD
    A["웹캠 입력<br/>MediaStream"] --> B["GestureWorker<br/>Hand Landmarker 전용"]
    A --> C["MediaRecorder<br/>녹화 Blob 축적"]
    B --> D["슬라이드 제어 이벤트<br/>next / prev"]
    D --> E["SlideViewer<br/>슬라이드 전환 + SlideLog 기록"]
```

**2단계: 발표 후 ("분석하기" 버튼 클릭)**

```mermaid
flowchart TD
    A["녹화 Blob URL<br/>HTMLVideoElement 로드"] --> B["VideoAnalyzer<br/>Face + Pose + Hand Landmarker"]
    B --> C["분석 엔진<br/>FrameData JSON"]
    C --> D["문제 순간 판단<br/>timestamp + reason"]
    D --> E["Canvas 캡처<br/>JPEG Blob"]
    C --> F["발표 종료 집계<br/>SessionSummary JSON"]
    E --> G["Supabase Storage<br/>capture JPEG"]
    F --> H["FastAPI 보고서 요청<br/>summary + capture metadata"]
    G --> H
    H --> I["Gemini API<br/>summary JSON + image data"]
    I --> J["CoachingResult[]"]
    J --> K["PDF Generator<br/>PDF BytesIO"]
    K --> L["Supabase Storage<br/>report.pdf"]
    L --> M["다운로드 URL 반환"]
```

| 단계 | 데이터 형태 | 저장 위치 | 비고 |
|------|-------------|-----------|------|
| 웹캠 입력 | MediaStream / VideoFrame | 클라이언트 메모리 | 외부 전송 없음 |
| 제스처 추론 | Hand landmark 배열 | GestureWorker 메모리 | 발표 중 실시간, 슬라이드 제어 전용 |
| 녹화 영상 | MediaRecorder Blob | 클라이언트 메모리 | 발표 종료 후 VideoAnalyzer 입력으로 사용 |
| 랜드마크 추론 | Face/Hand/Pose landmark 배열 | VideoAnalyzer 메모리 | 발표 후 오프라인, 프레임 단위 처리 후 원본 폐기 |
| 프레임 분석값 | FrameData JSON | 클라이언트 임시 버퍼 | timestamp 기준으로 누적 |
| 문제 순간 캡처 | JPEG Blob | Supabase Storage | 보고서 근거 이미지로 사용 |
| 발표 집계 | SessionSummary JSON | PostgreSQL analysis_results | 평균, 비율, 이벤트 타임라인 |
| AI 코칭 결과 | CoachingResult[] JSON | PostgreSQL analysis_results 또는 reports | Gemini 응답 파싱 결과 |
| 최종 보고서 | PDF 파일 | Supabase Storage | 다운로드 URL 반환 |

---

## 3. 모듈별 DSD

// 각 모듈은 아래 4가지 항목을 공통으로 채운다
// ① 기능 설명 ② 블록 다이어그램 ③ 입출력 파라미터 ④ 알고리즘

---

### 3.1 회원 관리 모듈

#### 기능 설명

// 회원가입 / 로그인 / 로그아웃 / 히스토리 조회 기능 한 단락 요약
// JWT 방식 채택 이유 한 줄 추가

#### 블록 다이어그램

// 그림 권장
// 흐름: 회원가입·로그인 Handler → UserService → JWTService → Supabase(users 테이블)
// 각 블록에 주요 함수명 적어둘 것

#### 입출력 파라미터

// 엔드포인트별 입력 / 출력 / 에러 케이스를 표로 정리
// 대상: /auth/signup, /auth/login, /auth/logout, /users/history

| 엔드포인트 | 입력 | 출력 | 에러 |
|-----------|------|------|------|
|  |  |  |  |

#### 알고리즘

// 비밀번호 해싱 방식 (bcrypt, salt rounds 몇으로 할지)
// JWT payload 구조 (필드명, 만료 시간)
// 토큰 검증 흐름 간략히

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

// 점검 메모: 분석 지표 17개와 임계값(yaw ±15도, pitch ±10도, 10프레임 유지, 1초 쿨다운)이 적절한지 확인한다.
// 손 제스처 매핑, 상체 앞쏠림 표현, FrameData/SessionSummary 구조가 다른 담당 파트와 연결되기 쉬운지 점검한다.

#### 기능 설명

영상 분석 모듈은 역할에 따라 GestureWorker와 VideoAnalyzer 두 가지로 분리된다.

**GestureWorker(발표 중 실시간):** 발표 중에는 Hand Landmarker만 실시간으로 구동하여 손 제스처를 인식하고 슬라이드 제어 이벤트를 생성한다. Face·Pose 분석은 수행하지 않아 브라우저 부하를 최소화한다.

**VideoAnalyzer(발표 후 오프라인):** 발표 종료 후 사용자가 "분석하기" 버튼을 클릭하면 VideoAnalyzer가 녹화 영상 Blob URL을 입력으로 받아 Face Landmarker, Pose Landmarker, Hand Landmarker를 순서대로 실행한다. 발표자의 시선, 자세, 제스처 관련 17개 지표를 프레임 단위로 계산하고 SessionSummary로 집계한다.

MediaPipe 호출 방식은 두 컴포넌트 모두 `VIDEO` 모드를 사용하며 프레임 타임스탬프를 명시적으로 전달한다. VideoAnalyzer의 경우 입력 소스는 실시간 웹캠 스트림이 아닌 녹화된 Blob URL을 HTMLVideoElement에 로드한 것이다.

공식 문서 확인 결과, MediaPipe Web 태스크의 `detect()`와 `detectForVideo()` 호출은 동기적으로 실행되어 UI 스레드를 블로킹할 수 있으므로 Web Worker 분리 설계가 필요하다. 또한 Hand Landmarker는 손당 21개 랜드마크와 handedness를 제공하고, Face Landmarker는 얼굴 랜드마크·blendshape·facial transformation matrix를 제공하며, Pose Landmarker는 자세 랜드마크와 world landmark를 제공한다. 본 모듈은 이 출력값 중 발표 분석에 직접 필요한 값만 FrameData로 축약한다.

| 모델 | 사용 시점 | 공식 출력 | 본 프로젝트 사용 값 |
|------|----------|-----------|---------------------|
| Hand Landmarker | 발표 중 실시간 (GestureWorker) | 손 랜드마크 21개, handedness, world landmark | 왼손/오른손 구분, 주먹/손바닥 제스처 → 슬라이드 제어 |
| Face Landmarker | 발표 후 오프라인 (VideoAnalyzer) | 얼굴 랜드마크, blendshape, facial transformation matrix | yaw/pitch, 정면 응시 여부, EAR, 깜빡임 |
| Hand Landmarker | 발표 후 오프라인 (VideoAnalyzer) | 손 랜드마크 21개, handedness, world landmark | 손 움직임 속도, 양손 대칭성 분석 지표 |
| Pose Landmarker | 발표 후 오프라인 (VideoAnalyzer) | 자세 랜드마크, world landmark | 어깨 기울기, 상체 중심, 상체 흔들림 |

초기 설정값은 1차 프로토타입 기준으로 다음과 같이 둔다.

| 항목 | 설정값 | 이유 |
|------|--------|------|
| runningMode | `VIDEO` | 프레임 timestamp를 직접 관리하고 동기 추론 결과를 일관되게 수집한다. VideoAnalyzer는 Blob URL 기반 HTMLVideoElement를 입력 소스로 사용한다. |
| numFaces / numHands / numPoses | 얼굴 1명, 손 2개, 자세 1명 | DRD의 1인 1세션 조건과 일치한다. |
| confidence threshold | 기본 0.5부터 시작, 테스트 후 조정 | 공식 기본값을 기준으로 조명·웹캠 환경 테스트 결과에 따라 보정한다. |
| 분석 fps (VideoAnalyzer) | 목표 15~20fps | 녹화 영상 전체를 처리할 때 CPU 사용량을 줄이기 위해 프레임 샘플링을 적용한다. |

#### 블록 다이어그램

```mermaid
flowchart LR
    Webcam["Webcam Stream"]
    RecordedBlob["녹화 Blob URL<br/>(발표 후)"]

    subgraph GW["GestureWorker (발표 중 실시간)"]
        HandRT["Hand Landmarker"]
        GestureJudge["제스처 판별<br/>fist / open / none"]
    end

    subgraph VA["VideoAnalyzer (발표 후 오프라인)"]
        FaceOff["Face Landmarker<br/>Head Pose / EAR"]
        HandOff["Hand Landmarker<br/>Velocity / Symmetry"]
        PoseOff["Pose Landmarker<br/>Shoulder / Torso"]
        Metric["Metric Calculator<br/>17 indicators"]
        Buffer["FrameData Buffer"]
    end

    Webcam --> HandRT
    HandRT --> GestureJudge
    GestureJudge -- "슬라이드 제어 이벤트" --> SlideControl["SlideViewer"]

    RecordedBlob --> FaceOff
    RecordedBlob --> HandOff
    RecordedBlob --> PoseOff
    FaceOff --> Metric
    HandOff --> Metric
    PoseOff --> Metric
    Metric --> Buffer
    Buffer -- "postMessage(FrameData)" --> Main["React Main Thread"]
    Main --> Summary["SessionSummary 집계"]
    Main --> Capture["Capture Trigger"]
```

#### 입출력 파라미터

| # | 지표명 | 사용 모델 | 계산 방법 | 단위 |
|---|--------|---------|---------|------|
| 1 | 얼굴 검출 신뢰도 | Face Landmarker | 얼굴 landmark confidence 평균 | 0~1 |
| 2 | yaw 각도 | Face Landmarker | 얼굴 기준점의 좌우 회전 추정값 | degree |
| 3 | pitch 각도 | Face Landmarker | 얼굴 기준점의 상하 회전 추정값 | degree |
| 4 | 정면 응시 여부 | Face Landmarker | `abs(yaw) <= 15` 및 `abs(pitch) <= 10` | boolean |
| 5 | 시선 좌우 편향 | Face Landmarker | yaw 평균값의 부호와 크기로 좌/우 편향 계산 | degree |
| 6 | 시선 분산도 | Face Landmarker | 최근 N프레임 yaw/pitch 표준편차 | degree |
| 7 | EAR | Face Landmarker | 눈 세로 거리 합 / 눈 가로 거리 | ratio |
| 8 | 눈 깜빡임 횟수 | Face Landmarker | EAR이 임계값 이하로 내려갔다가 회복되는 이벤트 카운트 | count |
| 9 | 어깨 기울기 | Pose Landmarker | 좌우 어깨 좌표의 기울기 `atan2(dy, dx)` | degree |
| 10 | 상체 중심 X | Pose Landmarker | 좌우 어깨와 좌우 골반 중심의 평균 X 좌표 | normalized |
| 11 | 상체 중심 Y | Pose Landmarker | 좌우 어깨와 좌우 골반 중심의 평균 Y 좌표 | normalized |
| 12 | 상체 흔들림 | Pose Landmarker | 최근 N프레임 상체 중심 좌표의 이동평균 표준편차 | normalized |
| 13 | 상체 앞쏠림 추정 | Pose Landmarker | 어깨 중심과 골반 중심의 상대 위치 변화량 | normalized |
| 14 | 왼손 제스처 | Hand Landmarker | 손가락 굽힘 상태 기반 `fist/open/none` 판정 | enum |
| 15 | 오른손 제스처 | Hand Landmarker | 손가락 굽힘 상태 기반 `fist/open/none` 판정 | enum |
| 16 | 손 움직임 속도 | Hand Landmarker | 손목 좌표의 프레임 간 이동거리 / 시간차 | normalized/sec |
| 17 | 양손 대칭성 | Hand/Pose Landmarker | 양손 위치와 어깨 중심 간 거리 차이의 절댓값 | normalized |

`FrameData`는 매 분석 프레임에서 생성되는 원시 데이터 구조이다.

```text
FrameData {
  timestampMs: number
  face: {
    confidence: number
    yawDeg: number
    pitchDeg: number
    frontGaze: boolean
    gazeDispersionDeg: number
    ear: number
    blinkEvent: boolean
  }
  pose: {
    shoulderTiltDeg: number
    torsoCenterX: number
    torsoCenterY: number
    torsoSway: number
    forwardLean: number
  }
  hand: {
    leftGesture: "fist" | "open" | "none"
    rightGesture: "fist" | "open" | "none"
    handVelocity: number
    bilateralSymmetry: number
  }
  events: string[]
}
```

`SessionSummary`는 발표 종료 시 FrameData를 집계한 결과이며 AI 코칭, 점수화, PDF 보고서 생성의 공통 입력으로 사용한다.

```text
SessionSummary {
  sessionId: string
  durationSec: number
  frameCount: number
  frontGazeRatio: number
  avgYawDeg: number
  avgPitchDeg: number
  blinkCount: number
  avgShoulderTiltDeg: number
  torsoSwayAvg: number
  gestureCounts: { leftFist: number, rightFist: number, openPalm: number }
  issueEvents: Array<{ timestampMs: number, category: string, reason: string, severity: number }>
  captureIds: string[]
}
```

#### 알고리즘

1. 모델 초기화
   - **GestureWorker(발표 중):** 클라이언트가 웹캠 권한을 획득하면 GestureWorker를 생성한다. Worker는 MediaPipe Vision WASM 리소스를 로드한 뒤 `HandLandmarker`만 `runningMode: "VIDEO"`로 초기화한다. 메인 스레드는 `requestVideoFrameCallback` 또는 동등한 타이머로 웹캠 프레임과 타임스탬프를 Worker에 전달하고, Worker는 제스처 판별 결과를 슬라이드 제어 이벤트로 반환한다.
   - **VideoAnalyzer(발표 후):** 사용자가 "분석하기" 버튼을 클릭하면 VideoAnalyzer Worker를 생성한다. Worker는 `FaceLandmarker`, `HandLandmarker`, `PoseLandmarker`를 순서대로 초기화한다. 메인 스레드는 녹화 Blob URL을 HTMLVideoElement에 로드하고, 프레임 단위로 `detectForVideo()`를 호출하여 타임스탬프와 함께 전달한다. 세 모델 추론 결과가 모두 도착하면 동일 timestamp 기준으로 하나의 FrameData를 생성한다.

2. 제스처 판별
   - 손가락 i에 대해 `fingerCurl_i = distance(tip_i, wrist) / distance(mcp_i, wrist)`로 굽힘 정도를 계산한다.
   - 엄지를 제외한 네 손가락의 `fingerCurl_i`가 기준값보다 작으면 해당 손가락을 접힌 상태로 본다.
   - 접힌 손가락이 4개 이상이면 `fist`, 펴진 손가락이 4개 이상이면 `open`, 그 외는 `none`으로 판정한다.
   - 동일 제스처가 10프레임 이상 유지될 때만 슬라이드 제어 이벤트를 발생시키고, 이벤트 발생 후 1초 쿨다운을 적용한다.
   - 왼손 `fist`는 이전 슬라이드, 오른손 `fist`는 다음 슬라이드, `open`은 레이저 포인터 후보 입력으로 전달한다.

3. 시선 분석
   - Face Landmarker의 코, 양 눈가, 얼굴 윤곽 기준점을 이용해 Head Pose의 yaw, pitch를 추정한다.
   - `abs(yaw) <= 15`이고 `abs(pitch) <= 10`이면 정면 응시 프레임으로 분류한다.
   - 시선 분산도는 최근 N프레임의 yaw, pitch 표준편차로 계산한다.
   - EAR은 `(||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)`로 계산하며, 임계값 이하로 내려간 뒤 회복되는 순간을 깜빡임 이벤트로 기록한다.

4. 자세 분석
   - 어깨 기울기는 `atan2(rightShoulder.y - leftShoulder.y, rightShoulder.x - leftShoulder.x)`로 계산한다.
   - 상체 중심은 좌우 어깨와 좌우 골반 중심점의 평균 좌표로 정의한다.
   - 상체 흔들림은 최근 N프레임 상체 중심 좌표에 대한 이동평균 표준편차로 계산한다.
   - confidence가 낮거나 필수 landmark가 누락된 프레임은 결측 프레임으로 표시하고 평균 계산에서 제외한다.

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

// 점검 메모: Gemini를 발표 종료 후 1회 호출하는 방식, 캡처 이미지 최대 5개 제한, Base64 inlineData 방식이 팀 방향과 맞는지 확인한다.
// CoachingResult 필드가 PDF 보고서에 충분한지, API 실패 시 규칙 기반 fallback 문구가 필요한지 점검한다.

#### 기능 설명

AI 코칭 모듈은 발표 종료 후 `SessionSummary`와 문제 순간 캡처 이미지를 바탕으로 Gemini API를 호출하여 행동 개선 중심의 코칭 텍스트를 생성한다.
발표 중에는 Gemini API를 호출하지 않고, 발표 종료 후 1회 일괄 호출하는 방식을 채택한다. 이는 발표 중 지연을 없애고, API 호출 제한과 비용을 줄이며, 전체 발표 맥락을 반영한 코칭을 생성하기 위한 설계이다.
Gemini 응답은 `CoachingResult[]` 구조로 파싱되어 PDF 보고서와 결과 화면에서 공통으로 사용된다.

추가 조사 기준으로 Gemini API는 텍스트와 이미지를 함께 입력하는 multimodal prompting을 지원하고, 작은 이미지는 Base64 `inlineData`로 직접 전달할 수 있다. 또한 `response_mime_type: application/json`과 JSON Schema를 이용한 structured output을 지원하므로, 코칭 결과는 자연어를 다시 파싱하는 방식이 아니라 명시적 스키마를 따르는 JSON 배열로 받는다.

| 설계 항목 | 결정 |
|-----------|------|
| 호출 시점 | 발표 종료 후 1회 일괄 호출 |
| 모델 후보 | Gemini 2.5 Flash 계열, structured output 지원 모델 사용 |
| 이미지 입력 | 캡처 JPEG를 5개 이하로 선별 후 Base64 `inlineData`로 전달 |
| 출력 형식 | `CoachingResult[]` JSON Schema 기반 structured output |
| 검증 방식 | Pydantic 모델로 JSON 필드와 enum 값을 검증 후 저장 |

#### 블록 다이어그램

```mermaid
flowchart LR
    Summary["SessionSummary JSON"] --> Selector["Issue Selector<br/>top N captures"]
    Captures["Capture Metadata<br/>Storage path / signed URL"] --> Selector
    Selector --> Builder["Prompt Builder<br/>system + metrics + images"]
    Builder --> Gemini["Gemini API"]
    Gemini --> Parser["JSON Response Parser"]
    Parser --> Validator["Schema Validator"]
    Validator --> Result["CoachingResult[]"]
    Validator -- "invalid or failed" --> Fallback["Rule-based fallback text"]
    Fallback --> Result
```

#### 입출력 파라미터

`CoachingRequest`는 백엔드 내부에서 Gemini 호출 직전에 구성하는 입력 데이터이다.

| 필드 | 타입 | 설명 |
|------|------|------|
| sessionId | string | 발표 세션 식별자 |
| userId | string | 사용자 식별자 |
| durationSec | number | 전체 발표 시간 |
| summary | SessionSummary | 영상 분석 집계 데이터 |
| slideLogs | SlideLog[] | 슬라이드별 진입·종료·체류 시간 |
| captures | CaptureItem[] | 문제 순간 캡처 이미지와 원인 메타데이터 |
| maxCoachingItems | number | 생성할 코칭 항목 최대 개수, 기본값 5 |

`CaptureItem`은 Gemini에 전달할 이미지 후보를 표현한다.

| 필드 | 타입 | 설명 |
|------|------|------|
| captureId | string | 캡처 이미지 식별자 |
| storagePath | string | Supabase Storage 내부 경로 |
| signedUrl | string | 백엔드가 이미지를 조회하기 위한 임시 URL |
| timestampMs | number | 문제 발생 시점 |
| category | string | gaze, posture, gesture, time 중 하나 |
| reason | string | 캡처가 발생한 규칙 또는 지표 설명 |
| severity | number | 문제 심각도, 0~1 |

`CoachingResult`는 Gemini 응답 파싱 후 저장되는 출력 데이터이다.

| 필드 | 타입 | 설명 |
|------|------|------|
| category | string | 코칭 분류(gaze, posture, gesture, time 등) |
| captureId | string | 연결된 캡처 이미지 ID |
| captureUrl | string | 결과 화면 또는 PDF에서 사용할 이미지 URL |
| issue | string | 발견된 문제 요약 |
| evidence | string | 수치 근거 또는 캡처 시점 설명 |
| coaching | string | 발표자에게 제공할 코칭 문장 |
| improvement | string | 다음 연습에서 실행할 개선 행동 |
| severity | number | 정렬과 보고서 우선순위에 사용할 심각도 |

Gemini 응답은 다음 JSON 배열 형태를 요구한다.

```json
[
  {
    "category": "posture",
    "captureId": "capture_003",
    "issue": "오른쪽 어깨 기울기가 기준값보다 오래 유지됨",
    "evidence": "3번 슬라이드 42초 지점, shoulderTiltDeg 평균 8.5도",
    "coaching": "문장을 시작하기 전 양발을 고르게 딛고 어깨 높이를 맞춘 뒤 말하면 화면상 안정감이 좋아집니다.",
    "improvement": "다음 연습에서는 슬라이드 전환 직후 2초 동안 정면 자세를 유지합니다.",
    "severity": 0.82
  }
]
```

#### 알고리즘

1. 코칭 대상 선별
   - `issueEvents`를 severity 내림차순으로 정렬한다.
   - 동일 카테고리만 과도하게 선택되지 않도록 gaze, posture, gesture, time 카테고리별 최소 1개 후보를 우선 배치한다.
   - Gemini 입력 이미지 수는 기본 5개 이하로 제한한다. 이는 응답 지연과 토큰 사용량을 줄이고 PDF 보고서의 코칭 섹션이 과도하게 길어지는 것을 방지하기 위함이다.

2. 이미지 전달 방식
   - 캡처 이미지는 Supabase Storage의 비공개 버킷에 저장한다.
   - 백엔드는 짧은 만료 시간의 Signed URL을 발급해 이미지를 조회한 뒤, Gemini 요청에는 Base64 `inlineData` 형태로 포함한다.
   - 이 방식은 이미지를 공개 URL로 노출하지 않으면서도 Gemini 요청을 하나의 self-contained payload로 구성할 수 있다.

3. 프롬프트 구성
   - System Instruction: 발표 코치 역할, 한국어 응답, 비난이 아닌 행동 개선 중심 문체를 지정한다.
   - Metrics JSON: `SessionSummary`, `SlideLog`, issueEvents의 핵심 수치를 전달한다.
   - Image Part: 선별된 캡처 이미지와 각 이미지의 timestamp, category, reason을 함께 제공한다.
   - Output Instruction: `response_mime_type`을 `application/json`으로 설정하고, `CoachingResult[]` JSON Schema를 함께 전달한다.

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "category": { "type": "string", "enum": ["gaze", "posture", "gesture", "time"] },
      "captureId": { "type": "string" },
      "issue": { "type": "string" },
      "evidence": { "type": "string" },
      "coaching": { "type": "string" },
      "improvement": { "type": "string" },
      "severity": { "type": "number", "minimum": 0, "maximum": 1 }
    },
    "required": ["category", "captureId", "issue", "evidence", "coaching", "improvement", "severity"]
  },
  "minItems": 1,
  "maxItems": 5
}
```

4. 응답 처리
   - Gemini 응답 문자열에서 JSON 배열을 파싱한다.
   - 필수 필드(`category`, `captureId`, `issue`, `coaching`, `improvement`)가 없으면 해당 항목을 폐기하거나 fallback 항목으로 대체한다.
   - 파싱된 결과는 severity 기준으로 정렬하고 PDF 보고서 생성 모듈에 전달한다.

5. 실패 처리
   - Gemini 호출 실패 시 최대 2회까지 지수 백오프 방식으로 재시도한다.
   - 재시도 후에도 실패하면 규칙 기반 템플릿을 사용한다. 예를 들어 정면 응시율이 낮으면 "발표 중 화면 밖을 보는 시간이 길었습니다. 핵심 문장을 말할 때 카메라 방향을 2초 이상 유지해 보세요."와 같은 기본 코칭을 생성한다.
   - fallback 여부는 보고서 메타데이터에 기록하여 추후 품질 개선 시 확인할 수 있도록 한다.

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

// 입력: ScoreResult + CoachingResult[] + SlideLog[]
// 출력: PDF → Supabase Storage 저장 → 다운로드 URL 반환
// 사용 라이브러리: ReportLab (레이아웃) + Matplotlib (그래프)

#### 블록 다이어그램

// ★ 그림 필수 ★ — PDF 페이지 레이아웃 스케치
// 1페이지: 표지 (점수 요약 + 레이더 차트)
// 2페이지: 카테고리별 바 차트 + 슬라이드별 시간 그래프
// 3페이지~: 코칭 섹션 반복 (좌: 캡처 이미지 / 우: 코칭 텍스트, 2단 레이아웃)
// 실제 여백·비율 비례하게 표현하면 구현할 때 훨씬 편함

#### 입출력 파라미터

// 표: 페이지 번호 / 포함 내용 / 사용 라이브러리

| 페이지 | 내용 | 라이브러리 |
|--------|------|----------|
|  |  |  |

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

| 경로 | 페이지명 | 인증 필요 |
|------|---------|---------|
|  |  |  |

### 6.2 상태 관리 설계

// Context API 4개(Auth / Session / Analysis / Report) 각각의 주요 상태 필드와 역할을 표로

| Context | 주요 상태 필드 | 역할 |
|---------|-------------|------|
|  |  |  |

### 6.3 주요 컴포넌트 명세

// 핵심 컴포넌트 위주로 표 작성
// WebcamAnalyzer / SlideViewer / GestureOverlay / TimerBar / ReportViewer / CoachingCard / RadarChart

| 컴포넌트 | 위치(페이지) | 역할 | 주요 Props |
|----------|------------|------|-----------|
|  |  |  |  |

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

1. 홍동표, 우운택, "제스처 기반 사용자 인터페이스에 대한 연구 동향", KCI, 2008
2. 변정민, "청중을 고려한 발표자의 언어적·비언어적 표현 연구", KCI, 2009
3. 이유나, 허경호, "발표상황에서 발표자의 비언어적 요소가 발표자의 이미지 및 메시지 인지도에 미치는 영향", KCI, 2008
4. Google MediaPipe Documentation, https://developers.google.com/mediapipe
5. Google AI Edge, "Pose landmark detection guide for Web", https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/web_js
6. Google AI Edge, "Hand landmark detection guide for Web", https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/web_js
7. Google AI Edge, "Face landmark detection guide", https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker
8. Google AI for Developers, "Gemini API Structured outputs", https://ai.google.dev/gemini-api/docs/structured-output
9. Google AI for Developers, "Gemini API Image understanding", https://ai.google.dev/gemini-api/docs/image-understanding
10. Supabase Docs, "Create a signed URL", https://supabase.com/docs/reference/javascript/storage-from-createsignedurl
11. MDN Web Docs, "MediaRecorder", https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder
12. MDN Web Docs, "CanvasRenderingContext2D: drawImage()", https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/drawImage
13. MDN Web Docs, "Using Web Workers", https://developer.mozilla.org/docs/Web/API/Web_Workers_API/Using_web_workers
