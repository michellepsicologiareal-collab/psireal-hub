-- ══════════════════════════════════════════════════
-- Tabela: contatos
-- Projeto: Psicologia Real / psimichelledonega
-- Supabase: qpwjxacdjzzsyjbuuwsq
-- ══════════════════════════════════════════════════

create table if not exists public.contatos (
  id            bigint generated always as identity primary key,
  nome          text not null,
  whatsapp      text not null,
  servico       text not null,
  mensagem      text,
  pagina        text,
  status        text default 'novo',
  notas         text,
  criado_em     timestamptz default now(),
  atualizado_em timestamptz default now()
);

create index if not exists contatos_status_idx    on public.contatos(status);
create index if not exists contatos_criado_em_idx on public.contatos(criado_em desc);

alter table public.contatos enable row level security;

create policy "Anon pode inserir contato"
  on public.contatos for insert to anon with check (true);

create policy "Autenticado pode ler contatos"
  on public.contatos for select to authenticated using (true);

create policy "Autenticado pode atualizar contatos"
  on public.contatos for update to authenticated using (true);

create or replace function public.set_atualizado_em()
returns trigger language plpgsql as $$
begin new.atualizado_em = now(); return new; end;
$$;

create trigger contatos_atualizado_em
  before update on public.contatos
  for each row execute procedure public.set_atualizado_em();
