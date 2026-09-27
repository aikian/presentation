import { Line } from "react-chartjs-2";
// 실행을 하려면 npm install react-chartjs-2 chart.js 으로 chat.js 설치 필요

import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
} from "chart.js";

import { NEGATIVE_EVENTS, POSITIVE_EVENTS, EVENT_META } from "./EventCategory";

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

// 초단위 이벤트(문자열 배열)에서 감점/가점 이벤트 존재 여부 판정
function hasNegativeEventSecond(item) {
    return (item.events ?? []).some((code) => NEGATIVE_EVENTS.has(code));
}
function hasPositiveEventSecond(item) {
    return (item.events ?? []).some((code) => POSITIVE_EVENTS.has(code));
}    

// 분단위 이벤트({코드: 횟수} 객체)에서 감점/가점 이벤트 존재 여부 판정
function hasNegativeEventMinute(item) {
    const events = item.events ?? {};
    return Object.keys(events).some((code) => NEGATIVE_EVENTS.has(code) && events[code] > 0);
}
function hasPositiveEventMinute(item) {
    const events = item.events ?? {};
    return Object.keys(events).some((code) => POSITIVE_EVENTS.has(code) && events[code] > 0);
}

export function Graph({ predictResult, selectedFactor, selectedSecond, view, onViewChange }) {
    if (!predictResult) {
        return (
            <div className="mb-10">
                <h2 className="mb-4 text-xl font-bold text-gray-900">
                    청중 집중도 예측 결과가 없습니다.
                </h2>

                <div className="flex h-[300px] w-full items-center justify-center rounded-xl border border-gray-200 bg-gray-50">
                    <p className="text-sm text-gray-400">
                        예측된 청중 집중도 결과가 없습니다.
                    </p>
                </div>
            </div> 
        ) 
    }

    const secondTimeline = predictResult.timeline_second ?? [];
    const minuteTimeline = predictResult.timeline_minute ?? [];

    const hasSecondData = secondTimeline.length > 0;
    const hasMinuteData = minuteTimeline.length > 0;

    const isSecondTimeline = view === "second" ? hasSecondData : !hasMinuteData && hasSecondData;
    const timeline = isSecondTimeline ? secondTimeline : minuteTimeline;

    // timeline 데이터가 없는 경우
    if (timeline.length === 0) {
        return <div className="mb-10">
                  <h2 className="mb-4 text-xl font-bold text-gray-900">
                    청중 집중도 예측 결과가 없습니다.
                  </h2>

                  <div className="flex h-[300px] w-full items-center justify-center rounded-xl border border-gray-200 bg-gray-50">
                    <p className="text-sm text-gray-400">
                      예측된 청중 집중도 결과가 없습니다.
                    </p>
                  </div>
                </div> 
    }

    const labels = isSecondTimeline ? timeline.map((item) => `${item.sec}초`) : timeline.map((item) => `${item.minute}분`);

    const hasNegativeEvent = isSecondTimeline ? hasNegativeEventSecond : hasNegativeEventMinute;
    const hasPositiveEvent = isSecondTimeline ? hasPositiveEventSecond : hasPositiveEventMinute;

    const isSelectedPoint = (item) => {
        if (selectedSecond == null) return false;
        return isSecondTimeline
            ? item.sec === selectedSecond
            : item.minute === Math.floor(selectedSecond / 60);
    };

    const isFiltering = selectedSecond != null

    const datasets = [
        {
            label: '추정 집중도 점수',
            data: timeline.map((item) => item.score),

            borderColor: "#2563eb",
            backgroundColor: "rgba(37, 99, 235, 0.1)",

            borderWidth: 2,

            pointRadius: isSecondTimeline ? 1 : 2,
            pointHoverRadius: 5,

            tension: 0.3,

            fill: true,

            order: 3
        },
        {
            label: '감점 이벤트',
            data: timeline.map((item) => (!isFiltering && hasNegativeEvent(item) ? item.score : null)),

            borderColor: "transparent",
            backgroundColor: "rgba(239, 68, 68, 0.7)",
            pointBackgroundColor: "rgba(239, 68, 68, 0.7)",

            pointStyle: "triangle",
            rotation: 180,

            pointRadius: 8,
            pointHoverRadius: 10,

            showLine: false,
            spanGaps: false,
                
            order: 2
        },
        {
            label: '가점 이벤트',
            data: timeline.map((item) => (!isFiltering && hasPositiveEvent(item) ? item.score : null)),

            borderColor: "transparent",
            backgroundColor: "rgba(34, 197, 94, 0.7)",
            pointBackgroundColor: "rgba(34, 197, 94, 0.7)",

            pointStyle: "triangle",

            pointRadius: 8,
            pointHoverRadius: 10,

            showLine: false,
            spanGaps: false,
                
            order: 1
        }
    ];

    if (selectedSecond != null) {
        const tone = EVENT_META[selectedFactor]?.tone ?? "negative";
        const isNegativeTone = tone !== "positive"

        const selectedMinute = Math.floor(selectedSecond / 60);
        const selectionLabel = isSecondTimeline ? `선택: ${selectedSecond}초` : `선택: ${selectedMinute}분`;

        datasets.push({
            label: selectionLabel,
            data: timeline.map((item) => (isSelectedPoint(item) ? item.score : null)),

            borderColor: "#ffffff",
            backgroundColor: "#f59e0b",
            pointBackgroundColor: "#f59e0b",
            pointBorderColor: "#ffffff",
            pointBorderWidth: 2,

            pointStyle: "triangle",
            rotation: isNegativeTone ? 180 : 0,

            pointRadius: 10,
            pointHoverRadius: 12,

            showLine: false,
            spanGaps: false,

            order: 0,
        });
    }

    const data = { labels, datasets };

    const options = {
        responsive: true,
        maintainAspectRatio: false,

        scales: {
            y: {
                min: 0,
                max: 100,

                title: {
                    display: true,
                    text: "추정 집중도",
                },
            },

            x: {
                title: {
                    display: true,
                    text: isSecondTimeline ? "발표 시간(초)" : "발표 시간(분)",
                },
            },
        },

        plugins: {
            legend: {
                display: true,
            },

            tooltip: {
                callbacks: {
                    title: function (tooltipItems) {
                        const index = tooltipItems[0].dataIndex;
                        const item = timeline[index];

                        return isSecondTimeline
                            ? `${item.sec}초`
                            : `${item.minute}분`;
                    },

                    label: function (context) {
                        if (context.datasetIndex !== 0) {
                            return null;
                        }

                        const index = context.dataIndex;
                        const item = timeline[index];

                        return `집중도: ${item.score}점`;
                    },

                    afterBody: function (tooltipItems) {
                        if (!tooltipItems.length) {
                            return [];
                        }

                        const index = tooltipItems[0].dataIndex;
                        const item = timeline[index];

                        const messages = [];

                        if (item.penalties?.length > 0) {
                            messages.push(
                                ...item.penalties.map(
                                    (penalty) => `▼ ${penalty}`
                                )
                            );
                        }

                        if (item.boosts?.length > 0) {
                            messages.push(
                                ...item.boosts.map(
                                    (boost) => `▲ ${boost}`
                                )
                            );
                        }

                        return messages;
                    },
                },
            },
        },
    };

    return (
        <div className="mb-10">
            <div className="mb-4 flex items-center justify-between">
                <h2 className="mb-4 text-xl font-bold text-gray-900">
                    청중의 집중도 흐름
                </h2>

                {hasSecondData && hasMinuteData && (
                    <div className="flex rounded-lg border border-gray-200 bg-gray-50 p-1 text-sm">
                        <button 
                            type="button"
                            onClick={() => onViewChange("second")}
                            className={`rounded-md px-3 py-1 transition-colors ${
                                view === "second"
                                    ? "bg-white text-indigo-600 shadow-sm"
                                    : "text-gray-500 hover:text-gray-700"
                            }`}
                        >
                            초 단위
                        </button>
                        <button 
                            type="button"
                            onClick={() => onViewChange("minute")}
                            className={`rounded-md px-3 py-1 transition-colors ${
                                view === "minute"
                                    ? "bg-white text-indigo-600 shadow-sm"
                                    : "text-gray-500 hover:text-gray-700"
                            }`}
                        >
                            분 단위
                        </button>
                    </div>
                )}
            </div>
            
            <div className="rounded-xl border border-gray-200 bg-white p-6">
                <div className="h-[350px] w-full">
                    <Line data={data} options={options}/>
                </div>

                <div className="mt-4 flex gap-6 text-sm text-gray-500">
                    <span className="flex items-center gap-2">
                        <span className="h-3 w-3 rounded-full bg-blue-500"/>
                        집중도
                    </span>

                    {!isFiltering && (
                        <>
                            <div>
                                <span className="text-red-500">
                                ▼
                                </span>{" "}
                                감점 요인
                            </div>

                            <div>
                                <span className="text-green-500">
                                    ▲
                                </span>{" "}
                                가점 요인
                            </div>
                        </>
                    )}
                    

                    {selectedSecond != null && (
                        <div>
                            <span className="text-amber-500">●</span>{" "}
                            선택한 지점
                        </div>
                    )}
                </div>
            </div>
        </div>
    );    
}