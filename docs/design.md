# FinPilot — Direção Visual

Documento de direção de design do FinPilot. Serve como fonte única de verdade visual para a implementação (FastAPI + SQLite no backend, HTML/CSS/JS vanilla + Tailwind CDN + Chart.js CDN no frontend). Nenhuma decisão aqui depende de Node.js, bundler ou biblioteca de componentes React.

---

## 1. Conceito visual

FinPilot é um cockpit financeiro pessoal: escuro por padrão, denso em números mas nunca sufocante, com hierarquia clara entre "o que é seu dinheiro" e "o que a IA está te dizendo sobre ele". A estética é de ferramenta profissional de fintech/trading — sóbria, confiável, sem gamificação nem tom de rede social. Cor é usada com escassez e propósito: quase tudo é neutro em cinza-azulado escuro, e a cor só aparece para carregar significado (ganho, perda, alerta, ação). O produto deve transmitir controle e clareza, como um extrato bem organizado, não como um app de consumo casual.

---

## 2. Paleta de cores

### 2.1 Dark (padrão, tema principal)

| Token | Hex | Uso |
|---|---|---|
| `--color-bg` | `#0B0F14` | Fundo base da aplicação (body) |
| `--color-surface` | `#11161D` | Cards, sidebar, superfícies de primeiro nível |
| `--color-surface-elevated` | `#171D26` | Modais, dropdowns, popovers, linha em hover de tabela |
| `--color-border` | `#232B36` | Bordas sutis, divisores |
| `--color-border-strong` | `#2E3945` | Bordas de foco/hover, contornos de input |
| `--color-text-primary` | `#E7EBF0` | Texto principal, valores em destaque |
| `--color-text-secondary` | `#A9B4C0` | Labels, descrições, texto de suporte |
| `--color-text-muted` | `#6B7684` | Placeholders, metadados, timestamps |
| `--color-accent` | `#4C8DFF` | Cor de acento única — ações primárias, links, foco, gráficos neutros |
| `--color-accent-soft` | `#1B2B47` | Fundo suave do acento (badges, hover leve) |

**Cores semânticas**

| Token | Hex | Uso |
|---|---|---|
| `--color-positive` | `#2FD68C` | Receita, saldo positivo, variação favorável |
| `--color-positive-soft` | `#0F2E22` | Fundo suave para badges/positivo |
| `--color-negative` | `#FF5C6C` | Despesa, saldo negativo, variação desfavorável |
| `--color-negative-soft` | `#3A1418` | Fundo suave para badges/negativo |
| `--color-warning` | `#F2B94D` | Alerta (orçamento em atenção, ~80-100%) |
| `--color-warning-soft` | `#3A2A0E` | Fundo suave de alerta |
| `--color-critical` | `#FF7A45` | Crítico (orçamento estourado, dica de alta severidade) |
| `--color-critical-soft` | `#3D1F10` | Fundo suave crítico |
| `--color-info` | `#4C8DFF` | Informativo (mesma cor do acento, reforça consistência) |
| `--color-info-soft` | `#1B2B47` | Fundo suave informativo |

### 2.2 Light (variante opcional)

A variante light existe para acessibilidade/preferência do usuário, mantendo a mesma lógica cromática (acento e semânticas idênticos, invertendo neutros).

| Token | Hex | Uso |
|---|---|---|
| `--color-bg` (light) | `#F5F7FA` | Fundo base |
| `--color-surface` (light) | `#FFFFFF` | Cards, sidebar |
| `--color-surface-elevated` (light) | `#FFFFFF` com sombra mais forte | Modais, popovers |
| `--color-border` (light) | `#E2E7EE` | Bordas sutis |
| `--color-border-strong` (light) | `#C7CFDA` | Bordas de foco/hover |
| `--color-text-primary` (light) | `#101720` | Texto principal |
| `--color-text-secondary` (light) | `#4B5563` | Labels, descrições |
| `--color-text-muted` (light) | `#8A94A3` | Placeholders, metadados |
| `--color-accent` (light) | `#2F6FE0` | Acento (levemente mais escuro para contraste em fundo claro) |
| `--color-positive` (light) | `#158A56` | Receita/positivo |
| `--color-negative` (light) | `#D8384A` | Despesa/negativo |
| `--color-warning` (light) | `#B5790A` | Alerta |
| `--color-critical` (light) | `#D9531F` | Crítico |

