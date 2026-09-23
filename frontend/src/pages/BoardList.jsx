import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchBoardPosts, fetchMyBoardPosts } from '../api/client'
import PostCard from '../components/board/PostCard'

const PAGE_LIMIT = 20

export default function BoardList() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('all') // all | mine
  const [form, setForm] = useState({ q: '', topic: '', tag: '', sort: 'latest' })
  const [applied, setApplied] = useState(form) // "검색" 버튼을 눌렀을 때만 적용
  const [items, setItems] = useState([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(
    async (p, append) => {
      try {
        const res =
          tab === 'mine'
            ? await fetchMyBoardPosts(p, PAGE_LIMIT)
            : await fetchBoardPosts({ ...applied, page: p, limit: PAGE_LIMIT })
        setItems((prev) => (append ? [...prev, ...res.items] : res.items))
        setHasMore(res.items.length === PAGE_LIMIT)
        setError(null)
      } catch (e) {
        setError(e.response?.data?.detail ?? '게시글을 불러오지 못했습니다.')
      }
    },
    [tab, applied],
  )

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setPage(1)
    load(1, false).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [load])

  function handleSearch(e) {
    e.preventDefault()
    setApplied({ ...form, tag: form.tag.replace(/^#/, '').trim() })
  }

  async function handleMore() {
    const next = page + 1
    await load(next, true)
    setPage(next)
  }

  const inputCls =
    'rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">발표 사례 라이브러리</h1>
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/board/new')}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
            >
              글쓰기
            </button>
            <button
              onClick={() => navigate('/')}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
            >
              처음으로
            </button>
          </div>
        </div>

        <div className="mb-4 flex gap-2">
          {[['all', '전체 게시글'], ['mine', '내 게시글']].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`rounded-full px-4 py-1.5 text-sm font-semibold ${
                tab === key ? 'bg-gray-900 text-white' : 'border border-gray-300 bg-white text-gray-500'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === 'all' && (
          <form onSubmit={handleSearch} className="mb-6 grid gap-2 sm:grid-cols-[1fr_9rem_9rem_8rem_auto]">
            <input
              value={form.q}
              onChange={(e) => setForm({ ...form, q: e.target.value })}
              placeholder="제목 검색"
              className={inputCls}
            />
            <input
              value={form.topic}
              onChange={(e) => setForm({ ...form, topic: e.target.value })}
              placeholder="발표 주제"
              className={inputCls}
            />
            <input
              value={form.tag}
              onChange={(e) => setForm({ ...form, tag: e.target.value })}
              placeholder="#태그"
              className={inputCls}
            />
            <select
              value={form.sort}
              onChange={(e) => setForm({ ...form, sort: e.target.value })}
              className={inputCls}
            >
              <option value="latest">최신순</option>
              <option value="score">AI 점수순</option>
            </select>
            <button type="submit" className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">
              검색
            </button>
          </form>
        )}

        {loading ? (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 animate-pulse rounded-2xl bg-gray-200" />
            ))}
          </div>
        ) : error ? (
          <p className="py-20 text-center text-red-600">{error}</p>
        ) : items.length === 0 ? (
          <div className="py-20 text-center text-gray-400">
            <p className="mb-4 text-4xl">📭</p>
            <p>{tab === 'mine' ? '아직 올린 게시글이 없습니다.' : '조건에 맞는 게시글이 없습니다.'}</p>
          </div>
        ) : (
          <>
            <div className="space-y-3">
              {items.map((post) => (
                <PostCard key={post.id} post={post} onClick={() => navigate(`/board/${post.id}`)} />
              ))}
            </div>
            {hasMore && (
              <div className="mt-6 text-center">
                <button
                  onClick={handleMore}
                  className="rounded-lg border border-indigo-300 px-6 py-2 text-sm text-indigo-600 hover:text-indigo-800"
                >
                  더 보기
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
