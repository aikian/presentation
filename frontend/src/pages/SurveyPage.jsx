import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { submitSurveyResponse } from '../api/client'

const QUESTIONS = [
  '발표자의 말하는 속도는 적절했나요?',
  '발표자의 목소리에 적절한 변화가 있어서 집중하기 좋았나요?',
  '목소리 크기 강조가 적절했나요?',
  '발표 중 멈춤이나 침묵이 발표 내용을 이해하는 데 적절했나요?',
]

// http 환경(폰)에서도 동작하도록 randomUUID가 없으면 대체 ID 사용
function makeId() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID()
  return 'p-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10)
}

// 같은 기기에서 같은 응답자로 인식하기 위한 익명 ID
function getParticipantId() {
  try {
    let id = localStorage.getItem('participant_id')
    if (!id) {
      id = makeId()
      localStorage.setItem('participant_id', id)
    }
    return id
  } catch {
    return makeId()
  }
}
export default function SurveyPage() {
  const { token } = useParams()

  const [scores, setScores] = useState(['', '', '', '', ''])
  const [opinion, setOpinion] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  function handleScoreChange(index, value) {
    setScores((prev) => 
      prev.map((score, i) => i === index ? value : score)
    )
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    if (scores.some(score => score === '')) {
      setError('모든 항목에 점수를 입력해주세요.')
      return
    }

    const payload = {
      participant_id: getParticipantId(),
      scores: {
        question_1: Number(scores[0]),
        question_2: Number(scores[1]),
        question_3: Number(scores[2]),
        question_4: Number(scores[3]),
        question_5: Number(scores[4])
      },
      opinion: opinion.trim()
    }
    
    setSubmitting(true)

    try {
      await submitSurveyResponse(token, payload)
      setSubmitted(true)
    } catch (err) {
      setError(err.message || '서버 연결에 실패했습니다.')
    } finally {
      setSubmitting(false)
    }
  }

  // 설문 제출 완료 화면
  if (submitted) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-5 py-10">
        <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-sm text-center">
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
            <span className="text-3xl text-green-600">✓</span>
          </div>

          <h1 className="text-2xl font-bold text-gray-900">설문이 제출되었습니다!</h1>
          
          <p className="mt-3 text-sm leading-6 text-gray-500">
            소중한 의견 감사합니다.
            <br/>
            여러분의 응답은 프로그램 개선에 활용됩니다.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-2xl rounded-2xl bg-white p-6 shadow-sm sm:p-8">

        {/* 설문 제목 */}
        <div className="mb-8 border-b border-gray-100 pb-6">
          <div className="mb-2 text-xs font-bold tracking-widest text-indigo-600">
            PRESENTATION SURVEY
          </div>

          <h1 className="text-2xl font-bold text-gray-900">
            청중 집중도 및 발표 평가
          </h1>

          <p className="mt-3 text-sm leading-6 text-gray-500">
            발표를 듣고 느낀 점을 자유롭게 작성해주세요.
            <br/>
            여러분의 응답은 청중의 집중도 분석에 활용됩니다.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          
          {/* 1~4번 문항 */}
          <div className="space-y-8">
            {QUESTIONS.map((question, index) => (
              <div key={index}>
                <h2 className="mb-3 text-sm font-bold leading-6 text-gray-800">
                  <span className="mr-2 text-indigo-600">
                    Q{index + 1}
                  </span>
                  {question}
                </h2>

                <div className="grid grid-cols-5 gap-2">
                  {[1, 2, 3, 4, 5].map((score) => (
                    <button
                      key={score}
                      type="button"
                      onClick={() => handleScoreChange(index, String(score))}
                      className={`rounded-xl border py-3 text-sm font-semibold transition ${
                        scores[index] === String(score)
                          ? 'border-indigo-600 bg-indigo-600 text-white'
                          : 'border-gray-200 bg-white text-gray-600 hover:border-indigo-300'
                      }`}
                    >
                      {score}
                    </button>
                  ))}
                </div>

                <div className="mt-2 flex justify-between text-xs text-gray-400">
                  <span>전혀 그렇지 않다</span>
                  <span>매우 그렇다</span>
                </div>
              </div>
            ))}
            
            {/* 5번 문항 */}
            <div>
              <h2 className="mb-3 text-sm font-bold leading-6 text-gray-800">
                <span className="mr-2 text-indigo-600">Q5.</span>
                음성을 기준으로 발표를 얼마나 집중해서 들으셨나요?
              </h2>

              <div className="rounded-xl bg-gray-50 p-4">
                <div className="mb-4 flex items-center justify-between">
                  <span className="text-xs text-gray-500">
                    전혀 집중하지 못함
                  </span>
                  
                  <span className="text-2xl font-bold text-indigo-600">
                    {scores[4] === '' ? '-' : scores[4]}
                    <span className="ml-1 text-sm font-medium">점</span>
                  </span>

                  <span className="text-xs text-gray-500">
                    매우 집중함
                  </span>
                </div>

                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={scores[4] === '' ? 50 : scores[4]}
                  onChange={(e) =>
                    handleScoreChange(4, e.target.value)
                  }
                  className="w-full cursor-pointer accent-indigo-600"
                />

                <div className="mt-2 flex justify-between text-xs text-gray-400">
                  <span>0점</span>
                  <span>50점</span>
                  <span>100점</span>
                </div>
              </div>
            </div>

            {/* 자유 의견 */}
            <div>
              <h2 className="mb-3 text-sm font-bold text-gray-800">
                <span className="mr-2 text-indigo-600">Q6.</span>
                발표에 대한 자유 의견
                <span className="ml-2 text-xs font-normal text-gray-400">
                  (선택)
                </span>
              </h2>

              <textarea
                value={opinion}
                onChange={(e) => setOpinion(e.target.value)}
                placeholder='발표에서 좋았던 점이나 개선하면 좋을 점을 자유롭게 작성해주세요.'
                rows={4}
                maxLength={1000}
                className="w-full resize-none rounded-xl border border-gray-200 p-4 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              />

              <p className="mt-1 text-right text-xs text-gray-400">
                {opinion.length} / 1000
              </p>
            </div>
          </div>

          {/* 오류 메시지 */}
          {error && (
            <div className="mt-6 rounded-lg bg-red-50 p-4 text-sm text-red-600">
              {error}
            </div>
          )}

          {/* 제출 버튼 */}
          <button
            type="submit"
            disabled={submitting}
            className="mt-8 w-full rounded-xl bg-indigo-600 py-4 text-sm font-bold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? '제출 중...' : '설문 제출하기'}
          </button>
        </form>
      </div>
    </div>
  )
}
