create extension if not exists pgcrypto;

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

create table if not exists public.analysis_results (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.users(id) on delete cascade,
  gaze_away_ratio double precision not null default 0,
  shoulder_tilt_avg double precision not null default 0,
  gesture_count integer not null default 0,
  ear_blink_ratio double precision not null default 0,
  silence_ratio double precision not null default 0,
  problem_frames jsonb not null default '[]'::jsonb,
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
  add column if not exists problem_frames jsonb not null default '[]'::jsonb,
  add column if not exists score_gaze integer,
  add column if not exists score_pose integer,
  add column if not exists score_gesture integer,
  add column if not exists score_time integer,
  add column if not exists score_total integer,
  add column if not exists elapsed_sec double precision,
  add column if not exists goal_sec double precision;

update public.analysis_results
set problem_frames = '[]'::jsonb
where problem_frames is null;

alter table public.analysis_results
  alter column problem_frames set default '[]'::jsonb,
  alter column problem_frames set not null;

-- 2학기 스키마 v0.1: 분석 결과 JSON 전체 저장 (구조는 docs/schema/ 참고, 기존 평면 컬럼은 호환용 유지)
alter table public.analysis_results
  add column if not exists details jsonb;

create index if not exists analysis_results_user_created_at_idx
  on public.analysis_results (user_id, created_at desc);

alter table public.analysis_results
  drop constraint if exists analysis_results_user_id_fkey;

alter table public.analysis_results
  add constraint analysis_results_user_id_fkey
  foreign key (user_id) references public.users(id) on delete cascade;

create table if not exists public.sessions (
  session_id text primary key,
  user_id text not null references public.users(id) on delete cascade,
  title varchar,
  slide_log jsonb,
  target_time integer,
  created_at timestamptz not null default now()
);

alter table public.sessions
  add column if not exists title varchar,
  add column if not exists slide_log jsonb,
  add column if not exists target_time integer;

alter table public.sessions
  drop constraint if exists sessions_user_id_fkey;

alter table public.sessions
  add constraint sessions_user_id_fkey
  foreign key (user_id) references public.users(id) on delete cascade;

create table if not exists public.reports (
  report_id text primary key,
  session_id text references public.sessions(session_id) on delete cascade,
  report_url text not null,
  created_at timestamptz not null default now()
);

alter table public.reports
  add column if not exists session_id text references public.sessions(session_id) on delete cascade,
  add column if not exists report_url text,
  add column if not exists created_at timestamptz not null default now();

alter table public.reports
  drop constraint if exists reports_session_id_fkey;

alter table public.reports
  add constraint reports_session_id_fkey
  foreign key (session_id) references public.sessions(session_id) on delete cascade;

-- 롤모델 벤치마킹: 명연사 발표 1편 = 레코드 1개.
-- 사용자 세션의 audio.summary와 비교해 코칭 근거로 쓴다.
create table if not exists public.reference_speakers (
  id text primary key,
  name text not null,
  affiliation text,
  source text,
  source_url text,
  title text,
  duration_sec double precision,
  usable_sec double precision,     -- 연사가 화면에 크게 잡힌 구간의 합 (영상 지표 신뢰도 판단용)
  audio_summary jsonb,
  video_summary jsonb,             -- 표정·시선 등. 담당자 구현 전까지 null
  created_at timestamptz not null default now()
);

create index if not exists reference_speakers_name_idx on public.reference_speakers (name);

alter table public.users enable row level security;
alter table public.analysis_results enable row level security;
alter table public.reference_speakers enable row level security;
alter table public.sessions enable row level security;
alter table public.reports enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'users' and policyname = 'users_select_own'
  ) then
    create policy "users_select_own"
      on public.users for select
      using (id = (select auth.uid()::text));
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'users' and policyname = 'users_update_own'
  ) then
    create policy "users_update_own"
      on public.users for update
      using (id = (select auth.uid()::text));
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'analysis_results' and policyname = 'analysis_results_select_own'
  ) then
    create policy "analysis_results_select_own"
      on public.analysis_results for select
      using (user_id = (select auth.uid()::text));
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'analysis_results' and policyname = 'analysis_results_insert_own'
  ) then
    create policy "analysis_results_insert_own"
      on public.analysis_results for insert
      with check (user_id = (select auth.uid()::text));
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'analysis_results' and policyname = 'analysis_results_delete_own'
  ) then
    create policy "analysis_results_delete_own"
      on public.analysis_results for delete
      using (user_id = (select auth.uid()::text));
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'sessions' and policyname = 'sessions_select_own'
  ) then
    create policy "sessions_select_own"
      on public.sessions for select
      using (user_id = (select auth.uid()::text));
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'sessions' and policyname = 'sessions_insert_own'
  ) then
    create policy "sessions_insert_own"
      on public.sessions for insert
      with check (user_id = (select auth.uid()::text));
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'sessions' and policyname = 'sessions_delete_own'
  ) then
    create policy "sessions_delete_own"
      on public.sessions for delete
      using (user_id = (select auth.uid()::text));
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'reference_speakers' and policyname = 'reference_speakers_read_all'
  ) then
    -- 롤모델은 개인 데이터가 아니라 모든 사용자가 읽는다. 쓰기는 서버(service_role)만.
    create policy "reference_speakers_read_all"
      on public.reference_speakers for select
      using (true);
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'reports' and policyname = 'reports_select_own'
  ) then
    create policy "reports_select_own"
      on public.reports for select
      using (
        session_id in (
          select session_id from public.sessions
          where user_id = (select auth.uid()::text)
        )
      );
  end if;
end $$;
