import { useState, useEffect, useRef, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import VideoUpload from '../components/analysis/VideoUpload'
import AnalysisProgress from '../components/analysis/AnalysisProgress'
import CoachingResult from '../components/analysis/CoachingResult'
import { useToast } from '../components/common/Toast'
import { uploadVideo, pollAnalysis } from '../api/client'

const POLL_INTERVAL = 2000

export default function VideoAnalysis() {
  const location = useLocation()
  const toast = useToast()
  const [stage, setStage] = useState('upload') // upload | progress | result | error
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [resultId, setResultId] = useState(null)
  const [stepHint, setStepHint] = useState(0)
  const jobIdRef = useRef(null)
  const timerRef = useRef(null)

  const startPolling = useCallback((jobId) => {
    timerRef.current = setInterval(async () => {
      try {
        const data = await pollAnalysis(jobId)
        if (data.step !== undefined) setStepHint(data.step)
        if (data.status === 'done') {
          clearInterval(timerRef.current)
          setResult(data.result)
          setResultId(data.result_id ?? null)
          setStage('result')
        } else if (data.status === 'error') {
          clearInterval(timerRef.current)
          setError(data.error ?? '분석 중 오류 발생')
          setStage('error')
        }
      } catch {
        clearInterval(timerRef.current)
        setError('서버 연결 오류')
        setStage('error')
      }
    }, POLL_INTERVAL)
  }, [])

  // 발표 모드에서 넘어온 job_id 자동 처리
  useEffect(() => {
    const jobId = location.state?.jobId
    if (jobId) {
      jobIdRef.current = jobId
      queueMicrotask(() => {
        setStage('progress')
        startPolling(jobId)
      })
    }
    return () => clearInterval(timerRef.current)
  }, [location.state?.jobId, startPolling])

  async function handleUpload(file) {
    setStage('progress')
    setStepHint(0)
    setError(null)
    try {
      const { job_id } = await uploadVideo(file)
      jobIdRef.current = job_id
      startPolling(job_id)
    } catch (e) {
      const msg = e.response?.data?.detail ?? '업로드 실패'
      setError(msg)
      toast(msg)
      setStage('error')
    }
  }

  if (stage === 'upload') return <VideoUpload onUpload={handleUpload} loading={false} />
  if (stage === 'progress') return <AnalysisProgress stepHint={stepHint} />
  if (stage === 'result') return <CoachingResult result={result} resultId={resultId} />

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="text-5xl mb-4">⚠️</div>
        <p className="text-red-600 font-medium">{error}</p>
        <button
          onClick={() => setStage('upload')}
          className="mt-6 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 transition-colors"
        >
          다시 시도
        </button>
      </div>
    </div>
  )
}