O dark é o tema padrão de lançamento; o light é um toggle em Configurações, não uma prioridade de implementação inicial.

---

## 3. Tipografia

- **Família:** [Inter](https://fonts.google.com/specimen/Inter) via Google Fonts CDN (`<link>`), com fallback `system-ui, -apple-system, "Segoe UI", sans-serif`.
- **Fonte para números (opcional, reforço):** Inter já possui bom suporte a `tabular-nums`; não é necessária uma segunda família. Para telas muito densas em números (tabela de transações, KPIs), aplicar `font-variant-numeric: tabular-nums` para alinhamento vertical perfeito de dígitos.

### Escala de tamanhos

| Token | Tamanho | Line-height | Peso | Uso |
|---|---|---|---|---|
| `--text-xs` | 12px | 16px | 400/500 | Metadados, timestamps, legendas de gráfico |
| `--text-sm` | 13px | 18px | 400/500 | Texto secundário, labels de formulário, células de tabela |
| `--text-base` | 14px | 20px | 400 | Corpo padrão, texto de tabela principal |
| `--text-md` | 16px | 24px | 500 | Títulos de card, subtítulos de seção |
| `--text-lg` | 20px | 28px | 600 | Títulos de página |
| `--text-xl` | 28px | 34px | 600/700 | Valor de KPI principal (saldo) |
| `--text-2xl` | 36px | 40px | 700 | Valor hero (opcional, saldo total no dashboard) |

### Pesos usados
- **400 (Regular):** corpo de texto, texto secundário.
- **500 (Medium):** labels, botões secundários, títulos de card.
- **600 (SemiBold):** títulos de página, valores de KPI, botões primários.
- **700 (Bold):** apenas para o valor hero de saldo e destaques pontuais — usar com moderação.

### Regra para números/valores monetários
- Sempre `font-variant-numeric: tabular-nums` em qualquer local onde números aparecem em coluna/lista (tabela de transações, listas de categoria, KPIs).
- Formato brasileiro obrigatório: separador de milhar `.`, decimal `,`, símbolo `R$` com espaço não-quebrável (`R$ 1.234,56`).
- Valores negativos (despesas) usam `--color-negative` e prefixo `-`; valores positivos (receita) usam `--color-positive` e podem levar prefixo `+` em contextos de variação/diferença.
- KPIs e valores de destaque usam peso 600–700; valores em tabela usam peso 400–500 para não competir com a hierarquia dos cards.

---

## 4. Espaçamento, raio e sombras

### Escala de espaçamento (base 4px)

| Token | Valor |
|---|---|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 20px |
| `--space-6` | 24px |
| `--space-8` | 32px |
| `--space-10` | 40px |
| `--space-12` | 48px |
| `--space-16` | 64px |

Padding padrão de card: `--space-5` (20px). Gap entre cards em grid: `--space-4` a `--space-6`. Padding de página (container principal): `--space-6` no mobile, `--space-8` no desktop.

### Raio de borda

| Token | Valor | Uso |
|---|---|---|
| `--radius-sm` | 6px | Badges, inputs pequenos, chips |
| `--radius-md` | 10px | Botões, inputs, itens de lista |
| `--radius-lg` | 14px | Cards padrão |
| `--radius-xl` | 20px | Modais, cards elevados/destaque |
| `--radius-full` | 999px | Avatares, pills, indicadores circulares |

Nota: propositalmente **não** usamos o mesmo raio em tudo (evitar "tudo com o mesmo `rounded-xl`") — cards e modais têm raio maior que botões/inputs para criar hierarquia de contenção.

### Sombras

| Token | Valor | Uso |
|---|---|---|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.24)` | Botões, chips em hover |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.32)` | Cards padrão (dark, sombra é sutil pois o fundo já é escuro — usar mais borda que sombra) |
| `--shadow-lg` | `0 12px 32px rgba(0,0,0,0.44)` | Modais, dropdowns, popovers |
| `--shadow-focus` | `0 0 0 3px rgba(76,141,255,0.35)` | Anel de foco em elementos interativos |

