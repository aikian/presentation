// 히트맵·표정 탭. details.summary(표정 지표)와 details.x_gaze_heatmap(9분할)을 읽는다.
//
// MVP 원칙대로 시작한다: 히트맵은 9분할 정적, 표정은 2지표(미소·긴장).
// 측정하지 못한 값은 null이고, 화면은 그 사실을 그대로 말한다.

const EMPTY = '측정되지 않음'

const ROW_LABEL = ['위', '중앙', '아래']
const COL_LABEL = ['왼쪽', '중앙', '오른쪽']

function pct(v, digits = 1) {
  if (v == null) return EMPTY
  return `${(Number(v) * 100).toFixed(digits)}%`
}

/** 9분할 시선 히트맵. 값(0~1)이 클수록 진하게 칠한다. */
function GazeGrid({ heatmap }) {
  if (!heatmap?.grid) return null
  const max = Math.max(...heatmap.grid.flat(), 0.001)

  return (
    <div>
      <div className="grid grid-cols-3 gap-1.5" style={{ maxWidth: 360 }}>
        {heatmap.grid.flatMap((row, r) =>
          row.map((v, c) => {
            const intensity = v / max
            const isCenter = r === 1 && c === 1
            return (
              <div
                key={`${r}-${c}`}
                className="relative flex aspect-square flex-col items-center justify-center rounded-lg border border-slate-200"
                style={{ backgroundColor: `rgba(79, 70, 229, ${0.06 + intensity * 0.7})` }}
                title={`${ROW_LABEL[r]}·${COL_LABEL[c]}: ${pct(v)}`}
              >
                <span className={`text-sm font-bold ${intensity > 0.55 ? 'text-white' : 'text-slate-800'}`}>
                  {pct(v, 0)}
                </span>
                {isCenter && (
                  <span className={`text-[10px] ${intensity > 0.55 ? 'text-indigo-100' : 'text-slate-500'}`}>
                    정면(카메라)
                  </span>
                )}
              </div>
            )
          }),
        )}
      </div>
      <p className="mt-2 text-xs text-slate-500">
        발표 중 시선이 머문 방향의 비율입니다 (프레임 {heatmap.n_frames}장 기준, 화면에서 본 방향).
      </p>
    </div>
  )
}

function ExpressionCard({ label, value, hint, good }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-baseline justify-between">
        <span className="text-sm text-slate-500">{label}</span>
        <span className={`text-2xl font-bold ${good == null ? 'text-slate-900' : good ? 'text-emerald-600' : 'text-rose-600'}`}>
          {pct(value)}
        </span>
      </div>
      <p className="mt-1.5 text-xs leading-relaxed text-slate-500">{hint}</p>
    </div>
  )
}

export default function VisualTab({ details }) {
  const summary = details?.summary ?? {}
  const heatmap = details?.x_gaze_heatmap ?? null
  const smile = summary.smile_ratio
  const tension = summary.tension_ratio
  const changeStd = summary.expression_change_std

  const nothing = smile == null && tension == null && !heatmap

  if (nothing) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-8 text-center">
        <p className="font-medium text-slate-700">표정과 시선을 분석하지 못했습니다.</p>
        <p className="mt-1 text-sm text-slate-500">
          얼굴이 화면에 충분히 잡히지 않은 경우입니다. 카메라에 얼굴이 보이도록 찍은 영상으로
          다시 분석해보세요.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-lg font-bold text-slate-900">시선 히트맵</h3>
        <p className="mb-4 text-xs text-slate-500">
          청중(카메라)을 보는 시간이 길수록 가운데 칸이 진해집니다. 특정 방향 칸이 진하면
          대본이나 슬라이드만 보고 있었다는 뜻일 수 있습니다.
        </p>
        {heatmap ? <GazeGrid heatmap={heatmap} /> : <p className="text-sm text-slate-500">{EMPTY}</p>}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="mb-3 text-lg font-bold text-slate-900">표정</h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <ExpressionCard
            label="미소 비율"
            value={smile}
            good={smile == null ? null : smile >= 0.1}
            hint="입꼬리가 올라간 프레임의 비율입니다. 발표 내내 0%면 굳은 인상을 줄 수 있습니다."
          />
          <ExpressionCard
            label="긴장(찌푸림) 비율"
            value={tension}
            good={tension == null ? null : tension < 0.3}
            hint="눈썹이 내려간 프레임의 비율입니다. 높으면 긴장했거나 찌푸린 표정이 잦았다는 뜻입니다."
          />
          <ExpressionCard
            label="표정 변화량"
            value={changeStd == null ? null : Math.min(changeStd * 10, 1)}
            good={null}
            hint="표정이 얼마나 움직였는지입니다. 너무 낮으면 무표정, 적당히 있으면 생동감 있는 발표입니다."
          />
        </div>
        <p className="mt-3 rounded-lg bg-amber-50 p-3 text-xs leading-relaxed text-amber-800">
          <b>참고:</b> 입꼬리와 눈썹 위치로 추정한 값이라 얼굴형과 카메라 각도에 따라 오차가
          있습니다. 비율의 절대값보다는 다음 발표와 비교해 변화를 보는 용도로 적합합니다.
        </p>
      </section>
    </div>
  )
}
