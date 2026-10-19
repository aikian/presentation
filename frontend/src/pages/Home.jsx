import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { changePassword, fetchGrowth, fetchHistory } from '../api/client'
import { useToast } from '../components/common/Toast'
import { useAuth } from '../context/AuthContext'
import Icon from '../components/common/Icons'

const SETTINGS_KEY = 'presentationcoach.settings'
const defaultSettings = {
  showFacePreview: true,
  defaultGoalMinutes: '',
  autoOpenHistory: false,
}

// 홈 하단 바로가기. 색은 모두 파란 계열로 통일하고, 의미 색(점수)과 섞지 않는다.
const shortcuts = [
  { id: 'presentation', icon: 'video', title: '촬영 모드', desc: '슬라이드를 띄우고 발표하며 녹화합니다.', path: '/presentation' },
  { id: 'analysis', icon: 'upload', title: '영상 분석', desc: '녹화한 영상을 올려 AI 코칭을 받습니다.', path: '/analysis' },
  { id: 'growth', icon: 'trend', title: '성장 분석', desc: '이전 발표와 점수 변화를 비교합니다.', path: '/growth' },
  { id: 'board', icon: 'library', title: '사례 라이브러리', desc: '다른 발표를 보고 내 발표와 비교합니다.', path: '/board' },
]

