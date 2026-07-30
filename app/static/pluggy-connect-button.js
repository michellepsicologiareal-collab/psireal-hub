/**
 * Botão Pluggy para frontend HTML/JS sem Node.js.
 *
 * Uso:
 *   <aside data-finpilot-sidebar>...</aside>
 *   <script src="/static/pluggy-connect-button.js"></script>
 *
 * O script encontra a sidebar, cria o botão e carrega o widget oficial somente
 * depois do clique. PLUGGY_CLIENT_SECRET nunca é enviado ao navegador.
 */
(function () {
  "use strict";

  const SDK_URL = "https://cdn.pluggy.ai/pluggy-connect/v2.13.0/pluggy-connect.js";

  function loadSdk() {
    if (window.PluggyConnect) return Promise.resolve(window.PluggyConnect);
    return new Promise((resolve, reject) => {
      const existing = document.querySelector('script[data-pluggy-connect-sdk="true"]');
      if (existing) {
        existing.addEventListener("load", () => resolve(window.PluggyConnect), { once: true });
        existing.addEventListener("error", reject, { once: true });
        return;
      }
      const script = document.createElement("script");
      script.src = SDK_URL;
      script.async = true;
      script.dataset.pluggyConnectSdk = "true";
      script.onload = () => resolve(window.PluggyConnect);
      script.onerror = () => reject(new Error("Não foi possível carregar a conexão bancária."));
      document.head.appendChild(script);
    });
  }

  function setStatus(container, message, state) {
    const status = container.querySelector(".finpilot-pluggy-status");
    status.textContent = message || "";
    status.dataset.state = state || "";
  }

  async function readError(response) {
    try {
      const body = await response.json();
      return body.detail || body.message || "Não foi possível concluir.";
    } catch {
      return "Não foi possível concluir.";
    }
  }

  async function requestConnectToken() {
    const response = await fetch("/api/pluggy/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!response.ok) throw new Error(await readError(response));
    return response.json();
  }

  async function saveConnectionAndSync(itemId) {
    const save = await fetch("/api/pluggy/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_id: itemId }),
    });
    if (!save.ok) throw new Error(await readError(save));

    const sync = await fetch("/api/pluggy/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_id: itemId, dias: 365 }),
    });
    if (!sync.ok) throw new Error(await readError(sync));
    return sync.json();
  }

  function sdkConstructor(value) {
    return value && (value.default || value.PluggyConnect || value);
  }

  function createView() {
    const view = document.createElement("div");
    view.className = "finpilot-pluggy";
    view.innerHTML = [
      '<button type="button" class="finpilot-pluggy-button">',
      '<span class="finpilot-pluggy-icon" aria-hidden="true">⌁</span>',
      "<span>Conectar banco</span>",
      "</button>",
      '<p class="finpilot-pluggy-status" role="status" aria-live="polite"></p>',
    ].join("");
    return view;
  }

  function addStyles() {
    if (document.getElementById("finpilot-pluggy-styles")) return;
    const style = document.createElement("style");
    style.id = "finpilot-pluggy-styles";
    style.textContent = `
      .finpilot-pluggy { margin: 12px; }
      .finpilot-pluggy-button {
        width: 100%; min-height: 44px; display: flex; align-items: center;
        justify-content: flex-start; gap: 10px; border: 1px solid rgba(124, 92, 246, .28);
        border-radius: 12px; padding: 10px 12px; background: rgba(124, 92, 246, .12);
        color: inherit; font: inherit; font-weight: 700; cursor: pointer;
      }
      .finpilot-pluggy-button:hover { background: rgba(124, 92, 246, .2); }
      .finpilot-pluggy-button:focus-visible { outline: 3px solid #7c5cf6; outline-offset: 2px; }
      .finpilot-pluggy-button:disabled { cursor: wait; opacity: .65; }
      .finpilot-pluggy-icon { color: #7c5cf6; font-size: 22px; line-height: 1; }
      .finpilot-pluggy-status { margin: 7px 2px 0; min-height: 1.2em; font-size: 12px; opacity: .76; }
      .finpilot-pluggy-status[data-state="error"] { color: #c74463; opacity: 1; }
      .finpilot-pluggy-status[data-state="success"] { color: #16845f; opacity: 1; }
      @media (max-width: 760px) {
        .finpilot-pluggy { margin: 8px; }
        .finpilot-pluggy-button { justify-content: center; }
      }
    `;
    document.head.appendChild(style);
  }

  function mount(target) {
    const sidebar = typeof target === "string" ? document.querySelector(target) : target;
    if (!sidebar || sidebar.querySelector(".finpilot-pluggy")) return null;
    addStyles();
    const view = createView();
    const button = view.querySelector(".finpilot-pluggy-button");

    button.addEventListener("click", async () => {
      button.disabled = true;
      setStatus(view, "Abrindo conexão segura…");
      try {
        const [tokenData, sdkValue] = await Promise.all([requestConnectToken(), loadSdk()]);
        const PluggyConnect = sdkConstructor(sdkValue);
        if (typeof PluggyConnect !== "function") throw new Error("Widget bancário indisponível.");

        const widget = new PluggyConnect({
          connectToken: tokenData.accessToken,
          includeSandbox: sidebar.dataset.pluggySandbox === "true",
          language: "pt",
          onSuccess: async ({ item }) => {
            setStatus(view, "Banco conectado. Importando lançamentos…");
            try {
              const result = await saveConnectionAndSync(item.id);
              setStatus(
                view,
                `${result.importadas} lançamento(s) importado(s).`,
                "success"
              );
              window.dispatchEvent(new CustomEvent("finpilot:pluggy-synced", { detail: result }));
            } catch (error) {
              setStatus(view, error.message, "error");
            }
          },
          onError: (error) => {
            setStatus(view, error && error.message ? error.message : "Conexão não concluída.", "error");
          },
          onClose: () => {
            button.disabled = false;
          },
        });
        widget.init();
      } catch (error) {
        setStatus(view, error.message || "Não foi possível conectar agora.", "error");
        button.disabled = false;
      }
    });

    sidebar.appendChild(view);
    return view;
  }

  window.FinPilotPluggy = { mount };
  document.addEventListener("DOMContentLoaded", () => mount("[data-finpilot-sidebar]"), { once: true });
  if (document.readyState !== "loading") mount("[data-finpilot-sidebar]");
})();

