import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import CoachingResult from '../analysis/CoachingResult'
import VoiceTab from './VoiceTab'
import RoleModelTab from './RoleModelTab'
import PlaceholderTab from './PlaceholderTab'
import VisualTab from './VisualTab'
import ValidityBanner from './ValidityBanner'

// 결과 화면 탭 컨테이너.
//
// 기존 CoachingResult는 그대로 "점수" 탭으로 쓴다. 담당자가 여럿 손대는 파일이라
// 통째로 옮기면 충돌이 커진다. 새 탭은 각자 이 폴더에 파일을 추가하고 아래 TABS에
// 한 줄 등록하면 된다.
//
// 데이터는 details(공유 스키마 JSON)를 본다. 평면 컬럼은 CoachingResult가 쓰는 동안만 유지한다.

const TABS = [
  { key: 'score', label: '점수' },
  { key: 'timeline', label: '타임라인·습관' },
  { key: 'visual', label: '히트맵·표정' },
  { key: 'voice', label: '음성' },
  { key: 'rolemodel', label: '성장·롤모델' },
]

export default function ResultTabs({ result, resultId }) {
  const [active, setActive] = useState('score')
  const navigate = useNavigate()

  // 업로드 직후에는 job 응답(평면 필드 + details)이고,
  // 히스토리에서 열면 DB 행(평면 컬럼 + details)이다. 둘 다 details를 갖는다.
  const details = result?.details ?? null
  const validity = details?.x_validity ?? null
  // 발표 영상이 아니면 점수를 보여주지 않는다. 사용자가 그 숫자를 자기 점수로 읽는다.
  const scorable = validity ? validity.scorable !== false : true

  function renderBody() {
    switch (active) {
      case 'score':
        if (!scorable) {
          return (
            <div className="rounded-xl border border-slate-200 bg-white p-8 text-center">
              <p className="font-medium text-slate-700">점수를 매기지 않았습니다.</p>
              <p className="mt-1 text-sm text-slate-500">
                발표자 얼굴도 말소리도 찾지 못해서, 어떤 항목도 측정하지 못했습니다.
              </p>
            </div>
          )
        }
        return <CoachingResult result={result} resultId={resultId} embedded />
      case 'voice':
        return <VoiceTab details={details} />
      case 'rolemodel':
        return <RoleModelTab details={details} />
      case 'timeline':
        return (
          <PlaceholderTab
            title="타임라인·습관"
            owner="김민서"
            available={[
              details?.video_timeline?.length
                ? `자세·제스처 시간축 ${details.video_timeline.length}구간`
                : null,
              details?.habits?.posture ? '자세 습관 탐지 결과' : null,
              details?.habits?.gesture ? '제스처 습관 탐지 결과' : null,
              details?.habits?.filler ? '군말 습관 탐지 결과' : null,
              details?.habits?.monotone ? '단조로움 습관 탐지 결과' : null,
            ].filter(Boolean)}
          />
        )
      case 'visual':
        return <VisualTab details={details} />
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8 text-left">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-indigo-600">PresentationCoach</p>
            <h1 className="mt-1 text-3xl font-bold text-slate-950">분석 결과</h1>
          </div>
          <div className="no-print flex gap-2">
            <button
              onClick={() => window.print()}
              className="rounded-lg border border-indigo-300 px-4 py-2 text-sm font-semibold text-indigo-700 transition-colors hover:bg-indigo-50"
            >
              인쇄 / PDF 저장
            </button>
            <button
              onClick={() => navigate('/')}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-white"
            >
              처음으로
            </button>
          </div>
        </div>

        {/* 탭 바. 인쇄할 때는 숨기고 전체를 펼쳐 보여주는 게 맞지만, 그건 PDF 개편 때 같이 한다. */}
        <div className="no-print mt-6 flex gap-1 overflow-x-auto border-b border-slate-200">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActive(tab.key)}
              className={`shrink-0 border-b-2 px-4 py-2.5 text-sm font-semibold transition-colors ${
                active === tab.key
                  ? 'border-indigo-600 text-indigo-700'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="mt-6 space-y-4">
          <ValidityBanner validity={validity} />
          {renderBody()}
        </div>
      </div>
    </div>
  )
}
