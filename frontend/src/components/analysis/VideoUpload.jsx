import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchSpeakers } from '../../api/client'
import Icon from '../common/Icons'

const ACCEPTED = '.mp4,.mov,.avi,.webm,.mkv'
const MAX_UPLOAD_MB = 95

const CHECKLIST = [
  { icon: 'eye', title: '시선', desc: '청중을 보는 시간과 시선이 흐트러지는 비율' },
  { icon: 'user', title: '자세', desc: '어깨 기울기와 몸의 안정감' },
  { icon: 'hand', title: '제스처', desc: '손동작 횟수와 적절한 빈도' },
  { icon: 'mic', title: '목소리', desc: '말 속도, 군말, 침묵, 억양' },
]

export default function VideoUpload({ onUpload, loading }) {
  const navigate = useNavigate()
  const [dragging, setDragging] = useState(false)
  const [speakers, setSpeakers] = useState([])
  const [rolemodelId, setRolemodelId] = useState('')
  const inputRef = useRef(null)

  // 따라 하고 싶은 연사를 고를 수 있게 목록을 받아둔다.
  // 목록을 못 받아도 업로드는 되어야 하므로 실패는 조용히 넘긴다.
  useEffect(() => {
    let alive = true
    fetchSpeakers()
      .then((list) => alive && setSpeakers(list))
      .catch(() => {})
    return () => { alive = false }
  }, [])

  function handleFile(file) {
    if (!file || loading) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['mp4', 'mov', 'avi', 'webm', 'mkv'].includes(ext)) {
      alert('MP4, MOV, AVI, WebM, MKV 파일만 업로드할 수 있습니다.')
      return
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      alert(`운영 서버에서는 ${MAX_UPLOAD_MB}MB 이하 영상만 업로드할 수 있습니다. 영상을 압축한 뒤 다시 시도해 주세요.`)
      return
    }
    onUpload(file, { rolemodelId: rolemodelId || null })
  }

  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-10 text-left">
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-950">영상 분석</h1>
        <p className="mt-2 text-base text-slate-600">녹화한 발표 영상을 올리면 AI가 분석하고 코칭 결과를 보여 드립니다.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        {/* 왼쪽: 업로드 + 연사 선택 */}
        <div className="space-y-6">
          <div
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); !loading && inputRef.current?.click() } }}
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }}
            onClick={() => !loading && inputRef.current?.click()}
            className={[
              'flex min-h-[20rem] cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed p-10 text-center',
              'transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
              dragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300 bg-white hover:border-blue-400 hover:bg-blue-50/40',
              loading ? 'cursor-wait opacity-70' : '',
            ].join(' ')}
          >
            <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
              {loading ? (
                <span className="h-7 w-7 animate-spin rounded-full border-[3px] border-blue-600 border-t-transparent" />
              ) : (
                <Icon name="upload" className="h-8 w-8" />
              )}
            </span>
            {loading ? (
              <>
                <p className="mt-5 text-lg font-bold text-slate-900">영상을 올리고 있어요</p>
                <p className="mt-1 text-sm text-slate-500">창을 닫지 말고 잠시만 기다려 주세요.</p>
              </>
            ) : (
              <>
                <p className="mt-5 text-lg font-bold text-slate-900">영상 파일을 여기로 끌어다 놓으세요</p>
                <p className="mt-1 text-sm text-slate-500">또는 클릭해서 파일 선택</p>
                <span className="mt-5 inline-flex rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white">파일 선택</span>
                <div className="mt-5 flex flex-wrap justify-center gap-1.5">
                  {['MP4', 'MOV', 'AVI', 'WebM', 'MKV'].map((f) => (
                    <span key={f} className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">{f}</span>
                  ))}
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">최대 {MAX_UPLOAD_MB}MB</span>
                </div>
              </>
            )}
            <input ref={inputRef} type="file" accept={ACCEPTED} className="hidden" onChange={(e) => handleFile(e.target.files[0])} />
          </div>

          {speakers.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6">
              <label htmlFor="rolemodel" className="block text-sm font-bold text-slate-900">
                따라 하고 싶은 연사 <span className="font-normal text-slate-400">(선택)</span>
              </label>
              <select
                id="rolemodel"
                value={rolemodelId}
                onChange={(e) => setRolemodelId(e.target.value)}
                disabled={loading}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30 disabled:opacity-60"
              >
                <option value="">고르지 않음 — 명연사 전체 범위와 비교</option>
                {speakers.map((s, i) => {
                  // 출처·소속은 보여주지 않고 이름만. 같은 연사의 강연이 여럿이면 번호로 구분한다.
                  const dup = speakers.filter((x) => x.name === s.name).length > 1
                  const nth = speakers.slice(0, i + 1).filter((x) => x.name === s.name).length
                  return (
                    <option key={s.id} value={s.id}>
                      {s.name}{dup ? ` ${nth}` : ''}
                    </option>
                  )
                })}
              </select>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                연사를 고르면 그 사람의 말속도·군말·침묵·억양과 1:1로 비교합니다. 고르지 않으면
                명연사 {speakers.length}편의 최소~최대 범위를 기준으로 봅니다.
              </p>
            </div>
          )}
        </div>

        {/* 오른쪽: 무엇을 분석하는지 + 촬영 모드 안내 */}
        <aside className="space-y-6">
          <div className="rounded-3xl border border-slate-200 bg-white p-6">
            <h2 className="text-lg font-bold text-slate-950">AI가 확인하는 항목</h2>
            <ul className="mt-5 space-y-4">
              {CHECKLIST.map((c) => (
                <li key={c.title} className="flex gap-3.5">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                    <Icon name={c.icon} className="h-5 w-5" />
                  </span>
                  <div>
                    <p className="text-sm font-bold text-slate-900">{c.title}</p>
                    <p className="mt-0.5 text-sm leading-6 text-slate-500">{c.desc}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="flex items-center justify-between gap-4 rounded-2xl bg-slate-950 p-5 text-white">
            <div>
              <p className="font-bold">영상이 아직 없나요?</p>
              <p className="mt-0.5 text-sm text-white/60">촬영 모드에서 바로 녹화할 수 있어요.</p>
            </div>
            <button
              onClick={() => navigate('/presentation')}
              className="shrink-0 rounded-xl bg-white px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-slate-100"
            >
              촬영하러 가기
            </button>
          </div>
        </aside>
      </div>
    </main>
  )
}
