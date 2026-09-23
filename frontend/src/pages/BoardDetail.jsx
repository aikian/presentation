import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  addBoardComment, deleteBoardComment, deleteBoardPost,
  fetchBoardPost, fetchBoardRecommendations, fetchHistory,
} from '../api/client'
import PostCard, { ScoreBadge } from '../components/board/PostCard'
import { useToast } from '../components/common/Toast'
import { useAuth } from '../context/AuthContext'

const pct = (v) => (v == null ? '-' : `${(v * 100).toFixed(0)}%`)
const deg = (v) => (v == null ? '-' : `${Number(v).toFixed(1)}도`)
const times = (v) => (v == null ? '-' : `${v}회`)
const point = (v) => (v == null ? '-' : `${v}점`)

// 게시글 스냅샷(board_snapshot)과 "내 최근 발표"를 같은 항목으로 나란히 놓는다. (사용자 시나리오 5)
function buildCompareRows(snap, mine) {
  const scores = snap.scores ?? {}
  const metrics = snap.metrics ?? {}
  return [
    { label: 'AI 총점', theirs: point(scores.total), mine: point(mine?.score_total) },
    { label: '시선 점수', theirs: point(scores.gaze), mine: point(mine?.score_gaze) },
    { label: '자세 점수', theirs: point(scores.posture), mine: point(mine?.score_pose) },
    { label: '제스처 점수', theirs: point(scores.gesture), mine: point(mine?.score_gesture) },
    { label: '시간 점수', theirs: point(scores.time), mine: point(mine?.score_time) },
    { label: '시선 이탈률', theirs: pct(metrics.gaze_away_ratio), mine: pct(mine?.gaze_away_ratio) },
    { label: '어깨 기울기', theirs: deg(metrics.shoulder_tilt_avg), mine: deg(mine?.shoulder_tilt_avg) },
    { label: '제스처 횟수', theirs: times(metrics.gesture_count), mine: times(mine?.gesture_count) },
  ]
}

