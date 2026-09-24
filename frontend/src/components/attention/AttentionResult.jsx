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

// 총 점수
function TotalScore({ predictResult }) {
    if (!predictResult) {
        return null;
    }

    const score = predictResult.attention_score;

    return (
        <div className="mb-8 rounded-xl border border-gray-200 bg-white p-6">
            <p className="text-sm font-medium text-gray-500">
                최종 집중도 점수
            </p>

            <div className="mt-2 flex items-end gap-2">
                <span className="text-4xl font-bold text-gray-600">
                    {score == null ? "-" : Number(score).toFixed(1)}
                </span>

                <span className="mb-1 text-lg text-gray-500">
                    / 100
                </span>
            </div>
        </div>
    );
}

// 집중도 그래프
function Graph({ predictResult }) {
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

    const isSecondTimeline = secondTimeline.length > 0;
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

    const data = {
        labels: labels,
        datasets: [
            {
                label: '집중도 점수',
                data: timeline.map((item) => item.score),

                borderColor: "#2563eb",
                backgroundColor: "rgba(37, 99, 235, 0.1)",

                borderWidth: 2,

                pointRadius: isSecondTimeline ? 1 : 2,
                pointHoverRadius: 5,

                tension: 0.3,

                fill: true,
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,

        scales: {
            y: {
                min: 0,
                max: 100,

                title: {
                    display: true,
                    text: "집중도",
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
                        const index = context.dataIndex;
                        const item = timeline[index];

                        return `집중도: ${item.score}점`;
                    },

                    afterLabel: function (context) {
                        const index = context.dataIndex;
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
            <h2 className="mb-4 text-xl font-bold text-gray-900">
                청중의 집중도 흐름
            </h2>

            <div className="rounded-xl border border-gray-200 bg-white p-6">
                <div className="h-[350px] w-full">
                    <Line data={data} options={options}/>
                </div>

                <div className="mt-4 flex gap-6 text-sm text-gray-500">
                    <span className="flex items-center gap-2">
                        <span className="h-3 w-3 rounded-full bg-blue-500"/>
                        집중도
                    </span>

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
                </div>
            </div>
        </div>
    );    
}

export default function AttentionResult({predictResult}){
    
    if(!predictResult) {
        return (
            <div className="text-sm text-gray-400">
                집중도 분석 결과가 없습니다.
            </div>
        )
    }

    if (predictResult.status === "ERROR") {
        return (
            <div className="mb-8 rounded-xl border border-red-200 bg-red-50 p-6">
                <p className="text-sm font-semibold text-red-600">
                    청중 집중도를 예측하지 못했습니다.
                </p>

                <p className="mt-1 text-sm text-red-500">
                    {predictResult.message ?? "음성 분석 중 오류가 발생했습니다."}
                </p>
            </div>
        )
    }

    return(
        <div>
            <TotalScore predictResult={predictResult} />
            <Graph predictResult={predictResult} />
        </div>
    )
}