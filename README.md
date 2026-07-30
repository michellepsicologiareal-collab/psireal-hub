# FinPilot — Backend

Painel de gestão financeira pessoal focado em controle de custos. O backend
FastAPI usa SQLite localmente e PostgreSQL/Supabase na Vercel. Inclui um motor
de insights determinístico e enriquecimento opcional dos conselhos pela API
Anthropic.

## Stack

- **FastAPI** + **Uvicorn** (servidor ASGI)
- **PostgreSQL/Supabase** na Vercel e **SQLite** no desenvolvimento local
- **Pydantic** para validação de request/response
- **Anthropic SDK** para reescrita opcional dos conselhos
- **pytest** para testes automatizados

Todo valor monetário é armazenado no banco como `INTEGER` em **centavos**
(nunca `float`). A conversão para reais acontece somente na serialização da
API (respostas JSON).

## Pré-requisitos

- Windows com `cmd`
- Python 3.13 instalado em:
  `C:\Users\midon\AppData\Local\Programs\Python\Python313\python.exe`
  (o comando `python` **não** está no PATH deste ambiente — use sempre o
  caminho completo, ou o `python.exe` de dentro do `.venv` depois de criado)
- **Node.js não é necessário** — este projeto não usa nenhuma ferramenta de
  frontend/bundler.

## Passo a passo de setup (Windows / cmd)

Abra o `cmd` na raiz do projeto (`C:\Users\midon\Documents\projects\finpilot`)
e rode, na ordem:

### 1. Criar o ambiente virtual

```bat
C:\Users\midon\AppData\Local\Programs\Python\Python313\python.exe -m venv .venv
```

### 2. Instalar as dependências

```bat
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. (Opcional) Configurar variáveis de ambiente

Copie `.env.example` para `.env` e ajuste se necessário. Sem
`ANTHROPIC_API_KEY`, o motor continua funcionando com conselhos locais. A chave
fica somente no servidor e nunca é retornada ao frontend.

```bat
copy .env.example .env
```

### 4. Popular o banco com dados de exemplo (seed)

Gera ~6 meses de transações realistas em BRL (salário, aluguel, mercado,
transporte, assinaturas, etc.), categorias e orçamentos padrão. O script é
determinístico (mesma saída sempre) e idempotente (pode rodar de novo sem
duplicar dados).

```bat
.venv\Scripts\python.exe scripts\seed.py
```

Saída esperada:

```
Seed concluído: 160 transações geradas, 14 categorias, 11 orçamentos padrão.
```

### 5. Rodar os testes

```bat
.venv\Scripts\python.exe -m pytest -q
```

Saída esperada: todos os testes passando (atualmente `78 passed`).

### 6. Subir o servidor

```bat
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Localmente, o banco `finpilot.db` é criado/migrado automaticamente. Na Vercel,
o mesmo processo cria as tabelas no PostgreSQL do Supabase indicado por
`POSTGRES_URL`.

Com o servidor rodando, acesse:

- Documentação interativa (Swagger UI): `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/health`

Para parar o servidor, use `Ctrl+C` no terminal.

## Estrutura do projeto

```
app/
  main.py            # criação do FastAPI, CORS, inclusão dos routers
  db.py              # SQLite local + PostgreSQL/Supabase na Vercel
  models.py          # schemas Pydantic (request/response)
  routers/           # um router por recurso (categories, transactions, ...)
  services/          # regras de negócio (analytics, budgets, recurring, csv_import, dates)
scripts/
  seed.py            # popula o banco com dados de exemplo determinísticos
tests/
  test_*.py          # testes pytest (aritmética, filtros, summary, budgets, recurring, csv import)
```

## Endpoints principais

Todos os endpoints começam com `/api`. Alguns exemplos:

- `GET /api/health`
- `GET/POST /api/categories`, `PATCH/DELETE /api/categories/{id}`
- `GET/POST /api/transactions` (filtros: `mes`, `de`, `ate`, `category_id`, `tipo`, `busca`, `ordem`, `limit`, `offset`), `PATCH/DELETE /api/transactions/{id}`
- `GET/POST /api/budgets`, `PATCH/DELETE /api/budgets/{id}`, `GET /api/budgets/status?mes=YYYY-MM`
- `GET/POST /api/goals`, `PATCH/DELETE /api/goals/{id}`
- `GET/POST /api/accounts`, `PATCH/DELETE /api/accounts/{id}`
- `GET/POST /api/reminders`, `PATCH/DELETE /api/reminders/{id}`
- `GET/POST /api/scheduled-expenses`, `PATCH/DELETE /api/scheduled-expenses/{id}`
- `POST /api/scheduled-expenses/{id}/pay` (transforma a previsão em gasto no Diário)
- `GET/POST /api/purchase-plans`, `PATCH/DELETE /api/purchase-plans/{id}`
- `GET /api/summary?mes=YYYY-MM`
- `GET /api/spending-by-category?mes=YYYY-MM`
- `GET /api/trend?meses=6`
- `GET /api/recurring`
- `GET /api/insights?mes=YYYY-MM&usar_ia=true`
- `POST /api/import/csv` (upload multipart de extrato CSV)
- `GET/PUT /api/settings`

