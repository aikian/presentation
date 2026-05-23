import axios from 'axios'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
const api = axios.create({ baseURL: apiBaseUrl })

function resolveBackendAssetUrl(path) {
  if (!path || /^https?:\/\//.test(path) || !/^https?:\/\//.test(apiBaseUrl)) return path
  return new URL(path, apiBaseUrl).toString()
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export async function signup(email, password) {
  const { data } = await api.post('/auth/signup', { email, password })
  return data // { access_token, token_type }
}

export async function login(email, password) {
  const { data } = await api.post('/auth/login', { email, password })
  return data // { access_token, token_type }
}

export async function fetchMe() {
  const { data } = await api.get('/auth/me')
  return data // { id, email }
}

export async function fetchHistory() {
  const { data } = await api.get('/history')
  return data // [{ id, gaze_away_ratio, shoulder_tilt_avg, gesture_count, coaching, created_at }]
}

export async function downloadPdf(resultId) {
  const res = await api.get(`/history/${resultId}/pdf`, { responseType: 'blob' })
  const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `presentationcoach_report_${resultId.slice(0, 8)}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

export async function uploadSlides(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/slides/upload', form)
  data.slides = data.slides?.map(resolveBackendAssetUrl) ?? []
  return data // { session_id, slides: [url...], total }
}

export async function deleteSlides(sessionId) {
  await api.delete(`/slides/${sessionId}`)
}

export async function uploadVideo(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/analysis/upload', form)
  return data // { job_id }
}

export async function pollAnalysis(jobId) {
  const { data } = await api.get(`/analysis/${jobId}`)
  return data // { status, result? }
}

