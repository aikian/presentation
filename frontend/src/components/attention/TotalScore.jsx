// 총 점수
export function TotalScore({ predictResult }) {
    if (!predictResult) {
        return null;
    }

    const score = predictResult.attention_score;
    const baseScore = predictResult.base_score;

    return (
        <div className="mb-8 rounded-xl border border-gray-200 bg-white p-6">
            <p className="text-sm font-medium text-gray-500">
                발표 집중도 추정
            </p>

            <div className="mt-2 flex items-end gap-2">
                <span className="text-4xl font-bold text-gray-600">
                    {score == null ? "-" : Number(score).toFixed(1)}
                </span>

                <span className="mb-1 text-lg text-gray-500">
                    / 100
                </span>
            </div>
            
            {baseScore != null && (
                <p className="mt-2 text-xs text-gray-400">
                    기준 점수 {baseScore}점은 특별한 감점/가점 요인이 없는 평이한 상태를 의미하며,
                    점수가 기준보다 높거나 낮을수록 발표 중 특징적인 구간이 많았다는 뜻입니다.
                </p>
            )}
        </div>
    );
}