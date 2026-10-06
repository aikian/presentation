import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { fetchGrowth } from '../api/client'

// 그래프에 그릴 수 있는 지표. 기본은 총점만 켜 두고 나머지는 선택(계획서: 핵심 지표 우선, 상세는 선택).
const SERIES = [
  { key: 'score_total', label: '총점', color: '#4f46e5' },
  { key: 'score_gaze', label: '시선', color: '#0ea5e9' },
  { key: 'score_pose', label: '자세', color: '#10b981' },
  { key: 'score_gesture', label: '제스처', color: '#f59e0b' },
  { key: 'score_time', label: '시간', color: '#ec4899' },
]

const VERDICT_STYLE = {
  improved: { text: '개선', cls: 'bg-green-100 text-green-700' },
  declined: { text: '하락', cls: 'bg-red-100 text-red-700' },
  same: { text: '변화 없음', cls: 'bg-gray-100 text-gray-500' },
  changed: { text: '변화', cls: 'bg-blue-100 text-blue-700' },
}

function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function signed(n) {
  return n > 0 ? `+${n}` : `${n}`
}

// "## 제목" 줄은 소제목으로, 나머지는 문단으로 그린다.
function FeedbackText({ text }) {
  return (
    <div className="space-y-1 text-sm leading-relaxed text-gray-700">
      {text.split('\n').map((line, i) => {
        if (line.startsWith('## ')) {
          return <p key={i} className="mt-3 font-semibold text-gray-900 first:mt-0">{line.slice(3)}</p>
        }
        if (!line.trim()) return null
        return <p key={i}>{line}</p>
      })}
    </div>
  )
}

