import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const features = [
  {
    id: 'presentation',
    icon: '🖥️',
    title: '발표 모드',
    description: 'PDF / PPTX 파일을 업로드하면\n슬라이드를 웹에서 직접 발표할 수 있습니다.',
    detail: '키보드 ← → 또는 버튼으로 슬라이드 전환',
    color: 'from-blue-500 to-indigo-600',
    bg: 'bg-blue-50 hover:bg-blue-100',
    border: 'border-blue-200 hover:border-blue-400',
    path: '/presentation',
  },
  {
    id: 'analysis',
    icon: '🎬',
    title: '영상 분석',
    description: '녹화된 발표 영상을 업로드하면\nAI가 시선·자세·제스처를 분석합니다.',
    detail: 'MediaPipe + Gemini AI 코칭 제공',
    color: 'from-purple-500 to-pink-600',
    bg: 'bg-purple-50 hover:bg-purple-100',
    border: 'border-purple-200 hover:border-purple-400',
    path: '/analysis',
  },
]

export default function Home() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
      <div className="absolute top-4 right-4 flex items-center gap-3">
        <span className="text-sm text-gray-400">{user?.email}</span>
        <button
          onClick={logout}
          className="text-xs text-gray-400 hover:text-gray-600 border border-gray-200 rounded-lg px-3 py-1.5 transition-colors"
        >
          로그아웃
        </button>
      </div>

      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-3">
          PresentationCoach 발표 분석
        </h1>
        <p className="text-lg text-gray-500">
          어떤 기능을 사용하시겠어요?
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-3xl">
        {features.map((f) => (
          <button
            key={f.id}
            onClick={() => navigate(f.path)}
            className={`
              ${f.bg} ${f.border}
              border-2 rounded-2xl p-8 text-left
              transition-all duration-200 cursor-pointer
              shadow-sm hover:shadow-md
              group
            `}
          >
            <div className="text-5xl mb-4">{f.icon}</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2 group-hover:text-gray-700">
              {f.title}
            </h2>
            <p className="text-gray-600 whitespace-pre-line text-sm leading-relaxed mb-3">
              {f.description}
            </p>
            <span className="inline-block text-xs text-gray-400 bg-white rounded-full px-3 py-1 border border-gray-200">
              {f.detail}
            </span>
          </button>
        ))}
      </div>

      <button
        onClick={() => navigate('/history')}
        className="mt-8 flex items-center gap-2 text-sm text-gray-500 hover:text-indigo-600 transition-colors"
      >
        <span>📋</span>
        <span>발표 히스토리 보기</span>
      </button>
    </div>
  )
}