No dark mode, a sombra sozinha não é suficiente para separar superfícies — sempre combinar `--shadow-md`/`lg` com `--color-border` de 1px para dar definição real ao card.

---

## 5. Catálogo de componentes

### 5.1 Sidebar de navegação
- **Visual:** coluna fixa à esquerda, largura ~240px no desktop, fundo `--color-surface`, borda direita de 1px `--color-border`. Logo/nome "FinPilot" no topo (32-40px altura), seguido de lista de itens de navegação: Visão Geral, Transações, Orçamentos, Dicas de IA, Configurações. Cada item com ícone (linha, 20px) + label, altura de linha ~44px, raio `--radius-md` no item ativo.
- **Estados:**
  - *Default:* ícone/texto em `--color-text-secondary`, fundo transparente.
  - *Hover:* fundo `--color-surface-elevated`, texto `--color-text-primary`.
  - *Ativo:* fundo `--color-accent-soft`, texto e ícone em `--color-accent`, barra vertical de 3px `--color-accent` colada à borda esquerda do item.
  - *Foco (teclado):* anel `--shadow-focus` visível ao redor do item.
- **Responsivo:** no mobile, colapsa em barra inferior fixa (bottom tab bar) com 5 ícones + label curto, ou em drawer lateral acionado por botão hambúrguer no header — ver wireframes (seção 6).

### 5.2 Card de KPI (saldo, receita, despesa, taxa de poupança)
- **Visual:** card `--color-surface`, padding `--space-5`, raio `--radius-lg`, borda 1px `--color-border`. Estrutura: label pequeno no topo (`--text-sm`, `--color-text-secondary`, ex. "Saldo atual"), valor grande abaixo (`--text-xl`/`--text-2xl`, tabular-nums, cor neutra `--color-text-primary` para saldo, ou semântica para receita/despesa), linha de variação abaixo (ex. "+12,4% vs mês anterior" em `--text-xs` com ícone de seta e cor semântica).
- **Estados:**
  - *Default:* como descrito.
  - *Hover:* leve elevação (`--shadow-md` → `--shadow-lg`), borda muda para `--color-border-strong`.
  - *Loading:* skeleton shimmer — retângulos cinza (`--color-surface-elevated` pulsando) no lugar do label e do valor.
  - *Vazio:* quando não há dados no período, valor mostra "R$ 0,00" em `--color-text-muted` e subtexto "Sem movimentações neste mês".
  - *Erro:* ícone de alerta + texto "Não foi possível carregar" em `--color-negative`, com botão "Tentar novamente" em texto pequeno.

### 5.3 Gráfico de tendência (linha/área)
- **Visual:** card largo, título "Evolução do saldo" ou "Receitas x Despesas", seletor de período (7d/30d/12m) alinhado à direita do título. Área sob a linha com gradiente sutil da cor da série (verde para receita, vermelho para despesa, azul-acento para saldo) indo de ~25% opacidade no topo a 0% na base. Grid horizontal discreto em `--color-border`, eixo Y com valores abreviados (ex. "R$ 5k"), tooltip customizado (Chart.js `tooltip` callback) usando `--color-surface-elevated` com borda e sombra `--shadow-lg`.
- **Estados:**
  - *Default:* linha suave (tension ~0.3), pontos visíveis só no hover.
  - *Hover:* linha vertical guia (crosshair) + tooltip com valor formatado em BRL e data.
  - *Loading:* skeleton com "ondas" horizontais simulando o gráfico, ou spinner central discreto.
  - *Vazio:* mensagem central "Nenhum dado no período selecionado" com ícone de gráfico apagado.
  - *Erro:* mesma abordagem do KPI (ícone + retry).

