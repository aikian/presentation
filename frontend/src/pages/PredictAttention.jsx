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
    const [surveyError, setSurveyError] = useState(null)

    // 집중도 분석 결과 가져오기
    useEffect(() => {
        async function loadPrediction() {
            try {
                const data = await fetchAttentionResult(id)
                setPredictResult(data)
            } catch (error) {
                setError("예측 결과를 가져오는 데 실패했습니다.")
            } finally {
                setLoading(false)
            }
        }

        loadPrediction()
    }, [id])

    const handleSurveyUploaded = (data) => {

        const result = data?.analysis_result ?? data?.survey_result ?? null

        if (!result) {
            setSurveyError("설문 결과를 불러오지 못했습니다. 다시 업로드해 주세요.")
            return
        }

        setSurveyError(null)
        setSurveyResult(result)
    }


    // 청중의 실제 집중도를 0~100점으로 환산
    const getActualAttentionScore = () => {
        if (!surveyResult) return null
        
        const score = Number(surveyResult.average_attention_score)

        if (!Number.isFinite(score)) {
            return null
        }

        return (score / 5) * 100
    }

    // 신뢰도 계산
    const getPredictConfidence = () => {
        if(!predictResult || !surveyResult) {
            return null
        }

        // 예측에 실패한 경우(점수 없음)에는 계산하지 않음
        if (predictResult.attention_score == null) {
            return null
        }

        const predictedScore = Number(predictResult.attention_score)
        const actualScore = getActualAttentionScore()

        if(!Number.isFinite(predictedScore) || actualScore===null){
            return null
        }

        const error = Math.abs(predictedScore - actualScore)
        const confidence = Math.max(0, 100 - error)

        return {
            predictedScore,
            actualScore,
            error,
            confidence
        }
    }

    const predictConfidence = getPredictConfidence()

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
                    <p className="text-red-500 mb-4">
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
                    <div className="mt-8 rounded-xl border border-gray-200 bg-gray-50 p-8">
                        <div className="mb-6 text-center">
                            <h2 className="mb-2 text-lg font-semibold text-gray-800">
                                청중 설문 결과
                            </h2>

                            <p className="text-sm leading-6 text-gray-500">
                                다음 설문 문항을 참고하여 청중 설문을 진행한 후
                                <br/>
                                응답 결과를 CSV 파일로 업로드해주세요.
                            </p>
                        </div>

                        {/* 권장 설문 문항 */}
                        <details className="mb-6 rounded-lg border border-gray-200 bg-white">
                            <summary className="cursor-pointer px-5 py-4 text-sm font-semibold text-gray-800">
                                권장 설문 문항 보기
                            </summary>

                            <div className="border-t border-gray-100 px-5 py-4">
                                <ol className="list-decimal list-inside space-y-3 text-left text-sm leading-6 text-gray-700">
                                    <li>
                                        발표자의 말하는 속도는 적절했나요?
                                    </li>

                                    <li>
                                        발표자의 목소리에 적절한 변화가 있어서 집중하기 좋았나요?
                                    </li>

                                    <li>
                                        목소리 크기 강조가 적절했나요?
                                    </li>

                                    <li>
                                        발표 중 멈춤이나 침묵이 발표 내용을 이해하는 데 적절했나요?
                                    </li>

                                    <li>
                                        "음", "어", "그..." 등의 군말이 발표 집중에 방해가 되었나요?
                                    </li>

                                    <li>
                                        발표를 얼마나 집중해서 들으셨나요?
                                    </li>

                                    <li>
                                        발표가 진행되는 동안 집중력이 잘 유지되었나요?
                                    </li>

                                    <li>
                                        자유 의견
                                    </li>
                                </ol>

                                <div className="mt-5 rounded-lg bg-indigo-50 p-4">
                                    <p className="text-xs leading-5 text-indigo-800">
                                        객관식 문항은 1~5점 척도로 구성하는 것을 권장합니다.
                                        자유 의견 문항은 서술형으로 설정해주세요.
                                    </p>
                                </div>
                            </div>
                        </details>

                        {/* CSV 업로드 */}
                        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-6 text-center">
                            <h3 className="mb-2 text-sm font-semibold text-gray-800">
                                설문 결과 CSV 업로드
                            </h3>
                            <CsvUpload 
                                resultId={id}
                                onUploaded={handleSurveyUploaded}
                            />

                            {surveyError && (
                                <p className="mt-2 text-sm text-red-500">
                                    {surveyError}
                                </p>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="mt-8 rounded-xl border border-gray-200 bg-gray-50 p-8">
                        <h2 className="mb-4 text-lg font-semibold text-gray-800">
                            청중 설문 결과
                        </h2>

                        <div className="grid grid-cols-3 gap-4">
                            <div className="rounded-lg bg-white p-4">
                                <p className="text-sm text-gray-600">참여 인원</p>
                                <p className="mt-1 text-2xl font-bold">
                                    {surveyResult.participant_count}
                                    <span className="ml-1 text-base font-normal text-gray-500">
                                        명
                                    </span>
                                </p>
                            </div>

                            {/* 실제 집중도 */}
                            <div className="rounded-lg bg-white p-4">
                                <p className="text-sm text-gray-600">실제 청중 집중도</p>
                                <p className="mt-1 text-3xl font-bold text-green-600">
                                    {predictConfidence
                                        ? predictConfidence.actualScore.toFixed(1)
                                        : "-"
                                    }

                                    <span className="ml-1 text-base font-normal text-gray-500">
                                        / 100
                                    </span>
                                </p>

                                <p className="mt-1 text-xs text-gray-400">
                                    집중도 평균{" "}
                                    {surveyResult.average_attention_score}
                                    {" / 5"}
                                </p>
                            </div>

                            {/* 예측 신뢰도 */}
                            <div className="rounded-lg bg-white p-5">
                                <p className="text-sm text-gray-500">
                                    예측 신뢰도
                                </p>

                                {predictConfidence ? (
                                    <div>
                                        <p className="mt-1 text-3xl font-bold text-indigo-600">
                                            {predictConfidence.confidence.toFixed(1)} %
                                        </p>

                                        <p className="mt-1 text-xs text-gray-400">
                                            예측{" "}
                                            {predictConfidence.predictedScore.toFixed(1)}

                                            {" / "}

                                            실제{" "}
                                            {predictConfidence.actualScore.toFixed(1)}
                                            점
                                        </p>
                                    </div>
                                        
                                ): (
                                    <p className="mt-1 text-3xl font-bold text-gray-400">
                                        -
                                    </p>
                                )}
                            </div>
                        </div>

                        {/* 설문 결과는 가장 많이 나온 유형의 피드백 3가지만 보여주도록 수정 필요 */}
                        {surveyResult.feedbacks && surveyResult.feedbacks.length > 0 && (
                            <div className="mt-6">
                                <h3 className="mb-3 text-base font-semibold text-gray-800">청중 피드백</h3>
                                <div className="space-y-2">
                                    {surveyResult.feedbacks.map((item, index) => {
                                        
                                        const text = typeof item === 'string' ? item : item?.text

                                        if (!text) return null

                                        return (
                                            <div key={item?.id ?? index} className="rounded-lg bg-white p-4">
                                                <p className="text-sm text-gray-700">{text}</p>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>

                        )}
                    </div>
                )}

            </div>
        </div>
    )
}
