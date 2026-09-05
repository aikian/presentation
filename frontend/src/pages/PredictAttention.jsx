import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AttentionResult from "../components/attention/AttentionResult"
import CsvUpload from "../components/attention/CsvUpload"
import { fetchAttentionResult } from "../api/client"

export default function PredictAttention() {

    const { id } = useParams()
    const navigate = useNavigate()

    const [predictResult, setPredictResult] = useState(null)
    const [surveyResult, setSurveyResult] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    // 집중도 분석 결과 가져오기
    useEffect(() => {
        async function loadPrediction() {
            try {
                const data = await fetchAttentionResult(id)
                console.log("청중 집중도 조회 결과:", data)
                setPredictResult(data)
            } catch (error) {
                console.error("청중 집중도 조회 실패:", error)
                setError("예측 결과를 가져오는 데 실패했습니다.")
            } finally {
                setLoading(false)
            }
        }

        loadPrediction()
    }, [id])

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <p className="text-gray-500">
                    청중 집중도 예측 결과를 불러오는 중...
                </p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <p className="text-red-500">
                        {error}
                    </p>

                    <button
                        onClick={() => navigate('/history')}
                        className="text-sm text-indigo-600 hover:text-indigo-800 border border-indigo-300 rounded-lg px-4 py-2"
                    >
                        이전으로
                    </button>
                </div>
            </div>
        )
    }

    return(
        <div className="min-h-screen bg-gray-50 px-6 py-10">
            <div className="mx-auto max-w-6xl rounded-xl bg-white p-8 shadow-sm">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="mb-2 text-2xl font-bold text-gray-900">
                            청중 집중도 분석 결과
                        </h1>

                        <p className="text-sm text-gray-600">
                            발표 중 예측된 청중 집중도와 실제 설문 결과를 확인하실 수 있습니다.
                        </p>
                    </div>

                    <button
                        onClick={() => navigate('/history')}
                        className="shrink-0 text-sm text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg px-4 py-2 transition-colors"
                    >
                        이전으로
                    </button>
                </div>

                {/* 예측 집중도 시간순으로 그래프 표현*/}
                <AttentionResult predictResult={predictResult} />

                {/* 설문 결과가 없으면 업로드 버튼 표시 */}
                {!surveyResult ? (
                    <div className="mt-8 rounded-xl border border-gray-200 bg-gray-50 p-8 text-center">
                        <h2 className="mb-2 text-lg font-semibold text-gray-800">
                            청중 설문 결과가 없습니다.
                        </h2>
                        <p className="mb-5 text-sm text-gray-500">
                            아래 버튼을 클릭하여 설문 결과를 CSV 파일로 업로드해주세요.
                        </p>
                        <CsvUpload 
                            resultId={id}
                            onUploaded={(data) => {
                                console.log("CSV 분석 결과:", data)
                                setSurveyResult(data.analysis_result)
                            }}
                        />
                    </div>
                ) : (
                    <div className="mt-8 rounded-xl border border-gray-200 bg-gray-50 p-8">
                        <h2 className="mb-4 text-lg font-semibold text-gray-800">
                            청중 설문 결과
                        </h2>

                        <div className="grid grid-cols-3 gap-4">
                            <div className="rounded-lg bg-white p-4">
                                <p className="text-sm text-gray-600">참여 인원</p>
                                <p className="mt-1 text-2xl font-bold">{surveyResult.participant_count}</p>
                            </div>

                            <div className="rounded-lg bg-white p-4">
                                <p className="text-sm text-gray-600">집중도 평균</p>
                                <p className="mt-1 text-2xl font-bold">{surveyResult.average_attention_score}</p>
                            </div>
                        </div>

                        {/* 설문 결과는 가장 많이 나온 유형의 피드백 3가지만 보여주도록 수정 필요 */}
                        {surveyResult.feedbacks && surveyResult.feedbacks.length > 0 && (
                            <div className="mt-6">
                                <h3 className="mb-3 text-base font-semibold text-gray-800">청중 피드백</h3>
                                <div className="space-y-2">
                                    {surveyResult.feedbacks.map((item, index) => (
                                        <div key={item.id ?? index} className="rounded-lg bg-white p-4">
                                            <p className="text-sm text-gray-700">{item.text}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

            </div>
        </div>
    )
}
