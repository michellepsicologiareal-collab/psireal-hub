-- Permite que administradoras vejam e gerenciem a lista de psicologas assinantes.
-- Rode depois da migration principal.

grant select, update on public.psis to authenticated;

drop policy if exists "admin_select_all_psis" on public.psis;
create policy "admin_select_all_psis"
on public.psis
for select
to authenticated
using (
  exists (
    select 1
    from public.admin_users
    where admin_users.user_id = auth.uid()
  )
);

drop policy if exists "admin_update_all_psis" on public.psis;
create policy "admin_update_all_psis"
on public.psis
for update
to authenticated
using (
  exists (
    select 1
    from public.admin_users
    where admin_users.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.admin_users
    where admin_users.user_id = auth.uid()
  )
);
