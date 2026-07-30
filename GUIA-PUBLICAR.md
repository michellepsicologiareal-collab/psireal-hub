# Publicar esta versão do FinPilot

Este pacote corrige o erro `FUNCTION_INVOCATION_FAILED` causado pelo SQLite na
Vercel e adiciona cadastro/login pelo Supabase.

## No GitHub

1. Extraia o arquivo ZIP no computador.
2. Abra o repositório `finpilot` no GitHub.
3. Envie **os arquivos e as pastas que estão dentro da pasta extraída** para a
   raiz do repositório.
4. Substitua os arquivos antigos e confirme o commit.

Não envie o ZIP fechado e não envie arquivos `.env`, senhas ou chaves.

## Na Vercel

O Vercel fará um novo deployment automaticamente depois do commit. Não
configure Build Command nem Output Directory.

A integração Supabase precisa disponibilizar em Production:

- `POSTGRES_URL`;
- `SUPABASE_URL`;
- pelo menos uma chave pública:
  `SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` ou
  `SUPABASE_ANON_KEY`.

Os valores são secretos e devem permanecer no painel da Vercel.

## Primeiro acesso

1. Abra o endereço do FinPilot.
2. Escolha **Criar conta**.
3. Cadastre nome, e-mail e senha.
4. Se receber um e-mail do Supabase, confirme a conta.
5. Volte ao FinPilot e entre.

Se o deployment falhar, abra **Vercel → Deployments → o deployment mais
recente → Logs**. Copie somente a primeira mensagem de erro, sem copiar
variáveis, senhas ou chaves.