A lista completa de rotas e seus schemas pode ser consultada em
`http://127.0.0.1:8000/docs` com o servidor rodando.

## Telas incluídas

- Diário com visões de dia, semana e mês, fluxos, calendário e gráfico por categoria
- Categorias e subcategorias com ícones e cores
- Calendário financeiro com lançamentos, previsões e lembretes
- Caixinhas de metas
- Planejamento: despesas previstas, compras futuras e orçamentos
- Contas e patrimônio: bancos, cartões, investimentos e importação de fatura PDF/CSV
- Lembretes financeiros
- Modo Consciente com check-in semanal, reflexões, padrões e próximos passos
- Modo claro/escuro e navegação responsiva para celular e notebook

## Insights e IA

O endpoint `GET /api/insights` detecta localmente orçamento estourado ou em
risco, aumento relevante de gastos, margem de poupança baixa e recorrências
não essenciais. Os cálculos, evidências e impactos em reais nunca dependem da
IA. Quando `usar_ia=true` e a chave está configurada, a Anthropic pode
reescrever apenas `titulo`, `descricao` e `acao`. Se a API estiver indisponível
ou retornar algo inválido, a resposta usa automaticamente o texto local.

## Modo Consciente

O Modo Consciente oferece reflexões opcionais sobre o contexto de despesas,
detecta padrões por regras locais e apresenta uma ação prática. Não realiza
diagnóstico nem substitui atendimento psicológico ou orientação financeira.

- `GET /api/conscious/options`
- `POST/GET /api/conscious/reflections`
- `GET /api/conscious/prompts?mes=YYYY-MM`
- `POST /api/conscious/weekly-checkins`
- `GET /api/conscious/weekly?semana=YYYY-MM-DD&usar_ia=false`

A IA fica desligada por padrão. Quando ativada, recebe somente padrões
agregados; contexto, pensamentos e anotações permanecem no banco do FinPilot. A
integração visual sem Node.js está em `app/static/conscious-mode.js`. Consulte
`docs/MODO_CONSCIENTE.md`.

## Publicação na Vercel com Supabase

A integração do Supabase cria `POSTGRES_URL` automaticamente na Vercel. Quando
essa variável existe, o backend usa PostgreSQL e não tenta gravar um arquivo
SQLite no ambiente serverless. O ponto de entrada da Vercel é `app/app.py`.

Consulte `docs/VERCEL_SUPABASE.md` antes de publicar. O cadastro e o login usam
Supabase Auth, com tokens em cookies `HttpOnly`. No PostgreSQL, cada tabela
financeira possui `user_id` e políticas RLS que separam os registros por conta.

## Cadastro e acesso protegido

Na Vercel, `SUPABASE_URL` e uma chave pública do Supabase são obrigatórias. Sem
essa configuração, o sistema falha fechado: telas e APIs financeiras ficam
bloqueadas. O login cria cookies `HttpOnly`, `Secure` e `SameSite=Lax`, e a
sessão pode ser renovada com segurança. Consulte `docs/USO_PESSOAL.md`.

## CORS

Liberado somente para origens locais explicitamente cadastradas. Na Vercel, a
interface usa rotas relativas na mesma origem.

## Observações sobre o importador de CSV (`POST /api/import/csv`)

- Detecta automaticamente o delimitador (`,`, `;`, tab, `|`).
- Reconhece variações comuns de nome de coluna em pt-BR (ex. `Data`,
  `Descrição`/`Histórico`, `Valor`).
- Aceita valores em formato brasileiro (`1.234,56`) ou internacional
  (`1234.56`).
- Convenção de sinal: valor negativo = despesa, positivo = receita. Se o
  arquivo inteiro não tiver nenhum valor negativo, todas as linhas são
  tratadas como despesa (caso comum de fatura de cartão de crédito).
- Faz de-duplicação por `data + descrição + valor`: reimportar o mesmo
  arquivo não duplica lançamentos.
- Retorna um resumo com quantidade importada, ignorada (duplicada) e com
  erro — incluindo o motivo de cada linha inválida.
