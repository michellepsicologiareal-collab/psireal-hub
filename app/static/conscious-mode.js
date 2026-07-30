/**
 * FinPilot — Modo Consciente
 * Componente HTML/JS vanilla, responsivo e sem Node.js.
 *
 * Uso:
 *   <section data-finpilot-conscious></section>
 *   <script src="/static/conscious-mode.js"></script>
 */
(function () {
  "use strict";

  const state = {
    options: null,
    prompts: [],
    week: null,
    activePrompt: null,
  };

  const escapeHtml = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const brl = (value) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value || 0));

  const today = () => new Date().toISOString().slice(0, 10);
  const currentMonth = () => today().slice(0, 7);

  async function api(path, options) {
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options && options.headers) },
      ...options,
    });
    if (!response.ok) {
      let message = "Não foi possível concluir agora.";
      try {
        const body = await response.json();
        message = body.detail || message;
      } catch {}
      throw new Error(message);
    }
    return response.json();
  }

  function notice(root, message, type = "") {
    const element = root.querySelector("[data-conscious-notice]");
    if (!element) return;
    element.textContent = message || "";
    element.dataset.type = type;
  }

  function injectStyles() {
    if (document.getElementById("finpilot-conscious-styles")) return;
    const style = document.createElement("style");
    style.id = "finpilot-conscious-styles";
    style.textContent = `
      :root {
        --fc-bg: #f7f5fb; --fc-card: #ffffff; --fc-text: #18233a;
        --fc-muted: #65718a; --fc-border: #ddd8ea; --fc-accent: #714ad7;
        --fc-accent-soft: #eee8ff; --fc-green: #167a59; --fc-shadow: 0 16px 40px rgba(36, 28, 62, .10);
      }
      @media (prefers-color-scheme: dark) {
        :root {
          --fc-bg: #0f1219; --fc-card: #181d27; --fc-text: #f4f1fb;
          --fc-muted: #b8c0d1; --fc-border: #353b49; --fc-accent: #a98aff;
          --fc-accent-soft: #29223f; --fc-green: #63d7aa; --fc-shadow: 0 16px 44px rgba(0, 0, 0, .34);
        }
      }
      .fc-shell { color: var(--fc-text); font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; }
      .fc-hero {
        display: flex; align-items: flex-start; justify-content: space-between; gap: 20px;
        padding: 24px; border: 1px solid var(--fc-border); border-radius: 20px;
        background: linear-gradient(135deg, var(--fc-card), var(--fc-accent-soft)); box-shadow: var(--fc-shadow);
      }
      .fc-eyebrow { margin: 0 0 7px; color: var(--fc-accent); font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
      .fc-title { margin: 0; color: var(--fc-text); font-size: clamp(24px, 4vw, 38px); line-height: 1.08; letter-spacing: -.035em; }
      .fc-subtitle { max-width: 680px; margin: 10px 0 0; color: var(--fc-muted); font-size: 15px; line-height: 1.6; }
      .fc-badge { flex: 0 0 auto; padding: 8px 11px; border-radius: 999px; background: var(--fc-accent-soft); color: var(--fc-accent); font-size: 12px; font-weight: 800; }
      .fc-notice { min-height: 20px; margin: 12px 2px; color: var(--fc-muted); font-size: 13px; }
      .fc-notice[data-type="error"] { color: #d95772; } .fc-notice[data-type="success"] { color: var(--fc-green); }
      .fc-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 16px 0; }
      .fc-stat { padding: 17px; border: 1px solid var(--fc-border); border-radius: 16px; background: var(--fc-card); }
      .fc-stat span { display: block; color: var(--fc-muted); font-size: 12px; font-weight: 700; }
      .fc-stat strong { display: block; margin-top: 6px; color: var(--fc-text); font-size: 22px; letter-spacing: -.02em; }
      .fc-section { margin-top: 16px; padding: 20px; border: 1px solid var(--fc-border); border-radius: 18px; background: var(--fc-card); }
      .fc-section-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
      .fc-section h2 { margin: 0; color: var(--fc-text); font-size: 18px; }
      .fc-checkin-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 13px; }
      .fc-checkin-card { display: grid; gap: 8px; padding: 15px; border: 1px solid var(--fc-border); border-radius: 14px; background: var(--fc-bg); }
      .fc-prompt, .fc-pattern {
        display: grid; grid-template-columns: 1fr auto; gap: 14px; align-items: center;
        padding: 15px 0; border-top: 1px solid var(--fc-border);
      }
      .fc-prompt:first-child, .fc-pattern:first-child { border-top: 0; }
      .fc-prompt-title { margin: 0 0 4px; color: var(--fc-text); font-size: 15px; font-weight: 800; }
      .fc-copy { margin: 0; color: var(--fc-muted); font-size: 14px; line-height: 1.5; }
      .fc-action-card { padding: 15px; border-radius: 14px; background: var(--fc-accent-soft); color: var(--fc-text); }
      .fc-action-card strong { display: block; margin-bottom: 4px; color: var(--fc-accent); }
      .fc-button {
        min-height: 42px; border: 0; border-radius: 12px; padding: 10px 15px;
        background: var(--fc-accent); color: #fff; font: inherit; font-size: 14px; font-weight: 800; cursor: pointer;
      }
      .fc-button:hover { filter: brightness(1.06); }
      .fc-button:focus-visible, .fc-field:focus-visible { outline: 3px solid var(--fc-accent); outline-offset: 2px; }
      .fc-button--quiet { border: 1px solid var(--fc-border); background: transparent; color: var(--fc-text); }
      .fc-empty { padding: 22px; border: 1px dashed var(--fc-border); border-radius: 14px; text-align: center; color: var(--fc-muted); }
      .fc-dialog { width: min(620px, calc(100vw - 24px)); max-height: calc(100vh - 24px); overflow: auto; border: 1px solid var(--fc-border); border-radius: 20px; padding: 0; background: var(--fc-card); color: var(--fc-text); box-shadow: var(--fc-shadow); }
      .fc-dialog::backdrop { background: rgba(6, 8, 14, .68); backdrop-filter: blur(4px); }
      .fc-dialog-inner { padding: 22px; }
      .fc-dialog-head { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
      .fc-dialog h2 { margin: 0; font-size: 22px; } .fc-dialog .fc-copy { margin-top: 7px; }
      .fc-close { border: 0; background: transparent; color: var(--fc-muted); font-size: 25px; cursor: pointer; }
      .fc-form { display: grid; gap: 15px; margin-top: 20px; }
      .fc-label { display: grid; gap: 7px; color: var(--fc-text); font-size: 13px; font-weight: 800; }
      .fc-field { width: 100%; box-sizing: border-box; border: 1px solid var(--fc-border); border-radius: 11px; padding: 11px 12px; background: var(--fc-bg); color: var(--fc-text); font: inherit; }
      textarea.fc-field { min-height: 82px; resize: vertical; }
      .fc-range-row { display: flex; align-items: center; gap: 12px; } .fc-range-row input { flex: 1; accent-color: var(--fc-accent); }
      .fc-range-value { min-width: 34px; padding: 5px 8px; border-radius: 8px; background: var(--fc-accent-soft); color: var(--fc-accent); text-align: center; font-weight: 900; }
      .fc-form-actions { display: flex; justify-content: flex-end; gap: 9px; margin-top: 4px; }
      .fc-sidebar-button {
        width: calc(100% - 24px); min-height: 44px; margin: 10px 12px; border: 1px solid rgba(124, 92, 246, .3);
        border-radius: 12px; padding: 10px 12px; background: var(--fc-accent-soft); color: var(--fc-text);
        font: inherit; font-weight: 800; cursor: pointer;
      }
      @media (max-width: 840px) { .fc-grid { grid-template-columns: repeat(2, 1fr); } }
      @media (max-width: 560px) {
        .fc-hero { display: block; padding: 19px; } .fc-badge { display: inline-block; margin-top: 14px; }
        .fc-grid { grid-template-columns: 1fr 1fr; } .fc-stat { padding: 14px; }
        .fc-prompt, .fc-pattern { grid-template-columns: 1fr; } .fc-button { width: 100%; }
        .fc-section { padding: 16px; } .fc-form-actions { flex-direction: column-reverse; }
        .fc-checkin-grid { grid-template-columns: 1fr; }
      }
    `;
    document.head.appendChild(style);
  }

  function selectOptions(items) {
    return items.map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label || item.titulo)}</option>`).join("");
  }

  function dialogMarkup() {
    return `
      <dialog class="fc-dialog" data-conscious-dialog>
        <div class="fc-dialog-inner">
          <div class="fc-dialog-head">
            <div>
              <p class="fc-eyebrow">Pausa consciente</p>
              <h2>O que estava por trás dessa decisão?</h2>
              <p class="fc-copy" data-dialog-transaction></p>
            </div>
            <button class="fc-close" type="button" aria-label="Fechar" data-dialog-close>×</button>
          </div>
          <form class="fc-form" data-reflection-form>
            <label class="fc-label">Como você estava se sentindo?
              <select class="fc-field" name="emotion" required>${selectOptions(state.options.emotions)}</select>
            </label>
            <label class="fc-label">Qual era a intensidade?
              <span class="fc-range-row">
                <input name="intensity" type="range" min="1" max="5" value="3">
                <output class="fc-range-value" data-intensity-output>3</output>
              </span>
            </label>
            <label class="fc-label">Como você descreveria a decisão?
              <select class="fc-field" name="decision_type" required>${selectOptions(state.options.decision_types)}</select>
            </label>
            <label class="fc-label">O que estava acontecendo? <span class="fc-copy">Opcional</span>
              <textarea class="fc-field" name="context" maxlength="500" placeholder="Ex.: dia cansativo, comemoração, convite de amigos…"></textarea>
            </label>
            <label class="fc-label">O que passou pela sua cabeça? <span class="fc-copy">Opcional</span>
              <textarea class="fc-field" name="automatic_thought" maxlength="500" placeholder="Ex.: eu mereço, depois eu resolvo, preciso aproveitar…"></textarea>
            </label>
            <label class="fc-label">Qual próximo passo parece útil?
              <select class="fc-field" name="chosen_action">${selectOptions(state.options.actions)}</select>
            </label>
            <p class="fc-copy">${escapeHtml(state.options.privacy)}</p>
            <div class="fc-form-actions">
              <button class="fc-button fc-button--quiet" type="button" data-dialog-cancel>Agora não</button>
              <button class="fc-button" type="submit">Salvar reflexão</button>
            </div>
          </form>
        </div>
      </dialog>
    `;
  }

  function checkinDialogMarkup() {
    const checkin = state.week?.checkin || {};
    return `
      <dialog class="fc-dialog" data-checkin-dialog>
        <div class="fc-dialog-inner">
          <div class="fc-dialog-head">
            <div>
              <p class="fc-eyebrow">Check-in semanal</p>
              <h2>Como foi cuidar do dinheiro nesta semana?</h2>
              <p class="fc-copy">Não existe resposta certa. Use esta pausa apenas para observar.</p>
            </div>
            <button class="fc-close" type="button" aria-label="Fechar" data-checkin-close>×</button>
          </div>
          <form class="fc-form" data-checkin-form>
            <label class="fc-label">Quanto estresse financeiro você sentiu? (1 a 5)
              <input class="fc-field" name="financial_stress" type="range" min="1" max="5" value="${checkin.financial_stress || 3}">
            </label>
            <label class="fc-label">Quanta confiança você sentiu para lidar com o dinheiro? (1 a 5)
              <input class="fc-field" name="confidence" type="range" min="1" max="5" value="${checkin.confidence || 3}">
            </label>
            <label class="fc-checkin-card">
              <span>Evitei olhar contas, saldo ou fatura nesta semana</span>
              <input name="avoided_finances" type="checkbox" ${checkin.avoided_finances ? "checked" : ""}>
            </label>
            <label class="fc-label">O que você gostaria de lembrar? <span class="fc-copy">Opcional</span>
              <textarea class="fc-field" name="note" maxlength="500" placeholder="Uma frase curta sobre sua semana…">${escapeHtml(checkin.note || "")}</textarea>
            </label>
            <div class="fc-form-actions">
              <button class="fc-button fc-button--quiet" type="button" data-checkin-cancel>Agora não</button>
              <button class="fc-button" type="submit">Salvar check-in</button>
            </div>
          </form>
        </div>
      </dialog>`;
  }

  function dashboardMarkup() {
    const week = state.week;
    const prompts = state.prompts;
    const patterns = week.patterns || [];
    const emotion = week.dominant_emotion ? week.dominant_emotion.label : "Ainda observando";
    return `
      <div class="fc-shell">
        <div class="fc-hero">
          <div>
            <p class="fc-eyebrow">Modo Consciente</p>
            <h1 class="fc-title">Dinheiro com mais consciência.</h1>
            <p class="fc-subtitle">Observe padrões com curiosidade, sem culpa. Você escolhe o que responder e pode parar quando quiser.</p>
          </div>
          <span class="fc-badge">Privado e opcional</span>
        </div>
        <p class="fc-notice" data-conscious-notice>${escapeHtml(week.notice)}</p>
        <div class="fc-grid">
          <article class="fc-stat"><span>Reflexões na semana</span><strong>${week.reflections}</strong></article>
          <article class="fc-stat"><span>Emoção mais registrada</span><strong>${escapeHtml(emotion)}</strong></article>
          <article class="fc-stat"><span>Valor observado</span><strong>${brl(week.reflected_total)}</strong></article>
          <article class="fc-stat"><span>Cobertura voluntária</span><strong>${week.coverage_percentage}%</strong></article>
        </div>
        <section class="fc-section">
          <div class="fc-section-head">
            <div>
              <h2>Check-in da semana</h2>
              <p class="fc-copy">${week.checkin ? "Seu check-in está salvo e pode ser atualizado." : "Uma pausa de dois minutos para perceber como você está."}</p>
            </div>
            <button class="fc-button" type="button" data-open-checkin>${week.checkin ? "Atualizar" : "Fazer check-in"}</button>
          </div>
          <div class="fc-checkin-grid">
            <article class="fc-checkin-card"><span class="fc-copy">Estresse financeiro</span><strong>${week.checkin ? `${week.checkin.financial_stress} de 5` : "Ainda não registrado"}</strong></article>
            <article class="fc-checkin-card"><span class="fc-copy">Confiança para lidar com o dinheiro</span><strong>${week.checkin ? `${week.checkin.confidence} de 5` : "Ainda não registrada"}</strong></article>
          </div>
        </section>
        <section class="fc-section">
          <div class="fc-section-head"><h2>Convites para refletir</h2><span class="fc-badge">${prompts.length}</span></div>
          <div data-prompts>
            ${prompts.length ? prompts.map((prompt) => `
              <article class="fc-prompt">
                <div>
                  <p class="fc-prompt-title">${escapeHtml(prompt.transaction.description)} · ${brl(prompt.transaction.value)}</p>
                  <p class="fc-copy">${escapeHtml(prompt.explanation)}</p>
                </div>
                <button class="fc-button" type="button" data-reflect="${escapeHtml(prompt.id)}">Refletir</button>
              </article>
            `).join("") : '<div class="fc-empty">Nenhum gasto pede atenção agora. Isso também é uma boa notícia.</div>'}
          </div>
        </section>
        <section class="fc-section">
          <div class="fc-section-head"><h2>Padrões da semana</h2><span class="fc-badge">${patterns.length}</span></div>
          ${patterns.length ? patterns.map((pattern) => `
            <article class="fc-pattern">
              <div>
                <p class="fc-prompt-title">${escapeHtml(pattern.emotion_label)} + ${escapeHtml(pattern.category)}</p>
                <p class="fc-copy">${escapeHtml(pattern.question)}</p>
              </div>
              <div class="fc-action-card"><strong>Ação possível</strong>${escapeHtml(pattern.action)}</div>
            </article>
          `).join("") : '<div class="fc-empty">Depois de duas ou mais reflexões semelhantes, seus primeiros padrões aparecerão aqui.</div>'}
        </section>
        <section class="fc-section">
          <div class="fc-section-head"><h2>Próximo passo</h2></div>
          <div class="fc-action-card">
            <strong>${escapeHtml(week.next_step.titulo)}</strong>
            ${escapeHtml(week.next_step.descricao)}
          </div>
        </section>
        ${dialogMarkup()}
        ${checkinDialogMarkup()}
      </div>
    `;
  }

  async function load(root) {
    notice(root, "Carregando seu resumo…");
    try {
      if (window.FinPilotConsciousDemoData) {
        state.options = window.FinPilotConsciousDemoData.options;
        state.prompts = window.FinPilotConsciousDemoData.prompts;
        state.week = window.FinPilotConsciousDemoData.week;
        root.innerHTML = dashboardMarkup();
        bind(root);
        return;
      }
      const [optionsData, promptData, weekData] = await Promise.all([
        api("/api/conscious/options"),
        api(`/api/conscious/prompts?mes=${currentMonth()}`),
        api(`/api/conscious/weekly?semana=${today()}`),
      ]);
      state.options = optionsData;
      state.prompts = promptData.items;
      state.week = weekData;
      root.innerHTML = dashboardMarkup();
      bind(root);
    } catch (error) {
      root.innerHTML = `<div class="fc-shell">
        <div class="fc-hero">
          <div><p class="fc-eyebrow">Modo Consciente</p><h1 class="fc-title">Dinheiro com mais consciência.</h1>
          <p class="fc-subtitle">Check-in emocional, reflexão de gastos, padrões percebidos e próximos passos sem culpa.</p></div>
          <span class="fc-badge">Privado e opcional</span>
        </div>
        <section class="fc-section">
          <div class="fc-empty">${escapeHtml(error.message)}<br><button class="fc-button" type="button" data-conscious-retry>Tentar novamente</button></div>
        </section>
      </div>`;
      root.querySelector("[data-conscious-retry]")?.addEventListener("click", () => load(root));
    }
  }

  function openReflection(root, prompt) {
    state.activePrompt = prompt;
    const dialog = root.querySelector("[data-conscious-dialog]");
    dialog.querySelector("[data-dialog-transaction]").textContent =
      `${prompt.transaction.description} · ${brl(prompt.transaction.value)}`;
    dialog.showModal();
  }

  function bind(root) {
    root.querySelectorAll("[data-reflect]").forEach((button) => {
      button.addEventListener("click", () => {
        const prompt = state.prompts.find((item) => item.id === button.dataset.reflect);
        if (prompt) openReflection(root, prompt);
      });
    });
    const dialog = root.querySelector("[data-conscious-dialog]");
    const close = () => dialog.close();
    dialog.querySelector("[data-dialog-close]").addEventListener("click", close);
    dialog.querySelector("[data-dialog-cancel]").addEventListener("click", close);
    const range = dialog.querySelector('input[name="intensity"]');
    range.addEventListener("input", () => {
      dialog.querySelector("[data-intensity-output]").value = range.value;
    });
    dialog.querySelector("[data-reflection-form]").addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!state.activePrompt) return;
      const form = new FormData(event.currentTarget);
      const payload = {
        transaction_id: state.activePrompt.transaction.id,
        emotion: form.get("emotion"),
        intensity: Number(form.get("intensity")),
        decision_type: form.get("decision_type"),
        context: form.get("context") || null,
        automatic_thought: form.get("automatic_thought") || null,
        chosen_action: form.get("chosen_action") || null,
        trigger_source: state.activePrompt.trigger,
      };
      const submit = event.currentTarget.querySelector('button[type="submit"]');
      submit.disabled = true;
      try {
        await api("/api/conscious/reflections", { method: "POST", body: JSON.stringify(payload) });
        close();
        await load(root);
        notice(root, "Reflexão salva. Obrigado por observar esse momento.", "success");
        window.dispatchEvent(new CustomEvent("finpilot:conscious-saved", { detail: payload }));
      } catch (error) {
        notice(root, error.message, "error");
      } finally {
        submit.disabled = false;
      }
    });

    const checkinDialog = root.querySelector("[data-checkin-dialog]");
    const closeCheckin = () => checkinDialog.close();
    root.querySelector("[data-open-checkin]").addEventListener("click", () => checkinDialog.showModal());
    checkinDialog.querySelector("[data-checkin-close]").addEventListener("click", closeCheckin);
    checkinDialog.querySelector("[data-checkin-cancel]").addEventListener("click", closeCheckin);
    checkinDialog.querySelector("[data-checkin-form]").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const submit = event.currentTarget.querySelector('button[type="submit"]');
      submit.disabled = true;
      try {
        await api("/api/conscious/weekly-checkins", {
          method: "POST",
          body: JSON.stringify({
            week_start: today(),
            financial_stress: Number(form.get("financial_stress")),
            confidence: Number(form.get("confidence")),
            avoided_finances: form.get("avoided_finances") === "on",
            note: form.get("note") || null,
          }),
        });
        closeCheckin();
        await load(root);
        notice(root, "Check-in salvo. Obrigado por fazer essa pausa.", "success");
      } catch (error) {
        notice(root, error.message, "error");
      } finally {
        submit.disabled = false;
      }
    });
  }

  function mount(target) {
    const root = typeof target === "string" ? document.querySelector(target) : target;
    if (!root || root.dataset.consciousMounted === "true") return null;
    root.dataset.consciousMounted = "true";
    injectStyles();
    root.innerHTML = '<div class="fc-shell"><div class="fc-empty">Carregando Modo Consciente…</div></div>';
    load(root);
    return root;
  }

  function mountSidebar() {
    const sidebar = document.querySelector("[data-finpilot-sidebar]");
    const conscious = document.querySelector("[data-finpilot-conscious]");
    if (!sidebar || !conscious || sidebar.querySelector("[data-conscious-nav]")) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "fc-sidebar-button";
    button.dataset.consciousNav = "true";
    button.textContent = "◌  Modo Consciente";
    button.addEventListener("click", () => conscious.scrollIntoView({ behavior: "smooth", block: "start" }));
    sidebar.appendChild(button);
  }

  window.FinPilotConscious = { mount, open: openReflection };
  const boot = () => {
    document.querySelectorAll("[data-finpilot-conscious]").forEach(mount);
    mountSidebar();
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
