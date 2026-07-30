# Integração Pluggy (Open Finance)

## Configuração

1. Copie `.env.example` para `.env`.
2. Preencha `PLUGGY_CLIENT_ID` e `PLUGGY_CLIENT_SECRET` **somente no servidor**.
3. Reinicie o FastAPI.

As credenciais são trocadas no backend por uma API Key temporária. O navegador
recebe somente o Connect Token de 30 minutos usado pelo widget oficial.

## Fluxo dos endpoints

- `POST /api/pluggy/connect` sem `item_id`: cria um Connect Token.
- `POST /api/pluggy/connect` com `{"item_id": "..."}`: confirma e guarda a
  conexão retornada pelo `onSuccess` do widget.
- `GET /api/pluggy/accounts`: atualiza e lista as contas conectadas, com número
  mascarado e sem CPF.
- `POST /api/pluggy/sync`: importa até 365 dias por padrão. Aceita
  `{"item_id": "...", "dias": 90}`.

A sincronização é idempotente: o vínculo pelo ID da transação da Pluggy evita
duplicações e permite atualizar um lançamento já importado. Transações
`PENDING` não entram no diário. Em cartão de crédito, pagamentos/créditos da
fatura são ignorados para não virarem receita indevidamente.
Movimentos em outra moeda só entram quando a Pluggy também fornece
`amountInAccountCurrency` convertido para uma conta em BRL.

## Botão sem Node.js

O repositório atual não contém as páginas do frontend, por isso o componente
foi preparado como JavaScript vanilla em:

`/static/pluggy-connect-button.js`

Na sidebar existente, adicione o atributo e o script:

```html
<aside class="sidebar" data-finpilot-sidebar>
  <!-- navegação existente -->
</aside>

<script src="/static/pluggy-connect-button.js"></script>
```

O script cria o botão **Conectar banco**, abre o widget oficial, registra o
`item_id` no backend e sincroniza o diário após a conexão.

## Segurança

O `clientUserId` enviado à Pluggy é o UUID da conta autenticada. Conexões,
contas e transações importadas também recebem `user_id` e são protegidas pelas
políticas RLS do Supabase. As credenciais `PLUGGY_CLIENT_ID` e
`PLUGGY_CLIENT_SECRET` permanecem somente no servidor.
