import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import ResultTabs from '../components/result/ResultTabs'
import { fetchResult } from '../api/client'

// 히스토리에서 지난 분석 결과를 다시 연다.
// 업로드 직후의 job 응답과 달리 DB 행을 읽으므로 서버가 재시작돼도 열린다.
export default function ResultDetail() {
  const { resultId } = useParams()
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    fetchResult(resultId)
      .then((r) => alive && setResult(r))
      .catch((e) => alive && setError(e.response?.data?.detail ?? '결과를 불러오지 못했습니다'))
    return () => { alive = false }
  }, [resultId])

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-rose-600">{error}</p>
      </div>
    )
  }
  if (!result) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-slate-500">불러오는 중...</p>
      </div>
    )
  }
  return <ResultTabs result={result} resultId={resultId} />
}