### 5.4 Gráfico de gastos por categoria (donut) + legenda
- **Visual:** donut à esquerda (ou topo no mobile), ~160-200px de diâmetro, espessura de anel moderada (não muito fina). Cada fatia usa uma cor de uma paleta categórica de 6-8 tons derivados do acento e das semânticas (variações de matiz mantendo saturação/luminosidade parecidas para não competir com as cores de status). Centro do donut mostra o total gasto no período (`--text-md`, tabular-nums). Legenda à direita (ou abaixo): lista com bolinha de cor + nome da categoria + valor em BRL alinhado à direita + percentual pequeno em `--color-text-muted`.
- **Estados:**
  - *Default:* como descrito, ordenado do maior para o menor gasto.
  - *Hover:* fatia correspondente se destaca (leve `scale`/offset), linha da legenda ganha fundo `--color-surface-elevated`.
  - *Loading:* donut cinza pulsante + linhas de legenda em skeleton.
  - *Vazio:* donut substituído por círculo tracejado cinza + texto "Sem despesas categorizadas".
  - *Erro:* mensagem de erro com retry, mesma linguagem visual dos outros gráficos.

### 5.5 Tabela de transações com filtros e busca
- **Visual:** barra superior com campo de busca (ícone lupa + placeholder "Buscar transação..."), filtros por categoria/tipo/período (dropdowns/pills), botão "+ Nova transação" em destaque (`--color-accent`) alinhado à direita. Tabela com header sticky, colunas: Data, Descrição, Categoria (badge colorido), Valor (alinhado à direita, tabular-nums, cor semântica), Ações (ícones editar/excluir aparecem no hover da linha). Zebra striping sutil ou apenas divisórias `--color-border` entre linhas — preferir divisórias (mais sóbrio).
- **Estados:**
  - *Default:* linhas com hover destacando fundo `--color-surface-elevated`.
  - *Hover (linha):* ícones de ação aparecem (fade-in), cursor pointer se a linha for clicável para detalhe.
  - *Loading:* skeleton de linhas (5-8 linhas cinza pulsantes) mantendo estrutura de colunas.
  - *Vazio:* estado vazio central com ilustração simples (ícone de carteira/documento), texto "Nenhuma transação encontrada" + botão "Adicionar primeira transação" (se filtro ativo: "Nenhum resultado para os filtros aplicados" + botão "Limpar filtros").
  - *Erro:* banner de erro no topo da tabela + retry.
  - *Paginação:* rodapé com "Mostrando 1-20 de 143" + botões anterior/próximo.

### 5.6 Barra de progresso de orçamento
- **Visual:** dentro do card de categoria de orçamento: nome da categoria + valor gasto / valor limite (ex. "R$ 420,00 / R$ 500,00") acima da barra. Barra horizontal, altura ~8px, fundo `--color-border`, preenchimento com cor semântica conforme estado, raio `--radius-full`.
- **Estados:**
  - *Normal (< 80% do limite):* preenchimento `--color-positive` ou `--color-accent` (recomendado usar acento para "normal" e reservar verde só para receita, evitando ambiguidade — decisão: usar `--color-accent` no normal).
  - *Atenção (80-99%):* preenchimento `--color-warning`, pequeno ícone de alerta triangular ao lado do valor.
  - *Estourado (≥100%):* preenchimento `--color-critical`, barra pode ultrapassar visualmente o container (marca de "overflow" tracejada) e texto do valor gasto em `--color-critical` com peso 600.
  - *Loading:* barra cinza pulsante sem preenchimento definido.
  - *Vazio:* categoria sem orçamento definido mostra texto "Definir orçamento" como link/botão no lugar da barra.

