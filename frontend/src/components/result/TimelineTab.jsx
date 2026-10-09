import { useMemo } from 'react'
import {
  ComposedChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceArea, CartesianGrid, Scatter,
} from 'recharts'

// 타임라인·습관 탭. details.video_timeline과 details.habits를 읽는다.
// 데이터와 탐지 로직은 김민서 블록이고, 이 파일은 그 결과를 그리기만 한다.

const EMPTY = '측정되지 않음'

const HABIT_LABEL = {
  persistent: '오래 지속',
  repeated: '반복됨',
}

const GAZE_LABEL = {
  left: '왼쪽',
  right: '오른쪽',
  up: '위쪽',
  down: '아래쪽',
  left_up: '왼쪽 위',
  right_up: '오른쪽 위',
  left_down: '왼쪽 아래',
  right_down: '오른쪽 아래',
}

function fmtSec(s) {
  if (s == null) return '?'
  const m = Math.floor(s / 60)
  return m > 0 ? `${m}분 ${Math.round(s % 60)}초` : `${Math.round(s)}초`
}

/** 자세 기울기 라인 + 제스처 활성 점 + 습관 구간 띠 */
function PostureChart({ timeline, postureHabits }) {
  const data = useMemo(
    () =>
      (timeline || []).map((t) => ({
        sec: t.sec,
        tilt: t.posture?.shoulder_tilt_deg ?? null,
        gesture: t.gesture?.active ? 0 : null, // 활성 구간을 바닥에 점으로
      })),
    [timeline],
  )
  const segments = postureHabits?.segments ?? []

  if (!data.some((d) => d.tilt != null)) {
    return <p className="text-sm text-slate-500">자세 시간축이 없습니다 (몸이 화면에 충분히 잡히지 않았습니다).</p>
  }

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: -16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          {segments.map((s, i) => (
            <ReferenceArea key={i} x1={s.start_sec} x2={s.end_sec} fill="#f43f5e" fillOpacity={0.12} />
          ))}
          <XAxis dataKey="sec" unit="s" tick={{ fontSize: 11 }} stroke="#94a3b8" />
          <YAxis unit="°" tick={{ fontSize: 11 }} stroke="#94a3b8" />
          <Tooltip
            formatter={(v, name) => [v == null ? EMPTY : v, name === 'tilt' ? '어깨 기울기(도)' : '제스처 활성']}
            labelFormatter={(l) => `${l}초`}
          />
          <Line type="monotone" dataKey="tilt" stroke="#4f46e5" dot={false} strokeWidth={2} connectNulls />
          <Scatter dataKey="gesture" fill="#10b981" />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="mt-1 flex gap-3 text-[11px] text-slate-500">
        <span><i className="mr-1 inline-block h-2 w-3 bg-indigo-600 align-middle" />어깨 기울기</span>
        <span><i className="mr-1 inline-block h-2 w-3 bg-emerald-500 align-middle" />제스처 활성 시점</span>
        <span><i className="mr-1 inline-block h-2 w-3 bg-rose-300 align-middle" />자세 문제 구간</span>
      </div>
    </div>
  )
}

