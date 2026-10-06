import { useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceArea, CartesianGrid,
} from 'recharts'

// 음성 탭. details.audio와 details.x_voice_score를 읽는다.
//
// 점수만 보여주면 "왜 이 점수냐"에 답할 수 없다.
// 지표마다 내 값과 명연사 범위를 나란히 두고, 깎인 점수와 그 이유까지 같이 보여준다.

const EMPTY = '측정되지 않음'

function fmt(value, digits = 1, unit = '') {
  if (value == null) return EMPTY
  return `${Number(value).toFixed(digits)}${unit}`
}

function pct(value) {
  if (value == null) return EMPTY
  return `${(Number(value) * 100).toFixed(1)}%`
}

function scoreColor(score) {
  if (score == null) return 'bg-slate-300'
  if (score >= 90) return 'bg-emerald-500'
  if (score >= 70) return 'bg-amber-500'
  return 'bg-rose-500'
}

/** 내 값이 명연사 범위 안에서 어디쯤인지 막대로 보여준다. */
function RangeBar({ value, min, max }) {
  if (value == null || min == null || max == null) return null

  // 범위 폭의 60%만큼 양옆을 더 그려서, 벗어난 값도 화면 안에 들어오게 한다.
  const width = max - min
  const left = min - width * 0.6
  const right = max + width * 0.6
  const toPct = (v) => Math.max(0, Math.min(100, ((v - left) / (right - left)) * 100))

  const inRange = value >= min && value <= max

  return (
    <div className="relative mt-2 h-7">
      <div className="absolute inset-x-0 top-3 h-1 rounded bg-slate-200" />
      <div
        className="absolute top-3 h-1 rounded bg-indigo-200"
        style={{ left: `${toPct(min)}%`, width: `${toPct(max) - toPct(min)}%` }}
      />
      <div
        className={`absolute top-1 h-5 w-1 rounded ${inRange ? 'bg-indigo-600' : 'bg-rose-500'}`}
        style={{ left: `${toPct(value)}%` }}
        title={`내 값 ${value}`}
      />
      <div className="absolute top-5 text-[10px] text-slate-400" style={{ left: `${toPct(min)}%` }}>
        {min}
      </div>
      <div className="absolute top-5 text-[10px] text-slate-400" style={{ left: `${toPct(max)}%` }}>
        {max}
      </div>
    </div>
  )
}

function MetricRow({ metric, rank }) {
  const { label, value, reference_min, reference_max, score, weight, verdict, concern } = metric

  return (
    <div className={`rounded-lg border p-4 ${concern ? 'border-rose-200 bg-rose-50/40' : 'border-slate-200 bg-white'}`}>
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex items-baseline gap-2">
          <span className="font-semibold text-slate-900">{label}</span>
          <span className="text-xs text-slate-500">종합점수 반영 {Math.round(weight * 100)}%</span>
          {rank != null && (
            <span className="rounded bg-rose-100 px-1.5 py-0.5 text-[11px] font-semibold text-rose-700">
              개선 {rank}순위
            </span>
          )}
        </div>
        <div className="text-right">
          <span className="text-xl font-bold text-slate-900">{score}</span>
          <span className="ml-0.5 text-xs text-slate-500">점</span>
        </div>
      </div>

      <div className="mt-1 text-sm text-slate-600">
        내 값 <b className="text-slate-900">{value}</b>
        <span className="mx-1.5 text-slate-300">|</span>
        명연사 {reference_min} ~ {reference_max}
        <span className="mx-1.5 text-slate-300">|</span>
        <span className={concern ? 'text-rose-700' : 'text-emerald-700'}>{verdict}</span>
      </div>

      <RangeBar value={value} min={reference_min} max={reference_max} />
    </div>
  )
}

/** 1초 단위 말속도·피치 시간축. 필러워드와 침묵 구간을 겹쳐 그린다. */
function AudioTimeline({ timeline, fillerWords, silences }) {
  const data = useMemo(
    () =>
      (timeline || []).map((t) => ({
        sec: t.sec,
        spm: t.spm ?? null,
        pitch: t.pitch_hz ?? t.pitch ?? null,
      })),
    [timeline],
  )

  if (!data.length) {
    return <p className="text-sm text-slate-500">시간축 데이터가 없습니다.</p>
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: -16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          {/* 침묵 구간을 회색 띠로 깔아둔다 */}
          {(silences || []).map((s, i) => (
            <ReferenceArea key={`sil-${i}`} x1={s.start} x2={s.end} fill="#94a3b8" fillOpacity={0.18} />
          ))}
          {/* 군말이 나온 시점을 세로선으로 */}
          {(fillerWords || []).map((f, i) => (
            <ReferenceArea
              key={`fil-${i}`}
              x1={f.sec}
              x2={f.sec + 0.6}
              fill="#f43f5e"
              fillOpacity={0.5}
            />
          ))}
          <XAxis dataKey="sec" unit="s" tick={{ fontSize: 11 }} stroke="#94a3b8" />
          <YAxis yAxisId="spm" tick={{ fontSize: 11 }} stroke="#94a3b8" />
          <YAxis yAxisId="pitch" orientation="right" tick={{ fontSize: 11 }} stroke="#cbd5e1" />
          <Tooltip
            formatter={(v, name) => [v == null ? EMPTY : Math.round(v), name === 'spm' ? '말속도(음절/분)' : '피치(Hz)']}
            labelFormatter={(l) => `${l}초`}
          />
          <Line yAxisId="spm" type="monotone" dataKey="spm" stroke="#4f46e5" dot={false} strokeWidth={2} connectNulls />
          <Line yAxisId="pitch" type="monotone" dataKey="pitch" stroke="#cbd5e1" dot={false} strokeWidth={1.5} connectNulls />
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-1 flex flex-wrap gap-3 text-[11px] text-slate-500">
        <span><i className="mr-1 inline-block h-2 w-3 bg-indigo-600 align-middle" />말속도</span>
        <span><i className="mr-1 inline-block h-2 w-3 bg-slate-300 align-middle" />피치</span>
        <span><i className="mr-1 inline-block h-2 w-3 bg-rose-400 align-middle" />군말</span>
        <span><i className="mr-1 inline-block h-2 w-3 bg-slate-400 align-middle" />침묵 구간</span>
      </div>
    </div>
  )
}