### 5.7 Card de dica de IA
- **Visual:** card com borda esquerda de 3-4px na cor de severidade (em vez de fundo colorido inteiro, para manter sobriedade). Topo: badge de severidade ("Informativo" / "Atenção" / "Crítico") + ícone de categoria da dica (ex. assinatura recorrente, gasto acima da média). Corpo: texto da dica em linguagem natural (`--text-base`), destaque do impacto estimado em uma linha própria: "Impacto estimado: R$ 87,00/mês" com o valor em tabular-nums e cor semântica correspondente à severidade. Rodapé com ações: "Marcar como resolvida" / "Ignorar" (texto secundário) e timestamp de quando a dica foi gerada.
- **Estados:**
  - *Severidade Informativo:* borda/ícone em `--color-info`.
  - *Severidade Atenção:* borda/ícone em `--color-warning`.
  - *Severidade Crítico:* borda/ícone em `--color-critical`, pode incluir leve fundo `--color-critical-soft` para reforçar prioridade.
  - *Loading:* skeleton com placeholder de badge + 2 linhas de texto.
  - *Vazio:* estado "Nenhuma dica no momento" com ícone de lâmpada apagada + texto "Continue registrando transações para receber recomendações".
  - *Erro:* "Não foi possível gerar dicas agora" + retry.
  - *Resolvida/Ignorada:* card com opacidade reduzida (~60%) e texto riscado ou badge "Resolvida" em cinza, movida para o fim da lista ou colapsada.

### 5.8 Modal de formulário (nova transação)
- **Visual:** overlay escuro (`rgba(0,0,0,0.6)`) sobre o app, modal centralizado, largura ~480px, fundo `--color-surface-elevated`, raio `--radius-xl`, sombra `--shadow-lg`. Header com título "Nova transação" + botão fechar (X) no canto superior direito. Corpo com campos: Tipo (toggle Receita/Despesa), Valor (input numérico grande, formatado em BRL ao vivo), Categoria (select), Data (date picker nativo estilizado), Descrição (input texto), Recorrente (checkbox opcional). Rodapé com botões "Cancelar" (secundário, texto) e "Salvar" (primário, `--color-accent`, alinhado à direita).
- **Estados:**
  - *Default:* campos com borda `--color-border`, foco muda borda para `--color-accent` + `--shadow-focus`.
  - *Validação/erro de campo:* borda `--color-negative` + texto de erro pequeno abaixo do campo.
  - *Loading (salvando):* botão "Salvar" mostra spinner inline e fica desabilitado, texto muda para "Salvando...".
  - *Sucesso:* modal fecha automaticamente e dispara toast de confirmação (ver 5.9).
  - *Erro de submissão:* banner de erro no topo do modal ("Não foi possível salvar. Tente novamente.") sem fechar o modal.

### 5.9 Toast de feedback
- **Visual:** aparece no canto inferior direito (desktop) ou centralizado inferior (mobile), largura ~320-360px, fundo `--color-surface-elevated`, borda 1px correspondente à cor semântica, raio `--radius-md`, sombra `--shadow-lg`. Ícone à esquerda (check/alerta/X conforme tipo) + mensagem curta + botão de fechar opcional (X pequeno). Barra de progresso fina no rodapé do toast indicando tempo até auto-dismiss (~4s).
- **Estados:**
  - *Sucesso:* borda/ícone `--color-positive` ("Transação adicionada com sucesso").
  - *Erro:* borda/ícone `--color-negative` ("Erro ao salvar transação").
  - *Aviso:* borda/ícone `--color-warning`.
  - *Info:* borda/ícone `--color-info`.
  - *Entrada/saída:* slide-in + fade (translateY 8px → 0, opacity 0 → 1) na entrada; fade-out na saída.

---

## 6. Wireframes textuais por tela

Convenção de breakpoints: **mobile** `< 640px`, **tablet** `640–1024px`, **desktop** `> 1024px`. Sidebar vira bottom-bar/drawer no mobile; grids de N colunas colapsam progressivamente.

### 6.1 Visão Geral (Dashboard)

