# FinPilot — Modo Consciente

O Modo Consciente ajuda a pessoa a observar o contexto de decisões financeiras
sem culpa e sem diagnóstico. Ele não é psicoterapia e não substitui psicólogo
ou orientação financeira profissional.

## O que foi implementado

- Reflexão opcional vinculada a uma despesa.
- Emoção, intensidade, tipo de decisão, contexto e próximo passo.
- Opção “prefiro não informar”.
- Gatilhos locais para valor fora do padrão, gasto relevante, orçamento em
  risco e repetição em um dia da semana.
- Resumo semanal com padrões agregados e ação concreta.
- Check-in semanal de estresse financeiro e confiança.
- IA desligada por padrão. Quando ativada, recebe apenas emoção, categoria,
  quantidade e total agregados. Contextos, pensamentos e anotações não saem do
  banco do FinPilot e não são enviados ao provedor de IA.

## Endpoints

- `GET /api/conscious/options`
- `POST /api/conscious/reflections`
- `GET /api/conscious/reflections?mes=YYYY-MM`
- `GET /api/conscious/prompts?mes=YYYY-MM`
- `POST /api/conscious/weekly-checkins`
- `GET /api/conscious/weekly?semana=YYYY-MM-DD&usar_ia=false`

Salvar novamente uma reflexão para a mesma transação atualiza o registro em vez
de duplicá-lo.

## Componente visual sem Node.js

Página funcional para desenvolvimento:

`http://127.0.0.1:8000/static/conscious-mode.html`

Prévia visual com dados fictícios:

`app/static/conscious-mode-preview.html`

Para colocar o módulo no frontend definitivo:

```html
<aside data-finpilot-sidebar>
  <!-- navegação existente -->
</aside>

<section data-finpilot-conscious></section>
<script src="/static/conscious-mode.js"></script>
```

O componente respeita o modo claro/escuro do aparelho, funciona em celular e
notebook e usa contraste alto.

## Privacidade

As reflexões recebem `user_id` e são separadas por políticas RLS do Supabase.
O produto também exibe uma política de privacidade. Antes da venda pública,
conclua o consentimento específico e a exclusão/exportação das reflexões.
