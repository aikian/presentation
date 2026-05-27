import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchHistory, downloadPdf } from '../api/client'

function statusColor(val, thresholds) {
  if (val > thresholds[1]) return 'text-red-600'
  if (val > thresholds[0]) return 'text-yellow-600'
  return 'text-green-600'
}

function DetailPanel({ item, onClose }) {
  const [downloading, setDownloading] = useState(false)
  const { id, gaze_away_ratio, shoulder_tilt_avg, gesture_count, coaching, created_at } = item
  const date = new Date(created_at).toLocaleString('ko-KR')

  async function handleDownload() {
    setDownloading(true)
    try { await downloadPdf(id) } finally { setDownloading(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">분석 상세</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="text-sm text-indigo-600 hover:text-indigo-800 border border-indigo-300 rounded-lg px-3 py-1 transition-colors disabled:opacity-50"
            >
              {downloading ? '생성 중...' : 'PDF 저장'}
            </button>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
          </div>
        </div>
        <p className="text-xs text-gray-400 mb-4">{date}</p>
        <div className="grid grid-cols-3 gap-3 mb-5">
          {[
            { label: '시선 이탈률', value: `${(gaze_away_ratio * 100).toFixed(0)}%`, thresholds: [0.15, 0.3], raw: gaze_away_ratio },
            { label: '어깨 기울기', value: `${shoulder_tilt_avg.toFixed(1)}도`, thresholds: [8, 15], raw: shoulder_tilt_avg },
            { label: '제스처', value: `${gesture_count}회`, thresholds: [5, 50], raw: gesture_count < 5 ? 0 : gesture_count > 50 ? 100 : 10 },
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

export default function History() {
  const navigate = useNavigate()
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    fetchHistory()
      .then(setRecords)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">발표 히스토리</h1>
          <button
            onClick={() => navigate('/')}
            className="text-sm text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg px-4 py-2 transition-colors"
          >
            처음으로
          </button>
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
          <div className="text-center text-gray-400 py-20">
            <p className="text-4xl mb-4">📭</p>
            <p>아직 분석 기록이 없습니다.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {records.map((r) => {
              const date = new Date(r.created_at).toLocaleString('ko-KR')
              const gaze = (r.gaze_away_ratio * 100).toFixed(0)
              return (
                <button
                  key={r.id}
                  onClick={() => setSelected(r)}
                  className="w-full text-left bg-white border border-gray-200 rounded-2xl px-5 py-4 hover:border-indigo-300 hover:shadow-sm transition-all group"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">{date}</span>
                    <span className="text-xs text-indigo-500 group-hover:underline">자세히 보기 →</span>
                  </div>
                  <div className="flex gap-4 mt-2">
                    <span className={`text-sm font-semibold ${statusColor(r.gaze_away_ratio, [0.15, 0.3])}`}>
                      시선 이탈 {gaze}%
                    </span>
                    <span className={`text-sm font-semibold ${statusColor(r.shoulder_tilt_avg, [8, 15])}`}>
                      어깨 {r.shoulder_tilt_avg.toFixed(1)}도
                    </span>
                    <span className="text-sm font-semibold text-gray-600">
                      제스처 {r.gesture_count}회
                    </span>
                  </div>
                  {r.coaching && (
                    <p className="text-xs text-gray-400 mt-1 truncate">{r.coaching.split('\n')[0]}</p>
                  )}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {selected && <DetailPanel item={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
