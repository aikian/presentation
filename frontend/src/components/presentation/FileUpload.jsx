import { useState, useRef } from 'react'

const ACCEPTED = '.pdf,.pptx,.ppt'

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
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">발표 모드</h1>
      <p className="text-gray-500 mb-8">PDF 또는 PPTX 파일을 업로드하세요</p>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !loading && inputRef.current?.click()}
        className={`
          w-full max-w-lg border-2 border-dashed rounded-2xl p-16
          flex flex-col items-center justify-center cursor-pointer
          transition-all duration-200
          ${dragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-white hover:border-blue-400 hover:bg-blue-50'}
          ${loading ? 'opacity-60 cursor-wait' : ''}
        `}
      >
        <span className="text-5xl mb-4">📄</span>
        {loading ? (
          <>
            <p className="text-blue-600 font-medium">변환 중...</p>
            <p className="text-sm text-gray-400 mt-1">잠시 기다려주세요</p>
          </>
        ) : (
          <>
            <p className="text-gray-700 font-medium">파일을 여기에 드래그하거나 클릭하세요</p>
            <p className="text-sm text-gray-400 mt-1">PDF, PPTX 지원 · 최대 500MB</p>
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
