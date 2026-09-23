import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchHistory } from '../api/client'

// [2026-09-22 수정] 값이 null/undefined여도 화면이 깨지지 않게 방어한다.
// 한 건이라도 값이 비어 있으면 목록 전체가 렌더링에 실패해
// "기록이 사라진 것처럼" 보이던 문제를 막는다.
function num(v, fallback = 0) {
  return typeof v === 'number' && Number.isFinite(v) ? v : fallback
}

function statusColor(val, thresholds) {
  const v = num(val)
  if (v > thresholds[1]) return 'text-red-600'
  if (v > thresholds[0]) return 'text-yellow-600'
  return 'text-green-600'
}

function ScoreBadge({ score }) {
  if (score == null) return null
  const cls =
    score >= 70 ? 'bg-green-100 text-green-700' :
    score >= 50 ? 'bg-yellow-100 text-yellow-700' :
                  'bg-red-100 text-red-700'
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${cls}`}>
      {score}점
    </span>
  )
}

function DetailPanel({ item, onClose }) {
  const {
    gaze_away_ratio, shoulder_tilt_avg, gesture_count,
    coaching, created_at, score_total, elapsed_sec, goal_sec,
  } = item
  const date = new Date(created_at).toLocaleString('ko-KR')

  function fmtTime(s) {
    if (!s) return null
    return `${Math.floor(s / 60)}분 ${Math.round(s % 60)}초`
  }

  function handlePrint() {
    window.print()
  }

  return (
    <div className="print-modal-backdrop fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="print-report bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">분석 상세</h2>
          <div className="no-print flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="text-sm text-indigo-600 hover:text-indigo-800 border border-indigo-300 rounded-lg px-3 py-1 transition-colors"
            >
              인쇄 / PDF 저장
            </button>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
          </div>
        </div>

        <div className="flex items-center gap-2 mb-4">
          <p className="text-xs text-gray-400">{date}</p>
          {score_total != null && <ScoreBadge score={score_total} />}
        </div>

        {elapsed_sec != null && goal_sec != null && (
          <p className="text-xs text-gray-500 mb-3">
            발표 시간: {fmtTime(elapsed_sec)} / 목표: {fmtTime(goal_sec)}
          </p>
        )}

        <div className="grid grid-cols-3 gap-3 mb-5">
          {[
            { label: '시선 이탈률', value: `${(num(gaze_away_ratio) * 100).toFixed(0)}%`, thresholds: [0.15, 0.3], raw: num(gaze_away_ratio) },
            { label: '어깨 기울기', value: `${num(shoulder_tilt_avg).toFixed(1)}도`, thresholds: [8, 15], raw: num(shoulder_tilt_avg) },
            { label: '제스처', value: `${num(gesture_count)}회`, thresholds: [5, 50], raw: num(gesture_count) < 5 ? 0 : num(gesture_count) > 50 ? 100 : 10 },
          ].map(({ label, value, thresholds, raw }) => (
            <div key={label} className="border rounded-xl p-3 text-center">
              <div className={`text-xl font-bold ${statusColor(raw, thresholds)}`}>{value}</div>
              <div className="text-xs text-gray-500 mt-1">{label}</div>
            </div>
          ))}
        </div>

        <div className="bg-gray-50 rounded-xl p-4 text-sm text-gray-700 leading-relaxed whitespace-pre-line">
          <span className="font-semibold block mb-2">AI 코칭</span>
          {coaching || '코칭 없음'}
        </div>
      </div>
    </div>
  )
}

const PAGE_LIMIT = 20

export default function History() {
  const navigate = useNavigate()
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [selected, setSelected] = useState(null)
  // [2026-09-22 추가] 조회 실패를 화면에 드러낸다.
  const [error, setError] = useState(null)
  const [total, setTotal] = useState(null)

  const loadPage = useCallback(async (p, append = false) => {
    try {
      const res = await fetchHistory(p, PAGE_LIMIT)
      const items = res.items ?? res  // 이전 버전 호환
      if (!Array.isArray(items)) throw new Error('예상과 다른 응답 형식입니다.')

      setError(null)
      setTotal(res.total ?? null)

      if (append) {
        // [2026-09-22 수정] id 기준 중복 제거. 같은 기록이 두 번 쌓이지 않는다.
        setRecords((prev) => {
          const seen = new Set(prev.map((r) => r.id))
          return [...prev, ...items.filter((r) => !seen.has(r.id))]
        })
      } else {
        // [2026-09-22 수정] 새로 받은 목록이 비어 있고 이미 화면에 기록이 있으면
        // 기존 기록을 지우지 않는다. (일시적인 조회 실패로 기록이 사라져 보이던 문제)
        setRecords((prev) => (items.length === 0 && prev.length > 0 ? prev : items))
      }
      setHasMore(items.length === PAGE_LIMIT)
    } catch (e) {
      // [2026-09-22 수정] 예전에는 여기서 아무것도 하지 않아
      // 조회가 실패해도 "아직 분석 기록이 없습니다"로 보였다.
      // 이제 이미 불러온 기록은 그대로 두고, 원인을 화면에 표시한다.
      setError(e.response?.data?.detail ?? e.message ?? '히스토리를 불러오지 못했습니다.')
      setHasMore(false)
    }
  }, [])

  // [2026-09-22 수정] 성장 분석 등 다른 화면에 다녀와도 항상 최신 목록을 다시 불러온다.
  const reload = useCallback(() => {
    setPage(1)
    setLoading(true)
    loadPage(1).finally(() => setLoading(false))
  }, [loadPage])

  useEffect(() => {
    queueMicrotask(reload)

    // 탭으로 돌아왔을 때도 새로고침
    function onVisible() {
      if (document.visibilityState === 'visible') loadPage(1)
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [reload, loadPage])

  async function handleLoadMore() {
    const next = page + 1
    setLoadingMore(true)
    await loadPage(next, true)
    setPage(next)
    setLoadingMore(false)
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">발표 히스토리</h1>
          <div className="flex gap-2">
            <button
              onClick={reload}
              className="text-sm text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg px-4 py-2 transition-colors"
            >
              새로고침
            </button>
            <button
              onClick={() => navigate('/growth')}
              className="text-sm text-indigo-600 hover:text-indigo-800 border border-indigo-300 rounded-lg px-4 py-2 transition-colors"
            >
              성장 분석
            </button>
            <button
              onClick={() => navigate('/')}
              className="text-sm text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg px-4 py-2 transition-colors"
            >
              처음으로
            </button>
          </div>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-white border border-gray-100 rounded-2xl px-5 py-4 animate-pulse">
                <div className="h-3 bg-gray-200 rounded w-32 mb-3" />
                <div className="flex gap-4">
                  <div className="h-4 bg-gray-200 rounded w-24" />
                  <div className="h-4 bg-gray-200 rounded w-20" />
                  <div className="h-4 bg-gray-200 rounded w-20" />
                </div>
              </div>
            ))}
          </div>
        ) : records.length === 0 ? (
          <div className="text-center py-20">
            {/* [2026-09-22 수정] 조회 실패와 "정말 기록이 없음"을 구분해서 보여 준다. */}
            {error ? (
              <>
                <p className="text-red-600 font-medium">{error}</p>
                <p className="mt-2 text-sm text-gray-500">
                  기록이 삭제된 것이 아니라 불러오기에 실패한 것입니다. 서버 로그를 확인해 주세요.
                </p>
                <button
                  onClick={reload}
                  className="mt-6 rounded-lg bg-indigo-600 px-6 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
                >
                  다시 불러오기
                </button>
              </>
            ) : (
              <div className="text-gray-400">
                <p className="mb-4 text-4xl">📄</p>
                <p>아직 분석 기록이 없습니다.</p>
              </div>
            )}
          </div>
        ) : (
          <>
            {/* [2026-09-22 추가] 서버가 알려준 전체 건수. 화면 개수와 다르면 표시 쪽 문제다. */}
            {total != null && (
              <p className="mb-3 text-xs text-gray-400">
                전체 {total}건 중 {records.length}건 표시 중
              </p>
            )}
            {error && (
              <p className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                일부 기록을 불러오지 못했습니다: {error}
              </p>
            )}

            <div className="space-y-3">
              {records.map((r) => {
                const date = new Date(r.created_at).toLocaleString('ko-KR')
                const gaze = (num(r.gaze_away_ratio) * 100).toFixed(0)
                return (
                  <button
                    key={r.id}
                    onClick={() => setSelected(r)}
                    className="w-full text-left bg-white border border-gray-200 rounded-2xl px-5 py-4 hover:border-indigo-300 hover:shadow-sm transition-all group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-400">{date}</span>
                      <div className="flex items-center gap-2">
                        {r.score_total != null && <ScoreBadge score={r.score_total} />}
                        <span className="text-xs text-indigo-500 group-hover:underline">자세히 보기 →</span>
                      </div>
                    </div>
                    <div className="flex gap-4 mt-2">
                      <span className={`text-sm font-semibold ${statusColor(r.gaze_away_ratio, [0.15, 0.3])}`}>
                        시선 이탈 {gaze}%
                      </span>
                      <span className={`text-sm font-semibold ${statusColor(r.shoulder_tilt_avg, [8, 15])}`}>
                        어깨 {num(r.shoulder_tilt_avg).toFixed(1)}도
                      </span>
                      <span className="text-sm font-semibold text-gray-600">
                        제스처 {num(r.gesture_count)}회
                      </span>
                    </div>
                    {r.coaching && (
                      <p className="text-xs text-gray-400 mt-1 truncate">{r.coaching.split('\n')[0]}</p>
                    )}
                  </button>
                )
              })}
            </div>

            {hasMore && (
              <div className="mt-6 text-center">
                <button
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  className="text-sm text-indigo-600 hover:text-indigo-800 border border-indigo-300 rounded-lg px-6 py-2 transition-colors disabled:opacity-50"
                >
                  {loadingMore ? '불러오는 중...' : '더 보기'}
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {selected && <DetailPanel item={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
