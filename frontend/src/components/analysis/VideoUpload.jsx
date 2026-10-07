import { useState, useRef, useEffect } from 'react'
import { fetchSpeakers } from '../../api/client'

const ACCEPTED = '.mp4,.mov,.avi,.webm,.mkv'

export default function VideoUpload({ onUpload, loading }) {
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
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['mp4', 'mov', 'avi', 'webm', 'mkv'].includes(ext)) {
      alert('MP4, MOV, AVI, WebM, MKV 파일만 업로드할 수 있습니다.')
      return
    }
    onUpload(file, { rolemodelId: rolemodelId || null })
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">영상 분석</h1>
      <p className="text-gray-500 mb-8">녹화된 발표 영상을 업로드하세요</p>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }}
        onClick={() => !loading && inputRef.current?.click()}
        className={`
          w-full max-w-lg border-2 border-dashed rounded-2xl p-16
          flex flex-col items-center justify-center cursor-pointer
          transition-all duration-200
          ${dragging ? 'border-purple-500 bg-purple-50' : 'border-gray-300 bg-white hover:border-purple-400 hover:bg-purple-50'}
          ${loading ? 'opacity-60 cursor-wait' : ''}
        `}
      >
        <span className="text-5xl mb-4">🎬</span>
        {loading ? (
          <>
            <p className="text-purple-600 font-medium">업로드 중...</p>
            <p className="text-sm text-gray-400 mt-1">잠시 기다려주세요</p>
          </>
        ) : (
          <>
            <p className="text-gray-700 font-medium">영상 파일을 여기에 드래그하거나 클릭하세요</p>
            <p className="text-sm text-gray-400 mt-1">MP4, MOV, AVI, WebM 지원 · 최대 500MB</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          className="hidden"
          onChange={(e) => handleFile(e.target.files[0])}
        />
      </div>

      {speakers.length > 0 && (
        <div className="mt-6 w-full max-w-lg">
          <label htmlFor="rolemodel" className="block text-sm font-medium text-gray-700">
            따라 하고 싶은 연사 <span className="font-normal text-gray-400">(선택)</span>
          </label>
          <select
            id="rolemodel"
            value={rolemodelId}
            onChange={(e) => setRolemodelId(e.target.value)}
            disabled={loading}
            className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-purple-400 focus:outline-none disabled:opacity-60"
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
          <p className="mt-1.5 text-xs leading-relaxed text-gray-500">
            연사를 고르면 그 사람의 말속도·군말·침묵·억양과 1:1로 비교합니다. 고르지 않으면
            명연사 {speakers.length}편의 최소~최대 범위를 기준으로 봅니다.
          </p>
        </div>
      )}
    </div>
  )
}
