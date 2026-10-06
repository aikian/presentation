// 아직 화면이 없는 탭. 담당자가 이 폴더에 파일을 만들고 ResultTabs에서 바꿔 끼우면 된다.
//
// 그냥 "준비 중"이라고만 두지 않고, 백엔드에서 이미 나오고 있는 데이터를 적어둔다.
// 담당자가 무엇을 그려야 하는지 바로 알 수 있고, 통합이 어디까지 됐는지도 드러난다.

export default function PlaceholderTab({ title, owner, available = [] }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8">
      <h3 className="text-lg font-bold text-slate-900">{title}</h3>
      <p className="mt-1 text-sm text-slate-500">
        화면 준비 중입니다{owner ? ` (담당: ${owner})` : ''}.
      </p>

      {available.length > 0 ? (
        <div className="mt-5">
          <p className="text-sm font-semibold text-slate-700">분석 결과에 이미 들어와 있는 데이터</p>
          <ul className="mt-2 space-y-1">
            {available.map((item) => (
              <li key={item} className="text-sm text-slate-600">
                <span className="mr-1.5 text-emerald-600">✓</span>
                {item}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-400">
            frontend/src/components/result/ 에 탭 파일을 만들고 ResultTabs.jsx에 등록하면 됩니다.
          </p>
        </div>
      ) : (
        <p className="mt-5 text-sm text-slate-500">
          이 분석 결과에는 해당 데이터가 들어오지 않았습니다.
        </p>
      )}
    </div>
  )
}
