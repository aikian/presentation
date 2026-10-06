// 발표 영상인지에 대한 판정을 결과 맨 위에 보여준다. details.x_validity를 읽는다.
//
// 아무 영상이나 올려도 점수가 나오면 사용자는 그 점수를 자기 발표 점수로 읽는다.
// 못 쟀다는 사실을 조용히 null로만 두지 않고 화면에서 먼저 말한다.

export default function ValidityBanner({ validity }) {
  if (!validity || validity.level === 'ok') return null

  const invalid = validity.level === 'invalid'

  return (
    <div
      className={`rounded-lg border px-4 py-3 ${
        invalid
          ? 'border-rose-300 bg-rose-50 text-rose-900'
          : 'border-amber-300 bg-amber-50 text-amber-900'
      }`}
    >
      <p className="font-semibold">
        {invalid ? '이 영상은 발표로 분석할 수 없습니다' : '일부 항목만 분석했습니다'}
      </p>

      {validity.problems?.length > 0 && (
        <ul className="mt-1.5 space-y-0.5">
          {validity.problems.map((p) => (
            <li key={p.code} className="text-sm">
              · {p.message}
            </li>
          ))}
        </ul>
      )}

      <p className="mt-2 text-sm">
        {invalid
          ? '발표자가 화면에 보이고 목소리가 녹음된 영상을 올려주세요. 점수는 매기지 않았습니다.'
          : '측정하지 못한 항목은 점수 계산에서 제외했습니다. 0점으로 처리하지 않습니다.'}
      </p>
    </div>
  )
}
