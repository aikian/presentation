import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ToastProvider } from './components/common/Toast'
// [2026-09-22 신규] 모든 화면 상단에 고정되는 전역 내비게이션
import NavBar from './components/common/NavBar'
import Home from './pages/Home'
import Login from './pages/Login'
import PresentationMode from './pages/PresentationMode'
import VideoAnalysis from './pages/VideoAnalysis'
import History from './pages/History'
// [신규 추가] 성장 분석 / 발표 영상 공유 게시판
import Growth from './pages/Growth'
import BoardList from './pages/BoardList'
import BoardWrite from './pages/BoardWrite'
import BoardDetail from './pages/BoardDetail'

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  return user ? children : <Navigate to="/login" replace />
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  return user ? <Navigate to="/" replace /> : children
}

// [2026-09-22 신규] 발표 모드(전체화면)와 로그인을 제외한 모든 화면을
// NavBar가 달린 공통 레이아웃으로 감싼다.
// 홈 카드에 의존하지 않고 어디서나 게시판/성장 분석으로 이동할 수 있다.
function Shell({ children }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      {children}
    </div>
  )
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />

      {/* 발표 모드는 전체화면이므로 NavBar를 띄우지 않는다 */}
      <Route path="/presentation" element={<PrivateRoute><PresentationMode /></PrivateRoute>} />

      <Route path="/" element={<PrivateRoute><Shell><Home /></Shell></PrivateRoute>} />
      <Route path="/analysis" element={<PrivateRoute><Shell><VideoAnalysis /></Shell></PrivateRoute>} />
      <Route path="/history" element={<PrivateRoute><Shell><History /></Shell></PrivateRoute>} />

      {/* [신규 추가] 성장 분석 / 발표 영상 공유 게시판 */}
      <Route path="/growth" element={<PrivateRoute><Shell><Growth /></Shell></PrivateRoute>} />
      <Route path="/board" element={<PrivateRoute><Shell><BoardList /></Shell></PrivateRoute>} />
      <Route path="/board/new" element={<PrivateRoute><Shell><BoardWrite /></Shell></PrivateRoute>} />
      <Route path="/board/:postId" element={<PrivateRoute><Shell><BoardDetail /></Shell></PrivateRoute>} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  )
}
