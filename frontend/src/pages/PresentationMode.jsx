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
      <div className="bg-white rounded-2xl shadow-xl p-8 w-80 text-center">
        <div className="text-4xl mb-4">⏱️</div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">발표 설정</h2>
        <p className="text-sm text-gray-500 mb-4">목표 시간 및 영상 저장 폴더를 설정하세요.</p>

        <input
          type="number"
          min="1"
          max="120"
          placeholder="목표 시간 (분, 선택)"
          value={minutes}
          onChange={(e) => setMinutes(e.target.value)}
          className="w-full border rounded-lg px-4 py-2 text-center text-lg mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {SUPPORTS_FOLDER && (
          <button
            onClick={pickFolder}
            className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition mb-4 flex items-center justify-center gap-2"
          >
            <span>📁</span>
            <span>{folderName ? `저장 폴더: ${folderName}` : '영상 저장 폴더 선택 (선택)'}</span>
          </button>
        )}

        <button
          onClick={() => onStart(minutes ? parseInt(minutes) * 60 : null, folderHandle)}
          className="w-full bg-blue-600 text-white rounded-lg py-2.5 font-semibold hover:bg-blue-700 transition"
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
  const webcamRef = useRef(null)
  const timerRef = useRef(null)
  const folderHandleRef = useRef(null)

  useEffect(() => () => clearInterval(timerRef.current), [])

  async function handleUpload(file) {
    setLoading(true)
    try {
      const data = await uploadSlides(file)
      setSession({ sessionId: data.session_id, slides: data.slides })
      setCurrent(0)
      setShowGoal(true)
    } catch (e) {
      toast(e.response?.data?.detail ?? '업로드 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  function handleStart(goal, folderHandle) {
    folderHandleRef.current = folderHandle
    setGoalSec(goal)
    setShowGoal(false)
    setElapsed(0)
    timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000)
  }

  async function handleExit() {
    clearInterval(timerRef.current)
    setExiting(true)
    if (session) await deleteSlides(session.sessionId).catch(() => {})

    try {
      const blob = await webcamRef.current?.stop()
      if (blob && blob.size > 0) {
        // 폴더 저장 (선택된 경우)
        if (folderHandleRef.current) {
          await saveToFolder(blob, folderHandleRef.current)
        }

        const file = new File([blob], 'webcam_recording.webm', { type: blob.type })
        const { job_id } = await uploadVideo(file)
        navigate('/analysis', { state: { jobId: job_id } })
        return
      }
    } catch {
      toast('녹화 업로드에 실패했습니다.', 'error')
    }
    navigate('/')
  }

  const prev = useCallback(() => setCurrent((c) => Math.max(0, c - 1)), [])
  const next = useCallback(
    () => setCurrent((c) => Math.min((session?.slides.length ?? 1) - 1, c + 1)),
    [session]
  )

  if (!session) return <FileUpload onUpload={handleUpload} loading={loading} />

  return (
    <div className="h-screen flex flex-col bg-black relative">
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
      <WebcamRecorder ref={webcamRef} onStream={setWebcamStream} />
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
