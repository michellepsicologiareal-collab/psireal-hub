-- Psi Real secure product v2
-- Run after enabling pgcrypto and Supabase Auth.

create extension if not exists pgcrypto;

-- Canonical table for paid psychologists.
create table if not exists public.psis (
  user_id uuid primary key references auth.users(id) on delete cascade,
  psi_id text unique not null,
  nome text not null,
  email text unique not null,
  whatsapp text,
  plano text not null default 'mensal',
  ativa boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.admin_users (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);

-- One unguessable link per patient/instrument request.
create table if not exists public.patient_links (
  id uuid primary key default gen_random_uuid(),
  token uuid unique not null default gen_random_uuid(),
  psi_user_id uuid not null references public.psis(user_id) on delete cascade,
  patient_name text not null,
  patient_birth date,
  instrumento text not null,
  status text not null default 'ativo' check (status in ('ativo','respondido','revogado','expirado')),
  expires_at timestamptz,
  created_at timestamptz not null default now()
);

-- Harden existing responses table while preserving old columns for migration.
alter table if exists public.respostas_clinicas
  add column if not exists psi_user_id uuid references public.psis(user_id) on delete cascade,
  add column if not exists patient_link_id uuid references public.patient_links(id) on delete set null,
  add column if not exists instrumento text,
  add column if not exists respostas jsonb,
  add column if not exists scores jsonb,
  add column if not exists status text not null default 'novo',
  add column if not exists created_at timestamptz not null default now();

create index if not exists respostas_clinicas_psi_user_id_idx on public.respostas_clinicas (psi_user_id);
create index if not exists respostas_clinicas_created_at_idx on public.respostas_clinicas (created_at desc);
create index if not exists patient_links_psi_user_id_idx on public.patient_links (psi_user_id);
create index if not exists patient_links_token_idx on public.patient_links (token);

alter table public.psis enable row level security;
alter table public.admin_users enable row level security;
alter table public.patient_links enable row level security;
alter table public.respostas_clinicas enable row level security;

revoke all on public.psis from anon;
revoke all on public.admin_users from anon;
revoke all on public.patient_links from anon;
revoke all on public.respostas_clinicas from anon;
grant select on public.psis to authenticated;
grant select on public.admin_users to authenticated;
grant select, insert, update on public.patient_links to authenticated;
grant select, update on public.respostas_clinicas to authenticated;

drop policy if exists "psis_select_own" on public.psis;
create policy "psis_select_own"
on public.psis for select
to authenticated
using (user_id = auth.uid());

drop policy if exists "admin_users_select_self" on public.admin_users;
create policy "admin_users_select_self"
on public.admin_users for select
to authenticated
using (user_id = auth.uid());

drop policy if exists "patient_links_select_own" on public.patient_links;
create policy "patient_links_select_own"
on public.patient_links for select
to authenticated
using (psi_user_id = auth.uid());

drop policy if exists "patient_links_insert_own" on public.patient_links;
create policy "patient_links_insert_own"
on public.patient_links for insert
to authenticated
with check (psi_user_id = auth.uid());

drop policy if exists "patient_links_update_own" on public.patient_links;
create policy "patient_links_update_own"
on public.patient_links for update
to authenticated
using (psi_user_id = auth.uid())
with check (psi_user_id = auth.uid());

drop policy if exists "responses_select_own" on public.respostas_clinicas;
create policy "responses_select_own"
on public.respostas_clinicas for select
to authenticated
using (psi_user_id = auth.uid());

drop policy if exists "responses_update_own" on public.respostas_clinicas;
create policy "responses_update_own"
on public.respostas_clinicas for update
to authenticated
using (psi_user_id = auth.uid())
with check (psi_user_id = auth.uid());

-- Authenticated psychologist creates a patient link and receives only the tokenized URL data.
create or replace function public.create_patient_link(
  p_patient_name text,
  p_patient_birth date,
  p_instrumento text,
  p_expires_at timestamptz default null
)
returns table(token uuid, patient_name text, instrumento text)
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.uid() is null then
    raise exception 'authentication required';
  end if;

  if not exists (
    select 1 from public.psis
    where user_id = auth.uid() and ativa = true
  ) then
    raise exception 'inactive psychologist';
  end if;

  return query
  insert into public.patient_links (psi_user_id, patient_name, patient_birth, instrumento, expires_at)
  values (auth.uid(), trim(p_patient_name), p_patient_birth, p_instrumento, p_expires_at)
  returning patient_links.token, patient_links.patient_name, patient_links.instrumento;
end;
$$;

revoke all on function public.create_patient_link(text, date, text, timestamptz) from public;
grant execute on function public.create_patient_link(text, date, text, timestamptz) to authenticated;

-- Public patient submission. The token maps the response to the correct psychologist.
create or replace function public.submit_patient_response(
  p_token uuid,
  p_patient_name text,
  p_patient_birth date,
  p_instrumento text,
  p_respostas jsonb,
  p_scores jsonb,
  p_score_total numeric
)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_link public.patient_links%rowtype;
begin
  select *
  into v_link
  from public.patient_links
  where token = p_token
    and status = 'ativo'
    and (expires_at is null or expires_at > now())
  limit 1;

  if v_link.id is null then
    raise exception 'invalid or expired link';
  end if;

  if v_link.instrumento <> p_instrumento then
    raise exception 'instrument mismatch';
  end if;

  insert into public.respostas_clinicas (
    psi_user_id,
    patient_link_id,
    paciente_nome,
    paciente_nascimento,
    instrumento,
    respostas,
    scores,
    score_total,
    status,
    created_at
  ) values (
    v_link.psi_user_id,
    v_link.id,
    coalesce(nullif(trim(p_patient_name), ''), v_link.patient_name),
    coalesce(p_patient_birth, v_link.patient_birth),
    p_instrumento,
    p_respostas,
    p_scores,
    p_score_total,
    'novo',
    now()
  );

  update public.patient_links
  set status = 'respondido'
  where id = v_link.id;
end;
$$;

revoke all on function public.submit_patient_response(uuid, text, date, text, jsonb, jsonb, numeric) from public;
grant execute on function public.submit_patient_response(uuid, text, date, text, jsonb, jsonb, numeric) to anon, authenticated;

-- Optional migration helper from legacy uppercase table if it exists.
-- You still need to create matching auth.users manually before filling user_id.
-- select * from "PSIS";
