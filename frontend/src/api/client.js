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

export async function changePassword(currentPassword, newPassword) {
  const { data } = await api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
  return data
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

// ============================================================
// 성장 분석(Growth) API
// ============================================================
/**
 * @param {number} limit 비교에 사용할 최근 발표 개수 (2~50)
 * @param {boolean} ai   false면 AI 호출 없이 규칙 기반 피드백만 받는다
 */
export async function fetchGrowth(limit = 10, ai = true) {
  const { data } = await api.get('/history/growth', { params: { limit, ai } })
  // { schema_version, growth: { session_count, trend, compare_with_previous, feedback, feedback_source } }
  return data
}

// ============================================================
// 게시판(Board) API
// ============================================================
/**
 * @param {File} file
 * @param {(percent: number) => void} [onProgress] 업로드 진행률(0~100)
 */
export async function uploadBoardVideo(file, onProgress) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/board/upload-video', form, {
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return data // { video_storage_path, video_url }
}

/** @param {{ q?: string, topic?: string, tag?: string, sort?: 'latest'|'score', page?: number, limit?: number }} params */
export async function fetchBoardPosts({ q, topic, tag, sort = 'latest', page = 1, limit = 20 } = {}) {
  const { data } = await api.get('/board', {
    params: { q: q || undefined, topic: topic || undefined, tag: tag || undefined, sort, page, limit },
  })
  return data // { items: [...], page, limit, total }
}

export async function fetchMyBoardPosts(page = 1, limit = 20) {
  const { data } = await api.get('/board/mine', { params: { page, limit } })
  return data // { items: [...], page, limit }
}

export async function fetchBoardPost(postId) {
  const { data } = await api.get(`/board/${postId}`)
  return data // { ...post, comments: [...], video_signed_url, is_owner }
}

export async function createBoardPost({ analysisResultId, title, topic, tags, videoStoragePath, isPublic = true }) {
  const { data } = await api.post('/board', {
    analysis_result_id: analysisResultId,
    title,
    topic,
    tags,
    video_storage_path: videoStoragePath,
    is_public: isPublic,
  })
  return data
}

export async function deleteBoardPost(postId) {
  const { data } = await api.delete(`/board/${postId}`)
  return data
}

export async function addBoardComment(postId, content) {
  const { data } = await api.post(`/board/${postId}/comments`, { content })
  return data
}

export async function deleteBoardComment(postId, commentId) {
  const { data } = await api.delete(`/board/${postId}/comments/${commentId}`)
  return data
}

export async function fetchBoardRecommendations(postId, limit = 5) {
  const { data } = await api.get(`/board/${postId}/recommendations`, { params: { limit } })
  return data // { items: [...] }
}
