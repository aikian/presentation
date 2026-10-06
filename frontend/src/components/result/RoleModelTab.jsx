// 롤모델 비교 탭. details.x_rolemodel을 읽는다.
//
// 지도교수 피드백(9/22): 기준이 정해져 있다면 발표자의 모습을 그 기준과 비교해
// 잘했다/못했다를 판단해주면 되고, 그 판단 논리가 완벽하지 않더라도
// 일정 수준 이상 납득이 되어야 한다.
//
// 그래서 "범위 밖"이라고만 쓰지 않고, 어느 쪽으로 얼마나 벗어났는지와
// 그게 왜 문제인지(또는 왜 문제가 아닌지)를 같이 적는다.

const EMPTY = '측정되지 않음'

// 지표마다 "왜 이 범위가 좋은가"를 적어둔다. 숫자만 보여주면 납득이 안 된다.
const WHY = {
  spm_avg:
    '너무 빠르면 듣는 사람이 따라오지 못하고, 너무 느리면 집중이 끊깁니다. 명연사들은 좁은 띠 안에 모여 있습니다.',
  filler_per_min:
    '"어", "그" 같은 군말이 잦으면 내용 전달이 끊기고 준비가 덜 된 인상을 줍니다. 다만 명연사도 분당 1.5~2.9회는 씁니다.',
  silence_ratio:
    '침묵이 너무 많으면 흐름이 끊기고, 너무 적으면 듣는 사람이 숨 돌릴 틈이 없습니다.',
  monotone_ratio:
    '이웃한 초끼리 피치가 거의 변하지 않는 구간의 비율입니다. 높을수록 단조롭게 들립니다.',
  pitch_std:
    '억양이 오르내리는 폭입니다. 타고난 음역에 좌우되는 면이 있어 참고용으로만 봅니다.',
}

function Verdict({ metric }) {
  const { position, concern, value, reference_min, reference_max } = metric

  if (position === 'within') {
    return <span className="font-semibold text-emerald-700">명연사 범위 안</span>
  }

  const over = position === 'above'
  const edge = over ? reference_max : reference_min
  const gap = Math.abs(value - edge)
  const width = reference_max - reference_min
  const ratio = width > 0 ? gap / width : 0

  // 얼마나 벗어났는지를 말로 바꾼다. 범위 폭을 기준으로 삼는다.
  const degree = ratio < 0.25 ? '조금' : ratio < 1 ? '뚜렷하게' : '크게'
  const direction = over ? '높습니다' : '낮습니다'

  if (!concern) {
    return (
      <span className="font-semibold text-emerald-700">
        명연사보다 {degree} {direction} — 좋은 쪽입니다
      </span>
    )
  }

  return (
    <span className="font-semibold text-rose-700">
      명연사보다 {degree} {direction} — 개선이 필요합니다
    </span>
  )
}

function Row({ metric }) {
  const { label, key, value, reference_min, reference_max, concern } = metric

  return (
    <div className={`rounded-lg border p-4 ${concern ? 'border-rose-200 bg-rose-50/40' : 'border-slate-200 bg-white'}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-semibold text-slate-900">{label}</span>
        <Verdict metric={metric} />
      </div>
      <div className="mt-1 text-sm text-slate-600">
        내 값 <b className="text-slate-900">{value}</b>
        <span className="mx-1.5 text-slate-300">|</span>
        명연사 {reference_min} ~ {reference_max}
      </div>
      {WHY[key] && <p className="mt-2 text-xs leading-relaxed text-slate-500">{WHY[key]}</p>}
    </div>
  )
}

/** 연사 한 명을 골랐을 때. 범위가 아니라 그 사람의 값이 목표다. */
function OneRow({ metric }) {
  const { label, key, value, target, diff, diff_ratio, verdict, concern } = metric
  const sign = diff > 0 ? '+' : ''

  return (
    <div className={`rounded-lg border p-4 ${concern ? 'border-rose-200 bg-rose-50/40' : 'border-slate-200 bg-white'}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-semibold text-slate-900">{label}</span>
        <span className={concern ? 'font-semibold text-rose-700' : 'font-semibold text-emerald-700'}>
          {verdict}
        </span>
      </div>
      <div className="mt-1 text-sm text-slate-600">
        내 값 <b className="text-slate-900">{value}</b>
        <span className="mx-1.5 text-slate-300">|</span>
        연사 <b className="text-slate-900">{target}</b>
        <span className="mx-1.5 text-slate-300">|</span>
        차이 {sign}{diff}
        {diff_ratio != null && ` (${(diff_ratio * 100).toFixed(0)}%)`}
      </div>
      {WHY[key] && <p className="mt-2 text-xs leading-relaxed text-slate-500">{WHY[key]}</p>}
    </div>
  )
}

function OneComparison({ rm }) {
  const s = rm.speaker ?? {}
  const concerns = rm.metrics.filter((m) => m.concern)

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-lg font-bold text-slate-900">{s.name} 연사와 비교</h3>
        <p className="mt-1 text-sm text-slate-600">
          {[s.affiliation, s.source, s.title].filter(Boolean).join(' · ')}
        </p>
        <p className="mt-2 text-xs leading-relaxed text-slate-500">
          따라 하고 싶은 연사로 고르셨기 때문에, 범위 안에 있는지가 아니라 이 연사의 값에
          얼마나 가까운지를 봅니다. 차이가 15% 안이면 비슷하다고 봤습니다.
        </p>
        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
          {concerns.length === 0
            ? '네 지표 모두 이 연사와 비슷하거나 더 좋습니다.'
            : `${concerns.length}개 지표가 이 연사와 뚜렷하게 다릅니다.`}
        </div>
      </section>

      <section>
        <h4 className="mb-2 font-semibold text-slate-900">지표별 비교</h4>
        <div className="space-y-3">
          {rm.metrics.map((m) => (
            <OneRow key={m.key} metric={m} />
          ))}
        </div>
      </section>

      <p className="rounded-lg bg-amber-50 p-3 text-xs leading-relaxed text-amber-800">
        <b>참고:</b> 한 사람의 값과 맞추는 것이 항상 좋은 것은 아닙니다. 목소리와 말투는 사람마다
        다르고, 이 연사의 수치는 그 강연 한 편을 측정한 값입니다. 방향을 참고하는 정도로 보시면
        좋겠습니다.
      </p>
    </div>
  )
}

