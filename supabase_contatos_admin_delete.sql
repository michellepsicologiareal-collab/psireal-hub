grant delete on public.contatos to authenticated;

drop policy if exists "admin_delete_contatos" on public.contatos;
create policy "admin_delete_contatos"
on public.contatos
for delete
to authenticated
using (
  exists (
    select 1
    from public.admin_users
    where admin_users.user_id = auth.uid()
  )
);
