// 화면 전체에서 같이 쓰는 선 아이콘. 이모지(🎬 📄 🔍) 대신 사용해 톤을 통일한다.
const PATHS = {
    video: (<><rect x="3" y="6" width="12" height="12" rx="2" /><path d="M15 10.5l5-3v9l-5-3z" /></>),
    upload: (<><path d="M12 16V4" /><path d="M7 9l5-5 5 5" /><path d="M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3" /></>),
    trend: (<><path d="M3 17l6-6 4 4 8-8" /><path d="M15 7h6v6" /></>),
    library: (<><rect x="3" y="4" width="18" height="14" rx="2" /><path d="M10 9l5 3-5 3z" /><path d="M8 21h8" /></>),
    eye: (<><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" /></>),
    user: (<><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 4-6 8-6s8 2 8 6" /></>),
    hand: (<><path d="M8 13V6a1.5 1.5 0 013 0v5" /><path d="M11 11V4.5a1.5 1.5 0 013 0V11" /><path d="M14 11V6a1.5 1.5 0 013 0v8a6 6 0 01-6 6h-1a6 6 0 01-5-3l-2-4a1.5 1.5 0 012.5-1.5L8 14" /></>),
    mic: (<><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0014 0" /><path d="M12 18v3" /></>),
    check: (<path d="M5 12l5 5 9-10" />),
    clock: (<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>),
    slides: (<><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" /></>),
    chevron: (<path d="M9 6l6 6-6 6" />),
  }
  
  export default function Icon({ name, className = 'h-5 w-5', strokeWidth = 1.8 }) {
    return (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={className}
        aria-hidden="true"
      >
        {PATHS[name]}
      </svg>
    )
  }
  
