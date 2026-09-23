// 게시글 목록/추천 목록에서 함께 쓰는 카드 (BoardList, BoardDetail에서 사용)
export function ScoreBadge({ score }) {
    if (score == null) return null
    const cls =
      score >= 70 ? 'bg-green-100 text-green-700' :
      score >= 50 ? 'bg-yellow-100 text-yellow-700' :
                    'bg-red-100 text-red-700'
    return <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${cls}`}>AI {score}점</span>
  }
  
  export default function PostCard({ post, onClick }) {
    return (
      <button
        onClick={onClick}
        className="w-full rounded-2xl border border-gray-200 bg-white px-5 py-4 text-left transition-all hover:border-indigo-300 hover:shadow-sm"
      >
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-semibold text-gray-900">{post.title}</h3>
          <ScoreBadge score={post.score_total} />
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
          <span className="rounded bg-indigo-50 px-2 py-0.5 font-medium text-indigo-600">{post.topic}</span>
          {post.tags?.map((t) => (
            <span key={t} className="rounded bg-gray-100 px-2 py-0.5 text-gray-500">#{t}</span>
          ))}
          {post.is_public === false && (
            <span className="rounded bg-gray-800 px-2 py-0.5 text-white">비공개</span>
          )}
        </div>
        <p className="mt-2 text-xs text-gray-400">
          {post.author_name || '익명'} · {new Date(post.created_at).toLocaleDateString('ko-KR')}
        </p>
      </button>
    )
  }
  
