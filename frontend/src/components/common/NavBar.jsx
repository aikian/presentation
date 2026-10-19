// 전역 내비게이션 바 (UI 개선안 반영)
// 로고 · 메뉴 · 사용자 영역을 분리하고, 현재 위치는 파란 배경으로 표시한다.
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const MENU = [
  { to: '/', label: '홈', end: true },
  { to: '/presentation', label: '촬영 모드' },
  { to: '/analysis', label: '영상 분석' },
  { to: '/history', label: '발표 기록' },
  { to: '/growth', label: '성장 분석' },
  { to: '/board', label: '사례 라이브러리' },
]

export default function NavBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  if (!user) return null

  // 기존 logout()은 동기 함수(토큰 삭제 + user 초기화)라서 그대로 호출하면 된다.
  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="no-print sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 backdrop-blur-md">
      <div className="mx-auto flex min-h-[68px] max-w-7xl items-center gap-6 px-5">
        <button
          type="button"
          onClick={() => navigate('/')}
          className="flex shrink-0 items-center gap-2.5 text-lg font-extrabold tracking-tight text-slate-950"
          aria-label="PresentAI 홈으로 이동"
        >
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-blue-600 text-sm text-white">
            P
          </span>
          PresentAI
        </button>

        <nav aria-label="주요 메뉴" className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto py-2">
          {MENU.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                [
                  'shrink-0 rounded-xl px-3 py-2 text-sm font-semibold transition-colors duration-150',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
                  isActive ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950',
                ].join(' ')
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex shrink-0 items-center gap-3 border-l border-slate-200 pl-4">
          <div className="hidden text-right md:block">
            <p className="max-w-36 truncate text-sm font-semibold text-slate-800">{user.name || '사용자'}</p>
            <p className="max-w-36 truncate text-xs text-slate-500">{user.email || ''}</p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
          >
            로그아웃
          </button>
        </div>
      </div>
    </header>
  )
}
