import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine,
} from 'recharts'
import { downloadPdf } from '../../api/client'

function MetricCard({ label, value, unit, status }) {
  const colors = {
    good: 'bg-green-50 border-green-200 text-green-700',
    warn: 'bg-yellow-50 border-yellow-200 text-yellow-700',
    bad: 'bg-red-50 border-red-200 text-red-700',
  }
  return (
    <div className={`border rounded-xl p-4 ${colors[status]}`}>
      <div className="text-2xl font-bold">
        {value}
        <span className="text-sm font-normal ml-1">{unit}</span>
      </div>
      <div className="text-sm mt-1 opacity-80">{label}</div>
    </div>
  )
}

function score(raw, good, bad) {
  // 낮을수록 좋은 지표: good=0 → 100점, bad 이상 → 0점
  return Math.round(Math.max(0, Math.min(100, (1 - (raw - good) / (bad - good)) * 100)))
}

export default function CoachingResult({ result, resultId }) {
  const navigate = useNavigate()
  const [downloading, setDownloading] = useState(false)
  const {
    gaze_away_ratio, shoulder_tilt_avg, gesture_count,
    ear_blink_ratio, silence_ratio, gaze_timeline, problem_frames, coaching,
  } = result

  const gazeStatus = gaze_away_ratio > 0.3 ? 'bad' : gaze_away_ratio > 0.15 ? 'warn' : 'good'
  const tiltStatus = shoulder_tilt_avg > 15 ? 'bad' : shoulder_tilt_avg > 8 ? 'warn' : 'good'
  const gestureStatus = gesture_count < 5 || gesture_count > 50 ? 'warn' : 'good'

  // 레이더 차트 데이터 (0~100, 높을수록 좋음)
  const radarData = [
    { subject: '시선', score: score(gaze_away_ratio, 0, 0.4) },
    { subject: '자세', score: score(shoulder_tilt_avg, 0, 20) },
    { subject: '제스처', score: gesture_count < 5 || gesture_count > 50 ? 55 : 90 },
    { subject: '집중도', score: ear_blink_ratio != null ? score(ear_blink_ratio, 0, 0.5) : 80 },
    { subject: '발화', score: silence_ratio != null ? score(silence_ratio, 0, 0.7) : 80 },
  ]

  async function handleDownload() {
    if (!resultId) return
    setDownloading(true)
    try { await downloadPdf(resultId) } finally { setDownloading(false) }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* 헤더 */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">분석 결과</h1>
          <div className="flex gap-2">
            {resultId && (
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="text-sm text-indigo-600 hover:text-indigo-800 border border-indigo-300 rounded-lg px-4 py-2 transition-colors disabled:opacity-50"
              >
                {downloading ? '생성 중...' : 'PDF 저장'}
              </button>
            )}
            <button
              onClick={() => navigate('/')}
              className="text-sm text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg px-4 py-2 transition-colors"
            >
              처음으로
            </button>
          </div>
        </div>

        {/* 지표 카드 */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <MetricCard label="시선 이탈률" value={`${(gaze_away_ratio * 100).toFixed(0)}%`} unit="" status={gazeStatus} />
          <MetricCard label="어깨 기울기" value={shoulder_tilt_avg.toFixed(1)} unit="도" status={tiltStatus} />
          <MetricCard label="제스처 횟수" value={gesture_count} unit="회" status={gestureStatus} />
        </div>

        {/* 레이더 차트 */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 mb-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">종합 점수</h2>
          <ResponsiveContainer width="100%" height={240}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12 }} />
              <Radar dataKey="score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* 시선 이탈 타임라인 */}
        {gaze_timeline?.length > 1 && (
          <div className="bg-white border border-gray-200 rounded-2xl p-6 mb-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">시선 이탈 추이</h2>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={gaze_timeline} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <XAxis dataKey="sec" tickFormatter={(v) => `${v}s`} tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => [`${(v * 100).toFixed(0)}%`, '이탈']} labelFormatter={(v) => `${v}초`} />
                <ReferenceLine y={0.35} stroke="#f59e0b" strokeDasharray="4 2" label={{ value: '기준', fontSize: 10 }} />
                <Line type="monotone" dataKey="score" stroke="#6366f1" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* AI 코칭 */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 mb-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <span>🤖</span> AI 코칭
          </h2>
          <div className="text-gray-700 text-sm leading-relaxed whitespace-pre-line">{coaching}</div>
        </div>

        {/* 문제 프레임 */}
        {problem_frames?.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-2xl p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">주요 개선 구간</h2>
            <div className="grid grid-cols-2 gap-3">
              {problem_frames.map((b64, i) => (
                <img
                  key={i}
                  src={`data:image/jpeg;base64,${b64}`}
                  alt={`문제 장면 ${i + 1}`}
                  className="rounded-lg border border-gray-200 w-full object-cover"
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
