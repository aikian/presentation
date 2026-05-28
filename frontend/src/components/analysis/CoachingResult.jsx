import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine,
} from 'recharts'
import { downloadPdf } from '../../api/client'

const SECTION_ORDER = [
  { key: 'summary', title: '한줄 요약' },
  { key: 'gaze', title: '시선', visualType: 'gaze', evidenceTitle: '시선 이탈 장면' },
  { key: 'pose', title: '자세', visualType: 'pose', evidenceTitle: '자세 기울어짐 장면' },
  { key: 'gesture', title: '제스처' },
  { key: 'focus', title: '집중도' },
  { key: 'speech', title: '발화' },
  { key: 'priority', title: '다음 연습 우선순위' },
]

const HEADING_ALIASES = {
  '한줄 요약': 'summary',
  요약: 'summary',
  시선: 'gaze',
  '시선 이탈': 'gaze',
  자세: 'pose',
  '자세 기울어짐': 'pose',
  제스처: 'gesture',
  손동작: 'gesture',
  집중도: 'focus',
  눈감음: 'focus',
  발화: 'speech',
  침묵: 'speech',
  '다음 연습 우선순위': 'priority',
  우선순위: 'priority',
}

const STATUS_STYLE = {
  good: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  warn: 'border-amber-200 bg-amber-50 text-amber-800',
  bad: 'border-rose-200 bg-rose-50 text-rose-800',
}

const SCORE_COLOR = {
  good: 'bg-emerald-500',
  warn: 'bg-amber-500',
  bad: 'bg-rose-500',
}

function toNumber(value, fallback = 0) {
  const next = Number(value)
  return Number.isFinite(next) ? next : fallback
}

function score(raw, good, bad) {
  return Math.round(Math.max(0, Math.min(100, (1 - (raw - good) / (bad - good)) * 100)))
}

function MetricCard({ label, value, unit, status }) {
  return (
    <div className={`rounded-lg border p-4 ${STATUS_STYLE[status]}`}>
      <div className="text-2xl font-bold">
        {value}
        <span className="ml-1 text-sm font-normal">{unit}</span>
      </div>
      <div className="mt-1 text-sm opacity-80">{label}</div>
    </div>
  )
}

function scoreStatus(value) {
  if (value >= 70) return 'good'
  if (value >= 50) return 'warn'
  return 'bad'
}

function ScoreBar({ label, score, weight }) {
  const value = Math.max(0, Math.min(100, toNumber(score)))
  const status = scoreStatus(value)

  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="font-semibold text-slate-700">{label}</span>
        <span className="text-slate-500">{value}점 · {weight}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${SCORE_COLOR[status]}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}

function buildFocusItems(metrics) {
  const items = [
    {
      label: '시선',
      value: `${Math.round(metrics.gazeRatio * 100)}% 이탈`,
      severity: metrics.gazeRatio > 0.3 ? 3 : metrics.gazeRatio > 0.15 ? 2 : 1,
      detail: metrics.gazeRatio > 0.15 ? '카메라 응시 리듬을 먼저 잡는 게 좋습니다.' : '시선 처리는 안정적입니다.',
    },
    {
      label: '자세',
      value: `${metrics.tilt.toFixed(1)}도`,
      severity: metrics.tilt > 15 ? 3 : metrics.tilt > 8 ? 2 : 1,
      detail: metrics.tilt > 8 ? '상체 중심과 어깨 수평을 더 자주 점검하세요.' : '자세 균형은 좋은 편입니다.',
    },
    {
      label: '제스처',
      value: `${metrics.gestures}회`,
      severity: metrics.gestures < 5 || metrics.gestures > 50 ? 2 : 1,
      detail: metrics.gestures < 5 ? '핵심 포인트에 손동작을 붙이면 전달력이 올라갑니다.' : metrics.gestures > 50 ? '반복 손동작을 줄이고 강조 지점에만 쓰세요.' : '제스처 빈도는 적절합니다.',
    },
    {
      label: '발화',
      value: `${Math.round(metrics.silenceRatio * 100)}% 침묵`,
      severity: metrics.silenceRatio > 0.5 ? 3 : metrics.silenceRatio > 0.25 ? 2 : 1,
      detail: metrics.silenceRatio > 0.5 ? '슬라이드 전환 문장을 미리 정해 흐름을 이어가세요.' : '발화 흐름은 크게 무너지지 않았습니다.',
    },
  ]

  return items.sort((a, b) => b.severity - a.severity).slice(0, 3)
}

