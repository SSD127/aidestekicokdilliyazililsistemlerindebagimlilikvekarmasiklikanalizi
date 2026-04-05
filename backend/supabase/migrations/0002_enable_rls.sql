-- PolyMetric row level security policies
-- Principle: user can only read/write own projects.
-- Child tables are protected via project ownership checks.

create or replace function public.is_project_owner(p_project_id uuid)
returns boolean
language sql
stable
as $$
    select exists (
        select 1
        from public.projects p
        where p.id = p_project_id
          and p.owner_id = auth.uid()
    );
$$;

alter table public.projects enable row level security;
alter table public.analysis_runs enable row level security;
alter table public.files enable row level security;
alter table public.function_metrics enable row level security;
alter table public.dependencies enable row level security;
alter table public.hotspots enable row level security;
alter table public.run_metadata enable row level security;

-- PROJECTS
drop policy if exists "projects_select_own" on public.projects;
create policy "projects_select_own"
on public.projects
for select
to authenticated
using (owner_id = auth.uid());

drop policy if exists "projects_insert_own" on public.projects;
create policy "projects_insert_own"
on public.projects
for insert
to authenticated
with check (owner_id = auth.uid());

drop policy if exists "projects_update_own" on public.projects;
create policy "projects_update_own"
on public.projects
for update
to authenticated
using (owner_id = auth.uid())
with check (owner_id = auth.uid());

drop policy if exists "projects_delete_own" on public.projects;
create policy "projects_delete_own"
on public.projects
for delete
to authenticated
using (owner_id = auth.uid());

-- ANALYSIS RUNS
drop policy if exists "runs_select_own_project" on public.analysis_runs;
create policy "runs_select_own_project"
on public.analysis_runs
for select
to authenticated
using (public.is_project_owner(project_id));

drop policy if exists "runs_insert_own_project" on public.analysis_runs;
create policy "runs_insert_own_project"
on public.analysis_runs
for insert
to authenticated
with check (
    public.is_project_owner(project_id)
    and status = 'pending'
);

-- updates/deletes are service-only to prevent users from editing run outputs
drop policy if exists "runs_update_service_only" on public.analysis_runs;
create policy "runs_update_service_only"
on public.analysis_runs
for update
to authenticated
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists "runs_delete_service_only" on public.analysis_runs;
create policy "runs_delete_service_only"
on public.analysis_runs
for delete
to authenticated
using (auth.role() = 'service_role');

-- FILES
drop policy if exists "files_select_own_project" on public.files;
create policy "files_select_own_project"
on public.files
for select
to authenticated
using (
    exists (
        select 1
        from public.analysis_runs r
        where r.id = files.run_id
          and public.is_project_owner(r.project_id)
    )
);

drop policy if exists "files_write_service_only" on public.files;
create policy "files_write_service_only"
on public.files
for all
to authenticated
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

-- FUNCTION METRICS
drop policy if exists "function_metrics_select_own_project" on public.function_metrics;
create policy "function_metrics_select_own_project"
on public.function_metrics
for select
to authenticated
using (
    exists (
        select 1
        from public.analysis_runs r
        where r.id = function_metrics.run_id
          and public.is_project_owner(r.project_id)
    )
);

drop policy if exists "function_metrics_write_service_only" on public.function_metrics;
create policy "function_metrics_write_service_only"
on public.function_metrics
for all
to authenticated
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

-- DEPENDENCIES
drop policy if exists "dependencies_select_own_project" on public.dependencies;
create policy "dependencies_select_own_project"
on public.dependencies
for select
to authenticated
using (
    exists (
        select 1
        from public.analysis_runs r
        where r.id = dependencies.run_id
          and public.is_project_owner(r.project_id)
    )
);

drop policy if exists "dependencies_write_service_only" on public.dependencies;
create policy "dependencies_write_service_only"
on public.dependencies
for all
to authenticated
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

-- HOTSPOTS
drop policy if exists "hotspots_select_own_project" on public.hotspots;
create policy "hotspots_select_own_project"
on public.hotspots
for select
to authenticated
using (
    exists (
        select 1
        from public.analysis_runs r
        where r.id = hotspots.run_id
          and public.is_project_owner(r.project_id)
    )
);

drop policy if exists "hotspots_write_service_only" on public.hotspots;
create policy "hotspots_write_service_only"
on public.hotspots
for all
to authenticated
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

-- RUN METADATA
drop policy if exists "run_metadata_select_own_project" on public.run_metadata;
create policy "run_metadata_select_own_project"
on public.run_metadata
for select
to authenticated
using (
    exists (
        select 1
        from public.analysis_runs r
        where r.id = run_metadata.run_id
          and public.is_project_owner(r.project_id)
    )
);

drop policy if exists "run_metadata_write_service_only" on public.run_metadata;
create policy "run_metadata_write_service_only"
on public.run_metadata
for all
to authenticated
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');
