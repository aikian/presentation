import { useState, useRef } from 'react'
import Icon from '../common/Icons'

const ACCEPTED = '.pdf,.pptx,.ppt'

const CHECKS = [
  { icon: 'video', title: '카메라와 마이크 허용', desc: '시작하면 브라우저가 권한을 물어봅니다. 허용해야 녹화됩니다.' },
  { icon: 'slides', title: '슬라이드는 키보드나 손동작으로', desc: '← → 키, 버튼, 또는 카메라 앞에서 손을 좌우로 휘두르면 넘어갑니다.' },
  { icon: 'clock', title: '목표 시간은 시작 전에 설정', desc: '시간을 정해 두면 분석 점수에 목표 대비 시간이 반영됩니다.' },
]

// 촬영 모드 첫 화면: 슬라이드 파일 올리기 + 촬영 전 확인 사항
export default function FileUpload({ onUpload, loading }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef(null)

  function handleFile(file) {
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['pdf', 'pptx', 'ppt'].includes(ext)) {
      alert('PDF 또는 PPTX 파일만 업로드할 수 있습니다.')
      return
    }
    onUpload(file)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-10 text-left">
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-950">촬영 모드</h1>
        <p className="mt-2 text-base text-slate-600">발표 슬라이드를 올리면 전체 화면으로 띄우고, 발표하는 모습을 함께 녹화합니다.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); !loading && inputRef.current?.click() } }}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => !loading && inputRef.current?.click()}
          className={[
            'flex min-h-[26rem] cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed p-10 text-center',
            'transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
            dragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300 bg-white hover:border-blue-400 hover:bg-blue-50/40',
            loading ? 'cursor-wait opacity-70' : '',
          ].join(' ')}
        >
          <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
            {loading ? (
              <span className="h-7 w-7 animate-spin rounded-full border-[3px] border-blue-600 border-t-transparent" />
            ) : (
              <Icon name="slides" className="h-8 w-8" />
            )}
          </span>
          {loading ? (
            <>
              <p className="mt-5 text-lg font-bold text-slate-900">슬라이드를 변환하고 있어요</p>
              <p className="mt-1 text-sm text-slate-500">장수가 많으면 조금 걸릴 수 있습니다.</p>
            </>
          ) : (
            <>
              <p className="mt-5 text-lg font-bold text-slate-900">슬라이드 파일을 여기로 끌어다 놓으세요</p>
              <p className="mt-1 text-sm text-slate-500">또는 클릭해서 파일 선택</p>
              <span className="mt-5 inline-flex rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white">파일 선택</span>
              <p className="mt-5 text-xs text-slate-400">PDF · PPTX 지원 · 최대 500MB</p>
            </>
          )}
          <input ref={inputRef} type="file" accept={ACCEPTED} className="hidden" onChange={(e) => handleFile(e.target.files[0])} />
        </div>

        <aside className="rounded-3xl border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-bold text-slate-950">촬영 전에 확인하세요</h2>
          <ul className="mt-5 space-y-5">
            {CHECKS.map((c) => (
              <li key={c.title} className="flex gap-3.5">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-700">
                  <Icon name={c.icon} className="h-5 w-5" />
                </span>
                <div>
                  <p className="text-sm font-bold text-slate-900">{c.title}</p>
                  <p className="mt-0.5 text-sm leading-6 text-slate-500">{c.desc}</p>
                </div>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </main>
  )
}
