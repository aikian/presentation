import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AttentionResult from "../components/attention/AttentionResult"
import CsvUpload from "../components/attention/CsvUpload"
import { fetchAttentionResult, fetchSurveyResult } from "../api/client"

const FEATURE_LABELS = {
    spm: "말속도 적절성",
    pitch_variation: "어조 변화",
    db: "음량 강조",
    silence: "정적/멈춤 적절성"
}

export default function PredictAttention() {

    const { id } = useParams()
    const navigate = useNavigate()

    const [predictResult, setPredictResult] = useState(null)
    const [surveyResult, setSurveyResult] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [surveyError, setSurveyError] = useState(null)

    // 집중도 분석 결과 + 이전에 저장된 설문 결과 가져오기
    useEffect(() => {
        async function loadData() {
            try {
                const [prediction, survey] = await Promise.all([
                    fetchAttentionResult(id),
                    fetchSurveyResult(id).catch(() => null)
                ])
                setPredictResult(prediction)
                setSurveyResult(survey?.survey_result ?? null)
            } catch (error) {
                setError("서버에서 예측 결과를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.")
            } finally {
                setLoading(false)
            }
        }

        loadData()
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

    const getActualAttentionScore = () => {
        if (!surveyResult) return null
        
        const score = Number(surveyResult.average_attention_score)
        return Number.isFinite(score) ? score : null
    }

    const actualScore = getActualAttentionScore()

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
                            음성기반 청중 집중도 추정 결과
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
                {predictResult ? (
                    <AttentionResult predictResult={predictResult} />
                ) : (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center">
                        <p className="text-sm font-semibold text-amber-800">
                            발표 영상에서 청중 집중도를 예측하지 못했습니다.
                        </p>
                        <p className="mt-1 text-xs leading-5 text-amber-700">
                            음성이 인식되지 않았거나 분석 중 예측에 실패했을 수 있습니다.
                            설문 결과는 아래에서 업로드할 수 있습니다.
                        </p>
                    </div>
                )}

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
                                <p className="mt-2 text-xs leading-5 text-indigo-800">
                                    업로드 CSV 열 순서: 응답자 번호, 문항 1~5번 점수, 자유 의견 (총 7열)
                                </p>
                                
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
                                        발표를 얼마나 집중해서 들으셨나요?
                                    </li>

                                    <li>
                                        자유 의견
                                    </li>
                                </ol>

                                <div className="mt-5 rounded-lg bg-indigo-50 p-4">
                                    <p className="text-xs leading-5 text-indigo-800">
                                        객관식 문항은 1~5점 척도로 구성하는 것을 권장합니다.
                                        단, 집중도 문항(5번)은 0~100점으로 입력해주세요.
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
                        <div className="mb-4 flex items-center justify-between">
                            <h2 className="mb-4 text-lg font-semibold text-gray-800">
                                청중 설문 결과
                            </h2>

                            <button
                                onClick={() => setSurveyResult(null)}
                                className="text-sm text-indigo-600 hover:text-indigo-800"
                            >
                                다시 업로드
                            </button>
                        </div>

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
                                    {actualScore !== null ? actualScore.toFixed(1) : "-"}

                                    <span className="ml-1 text-base font-normal text-gray-500">
                                        / 100
                                    </span>
                                </p>
                            </div>
                        </div>

                        {/* 설문 문항별 평균 점수 */}
                        {surveyResult.feature_means && (
                            <div className="mt-6">
                                <h3 className="mb-3 text-base font-semibold text-gray-800">
                                    설문 문항별 평균 (1~5점)
                                </h3>
                                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                                    {Object.entries(FEATURE_LABELS).map(([key, label]) => {
                                        const value = surveyResult.feature_means[key]
                                        return (
                                            <div key={key} className="rounded-lg bg-white p-4 text-center">
                                                <p className="text-xs text-gray-500">{label}</p>
                                                <p className="mt-1 text-xl font-bold text-gray-700">
                                                    {value != null ? Number(value).toFixed(1) : "-"}
                                                </p>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>
                        )}

                        {/* 가장 많이 나온 유형의 피드백 3가지만 보여줌 */}
                        {surveyResult.top_feedbacks && surveyResult.top_feedbacks.length > 0 && (
                            <div className="mt-6">
                                <h3 className="mb-3 text-base font-semibold text-gray-800">청중 피드백</h3>
                                <div className="space-y-2">
                                    {surveyResult.top_feedbacks.map((item, index) => {
                                        return (
                                            <div key={index} className="rounded-lg bg-white p-4">
                                                <p className="text-sm text-gray-700">{item.summary}</p>
                                                <span className="ml-3 shrink-0 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-600">
                                                    {item.count}건
                                                </span>
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