function AnalysisOverview({ metrics, scores }) {
  const focusItems = buildFocusItems(metrics)
  const totalStatus = scores.total == null ? 'warn' : scoreStatus(scores.total)

  return (
    <section className="grid gap-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm lg:grid-cols-[220px_minmax(0,1fr)]">
      <div className="flex flex-col justify-between rounded-lg bg-slate-950 p-5 text-white">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Total Score</p>
          <div className="mt-2 flex items-end gap-1">
            <span className="text-5xl font-bold leading-none">{scores.total ?? '-'}</span>
            <span className="pb-1 text-sm text-slate-300">/ 100</span>
          </div>
        </div>
        <div className={`mt-5 h-1.5 rounded-full ${SCORE_COLOR[totalStatus]}`} />
      </div>

      <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_minmax(220px,0.8fr)]">
        <div>
          <h2 className="mb-3 text-lg font-bold text-slate-950">핵심 진단</h2>
          <div className="grid gap-2">
            {focusItems.map((item) => (
              <div key={item.label} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-bold text-slate-900">{item.label}</span>
                  <span className="text-xs font-semibold text-slate-500">{item.value}</span>
                </div>
                <p className="mt-1 text-xs leading-5 text-slate-600">{item.detail}</p>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h2 className="mb-3 text-lg font-bold text-slate-950">항목별 점수</h2>
          <div className="space-y-3">
            <ScoreBar label="시선" score={scores.gaze} weight="30%" />
            <ScoreBar label="자세" score={scores.pose} weight="25%" />
            <ScoreBar label="제스처" score={scores.gesture} weight="15%" />
            <ScoreBar label="시간" score={scores.time} weight="30%" />
          </div>
        </div>
      </div>
    </section>
  )
}

function headingToKey(rawTitle) {
  const normalized = rawTitle.replace(/[#*_`]/g, '').trim()
  if (HEADING_ALIASES[normalized]) return HEADING_ALIASES[normalized]
  const found = Object.entries(HEADING_ALIASES).find(([label]) => normalized.includes(label))
  return found?.[1] ?? 'summary'
}

function parseCoachingSections(coaching = '') {
  const sections = Object.fromEntries(SECTION_ORDER.map(({ key }) => [key, []]))
  let current = 'summary'
  let hasHeading = false

  coaching.split(/\r?\n/).forEach((line) => {
    const heading = line.match(/^#{1,3}\s+(.+?)\s*$/)
    if (heading) {
      current = headingToKey(heading[1])
      hasHeading = true
      return
    }

    if (!hasHeading) {
      const colon = line.match(/^(시선|자세|제스처|집중도|발화)\s*[:：]\s*(.+)$/)
      if (colon) {
        current = headingToKey(colon[1])
        sections[current].push(`**진단:** ${colon[2]}`)
        return
      }
    }

    sections[current].push(line)
  })

  return Object.fromEntries(
    Object.entries(sections).map(([key, lines]) => [key, lines.join('\n').trim()]),
  )
}

function fallbackSectionText(key, metrics) {
  const gazePct = Math.round(metrics.gazeRatio * 100)
  const tilt = metrics.tilt.toFixed(1)
  const blinkPct = Math.round(metrics.blinkRatio * 100)
  const silencePct = Math.round(metrics.silenceRatio * 100)

  const fallback = {
    summary: `- 시선 ${gazePct}%, 자세 ${tilt}도, 제스처 ${metrics.gestures}회를 기준으로 다음 연습 포인트를 정리했습니다.`,
    gaze: `**진단:** 시선 이탈률은 ${gazePct}%입니다.\n**코칭:** 핵심 문장을 말할 때 카메라를 먼저 보고, 슬라이드는 문장 사이에 짧게 확인하세요.`,
    pose: `**진단:** 어깨 기울기는 평균 ${tilt}도입니다.\n**코칭:** 카메라 중앙에 코와 명치를 맞추고, 문단이 바뀔 때마다 어깨 높이를 점검하세요.`,
    gesture: `**진단:** 제스처는 ${metrics.gestures}회 감지되었습니다.\n**코칭:** 숫자, 방향, 크기처럼 의미가 분명한 순간에만 손동작을 붙여 강조하세요.`,
    focus: `**진단:** 눈 감음 비율은 ${blinkPct}%입니다.\n**코칭:** 문장을 시작할 때 카메라를 또렷하게 보고, 말끝에서 시선을 떨어뜨리지 않도록 연습하세요.`,
    speech: `**진단:** 침묵 구간 비율은 ${silencePct}%입니다.\n**코칭:** 슬라이드별 첫 문장과 연결 문장을 미리 정해 발표 흐름이 끊기지 않게 하세요.`,
    priority: '1. 가장 낮은 지표 하나를 정해 다음 녹화에서 집중적으로 개선하세요.\n2. 발표 시작과 결론에서 카메라 응시를 의식적으로 유지하세요.',
  }

  return fallback[key]
}

function normalizeFrames(problemFrames = []) {
  return problemFrames.map((frame, index) => {
    if (typeof frame === 'string') {
      return { type: null, label: `문제 장면 ${index + 1}`, image: frame }
    }
    return {
      type: frame.type ?? null,
      label: frame.label ?? `문제 장면 ${index + 1}`,
      sec: frame.sec,
      image: frame.image ?? frame.b64 ?? frame.data ?? '',
    }
  }).filter((frame) => frame.image)
}

function frameSrc(frame) {
  if (frame.image.startsWith('data:')) return frame.image
  return `data:image/jpeg;base64,${frame.image}`
}

function framesForType(frames, type) {
  const typed = frames.filter((frame) => frame.type === type)
  if (typed.length > 0) {
    return typed
      .slice()
      .sort((a, b) => toNumber(b.score) - toNumber(a.score))
      .slice(0, 1)
  }

  const legacyFrames = frames.filter((frame) => !frame.type)
  if (type === 'gaze') return legacyFrames.slice(0, 1)
  if (type === 'pose') return legacyFrames.slice(3, 4)
  return []
}

function renderInline(text) {
  return text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index} className="font-semibold text-slate-950">{part.slice(2, -2)}</strong>
    }
    return <span key={index}>{part}</span>
  })
}

function MarkdownBlocks({ text }) {
  const blocks = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)

  return (
    <div className="space-y-2 text-sm leading-6 text-slate-700">
      {blocks.map((line, index) => {
        const bullet = line.match(/^[-*]\s+(.+)$/)
        if (bullet) {
          return (
            <div key={index} className="flex gap-2">
              <span className="mt-[0.55rem] h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400" />
              <p>{renderInline(bullet[1])}</p>
            </div>
          )
        }

        const numbered = line.match(/^(\d+)\.\s+(.+)$/)
        if (numbered) {
          return (
            <div key={index} className="flex gap-2">
              <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-slate-900 px-1 text-[11px] font-semibold text-white">
                {numbered[1]}
              </span>
              <p>{renderInline(numbered[2])}</p>
            </div>
          )
        }

        return <p key={index}>{renderInline(line)}</p>
      })}
    </div>
  )
}