```
Desktop (>1024px) — grid 12 colunas
┌───────────┬──────────────────────────────────────────────────────────────┐
│           │  Header: "Visão Geral"          [seletor de período ▾]       │
│  Sidebar  ├──────────────────────────────────────────────────────────────┤
│  (fixa,   │  [KPI Saldo] [KPI Receita] [KPI Despesa] [KPI Taxa Poupança] │  <- 4 cols, 1 linha
│  240px)   │  cada KPI ocupa 3/12 colunas                                  │
│           ├───────────────────────────────────┬────────────────────────┤
│  - Visão  │  Gráfico de tendência (8/12 cols)  │  Donut categorias      │
│    Geral  │  linha/área, seletor 7d/30d/12m    │  (4/12 cols) + legenda │
│  - Trans. │                                    │                        │
│  - Orçam. ├───────────────────────────────────┴────────────────────────┤
│  - Dicas  │  Últimas transações (tabela compacta, 5-6 linhas, link      │
│  - Config │  "ver todas") — full width                                  │
│           ├──────────────────────────────────────────────────────────────┤
│           │  Dicas de IA em destaque (2-3 cards em linha, carrossel     │
│           │  ou grid 3 cols) — full width                                │
└───────────┴──────────────────────────────────────────────────────────────┘

Tablet (640-1024px) — grid 2 colunas
- Sidebar colapsa para ícones apenas (64px) ou drawer.
- KPIs em grid 2x2.
- Gráfico de tendência full width; donut abaixo, full width.
- Tabela de últimas transações full width, colunas reduzidas (oculta "Ações" até tap).
- Dicas de IA em grid 2 colunas.

Mobile (<640px) — coluna única
- Sidebar vira bottom tab bar fixa (5 ícones).
- Header com título + botão de período em dropdown compacto.
- KPIs em carrossel horizontal com scroll-snap (1.2 cards visíveis) OU pilha vertical 1 coluna.
- Gráfico de tendência full width, altura reduzida (~180px).
- Donut + legenda empilhados (donut centralizado, legenda em lista abaixo).
- Últimas transações: lista de cards (não tabela) — cada transação é um card compacto.
- Dicas de IA: pilha vertical, 1 card por vez com scroll.
```

### 6.2 Transações

```
Desktop
┌───────────┬──────────────────────────────────────────────────────────────┐
│  Sidebar  │  Header: "Transações"                [+ Nova transação]     │
│           ├──────────────────────────────────────────────────────────────┤
│           │  [🔍 Buscar...] [Categoria ▾] [Tipo ▾] [Período ▾] [Limpar] │
│           ├──────────────────────────────────────────────────────────────┤
│           │  Tabela: Data | Descrição | Categoria | Valor | Ações        │
│           │  (header sticky, paginação no rodapé)                        │
│           ├──────────────────────────────────────────────────────────────┤
│           │  Rodapé: "Mostrando 1-20 de 143"      [< Anterior] [Próx >]  │
└───────────┴──────────────────────────────────────────────────────────────┘

Tablet
- Filtros colapsam em botão "Filtros" que abre painel/drawer lateral.
- Tabela mantém colunas principais, oculta coluna de Ações até hover/tap (aparece como menu "⋮").

Mobile
- Busca fixa no topo; filtros em botão que abre bottom sheet.
- Tabela vira lista de cards: cada card = Data pequena + Descrição + badge categoria + valor em destaque à direita.
- Botão "+ Nova transação" vira FAB (floating action button) circular no canto inferior direito.
```

### 6.3 Orçamentos

```
Desktop — grid de cards, 3 colunas
┌───────────┬──────────────────────────────────────────────────────────────┐
│  Sidebar  │  Header: "Orçamentos"              [+ Novo orçamento]        │
│           ├──────────────────────────────────────────────────────────────┤
│           │  Resumo do mês: total orçado vs total gasto (barra grande,   │
│           │  full width, com os 3 estados de cor)                        │
│           ├───────────────┬───────────────┬──────────────────────────────┤
│           │  Card categ. 1│  Card categ. 2│  Card categ. 3               │
│           │  (barra +     │               │                              │
│           │  valores)     │               │                              │
│           ├───────────────┴───────────────┴──────────────────────────────┤
│           │  ... mais linhas de 3 cards conforme número de categorias    │
└───────────┴──────────────────────────────────────────────────────────────┘

Tablet — grid 2 colunas de cards
Mobile — pilha vertical 1 coluna; resumo do mês mantém-se no topo, sticky opcional.
```

