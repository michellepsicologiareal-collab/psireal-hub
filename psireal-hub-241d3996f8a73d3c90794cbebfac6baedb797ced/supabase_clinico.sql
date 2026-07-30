-- ══════════════════════════════════════════════════
-- Hub Clínico — Psi Real Hub
-- Projeto: qpwjxacdjzzsyjbuuwsq
-- ══════════════════════════════════════════════════

-- Tabela de psicólogas cadastradas
create table if not exists public.psis (
  id            bigint generated always as identity primary key,
  psi_id        text not null unique,          -- código único ex: "michelle", "ana123"
  nome          text not null,
  email         text,
  status        text default 'ativo',          -- ativo | inativo
  plano         text default 'proprio',        -- proprio | basico | premium
  criado_em     timestamptz default now()
);

-- Inserir a Michelle como psi padrão
insert into public.psis (psi_id, nome, email, status, plano)
values ('michelle', 'Michelle Donegá', 'michelle@psicologiareal.com.br', 'ativo', 'proprio')
on conflict (psi_id) do nothing;

-- Tabela de respostas clínicas (todos os formulários)
create table if not exists public.respostas_clinicas (
  id                  bigint generated always as identity primary key,
  psi_id              text not null,
  paciente_nome       text not null,
  paciente_nascimento date,
  formulario          text not null,           -- YSQ-S3 | PHQ9 | GAD7 | URICA
  respostas_json      jsonb,                   -- scores por esquema/item
  score_total         numeric,
  visualizado         boolean default false,
  notas_psi           text,
  criado_em           timestamptz default now()
);

create index if not exists rc_psi_id_idx      on public.respostas_clinicas(psi_id);
create index if not exists rc_formulario_idx  on public.respostas_clinicas(formulario);
create index if not exists rc_criado_em_idx   on public.respostas_clinicas(criado_em desc);

-- RLS
alter table public.psis enable row level security;
alter table public.respostas_clinicas enable row level security;

-- Anon pode inserir respostas (paciente preenche sem login)
create policy "Anon insere resposta"
  on public.respostas_clinicas for insert to anon with check (true);

-- Anon pode ler suas próprias respostas (por psi_id — sem auth por enquanto)
create policy "Anon lê respostas"
  on public.respostas_clinicas for select to anon using (true);

-- Anon pode atualizar (visualizado, notas)
create policy "Anon atualiza resposta"
  on public.respostas_clinicas for update to anon using (true);

-- Anon pode ler psis (para validar psi_id no formulário)
create policy "Anon lê psis"
  on public.psis for select to anon using (true);
