# Psi Real - versao vendavel e segura

## Decisao principal

`psi_id` nao pode continuar funcionando como senha se a promessa for seguranca real.

A arquitetura segura passa a ser:

1. A psi entra com **email + senha** via Supabase Auth.
2. O banco associa a psi a `auth.uid()`.
3. O painel so consulta respostas cuja `psi_user_id = auth.uid()`.
4. O link enviado ao paciente usa um **token aleatorio** gerado em `patient_links`.
5. O paciente envia o teste por uma RPC publica que valida o token e grava a resposta na psi correta.
6. O cadastro de novas psis passa por uma Edge Function protegida, nao por senha escondida em HTML.

## Fluxo vendavel

```text
Kiwify
  -> admin autenticada chama create-psi-user
  -> funcao cria a conta Auth e o registro em public.psis
  -> psi faz login no painel
  -> painel chama create_patient_link(...)
  -> link gerado: formulario-esquemas.html?token=<uuid>
  -> paciente preenche
  -> formulario chama submit_patient_response(...)
  -> banco grava com psi_user_id correto
  -> psi ve apenas as proprias respostas por RLS
```

## O que muda em relacao ao sistema antigo

| Antes | Depois |
|---|---|
| `psi_id` como senha | Supabase Auth |
| filtro de seguranca no frontend | RLS no banco |
| link do paciente expoe `psi_id` | link usa token UUID |
| `anon` podia selecionar respostas | so a psi autenticada ve as proprias |
| admin no JS | cadastro seguro por Edge Function |

## Arquivos adicionados

- `supabase_secure_product.sql`
- `supabase/functions/create-psi-user/index.ts`

## O que precisa ser feito no Supabase antes de vender

1. Rodar `supabase_secure_product.sql`.
2. Criar sua propria conta Auth de administradora.
3. Inserir seu `user_id` em `public.admin_users`.
4. Publicar a Edge Function `create-psi-user`.
5. Usar essa funcao para cadastrar novas psis.
6. Migrar dados legados de `"PSIS"`/`respostas_clinicas`, se quiser preservar o historico antigo.
7. Testar ponta a ponta com duas psis diferentes para comprovar o isolamento.

## Formularios comerciais que alimentam o painel admin

Ja enviam para `contatos`:

- `index.html`
- `terapia.html`
- `supervisao.html`
- `corporativo.html`
- `ansiedade.html`
- `inventarios.html`

## Teste minimo de seguranca antes da venda

1. Criar `psi_a` e `psi_b` no Supabase Auth.
2. Cada uma gera um link para pacientes distintos.
3. Preencher os dois links.
4. Logar como `psi_a` e confirmar que so ve respostas de `psi_a`.
5. Logar como `psi_b` e confirmar que so ve respostas de `psi_b`.
6. Tentar consultar resposta da outra psi via DevTools e confirmar bloqueio por RLS.
