// [2026-09-22 신규 파일] 전역 내비게이션 바
//
// 홈 화면 카드에만 의존하면 Home.jsx가 구버전일 때 게시판/성장 분석으로 갈 방법이
// 사라진다. 이 컴포넌트를 App.jsx의 Shell에 달아 두면 어느 화면에서든
// 영상 분석·녹화와 같은 위치에서 게시판과 성장 분석에 바로 들어갈 수 있다.
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const MENU = [
  { to: '/', label: '홈', end: true },
  { to: '/presentation', label: '발표 모드' },
  { to: '/analysis', label: '영상 분석' },
  { to: '/history', label: '발표 히스토리' },
  { to: '/growth', label: '성장 분석' },
  { to: '/board', label: '발표 사례 라이브러리' },
]

export default function NavBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  // 로그인 전에는 표시하지 않는다.
  if (!user) return null

  return (
    <header className="no-print sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
      <nav className="mx-auto flex max-w-5xl items-center gap-1 overflow-x-auto px-4 py-2">
        <button
          onClick={() => navigate('/')}
          className="mr-2 shrink-0 text-sm font-extrabold text-slate-900"
        >
          PresentationCoach
        </button>

        {MENU.map((m) => (
          <NavLink
            key={m.to}
            to={m.to}
            end={m.end}
            className={({ isActive }) =>
              `shrink-0 rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
                isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'
              }`
            }
          >
            {m.label}
          </NavLink>
        ))}

        <button
          onClick={logout}
          className="ml-auto shrink-0 rounded-lg px-3 py-1.5 text-sm font-semibold text-red-600 hover:bg-red-50"
        >
          로그아웃
        </button>
      </nav>
    </header>
  )
}
