import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { changePassword } from '../api/client'
import { useToast } from '../components/common/Toast'
import { useAuth } from '../context/AuthContext'

const SETTINGS_KEY = 'presentationcoach.settings'

const defaultSettings = {
  showFacePreview: true,
  defaultGoalMinutes: '',
  autoOpenHistory: false,
}

const features = [
  {
    id: 'presentation',
    icon: '화면',
    title: '발표 모드',
    description: 'PDF / PPTX 파일을 업로드하면\n슬라이드를 웹에서 직접 발표할 수 있습니다.',
    detail: '키보드 ← → 또는 버튼으로 슬라이드 전환',
    bg: 'bg-blue-50 hover:bg-blue-100',
    border: 'border-blue-200 hover:border-blue-400',
    path: '/presentation',
  },
  {
    id: 'analysis',
    icon: '분석',
    title: '영상 분석',
    description: '녹화된 발표 영상을 업로드하면\nAI가 시선·자세·제스처를 분석합니다.',
    detail: 'MediaPipe + Gemini AI 코칭 제공',
    bg: 'bg-purple-50 hover:bg-purple-100',
    border: 'border-purple-200 hover:border-purple-400',
    path: '/analysis',
  },
]

const scoreRows = [
  { item: '시선', weight: '30%', formula: '시선 이탈률 0% = 100점, 50% 이상 = 0점' },
  { item: '자세', weight: '25%', formula: '어깨 기울기 0도 = 100점, 20도 이상 = 0점' },
  { item: '제스처', weight: '15%', formula: '15회가 가장 좋고, 0회 또는 50회 이상이면 낮아짐' },
  { item: '시간', weight: '30%', formula: '목표 시간과의 오차 0% = 100점, 30% 이상 = 0점' },
]

const scorePolicies = [
  '각 항목은 0~100점으로 환산한 뒤 가중 평균으로 최종 점수를 계산합니다.',
  '시선과 자세는 문제가 적을수록 높은 점수를 주고, 기준치를 넘으면 0점에 가깝게 낮춥니다.',
  '제스처는 너무 적거나 과도한 경우를 모두 감점하고, 적절한 빈도의 손 동작을 가장 높게 평가합니다.',
  '목표 시간을 설정하지 않으면 시간 항목은 기본 80점으로 반영합니다.',
]

function loadSettings() {
  try {
    return { ...defaultSettings, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}') }
  } catch {
    return defaultSettings
  }
}

function saveSettings(next) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(next))
}

