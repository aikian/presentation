const STEPS = [
    '영상 프레임 추출 중',
    '시선 분석 중 (FaceMesh)',
    '자세 분석 중 (Pose)',
    '제스처 분석 중 (Hands)',
    'AI 코칭 생성 중',
  ]
  
  export default function AnalysisProgress({ stepHint = 0 }) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-6 animate-pulse">🔍</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">영상 분석 중</h2>
          <p className="text-gray-500 mb-8">MediaPipe로 발표를 분석하고 있습니다</p>
  
          <div className="space-y-3 text-left">
            {STEPS.map((step, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className={`
                  w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0
                  ${i < stepHint ? 'bg-green-500 text-white' : i === stepHint ? 'bg-purple-500 text-white animate-pulse' : 'bg-gray-200 text-gray-400'}
                `}>
                  {i < stepHint ? '✓' : i + 1}
                </div>
                <span className={`text-sm ${i === stepHint ? 'text-purple-700 font-medium' : i < stepHint ? 'text-green-600' : 'text-gray-400'}`}>
                  {step}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }
  
