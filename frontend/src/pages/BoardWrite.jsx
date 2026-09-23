import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { createBoardPost, fetchHistory, uploadBoardVideo } from '../api/client'
import { useToast } from '../components/common/Toast'

const MAX_VIDEO_MB = 50 // 백엔드 settings.board_max_video_mb 와 맞춘다
const ACCEPT = '.mp4,.webm,.mov,video/mp4,video/webm,video/quicktime'

export default function BoardWrite() {
  const navigate = useNavigate()
  const toast = useToast()
  const [searchParams] = useSearchParams()

  const [history, setHistory] = useState([])
  const [resultId, setResultId] = useState(searchParams.get('resultId') ?? '')
  const [title, setTitle] = useState('')
  const [topic, setTopic] = useState('')
  const [tagsText, setTagsText] = useState('')
  const [isPublic, setIsPublic] = useState(true)
  const [file, setFile] = useState(null)
  const [progress, setProgress] = useState(null) // null | 0~100
  const [submitting, setSubmitting] = useState(false)

  // 분석 완료된 발표 목록 (게시할 분석 결과를 고르는 용도)
  useEffect(() => {
    fetchHistory(1, 30)
      .then((res) => setHistory(res.items ?? []))
      .catch(() => toast('발표 기록을 불러오지 못했습니다.'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleFile(e) {
    const picked = e.target.files?.[0]
    if (!picked) return
    if (picked.size > MAX_VIDEO_MB * 1024 * 1024) {
      toast(`영상은 ${MAX_VIDEO_MB}MB 이하만 올릴 수 있습니다.`)
      e.target.value = ''
      return
    }
    setFile(picked)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!resultId) return toast('게시할 분석 결과를 선택해 주세요.')
    if (!title.trim()) return toast('제목을 입력해 주세요.')
    if (!topic.trim()) return toast('발표 주제를 입력해 주세요.')
    if (!file) return toast('발표 영상을 선택해 주세요.')

    const tags = tagsText
      .split(/[,\s]+/)
      .map((t) => t.replace(/^#/, '').trim())
      .filter(Boolean)

    setSubmitting(true)
    setProgress(0)
    try {
      // 1) 영상을 Supabase Storage에 올리고 저장 경로를 받는다
      const { video_storage_path } = await uploadBoardVideo(file, setProgress)
      // 2) 경로 + 분석 결과 id로 게시글을 만든다 (분석 스냅샷은 서버가 붙인다)
      const post = await createBoardPost({
        analysisResultId: resultId,
        title: title.trim(),
        topic: topic.trim(),
        tags,
        videoStoragePath: video_storage_path,
        isPublic,
      })
      toast('게시글이 등록되었습니다.', 'success')
      navigate(`/board/${post.id}`, { replace: true })
    } catch (err) {
      const detail = err.response?.data?.detail
      toast(typeof detail === 'string' ? detail : '게시글 등록에 실패했습니다.')
      setSubmitting(false)
      setProgress(null)
    }
  }

  const inputCls =
    'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="mx-auto max-w-xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">발표 영상 공유하기</h1>
          <button
            onClick={() => navigate('/board')}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
          >
            목록으로
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">공유할 분석 결과</span>
            <select value={resultId} onChange={(e) => setResultId(e.target.value)} className={inputCls}>
              <option value="">선택하세요</option>
              {history.map((h) => (
                <option key={h.id} value={h.id}>
                  {new Date(h.created_at).toLocaleString('ko-KR')}
                  {h.score_total != null ? ` · ${h.score_total}점` : ''}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">제목</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={100} className={inputCls} placeholder="예) 캡스톤 최종 발표 연습" />
          </label>

          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">발표 주제</span>
            <input value={topic} onChange={(e) => setTopic(e.target.value)} maxLength={50} className={inputCls} placeholder="예) 캡스톤" />
          </label>

          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">태그 (쉼표 또는 공백으로 구분, 최대 10개)</span>
            <input value={tagsText} onChange={(e) => setTagsText(e.target.value)} className={inputCls} placeholder="#취업발표, #IR" />
          </label>

          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">발표 영상 (MP4·WebM·MOV, {MAX_VIDEO_MB}MB 이하)</span>
            <input type="file" accept={ACCEPT} onChange={handleFile} className="block w-full text-sm text-gray-600 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-3 file:py-2 file:text-indigo-700" />
            <span className="mt-1 block text-xs text-gray-400">분석이 끝난 영상은 서버에 남지 않으므로, 분석에 썼던 영상을 다시 선택해 주세요.</span>
          </label>

          <label className="flex items-center justify-between gap-4 text-sm">
            <span>
              <span className="block font-medium text-gray-700">전체 공개</span>
              <span className="text-xs text-gray-400">끄면 나만 볼 수 있습니다.</span>
            </span>
            <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} className="h-5 w-5 accent-indigo-600" />
          </label>

          {progress != null && (
            <div>
              <div className="h-2 overflow-hidden rounded-full bg-gray-200">
                <div className="h-full bg-indigo-500 transition-all" style={{ width: `${progress}%` }} />
              </div>
              <p className="mt-1 text-right text-xs text-gray-400">{progress < 100 ? `업로드 중 ${progress}%` : '게시글 만드는 중...'}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {submitting ? '등록 중...' : '게시하기'}
          </button>
        </form>
      </div>
    </div>
  )
}
