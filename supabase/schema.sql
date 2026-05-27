create extension if not exists pgcrypto;

-- ── 사용자 테이블 ────────────────────────────────────────────────────────────
create table if not exists public.users (
  id text primary key,
  email text unique not null,
  hashed_password text,
  name text,
  created_at timestamptz not null default now()
);

alter table public.users
  add column if not exists hashed_password text,
  add column if not exists name text;

-- ── 분석 결과 테이블 ─────────────────────────────────────────────────────────
create table if not exists public.analysis_results (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.users(id) on delete cascade,
  gaze_away_ratio double precision not null default 0,
  shoulder_tilt_avg double precision not null default 0,
  gesture_count integer not null default 0,
  ear_blink_ratio double precision not null default 0,
  silence_ratio double precision not null default 0,
  coaching text,
  score_gaze integer,
  score_pose integer,
  score_gesture integer,
  score_time integer,
  score_total integer,
  elapsed_sec double precision,
  goal_sec double precision,
  created_at timestamptz not null default now()
);

alter table public.analysis_results
  add column if not exists ear_blink_ratio double precision not null default 0,
  add column if not exists silence_ratio double precision not null default 0,
  add column if not exists score_gaze integer,
  add column if not exists score_pose integer,
  add column if not exists score_gesture integer,
  add column if not exists score_time integer,
  add column if not exists score_total integer,
  add column if not exists elapsed_sec double precision,
  add column if not exists goal_sec double precision;

create index if not exists analysis_results_user_created_at_idx
  on public.analysis_results (user_id, created_at desc);

-- ── 발표 세션 테이블 ─────────────────────────────────────────────────────────
create table if not exists public.sessions (
  session_id text primary key,
  user_id text not null references public.users(id) on delete cascade,
  title varchar,
  slide_log jsonb,
  target_time int,
  created_at timestamptz not null default now()
);

-- ── PDF 보고서 테이블 ─────────────────────────────────────────────────────────
create table if not exists public.reports (
  report_id text primary key,
  session_id text references public.sessions(session_id) on delete cascade,
  report_url text not null,
  created_at timestamptz not null default now()
);

-- ── Row Level Security ───────────────────────────────────────────────────────
alter table public.users enable row level security;
alter table public.analysis_results enable row level security;
alter table public.sessions enable row level security;
alter table public.reports enable row level security;

-- users: 자신의 행만 조회·수정
create policy if not exists "users_select_own"
  on public.users for select
  using (id = (select auth.uid()::text));

create policy if not exists "users_update_own"
  on public.users for update
  using (id = (select auth.uid()::text));

-- analysis_results: 자신의 결과만 CRUD
create policy if not exists "analysis_results_select_own"
  on public.analysis_results for select
  using (user_id = (select auth.uid()::text));

create policy if not exists "analysis_results_insert_own"
  on public.analysis_results for insert
  with check (user_id = (select auth.uid()::text));

create policy if not exists "analysis_results_delete_own"
  on public.analysis_results for delete
  using (user_id = (select auth.uid()::text));

-- sessions: 자신의 세션만 CRUD
create policy if not exists "sessions_select_own"
  on public.sessions for select
  using (user_id = (select auth.uid()::text));

create policy if not exists "sessions_insert_own"
  on public.sessions for insert
  with check (user_id = (select auth.uid()::text));

create policy if not exists "sessions_delete_own"
  on public.sessions for delete
  using (user_id = (select auth.uid()::text));

-- reports: 자신의 세션에 연결된 보고서만 조회
create policy if not exists "reports_select_own"
  on public.reports for select
  using (
    session_id in (
      select session_id from public.sessions
      where user_id = (select auth.uid()::text)
    )
  );
