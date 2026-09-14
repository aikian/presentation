//총점수
//Chart.js로 그래프 그리기
//청중 설문 결과
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
} from "chart.js";

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
);

const TEST_PREDICT_RESULT = {
    status: "SUCCESS",

    // 최종 집중도
    attention_score: 78.5,

    // 초 단위 집중도 변화
    timeline_second: [
        {
            sec: 0,
            score: 85,
            penalties: [],
            boosts: [],
        },
        {
            sec: 1,
            score: 85,
            penalties: [],
            boosts: [],
        },
        {
            sec: 2,
            score: 84.5,
            penalties: [],
            boosts: [],
        },
        {
            sec: 3,
            score: 84.5,
            penalties: [],
            boosts: [],
        },
        {
            sec: 4,
            score: 83.5,
            penalties: [],
            boosts: [],
        },
        {
            sec: 5,
            score: 82.5,
            penalties: [
                "말속도가 조금 빠릅니다."
            ],
            boosts: [],
        },
        {
            sec: 6,
            score: 82.5,
            penalties: [],
            boosts: [],
        },
        {
            sec: 7,
            score: 83.5,
            penalties: [],
            boosts: [
                "음량 강조 (+1.5)"
            ],
        },
        {
            sec: 8,
            score: 83.5,
            penalties: [],
            boosts: [],
        },
        {
            sec: 9,
            score: 82,
            penalties: [
                "발표 중 정적이 감지되었습니다."
            ],
            boosts: [],
        },
        {
            sec: 10,
            score: 79,
            penalties: [
                "2.5초 정적 감지 (-3.0)"
            ],
            boosts: [],
        },
        {
            sec: 11,
            score: 78,
            penalties: [
                "2.5초 정적 감지 (-1.5)"
            ],
            boosts: [],
        },
        {
            sec: 12,
            score: 78,
            penalties: [],
            boosts: [],
        },
        {
            sec: 13,
            score: 77,
            penalties: [
                "느린 말속도 (평균 200SPM)"
            ],
            boosts: [],
        },
        {
            sec: 14,
            score: 76,
            penalties: [],
            boosts: [],
        },
        {
            sec: 15,
            score: 75,
            penalties: [],
            boosts: [],
        },
        {
            sec: 16,
            score: 76.5,
            penalties: [],
            boosts: [
                "음량 강조 (+1.5)"
            ],
        },
        {
            sec: 17,
            score: 77,
            penalties: [],
            boosts: [],
        },
        {
            sec: 18,
            score: 77.5,
            penalties: [],
            boosts: [
                "단조로움 이후 피치 변화 (+2.0)"
            ],
        },
        {
            sec: 19,
            score: 78.5,
            penalties: [],
            boosts: [],
        },
    ],

    timeline_minute: [],

    total_stats: {
        total_spm_penalty_counts: 2,
        total_monotone_counts: 1,
        total_silence_counts: 2,
        total_silence_filler_counts: 1,
        total_filler_counts: 1,
        total_reengagement_boost_counts: 1,
        total_db_boost_counts: 2,
    },
};

// 총 점수
function TotalScore({ predictResult }) {
    if (!predictResult) {
        return null;
    }

    return (
        <div className="mb-8 rounded-xl border border-gray-200 bg-white p-6">
            <p className="text-sm font-medium text-gray-500">
                최종 집중도 점수
            </p>

            <div className="mt-2 flex items-end gap-2">
                <span className="text-4xl font-bold text-gray-600">
                    {Number(
                        predictResult.attention_score ?? 0
                    ).toFixed(1)}
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
                            : `${item.min}분`;
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

    return(
        <div>
            <TotalScore predictResult={result} />
            <Graph predictResult={result} />
            {/*<TotalScore predictResult={predictResult} />
            <Graph predictResult={predictResult} />*/}
        </div>
    )
}