export default function RoleModelTab({ details }) {
  const rm = details?.x_rolemodel ?? null

  if (rm?.mode === 'one') {
    return <OneComparison rm={rm} />
  }

  if (!rm) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-8 text-center">
        <p className="font-medium text-slate-700">롤모델과 비교할 수 없었습니다.</p>
        <p className="mt-1 text-sm text-slate-500">
          음성을 분석하지 못했거나 기준으로 쓸 연사 데이터를 읽지 못한 경우입니다.
        </p>
      </div>
    )
  }

  const concerns = rm.metrics.filter((m) => m.concern)
  const goods = rm.metrics.filter((m) => !m.concern)

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-lg font-bold text-slate-900">명연사와 비교</h3>
        <p className="mt-1 text-sm text-slate-600">
          기준: {rm.reference_names.join(', ')} 등 발표 {rm.reference_count}편의 실측 범위
        </p>
        <p className="mt-2 text-xs leading-relaxed text-slate-500">
          세바시 강연에서 연사가 화면에 잡히는 구간만 골라 같은 방식으로 음성을 분석한 값입니다.
          평균 하나로 줄이지 않고 최소~최대 범위를 쓴 이유는, 연사마다 스타일이 달라서 평균이
          아무에게도 해당하지 않는 값이 되기 쉽기 때문입니다.
        </p>

        <div className="mt-4 flex gap-3">
          <div className="flex-1 rounded-lg bg-rose-50 p-3 text-center">
            <div className="text-2xl font-bold text-rose-700">{concerns.length}</div>
            <div className="text-xs text-rose-600">개선 필요</div>
          </div>
          <div className="flex-1 rounded-lg bg-emerald-50 p-3 text-center">
            <div className="text-2xl font-bold text-emerald-700">{goods.length}</div>
            <div className="text-xs text-emerald-600">문제 없음</div>
          </div>
        </div>
      </section>

      {concerns.length > 0 && (
        <section>
          <h4 className="mb-2 font-semibold text-slate-900">개선이 필요한 항목</h4>
          <div className="space-y-3">
            {concerns.map((m) => (
              <Row key={m.key} metric={m} />
            ))}
          </div>
        </section>
      )}

      {goods.length > 0 && (
        <section>
          <h4 className="mb-2 font-semibold text-slate-900">문제 없는 항목</h4>
          <div className="space-y-3">
            {goods.map((m) => (
              <Row key={m.key} metric={m} />
            ))}
          </div>
        </section>
      )}

      <p className="rounded-lg bg-amber-50 p-3 text-xs leading-relaxed text-amber-800">
        <b>한계:</b> 기준으로 쓴 연사가 6명 7편뿐이고, 같은 사람의 강연이 둘 있는 경우가
        한 사람(김경일)뿐입니다. 그래서 지표가 사람의 실력을 재는지 그날의 상태를 재는지에 대한
        판단은 아직 잠정입니다. 표본을 늘리면 기준 범위가 달라질 수 있습니다.
      </p>
    </div>
  )
}
