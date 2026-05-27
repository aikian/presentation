import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'

const MIME_TYPE = (() => {
  const types = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm', 'video/mp4']
  return types.find((t) => MediaRecorder.isTypeSupported(t)) ?? ''
})()

const WebcamRecorder = forwardRef(function WebcamRecorder({ onStream }, ref) {
  const videoRef = useRef(null)
  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)
  const [status, setStatus] = useState('init') // init | recording | denied

  useEffect(() => {
    navigator.mediaDevices
      .getUserMedia({ video: true, audio: true })
      .then((stream) => {
        streamRef.current = stream
        if (videoRef.current) videoRef.current.srcObject = stream

        const recorder = new MediaRecorder(stream, MIME_TYPE ? { mimeType: MIME_TYPE } : {})
        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) chunksRef.current.push(e.data)
        }
        recorder.start(1000)
        recorderRef.current = recorder
        setStatus('recording')
        onStream?.(stream)
      })
      .catch(() => setStatus('denied'))

    return () => {
      recorderRef.current?.state !== 'inactive' && recorderRef.current?.stop()
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }
  }, [])

  useImperativeHandle(ref, () => ({
    stop: () =>
      new Promise((resolve) => {
        const recorder = recorderRef.current
        if (!recorder || recorder.state === 'inactive') {
          resolve(new Blob(chunksRef.current, { type: MIME_TYPE || 'video/webm' }))
          return
        }
        recorder.onstop = () => {
          streamRef.current?.getTracks().forEach((t) => t.stop())
          resolve(new Blob(chunksRef.current, { type: MIME_TYPE || 'video/webm' }))
        }
        recorder.stop()
      }),
  }))

  if (status === 'denied' || status === 'init') return null

  return (
    <div className="absolute bottom-16 right-4 z-20">
      <div className="relative w-32 h-24 rounded-xl overflow-hidden border-2 border-red-500 shadow-xl">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="w-full h-full object-cover scale-x-[-1]"
        />
        <div className="absolute top-1.5 right-1.5 flex items-center gap-1">
          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          <span className="text-white text-[9px] font-semibold">REC</span>
        </div>
      </div>
    </div>
  )
})

export default WebcamRecorder
