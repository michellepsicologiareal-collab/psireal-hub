# Cadastro e uso pessoal

O FinPilot usa contas individuais pelo Supabase Auth. A mesma estrutura serve
para uso pessoal agora e para múltiplos assinantes no futuro.

## Configuração na Vercel

A integração Supabase + Vercel deve criar automaticamente:

- `POSTGRES_URL`;
- `SUPABASE_URL`;
- `SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` ou
  `SUPABASE_ANON_KEY`.

Não copie os valores dessas variáveis para arquivos, GitHub, prints ou
conversas. Se estiverem vinculadas aos ambientes Production e Preview, basta
publicar o código.

## Como entrar

1. Abra o endereço publicado.
2. Escolha **Criar conta**.
3. Informe nome, e-mail e uma senha com pelo menos 8 caracteres, uma letra e
   um número.
4. Se o Supabase solicitar, confirme o e-mail.
5. Volte ao FinPilot e entre com o e-mail e a senha cadastrados.

## Proteção aplicada

- tokens ficam em cookies `HttpOnly`;
- cookies usam `Secure` na Vercel;
- senhas são tratadas pelo Supabase Auth, sem texto aberto no FinPilot;
- cada tabela possui `user_id`;
- políticas RLS restringem leitura e gravação ao `auth.uid()` da sessão;
- sem configuração de autenticação, a publicação na Vercel bloqueia o acesso.

Para comercialização pública, acrescente recuperação de senha, exclusão de
conta, canal de suporte/privacidade e revisão jurídica dos textos.
