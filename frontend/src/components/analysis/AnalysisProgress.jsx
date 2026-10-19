import Icon from '../common/Icons'

const STEPS = [
  { title: '영상 프레임 추출', desc: '분석할 장면을 뽑아냅니다' },
  { title: '시선 분석', desc: 'FaceMesh로 시선 방향을 확인합니다' },
  { title: '자세 분석', desc: 'Pose로 어깨와 몸의 기울기를 확인합니다' },
  { title: '제스처 분석', desc: 'Hands로 손동작 횟수를 셉니다' },
  { title: 'AI 코칭 생성', desc: '결과를 모아 개선할 점을 정리합니다' },
]

export default function AnalysisProgress({ stepHint = 0 }) {
  const pct = Math.round((Math.min(stepHint, STEPS.length) / STEPS.length) * 100)

  return (
    <main className="mx-auto w-full max-w-2xl px-5 py-14 text-left">
      <div className="rounded-3xl border border-slate-200 bg-white p-8 md:p-10">
        <div className="flex items-center gap-4">
          <span className="h-9 w-9 shrink-0 animate-spin rounded-full border-[3px] border-blue-600 border-t-transparent" />
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-950">영상을 분석하고 있어요</h1>
            <p className="mt-1 text-sm text-slate-500">보통 1~3분 걸립니다. 이 화면을 열어 두면 끝나는 즉시 결과가 나타납니다.</p>
          </div>
        </div>

        <div className="mt-7">
          <div className="mb-2 flex justify-between text-xs font-semibold text-slate-500">
            <span>진행률</span>
            <span className="tabular-nums">{pct}%</span>
          </div>
          <div className="h-2 rounded-full bg-slate-100" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
            <div className="h-2 rounded-full bg-blue-600 transition-all duration-500" style={{ width: `${Math.max(pct, 4)}%` }} />
          </div>
        </div>

        <ol className="mt-8 space-y-1">
          {STEPS.map((step, i) => {
            const done = i < stepHint
            const active = i === stepHint
            return (
              <li
                key={step.title}
                className={`flex items-center gap-4 rounded-2xl px-4 py-3 transition-colors ${active ? 'bg-blue-50' : ''}`}
              >
                <span
                  className={[
                    'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold',
                    done ? 'bg-blue-600 text-white' : active ? 'bg-blue-600 text-white ring-4 ring-blue-200' : 'bg-slate-100 text-slate-400',
                  ].join(' ')}
                >
                  {done ? <Icon name="check" className="h-4 w-4" strokeWidth={2.5} /> : i + 1}
                </span>
                <div className="min-w-0">
                  <p className={`text-sm font-bold ${done || active ? 'text-slate-900' : 'text-slate-400'}`}>{step.title}</p>
                  <p className={`text-xs ${active ? 'text-blue-700' : 'text-slate-400'}`}>{active ? '진행 중 · ' : done ? '완료 · ' : ''}{step.desc}</p>
                </div>
              </li>
            )
          })}
        </ol>
      </div>
    </main>
  )
}
