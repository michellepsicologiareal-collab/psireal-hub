(function () {
  "use strict";

  const DEFAULT_CATEGORIES = [
    { nome: "Alimentação", tipo: "despesa", cor: "#E49B35", icone: "🍽️", essencial: true },
    { nome: "Moradia", tipo: "despesa", cor: "#7868D8", icone: "🏠", essencial: true },
    { nome: "Transporte", tipo: "despesa", cor: "#4C8DFF", icone: "🚗", essencial: true },
    { nome: "Saúde", tipo: "despesa", cor: "#D85E7D", icone: "💊", essencial: true },
    { nome: "Educação", tipo: "despesa", cor: "#5A9BD5", icone: "💻", essencial: true },
    { nome: "Lazer", tipo: "despesa", cor: "#A978E8", icone: "🎮", essencial: false },
    { nome: "Assinaturas", tipo: "despesa", cor: "#7A69D8", icone: "🧾", essencial: false },
    { nome: "Roupas e calçados", tipo: "despesa", cor: "#E68A5C", icone: "👕", essencial: false },
    { nome: "Cuidados pessoais", tipo: "despesa", cor: "#D978B8", icone: "🧴", essencial: false },
    { nome: "Trabalho", tipo: "despesa", cor: "#4A8C82", icone: "👤", essencial: false },
    { nome: "Presentes", tipo: "despesa", cor: "#D38B4F", icone: "🎁", essencial: false },
    { nome: "Outros", tipo: "despesa", cor: "#7D8B99", icone: "📦", essencial: false },
    { nome: "Salário", tipo: "receita", cor: "#19A974", icone: "💰", essencial: true },
    { nome: "Rendimentos", tipo: "receita", cor: "#2F9E79", icone: "📈", essencial: false },
    { nome: "Outros recebimentos", tipo: "receita", cor: "#4C8DFF", icone: "➕", essencial: false },
  ];

  const PAGE_META = {
    overview: { hash: "diario", label: "Diário financeiro" },
    diary: { hash: "lancamentos", label: "Lançamentos do diário" },
    categories: { hash: "categorias", label: "Categorias" },
    calendar: { hash: "calendario", label: "Calendário financeiro" },
    goals: { hash: "metas", label: "Caixinhas de metas" },
    budgets: { hash: "planejamento", label: "Planejamento do mês" },
    cards: { hash: "contas-patrimonio", label: "Contas e patrimônio" },
    reminders: { hash: "lembretes", label: "Lembretes financeiros" },
    conscious: { hash: "modo-consciente", label: "Modo Consciente" },
  };

  const state = {
    page: "overview",
    month: new Date().toISOString().slice(0, 7),
    period: "month",
    selectedDate: new Date().toISOString().slice(0, 10),
    user: null,
    categories: [],
    transactions: [],
    summary: null,
    spending: [],
    goals: [],
    budgets: [],
    budgetStatus: [],
    cardSummary: null,
    cardFile: null,
    cardPreview: null,
    reminders: [],
    accounts: [],
    accountTab: "all",
    scheduledExpenses: [],
    purchasePlans: [],
    planningTab: "scheduled",
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const escapeHtml = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  function safeColor(value) {
    return /^#[0-9a-f]{3,8}$/i.test(value || "") ? value : "#7046D9";
  }

  function brl(value) {
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value || 0));
  }

  function formatNumber(value) {
    return new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value || 0));
  }

  function parseMoney(value) {
    let text = String(value ?? "").trim().replace(/[^\d,.-]/g, "");
    if (!text) return 0;
    const hasComma = text.includes(",");
    const hasDot = text.includes(".");
    if (hasComma && hasDot) text = text.replaceAll(".", "").replace(",", ".");
    else if (hasComma) text = text.replace(",", ".");
    const result = Number(text);
    return Number.isFinite(result) ? Math.round(result * 100) / 100 : 0;
  }

  function formatDate(value) {
    if (!value) return "Sem data";
    return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" })
      .format(new Date(`${value}T12:00:00`))
      .replace(".", "");
  }

  function longDate(value) {
    if (!value) return "Sem prazo";
    return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short", year: "numeric" })
      .format(new Date(`${value}T12:00:00`));
  }

  function isoDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function dateFromIso(value) {
    return new Date(`${value}T12:00:00`);
  }

  function monthLabel(value) {
    const [year, month] = value.split("-").map(Number);
    return new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric" })
      .format(new Date(year, month - 1, 1))
      .replace(/^./, (letter) => letter.toUpperCase());
  }

  function startOfWeek(value) {
    const date = dateFromIso(value);
    date.setDate(date.getDate() - date.getDay());
    return isoDate(date);
  }

  function endOfWeek(value) {
    const date = dateFromIso(startOfWeek(value));
    date.setDate(date.getDate() + 6);
    return isoDate(date);
  }

  function periodTransactions() {
    if (state.period === "month") return state.transactions;
    if (state.period === "day") {
      return state.transactions.filter((item) => item.data === state.selectedDate);
    }
    const start = startOfWeek(state.selectedDate);
    const end = endOfWeek(state.selectedDate);
    return state.transactions.filter((item) => item.data >= start && item.data <= end);
  }

  function periodDescription() {
    if (state.period === "day") {
      return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short", year: "numeric" })
        .format(dateFromIso(state.selectedDate))
        .replace(".", "");
    }
    if (state.period === "week") {
      const start = dateFromIso(startOfWeek(state.selectedDate));
      const end = dateFromIso(endOfWeek(state.selectedDate));
      const startText = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" }).format(start).replace(".", "");
      const endText = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" }).format(end).replace(".", "");
      return `${startText} – ${endText}`;
    }
    return monthLabel(state.month);
  }

  function detailMessage(body, fallback) {
    if (!body) return fallback;
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
    return body.message || fallback;
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    if (response.status === 401) {
      location.href = "/entrar?mode=login";
      throw new Error("Sua sessão terminou. Entre novamente.");
    }
    if (!response.ok) {
      let body = null;
      let fallback = "Não foi possível concluir essa ação.";
      try {
        body = await response.json();
      } catch {
        if (response.status >= 500) fallback = "O servidor não conseguiu salvar agora. Tente novamente em instantes.";
      }
      throw new Error(detailMessage(body, fallback));
    }
    if (response.status === 204) return null;
    return response.json();
  }

  async function upload(path, file) {
    const body = new FormData();
    body.append("file", file, file.name);
    const response = await fetch(path, {
      method: "POST",
      credentials: "same-origin",
      body,
    });
    if (response.status === 401) {
      location.href = "/entrar?mode=login";
      throw new Error("Sua sessão terminou. Entre novamente.");
    }
    if (!response.ok) {
      let responseBody = null;
      try { responseBody = await response.json(); } catch {}
      throw new Error(detailMessage(responseBody, "Não foi possível ler essa fatura."));
    }
    return response.json();
  }

  function toast(message, type = "success") {
    const stack = $("[data-toasts]");
    const item = document.createElement("div");
    item.className = `toast toast--${type}`;
    item.innerHTML = `<span aria-hidden="true">${type === "success" ? "✓" : "!"}</span><span>${escapeHtml(message)}</span>`;
    stack.appendChild(item);
    setTimeout(() => item.remove(), 4200);
  }

  function emptyState(icon, title, copy, action = "") {
    return `<div class="empty-state"><div><span aria-hidden="true">${icon}</span><strong>${escapeHtml(title)}</strong><p>${escapeHtml(copy)}</p>${action}</div></div>`;
  }

  function categoryById(id) {
    return state.categories.find((item) => Number(item.id) === Number(id)) || null;
  }

  async function ensureCategories() {
    state.categories = await api("/api/categories");
    if (state.categories.length) return;
    for (const category of DEFAULT_CATEGORIES) {
      await api("/api/categories", { method: "POST", body: JSON.stringify(category) });
    }
    state.categories = await api("/api/categories");
  }

  function setUser(user) {
    state.user = user;
    const metadata = user.user_metadata || {};
    const fullName = user.display_name || metadata.display_name || metadata.full_name || user.email?.split("@")[0] || "Minha conta";
    const firstName = fullName.trim().split(/\s+/)[0] || "Olá";
    $$("[data-user-name]").forEach((node) => { node.textContent = fullName; });
    $$("[data-first-name]").forEach((node) => { node.textContent = firstName; });
    $$("[data-avatar]").forEach((node) => { node.textContent = firstName.charAt(0).toUpperCase(); });
  }

  function setTheme(theme) {
    const next = theme === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("finpilot-theme", next);
    $$("[data-theme-icon]").forEach((node) => { node.textContent = next === "dark" ? "☀" : "☾"; });
    $$("[data-theme-label]").forEach((node) => { node.textContent = next === "dark" ? "Modo claro" : "Modo escuro"; });
    const meta = $('meta[name="theme-color"]');
    if (meta) meta.content = next === "dark" ? "#11141c" : "#f5f3fa";
  }

  function pageFromHash() {
    const hash = location.hash.replace("#", "");
    return Object.entries(PAGE_META).find(([, item]) => item.hash === hash)?.[0] || "overview";
  }

  function setPage(page, updateHash = true) {
    if (!PAGE_META[page]) page = "overview";
    state.page = page;
    $$("[data-page]").forEach((node) => node.classList.toggle("is-active", node.dataset.page === page));
    $$("[data-page-link]").forEach((node) => node.classList.toggle("is-active", node.dataset.pageLink === page));
    $("[data-breadcrumb]").textContent = PAGE_META[page].label;
    if (updateHash) history.replaceState(null, "", `#${PAGE_META[page].hash}`);
    closeMobileMenu();
    $(".main-content").focus({ preventScroll: true });
    scrollTo({ top: 0, behavior: "smooth" });
  }

  function openMobileMenu() {
    $(".sidebar")?.classList.add("is-open");
    const overlay = $("[data-menu-close]");
    if (overlay) overlay.hidden = false;
  }

  function closeMobileMenu() {
    $(".sidebar")?.classList.remove("is-open");
    const overlay = $("[data-menu-close]");
    if (overlay) overlay.hidden = true;
  }

  function categoryOptions(type, selected = "") {
    const items = state.categories.filter((item) => item.tipo === type && !item.parent_id);
    return `<option value="">Sem categoria</option>${items.map((item) =>
      `<option value="${item.id}" ${Number(selected) === Number(item.id) ? "selected" : ""}>${escapeHtml(item.icone || "•")} ${escapeHtml(item.nome)}</option>`
    ).join("")}`;
  }

  function subcategoryOptions(parentId, selected = "") {
    const items = state.categories.filter((item) => Number(item.parent_id) === Number(parentId));
    return `<option value="">Sem subcategoria</option>${items.map((item) =>
      `<option value="${item.id}" ${Number(selected) === Number(item.id) ? "selected" : ""}>${escapeHtml(item.icone || "•")} ${escapeHtml(item.nome)}</option>`
    ).join("")}`;
  }

  function parentCategoryOptions(type, selected = "", editingId = "") {
    return `<option value="">Nenhuma — categoria principal</option>${state.categories
      .filter((item) => item.tipo === type && !item.parent_id && Number(item.id) !== Number(editingId))
      .map((item) => `<option value="${item.id}" ${Number(selected) === Number(item.id) ? "selected" : ""}>${escapeHtml(item.icone || "•")} ${escapeHtml(item.nome)}</option>`)
      .join("")}`;
  }

  function budgetCategoryOptions(selected = "") {
    return state.categories.filter((item) => item.tipo === "despesa" && !item.parent_id).map((item) =>
      `<option value="${item.id}" ${Number(selected) === Number(item.id) ? "selected" : ""}>${escapeHtml(item.icone || "•")} ${escapeHtml(item.nome)}</option>`
    ).join("");
  }

  function transactionRow(transaction, showActions = true) {
    const category = categoryById(transaction.category_id);
    const color = safeColor(category?.cor);
    const categoryName = category?.nome || "Sem categoria";
    const sign = transaction.tipo === "despesa" ? "−" : "+";
    const meta = [formatDate(transaction.data), categoryName, transaction.metodo_pagamento].filter(Boolean).join(" · ");
    return `
      <article class="transaction-row">
        <span class="transaction-icon" style="--category-soft:${color}1f">${escapeHtml(category?.icone || (transaction.tipo === "receita" ? "💰" : "📦"))}</span>
        <div class="transaction-copy">
          <strong>${escapeHtml(transaction.descricao)}</strong>
          <small>${escapeHtml(meta)}${transaction.recorrente ? " · Repete" : ""}</small>
        </div>
        <div class="transaction-side">
          <span class="transaction-value transaction-value--${transaction.tipo}">${sign} ${brl(transaction.valor)}</span>
          ${showActions ? `<span class="transaction-actions">
            <button class="mini-button" type="button" data-edit-transaction="${transaction.id}" aria-label="Editar ${escapeHtml(transaction.descricao)}">Editar</button>
            <button class="mini-button mini-button--danger" type="button" data-delete-transaction="${transaction.id}" aria-label="Excluir ${escapeHtml(transaction.descricao)}">Excluir</button>
          </span>` : ""}
        </div>
      </article>`;
  }

  function groupedTotals(items, type) {
    const grouped = new Map();
    items.filter((item) => item.tipo === type).forEach((item) => {
      const directCategory = categoryById(item.category_id);
      const category = directCategory?.parent_id ? categoryById(directCategory.parent_id) || directCategory : directCategory;
      const key = category?.id || `none-${type}`;
      const current = grouped.get(key) || {
        name: category?.nome || (type === "receita" ? "Outros recebimentos" : "Sem categoria"),
        color: safeColor(category?.cor),
        value: 0,
      };
      current.value += Number(item.valor || 0);
      grouped.set(key, current);
    });
    return [...grouped.values()].sort((a, b) => b.value - a.value);
  }

  function flowMarkup(rows, emptyCopy) {
    if (!rows.length) return `<p class="fc-copy">${escapeHtml(emptyCopy)}</p>`;
    return rows.slice(0, 6).map((row) => `
      <div class="flow-row">
        <span style="--row-color:${safeColor(row.color)}">${escapeHtml(row.name)}</span>
        <strong>${brl(row.value)}</strong>
      </div>`).join("");
  }

  function renderSummary(items) {
    const income = items.filter((item) => item.tipo === "receita").reduce((sum, item) => sum + Number(item.valor), 0);
    const expense = items.filter((item) => item.tipo === "despesa").reduce((sum, item) => sum + Number(item.valor), 0);
    const balance = income - expense;
    const expenses = groupedTotals(items, "despesa");
    const largest = expenses[0];
    $("[data-summary-income]").textContent = brl(income);
    $("[data-summary-expense]").textContent = brl(expense);
    $("[data-summary-balance]").textContent = brl(balance);
    $("[data-summary-saving]").textContent = "Entradas menos despesas";
    $("[data-summary-category]").textContent = largest?.name || "—";
    $("[data-summary-category-value]").textContent = largest && expense
      ? `${brl(largest.value)} · ${((largest.value / expense) * 100).toFixed(1)}%`
      : "Sem gastos ainda";
    $("[data-summary-income-variation]").textContent = `${items.filter((item) => item.tipo === "receita").length} valores recebidos`;
    $("[data-summary-expense-variation]").textContent = `${items.filter((item) => item.tipo === "despesa").length} lançamentos no período`;
    return { income, expense, balance, expenses };
  }

  function calendarMarkup(month, selectedDate = "") {
    const [year, monthNumber] = month.split("-").map(Number);
    const first = new Date(year, monthNumber - 1, 1);
    const start = new Date(year, monthNumber - 1, 1 - first.getDay());
    const today = isoDate(new Date());
    const totals = new Map();
    state.transactions.forEach((item) => {
      const current = totals.get(item.data) || { income: 0, expense: 0, planned: 0, reminders: 0 };
      current[item.tipo === "receita" ? "income" : "expense"] += Number(item.valor);
      totals.set(item.data, current);
    });
    state.scheduledExpenses.forEach((item) => {
      if (item.data_vencimento.slice(0, 7) !== month) return;
      const current = totals.get(item.data_vencimento) || { income: 0, expense: 0, planned: 0, reminders: 0 };
      current.planned += 1;
      totals.set(item.data_vencimento, current);
    });
    state.reminders.filter((item) => !item.concluido).forEach((item) => {
      const current = totals.get(item.data_vencimento) || { income: 0, expense: 0, planned: 0, reminders: 0 };
      current.reminders += 1;
      totals.set(item.data_vencimento, current);
    });
    const weekdays = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
      .map((name) => `<div class="calendar-weekday">${name}</div>`).join("");
    const cells = [];
    for (let index = 0; index < 42; index += 1) {
      const date = new Date(start);
      date.setDate(start.getDate() + index);
      const value = isoDate(date);
      const total = totals.get(value);
      const outside = date.getMonth() !== monthNumber - 1;
      cells.push(`
        <button class="calendar-cell ${outside ? "is-outside" : ""} ${value === today ? "is-today" : ""} ${value === selectedDate ? "is-selected" : ""}"
          type="button" data-calendar-date="${value}" aria-label="${longDate(value)}">
          <strong>${date.getDate()}</strong>
          ${total?.expense ? `<small>− ${brl(total.expense)}</small>` : ""}
          ${total?.income ? `<small class="is-income">+ ${brl(total.income)}</small>` : ""}
          ${total?.planned || total?.reminders ? `<small class="is-planned">• ${Number(total.planned || 0) + Number(total.reminders || 0)} previsto${Number(total.planned || 0) + Number(total.reminders || 0) === 1 ? "" : "s"}</small>` : ""}
        </button>`);
    }
    return weekdays + cells.join("");
  }

  function renderCalendarDay(date) {
    const title = $("[data-calendar-day-title]");
    const container = $("[data-calendar-day-items]");
    if (!title || !container) return;
    title.textContent = longDate(date);
    const items = state.transactions.filter((item) => item.data === date);
    const planned = state.scheduledExpenses.filter((item) => item.data_vencimento === date);
    const reminders = state.reminders.filter((item) => item.data_vencimento === date && !item.concluido);
    const extra = [
      ...planned.map((item) => `<article class="calendar-planned-item"><span>▤</span><div><strong>${escapeHtml(item.titulo)}</strong><small>Despesa prevista · ${brl(item.valor)}</small></div><button class="mini-button" type="button" data-pay-scheduled="${item.id}">Marcar paga</button></article>`),
      ...reminders.map((item) => `<article class="calendar-planned-item"><span>♧</span><div><strong>${escapeHtml(item.titulo)}</strong><small>Lembrete${item.valor !== null ? ` · ${brl(item.valor)}` : ""}</small></div><button class="mini-button" type="button" data-toggle-reminder="${item.id}">Concluir</button></article>`),
    ];
    container.innerHTML = items.length || extra.length
      ? `${items.map((item) => transactionRow(item, true)).join("")}${extra.join("")}`
      : emptyState("▦", "Dia sem lançamentos", "Use “Novo lançamento” para registrar uma movimentação.");
  }

  function renderCalendars() {
    const overview = $("[data-overview-calendar]");
    const full = $("[data-full-calendar]");
    if (overview) overview.innerHTML = calendarMarkup(state.month, state.selectedDate);
    if (full) full.innerHTML = calendarMarkup(state.month, state.selectedDate);
    const label = $("[data-calendar-month-label]");
    if (label) label.textContent = monthLabel(state.month);
    renderCalendarDay(state.selectedDate);
  }

  function renderDonut(expenses, total) {
    const donut = $("[data-category-donut]");
    const legend = $("[data-donut-legend]");
    if (!donut || !legend) return;
    $("[data-donut-total]").textContent = brl(total);
    if (!expenses.length || total <= 0) {
      donut.style.background = "conic-gradient(var(--border-strong) 0 100%)";
      legend.innerHTML = '<p class="fc-copy">As categorias aparecerão após o primeiro gasto.</p>';
      return;
    }
    let cursor = 0;
    const segments = expenses.slice(0, 7).map((item) => {
      const start = cursor;
      cursor += (item.value / total) * 100;
      return `${safeColor(item.color)} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`;
    });
    donut.style.background = `conic-gradient(${segments.join(",")})`;
    legend.innerHTML = expenses.slice(0, 7).map((item) => `
      <div class="flow-row">
        <span style="--row-color:${safeColor(item.color)}">${escapeHtml(item.name)}</span>
        <strong>${((item.value / total) * 100).toFixed(1)}%</strong>
      </div>`).join("");
  }

  function renderOverview() {
    const items = periodTransactions();
    const totals = renderSummary(items);
    const incomes = groupedTotals(items, "receita");
    $("[data-period-label]").textContent = periodDescription();
    $$("[data-period]").forEach((button) => button.classList.toggle("is-active", button.dataset.period === state.period));
    $("[data-flow-income-total]").textContent = brl(totals.income);
    $("[data-flow-expense-total]").textContent = brl(totals.expense);
    $("[data-income-flow]").innerHTML = flowMarkup(incomes, "As entradas aparecerão aqui.");
    $("[data-expense-flow]").innerHTML = flowMarkup(totals.expenses, "Os gastos aparecerão aqui.");

    const goalSaved = state.goals.reduce((sum, goal) => sum + Number(goal.valor_atual || 0), 0);
    const bankTotal = state.accounts.filter((item) => item.account_type === "bank").reduce((sum, item) => sum + Number(item.valor || 0), 0);
    const investmentTotal = state.accounts.filter((item) => item.account_type === "investment").reduce((sum, item) => sum + Number(item.valor || 0), 0);
    const visibleBalance = bankTotal || Math.max(0, totals.balance);
    const wealthTotal = visibleBalance + investmentTotal + goalSaved;
    $("[data-flow-wealth-total]").textContent = brl(wealthTotal);
    $("[data-wealth-flow]").innerHTML = flowMarkup([
      { name: "Bancos", value: visibleBalance, color: "#4C8DFF" },
      { name: "Investimentos", value: investmentTotal, color: "#19A974" },
      { name: "Alocado em caixinhas", value: goalSaved, color: "#7868D8" },
    ], "Seu patrimônio aparecerá aqui.");
    const plannedRemaining = state.budgetStatus.reduce(
      (sum, item) => sum + Math.max(0, Number(item.limite || 0) - Number(item.gasto || 0)),
      0
    );
    $("[data-planned-remaining]").textContent = brl(plannedRemaining);
    $("[data-calendar-expense-total]").textContent = brl(
      state.transactions.filter((item) => item.tipo === "despesa").reduce((sum, item) => sum + Number(item.valor), 0)
    );
    renderCalendars();
    renderDonut(totals.expenses, totals.expense);
  }

  function filteredTransactions() {
    const search = ($("[data-transaction-search]")?.value || "").trim().toLocaleLowerCase("pt-BR");
    const type = $("[data-transaction-type-filter]")?.value || "";
    return state.transactions.filter((item) =>
      (!type || item.tipo === type) &&
      (!search || item.descricao.toLocaleLowerCase("pt-BR").includes(search) ||
        (categoryById(item.category_id)?.nome || "").toLocaleLowerCase("pt-BR").includes(search))
    );
  }

  function renderDiary() {
    const items = filteredTransactions();
    $("[data-diary-count]").textContent = `${items.length} ${items.length === 1 ? "lançamento" : "lançamentos"}`;
    $("[data-all-transactions]").innerHTML = items.length
      ? items.map((item) => transactionRow(item, true)).join("")
      : emptyState("⌕", "Nada encontrado", "Ajuste os filtros ou registre um novo lançamento.", '<button class="secondary-button" type="button" data-new-transaction>Novo lançamento</button>');
  }

  function renderCards() {
    const card = state.cardSummary || {
      total_liquido: 0, total_estornos: 0, quantidade: 0, ticket_medio: 0,
      maior_compra: 0, categorias: [], estabelecimentos: [], parcelas: [], historico: [],
    };
    $("[data-card-total]").textContent = brl(card.total_liquido);
    $("[data-card-count]").textContent = `${card.quantidade || 0} ${(card.quantidade || 0) === 1 ? "lançamento" : "lançamentos"}`;
    $("[data-card-average]").textContent = brl(card.ticket_medio);
    $("[data-card-largest]").textContent = brl(card.maior_compra);
    $("[data-card-refunds]").textContent = brl(card.total_estornos);

    $("[data-card-categories]").innerHTML = card.categorias?.length
      ? card.categorias.map((item) => `
          <div class="category-line">
            <div class="category-line-head"><span>${escapeHtml(item.icone || "💳")} ${escapeHtml(item.nome)}</span><strong>${brl(item.valor)}</strong></div>
            <div class="progress-track"><div class="progress-fill" style="--progress:${Math.min(100, Number(item.percentual || 0))}%;--progress-color:${safeColor(item.cor)}"></div></div>
          </div>`).join("")
      : emptyState("▰", "Nenhuma compra no cartão", "Importe uma fatura ou registre um gasto com a forma de pagamento “Cartão de crédito”.");

    const historyMax = Math.max(1, ...(card.historico || []).map((item) => Math.max(0, Number(item.valor))));
    $("[data-card-history]").innerHTML = card.historico?.length
      ? card.historico.map((item) => {
          const height = Math.max(3, Math.max(0, Number(item.valor)) * 100 / historyMax);
          return `<div class="history-column">
            <div class="history-bar-wrap"><div class="history-bar" style="--bar-height:${height}%" data-value="${escapeHtml(brl(item.valor))}"></div></div>
            <small>${escapeHtml(item.rotulo)}</small>
          </div>`;
        }).join("")
      : emptyState("▥", "Histórico em construção", "Os próximos meses aparecerão aqui.");

    $("[data-card-merchants]").innerHTML = card.estabelecimentos?.length
      ? card.estabelecimentos.map((item) => `<div class="merchant-row"><span>${escapeHtml(item.nome)}</span><strong>${brl(item.valor)}</strong></div>`).join("")
      : emptyState("⌂", "Sem estabelecimentos", "As maiores compras aparecerão aqui.");

    $("[data-card-installments]").innerHTML = card.parcelas?.length
      ? card.parcelas.map((item) => `<div class="installment-row">
          <div><strong>${escapeHtml(item.descricao)}</strong><small>Parcela ${item.atual} de ${item.total} · faltam ${item.restantes}</small></div>
          <strong>${brl(item.valor)}</strong>
        </div>`).join("")
      : emptyState("↻", "Nenhuma parcela identificada", "Descrições como “2/10” serão reconhecidas automaticamente.");
  }

  function accountMeta(account) {
    if (account.account_type === "credit_card") {
      const dates = [
        account.dia_fechamento ? `fecha dia ${account.dia_fechamento}` : "",
        account.dia_vencimento ? `vence dia ${account.dia_vencimento}` : "",
      ].filter(Boolean).join(" · ");
      return { icon: "▰", label: "Cartão de crédito", valueLabel: "Fatura atual", details: dates };
    }
    if (account.account_type === "investment") {
      return { icon: "↗", label: account.subtipo || "Investimento", valueLabel: "Valor atual", details: "" };
    }
    return { icon: "▣", label: account.subtipo || "Conta bancária", valueLabel: "Saldo atual", details: "" };
  }

  function renderAccounts() {
    const banks = state.accounts.filter((item) => item.account_type === "bank");
    const cards = state.accounts.filter((item) => item.account_type === "credit_card");
    const investments = state.accounts.filter((item) => item.account_type === "investment");
    const bankTotal = banks.reduce((sum, item) => sum + Number(item.valor || 0), 0);
    const investmentTotal = investments.reduce((sum, item) => sum + Number(item.valor || 0), 0);
    const cardTotal = cards.reduce((sum, item) => sum + Number(item.valor || 0), 0);
    $("[data-account-summary]").innerHTML = `
      <article><span>Em contas</span><strong>${brl(bankTotal)}</strong></article>
      <article><span>Investimentos</span><strong style="color:var(--green)">${brl(investmentTotal)}</strong></article>
      <article><span>Faturas atuais</span><strong style="color:var(--red)">${brl(cardTotal)}</strong></article>`;

    $$("[data-account-tab]").forEach((button) => button.classList.toggle("is-active", button.dataset.accountTab === state.accountTab));
    const visible = state.accountTab === "all"
      ? state.accounts
      : state.accounts.filter((item) => item.account_type === state.accountTab);
    $("[data-accounts]").innerHTML = visible.length
      ? visible.map((account) => {
          const meta = accountMeta(account);
          return `<article class="account-card" style="--account-color:${safeColor(account.cor)}">
            <div class="account-card-head">
              <div class="account-identity">
                <span class="account-icon">${meta.icon}</span>
                <div><strong>${escapeHtml(account.nome)}</strong><small>${escapeHtml(account.instituicao || meta.label)}</small></div>
              </div>
              <div class="card-actions">
                <button class="mini-button" type="button" data-edit-account="${account.id}">Editar</button>
                <button class="mini-button mini-button--danger" type="button" data-delete-account="${account.id}">Excluir</button>
              </div>
            </div>
            <div class="account-balance">
              <small>${meta.valueLabel}</small>
              <strong>${brl(account.valor)}</strong>
              ${account.limite !== null && account.limite !== undefined ? `<small>Limite ${brl(account.limite)}</small>` : ""}
              ${meta.details ? `<small>${escapeHtml(meta.details)}</small>` : ""}
            </div>
          </article>`;
        }).join("")
      : emptyState("▣", "Nenhuma conta cadastrada", "Adicione banco, cartão ou investimento para enxergar seu patrimônio.", '<button class="secondary-button" type="button" data-new-account>Adicionar conta</button>');
  }

  function renderPlanning() {
    $$("[data-planning-tab]").forEach((button) => button.classList.toggle("is-active", button.dataset.planningTab === state.planningTab));
    $$("[data-planning-section]").forEach((section) => {
      section.hidden = section.dataset.planningSection !== state.planningTab;
    });
    const primary = $("[data-planning-primary]");
    if (primary) {
      primary.textContent = state.planningTab === "scheduled"
        ? "＋ Nova previsão"
        : state.planningTab === "purchases"
          ? "＋ Planejar compra"
          : "＋ Novo orçamento";
    }

    const activeExpenses = state.scheduledExpenses.filter((item) => item.ativo);
    const carried = activeExpenses.filter((item) => item.levado_de_outro_mes);
    const scheduledTotal = activeExpenses.reduce((sum, item) => sum + Number(item.valor || 0), 0);
    $("[data-scheduled-summary]").innerHTML = `
      <article><span>Pendências</span><strong>${activeExpenses.length}</strong></article>
      <article><span>Total previsto</span><strong>${brl(scheduledTotal)}</strong></article>
      <article><span>Levado de outro mês</span><strong>${carried.length}</strong></article>`;
    $("[data-scheduled-expenses]").innerHTML = activeExpenses.length
      ? activeExpenses.map((item) => {
          const category = categoryById(item.category_id);
          const overdue = item.atrasado;
          return `<article class="planned-row ${overdue ? "is-overdue" : ""}">
            <button class="planned-check" type="button" data-pay-scheduled="${item.id}" title="Marcar como pago e enviar ao Diário">✓</button>
            <div class="planned-copy">
              <strong>${escapeHtml(item.titulo)}</strong>
              <small>${escapeHtml(category?.nome || "Sem categoria")} · ${item.recorrencia === "mensal" ? "Repete todo mês" : "Uma vez"}${item.notas ? ` · ${escapeHtml(item.notas)}` : ""}</small>
              <span class="due-badge ${overdue ? "is-overdue" : ""}">${item.levado_de_outro_mes ? "De outro mês · " : ""}${overdue ? "Atrasado · " : ""}vence ${escapeHtml(formatDate(item.data_vencimento))}</span>
            </div>
            <strong class="planned-value">${brl(item.valor)}</strong>
            <div class="card-actions">
              <button class="mini-button" type="button" data-edit-scheduled="${item.id}">Editar</button>
              <button class="mini-button mini-button--danger" type="button" data-delete-scheduled="${item.id}">Excluir</button>
            </div>
          </article>`;
        }).join("")
      : emptyState("▤", "Nenhuma despesa prevista", "Cadastre aluguel, internet, assinaturas e outros vencimentos.", '<button class="secondary-button" type="button" data-new-scheduled>Nova previsão</button>');

    const openPurchases = state.purchasePlans.filter((item) => item.status !== "comprada");
    const bought = state.purchasePlans.filter((item) => item.status === "comprada");
    const purchaseTotal = openPurchases.reduce((sum, item) => sum + Number(item.valor_estimado || 0), 0);
    $("[data-purchase-summary]").innerHTML = `
      <article><span>Planejadas</span><strong>${openPurchases.length}</strong></article>
      <article><span>Valor estimado</span><strong>${brl(purchaseTotal)}</strong></article>
      <article><span>Já compradas</span><strong>${bought.length}</strong></article>`;
    $("[data-purchase-plans]").innerHTML = state.purchasePlans.length
      ? state.purchasePlans.map((item) => `<article class="purchase-card ${item.status === "comprada" ? "is-bought" : ""}">
          <div class="purchase-card-head">
            <div><span class="priority-badge priority-badge--${item.prioridade}">${escapeHtml(item.prioridade)}</span><h2 class="purchase-name">${escapeHtml(item.nome)}</h2></div>
            <div class="card-actions">
              <button class="mini-button" type="button" data-edit-purchase="${item.id}">Editar</button>
              <button class="mini-button mini-button--danger" type="button" data-delete-purchase="${item.id}">Excluir</button>
            </div>
          </div>
          <div><strong>${brl(item.valor_estimado)}</strong><small>${item.data_desejada ? `Desejado para ${escapeHtml(longDate(item.data_desejada))}` : "Sem data definida"}${item.notas ? ` · ${escapeHtml(item.notas)}` : ""}</small></div>
          <button class="${item.status === "comprada" ? "secondary-button" : "primary-button"}" type="button" data-toggle-purchase="${item.id}">${item.status === "comprada" ? "Reabrir plano" : "Marcar como comprada"}</button>
        </article>`).join("")
      : emptyState("🛒", "Nenhuma compra planejada", "Registre desejos e decisões futuras antes de gastar.", '<button class="secondary-button" type="button" data-new-purchase>Planejar compra</button>');
  }

  function renderGoals() {
    const totalTarget = state.goals.reduce((sum, item) => sum + Number(item.valor_alvo), 0);
    const totalCurrent = state.goals.reduce((sum, item) => sum + Number(item.valor_atual), 0);
    $("[data-goal-summary]").innerHTML = `
      <article class="goal-summary-card"><span>Objetivo total</span><strong>${brl(totalTarget)}</strong></article>
      <article class="goal-summary-card"><span>Já guardado</span><strong style="color:var(--green)">${brl(totalCurrent)}</strong></article>
      <article class="goal-summary-card"><span>Falta guardar</span><strong>${brl(Math.max(0, totalTarget - totalCurrent))}</strong></article>`;

    $("[data-goals]").innerHTML = state.goals.length
      ? state.goals.map((goal) => {
          const percentage = goal.valor_alvo > 0 ? Math.min(100, (goal.valor_atual / goal.valor_alvo) * 100) : 0;
          return `<article class="goal-card">
            <div class="goal-card-head">
              <div class="goal-title"><span class="goal-icon">◎</span><div><h2>${escapeHtml(goal.nome)}</h2><small>${goal.prazo ? `até ${escapeHtml(longDate(goal.prazo))}` : "sem prazo definido"}</small></div></div>
              <div class="card-actions">
                <button class="mini-button" type="button" data-edit-goal="${goal.id}">Editar</button>
                <button class="mini-button mini-button--danger" type="button" data-delete-goal="${goal.id}">Excluir</button>
              </div>
            </div>
            <div class="goal-numbers"><strong>${brl(goal.valor_atual)}</strong><span>de ${brl(goal.valor_alvo)}</span></div>
            <div class="progress-track goal-progress"><div class="progress-fill" style="--progress:${percentage}%;--progress-color:var(--blue)"></div></div>
            <p class="goal-percentage">${percentage.toFixed(0)}% concluído</p>
            <div class="goal-deposit">
              <input inputmode="decimal" placeholder="Quanto deseja guardar?" data-goal-deposit="${goal.id}">
              <button class="primary-button" type="button" data-save-goal-deposit="${goal.id}">Guardar</button>
            </div>
          </article>`;
        }).join("")
      : emptyState("◎", "Crie sua primeira caixinha", "Uma meta clara transforma planos em pequenos próximos passos.", '<button class="secondary-button" type="button" data-new-goal>Nova caixinha</button>');
  }

  function budgetStatusFor(categoryId) {
    return state.budgetStatus.find((item) => Number(item.category_id) === Number(categoryId)) || null;
  }

  function renderBudgets() {
    $("[data-budgets]").innerHTML = state.budgets.length
      ? state.budgets.map((budget) => {
          const category = categoryById(budget.category_id);
          const status = budgetStatusFor(budget.category_id) || {
            gasto: 0, limite: budget.limite, percentual: 0, dias_restantes: 0, estado: "normal",
          };
          const stateLabel = status.estado === "estourado" ? "Limite ultrapassado" : status.estado === "atencao" ? "Atenção" : "No ritmo";
          return `<article class="budget-card">
            <div class="budget-card-head">
              <div class="goal-title"><span class="transaction-icon" style="--category-soft:${safeColor(category?.cor)}1f">${escapeHtml(category?.icone || "◔")}</span><div><h2>${escapeHtml(category?.nome || "Categoria")}</h2><small>${budget.mes ? "Somente este mês" : "Repete todo mês"}</small></div></div>
              <div>
                <span class="budget-state budget-state--${status.estado}">${stateLabel}</span>
                <div class="card-actions">
                  <button class="mini-button" type="button" data-edit-budget="${budget.id}">Editar</button>
                  <button class="mini-button mini-button--danger" type="button" data-delete-budget="${budget.id}">Excluir</button>
                </div>
              </div>
            </div>
            <div class="budget-amount"><strong>${brl(status.gasto)}</strong> <span>de ${brl(budget.limite)}</span></div>
            <div class="progress-track goal-progress"><div class="progress-fill" style="--progress:${Math.min(100, Number(status.percentual || 0))}%;--progress-color:${safeColor(category?.cor)}"></div></div>
            <div class="budget-card-footer"><span>${Number(status.percentual || 0).toFixed(0)}% usado</span><span>${Math.max(0, Number(status.dias_restantes || 0))} dias restantes</span></div>
          </article>`;
        }).join("")
      : emptyState("◔", "Planeje sem complicar", "Escolha uma categoria e defina quanto pretende gastar.", '<button class="secondary-button" type="button" data-new-budget>Criar orçamento</button>');
  }

  function categoryCard(category) {
    const children = state.categories.filter((item) => Number(item.parent_id) === Number(category.id));
    return `<article class="category-manage-card">
      <span class="transaction-icon" style="--category-soft:${safeColor(category.cor)}1f">${escapeHtml(category.icone || "📦")}</span>
      <div>
        <strong>${escapeHtml(category.nome)}</strong>
        <small>${category.essencial ? "Essencial" : "Personalizada"} · ${children.length} ${children.length === 1 ? "subcategoria" : "subcategorias"}</small>
        ${children.length ? `<div class="subcategory-list">${children.map((child) => `
          <span class="subcategory-chip">${escapeHtml(child.icone || "•")} ${escapeHtml(child.nome)}
            <button type="button" data-edit-category="${child.id}" aria-label="Editar ${escapeHtml(child.nome)}">✎</button>
            <button type="button" data-delete-category="${child.id}" aria-label="Excluir ${escapeHtml(child.nome)}">×</button>
          </span>`).join("")}</div>` : ""}
      </div>
      <div class="card-actions">
        <button class="mini-button" type="button" data-edit-category="${category.id}" aria-label="Editar ${escapeHtml(category.nome)}">Editar</button>
        <button class="mini-button mini-button--danger" type="button" data-delete-category="${category.id}" aria-label="Excluir ${escapeHtml(category.nome)}">Excluir</button>
      </div>
    </article>`;
  }

  function renderCategories() {
    const expenses = state.categories.filter((item) => item.tipo === "despesa" && !item.parent_id);
    const incomes = state.categories.filter((item) => item.tipo === "receita" && !item.parent_id);
    $("[data-expense-category-count]").textContent = expenses.length;
    $("[data-income-category-count]").textContent = incomes.length;
    $("[data-expense-categories]").innerHTML = expenses.length
      ? expenses.map(categoryCard).join("")
      : emptyState("◈", "Sem categorias de despesas", "Crie sua primeira categoria.");
    $("[data-income-categories]").innerHTML = incomes.length
      ? incomes.map(categoryCard).join("")
      : emptyState("◈", "Sem categorias de entradas", "Crie sua primeira categoria.");
  }

  function renderReminders() {
    const today = isoDate(new Date());
    const pending = state.reminders.filter((item) => !item.concluido);
    const overdue = pending.filter((item) => item.data_vencimento < today);
    const total = pending.reduce((sum, item) => sum + Number(item.valor || 0), 0);
    $("[data-reminder-summary]").innerHTML = `
      <article><span>Pendentes</span><strong>${pending.length}</strong></article>
      <article><span>Atrasados</span><strong style="color:var(--red)">${overdue.length}</strong></article>
      <article><span>Valor previsto</span><strong>${brl(total)}</strong></article>`;
    $("[data-reminders]").innerHTML = state.reminders.length
      ? state.reminders.map((item) => `
        <article class="reminder-row ${item.concluido ? "is-done" : ""}">
          <button class="reminder-check" type="button" data-toggle-reminder="${item.id}" aria-label="${item.concluido ? "Reabrir" : "Concluir"} ${escapeHtml(item.titulo)}">${item.concluido ? "✓" : ""}</button>
          <div class="reminder-copy">
            <strong>${escapeHtml(item.titulo)}</strong>
            <small>${item.data_vencimento < today && !item.concluido ? "Atrasado · " : ""}${escapeHtml(longDate(item.data_vencimento))}${item.recorrente ? " · Repete todo mês" : ""}${item.notas ? ` · ${escapeHtml(item.notas)}` : ""}</small>
          </div>
          <span class="reminder-value">${item.valor === null ? "—" : brl(item.valor)}</span>
          <div class="card-actions">
            <button class="mini-button" type="button" data-edit-reminder="${item.id}">Editar</button>
            <button class="mini-button mini-button--danger" type="button" data-delete-reminder="${item.id}">Excluir</button>
          </div>
        </article>`).join("")
      : emptyState("♧", "Nenhum lembrete", "Crie um aviso para uma conta, pagamento ou compromisso.", '<button class="secondary-button" type="button" data-new-reminder>Novo lembrete</button>');
  }

  function renderAll() {
    renderOverview();
    renderDiary();
    renderCards();
    renderAccounts();
    renderCategories();
    renderGoals();
    renderBudgets();
    renderPlanning();
    renderReminders();
  }

  async function refreshData() {
    const encodedMonth = encodeURIComponent(state.month);
    const [
      transactions, summary, spending, goals, budgets, budgetStatus, cardSummary,
      reminders, accounts, scheduledExpenses, purchasePlans,
    ] = await Promise.all([
      api(`/api/transactions?mes=${encodedMonth}&ordem=data_desc&limit=500`),
      api(`/api/summary?mes=${encodedMonth}`),
      api(`/api/spending-by-category?mes=${encodedMonth}`),
      api("/api/goals"),
      api("/api/budgets"),
      api(`/api/budgets/status?mes=${encodedMonth}`),
      api(`/api/cards/summary?mes=${encodedMonth}`),
      api(`/api/reminders?mes=${encodedMonth}`),
      api("/api/accounts"),
      api(`/api/scheduled-expenses?mes=${encodedMonth}`),
      api("/api/purchase-plans"),
    ]);
    state.transactions = transactions.items || [];
    state.summary = summary;
    state.spending = spending || [];
    state.goals = goals || [];
    state.budgets = budgets || [];
    state.budgetStatus = budgetStatus || [];
    state.cardSummary = cardSummary || null;
    state.reminders = reminders || [];
    state.accounts = accounts || [];
    state.scheduledExpenses = scheduledExpenses || [];
    state.purchasePlans = purchasePlans || [];
    renderAll();
  }

  function clearCardFile() {
    state.cardFile = null;
    state.cardPreview = null;
    const input = $("[data-card-file-input]");
    if (input) input.value = "";
    $("[data-card-selected]").hidden = true;
    $("[data-card-preview]").hidden = true;
  }

  function renderCardPreview(preview) {
    state.cardPreview = preview;
    $("[data-card-preview-count]").textContent = preview.quantidade;
    $("[data-card-preview-total]").textContent = brl(preview.total_liquido);
    $("[data-card-preview-warning]").textContent = preview.aviso || "";
    $("[data-card-preview-items]").innerHTML = preview.items.map((item) => `
      <article class="invoice-preview-row ${item.tipo === "receita" ? "is-refund" : ""}">
        <time>${escapeHtml(formatDate(item.data))}</time>
        <div>
          <strong>${escapeHtml(item.descricao)}</strong>
          <small>${escapeHtml(item.categoria_sugerida)}${item.parcela ? ` · ${item.parcela.atual}/${item.parcela.total}` : ""}</small>
        </div>
        <span>${item.tipo === "receita" ? "−" : ""}${brl(item.valor)}</span>
      </article>`).join("");
    $("[data-card-preview]").hidden = false;
  }

  async function previewCardFile(file) {
    if (!file) return;
    state.cardFile = file;
    state.cardPreview = null;
    $("[data-card-filename]").textContent = file.name;
    $("[data-card-filesize]").textContent = `${(file.size / 1024).toFixed(0)} KB · preparando prévia…`;
    $("[data-card-selected]").hidden = false;
    $("[data-card-preview]").hidden = true;
    try {
      const preview = await upload("/api/import/card/preview", file);
      $("[data-card-filesize]").textContent = `${(file.size / 1024).toFixed(0)} KB · ${preview.formato}`;
      renderCardPreview(preview);
    } catch (error) {
      clearCardFile();
      toast(error.message, "error");
    }
  }

  async function importCardFile(button) {
    if (!state.cardFile || !state.cardPreview) return toast("Escolha e confira uma fatura primeiro.", "error");
    setButtonBusy(button, true, "Importando…");
    try {
      const result = await upload("/api/import/card", state.cardFile);
      clearCardFile();
      await refreshData();
      toast(
        result.importadas
          ? `${result.importadas} compras adicionadas ao diário.`
          : "Esta fatura já estava importada. Nenhuma compra foi duplicada."
      );
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonBusy(button, false);
    }
  }

  function openTransaction(transaction = null) {
    const modal = $("[data-transaction-modal]");
    const form = $("[data-transaction-form]");
    form.reset();
    form.elements.id.value = transaction?.id || "";
    form.elements.tipo.value = transaction?.tipo || "despesa";
    form.elements.data.value = transaction?.data || new Date().toISOString().slice(0, 10);
    form.elements.descricao.value = transaction?.descricao || "";
    form.elements.valor.value = transaction ? formatNumber(transaction.valor) : "";
    const directCategory = categoryById(transaction?.category_id);
    const parentId = directCategory?.parent_id || directCategory?.id || "";
    const childId = directCategory?.parent_id ? directCategory.id : "";
    form.elements.category_id.innerHTML = categoryOptions(form.elements.tipo.value, parentId);
    form.elements.subcategory_id.innerHTML = subcategoryOptions(parentId, childId);
    $("[data-subcategory-field]").hidden = !state.categories.some((item) => Number(item.parent_id) === Number(parentId));
    form.elements.metodo_pagamento.value = transaction?.metodo_pagamento || "";
    form.elements.recorrente.checked = Boolean(transaction?.recorrente);
    form.elements.notas.value = transaction?.notas || "";
    $("[data-transaction-modal-title]").textContent = transaction ? "Editar lançamento" : "Novo lançamento";
    $("[data-calculator]").hidden = true;
    resetCalculator(transaction?.valor || 0);
    modal.showModal();
    setTimeout(() => form.elements.descricao.focus(), 50);
  }

  function openGoal(goal = null) {
    const form = $("[data-goal-form]");
    form.reset();
    form.elements.id.value = goal?.id || "";
    form.elements.nome.value = goal?.nome || "";
    form.elements.valor_alvo.value = goal ? formatNumber(goal.valor_alvo) : "";
    form.elements.valor_atual.value = goal ? formatNumber(goal.valor_atual) : "";
    form.elements.prazo.value = goal?.prazo || "";
    $("[data-goal-modal-title]").textContent = goal ? "Editar caixinha" : "Nova meta";
    $("[data-goal-modal]").showModal();
  }

  function openBudget(budget = null) {
    const form = $("[data-budget-form]");
    form.reset();
    form.elements.id.value = budget?.id || "";
    form.elements.category_id.innerHTML = budgetCategoryOptions(budget?.category_id);
    form.elements.limite.value = budget ? formatNumber(budget.limite) : "";
    form.elements.recorrente.checked = budget ? !budget.mes : true;
    $("[data-budget-modal-title]").textContent = budget ? "Editar orçamento" : "Novo orçamento";
    $("[data-budget-modal]").showModal();
  }

  function selectCategoryIcon(icon) {
    const form = $("[data-category-form]");
    form.elements.icone.value = icon || "📦";
    $$("[data-category-icon]", form).forEach((button) => {
      button.classList.toggle("is-selected", button.dataset.categoryIcon === form.elements.icone.value);
    });
  }

  function openCategory(category = null) {
    const form = $("[data-category-form]");
    form.reset();
    form.elements.id.value = category?.id || "";
    form.elements.nome.value = category?.nome || "";
    form.elements.tipo.value = category?.tipo || "despesa";
    form.elements.parent_id.innerHTML = parentCategoryOptions(form.elements.tipo.value, category?.parent_id, category?.id);
    form.elements.cor.value = safeColor(category?.cor || "#7046d9");
    form.elements.essencial.checked = Boolean(category?.essencial);
    $("[data-category-color-label]").textContent = form.elements.cor.value.toUpperCase();
    selectCategoryIcon(category?.icone || "📦");
    $("[data-category-modal-title]").textContent = category ? "Editar categoria" : "Nova categoria";
    $("[data-category-modal]").showModal();
    setTimeout(() => form.elements.nome.focus(), 50);
  }

  function updateAccountFields() {
    const form = $("[data-account-form]");
    const isCard = form.elements.account_type.value === "credit_card";
    $("[data-account-limit-field]").hidden = !isCard;
    $("[data-account-card-days]").hidden = !isCard;
    $("[data-account-value-label]").childNodes[0].textContent = isCard ? "Fatura atual " : form.elements.account_type.value === "investment" ? "Valor atual " : "Saldo atual ";
  }

  function openAccount(account = null) {
    const form = $("[data-account-form]");
    form.reset();
    form.elements.id.value = account?.id || "";
    form.elements.account_type.value = account?.account_type || "bank";
    form.elements.account_type.disabled = Boolean(account);
    form.elements.nome.value = account?.nome || "";
    form.elements.instituicao.value = account?.instituicao || "";
    form.elements.valor.value = account ? formatNumber(account.valor) : "";
    form.elements.limite.value = account?.limite !== null && account?.limite !== undefined ? formatNumber(account.limite) : "";
    form.elements.dia_fechamento.value = account?.dia_fechamento || "";
    form.elements.dia_vencimento.value = account?.dia_vencimento || "";
    form.elements.subtipo.value = account?.subtipo || "";
    form.elements.cor.value = safeColor(account?.cor || "#7046d9");
    updateAccountFields();
    $("[data-account-modal-title]").textContent = account ? "Editar conta" : "Nova conta";
    $("[data-account-modal]").showModal();
    setTimeout(() => form.elements.nome.focus(), 50);
  }

  function openScheduled(expense = null) {
    const form = $("[data-scheduled-form]");
    form.reset();
    form.elements.id.value = expense?.id || "";
    form.elements.titulo.value = expense?.titulo || "";
    form.elements.valor.value = expense ? formatNumber(expense.valor) : "";
    form.elements.data_vencimento.value = expense?.data_vencimento || state.selectedDate;
    form.elements.category_id.innerHTML = categoryOptions("despesa", expense?.category_id);
    form.elements.recorrencia.value = expense?.recorrencia || "mensal";
    form.elements.notas.value = expense?.notas || "";
    $("[data-scheduled-modal-title]").textContent = expense ? "Editar previsão" : "Nova previsão";
    $("[data-scheduled-modal]").showModal();
    setTimeout(() => form.elements.titulo.focus(), 50);
  }

  function openPurchase(plan = null) {
    const form = $("[data-purchase-form]");
    form.reset();
    form.elements.id.value = plan?.id || "";
    form.elements.nome.value = plan?.nome || "";
    form.elements.valor_estimado.value = plan ? formatNumber(plan.valor_estimado) : "";
    form.elements.prioridade.value = plan?.prioridade || "media";
    form.elements.data_desejada.value = plan?.data_desejada || "";
    form.elements.notas.value = plan?.notas || "";
    $("[data-purchase-modal-title]").textContent = plan ? "Editar compra" : "Planejar compra";
    $("[data-purchase-modal]").showModal();
    setTimeout(() => form.elements.nome.focus(), 50);
  }

  function openReminder(reminder = null) {
    const form = $("[data-reminder-form]");
    form.reset();
    form.elements.id.value = reminder?.id || "";
    form.elements.titulo.value = reminder?.titulo || "";
    form.elements.data_vencimento.value = reminder?.data_vencimento || state.selectedDate;
    form.elements.valor.value = reminder?.valor !== null && reminder?.valor !== undefined ? formatNumber(reminder.valor) : "";
    form.elements.notas.value = reminder?.notas || "";
    form.elements.recorrente.checked = Boolean(reminder?.recorrente);
    $("[data-reminder-modal-title]").textContent = reminder ? "Editar lembrete" : "Novo lembrete";
    $("[data-reminder-modal]").showModal();
    setTimeout(() => form.elements.titulo.focus(), 50);
  }

  function setButtonBusy(button, busy, label = "") {
    if (!button) return;
    if (busy) {
      button.dataset.originalText = button.textContent;
      button.disabled = true;
      button.textContent = label || "Salvando…";
    } else {
      button.disabled = false;
      button.textContent = button.dataset.originalText || button.textContent;
    }
  }

  async function submitTransaction(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = $('button[type="submit"]', form);
    const id = form.elements.id.value;
    const value = parseMoney(form.elements.valor.value);
    if (value <= 0) {
      toast("Digite um valor maior que zero.", "error");
      form.elements.valor.focus();
      return;
    }
    const payload = {
      tipo: form.elements.tipo.value,
      data: form.elements.data.value,
      descricao: form.elements.descricao.value.trim(),
      valor: value,
      category_id: form.elements.subcategory_id.value
        ? Number(form.elements.subcategory_id.value)
        : form.elements.category_id.value
          ? Number(form.elements.category_id.value)
          : null,
      metodo_pagamento: form.elements.metodo_pagamento.value || null,
      recorrente: form.elements.recorrente.checked,
      notas: form.elements.notas.value.trim() || null,
    };
    setButtonBusy(button, true);
    try {
      await api(id ? `/api/transactions/${id}` : "/api/transactions", {
        method: id ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      $("[data-transaction-modal]").close();
      await refreshData();
      toast(id ? "Lançamento atualizado." : "Lançamento salvo no diário.");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonBusy(button, false);
    }
  }

  async function submitGoal(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = $('button[type="submit"]', form);
    const id = form.elements.id.value;
    const payload = {
      nome: form.elements.nome.value.trim(),
      valor_alvo: parseMoney(form.elements.valor_alvo.value),
      valor_atual: parseMoney(form.elements.valor_atual.value),
      prazo: form.elements.prazo.value || null,
    };
    if (payload.valor_alvo <= 0) return toast("O objetivo precisa ser maior que zero.", "error");
    setButtonBusy(button, true);
    try {
      await api(id ? `/api/goals/${id}` : "/api/goals", { method: id ? "PATCH" : "POST", body: JSON.stringify(payload) });
      $("[data-goal-modal]").close();
      await refreshData();
      toast(id ? "Caixinha atualizada." : "Caixinha criada.");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonBusy(button, false);
    }
  }

  async function submitBudget(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = $('button[type="submit"]', form);
    const id = form.elements.id.value;
    const limit = parseMoney(form.elements.limite.value);
    if (limit <= 0) return toast("O limite precisa ser maior que zero.", "error");
    const payload = {
      category_id: Number(form.elements.category_id.value),
      limite: limit,
      mes: form.elements.recorrente.checked ? null : state.month,
    };
    setButtonBusy(button, true);
    try {
      await api(id ? `/api/budgets/${id}` : "/api/budgets", { method: id ? "PATCH" : "POST", body: JSON.stringify(payload) });
      $("[data-budget-modal]").close();
      await refreshData();
      toast(id ? "Orçamento atualizado." : "Orçamento criado.");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonBusy(button, false);
    }
  }

  async function submitCategory(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = $('button[type="submit"]', form);
    const id = form.elements.id.value;
    const payload = {
      nome: form.elements.nome.value.trim(),
      tipo: form.elements.tipo.value,
      parent_id: form.elements.parent_id.value ? Number(form.elements.parent_id.value) : null,
      cor: form.elements.cor.value,
      icone: form.elements.icone.value || "📦",
      essencial: form.elements.essencial.checked,
    };
    setButtonBusy(button, true);
    try {
      await api(id ? `/api/categories/${id}` : "/api/categories", {
        method: id ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      $("[data-category-modal]").close();
      state.categories = await api("/api/categories");
      await refreshData();
      toast(id ? "Categoria atualizada." : "Categoria criada.");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonBusy(button, false);
    }
  }

  async function submitReminder(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = $('button[type="submit"]', form);
    const id = form.elements.id.value;
    const parsedValue = parseMoney(form.elements.valor.value);
    const payload = {
      titulo: form.elements.titulo.value.trim(),
      data_vencimento: form.elements.data_vencimento.value,
      valor: form.elements.valor.value.trim() ? parsedValue : null,
      recorrente: form.elements.recorrente.checked,
      notas: form.elements.notas.value.trim() || null,
    };
    setButtonBusy(button, true);
    try {
      await api(id ? `/api/reminders/${id}` : "/api/reminders", {
        method: id ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      $("[data-reminder-modal]").close();
      await refreshData();
      toast(id ? "Lembrete atualizado." : "Lembrete criado.");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonBusy(button, false);
    }
  }

  async function submitAccount(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = $('button[type="submit"]', form);
    const id = form.elements.id.value;
    const payload = {
      nome: form.elements.nome.value.trim(),
      instituicao: form.elements.instituicao.value.trim(),
      valor: parseMoney(form.elements.valor.value),
      limite: form.elements.limite.value.trim() ? parseMoney(form.elements.limite.value) : null,
      dia_fechamento: form.elements.dia_fechamento.value ? Number(form.elements.dia_fechamento.value) : null,
      dia_vencimento: form.elements.dia_vencimento.value ? Number(form.elements.dia_vencimento.value) : null,
      subtipo: form.elements.subtipo.value.trim(),
      cor: form.elements.cor.value,
    };
    if (!id) payload.account_type = form.elements.account_type.value;
    if (form.elements.account_type.value !== "credit_card") {
      payload.limite = null;
      payload.dia_fechamento = null;
      payload.dia_vencimento = null;
    }
    setButtonBusy(button, true);
    try {
      await api(id ? `/api/accounts/${id}` : "/api/accounts", {
        method: id ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      $("[data-account-modal]").close();
      await refreshData();
      toast(id ? "Conta atualizada." : "Conta adicionada.");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonBusy(button, false);
    }
  }

  async function submitScheduled(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = $('button[type="submit"]', form);
    const id = form.elements.id.value;
    const payload = {
      titulo: form.elements.titulo.value.trim(),
      valor: parseMoney(form.elements.valor.value),
      category_id: form.elements.category_id.value ? Number(form.elements.category_id.value) : null,
      data_vencimento: form.elements.data_vencimento.value,
      recorrencia: form.elements.recorrencia.value,
      notas: form.elements.notas.value.trim() || null,
    };
    if (payload.valor <= 0) return toast("O valor previsto precisa ser maior que zero.", "error");
    setButtonBusy(button, true);
    try {
      await api(id ? `/api/scheduled-expenses/${id}` : "/api/scheduled-expenses", {
        method: id ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      $("[data-scheduled-modal]").close();
      await refreshData();
      toast(id ? "Previsão atualizada." : "Despesa prevista criada.");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonBusy(button, false);
    }
  }

  async function submitPurchase(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = $('button[type="submit"]', form);
    const id = form.elements.id.value;
    const payload = {
      nome: form.elements.nome.value.trim(),
      valor_estimado: parseMoney(form.elements.valor_estimado.value),
      prioridade: form.elements.prioridade.value,
      data_desejada: form.elements.data_desejada.value || null,
      notas: form.elements.notas.value.trim() || null,
    };
    setButtonBusy(button, true);
    try {
      await api(id ? `/api/purchase-plans/${id}` : "/api/purchase-plans", {
        method: id ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      $("[data-purchase-modal]").close();
      await refreshData();
      toast(id ? "Compra atualizada." : "Compra planejada.");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonBusy(button, false);
    }
  }

  async function payScheduled(id, button) {
    if (!confirm("Marcar esta previsão como paga e criar o gasto no Diário?")) return;
    setButtonBusy(button, true, "…");
    try {
      await api(`/api/scheduled-expenses/${id}/pay`, {
        method: "POST",
        body: JSON.stringify({ data_pagamento: isoDate(new Date()), metodo_pagamento: "outro" }),
      });
      await refreshData();
      toast("Pagamento registrado no Diário.");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonBusy(button, false);
    }
  }

  async function togglePurchase(id) {
    const plan = state.purchasePlans.find((item) => Number(item.id) === Number(id));
    if (!plan) return;
    try {
      await api(`/api/purchase-plans/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: plan.status === "comprada" ? "planejada" : "comprada" }),
      });
      await refreshData();
      toast(plan.status === "comprada" ? "Compra voltou ao planejamento." : "Compra marcada como realizada.");
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function toggleReminder(id) {
    const reminder = state.reminders.find((item) => Number(item.id) === Number(id));
    if (!reminder) return;
    try {
      await api(`/api/reminders/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ concluido: !reminder.concluido }),
      });
      await refreshData();
      toast(reminder.concluido ? "Lembrete reaberto." : "Lembrete concluído.");
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function removeItem(kind, id, label) {
    if (!confirm(`Excluir ${label}? Essa ação não pode ser desfeita.`)) return;
    const endpoints = {
      transaction: "transactions",
      goal: "goals",
      budget: "budgets",
      category: "categories",
      reminder: "reminders",
      account: "accounts",
      scheduled: "scheduled-expenses",
      purchase: "purchase-plans",
    };
    try {
      await api(`/api/${endpoints[kind]}/${id}`, { method: "DELETE" });
      if (kind === "category") state.categories = await api("/api/categories");
      await refreshData();
      toast("Item excluído.");
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function saveGoalDeposit(id, button) {
    const goal = state.goals.find((item) => Number(item.id) === Number(id));
    const input = $(`[data-goal-deposit="${id}"]`);
    const value = parseMoney(input?.value);
    if (!goal || value <= 0) return toast("Digite quanto deseja guardar.", "error");
    setButtonBusy(button, true, "Guardando…");
    try {
      await api(`/api/goals/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ valor_atual: Math.round((Number(goal.valor_atual) + value) * 100) / 100 }),
      });
      await refreshData();
      toast(`${brl(value)} guardados em “${goal.nome}”.`);
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setButtonBusy(button, false);
    }
  }

  async function setDisplayedMonth(month) {
    state.month = month;
    $("[data-month]").value = month;
    await refreshData();
  }

  async function shiftMonth(offset) {
    const [year, month] = state.month.split("-").map(Number);
    const target = new Date(year, month - 1 + offset, 1);
    state.selectedDate = `${isoDate(target).slice(0, 8)}01`;
    await setDisplayedMonth(isoDate(target).slice(0, 7));
  }

  async function shiftPeriod(offset) {
    if (state.period === "month") {
      await shiftMonth(offset);
      return;
    }
    const target = dateFromIso(state.selectedDate);
    target.setDate(target.getDate() + offset * (state.period === "week" ? 7 : 1));
    state.selectedDate = isoDate(target);
    const nextMonth = state.selectedDate.slice(0, 7);
    if (nextMonth !== state.month) await setDisplayedMonth(nextMonth);
    else renderOverview();
  }

  async function selectCalendarDate(date) {
    state.selectedDate = date;
    renderCalendars();
    renderCalendarDay(date);
    if (state.page === "overview") {
      state.period = "day";
      renderOverview();
    }
  }

  const calculator = { display: "0", accumulator: null, operator: null, waiting: false };

  function calcNumber() {
    return Number(calculator.display.replace(",", ".")) || 0;
  }

  function resetCalculator(value = 0) {
    calculator.display = Number(value || 0) ? String(Number(value)).replace(".", ",") : "0";
    calculator.accumulator = null;
    calculator.operator = null;
    calculator.waiting = false;
    updateCalculator();
  }

  function updateCalculator() {
    const display = $("[data-calculator-display]");
    const memory = $("[data-calculator-memory]");
    if (!display || !memory) return;
    display.textContent = calculator.display;
    memory.textContent = calculator.operator !== null ? `${String(calculator.accumulator).replace(".", ",")} ${calculator.operator}` : "Calculadora";
  }

  function calculate(a, operator, b) {
    if (operator === "+") return a + b;
    if (operator === "−") return a - b;
    if (operator === "×") return a * b;
    if (operator === "÷") return b === 0 ? a : a / b;
    return b;
  }

  function calcKey(key) {
    if (/^\d$/.test(key)) {
      calculator.display = calculator.waiting || calculator.display === "0" ? key : `${calculator.display}${key}`;
      calculator.waiting = false;
    } else if (key === "decimal" && !calculator.display.includes(",")) {
      calculator.display = calculator.waiting ? "0," : `${calculator.display},`;
      calculator.waiting = false;
    } else if (key === "clear") {
      resetCalculator();
      return;
    } else if (key === "back") {
      calculator.display = calculator.display.length > 1 ? calculator.display.slice(0, -1) : "0";
    } else if (key === "percent") {
      calculator.display = String(Math.round((calcNumber() / 100) * 100000000) / 100000000).replace(".", ",");
    } else if (key === "equals" && calculator.operator !== null) {
      const result = calculate(Number(calculator.accumulator), calculator.operator, calcNumber());
      calculator.display = String(Math.round(result * 100000000) / 100000000).replace(".", ",");
      calculator.accumulator = null;
      calculator.operator = null;
      calculator.waiting = true;
    }
    updateCalculator();
  }

  function calcOperator(operator) {
    const value = calcNumber();
    if (calculator.operator !== null && !calculator.waiting) {
      calculator.accumulator = calculate(Number(calculator.accumulator), calculator.operator, value);
      calculator.display = String(Math.round(calculator.accumulator * 100000000) / 100000000).replace(".", ",");
    } else {
      calculator.accumulator = value;
    }
    calculator.operator = operator;
    calculator.waiting = true;
    updateCalculator();
  }

  function bindEvents() {
    document.addEventListener("click", async (event) => {
      const pageLink = event.target.closest("[data-page-link], [data-go-page]");
      if (pageLink) setPage(pageLink.dataset.pageLink || pageLink.dataset.goPage);

      if (event.target.closest("[data-new-transaction]")) openTransaction();
      if (event.target.closest("[data-new-goal]")) openGoal();
      if (event.target.closest("[data-new-budget]")) openBudget();
      if (event.target.closest("[data-new-category]")) openCategory();
      if (event.target.closest("[data-new-reminder]")) openReminder();
      if (event.target.closest("[data-new-account]")) openAccount();
      if (event.target.closest("[data-new-scheduled]")) openScheduled();
      if (event.target.closest("[data-new-purchase]")) openPurchase();
      if (event.target.closest("[data-planning-primary]")) {
        if (state.planningTab === "scheduled") openScheduled();
        else if (state.planningTab === "purchases") openPurchase();
        else openBudget();
      }
      if (event.target.closest("[data-menu-toggle]")) openMobileMenu();
      if (event.target.closest("[data-menu-close]")) closeMobileMenu();
      if (event.target.closest("[data-select-card-file]")) $("[data-card-file-input]").click();
      if (event.target.closest("[data-card-clear]")) clearCardFile();
      const importCardButton = event.target.closest("[data-card-import-confirm]");
      if (importCardButton) await importCardFile(importCardButton);

      const editTransaction = event.target.closest("[data-edit-transaction]");
      if (editTransaction) openTransaction(state.transactions.find((item) => Number(item.id) === Number(editTransaction.dataset.editTransaction)));
      const deleteTransaction = event.target.closest("[data-delete-transaction]");
      if (deleteTransaction) await removeItem("transaction", deleteTransaction.dataset.deleteTransaction, "este lançamento");

      const editGoal = event.target.closest("[data-edit-goal]");
      if (editGoal) openGoal(state.goals.find((item) => Number(item.id) === Number(editGoal.dataset.editGoal)));
      const deleteGoal = event.target.closest("[data-delete-goal]");
      if (deleteGoal) await removeItem("goal", deleteGoal.dataset.deleteGoal, "esta caixinha");

      const editBudget = event.target.closest("[data-edit-budget]");
      if (editBudget) openBudget(state.budgets.find((item) => Number(item.id) === Number(editBudget.dataset.editBudget)));
      const deleteBudget = event.target.closest("[data-delete-budget]");
      if (deleteBudget) await removeItem("budget", deleteBudget.dataset.deleteBudget, "este orçamento");

      const editCategory = event.target.closest("[data-edit-category]");
      if (editCategory) openCategory(state.categories.find((item) => Number(item.id) === Number(editCategory.dataset.editCategory)));
      const deleteCategory = event.target.closest("[data-delete-category]");
      if (deleteCategory) await removeItem("category", deleteCategory.dataset.deleteCategory, "esta categoria");

      const editReminder = event.target.closest("[data-edit-reminder]");
      if (editReminder) openReminder(state.reminders.find((item) => Number(item.id) === Number(editReminder.dataset.editReminder)));
      const deleteReminder = event.target.closest("[data-delete-reminder]");
      if (deleteReminder) await removeItem("reminder", deleteReminder.dataset.deleteReminder, "este lembrete");
      const toggle = event.target.closest("[data-toggle-reminder]");
      if (toggle) await toggleReminder(toggle.dataset.toggleReminder);

      const editAccount = event.target.closest("[data-edit-account]");
      if (editAccount) openAccount(state.accounts.find((item) => Number(item.id) === Number(editAccount.dataset.editAccount)));
      const deleteAccount = event.target.closest("[data-delete-account]");
      if (deleteAccount) await removeItem("account", deleteAccount.dataset.deleteAccount, "esta conta");

      const editScheduled = event.target.closest("[data-edit-scheduled]");
      if (editScheduled) openScheduled(state.scheduledExpenses.find((item) => Number(item.id) === Number(editScheduled.dataset.editScheduled)));
      const deleteScheduled = event.target.closest("[data-delete-scheduled]");
      if (deleteScheduled) await removeItem("scheduled", deleteScheduled.dataset.deleteScheduled, "esta previsão");
      const pay = event.target.closest("[data-pay-scheduled]");
      if (pay) await payScheduled(pay.dataset.payScheduled, pay);

      const editPurchase = event.target.closest("[data-edit-purchase]");
      if (editPurchase) openPurchase(state.purchasePlans.find((item) => Number(item.id) === Number(editPurchase.dataset.editPurchase)));
      const deletePurchase = event.target.closest("[data-delete-purchase]");
      if (deletePurchase) await removeItem("purchase", deletePurchase.dataset.deletePurchase, "esta compra planejada");
      const togglePurchaseButton = event.target.closest("[data-toggle-purchase]");
      if (togglePurchaseButton) await togglePurchase(togglePurchaseButton.dataset.togglePurchase);

      const accountTab = event.target.closest("[data-account-tab]");
      if (accountTab) {
        state.accountTab = accountTab.dataset.accountTab;
        renderAccounts();
      }
      const planningTab = event.target.closest("[data-planning-tab]");
      if (planningTab) {
        state.planningTab = planningTab.dataset.planningTab;
        renderPlanning();
      }

      const deposit = event.target.closest("[data-save-goal-deposit]");
      if (deposit) await saveGoalDeposit(deposit.dataset.saveGoalDeposit, deposit);

      const icon = event.target.closest("[data-category-icon]");
      if (icon) selectCategoryIcon(icon.dataset.categoryIcon);

      const period = event.target.closest("[data-period]");
      if (period) {
        state.period = period.dataset.period;
        renderOverview();
      }
      if (event.target.closest("[data-period-prev]")) {
        try { await shiftPeriod(-1); } catch (error) { toast(error.message, "error"); }
      }
      if (event.target.closest("[data-period-next]")) {
        try { await shiftPeriod(1); } catch (error) { toast(error.message, "error"); }
      }
      if (event.target.closest("[data-period-today]")) {
        state.selectedDate = isoDate(new Date());
        try { await setDisplayedMonth(state.selectedDate.slice(0, 7)); } catch (error) { toast(error.message, "error"); }
      }
      if (event.target.closest("[data-calendar-prev]")) {
        try { await shiftMonth(-1); } catch (error) { toast(error.message, "error"); }
      }
      if (event.target.closest("[data-calendar-next]")) {
        try { await shiftMonth(1); } catch (error) { toast(error.message, "error"); }
      }
      const calendarDate = event.target.closest("[data-calendar-date]");
      if (calendarDate) await selectCalendarDate(calendarDate.dataset.calendarDate);

      const close = event.target.closest("[data-close-modal]");
      if (close) close.closest("dialog")?.close();

      if (event.target.closest("[data-theme-toggle]")) {
        setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
      }

      if (event.target.closest("[data-calculator-toggle]")) {
        const panel = $("[data-calculator]");
        const input = $('[name="valor"]', $("[data-transaction-form]"));
        resetCalculator(parseMoney(input.value));
        panel.hidden = !panel.hidden;
      }
      const calc = event.target.closest("[data-calc]");
      if (calc) calcKey(calc.dataset.calc);
      const operator = event.target.closest("[data-calc-op]");
      if (operator) calcOperator(operator.dataset.calcOp);
      if (event.target.closest("[data-calculator-use]")) {
        $('[name="valor"]', $("[data-transaction-form]")).value = formatNumber(calcNumber());
        $("[data-calculator]").hidden = true;
      }
    });

    $$("[data-theme-toggle]").forEach((button) => button.addEventListener("click", () => {}));
    $("[data-transaction-form]").addEventListener("submit", submitTransaction);
    $("[data-goal-form]").addEventListener("submit", submitGoal);
    $("[data-budget-form]").addEventListener("submit", submitBudget);
    $("[data-category-form]").addEventListener("submit", submitCategory);
    $("[data-reminder-form]").addEventListener("submit", submitReminder);
    $("[data-account-form]").addEventListener("submit", submitAccount);
    $("[data-scheduled-form]").addEventListener("submit", submitScheduled);
    $("[data-purchase-form]").addEventListener("submit", submitPurchase);

    $('[name="tipo"]', $("[data-transaction-form]")).addEventListener("change", (event) => {
      const select = $('[name="category_id"]', $("[data-transaction-form]"));
      select.innerHTML = categoryOptions(event.target.value);
      const childSelect = $('[name="subcategory_id"]', $("[data-transaction-form]"));
      childSelect.innerHTML = subcategoryOptions("");
      $("[data-subcategory-field]").hidden = true;
    });
    $('[name="category_id"]', $("[data-transaction-form]")).addEventListener("change", (event) => {
      const field = $("[data-subcategory-field]");
      const childSelect = $('[name="subcategory_id"]', $("[data-transaction-form]"));
      childSelect.innerHTML = subcategoryOptions(event.target.value);
      field.hidden = !state.categories.some((item) => Number(item.parent_id) === Number(event.target.value));
    });
    $('[name="tipo"]', $("[data-category-form]")).addEventListener("change", (event) => {
      const form = $("[data-category-form]");
      form.elements.parent_id.innerHTML = parentCategoryOptions(event.target.value, "", form.elements.id.value);
    });
    $('[name="account_type"]', $("[data-account-form]")).addEventListener("change", updateAccountFields);

    $("[data-month]").addEventListener("change", async (event) => {
      if (!event.target.value) return;
      state.selectedDate = `${event.target.value}-01`;
      try { await setDisplayedMonth(event.target.value); } catch (error) { toast(error.message, "error"); }
    });
    $('[name="cor"]', $("[data-category-form]")).addEventListener("input", (event) => {
      $("[data-category-color-label]").textContent = event.target.value.toUpperCase();
    });
    $("[data-transaction-search]").addEventListener("input", renderDiary);
    $("[data-transaction-type-filter]").addEventListener("change", renderDiary);
    $("[data-card-file-input]").addEventListener("change", (event) => {
      previewCardFile(event.target.files?.[0]);
    });

    $("[data-logout]").addEventListener("click", async () => {
      try { await api("/api/auth/logout", { method: "POST", body: "{}" }); } catch {}
      location.href = "/entrar?mode=login";
    });

    window.addEventListener("hashchange", () => setPage(pageFromHash(), false));
    window.addEventListener("resize", () => {
      if (innerWidth > 680) closeMobileMenu();
    });
    window.addEventListener("finpilot:pluggy-synced", async () => {
      await refreshData();
      toast("Extrato bancário sincronizado.");
    });

    $$("dialog.modal").forEach((dialog) => {
      dialog.addEventListener("click", (event) => {
        const rect = dialog.getBoundingClientRect();
        const outside = event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom;
        if (event.target === dialog && outside) dialog.close();
      });
    });
  }

  async function init() {
    setTheme(document.documentElement.dataset.theme);
    $("[data-month]").value = state.month;
    bindEvents();
    setPage(pageFromHash(), false);
    try {
      const user = await api("/api/auth/me");
      setUser(user);
      await ensureCategories();
      await refreshData();
      if (window.FinPilotPluggy) window.FinPilotPluggy.mount($("[data-bank-connect]"));
    } catch (error) {
      toast(error.message, "error");
    } finally {
      $("[data-loading]").classList.add("is-done");
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
