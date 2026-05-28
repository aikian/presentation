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

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}

function isPinching(lm) {
  const thumbTip = lm[4]
  const indexTip = lm[8]
  const palmSize = Math.max(distance(lm[0], lm[9]), 0.08)
  const pinchDistance = distance(thumbTip, indexTip)
  const indexNotFoldedIntoFist = indexTip.y < lm[5].y + palmSize * 0.45
  return pinchDistance < palmSize * 0.38 && indexNotFoldedIntoFist
}

function getPinchPosition(lm) {
  const thumbTip = lm[4]
  const indexTip = lm[8]
  const x = (thumbTip.x + indexTip.x) / 2
  const y = (thumbTip.y + indexTip.y) / 2
  return {
    x: clamp((1 - x) * 100, 4, 96),
    y: clamp(y * 100, 6, 94),
  }
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
  const [pointer, setPointer] = useState(null)
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
            setPointer(null)
            return
          }

          const lm = multiHandLandmarks[0]
          if (isPinching(lm)) {
            gestureRef.current = { side: null, startTime: 0 }
            setHint(null); setProgress(0)
            setPointer(getPinchPosition(lm))
            return
          }

          setPointer(null)

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
    <div className="pointer-events-none absolute inset-x-0 top-0 bottom-16 z-10">
      <PinchPointer pointer={pointer} />
      <div className="absolute inset-0 flex items-center justify-between px-6">
        <GestureIndicator active={hint === 'left'} progress={hint === 'left' ? progress : 0} label="◀ 이전" />
        <GestureIndicator active={hint === 'right'} progress={hint === 'right' ? progress : 0} label="다음 ▶" />
      </div>
    </div>
  )
}

function PinchPointer({ pointer }) {
  if (!pointer) return null

  return (
    <div
      className="absolute z-20 h-12 w-12 -translate-x-1/2 -translate-y-1/2"
      style={{ left: `${pointer.x}%`, top: `${pointer.y}%` }}
    >
      <span className="absolute inset-0 rounded-full bg-red-500/25 animate-ping" />
      <span className="absolute inset-2 rounded-full border-2 border-white bg-red-500 shadow-[0_0_24px_rgba(239,68,68,0.9)]" />
      <span className="absolute left-1/2 top-1/2 h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white" />
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
