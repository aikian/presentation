import { useState, useRef } from 'react'

const ACCEPTED = '.mp4,.mov,.avi,.webm,.mkv'

export default function VideoUpload({ onUpload, loading }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef(null)

  function handleFile(file) {
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['mp4', 'mov', 'avi', 'webm', 'mkv'].includes(ext)) {
      alert('MP4, MOV, AVI, WebM, MKV 파일만 업로드할 수 있습니다.')
      return
    }
    onUpload(file)
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
    </div>
  )
}
