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

  return (
    <div className="flex-1 bg-black flex items-center justify-center overflow-hidden">
      <img
        src={slides[current]}
        alt={`슬라이드 ${current + 1}`}
        className="max-h-full max-w-full object-contain select-none"
        draggable={false}
      />
    </div>
  )
}
