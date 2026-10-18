// 발표 중 하단 컨트롤 바. 발표 모드는 집중이 중요하므로 어두운 배경 + 높은 대비를 유지하고,
// 위치를 고정한다: 왼쪽 = 종료·시간, 가운데 = 이동·진행률.
function fmt(sec) {
  const m = Math.floor(sec / 60).toString().padStart(2, '0')
  const s = (sec % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

export default function SlideControls({ current, total, onPrev, onNext, onExit, exiting, elapsed, goalSec }) {
  const progress = ((current + 1) / total) * 100
  const overtime = goalSec && elapsed > goalSec

  return (
    <div className="flex h-[72px] shrink-0 select-none items-center gap-5 border-t border-white/10 bg-slate-950 px-6 text-white">
      <div className="flex items-center gap-3">
        <button
          onClick={onExit}
          disabled={exiting}
          className="flex h-10 items-center gap-2 rounded-xl bg-red-600 px-4 text-sm font-bold text-white transition-colors hover:bg-red-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300 disabled:opacity-40"
          title="발표 종료"
        >
          <span className="h-2.5 w-2.5 rounded-sm bg-white" />
          발표 종료
        </button>

        {elapsed != null && (
          <div
            className={`flex h-10 items-center gap-1.5 rounded-xl px-3.5 font-mono text-sm font-semibold tabular-nums ${
              overtime ? 'animate-pulse bg-red-600/90' : 'bg-white/10'
            }`}
            aria-label="경과 시간"
          >
            <span>{fmt(elapsed)}</span>
            {goalSec && <span className="text-white/50">/ {fmt(goalSec)}</span>}
          </div>
        )}
      </div>

      <div className="mx-auto flex w-full max-w-2xl items-center gap-4">
        <button
          onClick={onPrev}
          disabled={current === 0}
          className="h-10 shrink-0 rounded-xl bg-white/10 px-4 text-sm font-semibold transition-colors hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 disabled:cursor-not-allowed disabled:opacity-30"
        >
          이전
        </button>
        <div className="flex flex-1 items-center gap-3">
          <div className="h-1.5 flex-1 rounded-full bg-white/15">
            <div className="h-1.5 rounded-full bg-blue-500 transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>
          <span className="whitespace-nowrap font-mono text-sm tabular-nums text-white/70">
            {current + 1} / {total}
          </span>
        </div>
        <button
          onClick={onNext}
          disabled={current === total - 1}
          className="h-10 shrink-0 rounded-xl bg-blue-600 px-5 text-sm font-semibold transition-colors hover:bg-blue-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 disabled:cursor-not-allowed disabled:opacity-30"
        >
          다음
        </button>
      </div>
    </div>
  )
}
