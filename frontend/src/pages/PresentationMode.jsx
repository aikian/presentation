import { useState, useCallback, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {QRCodeSVG} from 'qrcode.react'
import FileUpload from '../components/presentation/FileUpload'
import SlideViewer from '../components/presentation/SlideViewer'
import SlideControls from '../components/presentation/SlideControls'
import WebcamRecorder from '../components/presentation/WebcamRecorder'
import GestureController from '../components/presentation/GestureController'
import NavBar from '../components/common/NavBar'
import { useToast } from '../components/common/Toast'
import { uploadSlides, deleteSlides, uploadVideo, createSurveyLink, closeSurveyLink } from '../api/client'
const SUPPORTS_FOLDER = typeof window !== 'undefined' && 'showDirectoryPicker' in window
const SETTINGS_KEY = 'presentationcoach.settings'
function loadPresentationSettings() {
  try {
    return JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}')
  } catch {
    return {}
  }
}
const QUICK_MINUTES = [5, 10, 15, 20]

function GoalModal({ onStart }) {
  const savedSettings = loadPresentationSettings()
  const [minutes, setMinutes] = useState(savedSettings.defaultGoalMinutes || '')
  const [folderHandle, setFolderHandle] = useState(null)
  const [folderName, setFolderName] = useState('')
  const [showFacePreview, setShowFacePreview] = useState(savedSettings.showFacePreview !== false)

  async function pickFolder() {
    try {
      const handle = await window.showDirectoryPicker()
      setFolderHandle(handle)
      setFolderName(handle.name)
    } catch {
      // 취소
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-3xl bg-white p-7 text-left shadow-2xl">
        <h2 className="text-xl font-extrabold tracking-tight text-slate-950">촬영 설정</h2>
        <p className="mt-1 text-sm text-slate-500">시작하면 바로 녹화가 시작됩니다.</p>

        <div className="mt-6">
          <label htmlFor="goal-min" className="text-sm font-bold text-slate-900">
            목표 시간 <span className="font-normal text-slate-400">(선택)</span>
          </label>
          <div className="mt-2 flex flex-wrap gap-2">
            {QUICK_MINUTES.map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMinutes(String(m))}
                className={`rounded-lg border px-3.5 py-1.5 text-sm font-semibold transition ${
                  String(minutes) === String(m)
                    ? 'border-blue-600 bg-blue-600 text-white'
                    : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                {m}분
              </button>
            ))}
          </div>
          <div className="relative mt-2">
            <input
              id="goal-min"
              type="number"
              min="1"
              max="120"
              placeholder="직접 입력"
              value={minutes}
              onChange={(e) => setMinutes(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-4 py-2.5 pr-10 text-base focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
            />
            <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm text-slate-400">분</span>
          </div>
        </div>

        <label className="mt-5 flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-slate-200 px-4 py-3.5">
          <span>
            <span className="block text-sm font-bold text-slate-900">발표 중 내 얼굴 표시</span>
            <span className="block text-xs text-slate-500">끄더라도 녹화와 분석은 그대로 진행됩니다.</span>
          </span>
          <input
            type="checkbox"
            checked={showFacePreview}
            onChange={(e) => setShowFacePreview(e.target.checked)}
            className="h-5 w-5 accent-blue-600"
          />
        </label>

        {SUPPORTS_FOLDER && (
          <button
            onClick={pickFolder}
            className="mt-3 flex w-full items-center justify-between rounded-xl border border-slate-200 px-4 py-3 text-left text-sm transition hover:bg-slate-50"
          >
            <span className="font-bold text-slate-900">영상 저장 폴더</span>
            <span className={folderName ? 'font-semibold text-blue-700' : 'text-slate-400'}>
              {folderName || '선택 안 함'}
            </span>
          </button>
        )}

        <button
          onClick={() => onStart(minutes ? parseInt(minutes) * 60 : null, folderHandle, { showFacePreview })}
          className="mt-6 w-full rounded-xl bg-blue-600 py-3 font-bold text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
        >
          촬영 시작
        </button>
      </div>
    </div>
  )
}

function EndChoiceModal({ onAnalyze, onSurvey }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-3xl bg-white p-7 text-left shadow-2xl">
        <h2 className="text-xl font-extrabold tracking-tight text-slate-950">발표 종료</h2>
        <p className="mt-1 text-sm text-slate-500">녹화가 완료되었습니다. 다음 중 진행할 작업을 선택하세요.</p>
        <div className="mt-6 flex flex-col gap-3">
          <button
            onClick={onAnalyze}
            className="rounded-xl border border-slate-200 bg-white py-3 font-bold text-slate-900 transition hover:bg-slate-100"
          >
            분석 보러 가기
          </button>
          <button
            onClick={onSurvey}
            className="rounded-xl border border-slate-200 bg-white py-3 font-bold text-slate-900 transition hover:bg-slate-100"
          >
            설문 참여하기
          </button>  
        </div>
      </div>
    </div>
  )
}

function SurveyQRModal({ surveyURL, onNext, onClose }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-3xl bg-white p-7 text-left shadow-2xl">
        <h2 className="text-xl font-extrabold tracking-tight text-slate-950">설문 참여</h2>
        <p className="mt-1 text-sm text-slate-500">아래 QR 코드를 스캔하여 설문에 참여하세요.</p>

        <div className="mx-auto my-7 flex justify-center rounded-2xl border border-slate-200 bg-white p-6">
          <QRCodeSVG value={surveyURL} size={200} level="H" includeMargin={true} />
        </div>

        <p className="break-all text-sm text-slate-500">{surveyURL}</p>

        <div className="mt-6 flex flex-col gap-3">
          <button
            onClick={onNext}
            className="rounded-xl border border-slate-200 bg-white py-3 font-bold text-slate-900 transition hover:bg-slate-100"
          >
            설문 종료 및 발표 분석 시작
          </button>

          <button
            onClick={onClose}
            className="rounded-xl border border-slate-200 bg-white py-3 font-bold text-slate-900 transition hover:bg-slate-100"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  )
}

async function saveToFolder(blob, folderHandle) {
  try {
    const ts = new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-')
    const ext = blob.type.includes('mp4') ? 'mp4' : 'webm'
    const fileHandle = await folderHandle.getFileHandle(`presentationcoach_${ts}.${ext}`, { create: true })
    const writable = await fileHandle.createWritable()
    await writable.write(blob)
    await writable.close()
  } catch (e) {
    console.error('폴더 저장 실패:', e)
  }
}
export default function PresentationMode() {
  const navigate = useNavigate()
  const toast = useToast()
  const [loading, setLoading] = useState(false)
  const [session, setSession] = useState(null)
  const [current, setCurrent] = useState(0)
  const [exiting, setExiting] = useState(false)
  const [showGoal, setShowGoal] = useState(false)
  const [goalSec, setGoalSec] = useState(null)
  const [elapsed, setElapsed] = useState(null)
  const [webcamStream, setWebcamStream] = useState(null)
  const [showFacePreview, setShowFacePreview] = useState(true)
  const webcamRef = useRef(null)
  const timerRef = useRef(null)
  const folderHandleRef = useRef(null)
  // SlideLog: 슬라이드별 체류 시간 기록
  const slideLogRef = useRef([])          // [{slide: 0, duration: 3.2}, ...]
  const slideStartRef = useRef(null)       // 현재 슬라이드가 표시된 시각(ms)
  const currentRef = useRef(0)            // setCurrent와 동기화용
  
  const [showEndChoice, setShowEndChoice] = useState(false) // 발표 후 분석 또는 QR 설문 선택 모달 표시
  const [showSurveyQR, setShowSurveyQR] = useState(false) // 설문 QR 코드 표시
  const [surveyURL, setSurveyURL] = useState('') // 설문 URL
  const [surveyToken, setSurveyToken] = useState(null)
  const [surveyClosed, setSurveyClosed] = useState(false)
  const [surveyLoading, setSurveyLoading] = useState(false)
  const [recordedBlob, setRecordedBlob] = useState(null) // 녹화된 영상 Blob

  useEffect(() => () => clearInterval(timerRef.current), [])
  function _recordCurrentSlide() {
    if (slideStartRef.current !== null) {
      const duration = parseFloat(((Date.now() - slideStartRef.current) / 1000).toFixed(1))
      slideLogRef.current.push({ slide: currentRef.current, duration })
    }
    slideStartRef.current = Date.now()
  }
  async function handleUpload(file) {
    setLoading(true)
    try {
      const data = await uploadSlides(file)
      setSession({ sessionId: data.session_id, slides: data.slides })
      setCurrent(0)
      currentRef.current = 0
      setShowGoal(true)
    } catch (e) {
      toast(e.response?.data?.detail ?? '업로드 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }
  function handleStart(goal, folderHandle, options = {}) {
    folderHandleRef.current = folderHandle
    setGoalSec(goal)
    setShowFacePreview(options.showFacePreview !== false)
    setShowGoal(false)
    setElapsed(0)
    slideLogRef.current = []
    slideStartRef.current = Date.now()
    timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000)
  }
  
  async function handleExit() {
    if (exiting) return

    clearInterval(timerRef.current)
    _recordCurrentSlide()  // 마지막 슬라이드 체류 시간 기록
    setExiting(true)

    try {
      const blob = await webcamRef.current?.stop()
      if (!blob || blob.size == 0) {
        setShowEndChoice(false)
        setShowSurveyQR(false)
        navigate('/') // 녹화가 없으면 바로 홈으로
        return
      }

      setRecordedBlob(blob) // 녹화 영상 보관

      if (folderHandleRef.current) {
        await saveToFolder(blob, folderHandleRef.current)
      }

      setShowEndChoice(true) // 분석 또는 설문 선택 모달 표시
 
    } catch (e) {
      toast('녹화 업로드에 실패했습니다.', 'error')
    } finally {
      setExiting(false)
    }
  }

  async function handleAnalyze() {
    if (exiting || !recordedBlob) return

    setExiting(true)
    setShowEndChoice(false)
    setShowSurveyQR(false)

    try {
      if (surveyToken && !surveyClosed) {
        await closeSurveyLink(surveyToken).catch(() => {})
        setSurveyClosed(true)
      }

      const file = new File([recordedBlob], 'webcam_recording.webm', { type: recordedBlob.type })
      const { job_id } = await uploadVideo(file, {
        goal_sec: goalSec,
        elapsed_sec: elapsed,
        slide_log: slideLogRef.current,
        survey_token: surveyToken
      })

      if (session) await deleteSlides(session.sessionId).catch(() => {})

      navigate('/analysis', { state: { jobId: job_id } })

    } catch (e) {
      toast('분석 업로드에 실패했습니다.', 'error')
      setExiting(false)
      setShowEndChoice(true)
    }
  }

  async function handleShowSurvey() {
    if (surveyLoading) return

    // 이미 열려 있는 설문이 있으면 새로 만들지 않고 같은 QR을 다시 보여줌
    if (surveyToken && !surveyClosed) {
      setShowEndChoice(false)
      setShowSurveyQR(true)
      return
    }

    if (surveyToken && surveyClosed) {
      toast('이미 종료된 설문입니다.', 'error')
      return
    }

    setSurveyLoading(true)
    try {
      const { token } = await createSurveyLink()   // 버튼 누른 시점부터 30분
      setSurveyToken(token)
      setSurveyClosed(false)
      setSurveyURL(`${window.location.origin}/survey/${token}`)
      setShowEndChoice(false)
      setShowSurveyQR(true)
    } catch (e) {
      toast('설문 링크를 만들지 못했습니다.', 'error')
    } finally {
      setSurveyLoading(false)
    }
  }

  const prev = useCallback(() => {
    _recordCurrentSlide()
    setCurrent((c) => {
      const next = Math.max(0, c - 1)
      currentRef.current = next
      return next
    })
  }, [])
  const next = useCallback(() => {
    _recordCurrentSlide()
    setCurrent((c) => {
      const n = Math.min((session?.slides.length ?? 1) - 1, c + 1)
      currentRef.current = n
      return n
    })
  }, [session])
  // 슬라이드를 올리기 전에는 일반 화면(밝은 테마 + 내비게이션), 촬영이 시작되면 전체 화면 어두운 테마
  if (!session) {
    return (
      <div className="min-h-screen bg-slate-50">
        <NavBar />
        <FileUpload onUpload={handleUpload} loading={loading} />
      </div>
    )
  }
  return (
    <div className="fixed inset-0 z-50 flex h-screen w-screen flex-col bg-slate-950">
      <SlideViewer slides={session.slides} current={current} onPrev={prev} onNext={next} />
      <SlideControls
        current={current}
        total={session.slides.length}
        onPrev={prev}
        onNext={next}
        onExit={handleExit}
        exiting={exiting}
        elapsed={elapsed}
        goalSec={goalSec}
      />
      {elapsed != null && (
        <WebcamRecorder
          ref={webcamRef}
          onStream={setWebcamStream}
          showPreview={showFacePreview}
        />
      )}
      {webcamStream && (
        <GestureController stream={webcamStream} onLeft={prev} onRight={next} />
      )}
      {showGoal && <GoalModal onStart={handleStart} />}

      {/* 발표 종료 후 작업 선택 */}
      {showEndChoice && (
        <EndChoiceModal
          onAnalyze={handleAnalyze}
          onSurvey={handleShowSurvey}
          onCancel={() => setShowEndChoice(false)}
        />
      )}

      {/* 설문 QR 코드 표시 */}
      {showSurveyQR && (
        <SurveyQRModal 
          surveyURL={surveyURL} 
          onNext={handleAnalyze} 
          onClose={() => {
            setShowSurveyQR(false) 
            setShowEndChoice(true)
          }}  
        />
      )}
      {exiting && (
        <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-slate-950/80 backdrop-blur-sm">
          <div className="mb-4 h-10 w-10 animate-spin rounded-full border-4 border-white border-t-transparent" />
          <p className="text-base font-semibold text-white">녹화를 저장하고 있어요</p>
          <p className="mt-1 text-sm text-white/60">저장이 끝나면 자동으로 분석이 시작됩니다.</p>
        </div>
      )}
    </div>
  )
}
