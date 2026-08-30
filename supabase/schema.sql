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
alter table public.users enable row level security;
alter table public.analysis_results enable row level security;
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

-- ============================================================
-- [신규 추가] 발표 영상 공유 게시판 기능 (기능_추가_제안서.hwp 기능 1)
-- 위 내용은 기존 schema.sql 그대로이고, 아래부터가 새로 추가된 부분입니다.
-- 전부 if not exists 패턴이라 이미 실행된 schema.sql 뒤에 이어 붙여도 안전합니다.
-- ============================================================

-- [신규 추가] 발표 영상 공유 게시판 기능용 테이블
-- 기존 supabase/schema.sql 뒤에 이어서 실행한다.

create table if not exists public.board_posts (
  id text primary key,
  user_id text not null references public.users(id) on delete cascade,
  analysis_result_id uuid references public.analysis_results(id) on delete set null,
  title varchar not null,
  topic varchar not null,
  tags text[] not null default '{}',
  video_url text not null,      -- Supabase Storage 경로 (DB에는 경로만 저장 - 리스크 대응)
  snapshot jsonb not null,      -- board_schema.build_board_snapshot() 결과 (스키마 v0.1 조각)
  created_at timestamptz not null default now()
);

create index if not exists board_posts_topic_idx on public.board_posts (topic);
create index if not exists board_posts_tags_idx on public.board_posts using gin (tags);
create index if not exists board_posts_created_at_idx on public.board_posts (created_at desc);

create table if not exists public.board_comments (
  id text primary key,
  post_id text not null references public.board_posts(id) on delete cascade,
  user_id text not null references public.users(id) on delete cascade,
  content text not null,
  created_at timestamptz not null default now()
);

create index if not exists board_comments_post_id_idx on public.board_comments (post_id);

alter table public.board_posts enable row level security;
alter table public.board_comments enable row level security;

-- 게시글: 전체 공개 조회, 본인만 등록/삭제 (기존 users 정책 패턴과 동일)
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'board_posts' and policyname = 'board_posts_select_all'
  ) then
    create policy "board_posts_select_all"
      on public.board_posts for select
      using (true);
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'board_posts' and policyname = 'board_posts_insert_own'
  ) then
    create policy "board_posts_insert_own"
      on public.board_posts for insert
      with check (user_id = (select auth.uid()::text));
  end if;
end $$;

-- 댓글: 전체 공개 조회, 본인만 등록
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'board_comments' and policyname = 'board_comments_select_all'
  ) then
    create policy "board_comments_select_all"
      on public.board_comments for select
      using (true);
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'board_comments' and policyname = 'board_comments_insert_own'
  ) then
    create policy "board_comments_insert_own"
      on public.board_comments for insert
      with check (user_id = (select auth.uid()::text));
  end if;
end $$;
