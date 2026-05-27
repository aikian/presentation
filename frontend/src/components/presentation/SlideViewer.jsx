import { useEffect } from 'react'

export default function SlideViewer({ slides, current, onPrev, onNext }) {
  useEffect(() => {
    function handleKey(e) {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') onPrev()
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') {
        e.preventDefault()
        onNext()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onPrev, onNext])

  // 앞뒤 2장씩 미리 로드
  const preloadRange = []
  for (let i = Math.max(0, current - 2); i <= Math.min(slides.length - 1, current + 2); i++) {
    if (i !== current) preloadRange.push(i)
  }

  return (
    <div className="flex-1 min-h-0 w-full bg-black flex items-center justify-center overflow-hidden">
      <img
        src={slides[current]}
        alt={`슬라이드 ${current + 1}`}
        className="h-full w-full object-contain select-none"
        draggable={false}
      />
      {/* 숨겨진 preload 이미지 */}
      {preloadRange.map((i) => (
        <img key={i} src={slides[i]} alt="" style={{ display: 'none' }} />
      ))}
    </div>
  )
}