export default function VoiceTab({ details }) {
  const audio = details?.audio ?? null
  const voice = details?.x_voice_score ?? null

  if (!audio) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-8 text-center">
        <p className="font-medium text-slate-700">음성을 분석하지 못했습니다.</p>
        <p className="mt-1 text-sm text-slate-500">
          영상에 소리가 없거나 말소리를 찾지 못한 경우입니다. 점수에서도 제외됩니다.
        </p>
      </div>
    )
  }

  const summary = audio.summary ?? {}
  const priority = voice?.priority ?? []
  const rankOf = (key) => {
    const i = priority.indexOf(key)
    return i < 0 ? null : i + 1
  }

  return (
    <div className="space-y-6">
      {/* 음성 점수와 근거 */}
      {voice && (
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-baseline justify-between">
            <h3 className="text-lg font-bold text-slate-900">음성 점수</h3>
            <div>
              <span className="text-3xl font-bold text-slate-900">{voice.score}</span>
              <span className="ml-1 text-sm text-slate-500">/ 100</span>
            </div>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded bg-slate-100">
            <div className={`h-full ${scoreColor(voice.score)}`} style={{ width: `${voice.score}%` }} />
          </div>
          <p className="mt-3 text-xs leading-relaxed text-slate-500">
            명연사 6명 7편(세바시)의 실측 범위를 기준으로 삼았습니다. 범위 안이면 만점이고, 벗어난
            거리에 비례해 깎입니다. 지표별 반영 비율은 같은 연사의 다른 강연에서 값이 덜 흔들리는
            지표에 더 무게를 뒀습니다.
            {voice.measured_weight < 1 && (
              <>
                {' '}이번 분석에서는 일부 지표를 측정하지 못해, 측정된 지표
                {' '}{Math.round(voice.measured_weight * 100)}%만으로 점수를 냈습니다.
              </>
            )}
          </p>

          <div className="mt-4 space-y-3">
            {voice.metrics.map((m) => (
              <MetricRow key={m.key} metric={m} rank={rankOf(m.key)} />
            ))}
          </div>

          {priority.length > 0 && (
            <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
              <b>먼저 고칠 것:</b>{' '}
              {priority
                .map((key) => voice.metrics.find((m) => m.key === key)?.label)
                .filter(Boolean)
                .join(' → ')}
              <p className="mt-1 text-xs text-slate-500">
                점수를 많이 깎인 순서가 아니라, 종합점수에 미치는 영향이 큰 순서입니다.
              </p>
            </div>
          )}
        </section>
      )}

      {/* 시간축 */}
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-lg font-bold text-slate-900">발표 흐름</h3>
        <p className="mb-3 text-xs text-slate-500">
          1초 단위로 말속도와 피치를 재고, 군말이 나온 시점과 2초 이상 끊긴 구간을 겹쳐 표시했습니다.
        </p>
        <AudioTimeline
          timeline={audio.timeline}
          fillerWords={audio.filler_words}
          silences={audio.silences}
        />
      </section>

      {/* 요약 수치 */}
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="mb-3 text-lg font-bold text-slate-900">음성 지표</h3>
        <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
          {[
            ['말 속도', fmt(summary.spm_avg, 0, ' 음절/분')],
            ['군말', summary.filler_count == null ? EMPTY : `${summary.filler_count}회 (분당 ${fmt(summary.filler_per_min)}회)`],
            ['침묵 비율', pct(summary.silence_ratio)],
            ['2초 이상 끊김', `${(audio.silences || []).length}회`],
            ['억양 폭(표준편차)', fmt(summary.pitch_std, 1, ' Hz')],
            ['억양 단조로움', pct(summary.monotone_ratio)],
          ].map(([k, v]) => (
            <div key={k} className="flex items-baseline justify-between border-b border-slate-100 pb-1">
              <dt className="text-sm text-slate-500">{k}</dt>
              <dd className="text-sm font-semibold text-slate-900">{v}</dd>
            </div>
          ))}
        </dl>
        {summary.x_filler_detail && Object.keys(summary.x_filler_detail).length > 0 && (
          <p className="mt-3 text-sm text-slate-600">
            <b>자주 쓴 군말:</b>{' '}
            {Object.entries(summary.x_filler_detail)
              .sort((a, b) => b[1] - a[1])
              .map(([w, n]) => `'${w}' ${n}회`)
              .join(', ')}
          </p>
        )}
      </section>

      {/* 전사문 */}
      {(audio.transcript || []).length > 0 && (
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="mb-3 text-lg font-bold text-slate-900">
            전사문 <span className="text-sm font-normal text-slate-500">{audio.transcript.length}문장</span>
          </h3>
          <div className="max-h-72 space-y-1.5 overflow-y-auto pr-2">
            {audio.transcript.map((seg, i) => (
              <p key={i} className="text-sm leading-relaxed text-slate-700">
                <span className="mr-2 inline-block w-14 shrink-0 text-right font-mono text-xs text-slate-400">
                  {Number(seg.start ?? 0).toFixed(1)}s
                </span>
                {seg.text}
              </p>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