function CompareTable({ metrics }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="w-full min-w-[28rem] text-sm">
        <thead className="bg-gray-50 text-gray-500">
          <tr>
            <th className="px-3 py-2 text-left font-medium">항목</th>
            <th className="px-3 py-2 text-right font-medium">이전</th>
            <th className="px-3 py-2 text-right font-medium">현재</th>
            <th className="px-3 py-2 text-right font-medium">변화</th>
            <th className="px-3 py-2 text-right font-medium">판정</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => {
            const v = VERDICT_STYLE[m.verdict] ?? VERDICT_STYLE.changed
            return (
              <tr key={m.key} className="border-t border-gray-100">
                <td className="px-3 py-2 font-medium text-gray-800">{m.label}</td>
                <td className="px-3 py-2 text-right text-gray-500">{m.previous}{m.unit}</td>
                <td className="px-3 py-2 text-right text-gray-900">{m.current}{m.unit}</td>
                <td className="px-3 py-2 text-right text-gray-700">{signed(m.delta)}{m.unit}</td>
                <td className="px-3 py-2 text-right">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${v.cls}`}>{v.text}</span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function Growth() {
  const navigate = useNavigate()
  const [growth, setGrowth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [active, setActive] = useState(['score_total'])

  // [2026-09-22 수정] AI 피드백 호출이 실패해도 그래프는 반드시 그려지게 한다.
  // 1차로 AI 포함 요청, 실패하면 ai=false로 재시도해서 최소한 trend/비교표는 살린다.
  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const res = await fetchGrowth(10, true)
        if (!cancelled) setGrowth(res.growth)
      } catch {
        try {
          const res = await fetchGrowth(10, false)
          if (!cancelled) setGrowth(res.growth)
        } catch (e2) {
          if (!cancelled) setError(e2.response?.data?.detail ?? '성장 분석을 불러오지 못했습니다.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [])

  const chartData = useMemo(
    () =>
      (growth?.trend ?? []).map((p, i) => ({
        name: `${i + 1}회`,
        date: fmtDate(p.created_at),
        ...p,
      })),
    [growth],
  )

  // 채점 기준(weights_version)이 섞여 있으면 총점 그래프가 공정하지 않다는 안내를 띄운다.
  const mixedWeights = useMemo(
    () => new Set((growth?.trend ?? []).map((p) => p.weights_version ?? 'none')).size > 1,
    [growth],
  )

  function toggle(key) {
    setActive((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]))
  }

  const compare = growth?.compare_with_previous

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="mx-auto max-w-3xl">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">발표 성장 분석</h1>
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/history')}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-500 transition-colors hover:text-gray-700"
            >
              히스토리
            </button>
            <button
              onClick={() => navigate('/')}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-500 transition-colors hover:text-gray-700"
            >
              처음으로
            </button>
          </div>
        </div>

        {loading && (
          <div className="animate-pulse space-y-4">
            <div className="h-64 rounded-2xl bg-gray-200" />
            <div className="h-32 rounded-2xl bg-gray-200" />
          </div>
        )}

        {!loading && error && <p className="py-20 text-center text-red-600">{error}</p>}

        {!loading && !error && growth && growth.session_count === 0 && (
          <div className="py-20 text-center text-gray-400">
            <p className="mb-4 text-4xl">📈</p>
            <p>아직 분석 기록이 없습니다. 발표 영상을 분석하면 성장 그래프가 만들어져요.</p>
            <button
              onClick={() => navigate('/analysis')}
              className="mt-6 rounded-lg bg-purple-600 px-6 py-2 text-white hover:bg-purple-500"
            >
              영상 분석하러 가기
            </button>
          </div>
        )}

        {!loading && !error && growth && growth.session_count > 0 && (
          <div className="space-y-6">
            {/* 1. 그래프 */}
            <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg font-bold text-gray-900">점수 변화 추이</h2>
                <div className="flex flex-wrap gap-1.5">
                  {SERIES.map((s) => {
                    const on = active.includes(s.key)
                    return (
                      <button
                        key={s.key}
                        onClick={() => toggle(s.key)}
                        className={`rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${
                          on ? 'text-white' : 'bg-white text-gray-500 hover:bg-gray-50'
                        }`}
                        style={on ? { backgroundColor: s.color, borderColor: s.color } : undefined}
                      >
                        {s.label}
                      </button>
                    )
                  })}
                </div>
              </div>

              {growth.session_count < 2 && (
                <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">
                  발표가 2회 이상 쌓이면 이전 발표와의 비교와 AI 성장 피드백이 제공됩니다.
                </p>
              )}
              {mixedWeights && (
                <p className="mb-3 rounded-lg bg-blue-50 px-3 py-2 text-xs text-blue-700">
                  채점 기준(가중치)이 바뀐 발표가 섞여 있어 총점끼리의 단순 비교는 정확하지 않을 수 있어요. 개별 지표를 함께 확인해 주세요.
                </p>
              )}

              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={chartData} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                  <Tooltip
                    labelFormatter={(label, payload) => `${label}${payload?.[0]?.payload?.date ? ` (${payload[0].payload.date})` : ''}`}
                    formatter={(value, name) => [value == null ? '-' : `${value}점`, name]}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {SERIES.filter((s) => active.includes(s.key)).map((s) => (
                    <Line
                      key={s.key}
                      type="monotone"
                      dataKey={s.key}
                      name={s.label}
                      stroke={s.color}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </section>

            {/* 2. 직전 발표와 비교 */}
            {compare && (
              <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
                <h2 className="mb-1 text-lg font-bold text-gray-900">직전 발표와 비교</h2>
                <p className="mb-4 text-xs text-gray-400">
                  {/* [2026-09-22 수정] 필드가 없어도 화면이 깨지지 않게 방어 */}
                  {(compare.improved ?? []).length}개 항목 개선 · {(compare.declined ?? []).length}개 항목 하락
                </p>
                {(compare.metrics ?? []).length > 0 ? (
                  <CompareTable metrics={compare.metrics} />
                ) : (
                  <p className="text-sm text-gray-400">비교할 수 있는 지표가 아직 없습니다.</p>
                )}
              </section>
            )}

            {/* 3. AI 성장 피드백 */}
            {growth.feedback && (
              <section className="rounded-2xl border border-indigo-100 bg-indigo-50/60 p-5">
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-lg font-bold text-indigo-950">성장 피드백</h2>
                  <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-indigo-600">
                    {growth.feedback_source === 'ai' ? 'AI 분석' : '기본 분석'}
                  </span>
                </div>
                <FeedbackText text={growth.feedback} />
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