export default function BoardDetail() {
  const { postId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const { user } = useAuth()

  const [post, setPost] = useState(null)
  const [recs, setRecs] = useState([])
  const [mine, setMine] = useState(null) // 내 가장 최근 발표
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [comment, setComment] = useState('')
  const [sending, setSending] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await fetchBoardPost(postId)
      setPost(data)
      setError(null)
    } catch (e) {
      setError(e.response?.status === 404 ? '게시글을 찾을 수 없습니다.' : '게시글을 불러오지 못했습니다.')
    }
  }, [postId])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([
      load(),
      fetchBoardRecommendations(postId, 5).then((r) => !cancelled && setRecs(r.items ?? [])).catch(() => {}),
      fetchHistory(1, 1).then((r) => !cancelled && setMine(r.items?.[0] ?? null)).catch(() => {}),
    ]).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [postId, load])

  async function handleComment(e) {
    e.preventDefault()
    if (!comment.trim()) return
    setSending(true)
    try {
      await addBoardComment(postId, comment.trim())
      setComment('')
      await load()
    } catch (err) {
      toast(err.response?.data?.detail ?? '댓글 등록에 실패했습니다.')
    } finally {
      setSending(false)
    }
  }

  async function handleDeleteComment(commentId) {
    if (!window.confirm('댓글을 삭제할까요?')) return
    try {
      await deleteBoardComment(postId, commentId)
      await load()
    } catch (err) {
      toast(err.response?.data?.detail ?? '댓글 삭제에 실패했습니다.')
    }
  }

  async function handleDeletePost() {
    if (!window.confirm('이 게시글을 삭제할까요? 영상도 함께 삭제됩니다.')) return
    try {
      await deleteBoardPost(postId)
      toast('게시글이 삭제되었습니다.', 'success')
      navigate('/board', { replace: true })
    } catch (err) {
      toast(err.response?.data?.detail ?? '게시글 삭제에 실패했습니다.')
    }
  }

  if (loading) {
    return <div className="min-h-screen bg-gray-50 px-4 py-10"><div className="mx-auto h-96 max-w-3xl animate-pulse rounded-2xl bg-gray-200" /></div>
  }

  if (error || !post) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
        <p className="text-red-600">{error ?? '게시글을 찾을 수 없습니다.'}</p>
        <button onClick={() => navigate('/board')} className="mt-6 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">
          목록으로
        </button>
      </div>
    )
  }

  const snap = post.snapshot?.board_snapshot ?? {}
  const rows = buildCompareRows(snap, mine)

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center justify-between">
          <button onClick={() => navigate('/board')} className="text-sm text-gray-500 hover:text-gray-700">← 목록으로</button>
          {post.is_owner && (
            <button onClick={handleDeletePost} className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50">
              게시글 삭제
            </button>
          )}
        </div>

        <header>
          <div className="flex items-start justify-between gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{post.title}</h1>
            <ScoreBadge score={post.score_total} />
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
            <span className="rounded bg-indigo-50 px-2 py-0.5 font-medium text-indigo-600">{post.topic}</span>
            {post.tags?.map((t) => (
              <span key={t} className="rounded bg-gray-100 px-2 py-0.5 text-gray-500">#{t}</span>
            ))}
            {!post.is_public && <span className="rounded bg-gray-800 px-2 py-0.5 text-white">비공개</span>}
          </div>
          <p className="mt-2 text-xs text-gray-400">
            {post.author_name || '익명'} · {new Date(post.created_at).toLocaleString('ko-KR')}
          </p>
        </header>

        {/* 영상 */}
        <section className="overflow-hidden rounded-2xl bg-black">
          {post.video_signed_url ? (
            <video src={post.video_signed_url} controls className="aspect-video w-full" />
          ) : (
            <p className="py-24 text-center text-sm text-gray-400">영상을 불러올 수 없습니다.</p>
          )}
        </section>

        {/* AI 분석 결과 + 내 발표와 비교 */}
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-1 text-lg font-bold text-gray-900">AI 분석 결과</h2>
          <p className="mb-4 text-xs text-gray-400">
            {mine ? '내 가장 최근 발표와 나란히 비교해 보세요.' : '내 발표를 분석하면 이 표에서 바로 비교할 수 있어요.'}
          </p>
          <div className="overflow-x-auto rounded-xl border border-gray-200">
            <table className="w-full min-w-[22rem] text-sm">
              <thead className="bg-gray-50 text-gray-500">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">항목</th>
                  <th className="px-3 py-2 text-right font-medium">이 발표</th>
                  <th className="px-3 py-2 text-right font-medium">내 최근 발표</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.label} className="border-t border-gray-100">
                    <td className="px-3 py-2 font-medium text-gray-800">{r.label}</td>
                    <td className="px-3 py-2 text-right text-gray-900">{r.theirs}</td>
                    <td className="px-3 py-2 text-right text-gray-500">{mine ? r.mine : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {snap.coaching && (
            <details className="mt-4 rounded-xl bg-gray-50 p-4 text-sm text-gray-700">
              <summary className="cursor-pointer font-semibold">AI 코칭 전문 보기</summary>
              <div className="mt-3 whitespace-pre-line leading-relaxed">{snap.coaching}</div>
            </details>
          )}
        </section>

        {/* 댓글 */}
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-bold text-gray-900">댓글 {post.comments.length}</h2>

          <form onSubmit={handleComment} className="mb-4 flex gap-2">
            <input
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              maxLength={1000}
              placeholder="발표에 대한 피드백을 남겨 보세요"
              className="min-w-0 flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              type="submit"
              disabled={sending || !comment.trim()}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
            >
              등록
            </button>
          </form>

          {post.comments.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-400">첫 댓글을 남겨 보세요.</p>
          ) : (
            <ul className="space-y-3">
              {post.comments.map((c) => (
                <li key={c.id} className="rounded-xl bg-gray-50 px-4 py-3">
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>{c.author_name || '익명'} · {new Date(c.created_at).toLocaleString('ko-KR')}</span>
                    {(c.user_id === user?.id || post.is_owner) && (
                      <button onClick={() => handleDeleteComment(c.id)} className="text-red-400 hover:text-red-600">삭제</button>
                    )}
                  </div>
                  <p className="mt-1 whitespace-pre-line text-sm text-gray-800">{c.content}</p>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* 추천 */}
        {recs.length > 0 && (
          <section>
            <h2 className="mb-3 text-lg font-bold text-gray-900">AI 점수가 높은 다른 발표 사례</h2>
            <div className="space-y-3">
              {recs.map((r) => (
                <PostCard key={r.id} post={r} onClick={() => navigate(`/board/${r.id}`)} />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