### 6.4 Dicas de IA

```
Desktop — lista/feed em coluna única centralizada (max-width ~720px) com painel lateral de filtro
┌───────────┬──────────────────────────────────────────────────────────────┐
│  Sidebar  │  Header: "Dicas de IA"     [Filtro: Todas/Ativas/Resolvidas]│
│           ├───────────────────────────────┬──────────────────────────────┤
│           │  Feed de cards de dica         │  Painel lateral (opcional): │
│           │  (um abaixo do outro,          │  resumo "Economia potencial │
│           │  ordenados por severidade)     │  este mês: R$ X" + botão    │
│           │                                │  "Gerar novas dicas"        │
└───────────┴───────────────────────────────┴──────────────────────────────┘

Tablet — painel lateral desce para o topo (card de resumo acima do feed).
Mobile — feed único, full width; card de resumo colapsável no topo (accordion).
```

### 6.5 Configurações

```
Desktop — layout de duas colunas: navegação de seções + conteúdo
┌───────────┬──────────────────────────────────────────────────────────────┐
│  Sidebar  │  Header: "Configurações"                                    │
│           ├───────────────┬──────────────────────────────────────────────┤
│           │  Sub-nav:     │  Conteúdo da seção ativa:                   │
│           │  - Perfil     │  formulários simples (label + input, grupos │
│           │  - Categorias │  de campo com título de subseção,           │
│           │  - Aparência  │  botão "Salvar alterações" no rodapé)        │
│           │  - Dados      │                                              │
│           │  (tema        │                                              │
│           │  dark/light)  │                                              │
└───────────┴───────────────┴──────────────────────────────────────────────┘

Tablet — sub-nav vira tabs horizontais no topo do conteúdo (scroll horizontal se necessário).
Mobile — sub-nav vira accordion/lista de itens; toque em um item navega para tela de sub-página com botão "voltar".
```

---

## 7. Microinterações e acessibilidade