function EvidencePanel({ title, frames }) {
  if (!frames.length) {
    return (
      <div className="flex min-h-40 items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 text-center text-xs text-slate-500">
        감지된 장면 없음
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-slate-500">{title}</p>
      <div className="grid gap-2">
        {frames.slice(0, 1).map((frame, index) => (
          <figure key={`${frame.type}-${frame.sec}-${index}`} className="overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
            <img
              src={frameSrc(frame)}
              alt={frame.label}
              className="aspect-video w-full object-cover"
            />
            <figcaption className="flex items-center justify-between px-2 py-1.5 text-xs text-slate-500">
              <span>{frame.label}</span>
              <span>{frame.value ?? (frame.sec != null ? `${frame.sec}초` : '최대 구간')}</span>
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  )
}

function CoachingSection({ meta, text, frames }) {
  const hasEvidence = Boolean(meta.visualType)

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className={hasEvidence ? 'grid gap-4 md:grid-cols-[minmax(0,1fr)_260px]' : ''}>
        <div>
          <h3 className="mb-3 text-base font-bold text-slate-950">{meta.title}</h3>
          <MarkdownBlocks text={text} />
        </div>
        {hasEvidence && (
          <EvidencePanel title={meta.evidenceTitle} frames={frames} />
        )}
      </div>
    </section>
  )
}

export default function CoachingResult({ result, resultId }) {
  const navigate = useNavigate()
  const [downloading, setDownloading] = useState(false)
  const {
    gaze_away_ratio, shoulder_tilt_avg, gesture_count,
    ear_blink_ratio, silence_ratio, gaze_timeline, problem_frames, coaching,
    score_total, score_gaze, score_pose, score_gesture, score_time,
  } = result

  const metrics = {
    gazeRatio: toNumber(gaze_away_ratio),
    tilt: toNumber(shoulder_tilt_avg),
    gestures: toNumber(gesture_count),
    blinkRatio: toNumber(ear_blink_ratio),
    silenceRatio: toNumber(silence_ratio),
  }

  const gazeStatus = metrics.gazeRatio > 0.3 ? 'bad' : metrics.gazeRatio > 0.15 ? 'warn' : 'good'
  const tiltStatus = metrics.tilt > 15 ? 'bad' : metrics.tilt > 8 ? 'warn' : 'good'
  const gestureStatus = metrics.gestures < 5 || metrics.gestures > 50 ? 'warn' : 'good'

  const radarData = [
    { subject: '시선', score: score(metrics.gazeRatio, 0, 0.4) },
    { subject: '자세', score: score(metrics.tilt, 0, 20) },
    { subject: '제스처', score: metrics.gestures < 5 || metrics.gestures > 50 ? 55 : 90 },
    { subject: '집중도', score: score(metrics.blinkRatio, 0, 0.5) },
    { subject: '발화', score: score(metrics.silenceRatio, 0, 0.7) },
  ]

  const parsedSections = useMemo(() => parseCoachingSections(coaching), [coaching])
  const frames = useMemo(() => normalizeFrames(problem_frames), [problem_frames])
  const scores = {
    total: score_total == null ? null : toNumber(score_total),
    gaze: score_gaze == null ? score(metrics.gazeRatio, 0, 0.4) : toNumber(score_gaze),
    pose: score_pose == null ? score(metrics.tilt, 0, 20) : toNumber(score_pose),
    gesture: score_gesture == null ? (metrics.gestures < 5 || metrics.gestures > 50 ? 55 : 90) : toNumber(score_gesture),
    time: score_time == null ? score(metrics.silenceRatio, 0, 0.7) : toNumber(score_time),
  }

  async function handleDownload() {
    if (!resultId) return
    setDownloading(true)
    try { await downloadPdf(resultId) } finally { setDownloading(false) }
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8 text-left">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-indigo-600">PresentationCoach</p>
            <h1 className="mt-1 text-3xl font-bold text-slate-950">분석 결과</h1>
          </div>
          <div className="flex gap-2">
            {resultId && (
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="rounded-lg border border-indigo-300 px-4 py-2 text-sm font-semibold text-indigo-700 transition-colors hover:bg-indigo-50 disabled:opacity-50"
              >
                {downloading ? '생성 중...' : 'PDF 저장'}
              </button>
            )}
            <button
              onClick={() => navigate('/')}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-white"
            >
              처음으로
            </button>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <MetricCard label="시선 이탈률" value={`${(metrics.gazeRatio * 100).toFixed(0)}%`} unit="" status={gazeStatus} />
          <MetricCard label="어깨 기울기" value={metrics.tilt.toFixed(1)} unit="도" status={tiltStatus} />
          <MetricCard label="제스처 횟수" value={metrics.gestures} unit="회" status={gestureStatus} />
        </div>

        <AnalysisOverview metrics={metrics} scores={scores} />

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(360px,0.85fr)]">
          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-4 text-lg font-bold text-slate-950">종합 점수</h2>
            <ResponsiveContainer width="100%" height={240}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12 }} />
                <Radar dataKey="score" stroke="#4f46e5" fill="#4f46e5" fillOpacity={0.28} />
              </RadarChart>
            </ResponsiveContainer>
          </section>

          {gaze_timeline?.length > 1 && (
            <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-4 text-lg font-bold text-slate-950">시선 이탈 추이</h2>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={gaze_timeline} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <XAxis dataKey="sec" tickFormatter={(v) => `${v}s`} tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => [`${(v * 100).toFixed(0)}%`, '이탈']} labelFormatter={(v) => `${v}초`} />
                  <ReferenceLine y={0.35} stroke="#f59e0b" strokeDasharray="4 2" label={{ value: '기준', fontSize: 10 }} />
                  <Line type="monotone" dataKey="score" stroke="#4f46e5" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </section>
          )}
        </div>

        <div>
          <h2 className="mb-3 text-xl font-bold text-slate-950">AI 코칭</h2>
          <div className="space-y-3">
            {SECTION_ORDER.map((meta) => (
              <CoachingSection
                key={meta.key}
                meta={meta}
                text={parsedSections[meta.key] || fallbackSectionText(meta.key, metrics)}
                frames={meta.visualType ? framesForType(frames, meta.visualType) : []}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
