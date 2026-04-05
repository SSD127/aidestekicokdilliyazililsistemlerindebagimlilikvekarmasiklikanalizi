-- PolyMetric core relational schema
-- Target: Supabase Postgres

create extension if not exists pgcrypto;

create table if not exists public.projects (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    name text not null check (char_length(name) between 2 and 120),
    repo_url text not null,
    default_branch text not null default 'main',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (owner_id, repo_url)
);

create table if not exists public.analysis_runs (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    status text not null check (status in ('pending', 'running', 'completed', 'failed')),
    commit_hash text,
    branch_name text not null default 'main',
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.files (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references public.analysis_runs(id) on delete cascade,
    path text not null,
    language text not null,
    complexity_score numeric(10, 4),
    maintainability_index numeric(10, 4),
    dependency_count integer not null default 0 check (dependency_count >= 0),
    loc integer not null default 0 check (loc >= 0),
    created_at timestamptz not null default now(),
    unique (run_id, path)
);

create table if not exists public.function_metrics (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references public.analysis_runs(id) on delete cascade,
    file_id uuid not null references public.files(id) on delete cascade,
    function_name text not null,
    start_line integer,
    end_line integer,
    cyclomatic_complexity integer not null check (cyclomatic_complexity >= 0),
    halstead_score numeric(14, 4),
    loc integer not null default 0 check (loc >= 0),
    risk_score numeric(10, 4),
    created_at timestamptz not null default now(),
    unique (file_id, function_name, start_line)
);

create table if not exists public.dependencies (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references public.analysis_runs(id) on delete cascade,
    source_file_id uuid references public.files(id) on delete set null,
    target_file_id uuid references public.files(id) on delete set null,
    source_path text not null,
    target_path text not null,
    dependency_type text not null default 'import',
    source_symbol text,
    target_symbol text,
    created_at timestamptz not null default now()
);

create table if not exists public.hotspots (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references public.analysis_runs(id) on delete cascade,
    file_id uuid not null references public.files(id) on delete cascade,
    function_metric_id uuid references public.function_metrics(id) on delete set null,
    function_name text not null,
    risk_score numeric(10, 4) not null,
    reason text not null,
    rank smallint not null check (rank between 1 and 100),
    created_at timestamptz not null default now(),
    unique (run_id, rank)
);

create table if not exists public.run_metadata (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null unique references public.analysis_runs(id) on delete cascade,
    parser_version text not null,
    grammar_version text,
    analyzer_version text,
    analyzed_at timestamptz not null default now(),
    commit_tag text,
    extra jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_projects_owner_created on public.projects (owner_id, created_at desc);

create index if not exists idx_runs_project_started on public.analysis_runs (project_id, started_at desc);
create index if not exists idx_runs_project_status on public.analysis_runs (project_id, status);
create index if not exists idx_runs_project_commit on public.analysis_runs (project_id, commit_hash);

create index if not exists idx_files_run_path on public.files (run_id, path);
create index if not exists idx_files_run_language on public.files (run_id, language);

create index if not exists idx_function_metrics_run_risk on public.function_metrics (run_id, risk_score desc);
create index if not exists idx_function_metrics_run_cc on public.function_metrics (run_id, cyclomatic_complexity desc);
create index if not exists idx_function_metrics_file on public.function_metrics (file_id);

create index if not exists idx_dependencies_run_source on public.dependencies (run_id, source_path);
create index if not exists idx_dependencies_run_target on public.dependencies (run_id, target_path);

create index if not exists idx_hotspots_run_rank on public.hotspots (run_id, rank);
create index if not exists idx_hotspots_run_score on public.hotspots (run_id, risk_score desc);

create index if not exists idx_run_metadata_run on public.run_metadata (run_id);
create index if not exists idx_run_metadata_analyzed on public.run_metadata (analyzed_at desc);

create or replace view public.project_run_trends_v as
select
    r.id as run_id,
    r.project_id,
    r.started_at,
    r.finished_at,
    count(distinct f.id) as file_count,
    count(distinct fm.id) as function_count,
    coalesce(avg(fm.cyclomatic_complexity), 0)::numeric(10, 4) as mccabe_avg,
    coalesce(max(fm.cyclomatic_complexity), 0)::numeric(10, 4) as mccabe_max,
    coalesce(sum(fm.halstead_score), 0)::numeric(14, 4) as halstead_total,
    coalesce(sum(fm.risk_score), 0)::numeric(14, 4) as risk_total
from public.analysis_runs r
left join public.files f on f.run_id = r.id
left join public.function_metrics fm on fm.run_id = r.id
group by r.id, r.project_id, r.started_at, r.finished_at;