function HabitCard({ title, items, emptyText, analysisStatus }) {
  const unavailable = analysisStatus === 'unavailable'

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h4 className="font-semibold text-slate-900">{title}</h4>

      {unavailable ? (
        <p className="mt-1.5 text-sm text-slate-500">
          분석 가능한 데이터가 없습니다
        </p>
      ) : items.length === 0 ? (
        <p className="mt-1.5 text-sm text-emerald-700">{emptyText}</p>
      ) : (
        <ul className="mt-1.5 space-y-1">
          {items.map((it, i) => (
            <li key={i} className="text-sm text-rose-700">· {it}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function TimelineTab({ details }) {
  const timeline = details?.video_timeline ?? null
  const habits = details?.habits ?? {}

  const gaze = habits.gaze ?? null
  const posture = habits.posture ?? null
  const gesture = habits.gesture ?? null
  const filler = habits.filler ?? null
  const monotone = habits.monotone ?? null

  // 습관 탐지 결과를 사람이 읽는 문장으로
  const gazeItems = []

  for (const h of gaze?.habits?.persistent ?? []) {
    gazeItems.push(`${fmtSec(h.start_sec)}부터 ${fmtSec(h.duration_sec)} 동안 ${GAZE_LABEL[h.direction] ?? h.direction} 방향을 지속적으로 바라봄`)
  }

  for (const h of gaze?.habits?.repeated ?? []) {
    gazeItems.push(`${GAZE_LABEL[h.direction] ?? h.direction} 방향으로 시선을 ${h.count ?? '여러'}회 반복적으로 돌림`)
  }
  
  const postureItems = []
  for (const h of posture?.habits?.persistent ?? []) {
    postureItems.push(`${fmtSec(h.start_sec)}부터 ${fmtSec(h.duration_sec)} 동안 ${h.direction === 'left' ? '왼쪽' : '오른쪽'}으로 기울어짐`)
  }
  for (const h of posture?.habits?.repeated ?? []) {
    postureItems.push(`${h.direction === 'left' ? '왼쪽' : '오른쪽'} 기울임이 ${h.count ?? '여러'}회 반복됨`)
  }

  const gestureItems = (gesture?.persistent ?? []).map(
    (g) => `${fmtSec(g.start_sec)}부터 ${fmtSec(g.duration_sec)} 동안 손동작 없음`,
  )

  const fillerItems = (filler?.repeated ?? []).map(
    (f) => `'${f.word ?? f.filler ?? '?'}'를 ${f.count ?? '?'}회 반복`,
  )

  const monotoneItems = (monotone?.persistent ?? []).map(
    (m) => `${fmtSec(m.start_sec)}부터 ${fmtSec(m.duration_sec)} 동안 억양이 거의 변하지 않음`,
  )

  const nothingMeasured = !timeline?.length && !gaze && !posture && !gesture && !filler && !monotone

  if (nothingMeasured) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-8 text-center">
        <p className="font-medium text-slate-700">타임라인을 분석하지 못했습니다.</p>
        <p className="mt-1 text-sm text-slate-500">몸과 음성이 충분히 잡히지 않은 영상입니다.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-lg font-bold text-slate-900">자세·제스처 흐름</h3>
        <p className="mb-3 text-xs text-slate-500">
          어깨 기울기의 변화와 손동작이 있었던 시점입니다. 붉은 띠는 자세 문제로 탐지된 구간입니다.
        </p>
        <PostureChart timeline={timeline} postureHabits={posture} />
      </section>

      <section>
        <h3 className="mb-2 text-lg font-bold text-slate-900">탐지된 습관</h3>
        <p className="mb-3 text-xs text-slate-500">
          한 번의 실수가 아니라 지속되거나 반복되는 패턴만 습관으로 봅니다. 임계값은 현재 실험값이며
          영상 검증 후 조정됩니다.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <HabitCard title="시선" items={gazeItems} emptyText="지속되거나 반복되는 시선 이탈이 없습니다" analysisStatus={gaze?.analysis_status ?? (gaze?.gaze_points?.length ? 'available' : 'unavailable')} />
          <HabitCard title="자세" items={postureItems} emptyText="기울어짐 습관이 없습니다" analysisStatus={posture?.analysis_status ?? (posture ? 'available' : 'unavailable')} />
          <HabitCard title="제스처" items={gestureItems} emptyText="손동작이 오래 끊긴 구간이 없습니다" analysisStatus={gesture?.analysis_status ?? (gesture ? 'available' : 'unavailable')} />
          <HabitCard title="군말" items={fillerItems} emptyText="반복되는 군말이 없습니다" analysisStatus={filler ? 'available' : 'unavailable'} />
          <HabitCard title="억양" items={monotoneItems} emptyText="단조롭게 이어진 구간이 없습니다" analysisStatus={monotone?.analysis_status ?? (monotone ? 'available' : 'unavailable')} />
        </div>
      </section>
    </div>
  )
}
