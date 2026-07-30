# Vercel + Supabase

O FinPilot usa SQLite no desenvolvimento local e PostgreSQL/Supabase na
Vercel. A seleção é automática:

- com `POSTGRES_URL`: PostgreSQL;
- sem `POSTGRES_URL`: SQLite em `FINPILOT_DB_PATH` ou `finpilot.db`.

## Integração

Instale o Supabase pelo Marketplace da Vercel e conecte o recurso ao projeto
`finpilot` nos ambientes Production e Preview, sem prefixo personalizado. A
integração cria `POSTGRES_URL` e as demais variáveis automaticamente.

Não copie a URL do banco para o código, `.env.example`, documentação, issue ou
commit. O arquivo `.env` está ignorado pelo Git.

## Publicação

A Vercel reconhece `app/app.py` como entrada FastAPI e respeita
`.python-version`. Depois de atualizar a branch principal no GitHub, a Vercel
faz um novo deployment automaticamente.

Na primeira inicialização, o backend cria as tabelas e índices idempotentes no
PostgreSQL. O endereço `/api/health` confirma que a API iniciou, e `/docs`
expõe a documentação interativa.

## Cadastro e segurança

A integração deve disponibilizar `SUPABASE_URL` e uma das chaves públicas
`SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` ou
`SUPABASE_ANON_KEY`. Não copie chaves para o GitHub.

O cadastro e o login usam Supabase Auth. O backend grava os tokens somente em
cookies `HttpOnly` e troca a conexão PostgreSQL para o papel `authenticated` em
cada requisição. Todas as tabelas financeiras possuem uma política RLS
`user_id = auth.uid()`, impedindo que uma conta consulte ou altere dados de
outra.

Antes da venda pública ainda devem ser concluídos recuperação de senha, canal
de privacidade/exclusão de conta e testes independentes de segurança.
