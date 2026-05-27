import { useState, useCallback, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import FileUpload from '../components/presentation/FileUpload'
import SlideViewer from '../components/presentation/SlideViewer'
import SlideControls from '../components/presentation/SlideControls'
import WebcamRecorder from '../components/presentation/WebcamRecorder'
import GestureController from '../components/presentation/GestureController'
import { useToast } from '../components/common/Toast'
import { uploadSlides, deleteSlides, uploadVideo } from '../api/client'

const SUPPORTS_FOLDER = typeof window !== 'undefined' && 'showDirectoryPicker' in window

function GoalModal({ onStart }) {
  const [minutes, setMinutes] = useState('')
  const [folderHandle, setFolderHandle] = useState(null)
  const [folderName, setFolderName] = useState('')
  const [showFacePreview, setShowFacePreview] = useState(true)

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
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-40">
      <div className="w-[22rem] rounded-lg bg-white p-6 text-left shadow-xl">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-sm font-bold text-blue-700">
            SET
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">발표 설정</h2>
            <p className="text-sm text-gray-500">시작 전에 녹화 옵션을 정하세요.</p>
          </div>
        </div>

        <input
          type="number"
          min="1"
          max="120"
          placeholder="목표 시간 (분, 선택)"
          value={minutes}
          onChange={(e) => setMinutes(e.target.value)}
          className="mb-3 w-full rounded-lg border px-4 py-2 text-center text-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {SUPPORTS_FOLDER && (
          <button
            onClick={pickFolder}
            className="mb-3 flex w-full items-center justify-center rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 transition hover:bg-gray-50"
          >
            <span>{folderName ? `저장 폴더: ${folderName}` : '영상 저장 폴더 선택 (선택)'}</span>
          </button>
        )}

        <label className="mb-5 flex cursor-pointer items-center justify-between rounded-lg border border-gray-200 px-4 py-3">
          <span className="text-sm font-medium text-gray-800">발표 중 내 얼굴 표시</span>
          <input
            type="checkbox"
            checked={showFacePreview}
            onChange={(e) => setShowFacePreview(e.target.checked)}
            className="h-5 w-5 accent-blue-600"
          />
        </label>

        <button
          onClick={() => onStart(minutes ? parseInt(minutes) * 60 : null, folderHandle, { showFacePreview })}
          className="w-full rounded-lg bg-blue-600 py-2.5 font-semibold text-white transition hover:bg-blue-700"
        >
          발표 시작
        </button>
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
    if (session) await deleteSlides(session.sessionId).catch(() => {})

    try {
      const blob = await webcamRef.current?.stop()
      if (blob && blob.size > 0) {
        if (folderHandleRef.current) {
          await saveToFolder(blob, folderHandleRef.current)
        }

        const file = new File([blob], 'webcam_recording.webm', { type: blob.type })
        const { job_id } = await uploadVideo(file, {
          goal_sec: goalSec,
          elapsed_sec: elapsed,
          slide_log: slideLogRef.current,
        })
        navigate('/analysis', { state: { jobId: job_id } })
        return
      }
    } catch {
      toast('녹화 업로드에 실패했습니다.', 'error')
    }
    navigate('/')
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

  if (!session) return <FileUpload onUpload={handleUpload} loading={loading} />

  return (
    <div className="fixed inset-0 z-50 flex h-screen w-screen flex-col bg-black">
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

      {exiting && (
        <div className="absolute inset-0 bg-black/70 flex flex-col items-center justify-center z-30">
          <div className="w-10 h-10 border-4 border-white border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-white text-sm">녹화 저장 중... 잠시만 기다려 주세요</p>
        </div>
      )}
    </div>
  )
}
