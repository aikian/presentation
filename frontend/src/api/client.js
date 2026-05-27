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

export async function signup(email, password, name) {
  const { data } = await api.post('/auth/signup', { email, password, name })
  return data // { access_token, token_type }
}

export async function login(email, password) {
  const { data } = await api.post('/auth/login', { email, password })
  return data // { access_token, token_type }
}

export async function fetchMe() {
  const { data } = await api.get('/auth/me')
  return data // { id, email, name }
}

export async function fetchHistory(page = 1, limit = 20) {
  const { data } = await api.get('/history', { params: { page, limit } })
  return data // { items: [...], page, limit }
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

/**
 * @param {File} file
 * @param {{ goal_sec?: number, elapsed_sec?: number, slide_log?: object[] }} metadata
 */
export async function uploadVideo(file, metadata = {}) {
  const form = new FormData()
  form.append('file', file)
  if (metadata.goal_sec != null) form.append('goal_sec', metadata.goal_sec)
  if (metadata.elapsed_sec != null) form.append('elapsed_sec', metadata.elapsed_sec)
  if (metadata.slide_log?.length) form.append('slide_log', JSON.stringify(metadata.slide_log))
  const { data } = await api.post('/analysis/upload', form)
  return data // { job_id }
}

export async function pollAnalysis(jobId) {
  const { data } = await api.get(`/analysis/${jobId}`)
  return data // { status, result? }
}