- **Foco visível:** todo elemento interativo (botão, link, input, item de sidebar, linha de tabela clicável) deve ter `--shadow-focus` (anel azul de 3px, offset 2px) visível via `:focus-visible`. Nunca remover outline sem substituir por alternativa igualmente visível.
- **Contraste mínimo AA:** todos os pares texto/fundo devem atingir no mínimo 4.5:1 para texto normal e 3:1 para texto grande (≥18px ou 14px bold). A paleta dark foi calibrada para isso: `--color-text-primary` (#E7EBF0) sobre `--color-bg` (#0B0F14) e `--color-text-secondary` (#A9B4C0) sobre `--color-surface` (#11161D) atendem AA. Validar cores semânticas sobre fundo `-soft` correspondente antes de usar texto colorido em corpo de parágrafo.
- **Alvos de toque:** mínimo 44x44px para qualquer elemento tocável no mobile (itens de bottom bar, botões de ação em linha de tabela, FAB, checkboxes). Em desktop, botões/inputs mantêm altura mínima de 36-40px.
- **Feedback de carregamento:** nunca deixar a tela "congelada" sem sinal. Usar skeletons (não spinners genéricos) para conteúdo estruturado (cards, tabelas, gráficos); usar spinner inline apenas em botões durante submissão. Toda ação assíncrona (salvar, excluir, gerar dica) deve dar feedback em até 200ms (estado loading) e confirmar/errar via toast.
- **Transições:** duração padrão 150-200ms, easing `ease-out` para entradas e `ease-in` para saídas. Hover em cards/linhas: transição de `background-color` e `border-color` apenas (evitar animar `box-shadow` de forma pesada, custo de repaint).
- **Estados de erro nunca são silenciosos:** todo erro de carregamento ou submissão exibe mensagem textual + ação de recuperação (retry ou instrução clara), nunca apenas um ícone.
- **Redução de movimento:** respeitar `prefers-reduced-motion` — desativar transições de entrada/slide, manter apenas mudanças de opacidade quando o usuário sinalizar preferência por menos movimento.
- **Navegação por teclado:** modal de nova transação deve ter *focus trap* (Tab não escapa do modal) e fechar com `Esc`; toasts não devem roubar foco.

---

## Tokens

Design tokens prontos para uso direto como CSS custom properties. O tema dark é o padrão (`:root`); o tema light é ativado por classe `.theme-light` no `<html>`/`<body>` (a ser alternado via JS vanilla e persistido em `localStorage`).

```css
:root {
  /* Cores base — dark (padrão) */
  --color-bg: #0B0F14;
  --color-surface: #11161D;
  --color-surface-elevated: #171D26;
  --color-border: #232B36;
  --color-border-strong: #2E3945;

  --color-text-primary: #E7EBF0;
  --color-text-secondary: #A9B4C0;
  --color-text-muted: #6B7684;

  --color-accent: #4C8DFF;
  --color-accent-soft: #1B2B47;

  /* Semânticas */
  --color-positive: #2FD68C;
  --color-positive-soft: #0F2E22;
  --color-negative: #FF5C6C;
  --color-negative-soft: #3A1418;
  --color-warning: #F2B94D;
  --color-warning-soft: #3A2A0E;
  --color-critical: #FF7A45;
  --color-critical-soft: #3D1F10;
  --color-info: #4C8DFF;
  --color-info-soft: #1B2B47;

  /* Paleta categórica (gráfico donut, 8 tons) */
  --color-cat-1: #4C8DFF;
  --color-cat-2: #2FD68C;
  --color-cat-3: #F2B94D;
  --color-cat-4: #C792EA;
  --color-cat-5: #FF7A45;
  --color-cat-6: #5FD4D0;
  --color-cat-7: #FF5C6C;
  --color-cat-8: #8BA3C7;

  /* Tipografia */
  --font-family-base: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;

  --text-xs: 12px;
  --text-xs-lh: 16px;
  --text-sm: 13px;
  --text-sm-lh: 18px;
  --text-base: 14px;
  --text-base-lh: 20px;
  --text-md: 16px;
  --text-md-lh: 24px;
  --text-lg: 20px;
  --text-lg-lh: 28px;
  --text-xl: 28px;
  --text-xl-lh: 34px;
  --text-2xl: 36px;
  --text-2xl-lh: 40px;

  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  --font-numeric: tabular-nums;

  /* Espaçamento */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  /* Raio */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;
  --radius-full: 999px;

  /* Sombras */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.24);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.32);
  --shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.44);
  --shadow-focus: 0 0 0 3px rgba(76, 141, 255, 0.35);

  /* Transições */
  --transition-fast: 150ms ease-out;
  --transition-base: 200ms ease-out;

  /* Sidebar / layout */
  --sidebar-width: 240px;
  --sidebar-width-collapsed: 64px;
  --bottombar-height: 64px;
}

.theme-light {
  --color-bg: #F5F7FA;
  --color-surface: #FFFFFF;
  --color-surface-elevated: #FFFFFF;
  --color-border: #E2E7EE;
  --color-border-strong: #C7CFDA;

  --color-text-primary: #101720;
  --color-text-secondary: #4B5563;
  --color-text-muted: #8A94A3;

  --color-accent: #2F6FE0;
  --color-accent-soft: #DCE8FF;

  --color-positive: #158A56;
  --color-positive-soft: #E3F6ED;
  --color-negative: #D8384A;
  --color-negative-soft: #FBE4E6;
  --color-warning: #B5790A;
  --color-warning-soft: #FBEFD6;
  --color-critical: #D9531F;
  --color-critical-soft: #FBE6DB;
  --color-info: #2F6FE0;
  --color-info-soft: #DCE8FF;

  --shadow-sm: 0 1px 2px rgba(16, 23, 32, 0.06);
  --shadow-md: 0 4px 12px rgba(16, 23, 32, 0.08);
  --shadow-lg: 0 12px 32px rgba(16, 23, 32, 0.14);
  --shadow-focus: 0 0 0 3px rgba(47, 111, 224, 0.25);
}
```
