function fmt(sec) {
  const m = Math.floor(sec / 60).toString().padStart(2, '0')
  const s = (sec % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

export default function SlideControls({ current, total, onPrev, onNext, onExit, exiting, elapsed, goalSec }) {
  const progress = ((current + 1) / total) * 100
  const overtime = goalSec && elapsed > goalSec

  return (
    <div className="bg-gray-900 text-white flex items-center gap-4 px-6 py-3 select-none">
      <button
        onClick={onExit}
        disabled={exiting}
        className="text-gray-400 hover:text-white disabled:opacity-40 transition-colors text-sm mr-2"
        title="발표 종료"
      >
        ✕
      </button>

      <button
        onClick={onPrev}
        disabled={current === 0}
        className="px-4 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        ← 이전
      </button>

      <div className="flex-1 flex items-center gap-3">
        <div className="flex-1 bg-gray-700 rounded-full h-1.5">
          <div
            className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="text-sm text-gray-300 whitespace-nowrap">{current + 1} / {total}</span>
      </div>

      {/* 타이머 */}
      {elapsed != null && (
        <div className={`flex items-center gap-1.5 text-sm font-mono px-3 py-1 rounded-lg ${overtime ? 'bg-red-600 animate-pulse' : 'bg-gray-700'}`}>
          <span>{fmt(elapsed)}</span>
          {goalSec && <span className="opacity-60">/ {fmt(goalSec)}</span>}
        </div>
      )}

      <button
        onClick={onNext}
        disabled={current === total - 1}
        className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        다음 →
      </button>
    </div>
  )
}