const scoreRows = [
  { item: '시선', weight: '35.12%', formula: '시선 이탈률 0% = 100점, 50% 이상 = 0점' },
  { item: '음성', weight: '35.12%', formula: '말속도 30% · 단조로움 30% · 군말 25% · 침묵 15%' },
  { item: '자세', weight: '18.87%', formula: '어깨 기울기 0도 = 100점, 20도 이상 = 0점' },
  { item: '제스처', weight: '10.89%', formula: '분당 2~4회 = 100점, 0회 또는 8회 이상 = 0점' },
  { item: '시간', weight: '별도', formula: '목표 시간 설정 시 오차 0% = 100점, 30% 이상 = 0점' },
]
const scorePolicies = [
  '시선·음성·자세·제스처를 0~100점으로 환산한 뒤 AHP 가중 평균으로 종합점수를 계산합니다.',
  '시선과 자세는 문제가 적을수록 높은 점수를 주고, 기준치를 넘으면 0점에 가깝게 낮춥니다.',
  '제스처는 너무 적거나 과도한 경우를 모두 감점하고, 적절한 빈도의 손 동작을 가장 높게 평가합니다.',
  '측정하지 못한 항목은 0점으로 처리하지 않고 제외한 뒤, 남은 가중치를 다시 환산합니다.',
  '시간 점수는 목표 시간을 설정한 경우에만 별도로 제공하며 종합점수에는 포함하지 않습니다.',
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
      className={`relative h-6 w-11 rounded-full transition-colors ${checked ? 'bg-blue-600' : 'bg-slate-300'}`}
    >
      <span className={`absolute top-1 h-4 w-4 rounded-full bg-white transition-transform ${checked ? 'left-6' : 'left-1'}`} />
    </button>
  )
}
function ScorePolicyContent() {
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {scoreRows.map((row) => (
          <div key={row.item} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-semibold text-slate-500">
              {row.weight === '별도' ? '종합점수와 별도' : `가중치 ${row.weight}`}
            </p>
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
      <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-4">
        <p className="text-sm font-bold text-blue-950">코칭 점수 정책</p>
        <div className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
          {scorePolicies.map((policy) => (
            <p key={policy}>{policy}</p>
          ))}
        </div>
      </div>
      <p className="mt-3 text-xs leading-5 text-slate-500">
        최종 점수 = 시선 35.12% + 음성 35.12% + 자세 18.87% + 제스처 10.89%입니다. 점수는 발표자의 장단점을 빠르게 파악하기 위한 코칭 지표이며, 분석 결과 화면과 PDF 리포트에 동일한 기준으로 표시됩니다.
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
            <p className="text-sm font-semibold text-blue-600">Score Policy</p>
            <h2 className="mt-1 text-2xl font-bold text-slate-950">코칭 점수 알고리즘</h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              발표 분석 결과는 시선, 음성, 자세, 제스처 네 가지 지표를 점수화한 뒤 가중 평균으로 산출합니다. 시간 점수는 별도로 제공합니다.
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
            <p className="text-sm font-semibold text-blue-600">Settings</p>
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
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
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
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="현재 비밀번호"
            />
            <input
              type="password"
              value={passwords.newPassword}
              onChange={(e) => setPasswords((prev) => ({ ...prev, newPassword: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="새 비밀번호"
            />
            <div className="flex gap-2">
              <input
                type="password"
                value={passwords.confirmPassword}
                onChange={(e) => setPasswords((prev) => ({ ...prev, confirmPassword: e.target.value }))}
                className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
// ── 홈 화면 전용 조각 ────────────────────────────────────────────
function num(v) {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

// 점수 색은 "의미"를 전달하는 용도로만 쓴다. (버튼·강조 파란색과 분리)
function scoreTone(score) {
  if (score >= 70) return { chip: 'bg-emerald-50 text-emerald-700', bar: '#10b981' }
  if (score >= 50) return { chip: 'bg-amber-50 text-amber-700', bar: '#f59e0b' }
  return { chip: 'bg-rose-50 text-rose-700', bar: '#f43f5e' }
}

function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}월 ${d.getDate()}일 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function fmtDuration(sec) {
  const s = num(sec)
  if (s == null || s <= 0) return null
  return `${Math.floor(s / 60)}분 ${Math.round(s % 60)}초`
}

function ScoreRing({ score }) {
  const r = 52
  const c = 2 * Math.PI * r
  const value = score == null ? 0 : Math.max(0, Math.min(100, score))
  return (
    <div className="relative h-36 w-36">
      <svg viewBox="0 0 128 128" className="h-full w-full -rotate-90">
        <circle cx="64" cy="64" r={r} fill="none" stroke="#dbeafe" strokeWidth="10" />
        <circle
          cx="64" cy="64" r={r} fill="none" stroke="#2563eb" strokeWidth="10" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - value / 100)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-extrabold tracking-tight text-slate-950">{score == null ? '-' : score}</span>
        <span className="text-xs font-semibold text-slate-500">최근 총점</span>
      </div>
    </div>
  )
}

function Sparkline({ values }) {
  if (values.length < 2) return null
  const w = 280
  const h = 72
  const pad = 6
  const pts = values.map((v, i) => {
    const x = pad + (i * (w - pad * 2)) / (values.length - 1)
    const y = h - pad - (Math.max(0, Math.min(100, v)) / 100) * (h - pad * 2)
    return [x, y]
  })
  const line = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const [lx, ly] = pts[pts.length - 1]
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-[72px] w-full" role="img" aria-label="최근 발표 점수 추이">
      <polyline points={line} fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={lx} cy={ly} r="4.5" fill="#2563eb" />
    </svg>
  )
}

function RecentRecords({ records, loading, onOpen, onAll, onStart }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-950">최근 발표 기록</h2>
        <button onClick={onAll} className="text-sm font-semibold text-blue-600 hover:text-blue-700">
          전체 보기
        </button>
      </div>

      {loading && <div className="h-40 animate-pulse rounded-xl bg-slate-100" />}

      {!loading && records.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 px-6 py-10 text-center">
          <p className="font-semibold text-slate-800">아직 분석한 발표가 없어요</p>
          <p className="mt-1 text-sm text-slate-500">첫 발표를 촬영하거나 영상을 올리면 여기에 기록이 쌓입니다.</p>
          <button
            onClick={onStart}
            className="mt-4 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
          >
            촬영 모드 시작
          </button>
        </div>
      )}

      {!loading && records.length > 0 && (
        <ul className="divide-y divide-slate-100">
          {records.map((r) => {
            const score = num(r.score_total)
            const tone = score == null ? null : scoreTone(score)
            const dur = fmtDuration(r.elapsed_sec)
            return (
              <li key={r.id}>
                <button
                  onClick={() => onOpen(r.id)}
                  className="flex w-full items-center gap-4 rounded-xl px-2 py-3.5 text-left transition hover:bg-slate-50"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-slate-900">{fmtDate(r.created_at)} 발표</p>
                    <p className="mt-0.5 text-xs text-slate-500">{dur ? `발표 시간 ${dur}` : '발표 시간 기록 없음'}</p>
                  </div>
                  {tone ? (
                    <span className={`rounded-full px-3 py-1 text-sm font-bold ${tone.chip}`}>{score}점</span>
                  ) : (
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-500">점수 없음</span>
                  )}
                  <Icon name="chevron" className="h-4 w-4 text-slate-300" />
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

function GrowthSummary({ trend, loading, onOpen }) {
  const scores = trend.map((p) => num(p.score_total)).filter((v) => v != null)
  const last = scores.length ? scores[scores.length - 1] : null
  const prev = scores.length > 1 ? scores[scores.length - 2] : null
  const best = scores.length ? Math.max(...scores) : null
  const delta = last != null && prev != null ? last - prev : null

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-950">성장 요약</h2>
        <button onClick={onOpen} className="text-sm font-semibold text-blue-600 hover:text-blue-700">
          자세히
        </button>
      </div>

      {loading && <div className="h-40 animate-pulse rounded-xl bg-slate-100" />}

      {!loading && scores.length < 2 && (
        <p className="rounded-xl bg-slate-50 px-4 py-8 text-center text-sm leading-6 text-slate-500">
          발표가 2회 이상 쌓이면<br />점수 변화 그래프가 표시됩니다.
        </p>
      )}

      {!loading && scores.length >= 2 && (
        <>
          <div className="flex items-end gap-6">
            <div>
              <p className="text-xs font-semibold text-slate-500">지난 발표 대비</p>
              <p className={`mt-1 text-3xl font-extrabold tracking-tight ${delta > 0 ? 'text-emerald-600' : delta < 0 ? 'text-rose-600' : 'text-slate-700'}`}>
                {delta > 0 ? `+${delta}` : delta}점
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-500">최고 점수</p>
              <p className="mt-1 text-3xl font-extrabold tracking-tight text-slate-950">{best}점</p>
            </div>
          </div>
          <div className="mt-5 rounded-xl bg-slate-50 px-3 py-3">
            <Sparkline values={scores} />
            <p className="mt-1 text-xs text-slate-500">최근 {scores.length}회 발표 총점</p>
          </div>
        </>
      )}
    </section>
  )
}

export default function Home() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [scorePolicyOpen, setScorePolicyOpen] = useState(false)
  const [records, setRecords] = useState([])
  const [trend, setTrend] = useState([])
  const [loading, setLoading] = useState(true)

  // 최근 기록과 성장 요약은 홈의 부가 정보이므로 하나가 실패해도 나머지는 보여 준다.
  useEffect(() => {
    let alive = true
    Promise.allSettled([fetchHistory(1, 4), fetchGrowth(10, false)]).then(([hist, growth]) => {
      if (!alive) return
      if (hist.status === 'fulfilled') {
        const items = hist.value?.items ?? hist.value
        setRecords(Array.isArray(items) ? items.slice(0, 4) : [])
      }
      if (growth.status === 'fulfilled') {
        setTrend(growth.value?.growth?.trend ?? [])
      }
      setLoading(false)
    })
    return () => { alive = false }
  }, [])

  const displayName = user?.name || user?.email?.split('@')[0] || '사용자'
  const latest = trend.length ? num(trend[trend.length - 1]?.score_total) : null

  return (
    <div className="bg-slate-50 text-left">
      <main className="mx-auto w-full max-w-7xl px-5 py-8">
        {/* 1. 첫 화면: 바로 시작할 수 있는 영역 */}
        <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white">
          <div className="grid items-center gap-8 p-8 md:grid-cols-[1fr_auto] md:p-10">
            <div>
              <p className="text-sm font-semibold text-blue-600">{displayName}님, 안녕하세요</p>
              <h1 className="mt-2 text-3xl font-extrabold leading-tight tracking-tight text-slate-950 md:text-4xl">
                오늘 발표를 연습하고
                <br />
                바로 분석해 보세요
              </h1>
              <p className="mt-3 max-w-md text-base leading-7 text-slate-600">
                슬라이드를 띄워 촬영하면 시선·자세·제스처·목소리를 AI가 분석하고, 다음 발표에서 고칠 점을 알려 줍니다.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  onClick={() => navigate('/presentation')}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                >
                  <Icon name="video" className="h-5 w-5" />
                  촬영 모드 시작
                </button>
                <button
                  onClick={() => navigate('/analysis')}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-800 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                >
                  <Icon name="upload" className="h-5 w-5" />
                  영상 올려서 분석
                </button>
              </div>
            </div>
            <div className="flex flex-col items-center gap-2 rounded-2xl bg-blue-50/70 px-10 py-6">
              <ScoreRing score={latest} />
              <p className="text-xs text-slate-500">
                {latest == null ? '발표를 분석하면 점수가 표시됩니다' : `최근 ${trend.length}회 중 마지막 발표`}
              </p>
            </div>
          </div>
        </section>

        {/* 2. 최근 기록 + 성장 요약 */}
        <div className="mt-6 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
          <RecentRecords
            records={records}
            loading={loading}
            onOpen={(id) => navigate(`/result/${id}`)}
            onAll={() => navigate('/history')}
            onStart={() => navigate('/presentation')}
          />
          <GrowthSummary trend={trend} loading={loading} onOpen={() => navigate('/growth')} />
        </div>

        {/* 3. 기능 바로가기 */}
        <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {shortcuts.map((s) => (
            <button
              key={s.id}
              onClick={() => navigate(s.path)}
              className="group rounded-2xl border border-slate-200 bg-white p-5 text-left transition hover:border-blue-300 hover:bg-blue-50/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 transition group-hover:bg-blue-600 group-hover:text-white">
                <Icon name={s.icon} />
              </span>
              <h3 className="mt-4 font-bold text-slate-950">{s.title}</h3>
              <p className="mt-1 text-sm leading-6 text-slate-500">{s.desc}</p>
            </button>
          ))}
        </section>

        {/* 4. 설정·점수 기준 (기존 우측 상단 드롭다운에 있던 항목) */}
        <div className="mt-6 flex flex-wrap items-center justify-end gap-2 text-sm">
          <button
            onClick={() => setScorePolicyOpen(true)}
            className="rounded-lg px-3 py-2 font-semibold text-slate-500 transition hover:bg-white hover:text-slate-900"
          >
            코칭 점수 기준
          </button>
          <button
            onClick={() => setSettingsOpen(true)}
            className="rounded-lg px-3 py-2 font-semibold text-slate-500 transition hover:bg-white hover:text-slate-900"
          >
            계정 및 설정
          </button>
        </div>
      </main>

      {settingsOpen && <SettingsModal user={user} onClose={() => setSettingsOpen(false)} />}
      {scorePolicyOpen && <ScorePolicyModal onClose={() => setScorePolicyOpen(false)} />}
    </div>
  )
}