function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 rounded-full transition-colors ${checked ? 'bg-indigo-600' : 'bg-slate-300'}`}
    >
      <span className={`absolute top-1 h-4 w-4 rounded-full bg-white transition-transform ${checked ? 'left-6' : 'left-1'}`} />
    </button>
  )
}

function ScorePolicyContent() {
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {scoreRows.map((row) => (
          <div key={row.item} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-semibold text-slate-500">가중치 {row.weight}</p>
            <h3 className="mt-1 text-lg font-bold text-slate-950">{row.item}</h3>
            <p className="mt-2 text-xs leading-5 text-slate-600">{row.formula}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full min-w-[34rem] text-sm">
          <thead className="bg-slate-950 text-white">
            <tr>
              <th className="px-3 py-2 text-left">항목</th>
              <th className="px-3 py-2 text-left">가중치</th>
              <th className="px-3 py-2 text-left">계산 방식</th>
            </tr>
          </thead>
          <tbody>
            {scoreRows.map((row) => (
              <tr key={row.item} className="border-t border-slate-200 odd:bg-slate-50">
                <td className="px-3 py-2 font-semibold text-slate-900">{row.item}</td>
                <td className="px-3 py-2 text-slate-600">{row.weight}</td>
                <td className="px-3 py-2 text-slate-600">{row.formula}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 rounded-lg border border-indigo-100 bg-indigo-50 p-4">
        <p className="text-sm font-bold text-indigo-950">코칭 점수 정책</p>
        <div className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
          {scorePolicies.map((policy) => (
            <p key={policy}>{policy}</p>
          ))}
        </div>
      </div>

      <p className="mt-3 text-xs leading-5 text-slate-500">
        최종 점수 = 시선 30% + 자세 25% + 제스처 15% + 시간 30%입니다. 점수는 발표자의 장단점을 빠르게 파악하기 위한 코칭 지표이며, 분석 결과 화면과 PDF 리포트에 동일한 기준으로 표시됩니다.
      </p>
    </>
  )
}

function ScorePolicyModal({ onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="max-h-[88vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white p-6 text-left shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-indigo-600">Score Policy</p>
            <h2 className="mt-1 text-2xl font-bold text-slate-950">코칭 점수 알고리즘</h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              발표 분석 결과는 시선, 자세, 제스처, 시간 네 가지 지표를 점수화한 뒤 가중 평균으로 산출합니다.
            </p>
          </div>
          <button onClick={onClose} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-50">
            닫기
          </button>
        </div>

        <ScorePolicyContent />
      </div>
    </div>
  )
}

function SettingsModal({ user, onClose }) {
  const toast = useToast()
  const [settings, setSettings] = useState(loadSettings)
  const [savingPassword, setSavingPassword] = useState(false)
  const [passwords, setPasswords] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  })

  useEffect(() => {
    saveSettings(settings)
  }, [settings])

  function updateSetting(key, value) {
    setSettings((prev) => ({ ...prev, [key]: value }))
  }

  async function handlePasswordSubmit(e) {
    e.preventDefault()
    if (passwords.newPassword.length < 6) {
      toast('새 비밀번호는 6자 이상이어야 합니다.')
      return
    }
    if (passwords.newPassword !== passwords.confirmPassword) {
      toast('새 비밀번호 확인이 일치하지 않습니다.')
      return
    }

    setSavingPassword(true)
    try {
      await changePassword(passwords.currentPassword, passwords.newPassword)
      setPasswords({ currentPassword: '', newPassword: '', confirmPassword: '' })
      toast('비밀번호가 변경되었습니다.', 'success')
    } catch (e) {
      toast(e.response?.data?.detail ?? '비밀번호 변경에 실패했습니다.')
    } finally {
      setSavingPassword(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="max-h-[88vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white p-6 text-left shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-indigo-600">Settings</p>
            <h2 className="mt-1 text-2xl font-bold text-slate-950">계정 및 분석 설정</h2>
          </div>
          <button onClick={onClose} className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-50">
            닫기
          </button>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <section className="rounded-lg border border-slate-200 p-4">
            <h3 className="mb-3 text-base font-bold text-slate-900">계정</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">이메일</span>
                <span className="font-medium text-slate-900">{user?.email}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-slate-500">이름</span>
                <span className="font-medium text-slate-900">{user?.name || '미설정'}</span>
              </div>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 p-4">
            <h3 className="mb-3 text-base font-bold text-slate-900">발표 기본값</h3>
            <div className="space-y-3">
              <label className="flex items-center justify-between gap-4 text-sm">
                <span className="font-medium text-slate-700">발표 중 내 얼굴 표시</span>
                <Toggle checked={settings.showFacePreview} onChange={(v) => updateSetting('showFacePreview', v)} />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">기본 목표 시간 (분)</span>
                <input
                  type="number"
                  min="1"
                  max="120"
                  value={settings.defaultGoalMinutes}
                  onChange={(e) => updateSetting('defaultGoalMinutes', e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="선택"
                />
              </label>
              <label className="flex items-center justify-between gap-4 text-sm">
                <span className="font-medium text-slate-700">시작 후 히스토리 빠른 접근 표시</span>
                <Toggle checked={settings.autoOpenHistory} onChange={(v) => updateSetting('autoOpenHistory', v)} />
              </label>
            </div>
          </section>
        </div>

        <section className="mt-4 rounded-lg border border-slate-200 p-4">
          <h3 className="mb-3 text-base font-bold text-slate-900">비밀번호 변경</h3>
          <form onSubmit={handlePasswordSubmit} className="grid gap-3 md:grid-cols-3">
            <input
              type="password"
              value={passwords.currentPassword}
              onChange={(e) => setPasswords((prev) => ({ ...prev, currentPassword: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="현재 비밀번호"
            />
            <input
              type="password"
              value={passwords.newPassword}
              onChange={(e) => setPasswords((prev) => ({ ...prev, newPassword: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="새 비밀번호"
            />
            <div className="flex gap-2">
              <input
                type="password"
                value={passwords.confirmPassword}
                onChange={(e) => setPasswords((prev) => ({ ...prev, confirmPassword: e.target.value }))}
                className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="새 비밀번호 확인"
              />
              <button
                type="submit"
                disabled={savingPassword}
                className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              >
                변경
              </button>
            </div>
          </form>
        </section>

        <section className="mt-4">
          <h3 className="mb-3 text-base font-bold text-slate-900">점수 알고리즘</h3>
          <ScorePolicyContent />
        </section>
      </div>
    </div>
  )
}

export default function Home() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [scorePolicyOpen, setScorePolicyOpen] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    function handleClick(e) {
      if (!menuRef.current?.contains(e.target)) setMenuOpen(false)
    }
    window.addEventListener('mousedown', handleClick)
    return () => window.removeEventListener('mousedown', handleClick)
  }, [])

  function go(path) {
    setMenuOpen(false)
    navigate(path)
  }

  return (
    <div className="relative min-h-screen bg-gray-50 px-4 py-10">
      <div ref={menuRef} className="absolute right-4 top-4">
        <button
          onClick={() => setMenuOpen((open) => !open)}
          className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-left shadow-sm transition hover:border-indigo-200"
        >
          <span className="hidden max-w-52 truncate text-sm text-slate-500 sm:block">{user?.email}</span>
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-950 text-sm font-bold text-white">
            메뉴
          </span>
        </button>

        {menuOpen && (
          <div className="absolute right-0 mt-2 w-64 rounded-lg border border-slate-200 bg-white p-2 text-left shadow-xl">
            <div className="border-b border-slate-100 px-3 py-2">
              <p className="truncate text-sm font-semibold text-slate-900">{user?.email}</p>
              <p className="text-xs text-slate-400">{user?.name || 'PresentationCoach 사용자'}</p>
            </div>
            <button onClick={() => go('/history')} className="mt-2 w-full rounded-lg px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50">
              발표 히스토리
            </button>
            <button
              onClick={() => { setSettingsOpen(true); setMenuOpen(false) }}
              className="w-full rounded-lg px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
            >
              계정 및 설정
            </button>
            <button
              onClick={() => { setScorePolicyOpen(true); setMenuOpen(false) }}
              className="w-full rounded-lg px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
            >
              코칭 점수 알고리즘
            </button>
            <button
              onClick={logout}
              className="mt-2 w-full rounded-lg border border-red-100 px-3 py-2 text-left text-sm font-semibold text-red-600 hover:bg-red-50"
            >
              로그아웃
            </button>
          </div>
        )}
      </div>

      <main className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-4xl flex-col items-center justify-center">
        <div className="mb-12 text-center">
          <h1 className="mb-3 text-4xl font-bold text-gray-900">
            PresentationCoach 발표 분석
          </h1>
          <p className="text-lg text-gray-500">
            어떤 기능을 사용하시겠어요?
          </p>
        </div>

        <div className="grid w-full grid-cols-1 gap-6 md:grid-cols-2">
          {features.map((f) => (
            <button
              key={f.id}
              onClick={() => navigate(f.path)}
              className={`${f.bg} ${f.border} group rounded-lg border-2 p-8 text-left shadow-sm transition-all duration-200 hover:shadow-md`}
            >
              <div className="mb-4 inline-flex rounded-lg bg-white px-3 py-1 text-sm font-bold text-slate-700 shadow-sm">{f.icon}</div>
              <h2 className="mb-2 text-2xl font-bold text-gray-900 group-hover:text-gray-700">
                {f.title}
              </h2>
              <p className="mb-3 whitespace-pre-line text-sm leading-relaxed text-gray-600">
                {f.description}
              </p>
              <span className="inline-block rounded-full border border-gray-200 bg-white px-3 py-1 text-xs text-gray-400">
                {f.detail}
              </span>
            </button>
          ))}
        </div>

        <button
          onClick={() => navigate('/history')}
          className="mt-8 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-gray-500 transition-colors hover:text-indigo-600"
        >
          발표 히스토리 보기
        </button>
      </main>

      {settingsOpen && <SettingsModal user={user} onClose={() => setSettingsOpen(false)} />}
      {scorePolicyOpen && <ScorePolicyModal onClose={() => setScorePolicyOpen(false)} />}
    </div>
  )
}
