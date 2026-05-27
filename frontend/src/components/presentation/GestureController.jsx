import { useEffect, useRef, useState } from 'react'

const CDN = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1646424915'

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) { resolve(); return }
    const s = document.createElement('script')
    s.src = src
    s.crossOrigin = 'anonymous'
    s.onload = resolve
    s.onerror = reject
    document.head.appendChild(s)
  })
}

// 손가락 4개(검지~소지) 중 3개 이상이 MCP 관절보다 아래(y 큰) → 주먹
function isFist(lm) {
  const tips = [8, 12, 16, 20]
  const mcps = [5,  9, 13, 17]
  return tips.filter((t, i) => lm[t].y > lm[mcps[i]].y).length >= 3
}

// 화면 기준 좌우: 디스플레이는 mirror(-1) 이므로 raw x 부호 반전
// raw x < 0.35 → 화면 오른쪽 / raw x > 0.65 → 화면 왼쪽
function getScreenSide(lm) {
  const wx = lm[0].x
  if (wx < 0.35) return 'right'
  if (wx > 0.65) return 'left'
  return null
}

export default function GestureController({ stream, onLeft, onRight }) {
  const [hint, setHint] = useState(null)      // 'left' | 'right' | null
  const [progress, setProgress] = useState(0) // 0~100 (1초 홀드 진행률)
  const gestureRef = useRef({ side: null, startTime: 0 })

  useEffect(() => {
    if (!stream) return

    const video = document.createElement('video')
    video.srcObject = stream
    video.muted = true
    video.playsInline = true
    video.width = 320
    video.height = 240
    video.play().catch(() => {})

    let handsInstance = null
    let animId = null
    let active = true

    loadScript(`${CDN}/hands.js`)
      .then(() => {
        if (!active || !window.Hands) return

        handsInstance = new window.Hands({ locateFile: f => `${CDN}/${f}` })
        handsInstance.setOptions({
          maxNumHands: 1,
          modelComplexity: 0,
          minDetectionConfidence: 0.7,
          minTrackingConfidence: 0.5,
        })

        handsInstance.onResults(({ multiHandLandmarks }) => {
          if (!active) return

          if (!multiHandLandmarks?.length) {
            gestureRef.current = { side: null, startTime: 0 }
            setHint(null); setProgress(0)
            return
          }

          const lm = multiHandLandmarks[0]
          if (!isFist(lm)) {
            gestureRef.current = { side: null, startTime: 0 }
            setHint(null); setProgress(0)
            return
          }

          const side = getScreenSide(lm)
          if (!side) {
            gestureRef.current = { side: null, startTime: 0 }
            setHint(null); setProgress(0)
            return
          }

          setHint(side)

          if (gestureRef.current.side !== side) {
            gestureRef.current = { side, startTime: Date.now() }
            setProgress(0)
          } else {
            const held = Date.now() - gestureRef.current.startTime
            const pct = Math.min(100, (held / 1000) * 100)
            setProgress(pct)

            if (held >= 1000) {
              gestureRef.current = { side: null, startTime: 0 }
              setHint(null); setProgress(0)
              if (side === 'left') onLeft()
              else onRight()
            }
          }
        })

        async function loop() {
          if (!active) return
          if (video.readyState >= 2) {
            await handsInstance.send({ image: video }).catch(() => {})
          }
          animId = requestAnimationFrame(loop)
        }
        loop()
      })
      .catch(() => {})

    return () => {
      active = false
      cancelAnimationFrame(animId)
      handsInstance?.close()
      video.srcObject = null
    }
  }, [stream, onLeft, onRight])

  return (
    <div className="absolute inset-0 pointer-events-none z-10 flex items-center justify-between px-6">
      <GestureIndicator side="left" active={hint === 'left'} progress={hint === 'left' ? progress : 0} label="◀ 이전" />
      <GestureIndicator side="right" active={hint === 'right'} progress={hint === 'right' ? progress : 0} label="다음 ▶" />
    </div>
  )
}

function GestureIndicator({ active, progress, label }) {
  if (!active) return <div className="w-20" />
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-20 h-20">
        <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="6" />
          <circle
            cx="40" cy="40" r="34" fill="none"
            stroke="#3b82f6" strokeWidth="6"
            strokeDasharray={`${2 * Math.PI * 34}`}
            strokeDashoffset={`${2 * Math.PI * 34 * (1 - progress / 100)}`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 0.1s linear' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center text-2xl">✊</div>
      </div>
      <span className="text-white text-sm font-semibold bg-black/50 px-2 py-0.5 rounded">{label}</span>
    </div>
  )
}
