import { EVENT_META } from "./EventCategory";

function buildMainFactors(timeline, topN = 5) {
    const counts = {};

    for (const item of timeline) {
        for (const code of item.events ?? []) {
            counts[code] = (counts[code] ?? 0) + 1;
        }
    }

    return Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, topN)
        .map(([code, count]) => ({
            code,
            label: EVENT_META[code]?.label ?? code,
            tone: EVENT_META[code]?.tone ?? "neutral",
            count
        }));
}

function buildOccurrences(timeline, code) {
    const tone = EVENT_META[code]?.tone;
    return timeline
        .filter((item) => (item.events ?? []). includes(code))
        .map((item) => ({
            sec: item.sec,
            score: item.score,
            detail: tone === "positive" ? item.boosts : item.penalties
        }));
}

export function MainFactors({ predictResult, selectedFactor, onSelectFactor, selectedSecond, onSelectSecond }) {
    const secondTimeline = predictResult?.timeline_second ?? [];
    if (secondTimeline.length === 0) {
        return null;
    }

    const factors = buildMainFactors(secondTimeline);
    if (factors.length === 0) {
        return null;
    }
    
    const occurrences = selectedFactor ? buildOccurrences(secondTimeline, selectedFactor) : [];

    return (
        <div className="mb-10 rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-xl font-bold text-gray-900">
                집중도 변화 요인
            </h2>

            <div className="space-y-2">
                {factors.map((factor) => {
                    const isSelected = selectedFactor === factor.code;
                    return (
                        <button
                            type="button"
                            key={factor.code} 
                            onClick={() => {
                                const next = isSelected ? null : factor.code;
                                onSelectFactor(next);
                                onSelectSecond(null);
                            }}
                            className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-sm transition-colors ${
                                isSelected
                                    ? "border-amber-300 bg-amber-50"
                                    : "border-transparent hover:bg-gray-50"
                            }`}
                        >
                            <span className="flex items-center gap-2">
                                <span className={factor.tone === "positive" ? "text-green-500" : "text-red-500"}>
                                    {factor.tone === "positive" ? "▲" : "▼"}
                                </span>
                                {factor.label}
                            </span>
                            <span className="font-medium text-gray-700">
                                {factor.count}회
                            </span>
                        </button>
                    );
                })}
            </div>

            {selectedFactor && (
                <div className="mt-4 border-t border-gray-100 pt-4">
                    <p className="mb-2 text-xs font-medium text-gray-500">
                        {EVENT_META[selectedFactor]?.label ?? selectedFactor} 발생 구간
                        (초를 클릭하면 그래프에 해당 지점만 표시됩니다)
                    </p>
                    <div className="space-y-1">
                        {occurrences.map((occ) => {
                            const isSelected = selectedSecond === occ.sec;
                            return (
                                <button
                                    type="button"
                                    key={occ.sec} 
                                    onClick={() => onSelectSecond(isSelected ? null : occ.sec)}
                                    className={`flex w-full items-center justify-between rounded-md px-2 py-1 text-xs transition-colors ${
                                        isSelected
                                            ? "bg-amber-50 text-amber-700"
                                            : "text-gray-500 hover:bg-gray-50"
                                    }`}
                                >
                                  <span>{occ.sec}초 (점수 {occ.score})</span>
                                    <span className="text-gray-400">
                                        {occ.detail?.[0] ?? ""}
                                    </span>  
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    )
}